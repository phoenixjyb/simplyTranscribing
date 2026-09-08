# Installation and updates

## 1. Prepare the Windows host

Install Ubuntu 24.04 under WSL2 and a Windows NVIDIA driver that exposes the RTX 3090 to WSL. Confirm the GPU in Ubuntu with `/usr/lib/wsl/lib/nvidia-smi`. The worker explicitly selects an RTX 3090 and requires at least 10 GiB free according to both NVIDIA-SMI and the CUDA driver, with GPU utilization no higher than 50% at admission. It does not stop other GPU workloads or reserve capacity against another service starting later.

The Windows scheduled tasks must run as the same Windows user that owns this WSL distribution. Confirm `wsl.exe -l -v` before proceeding. Keep runtime files on the Linux filesystem rather than a Windows-mounted drive.

## 2. Install a fresh runtime in WSL

The commands below are for a **new installation only**. If `/opt/local-transcriber` already exists, preserve it and use the update section.

```bash
sudo apt-get update
sudo apt-get install -y python3-venv ffmpeg curl git
sudo mkdir /opt/local-transcriber
sudo chown "$USER":"$(id -gn)" /opt/local-transcriber
git clone https://github.com/phoenixjyb/simplyTranscribing.git /opt/local-transcriber
cd /opt/local-transcriber
umask 077
python3 -m venv .venv
.venv/bin/python -m pip install -r web-requirements.lock.txt
.venv/bin/python -m pip check
mkdir -p input output jobs logs models
chmod 700 run.sh service.sh web.sh
.venv/bin/python download_model.py
```

The full lock file is a reference Python 3.12/Linux installation, including both the web and CUDA inference packages. `requirements.txt` and `web-requirements.txt` specify direct dependencies if you need to resolve them separately. Never install these into an unrelated application's environment.

Model downloads default to the official Hugging Face host. If that host is unreachable, an explicitly chosen mirror can be configured with `HF_ENDPOINT`, for example `HF_ENDPOINT=https://hf-mirror.com .venv/bin/python download_model.py`. Every selected file is checked against the pinned manifest regardless of download host. Do not proceed until it prints `MODEL_FILES_VERIFIED`. No model weights are included in Git.

## 3. Configure account access

Use the exact login identities Tailscale reports, such as email addresses or a `username@github` login. Replace the illustrative values:

```bash
cd /opt/local-transcriber
.venv/bin/python configure_web.py \
  --allow-login 'first@example.com' \
  --allow-login 'second@example.com'
```

This creates private `web-config.json` with file mode 0600. On later runs it **replaces the full allowlist** while preserving the maintenance token. Include everyone who should retain access. The web server reloads this configuration on each request. With no allowed login and no valid maintenance token, job APIs deny access.

Accounts must also have access to the node through Tailscale membership or sharing and the applicable tailnet policy. Do not commit this file, put its maintenance token in browser JavaScript, or publish the real account list.

## 4. Register Windows tasks

In a Windows PowerShell session with permission to register tasks for the Windows user owning the distro, run the scripts from a source checkout or the WSL share:

```powershell
& '\\wsl.localhost\Ubuntu-24.04\opt\local-transcriber\install-service.ps1'
& '\\wsl.localhost\Ubuntu-24.04\opt\local-transcriber\install-web.ps1'
Get-ScheduledTask -TaskName 'Local Transcriber WSL','Local Transcriber Web'
curl.exe http://127.0.0.1:8020/health
```

If PowerShell execution policy blocks a downloaded script, review it and use your organization's approved script execution procedure. The web task's installed launcher uses a process-scoped execution-policy option; the scripts do not alter machine policy.

The scripts refuse to overwrite an existing task. The new web task starts at Windows boot, starts the queue task, and holds WSL open in the foreground. Both run as a limited S4U principal, have no execution time limit and permit three restart attempts. They do not wake the PC. The web task writes a launcher under the current Windows user's `.local-transcriber` folder. No other application's tasks are changed.

## 5. Serve privately with Tailscale

Install Tailscale on Windows, sign in to the desired account and enable unattended mode. Inspect any existing Serve configuration before adding a handler:

```powershell
$ts = 'C:\Program Files\Tailscale\tailscale.exe'
& $ts up --unattended=true
& $ts status
& $ts serve status
& $ts serve --bg http://127.0.0.1:8020
```

Use the HTTPS URL printed by Serve. The tailnet administrator may need to enable HTTPS certificates or Serve when prompted. If HTTPS port 443 already serves another application, choose a separate supported Serve port and retain that application's handler.

The backend binds only to `127.0.0.1:8020`. **Do not bind it to `0.0.0.0` or expose it through a generic public reverse proxy.** It trusts identity headers provided by the local Tailscale proxy. This setup uses private Serve; it does not enable Funnel.

Connect each client to Tailscale and verify the library, a small upload, progress and a download. If a shell-level HTTP proxy intercepts private addresses, try `curl --noproxy '*' https://YOUR-NODE.YOUR-TAILNET.ts.net/health` and configure private-host bypasses in that client as needed. Avoid changing unrelated global network settings.

References: [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve), [Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve), [Windows unattended mode](https://tailscale.com/docs/how-to/run-unattended).

## Optional SSH client

Configure Windows OpenSSH and a private host alias in the submitting computer's SSH configuration. Set `TRANSCRIBER_WINDOWS_ALIAS` to that alias. Optional variables:

| Variable | Meaning |
| --- | --- |
| `TRANSCRIBER_WINDOWS_ALIAS` | Required Windows SSH host/alias; never a command string |
| `TRANSCRIBER_DISTRO` | WSL distribution; defaults to `Ubuntu-24.04` |
| `TRANSCRIBER_RELAY_HELPER` | Optional executable wrapper accepting `PROFILE REMOTE_COMMAND` |
| `TRANSCRIBER_RELAY_PROFILE` | Required explicit profile when a helper is configured |

Without a helper, the client uses ordinary SSH; private SSH configuration may define a jump host. With a helper, that helper opens the relay and executes the quoted Windows SSH command there. Keep helper credentials/configuration outside this repository. The supplied client uses base64-encoded PowerShell to preserve arguments through Windows quoting rules.

For media already on the host, submit a WSL path with `--remote`. `--initial-prompt` can provide a recognition glossary and `--no-vad` disables voice activity filtering for a targeted rerun. Always use a new job/output directory.

## Update an existing installation

Publication to GitHub and deployment are separate operations. Preserve the existing input/output directories, model installation, credentials and other services. Review the source diff and run CPU tests before a live update.

For a host with this repository checked out and no conflicting local edits, fetch and review the intended revision, then update deliberately. An older installation without Git can receive worker source with `python3 deploy_source.py` and web source with `python3 deploy_web.py` from a configured client. These use the standard runtime path and preserve existing web credentials; they do not install dependencies or restart tasks.

Wait for uploads to finish before restarting only `Local Transcriber Web` for backend changes. Wait until the queue is idle before restarting `Local Transcriber WSL` for worker changes. Do not interrupt another application's processes to free GPU capacity. Verify web, queue, model files, GPU headroom and incumbent workloads separately after deployment.

To disable only this Serve mapping, use `tailscale serve --https=443 off`, after confirming it still refers to this application. Keep recordings and documents unless removal is explicitly intended.
