# Security

This is a private shared transcription workspace, not a public multi-tenant upload service. Everyone admitted by its access configuration can read the shared library. Media decoders run in the service account's OS context, so restrict access to trusted users and keep dependencies updated.

The server binds to loopback. Local mode requires both a loopback client address and a loopback Host header. Tailscale mode trusts identity headers supplied by Tailscale Serve on the same host; it must not be exposed through an arbitrary proxy or a LAN/public bind. Forwarded client headers are disabled in the supported launcher. No wildcard CORS policy is enabled.

Do not post credentials, private hostnames, recordings or transcripts in public issues. Use GitHub's **Security → Report a vulnerability** when available. If private reporting is unavailable, open an issue asking for a private reporting channel without including exploit details or private data. No security response SLA is currently promised. Report issues against the current default branch and state the exact revision tested.

The application stores recordings and results locally without automatic deletion or application-level encryption at rest. Account configuration and diagnostics are private deployment data. On Windows, protect the data directory with the service user's NTFS permissions; POSIX file modes do not provide an equivalent Windows ACL boundary.
