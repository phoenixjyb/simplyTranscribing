"""Select supported CPU/CUDA execution without assuming a GPU brand or OS."""
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid


def prepare_cuda_libraries():
    """Called in the launcher before importing CTranslate2; returns DLL handles."""
    import site
    directories = [p for root in site.getsitepackages() for p in Path(root).glob('nvidia/*/lib') if p.is_dir()]
    directories += [p for root in site.getsitepackages() for p in Path(root).glob('nvidia/*/bin') if p.is_dir()]
    if Path('/usr/lib/wsl/lib').is_dir():
        directories.append(Path('/usr/lib/wsl/lib'))
    paths = os.pathsep.join(map(str, directories))
    if paths:
        key = 'PATH' if os.name == 'nt' else 'LD_LIBRARY_PATH'
        os.environ[key] = paths + os.pathsep + os.environ.get(key, '')
    return [os.add_dll_directory(str(p)) for p in directories] if os.name == 'nt' else []


def cuda_state(index):
    """Query the same CUDA-visible ordinal used by CTranslate2, including UUID."""
    cuda = ctypes.CDLL('nvcuda.dll' if os.name == 'nt' else 'libcuda.so.1')
    def check(code):
        if code:
            raise RuntimeError(f'CUDA driver admission check failed: {code}')
    check(cuda.cuInit(0))
    device = ctypes.c_int()
    check(cuda.cuDeviceGet(ctypes.byref(device), index))
    raw_uuid = (ctypes.c_ubyte * 16)()
    check(cuda.cuDeviceGetUuid(ctypes.byref(raw_uuid), device))
    gpu_uuid = 'GPU-' + str(uuid.UUID(bytes=bytes(raw_uuid)))
    context = ctypes.c_void_p()
    check(cuda.cuCtxCreate_v2(ctypes.byref(context), 0, device))
    try:
        free, total = ctypes.c_size_t(), ctypes.c_size_t()
        check(cuda.cuMemGetInfo_v2(ctypes.byref(free), ctypes.byref(total)))
    finally:
        check(cuda.cuCtxDestroy_v2(context))
    executable = shutil.which('nvidia-smi')
    if not executable and Path('/usr/lib/wsl/lib/nvidia-smi').is_file():
        executable = '/usr/lib/wsl/lib/nvidia-smi'
    if not executable:
        raise RuntimeError('nvidia-smi is required for CUDA admission checks')
    output = subprocess.check_output([executable, '--id=' + gpu_uuid,
        '--query-gpu=memory.free,utilization.gpu', '--format=csv,noheader,nounits'], text=True, timeout=15)
    reported_free, utilization = [int(value.strip()) for value in output.strip().split(',')]
    return dict(uuid=gpu_uuid, free_mib=min(free.value // 1024**2, reported_free), utilization=utilization)


def resolve_runtime(args, backend=None):
    if args.device_index < 0 or args.cpu_threads < 1 or args.min_free_mib < 0 or not 0 <= args.max_gpu_utilization <= 100:
        raise ValueError('Invalid device index, thread count or GPU admission thresholds')
    if backend is None:
        import ctranslate2 as backend
    device = args.device
    if device == 'auto':
        device = 'cuda' if backend.get_cuda_device_count() else 'cpu'
    if device == 'cuda' and args.device_index >= backend.get_cuda_device_count():
        raise RuntimeError('The selected CUDA device is unavailable; choose --device cpu or another device index')
    supported = backend.get_supported_compute_types(device, args.device_index if device == 'cuda' else 0)
    compute = args.compute_type
    if compute == 'auto':
        preferred = 'int8' if device == 'cpu' else 'float16'
        compute = preferred if preferred in supported else 'float32'
    if compute not in supported:
        raise ValueError(f'{compute} is unsupported on {device}; supported types: {sorted(supported)}')
    admission = None
    if device == 'cuda':
        admission = cuda_state(args.device_index)
        if admission['free_mib'] < args.min_free_mib:
            raise RuntimeError('GPU admission: insufficient free memory; retry later or select a smaller model')
        if admission['utilization'] > args.max_gpu_utilization:
            raise RuntimeError('GPU admission: device is busy; retry later')
    return dict(device=device, device_index=args.device_index if device == 'cuda' else 0,
                compute_type=compute, admission=admission)
