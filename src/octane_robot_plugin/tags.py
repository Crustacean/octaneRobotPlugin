"""Robot and Octane tag normalization helpers."""

from __future__ import annotations

TAG_PREFIX = "octane_tag:"


def normalize_tag(value: str) -> str:
    """Normalize a Robot/Octane tag key for case-insensitive matching."""
    return value.strip().casefold()


def extract_robot_octane_tags(tags: object) -> list[str]:
    """Return stable Octane mapping tags from a Robot tag collection."""
    found: list[str] = []
    for tag in tags or []:
        raw = str(tag).strip()
        if raw.casefold().startswith(TAG_PREFIX):
            value = raw[len(TAG_PREFIX) :].strip()
            if value:
                found.append(value)
    return found


def extract_user_tag_names(user_tags: object) -> list[str]:
    """Normalize Octane user tag payloads into tag names.

    Octane relationship fields often arrive as {"data": [...]}, but some
    mocked or expanded responses may provide a plain list.
    """
    if not user_tags:
        return []

    tag_items: object
    if isinstance(user_tags, dict):
        tag_items = user_tags.get("data", [])
    else:
        tag_items = user_tags

    names: list[str] = []
    for item in tag_items or []:
        if isinstance(item, dict):
            candidate = item.get("name") or item.get("id")
        else:
            candidate = item
        if candidate:
            names.append(str(candidate).strip())
    return [name for name in names if name]
