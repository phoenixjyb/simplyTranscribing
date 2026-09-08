# Architecture

`app.py` supervises a loopback FastAPI server and a serial queue worker. The server streams uploads to the configured data directory, verifies media with FFprobe and atomically registers accepted jobs. `service.py` starts `transcribe.py` using the same Python interpreter, without a shell or OS-specific task scheduler.

Each inference process reads administrator-controlled runtime settings, selects CPU or CUDA and validates the requested compute type. CPU mode does not query CUDA. CUDA mode checks free memory and utilization for the actual selected device. A cross-platform file lock permits only one inference process per data directory. Different data directories are independent and can still compete for the same hardware; admission checks do not reserve resources.

Job records live under `jobs/`, uploaded media under `input/`, and final exports plus `run.json` and `segments.jsonl` under `output/ID/`. Segment journals are flushed throughout decoding. `complete=true` and completed queue state are required before the web API exposes downloads. Worker heartbeat timestamps are refreshed during inference and expire in the UI, without platform-specific PID probing.

Upload progress measures bytes transferred. Transcription progress measures the last decoded timestamp against recording duration and is capped at 99% until exports finish. Preparation, model download and silence can cause pauses. Percent complete is not an estimated remaining runtime. The browser polls every 2.5 seconds, so very short jobs can skip visible intermediate values.

The worker retains partial output on failure and marks abandoned running jobs interrupted when it restarts. There is no resumable inference, cancellation API or automatic retry. Re-upload the original media for a fresh job. Shutdown through the supported launcher requests worker cleanup; arbitrary process/OS termination has weaker guarantees.

Access is either local-browser mode with loopback Host/client validation, or Tailscale mode with a private login allowlist. Everyone admitted shares all jobs. Mutations require a custom request header and matching browser Origin; the app does not enable CORS. Transcript text is rendered as text, and download paths are allowlisted. The launcher disables forwarded-client headers. See SECURITY.md for the trust boundary and decoder limitations.
