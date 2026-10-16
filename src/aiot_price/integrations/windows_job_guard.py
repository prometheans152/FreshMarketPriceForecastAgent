"""Windows MCP transport-only fail-closed process-tree ownership.

The MCP *transport itself* joins a newly-created, private Job Object with
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.  Its ordinary child processes then inherit
that job.  If asyncio can never obtain a Process handle for a launched worker,
terminating the transport closes its job handle and Windows terminates those
children as well.  Do not assign the shared COS host, shell, or web server to
this job; call install_transport_job() only inside the dedicated MCP process.

Each numeric invocation also gets its own nested job, assigned while its
initial thread is suspended, so an invocation cannot strand descendants while
the transport stays alive. This is not a hard real-time scheduling guarantee
or protection from a malicious same-user local process.
"""
from __future__ import annotations

import os
import threading
import time

_TRANSPORT_JOB_HANDLE = None


def install_transport_job():
    """Require a private, verified kill-on-close job before stdio starts.

    Fail startup if Windows restrictions prevent assigning our own dedicated
    process; never silently downgrade the no-orphan claim.
    """
    global _TRANSPORT_JOB_HANDLE
    if os.name != "nt":
        raise RuntimeError("TW01 private MCP transport requires a Windows Job Object")
    if _TRANSPORT_JOB_HANDLE is not None:
        return _TRANSPORT_JOB_HANDLE

    import win32api
    import win32job

    job = win32job.CreateJobObject(None, "")
    info = win32job.QueryInformationJobObject(
        job, win32job.JobObjectExtendedLimitInformation
    )
    info["BasicLimitInformation"]["LimitFlags"] |= (
        win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    win32job.SetInformationJobObject(
        job, win32job.JobObjectExtendedLimitInformation, info
    )
    # GetCurrentProcess is a pseudo-handle; no other process is assigned.
    current_process = win32api.GetCurrentProcess()
    win32job.AssignProcessToJobObject(job, current_process)
    if not win32job.IsProcessInJob(current_process, job):
        raise RuntimeError("MCP transport did not enter its isolated Windows Job Object")
    _TRANSPORT_JOB_HANDLE = job  # keep it alive for the entire stdio session
    return job


def fail_closed_exit(exit_code: int = 125):
    """Abandon the entire *dedicated* MCP transport, never the COS host.

    In production, main() has already called install_transport_job(). Closing
    this process's job handle causes Windows to kill any remaining descendants.
    Tests which simulate an indefinitely pending process spawn must execute in
    a disposable child interpreter, not the pytest/COS process.
    """
    if os.name != "nt" or _TRANSPORT_JOB_HANDLE is None:
        # This condition never holds in production: main() fails before serve.
        # It prevents falsely claiming an orphan-safe shutdown in direct tests.
        raise RuntimeError("No Windows transport Job Object installed")
    os._exit(exit_code)


def _resume_suspended_process(pid: int):
    """Find and resume the sole initial thread using documented Win32 APIs.

    asyncio/Popen closes CreateProcess's primary-thread handle. A suspended
    worker has run no user code and must still have exactly that one thread.
    Never resume an ambiguous process or silently continue after API failure.
    """
    import ctypes
    from ctypes import wintypes

    class THREADENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ("Thread32First", "Thread32Next"):
        fn = getattr(kernel, name)
        fn.argtypes = (wintypes.HANDLE, ctypes.POINTER(THREADENTRY32))
        fn.restype = wintypes.BOOL
    kernel.OpenThread.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenThread.restype = wintypes.HANDLE
    kernel.ResumeThread.argtypes = (wintypes.HANDLE,)
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(0x00000004, 0)  # TH32CS_SNAPTHREAD
    if snapshot == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    thread_ids = []
    try:
        entry = THREADENTRY32()
        entry.dwSize = ctypes.sizeof(entry)
        present = kernel.Thread32First(snapshot, ctypes.byref(entry))
        if not present:
            raise ctypes.WinError(ctypes.get_last_error())
        while present:
            if entry.th32OwnerProcessID == pid:
                thread_ids.append(entry.th32ThreadID)
            entry.dwSize = ctypes.sizeof(entry)
            present = kernel.Thread32Next(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(snapshot)
    if len(thread_ids) != 1:
        raise RuntimeError("Suspended numeric worker does not have exactly one initial thread")
    thread = kernel.OpenThread(0x0002, False, thread_ids[0])  # THREAD_SUSPEND_RESUME
    if not thread:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        previous = kernel.ResumeThread(thread)
        if previous != 1:
            raise RuntimeError("Numeric worker initial thread was not suspended exactly once")
    finally:
        kernel.CloseHandle(thread)


class WorkerProcessJob:
    """Own one suspended numeric worker and its ordinary CreateProcess descendants.

    The caller itself is never assigned. The transport's outer job remains the
    fallback for a permanently pending spawn that has not returned a PID.
    """

    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("Numeric worker ownership requires Windows")
        import win32job
        self.handle = win32job.CreateJobObject(None, "")
        self._terminated = False
        info = win32job.QueryInformationJobObject(
            self.handle, win32job.JobObjectExtendedLimitInformation,
        )
        info["BasicLimitInformation"]["LimitFlags"] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(
            self.handle, win32job.JobObjectExtendedLimitInformation, info,
        )

    def attach_and_resume(self, pid: int):
        import win32api
        import win32con
        import win32job
        process = win32api.OpenProcess(
            win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE |
            win32con.PROCESS_QUERY_INFORMATION, False, pid,
        )
        try:
            win32job.AssignProcessToJobObject(self.handle, process)
            if not win32job.IsProcessInJob(process, self.handle):
                raise RuntimeError("Numeric worker did not enter its invocation Job Object")
            _resume_suspended_process(pid)
        finally:
            process.Close()

    def terminate(self):
        import win32job
        if not self._terminated:
            try:
                win32job.TerminateJobObject(self.handle, 125)
            except Exception:
                # The outer job is the fallback if the invocation tree cannot
                # be stopped or confirmed. Never release an unverified call.
                fail_closed_exit(125)
            self._terminated = True

    def active_processes(self) -> int:
        import win32job
        try:
            return win32job.QueryInformationJobObject(
                self.handle, win32job.JobObjectBasicAccountingInformation,
            )["ActiveProcesses"]
        except Exception:
            fail_closed_exit(125)

    def close(self):
        self.handle.Close()


class TransportDeadlineWatchdog:
    """One OS thread watches all MCP tool calls independently of asyncio.

    At the work deadline, exit this dedicated transport if a call is still
    active. That stops synchronous validation and a blocked CreateProcess as
    well as numeric descendants. The cleanup allowance is for termination
    confirmation only; it must never extend active work to 19 seconds.

    This is a fail-closed process bound, not a hard real-time scheduler.
    """

    def __init__(self, *, cleanup_seconds: float = 4.0):
        if not (0 < cleanup_seconds <= 4.0):
            raise ValueError("Cleanup allowance must be >0 and <=4 seconds")
        self.cleanup_seconds = cleanup_seconds
        self._condition = threading.Condition()
        self._calls: dict[int, float] = {}
        self._next_id = 0
        self._stopped = False
        self._started = False
        self._thread = threading.Thread(
            target=self._loop, name="tw01-mcp-job-failclosed-watchdog", daemon=True,
        )

    def start(self):
        with self._condition:
            if self._stopped or self._started:
                raise RuntimeError("Watchdog may be started once")
            self._started = True
            self._thread.start()

    def register(self, work_deadline: float) -> int:
        with self._condition:
            if not self._started or self._stopped:
                raise RuntimeError("Watchdog is not running")
            token = self._next_id
            self._next_id += 1
            self._calls[token] = work_deadline
            self._condition.notify_all()
            return token

    def unregister(self, token: int):
        with self._condition:
            self._calls.pop(token, None)
            self._condition.notify_all()

    def stop(self):
        with self._condition:
            self._stopped = True
            self._condition.notify_all()
        if self._started and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _loop(self):
        while True:
            with self._condition:
                if self._stopped:
                    return
                if not self._calls:
                    self._condition.wait()
                    continue
                until = min(self._calls.values()) - time.monotonic()
                if until > 0:
                    self._condition.wait(timeout=until)
                    continue
                # Make the expiry decision and abort atomic with unregister()
                # and stop(). Otherwise a completed call may unregister after
                # the lock is released but before fail_closed_exit executes,
                # unexpectedly killing a healthy MCP transport.
                # An active tool reached its work deadline;
                # a blocked event loop cannot be safely unwound, so abort only
                # this dedicated transport and its private Job Object.
                fail_closed_exit(125)
                return  # fail_closed_exit never returns in production
