# Contributing

Use a feature branch and a pull request with the problem, resulting behavior and relevant checks. Keep changes small enough to review. Bug reports should include OS, Python version, selected device/model, reproduction steps and redacted errors.

Install FFmpeg, create a Python 3.11+ virtual environment and install `requirements-test.txt`. Run `python -m unittest discover -p 'test_*.py' -v`, `python scripts/check_publication.py`, and `node --check web/app.js`. CPU tests use mocked inference and generated media; they need no GPU or downloaded model. Changes to model execution also need a bounded real-inference check with an explicitly chosen model/device. Label mocked, CPU, GPU, browser and deployment evidence separately.

Linux, macOS and Windows are CI targets. Do not introduce shell-only launch requirements into the core, unconditional CUDA imports or packages, machine-specific model names, source-relative runtime data, or untested claims of hardware support. WSL-specific helpers belong under `examples/wsl/`.

Never include real recordings, transcripts, tokens, account allowlists, SSH configuration, private addresses or raw deployment logs in a PR. Use synthetic examples. Configure Git with a public display name and your GitHub-provided noreply address before committing; commit metadata is public too. The automated publication check is heuristic and does not replace review.

Be respectful and specific in discussions. Review the code as well as its outcome, and welcome questions from people new to speech recognition or self-hosting. Contributions are made under the repository's MIT license; third-party code and model licenses must remain intact.
