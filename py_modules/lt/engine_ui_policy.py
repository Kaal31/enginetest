"""Engine-aware UI visibility policy.

Engine-neutral functionality remains available to both engines.  For now,
only fixes and DLC are treated as Moon-only.  The API tab, including sourced
keys, remains available with Luma as requested.
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
}


def is_luma_visible(tab_id: str) -> bool:
    return tab_id in LUMA_VISIBLE_TABS


def is_moon_only(tab_id: str) -> bool:
    return tab_id in MOON_ONLY_TABS


def visible_tabs(engine: str, tabs):
    if engine != "luma":
        return list(tabs)
    return [tab for tab in tabs if getattr(tab, "id", tab) in LUMA_VISIBLE_TABS]
