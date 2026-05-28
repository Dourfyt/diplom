"""
Шрифты ReportLab с поддержкой кириллицы для PDF-отчётов.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFError, TTFont

FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"

_BUNDLED_DIR = Path(__file__).resolve().parent / "fonts"
_SYSTEM_CANDIDATES: tuple[tuple[Path, Path], ...] = (
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ),
    (
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ),
    (
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ),
    (
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    ),
)


def _resolve_font_paths() -> tuple[Path, Path]:
    regular = _BUNDLED_DIR / "DejaVuSans.ttf"
    bold = _BUNDLED_DIR / "DejaVuSans-Bold.ttf"
    if regular.is_file() and bold.is_file():
        return regular, bold

    for reg_path, bold_path in _SYSTEM_CANDIDATES:
        if reg_path.is_file() and bold_path.is_file():
            return reg_path, bold_path

    raise FileNotFoundError(
        "Не найден шрифт с кириллицей для PDF. "
        f"Ожидаются файлы в {_BUNDLED_DIR} или системные DejaVu/Arial."
    )


@lru_cache(maxsize=1)
def ensure_pdf_cyrillic_fonts() -> tuple[str, str]:
    """Регистрирует TTF-шрифты в ReportLab (один раз за процесс)."""
    regular_path, bold_path = _resolve_font_paths()

    if FONT_REGULAR not in pdfmetrics.getRegisteredFontNames():
        try:
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular_path)))
        except TTFError as exc:
            raise FileNotFoundError(
                f"Не удалось загрузить шрифт PDF: {regular_path}"
            ) from exc

    if FONT_BOLD not in pdfmetrics.getRegisteredFontNames():
        try:
            pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))
        except TTFError as exc:
            raise FileNotFoundError(
                f"Не удалось загрузить жирный шрифт PDF: {bold_path}"
            ) from exc

    registerFontFamily(
        FONT_REGULAR,
        normal=FONT_REGULAR,
        bold=FONT_BOLD,
        italic=FONT_REGULAR,
        boldItalic=FONT_BOLD,
    )
    return FONT_REGULAR, FONT_BOLD
