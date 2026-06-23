"""Surveyor Micro Toolkit (SMT) - core engine for road/highway alignment math.

Layers: fpmath / wcb (foundation) -> alignment / vertical / crossfall / surface
(domain) -> builders -> check.  Pure, typed, tested.  See docs/blueprint.md.
"""
from . import (  # noqa: F401
    alignment,
    builders,  # noqa: F401
    check,  # noqa: F401
    crossfall,
    fpmath,
    surface,
    vertical,
    wcb,
)

__version__ = "0.1.0"
__all__ = ["fpmath", "wcb", "alignment", "vertical", "crossfall", "surface", "builders", "check"]
