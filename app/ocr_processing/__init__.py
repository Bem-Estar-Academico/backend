"""PDF / image processing package.

Small OCR helpers and regex-based parsers for RG/CNH.
This package is intentionally lightweight and intended to be run
inside the project's poetry environment where `pytesseract` and
`Pillow` are installed, and where the tesseract binary is available
on the system.
"""

from .improved_ocr import ocr

__all__ = ["ocr"]
