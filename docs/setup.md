# Setup and configuration

## Runtime requirements

Use Python 3.11 or newer and FFmpeg with `ffprobe` available on PATH. Install the application in its own virtual environment. Linux, macOS and native Windows use the same `python app.py init` / `python app.py start` flow in the README. There is no requirement for WSL, a particular GPU, a paid service or Tailscale.

The project is installed from source; no PyPI package or container image is currently published. A process supervisor can run `python app.py start` for unattended operation. Run initialization and the supervisor under the same OS account or explicitly provide the same `TRANSCRIBER_DATA_DIR`.

## Data directory

The default directory is:

| Platform | Default |
| --- | --- |
| Linux | `$XDG_DATA_HOME/simply-transcribing`, or `~/.local/share/simply-transcribing` |
| macOS | `~/Library/Application Support/simply-transcribing` |
| Windows | `%LOCALAPPDATA%\simply-transcribing` |

Override it before initialization and every subsequent command:

```bash
# Linux/macOS example
export TRANSCRIBER_DATA_DIR="$HOME/transcription-data"
```

```powershell
# Windows PowerShell example
$env:TRANSCRIBER_DATA_DIR = Join-Path $env:LOCALAPPDATA 'transcription-data'
```

Private configuration and artifacts belong here, never in a public source checkout. The earlier `TRANSCRIBER_ROOT` variable is accepted as a compatibility alias. Avoid committing either environment values or the contents of the directory.

## Inference settings

Edit `runtime.json` in the data directory. Settings are read for each new job:

```json
{
  "model": "base",
  "device": "cpu",
  "device_index": 0,
  "compute_type": "auto",
  "cpu_threads": 4,
  "min_free_mib": 1024,
  "max_gpu_utilization": 50,
  "offline": false
}
```

- Models: `tiny`, `base`, `small`, `medium`, `large-v3`; English-only `.en` variants are available except for `large-v3`.
- Device: `cpu` is predictable and does not probe the CUDA driver. `cuda` explicitly selects NVIDIA execution; `auto` selects CUDA if visible, otherwise CPU. A busy or misconfigured selected CUDA device causes a readable failure, not an unannounced CPU retry.
- Compute type: `auto` prefers `int8` on CPU and `float16` on CUDA, using `float32` when needed. Explicit choices are checked against CTranslate2's runtime capabilities.
- CUDA admission: `min_free_mib` and `max_gpu_utilization` apply to the chosen CUDA-visible ordinal. Increase the minimum for a larger model or shared host. Admission is a preflight check, not a reservation; another process can consume resources later.
- Offline: `false` permits first-use model download; `true` requires a cached model. `python download_model.py --model small --revision REVISION` can pin a selected model revision before an offline deployment. Set `HF_ENDPOINT` before starting the process if you deliberately use a model mirror.

For an individual file, `python transcribe.py recording.wav --output-dir new-results --device cpu --model tiny` bypasses the web queue. A fresh output directory is required. CLI exports include private provenance diagnostics; browser JSON downloads are sanitized. Run `python validate_output.py OUTPUT_DIRECTORY` to check export consistency, then review actual recognition against the recording.

## Optional CUDA

Install a compatible NVIDIA driver, CUDA 12 runtime and cuDNN 9 according to [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and [CTranslate2 installation guidance](https://opennmt.net/CTranslate2/installation.html). Linux x86_64 users can install the optional Python CUDA libraries with `python -m pip install -r requirements-cuda.txt`; Windows users should install the appropriate NVIDIA system libraries and make their DLLs discoverable.

The application launcher prepares library search paths before starting the worker. Use it for CUDA jobs, or configure library paths yourself when invoking `transcribe.py` directly. Set `device` to `cuda` and the desired `device_index` in the runtime configuration. Existing `CUDA_VISIBLE_DEVICES` filtering is respected; do not assume its logical index equals NVIDIA-SMI's physical index. Admission queries the CUDA-selected device's UUID to avoid checking a different GPU.

The default CPU path does not require `nvidia-smi`, CUDA libraries or a GPU. Apple Metal/MPS and AMD GPU backends are not implemented.

## Access modes

### Local browser

`python app.py init` defaults to local mode. Open `http://127.0.0.1:8020` on the server itself. The server checks the client and Host header against loopback addresses. Do not forward this mode to other machines. A local OS account/process is trusted at this boundary.

### Tailscale

For a fresh instance:

```bash
python app.py init --auth tailscale --allow-login first@example.com --allow-login second@example.com
python app.py start
```

Use exact login identities from your Tailscale account and replace the examples. To explicitly replace access on an already configured instance, use `python configure_web.py --allow-login first@example.com --allow-login second@example.com`; this selects Tailscale mode, replaces the complete allowlist and preserves the maintenance token.

Install Tailscale on the server and clients, grant appropriate tailnet/node access, and inspect existing Serve routes before adding this one:

```bash
tailscale serve status
tailscale serve --bg http://127.0.0.1:8020
```

Open the HTTPS address printed by Serve while connected to Tailscale. No personal server URL belongs in public setup documents. Windows hosts may need `tailscale up --unattended=true` for service operation outside a desktop login. The tailnet administrator may need to enable HTTPS/Serve.

Tailscale is optional. In both modes the backend binds only to loopback and ignores forwarded-client headers. Never expose trusted Tailscale identity headers through an arbitrary LAN/public reverse proxy. If port 443 already serves another application, preserve its configuration and use a suitable separate Serve port. See [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).

## Operation and upgrades

The launcher runs one web process and one queue worker. The model lives in a separate process per job. Keep the host awake. Closing the browser after an accepted upload does not stop processing. Stopping the launcher requests worker shutdown and terminates an active inference; partial results remain and the job must be resubmitted. Abrupt OS termination can also leave a stale running receipt until the worker restarts.

Upgrade source only after reviewing changes and completing active work. Keep the data directory and existing model cache. Back up configuration and recordings according to your requirements. Do not automatically restart unrelated GPU services or change their environment to accommodate an upgrade.

For the initial source-relative WSL release, explicitly set `TRANSCRIBER_DATA_DIR` to its existing runtime directory, retain its private `web-config.json`, and create a reviewed `runtime.json` with the intended model/device before migration. Existing configs without `auth_mode` remain Tailscale-restricted. Disable the old worker/web tasks only as part of an authorized cutover; never run old and new worker versions against the same queue. The previous frozen dependency snapshots and source-copy deployment helpers are retired because they were tied to one installation.
