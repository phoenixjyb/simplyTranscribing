# Architecture and security

The browser streams one file body to the FastAPI server through Tailscale Serve. The API checks authorization and origin, caps file size, checks free disk space, limits concurrent uploads to two and uses FFprobe to validate an audio track and duration. A completed upload is renamed from a partial file and registered atomically in the queue.

`service.py` holds a queue lock and runs one job at a time. It invokes `run.sh`, which configures the isolated CUDA libraries and launches `transcribe.py`. The speech model is loaded only in that job process. GPU selection and headroom checks happen before inference. Admission failure ends that job with a readable failure message; there is no automatic retry or cancellation endpoint.

## Job files and progress

| Runtime path | Contents |
| --- | --- |
| `input/ID.ext` | Uploaded recording with an opaque filename |
| `jobs/ID.json` | Queue state, title, language and submission time |
| `logs/ID.log` | Worker diagnostics |
| `output/ID/segments.jsonl` | Incremental, flushed segment journal |
| `output/ID/run.json` | Progress, input checksum, settings and completion receipt |
| `output/ID/transcript.*` | Final document exports |
| `service-health.json` | Queue process identity and readiness state |

Upload progress comes from bytes transferred. Processing progress comes from the last decoded segment's original timestamp divided by recording duration. It is capped at 99% until both the queue and export receipt indicate completion. Silence and model preparation can make progress pause; it is not a runtime estimate. The page polls every 2.5 seconds, so very short jobs can skip visible intermediate stages.

The worker journals each segment before exporting documents. A normal failure keeps diagnostics and partial segments; incomplete exports are not downloadable through the web UI. Restarting the queue marks interrupted jobs accordingly, preserving their output. It does not automatically resume partial inference. Resubmit the original recording for a fresh job.

## Trust boundary

Only the local Tailscale Serve proxy should reach the backend. The app trusts `Tailscale-User-Login` from that proxy and checks it against a private allowlist. Loopback is therefore part of the authentication boundary: a trusted local administrator/process can supply headers directly. This is a private shared service, not a multi-tenant internet service or a sandbox against hostile host users.

There are no per-user libraries. Everyone on the allowlist can view every job and download its documents. A generated maintenance token is accepted through a request header for local administration; keep it private. Browser assets contain no credentials. There is no public signup, password-reset flow, or public sharing link.

Mutating requests require `X-Transcriber-Request: 1` and, when present, a browser Origin matching the request Host. The app does not enable CORS. Transcript text is rendered with text nodes rather than inserted as HTML. Download paths are allowlisted; the web JSON export removes private host paths and worker diagnostics. CLI archives are administrator-level exports and include full provenance metadata.

Uploaded files are processed by FFmpeg/PyAV in the worker's OS context. Probe-time protocols are restricted and playlist formats are rejected, but the media decoder is not container-sandboxed. Keep dependencies patched and restrict access to trusted users. Runtime media and transcripts are retained until explicitly removed; backups and storage management are deployment responsibilities.
