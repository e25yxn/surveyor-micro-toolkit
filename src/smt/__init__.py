"""Surveyor Micro Toolkit (SMT) - core engine for road/highway alignment math.

Layers: fpmath / wcb (foundation) -> alignment / vertical / crossfall / surface
(domain) -> builders -> check.  Pure, typed, tested.  See docs/blueprint.md.
"""
from . import fpmath, wcb, alignment, vertical, crossfall, surface  # noqa: F401
from . import builders  # noqa: F401
from . import check  # noqa: F401

__version__ = "0.1.0"
__all__ = ["fpmath", "wcb", "alignment", "vertical", "crossfall", "surface", "builders", "check"]
