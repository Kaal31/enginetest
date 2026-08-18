"""Engine selection for SteamOS Game Mode.

The existing SLSsteam integration remains the Moon engine. This module adds a
second, isolated runtime profile containing ordinary SLSsteam + LumaLinux.

Important: this module does NOT install LumaLinux's upstream Game Mode/systemd
integration. EngineTest already owns the working gamescope-session hook. We only
install the native payloads and make that existing hook dispatch to the selected
profile.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from typing import Any, Dict, Optional

import httpx

from .logger import logger
from .paths import get_user_home

STATE_DIR = os.path.join(get_user_home(), ".config", "slsdeck")
STATE_PATH = os.path.join(STATE_DIR, "engine.json")
ENGINE_ROOT = os.path.join(get_user_home(), ".local", "share", "slsdeck", "engines")
MOON_ROOT = os.path.join(ENGINE_ROOT, "moon")
LUMA_ROOT = os.path.join(ENGINE_ROOT, "luma")
# Keep the existing EngineTest gamescope hook untouched: it already launches
# ~/.local/share/SLSsteam/path/steam. We replace that file's contents with this
# dispatcher instead of introducing another Gaming Mode entry point.
DISPATCHER = os.path.join(get_user_home(), ".local", "share", "SLSsteam", "path", "steam")

LUMA_SO_URL = "https://github.com/jayool/lumalinux/releases/latest/download/liblumalinux.so"
SLS_7Z_URL = "https://github.com/AceSLS/SLSsteam/releases/latest/download/SLSsteam-Any.7z"


def _home() -> str:
    return get_user_home()


def _write_json(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(tmp, path)


def _state() -> Dict[str, Any]:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("selected") in ("moon", "luma"):
            return data
    except Exception:
        pass
    return {"selected": "moon"}


def selected_engine() -> str:
    return str(_state().get("selected", "moon"))


def _set_selected(engine: str) -> None:
    if engine not in ("moon", "luma"):
        raise ValueError("unknown engine")
    _write_json(STATE_PATH, {"selected": engine, "changedAt": int(time.time())})


def _copy_if_exists(src: str, dst: str) -> bool:
    if not os.path.isfile(src):
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    os.chmod(dst, os.stat(src).st_mode | stat.S_IXUSR)
    return True


def _shared_sls_dir() -> str:
    return os.path.join(_home(), ".local", "share", "SLSsteam")


def _snapshot_current_moon() -> bool:
    """Preserve the currently installed Moon payload before Luma gets its own SLSsteam."""
    shared = _shared_sls_dir()
    so = os.path.join(shared, "SLSsteam.so")
    li = os.path.join(shared, "library-inject.so")
    if not os.path.isfile(so):
        return False
    os.makedirs(MOON_ROOT, exist_ok=True)
    _copy_if_exists(so, os.path.join(MOON_ROOT, "SLSsteam.so"))
    _copy_if_exists(li, os.path.join(MOON_ROOT, "library-inject.so"))
    for name in ("pattern-refresh", "pattern-cache.json"):
        _copy_if_exists(os.path.join(shared, name), os.path.join(MOON_ROOT, name))
    return os.path.isfile(os.path.join(MOON_ROOT, "SLSsteam.so"))


def _download(url: str, dest: str) -> None:
    if not url.lower().startswith("https://"):
        raise RuntimeError("refusing non-HTTPS download")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".download"
    try:
        with httpx.Client(follow_redirects=True, timeout=180) as client:
            with client.stream("GET", url) as r:
                for hop in list(r.history or []) + [r]:
                    if not str(hop.url).lower().startswith("https://"):
                        raise RuntimeError(f"redirected to non-HTTPS URL: {hop.url}")
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_bytes():
                        if chunk:
                            f.write(chunk)
        if os.path.getsize(tmp) <= 0:
            raise RuntimeError("downloaded file is empty")
        os.replace(tmp, dest)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _extract_7z(archive: str, dest: str) -> None:
    seven = next((shutil.which(x) for x in ("7z", "7za", "7zr") if shutil.which(x)), None)
    if not seven:
        raise RuntimeError("7z is required to install the Luma engine")
    os.makedirs(dest, exist_ok=True)
    r = subprocess.run([seven, "x", "-aoa", f"-o{dest}", archive],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError("SLSsteam archive extraction failed: " + (r.stdout or "")[-1500:])


def _find(root: str, name: str) -> Optional[str]:
    for base, _dirs, files in os.walk(root):
        if name in files:
            return os.path.join(base, name)
    return None


def install_luma() -> Dict[str, Any]:
    """Install isolated ordinary SLSsteam + LumaLinux payloads.

    This deliberately does not execute LumaLinux setup.sh: that script installs
    its own steam-launcher.service drop-in, desktop wrappers and guardian, which
    would conflict with EngineTest's existing Gaming Mode hook.
    """
    try:
        if not _snapshot_current_moon():
            return {"success": False, "error": "Could not snapshot the installed Moon SLSsteam.so"}

        os.makedirs(LUMA_ROOT, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="enginetest-luma-") as tmp:
            archive = os.path.join(tmp, "sls.7z")
            extract = os.path.join(tmp, "sls")
            _download(SLS_7Z_URL, archive)
            _extract_7z(archive, extract)
            sls = _find(extract, "SLSsteam.so")
            inject = _find(extract, "library-inject.so")
            if not sls:
                raise RuntimeError("SLSsteam.so not found in the release archive")
            _copy_if_exists(sls, os.path.join(LUMA_ROOT, "SLSsteam.so"))
            if inject:
                _copy_if_exists(inject, os.path.join(LUMA_ROOT, "library-inject.so"))
            _download(LUMA_SO_URL, os.path.join(LUMA_ROOT, "liblumalinux.so"))

        luma_cfg = os.path.join(_home(), ".config", "lumalinux")
        os.makedirs(luma_cfg, exist_ok=True)
        keys = os.path.join(luma_cfg, "keys.txt")
        if not os.path.exists(keys):
            with open(keys, "w", encoding="utf-8") as f:
                f.write("# LumaLinux depot key store\n")
                f.write("# depot_id;parent_app_id;manifest_gid;manifest_size;64-hex-key\n")

        _write_json(os.path.join(LUMA_ROOT, "engine.json"), {
            "name": "luma", "installedAt": int(time.time()),
            "slssteam": os.path.join(LUMA_ROOT, "SLSsteam.so"),
            "lumalinux": os.path.join(LUMA_ROOT, "liblumalinux.so"),
        })
        return {"success": True, "installed": True, "selected": selected_engine()}
    except Exception as exc:
        logger.warn(f"EngineTest: Luma install failed: {exc}")
        return {"success": False, "error": str(exc)}


def _engine_ready(engine: str) -> bool:
    if engine == "moon":
        return os.path.isfile(os.path.join(MOON_ROOT, "SLSsteam.so")) or os.path.isfile(os.path.join(_shared_sls_dir(), "SLSsteam.so"))
    return (os.path.isfile(os.path.join(LUMA_ROOT, "SLSsteam.so")) and
            os.path.isfile(os.path.join(LUMA_ROOT, "liblumalinux.so")))


def _dispatcher_content() -> str:
    moon = MOON_ROOT
    luma = LUMA_ROOT
    real = "/usr/bin/steam"
    return f'''#!/bin/sh
# EngineTest Steam dispatcher. One-shot wrapper; it disappears into Steam via exec.
ENGINE_FILE="$HOME/.config/slsdeck/engine.json"
MOON="{moon}"
LUMA="{luma}"
REAL="{real}"
engine="moon"
if [ -r "$ENGINE_FILE" ]; then
  engine="$(sed -n 's/.*"selected"[[:space:]]*:[[:space:]]*"\\(moon\\|luma\\)".*/\\1/p' "$ENGINE_FILE" | head -n1)"
fi
[ "$engine" = "luma" ] || engine="moon"
unset LD_AUDIT LD_PRELOAD LD_LIBRARY_PATH

if [ "$engine" = "luma" ] && [ -f "$LUMA/SLSsteam.so" ] && [ -f "$LUMA/liblumalinux.so" ]; then
  if [ -f "$LUMA/library-inject.so" ]; then
    export LD_AUDIT="$LUMA/library-inject.so:$LUMA/SLSsteam.so"
  else
    export LD_AUDIT="$LUMA/SLSsteam.so"
  fi
  export LD_PRELOAD="$LUMA/liblumalinux.so"
else
  # Missing/unready Luma always falls back to the known-good Moon payload.
  if [ -f "$MOON/SLSsteam.so" ]; then
    if [ -f "$MOON/library-inject.so" ]; then
      export LD_AUDIT="$MOON/library-inject.so:$MOON/SLSsteam.so"
    else
      export LD_AUDIT="$MOON/SLSsteam.so"
    fi
  fi
fi
exec "$REAL" "$@"
'''


def ensure_dispatcher() -> Dict[str, Any]:
    try:
        os.makedirs(os.path.dirname(DISPATCHER), exist_ok=True)
        with open(DISPATCHER, "w", encoding="utf-8") as f:
            f.write(_dispatcher_content())
        os.chmod(DISPATCHER, 0o755)
        return {"success": True, "path": DISPATCHER}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def status() -> Dict[str, Any]:
    s = _state()
    return {
        "success": True,
        "selected": s.get("selected", "moon"),
        "moonInstalled": _engine_ready("moon"),
        "lumaInstalled": _engine_ready("luma"),
        "dispatcher": os.path.isfile(DISPATCHER),
        "dispatcherPath": DISPATCHER,
        "lumaSlssteam": os.path.join(LUMA_ROOT, "SLSsteam.so"),
        "lumaLinux": os.path.join(LUMA_ROOT, "liblumalinux.so"),
    }


def set_engine(engine: str) -> Dict[str, Any]:
    if engine not in ("moon", "luma"):
        return {"success": False, "error": "Unknown engine"}
    if not _engine_ready(engine):
        return {"success": False, "error": f"{engine} engine is not installed"}
    r = ensure_dispatcher()
    if not r.get("success"):
        return r
    _set_selected(engine)
    return {"success": True, "selected": engine, "restartRequired": True}


def prepare() -> Dict[str, Any]:
    try:
        if os.path.isfile(os.path.join(_shared_sls_dir(), "SLSsteam.so")) and not _engine_ready("moon"):
            _snapshot_current_moon()
        return ensure_dispatcher()
    except Exception as exc:
        logger.warn(f"EngineTest: engine prepare failed: {exc}")
        return {"success": False, "error": str(exc)}
