from __future__ import annotations

ORIENTATION_OPTIONS: dict[str, str] = {
    "square": "Square",
    "portrait": "Portrait",
    "landscape": "Landscape",
}

GRID_OPTIONS_BY_ORIENTATION: dict[str, dict[str, str]] = {
    "square": {
        "2x2": "2×2",
        "3x3": "3×3",
        "4x4": "4×4",
    },
    "portrait": {
        "2x2": "2×2",
        "3x3": "3×3",
        "4x4": "4×4",
    },
    "landscape": {
        "2x2": "2×2",
        "3x3": "3×3",
        "4x4": "4×4",
    },
}


def is_allowed_orientation(value: str) -> bool:
    return value in ORIENTATION_OPTIONS


def get_grid_options(orientation: str) -> dict[str, str]:
    return GRID_OPTIONS_BY_ORIENTATION.get(orientation, {})


def is_allowed_grid(orientation: str, grid_code: str) -> bool:
    return grid_code in get_grid_options(orientation)