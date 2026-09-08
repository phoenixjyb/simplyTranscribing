# Validation boundaries

Automated tests cover export consistency, retained partial output, runtime configuration, CPU/CUDA device and compute-type selection, GPU admission failures, local/Tailscale access controls, upload validation and queue progress. Inference is mocked in the regular test suite; generated media is probed with FFprobe. A three-OS CI matrix targets Linux, macOS and Windows with Python 3.12.

These checks do not prove word accuracy, GPU driver compatibility or unattended host durability. A deployment should separately verify a bounded real CPU or GPU transcription, visible browser progress, document downloads and the intended client access route. Keep actual recordings, host identifiers, GPU serials and private logs outside public evidence.

Use `python validate_output.py OUTPUT_DIRECTORY` to compare exports and timestamp journals, then review names, technical terms, gaps and repeated phrases against the audio. State explicitly whether evidence comes from mocked tests, real inference, browser rendering, or a live deployment. No public performance guarantee is made for a particular recording length or hardware model.

For this portability change, the 17-test suite passed on macOS, and the earlier 16-test suite passed in an isolated WSL directory. A real synthetic speech sample was also transcribed with CUDA hidden, using CPU int8 execution; its expected two sentences were recovered. The launcher lifecycle check was subsequently added to the three-OS CI matrix. These are bounded implementation checks, not general accuracy or performance claims.
