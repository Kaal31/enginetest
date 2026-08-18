"""EngineTest entrypoint with the Moon/Luma engine control layer.

The original, large Decky implementation lives in main_legacy.py unchanged.
This thin subclass preserves every existing RPC and adds only engine controls.
"""
from __future__ import annotations

import asyncio

import decky

from main_legacy import Plugin as _LegacyPlugin
from lt import engine_manager


class Plugin(_LegacyPlugin):
    async def _main(self):
        # Keep the existing Gaming Mode startup path exactly as-is. The legacy
        # warm-up creates/repairs SLSsteam/path/steam; immediately after that,
        # replace that SAME wrapper with our engine dispatcher. No new daemon,
        # systemd service or second Game Mode launcher is introduced.
        try:
            import lt.slssteam as _sls
            _original = _sls.ensure_launch_wrapper
            def _ensure_and_dispatch():
                try:
                    _original()
                finally:
                    engine_manager.prepare()
            _sls.ensure_launch_wrapper = _ensure_and_dispatch
        except Exception as exc:
            decky.logger.warning(f"EngineTest: could not wrap launch-wrapper preparation: {exc}")
        await super()._main()

    async def get_engine_status(self):
        return await self._run(engine_manager.status)

    async def install_luma_engine(self):
        return await self._run(engine_manager.install_luma)

    async def set_engine(self, engine: str):
        return await self._run(engine_manager.set_engine, str(engine))

    async def get_selected_engine(self):
        return {"success": True, "selected": engine_manager.selected_engine()}
