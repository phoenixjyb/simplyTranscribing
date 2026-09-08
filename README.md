# Simply Transcribing

**Turn audio and video recordings into readable documents on your own machine.**

Simply Transcribing is a self-hosted web app for transcribing podcasts, interviews, lectures and other recordings. Upload a file, follow its progress, read the timestamped transcript, and download a Word document or subtitles. Speech recognition runs on your server using [faster-whisper](https://github.com/SYSTRAN/faster-whisper), with CPU execution by default and optional NVIDIA CUDA acceleration.

[![Checks](https://github.com/phoenixjyb/simplyTranscribing/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/phoenixjyb/simplyTranscribing/actions/workflows/checks.yml)

[Quick start](#quick-start) · [NVIDIA GPU setup](#nvidia-gpu-setup) · [Private sharing](#private-sharing) · [Documentation](#documentation) · [Contributing](#contributing)

![Simply Transcribing web UI showing upload controls, job progress and a transcript library with synthetic recordings](docs/web-ui.png)

*The screenshot uses synthetic examples.*

## What you can do

- **Upload audio or video.** Common inputs include MP3, MP4, WAV, M4A and FLAC; media must contain a decodable audio stream.
- **Follow each job.** Separate indicators show upload progress and transcription progress. Accepted recordings enter a queue and are processed one at a time.
- **Read and export.** Browse the shared library, open timestamped transcripts, and download Word, text, Markdown, SRT or JSON files.
- **Choose your hardware and model.** Run on a CPU or a supported NVIDIA GPU, with Whisper models from `tiny` to `large-v3`.
- **Use it locally or share privately.** Open the app on the server, or give trusted users access through Tailscale Serve.

No external transcription API or API key is required. Initial package and model downloads need internet access; recordings are processed on the machine running the service.

## Quick start

This starts a local instance using the **CPU** and the **`base` model**. For a Linux GPU server, you can go directly to the [Linux + CUDA installation tutorial](docs/linux-cuda.md).

### Prerequisites

- **Python 3.11 or newer**, with virtual environment support. CI uses Python 3.12. [Get Python](https://www.python.org/downloads/).
- **FFmpeg**, with `ffprobe` available on PATH. Run `ffprobe -version` to check. [Get FFmpeg](https://ffmpeg.org/download.html).
- **Git** to clone the source, and enough disk space for packages, models, uploaded media and results.

The app is installed from source. A packaged installer, PyPI release and application container image are not currently provided.

### Install and start

Choose the commands for your operating system. Run the application as your regular user in its own virtual environment.

<details open>
<summary><strong>Linux / macOS</strong></summary>

```bash
git clone https://github.com/phoenixjyb/simplyTranscribing.git
cd simplyTranscribing
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py init
python app.py start
```

On Ubuntu, install the prerequisites with `sudo apt install git python3 python3-venv python3-pip ffmpeg` after updating the package index. See the [Ubuntu walkthrough](docs/linux-cuda.md) for the full sequence.

</details>

<details>
<summary><strong>Windows PowerShell</strong></summary>

```powershell
git clone https://github.com/phoenixjyb/simplyTranscribing.git
cd simplyTranscribing
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py init
python app.py start
```

Use a Python 3.11+ installation. If `py` is unavailable but `python` points to that installation, use `python -m venv .venv`. If PowerShell blocks activation, skip the activation line and replace `python` in subsequent commands with `.\.venv\Scripts\python.exe`. [Python's virtual environment guide](https://docs.python.org/3/library/venv.html) explains both methods. Native Windows does not require WSL.

</details>

Open **[http://127.0.0.1:8020](http://127.0.0.1:8020)** in a browser **on the same machine**. For a headless server or another device, follow [private sharing](#private-sharing).

### Transcribe your first recording

1. Choose or drag in a short audio or video file.
2. Select automatic language detection, English or Chinese, and submit it.
3. Follow the queued job until it completes, then open its transcript.
4. Download a Word document or subtitle file and review it against the recording.

The first job downloads the selected model, which can delay visible transcription progress. Later jobs reuse the cache. Progress follows decoded recording timestamps; it is not an estimate of time remaining and may pause during preparation or silence.

Keep the launcher running and the host awake. Closing the browser after the upload is accepted does not stop the job. Pressing `Ctrl+C` in the launcher stops the service and interrupts active processing. On subsequent starts, activate the same environment and run `python app.py start`; initialization is only needed once.

## NVIDIA GPU setup

The default installation includes no NVIDIA libraries. GPU execution requires a compatible NVIDIA driver plus the CUDA libraries expected by the inference backend.

**[Follow the Linux + NVIDIA CUDA tutorial →](docs/linux-cuda.md)**

For an existing Linux x86_64 installation with a working driver, install the optional dependencies in the same virtual environment:

```bash
python -m pip install -r requirements-cuda.txt
```

Then set `device` to `cuda` in the data directory's `runtime.json` and start through `app.py`. Installing GPU packages alone does not change the default CPU selection. The tutorial covers driver checks, CUDA 12/cuDNN 9 libraries, configuration, a real transcription check and troubleshooting. Windows library setup is described in [setup and configuration](docs/setup.md#optional-cuda).

| Host | Execution options | Notes |
| --- | --- | --- |
| Linux | CPU or NVIDIA CUDA | The step-by-step GPU tutorial targets Ubuntu 24.04 x86_64 |
| macOS, Intel or Apple silicon | CPU | Metal/MPS acceleration is not implemented |
| Windows | CPU or NVIDIA CUDA | Uses the native Python launcher |
| WSL2 | CPU or NVIDIA CUDA | GPU access comes from the Windows host driver |

CUDA compatibility depends on the GPU, driver and available CTranslate2 wheels. AMD/Intel GPU acceleration is not implemented by this application. The three-OS CI suite checks application behavior with mocked inference; it does not establish GPU compatibility or transcription accuracy on every host. See [validation boundaries](docs/validation.md).

## Transcripts and downloads

| Format | Use it for |
| --- | --- |
| Word (`.docx`) | Reading, editing and sharing a document |
| Plain text (`.txt`) | Copying the transcript into another tool |
| Markdown (`.md`) | Notes and timestamped text workflows |
| SubRip (`.srt`) | Timestamped subtitles |
| JSON (`.json`) | Transcript text and segment data for scripts |

Automatic transcripts can contain mistakes. Review names, technical terms and timings before relying on or publishing them. Speaker identification, translation and editorial summaries are not included.

## Private sharing

The default local mode accepts a browser on the server itself. To access the app from another computer or phone, configure **Tailscale Serve** and an explicit allowlist of Tailscale login identities.

**[Set up private HTTPS access →](docs/setup.md#tailscale)**

The guide covers new and existing instances, client access and Serve configuration. Keep the backend on loopback and use the HTTPS address supplied by Tailscale Serve. Everyone admitted to an instance can view its entire library; separate private accounts and per-user libraries are not implemented. This app is intended for trusted users, not anonymous public uploads.

## Configuration and data

`python app.py init` prints the data directory and creates `runtime.json` and private access configuration. By default, data lives in the OS user-data directory, separate from this Git checkout. You can set `TRANSCRIBER_DATA_DIR` before initialization and every launch to choose another location. See [data directory settings](docs/setup.md#data-directory).

Edit `runtime.json` to choose the model, CPU/CUDA device, compute type, CPU threads and GPU admission thresholds. Changes apply to new jobs. The defaults use `base`, `cpu` and automatic compute-type selection. Larger models and longer recordings need more memory and disk space; GPU admission checks do not reserve resources against other workloads. See the [configuration reference](docs/setup.md#inference-settings).

To inspect configuration:

```bash
python app.py doctor
```

`doctor` reports configuration and FFprobe availability. A successful real transcription is still needed to verify inference on the selected hardware.

To prepare for offline inference, download the model while connected:

```bash
python download_model.py --model base
```

Then set `offline` to `true` in `runtime.json`. Cache each model you intend to use. Keep model files, recordings, transcripts and access configuration out of public Git history. Model downloads contact the selected model host; no external transcription API or application telemetry endpoint is included. Recordings and results have no automatic deletion policy, so plan disk usage and backups. See [privacy guidance](docs/privacy.md).

## Current limits

- Browser uploads are limited to **2 GiB per file** and **6 hours per recording**. These are input limits, not a promise that every host can process a recording of that size.
- One job runs at a time per instance. There is no cancellation API, automatic retry or resumable inference; an interrupted job must be resubmitted.
- Language choices in the web UI are automatic detection, English and Chinese. The CLI also accepts other Whisper language codes.
- No performance or word-accuracy guarantee is made for a particular GPU, model or recording.

## Documentation

| Guide | Contents |
| --- | --- |
| [Linux + NVIDIA CUDA tutorial](docs/linux-cuda.md) | Installation through the first GPU transcription |
| [Setup and configuration](docs/setup.md) | Runtime settings, Tailscale, offline use and upgrades |
| [Architecture](docs/architecture.md) | Web server, queue, inference processes and progress |
| [Validation boundaries](docs/validation.md) | What tests cover and how to check real results |
| [Privacy](docs/privacy.md) | Data handling and safe publication |
| [Security](SECURITY.md) | Trust boundaries and vulnerability reporting |
| [Optional WSL examples](examples/wsl/README.md) | Platform-specific deployment helpers |

## Contributing

Bug reports, documentation improvements and focused pull requests are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md). Include your OS, Python version, selected model/device and reproducible steps in an [issue](https://github.com/phoenixjyb/simplyTranscribing/issues); use synthetic media and redact private diagnostics. Report security issues through the process in [SECURITY.md](SECURITY.md).

From an activated development environment with FFmpeg installed:

```bash
python -m pip install -r requirements-test.txt
python -m unittest discover -p 'test_*.py' -v
python scripts/check_publication.py
```

Tests use generated media and mocked inference, so they do not download models or require a GPU. JavaScript source checks also use `node --check web/app.js` with Node.js installed. Keep runtime data outside Git and use public-safe commit metadata.

## License and acknowledgments

Simply Transcribing is available under the [MIT License](LICENSE). It uses faster-whisper and CTranslate2 for recognition, FastAPI for the web service, and python-docx for Word exports. Dependencies and downloaded models keep their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).
