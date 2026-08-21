"""LumaLinux engine backend.

Luma owns this backend's dependency and injection contract.  We intentionally do
not call upstream LumaLinux's setup.sh because that would install its own
steam-launcher.service/Game Mode integration. EngineTest already has a working
Gaming Mode entry point; Luma is embedded as a payload behind that entry point.

Dependency updates are isolated here: changing LumaLinux or the ordinary
SLSsteam release does not touch the Moon backend.
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

from ..logger import logger
from ..paths import get_user_home

ROOT = os.path.join(get_user_home(), ".local", "share", "slsdeck", "engines", "luma")
CONFIG = os.path.join(get_user_home(), ".config", "lumalinux")
LUMA_RELEASE = "https://github.com/jayool/LumaLinux/releases/latest/download/liblumalinux.so"
SLS_RELEASE = "https://github.com/AceSLS/SLSsteam/releases/latest/download/SLSsteam-Any.7z"


def _copy(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    os.chmod(dst, os.stat(src).st_mode | stat.S_IXUSR)


def _download(url: str, dst: str) -> None:
    if not url.startswith("https://"):
        raise RuntimeError("refusing non-HTTPS engine download")
    tmp = dst + ".download"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        with httpx.Client(follow_redirects=True, timeout=180) as client:
            with client.stream("GET", url) as r:
                if not str(r.url).startswith("https://"):
                    raise RuntimeError(f"non-HTTPS final URL: {r.url}")
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_bytes():
                        if chunk:
                            f.write(chunk)
        if os.path.getsize(tmp) == 0:
            raise RuntimeError("empty engine download")
        os.replace(tmp, dst)
    finally:
        try: os.remove(tmp)
        except OSError: pass


def _extract_7z(archive: str, dst: str) -> None:
    seven = next((shutil.which(x) for x in ("7z", "7za", "7zr") if shutil.which(x)), None)
    if not seven:
        raise RuntimeError("7z is required for the Luma engine's SLSsteam dependency")
    os.makedirs(dst, exist_ok=True)
    p = subprocess.run([seven, "x", "-aoa", f"-o{dst}", archive], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
    if p.returncode:
        raise RuntimeError((p.stdout or "SLSsteam extraction failed")[-1500:])


def _find(root: str, filename: str) -> Optional[str]:
    for base, _dirs, files in os.walk(root):
        if filename in files:
            return os.path.join(base, filename)
    return None


def installed() -> bool:
    return os.path.isfile(os.path.join(ROOT, "SLSsteam.so")) and os.path.isfile(os.path.join(ROOT, "liblumalinux.so"))


def install() -> Dict[str, Any]:
    """Install/update only Luma's dependency set."""
    try:
        os.makedirs(ROOT, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="enginetest-luma-") as tmp:
            archive = os.path.join(tmp, "SLSsteam.7z")
            unpack = os.path.join(tmp, "SLSsteam")
            _download(SLS_RELEASE, archive)
            _extract_7z(archive, unpack)
            sls = _find(unpack, "SLSsteam.so")
            inject = _find(unpack, "library-inject.so")
            if not sls:
                raise RuntimeError("SLSsteam.so missing from ordinary SLSsteam release")
            _copy(sls, os.path.join(ROOT, "SLSsteam.so"))
            if inject:
                _copy(inject, os.path.join(ROOT, "library-inject.so"))
            _download(LUMA_RELEASE, os.path.join(ROOT, "liblumalinux.so"))

        os.makedirs(CONFIG, exist_ok=True)
        keys = os.path.join(CONFIG, "keys.txt")
        if not os.path.exists(keys):
            with open(keys, "w", encoding="utf-8") as f:
                f.write("# LumaLinux depot key store\n")
                f.write("# depot_id;parent_app_id;manifest_gid;manifest_size;64-hex-key\n")
        with open(os.path.join(ROOT, "engine.json"), "w", encoding="utf-8") as f:
            json.dump({"engine": "luma", "updatedAt": int(time.time()), "slssteam": "SLSsteam.so", "lumalinux": "liblumalinux.so"}, f, indent=2)
        return {"success": True, "installed": installed()}
    except Exception as exc:
        logger.warn(f"Luma engine install/update failed: {exc}")
        return {"success": False, "error": str(exc)}


def prepare() -> Dict[str, Any]:
    """Validate Luma's private payload without touching Moon's installation."""
    return {"success": True, "installed": installed()}


def launcher_environment() -> Dict[str, str]:
    """Luma's complete injection contract.

    SLSsteam is injected through the ordinary library-inject/LD_AUDIT path;
    LumaLinux's own hook library is independently loaded through LD_PRELOAD.
    No Moon library is involved in this environment.
    """
    if not installed():
        raise RuntimeError("Luma engine is not installed")
    inject = os.path.join(ROOT, "library-inject.so")
    sls = os.path.join(ROOT, "SLSsteam.so")
    luma = os.path.join(ROOT, "liblumalinux.so")
    env: Dict[str, str] = {}
    env["LD_AUDIT"] = f"{inject}:{sls}" if os.path.isfile(inject) else sls
    env["LD_PRELOAD"] = luma
    return env


def status() -> Dict[str, Any]:
    return {"installed": installed(), "root": ROOT, "slssteam": os.path.join(ROOT, "SLSsteam.so"), "lumalinux": os.path.join(ROOT, "liblumalinux.so"), "config": CONFIG}
