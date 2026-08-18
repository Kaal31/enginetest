"""SLSsteam-moon engine backend.

Moon deliberately delegates to the existing, battle-tested SLSsteam module.
This module is the ownership boundary: Moon's installer/update/injection code
stays in slssteam.py and can evolve independently from the Luma backend.
"""
from __future__ import annotations

import os
import shutil
from typing import Any, Dict

from .. import slssteam
from ..logger import logger
from ..paths import get_user_home

ROOT = os.path.join(get_user_home(), ".local", "share", "slsdeck", "engines", "moon")


def installed() -> bool:
    return bool(slssteam.find_installed_lib()) or os.path.isfile(os.path.join(ROOT, "SLSsteam.so"))


def snapshot() -> bool:
    """Keep an independent Moon payload copy for engine switching.

    This is a cache of the dependency managed by slssteam.py, not a second Moon
    installer.  Updating/reinstalling Moon through the normal SLSsteam path can
    refresh it via snapshot().
    """
    src = slssteam.find_installed_lib()
    if not src:
        return os.path.isfile(os.path.join(ROOT, "SLSsteam.so"))
    os.makedirs(ROOT, exist_ok=True)
    try:
        shutil.copy2(src, os.path.join(ROOT, "SLSsteam.so"))
        # library-inject is resolved relative to the normal SLSsteam install.
        base = os.path.dirname(src)
        inject = os.path.join(base, "library-inject.so")
        if os.path.isfile(inject):
            shutil.copy2(inject, os.path.join(ROOT, "library-inject.so"))
        return True
    except Exception as exc:
        logger.warn(f"Moon engine snapshot failed: {exc}")
        return False


def prepare() -> Dict[str, Any]:
    """Let the existing Moon/SLSsteam integration prepare its own hook path."""
    try:
        snapshot()
        return {"success": True, "installed": installed()}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def launcher_environment() -> Dict[str, str]:
    """Return Moon's own launch environment.

    The dispatcher may select this environment, but it does not construct Moon's
    injection mechanism.  Moon remains responsible for LD_AUDIT/library-inject.
    """
    root = ROOT if os.path.isfile(os.path.join(ROOT, "SLSsteam.so")) else os.path.dirname(slssteam.find_installed_lib())
    env: Dict[str, str] = {}
    inject = os.path.join(root, "library-inject.so")
    sls = os.path.join(root, "SLSsteam.so")
    if os.path.isfile(inject):
        env["LD_AUDIT"] = f"{inject}:{sls}"
    elif os.path.isfile(sls):
        env["LD_AUDIT"] = sls
    return env


def status() -> Dict[str, Any]:
    return {"installed": installed(), "root": ROOT, "lib": os.path.join(ROOT, "SLSsteam.so")}
