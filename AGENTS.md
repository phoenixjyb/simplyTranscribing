# Simply Transcribing

This repository contains source and portable setup documentation for a private
Windows/WSL transcription service. Keep model weights, recordings, generated
transcripts, credentials, SSH configuration and machine-specific deployment
evidence outside Git.

- Preserve uncommitted work. Use feature branches after initial repository setup.
- Keep the web backend on loopback behind Tailscale Serve. Its identity headers
  are trusted only on this local proxy boundary; never bind it to the LAN.
- Preserve the serial GPU queue and admission checks for shared GPU workloads.
- Run `python -m unittest discover -p 'test_*.py' -v` with the CPU test dependencies
  and ffprobe installed. CI does not validate CUDA inference or Windows boot.
- Source publication does not authorize changing a live runtime. Deployments,
  service restarts and data removal need scope from the user's current request.
- Never reset existing scheduled tasks, overwrite web credentials or include
  personal hostnames/account IDs in public setup examples.
