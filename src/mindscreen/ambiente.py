"""Registro de versões e medição de memória no Windows, sem dependências extras."""

import ctypes
from importlib.metadata import distributions
import json
from pathlib import Path
import platform
import re
import sys


def peak_memory_mb():
    if sys.platform != "win32":
        return None
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    current = ctypes.windll.kernel32.GetCurrentProcess
    current.restype = wintypes.HANDLE
    info = ctypes.windll.psapi.GetProcessMemoryInfo
    info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not info(current(), ctypes.byref(counters), counters.cb):
        return None
    return round(counters.PeakWorkingSetSize / 1024**2, 2)


def register():
    if sys.prefix == sys.base_prefix:
        raise ValueError("Execute com o Python do ambiente virtual do projeto")
    packages = {}
    for dist in distributions():
        name, version = dist.metadata.get("Name", ""), dist.version
        if name.lower() == "mindscreen-ai":
            continue
        if re.fullmatch(r"[A-Za-z0-9_.-]+", name) and version and re.fullmatch(r"[A-Za-z0-9_.+!-]+", version):
            packages[name] = version
    Path("configs/requirements-lock.txt").write_text("\n".join(f"{name}=={packages[name]}" for name in sorted(packages, key=str.lower)) + "\n", encoding="utf-8")
    output = Path("reports/revisao")
    output.mkdir(parents=True, exist_ok=True)
    (output / "ambiente.json").write_text(json.dumps({"python": platform.python_version(), "sistema": platform.system(), "pacotes": packages}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Ambiente registrado: Python {platform.python_version()}, {len(packages)} pacotes")


if __name__ == "__main__":
    register()
