"""Engine-aware UI visibility policy.

The engine selector itself is engine-neutral.  Only features explicitly
classified as Moon-only are hidden when Luma is active.
"""

LUMA_VISIBLE_TABS = {
    "badges",
    "collections",
    "options",
    "api",
    "add_game",
    "about",
}

MOON_ONLY_TABS = {
    "fixes",
    "dlc",
    "sourced_keys",
}


def is_luma_visible(tab_id: str) -> bool:
    """Return whether a tab should remain visible with Luma selected."""
    return tab_id in LUMA_VISIBLE_TABS


def is_moon_only(tab_id: str) -> bool:
    """Return whether a tab is explicitly Moon-only for now."""
    return tab_id in MOON_ONLY_TABS


def visible_tabs(engine: str, tabs):
    """Filter tabs without changing their behavior or handlers."""
    if engine != "luma":
        return list(tabs)
    return [tab for tab in tabs if getattr(tab, "id", tab) in LUMA_VISIBLE_TABS]
