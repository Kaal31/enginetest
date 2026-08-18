"""Experimental Linux runtime watcher inspired by LumaLinux's KeyStore watcher.

This watcher is intentionally generic: it watches a directory and invokes a
callback after relevant file replacement/write activity. It does not unload a
native library or reinstall hooks. Native hook lifetime remains owned by the
engine that installed the hooks.
"""
from __future__ import annotations

import ctypes
import os
import struct
import threading
from typing import Callable, Optional

# Linux inotify constants. Kept local so the plugin has no Python dependency.
_IN_MODIFY = 0x00000002
_IN_CLOSE_WRITE = 0x00000008
_IN_MOVED_TO = 0x00000080
_IN_CREATE = 0x00000100
_IN_DELETE = 0x00000200
_IN_MOVED_FROM = 0x00000040
_IN_ATTRIB = 0x00000004
_IN_NONBLOCK = 0x800

_EVENT_HEADER = struct.Struct("iIII")


class DirectoryWatcher:
    """Small inotify wrapper that survives atomic replace/rename operations."""

    def __init__(self, directory: str, callback: Callable[[str], None]):
        self.directory = os.path.abspath(os.path.expanduser(directory))
        self.callback = callback
        self._fd: Optional[int] = None
        self._wd: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return True
        if not os.path.isdir(self.directory):
            return False
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        fd = libc.inotify_init1(_IN_NONBLOCK)
        if fd < 0:
            return False
        mask = (_IN_MODIFY | _IN_CLOSE_WRITE | _IN_MOVED_TO | _IN_CREATE |
                _IN_DELETE | _IN_MOVED_FROM | _IN_ATTRIB)
        wd = libc.inotify_add_watch(fd, self.directory.encode(), mask)
        if wd < 0:
            os.close(fd)
            return False
        self._fd, self._wd = fd, wd
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="EngineTestRuntimeWatch", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        fd, wd = self._fd, self._wd
        self._fd = self._wd = None
        if fd is not None:
            try:
                libc = ctypes.CDLL("libc.so.6", use_errno=True)
                if wd is not None:
                    libc.inotify_rm_watch(fd, wd)
            except Exception:
                pass
            try:
                os.close(fd)
            except OSError:
                pass
        t = self._thread
        if t and t is not threading.current_thread():
            t.join(timeout=1.0)
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            fd = self._fd
            if fd is None:
                return
            try:
                data = os.read(fd, 64 * 1024)
            except BlockingIOError:
                self._stop.wait(0.15)
                continue
            except OSError:
                return
            pos = 0
            while pos + _EVENT_HEADER.size <= len(data):
                _wd, _mask, cookie, name_len = _EVENT_HEADER.unpack_from(data, pos)
                pos += _EVENT_HEADER.size
                raw = data[pos:pos + name_len]
                pos += name_len
                name = raw.split(b"\0", 1)[0].decode("utf-8", "replace")
                if name:
                    try:
                        self.callback(os.path.join(self.directory, name))
                    except Exception:
                        # A watcher must never take the plugin down because a
                        # reload callback failed.
                        pass


__all__ = ["DirectoryWatcher"]
