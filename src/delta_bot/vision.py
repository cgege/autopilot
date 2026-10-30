from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

LOGGER = logging.getLogger(__name__)


def match_template(frame: np.ndarray, template_path: str | Path,
                   threshold: float = 0.82) -> tuple[int, int, float] | None:
    template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if template is None:
        LOGGER.warning("template missing: %s", template_path)
        return None
    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, location = cv2.minMaxLoc(result)
    if score < threshold:
        return None
    height, width = template.shape[:2]
    return location[0] + width // 2, location[1] + height // 2, float(score)


def read_text(frame: np.ndarray) -> str:
    """OCR adapter; install/configure Tesseract before using live OCR."""
    try:
        import pytesseract  # type: ignore
        return str(pytesseract.image_to_string(frame, config="--psm 6")).strip()
    except ImportError:
        LOGGER.warning("pytesseract is not installed; OCR result is empty")
        return ""
