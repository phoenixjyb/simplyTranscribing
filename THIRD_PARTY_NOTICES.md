# Third-party components

The project's MIT license covers its application code. It does not replace dependency, system-library, voice, or model licenses.

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper): MIT; provides Whisper inference through CTranslate2.
- [CTranslate2](https://github.com/OpenNMT/CTranslate2): MIT; backend hardware/runtime support depends on its build and platform.
- [Whisper](https://github.com/openai/whisper): MIT; consult the exact downloaded model repository and revision for its model card/license.
- [FFmpeg](https://ffmpeg.org/legal.html): licensing depends on the distribution/build configuration. FFmpeg is installed separately.
- NVIDIA drivers/CUDA/cuDNN are optional external components subject to NVIDIA's terms; they are not bundled in this repository.

Other dependencies retain their upstream notices. Inspect resolved packages and licenses when redistributing an environment, image, executable or model bundle. This repository currently distributes source only.
