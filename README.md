# Simply Transcribing

A private audio and video transcription service for a Windows PC with an RTX 3090, running in WSL2. Upload a recording, follow its progress, and read or download the transcript from a simple web page.

![Simply Transcribing web UI with illustrative sample jobs](docs/web-ui.png)

## What it does

- Drag-and-drop audio/video uploads, with separate upload and transcription progress.
- A shared library with timestamped transcript viewing.
- Word, plain text, SRT subtitles, Markdown and JSON downloads.
- Whisper large-v3 through faster-whisper, with automatic language detection or an English/Chinese selection in the UI.
- A durable serial job queue, incremental segment journal, and original recording timestamps.
- Private HTTPS through Tailscale Serve and an explicit account allowlist.
- GPU admission checks and model unloading after each job, to coexist with other GPU services.

The browser accepts files up to **2 GiB** and recordings up to **6 hours**. Keep the page open until the upload finishes; processing then continues in the background. Files and results are retained on the transcription PC until explicitly removed. The PC must remain powered on and awake.

## Set up

The reference deployment uses Windows, Ubuntu 24.04 on WSL2, Python 3.12, an NVIDIA RTX 3090, FFmpeg and Tailscale. Inference requires the GPU runtime; a CPU fallback is not implemented. Model weights and CUDA dependencies are installed on the transcription PC, not on a client laptop.

Follow **[the installation guide](docs/setup.md)** to install the runtime, configure allowed Tailscale logins and create the Windows startup task. Existing deployments should use the update guidance there instead of reinstalling over their data.

Once configured, connect a client to Tailscale and open the HTTPS address printed by `tailscale serve`. Choose a recording, optionally set its title and language, then select **Create transcript**. Completed entries offer **Read transcript** and document downloads. Everyone admitted by the allowlist shares the same library.

Automatic transcripts can contain mistakes, especially names and technical terms. This version transcribes the spoken language; it does not assign speakers, translate, or edit the recording into a summary.

## Command-line access

An optional macOS/Linux client submits files through Windows OpenSSH. Configure the destination in your private SSH configuration and export its alias:

```bash
export TRANSCRIBER_WINDOWS_ALIAS='transcription-pc'
python3 manage.py submit '/path/to/recording.mp4' --language auto
python3 manage.py status JOB_ID
python3 manage.py fetch JOB_ID --output-dir '/path/to/new-results'
```

The client assumes the standard `/opt/local-transcriber` installation and the `Local Transcriber WSL` Windows task. Optional relay configuration is described in [setup](docs/setup.md#optional-ssh-client). SSH is for administration and scripted submissions; normal web users only need Tailscale and a browser.

## Architecture and operations

The request path is browser → Tailscale Serve → loopback FastAPI server → filesystem queue → one GPU worker → documents. The lightweight web and queue processes stay resident; the speech model loads in a separate process per job. See [architecture and security](docs/architecture.md) for the trust boundary, job files, progress semantics and recovery behavior.

| File | Purpose |
| --- | --- |
| `web.py`, `web/` | Upload API, progress, transcript viewer and browser UI |
| `service.py`, `service.sh` | Serial queue worker |
| `transcribe.py`, `run.sh` | GPU admission, recognition and document exports |
| `configure_web.py` | Private account allowlist and maintenance-token initialization |
| `download_model.py`, `model-manifest.json` | Pinned model download and digest verification |
| `install-service.ps1`, `install-web.ps1` | Independent Windows scheduled tasks |
| `manage.py`, `bridge.py` | SSH submit/status/fetch client |
| `deploy_source.py`, `deploy_web.py` | Explicit source updates to an existing standard installation |
| `validate_output.py` | Export consistency and timestamp-gap reporting |

## Development checks

On Linux or macOS with Python 3.12 and `ffprobe` on PATH:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m unittest discover -p 'test_*.py' -v
```

These tests need no model weights or GPU. GitHub Actions runs them on Ubuntu, plus Python, shell and JavaScript syntax checks. GPU inference, Windows task behavior and Tailscale client access are separate validation steps. See [validation notes](docs/validation.md).

The repository contains source, configuration tooling and documentation. It intentionally excludes model weights, recordings, transcripts, private account configuration, SSH credentials and personal deployment records. The screenshot uses illustrative data.
