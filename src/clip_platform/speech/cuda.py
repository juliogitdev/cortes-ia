"""Registra as DLLs CUDA instaladas no venv GPU no Windows."""
import os
from pathlib import Path
import sys

_dll_handles = []


def configure_cuda_libraries():
    if sys.platform != 'win32':
        return
    base = Path(sys.prefix) / 'Lib' / 'site-packages' / 'nvidia'
    paths = [base / package / 'bin' for package in ('cublas', 'cudnn', 'cuda_nvrtc')]
    missing = [str(path) for path in paths if not path.is_dir()]
    if missing:
        raise RuntimeError('Bibliotecas CUDA ausentes no ambiente GPU: ' + ', '.join(missing))
    if not _dll_handles:
        _dll_handles.extend(os.add_dll_directory(str(path)) for path in paths)
