# Optional WSL integration

WSL is one host option, not a prerequisite. Use the core Python launcher and setup guide first. The scheduled-task examples here are for administrators who already have a configured Ubuntu distribution and a source checkout at `/opt/simply-transcribing` (override `SourceRoot` for another location).

`install-web.ps1` starts `app.py start` as a Windows boot task under the current Windows user. That launcher runs both the web process and worker; **do not also register a separate worker task for the same data directory**. The older `install-service.ps1` is retained for advanced worker-only supervision. Both scripts refuse existing task names. Set up the data directory under the same WSL account used by the task. Paths containing whitespace in task arguments need additional local quoting review. Reboot behavior needs a separate host test.

`bridge.py` and `manage.py` are legacy administration helpers for the original `/opt/local-transcriber` fixed-layout release. They are not the new portable client API. They require a private `TRANSCRIBER_WINDOWS_ALIAS` and optionally an explicit relay helper/profile. Credentials and real routes must remain outside this repository. New deployments should use the web UI or direct `transcribe.py` invocation until a portable remote CLI is provided.
