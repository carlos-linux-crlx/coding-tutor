"""Exec an app-managed runtime with limits before native code starts."""

import ctypes
import os
import resource
import signal
import sys


def main():
    parent, mib, threads, executable, *arguments = sys.argv[1:]
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != int(parent):
        raise SystemExit(1)
    memory_limit = int(mib) * 1024 ** 2
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (240, 245))
    available = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, available[:int(threads)])
    os.nice(10)
    os.execv(executable, [executable, *arguments])


if __name__ == "__main__":
    main()
