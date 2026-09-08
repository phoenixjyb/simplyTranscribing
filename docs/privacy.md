# Privacy and publication

Runtime configuration, model caches, recordings, transcripts, SSH credentials, account lists and raw diagnostics are not source artifacts. Keep them in the configured data directory and outside Git. Use synthetic recordings and screenshots in issues, documentation and tests. `scripts/check_publication.py` checks tracked files for common private-data and credential patterns, but it cannot prove that arbitrary text or images are anonymous.

The application sends no recordings to an external transcription API. Downloading a model contacts the chosen model host. The supported launcher disables Hugging Face telemetry, while the model download itself still exposes ordinary network metadata to that host. The application does not implement encryption at rest or automatic retention/deletion. Configure host storage permissions, backups and deletion practices for your needs.

Browser exports omit internal paths and GPU diagnostics. Administrator-level CLI exports and worker logs can contain the input path, original text and device details; do not attach them unredacted to public reports. A shared instance is visible to every allowed user, not a private library per account.

Git commits also publish author and committer names/emails. Configure a public-safe display name and your GitHub noreply email before committing. Removing information from the latest files does not remove it from Git history or copies already downloaded. Review initial history and release artifacts as well as the current tree before a public launch. Coordinate any history rewrite with existing collaborators and keep a private backup.
