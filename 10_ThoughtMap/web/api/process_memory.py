"""Resident memory of the current process, without a required dependency.

Memory is the number the worker-count decision rests on (T6 #14, #15): the
embedding matrix and the model weights are large, and if two workers duplicate
them then two workers cost twice the RAM for the same corpus. That question has
to be answerable on any machine, so this falls back from psutil to the platform
APIs rather than reporting nothing.
"""

from __future__ import annotations

import sys


def _psutil_bytes() -> tuple[int, int] | None:
    try:
        import psutil  # noqa: PLC0415

        info = psutil.Process().memory_info()
        # peak_wset exists on Windows only; elsewhere current is the best psutil
        # offers here and the platform branch below fills in the peak.
        peak = int(getattr(info, "peak_wset", 0)) or 0
        return int(info.rss), peak
    except Exception:
        return None


def _windows_bytes() -> tuple[int, int] | None:
    try:
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)

        # argtypes are not optional here. Without them the pseudo-handle -1
        # returned by GetCurrentProcess is marshalled as a 32-bit int, arrives
        # as 0x00000000FFFFFFFF instead of an all-ones HANDLE, and the call
        # fails silently with a zeroed struct.
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.GetCurrentProcess.argtypes = []
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(ProcessMemoryCounters)
        if not psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            return None
        return int(counters.WorkingSetSize), int(counters.PeakWorkingSetSize)
    except Exception:
        return None


def _posix_bytes() -> tuple[int, int] | None:
    current = 0
    peak = 0
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    current = int(line.split()[1]) * 1024
                elif line.startswith("VmHWM:"):
                    peak = int(line.split()[1]) * 1024
    except Exception:
        pass

    if not peak:
        try:
            import resource

            # ru_maxrss is KB on Linux and bytes on macOS.
            raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            peak = raw if sys.platform == "darwin" else raw * 1024
        except Exception:
            pass

    if not current and not peak:
        return None
    return current or peak, peak or current


def memory_bytes() -> tuple[int, int] | None:
    """(resident, peak) bytes for this process, or None if unavailable."""
    if sys.platform == "win32":
        # Preferred on Windows because it reports the peak too; psutil would
        # need a separate call for that.
        return _windows_bytes() or _psutil_bytes()

    from_psutil = _psutil_bytes()
    from_posix = _posix_bytes()
    if from_psutil and from_posix:
        return from_psutil[0], max(from_psutil[1], from_posix[1])
    return from_psutil or from_posix


def resident_mb() -> float | None:
    measured = memory_bytes()
    return round(measured[0] / (1024 * 1024), 1) if measured else None


def peak_mb() -> float | None:
    measured = memory_bytes()
    return round(measured[1] / (1024 * 1024), 1) if measured else None
