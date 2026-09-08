# Validation record

The initial implementation was exercised on an RTX 3090 under Ubuntu 24.04/WSL2 with Whisper large-v3, faster-whisper 1.2.1 and CTranslate2 4.8.2. Model files were verified against the pinned manifest.

Observed reference runs included a full 43-minute recording and shorter audio/video checks. A 90-second browser-uploaded clip produced 22 segments in approximately 24 seconds of worker time; intermediate browser progress was observed before completion. These are examples, not a throughput guarantee.

The original deployment passed real browser upload, intermediate progress, GPU completion, transcript preview, Word download, mobile layout and denied unauthenticated access. A client connected through real Tailscale HTTPS without a maintenance credential and downloaded a Word document matching the previously reviewed output byte-for-byte. Unrelated GPU services stayed healthy and GPU allocation returned to its pre-job baseline.

The source prepared for this repository includes portable SSH configuration, neutral UI labels and a configuration helper. The export, interruption-recovery, SSH argument/configuration and HTTP tests exercise the packaged source without loading a model. CI runs those CPU tests; it does not run inference, register Windows tasks or contact a private tailnet.

Before the initial publication, all ten packaged tests passed in an isolated temporary directory on the reference WSL host. The revised SSH transport also passed read-only PowerShell parameter-block and WSL execution checks. Python, shell and browser JavaScript syntax checks passed; the neutral UI screenshot and a 390-pixel layout were inspected without exposing real jobs.

The live deployment and repository snapshot should not be assumed identical after future source changes. Actual reboot/sleep-wake behavior, arbitrary-length recordings, every client device and transcription word accuracy require separate acceptance checks. A successful export-consistency test does not establish speech accuracy. Review names, technical terms, substantial gaps and repeated phrases against the audio when quality matters.

Personal recordings, actual transcripts, raw deployment logs, account identities and host addresses are intentionally excluded from this repository. The README screenshot uses synthetic illustrative jobs.
