# Linux with an NVIDIA GPU: installation tutorial

This walkthrough uses **Ubuntu 24.04 LTS on x86_64** and its Python 3.12. Other Linux distributions need equivalent OS packages. You can use an existing Linux GPU workstation or server; WSL and a particular GPU model are not required. ARM/Jetson installations need a separate compatible dependency stack and are outside this walkthrough.

**Release status:** these instructions accompany the portability work in [PR #1](https://github.com/phoenixjyb/simplyTranscribing/pull/1). Until it is merged, use the branch shown below; the initial `main` implementation does not have this setup flow.

## What to install

| Component | Purpose | Installation |
| --- | --- | --- |
| NVIDIA driver and `nvidia-smi` | Access and admission checks for the GPU | OS/vendor packages; often already installed |
| Python 3.11+ and virtual environment support | Application runtime | Ubuntu commands below install Python 3.12 |
| Git and FFmpeg, including `ffprobe` | Source checkout and media probing | Ubuntu packages |
| Application Python dependencies | Web UI, queue, recognition and document exports | `requirements-cuda.txt` in a virtual environment |
| CUDA 12 cuBLAS and cuDNN 9 libraries | GPU inference | Included by `requirements-cuda.txt` on Linux x86_64 |
| Whisper model files | Speech recognition | Download explicitly below, or on the first job |
| Tailscale, optional | Private access from other devices | [Access-mode instructions](setup.md#tailscale) |

The wheel-based installation does not need PyTorch, a CUDA compiler (`nvcc`), the full development toolkit, Docker, or an API key. The GPU libraries installed by pip do **not** install the kernel driver. The library versions follow [faster-whisper's GPU requirements](https://github.com/SYSTRAN/faster-whisper#gpu); check those requirements when upgrading dependencies.

Start with `base` and a short recording. Larger models need more GPU memory, and long media also consumes system RAM and disk space. There is no single memory threshold that guarantees every recording will fit.

## 1. Verify the driver

If Linux and CUDA are already working, run this and continue to step 2:

```bash
nvidia-smi
```

It should list the intended GPU without a driver error. The displayed CUDA version describes driver compatibility; it does not prove that cuBLAS or cuDNN is installed in your Python environment. Use a current driver supported by your GPU and the selected CUDA 12 libraries.

For a fresh **native Ubuntu desktop** installation, Ubuntu provides automatic driver selection:

```bash
sudo apt update
sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers list
sudo ubuntu-drivers install
```

Reboot after installation when existing work can be stopped, then run `nvidia-smi` again. Follow any Secure Boot key-enrollment instructions shown by the installer. Compute servers can use Ubuntu's `--gpgpu` driver route and matching NVIDIA utilities; see the [official Ubuntu driver guide](https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/). Keep a working vendor/cloud driver installation unless it needs an update for compatibility.

**WSL2 users:** skip Linux driver installation. Install the NVIDIA driver on Windows; WSL receives GPU access from that host driver. Follow [NVIDIA's WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html). The remaining Ubuntu userspace steps apply, but this tutorial does not configure Windows startup or networking.

## 2. Install the application and GPU libraries

Run the following on the Linux server. Only OS package installation needs `sudo`; run the application as your regular user.

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg
python3 --version
ffprobe -version

git clone --branch codex/portable-open-source https://github.com/phoenixjyb/simplyTranscribing.git
cd simplyTranscribing
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-cuda.txt
python -m pip check
```

After PR #1 is merged, a normal clone of `main` can be used. If you already have this checkout, enter it and activate its virtual environment instead of cloning again. Use [upgrade guidance](setup.md#operation-and-upgrades) for an existing service.

Internet access is needed for packages and the initial model download. Model and GPU-library downloads can be large; keep sufficient free disk space. No model files belong in the Git checkout.

## 3. Initialize and select CUDA

Use the same data-directory setting in every terminal or supervisor that runs the application:

```bash
export TRANSCRIBER_DATA_DIR="$HOME/transcription-data"
python app.py init
```

Initialization prints the private data directory and creates local-browser access configuration. For an existing instance, skip `init`; it intentionally refuses to replace access settings.

Update just the inference settings, preserving other configuration:

```bash
python - <<'PY'
import json
from settings import data_root

path = data_root() / "runtime.json"
config = json.loads(path.read_text(encoding="utf-8"))
config.update(model="base", device="cuda", device_index=0, compute_type="auto")
path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY

python download_model.py --model base
python app.py doctor
```

`doctor` should show `ffprobe: true`, `configured: true`, and `device: "cuda"`. It reports configuration; it does **not** load the GPU model or prove successful inference. With explicit `cuda`, an unavailable or busy GPU produces an error rather than silently switching to CPU.

`device_index` is a CUDA-visible index. If you set `CUDA_VISIBLE_DEVICES`, index `0` means the first device in that filtered list. The application checks that selected device's free memory and utilization before inference. Defaults are 1024 MiB minimum free memory and at most 50% utilization; these are admission thresholds, not memory sizing guarantees. See [inference settings](setup.md#inference-settings) before selecting a larger model or using a shared GPU.

## 4. Start the web UI and verify a real transcription

```bash
python app.py start
```

The launcher discovers the pip-installed NVIDIA libraries and supplies their search paths to the worker before it starts. Leave this terminal running. On a browser on the same machine, open **http://127.0.0.1:8020**.

1. Upload a 10–30 second audio or video recording with clearly audible speech.
2. Watch upload progress and then the transcription job status until completion.
3. Open the transcript and compare it with what was spoken.
4. Download a Word document and a subtitle file, and open both.

For a headless server or another person's device, configure [Tailscale access](setup.md#tailscale) before using the remote browser. The default local mode is for a browser on the server. The Tailscale section includes changing an already initialized instance's allowlist. Keep the application bound to loopback; everyone granted access shares the same transcript library.

The first successful job under the explicit CUDA configuration is the inference check. You can observe `nvidia-smi` in another terminal, although short jobs may finish between samples. CI uses mocked inference and cannot establish GPU compatibility on your host. This tutorial has been checked against the application and upstream installation guidance; a fresh native Linux GPU installation has not been exercised by the maintainers for this documentation change.

For another shell session, return to the checkout, activate `.venv`, and export the same `TRANSCRIBER_DATA_DIR` before starting again. Closing the browser does not cancel an accepted job. Stopping the launcher or shutting down the host interrupts active processing; see [operation guidance](setup.md#operation-and-upgrades).

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `nvidia-smi` fails or no GPU appears | Fix the host driver first; verify GPU passthrough on a VM. On WSL, check the Windows driver. |
| `libcuda.so.1` is missing | The driver library is unavailable to this Linux process; pip cuBLAS/cuDNN packages cannot supply it. |
| `libcublas.so.12` or `libcudnn.so.9` cannot be loaded | Activate the same virtual environment used for installation, install `requirements-cuda.txt`, and launch with `app.py start`. Check for incompatible system library overrides. |
| CUDA driver/runtime incompatibility | Compare the installed NVIDIA library versions with the driver's supported versions; follow the driver vendor's upgrade guidance. A working `nvidia-smi` alone does not prove library compatibility. |
| Selected CUDA device unavailable | Check `CUDA_VISIBLE_DEVICES` and `device_index`. Verify that the installed CTranslate2 wheel supports the host/GPU. |
| GPU admission says busy or insufficient memory | Wait for other work to finish, choose an available GPU, or use a smaller model with an appropriate memory threshold. Admission does not reserve GPU memory. |
| CUDA out of memory after admission | Try a smaller model or supported `int8_float16` compute type and a short sample. Other processes may have consumed memory after the check. |
| Missing `ffprobe` | Install FFmpeg and ensure the launcher account can find `ffprobe` on PATH. |
| Model download fails, or offline model is missing | Check network access to the model host; cache the chosen model before enabling `offline`. |
| Remote browser cannot connect or gets 403 | Use the configured Tailscale HTTPS route and exact allowed login identities; local mode only accepts loopback access. |

If using `transcribe.py` directly instead of the launcher, set the NVIDIA library path **before starting Python**. From the activated virtual environment on Linux:

```bash
export LD_LIBRARY_PATH="$(python -c 'import os, site; from pathlib import Path; print(os.pathsep.join(str(p) for root in site.getsitepackages() for p in Path(root).glob("nvidia/*/lib") if p.is_dir()))')${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python transcribe.py /path/to/short-recording.wav \
  --output-dir "$TRANSCRIBER_DATA_DIR/gpu-smoke-01" --device cuda --model base
python validate_output.py "$TRANSCRIBER_DATA_DIR/gpu-smoke-01"
```

Replace the input path and use a new output directory for each run. CLI exports include private provenance diagnostics; keep them out of public bug reports. Validation checks export consistency, and listening to the recording checks recognition quality. See [privacy guidance](privacy.md) before sharing diagnostics.
