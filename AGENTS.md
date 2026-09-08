# Simply Transcribing

This is a portable source repository. Keep runtime data, model weights, credentials, personal identifiers and private deployment records outside Git. Use feature branches and a reviewable pull request.

- CPU execution is the default. CUDA is optional, device-index based, and must retain admission checks. Never hard-code a GPU model or require CUDA packages on CPU hosts.
- Run through `app.py`; core code must not require WSL, Bash or a scheduled task. Keep platform-specific examples separate.
- Preserve the loopback security boundary and explicit authentication modes. Never expose trusted identity-header authentication on a public/LAN bind.
- Use the runtime data directory, not the source checkout, for configuration and artifacts.
- Run the CPU test suite, publication hygiene script and relevant platform/browser/inference checks. State which checks were actually run.
- Do not change a running deployment, rewrite published history or remove user data without current task authority. Git publication and deployment are separate.
- Use public-safe commit metadata. Never include private addresses or credentials in PR bodies or examples.
