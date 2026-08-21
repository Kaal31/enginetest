"""Engine backends.

Each backend owns its dependency layout, installation/update logic, and Steam
hook/injection contract.  engine_manager is intentionally only the selector and
lifecycle coordinator; it must not know how an engine injects itself.
"""

from .moon import MoonEngine
from .luma import LumaEngine

__all__ = ["MoonEngine", "LumaEngine"]
