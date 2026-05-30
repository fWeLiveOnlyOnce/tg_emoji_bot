from __future__ import annotations

ORIENTATION_OPTIONS: dict[str, str] = {
    "square": "Квадрат",
    "portrait": "Вертикальная",
    "landscape": "Горизонтальная",
}

# grid_code формата "{cols}x{rows}" (столбцы × строки).
# square    — равные стороны
# portrait  — строк больше, чем столбцов (выше, чем шире)
# landscape — столбцов больше, чем строк (шире, чем выше)
GRID_OPTIONS_BY_ORIENTATION: dict[str, dict[str, str]] = {
    "square": {
        "2x2": "2×2",
        "3x3": "3×3",
        "4x4": "4×4",
    },
    "portrait": {
        "2x3": "2×3",
        "3x4": "3×4",
        "2x4": "2×4",
    },
    "landscape": {
        "3x2": "3×2",
        "4x3": "4×3",
        "4x2": "4×2",
    },
}


def is_allowed_orientation(value: str) -> bool:
    return value in ORIENTATION_OPTIONS


def get_grid_options(orientation: str) -> dict[str, str]:
    return GRID_OPTIONS_BY_ORIENTATION.get(orientation, {})


def is_allowed_grid(orientation: str, grid_code: str) -> bool:
    return grid_code in get_grid_options(orientation)