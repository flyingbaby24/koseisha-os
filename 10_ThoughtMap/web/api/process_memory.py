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


def private_mb() -> float | None:
    """Memory this process would need even if every file page were dropped.

    Resident memory is not all equal. Most of this process's footprint is
    file-backed — 449 MB of memory-mapped ONNX weights, the 15.5 MB prepared
    `/map` response, the interpreter and its shared libraries — and the OS can
    drop those pages under pressure and re-read them. Only private, anonymous
    memory has to fit no matter what.

    That distinction is why resident memory here fluctuates by tens of MB
    between otherwise identical runs: when the machine has RAM to spare, more
    of the mapped weight file stays resident, and the number goes up without
    the process wanting anything more.

        Windows  PrivateUsage — the commit charge. Includes committed-but-
                 untouched pages, so it reads high in absolute terms; what it
                 is good for is the *delta* against resident memory.
        Linux    /proc/self/smaps_rollup Anonymous, which is exact. See
                 `verify_heap_trim`, which reports it directly.

    None where neither is available.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class ProcessMemoryCountersEx(ctypes.Structure):
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
                    ("PrivateUsage", ctypes.c_size_t),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.GetCurrentProcess.argtypes = []
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            psapi.GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ProcessMemoryCountersEx),
                wintypes.DWORD,
            ]

            counters = ProcessMemoryCountersEx()
            counters.cb = ctypes.sizeof(ProcessMemoryCountersEx)
            if not psapi.GetProcessMemoryInfo(
                kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
            ):
                return None
            return round(counters.PrivateUsage / (1024 * 1024), 1)
        except Exception:
            return None

    try:
        with open("/proc/self/smaps_rollup", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("Anonymous:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        pass
    return None


def release_free_heap() -> bool:
    """Ask the allocator to return its free arenas to the OS. True if it ran.

    Loading the corpus allocates far more than it keeps: the 542 MB artifact is
    parsed, merged and reshaped, and the intermediates are freed long before
    the first request. Freed, however, is not the same as returned — glibc's
    malloc holds the arenas for reuse, so the process keeps a resident
    high-water mark it will never need again. Measured here, releasing the
    corpus object gives back 106.6 MB of 219.4, leaving ~113 MB of free heap
    the process is still charged for.

    `malloc_trim(0)` walks those arenas and releases what is genuinely free. It
    is the one lever that reaches this memory, and it exists only on glibc:

        Linux + glibc   trims, which is what a Render instance runs
        musl (Alpine)   no such symbol; returns False
        Windows, macOS  no equivalent that returns heap to the OS; False

    Deliberately not emulated elsewhere. Windows offers `SetProcessWorkingSetSize`,
    which trims the *working set* by pushing pages to standby rather than
    freeing anything — it would improve the number this module reports while
    changing nothing about what the process holds, which would make every
    measurement in this codebase a lie.

    Safe to call at any time: it only affects free memory, never live objects.
    """
    if not sys.platform.startswith("linux"):
        return False

    try:
        import ctypes

        # Not ctypes.CDLL("libc.so.6"): the process already has libc mapped,
        # and resolving through the running image works whatever the soname.
        libc = ctypes.CDLL(None)
        trim = getattr(libc, "malloc_trim", None)
        if trim is None:  # musl
            return False
        trim.argtypes = [ctypes.c_size_t]
        trim.restype = ctypes.c_int
        trim(0)
        return True
    except Exception:
        return False


def resident_mb() -> float | None:
    measured = memory_bytes()
    return round(measured[0] / (1024 * 1024), 1) if measured else None


def peak_mb() -> float | None:
    measured = memory_bytes()
    return round(measured[1] / (1024 * 1024), 1) if measured else None
