"""vertical - Vertical alignment (profile) engine (Domain layer).

Port from reference/Vertical.gs (validated engine, AllTests 45/45).

Model: profile = ordered list of VerticalSegment, each covering [sta_start, sta_end].

Grade units : percent (%).  Elevation units: same as input (metres).
LVC conventions
  lvc = 0, lvc2 = None : tangent grade (no vertical curve)
  lvc > 0, lvc2 = None : symmetric parabolic VC  (total length = lvc)
  lvc > 0, lvc2 > 0    : asymmetric (unequal-tangent) VC — arms lvc (L1) and lvc2 (L2)

Segment table column order (matches tables.json "vtable"):
  [index] | sta_start | sta_end | level | grade_in | grade_out | lvc | (lvc2)

Standalone module (no dependency on fpmath, wcb, or alignment).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Data type
# ---------------------------------------------------------------------------

@dataclass
class VerticalSegment:
    """One vertical alignment segment.

    level    : elevation at sta_start (PVC level).
    grade_in : entry grade (%).
    grade_out: exit grade  (%).
    lvc      : vertical curve length (0 = tangent grade; >0 = VC length).
               For asymmetric VC this is the first arm L1.
    lvc2     : second arm L2 for asymmetric VC; None for symmetric or tangent.
    """
    sta_start: float
    sta_end: float
    level: float
    grade_in: float
    grade_out: float
    lvc: float
    lvc2: float | None


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------

def _has_second_arm(seg: VerticalSegment) -> bool:
    return seg.lvc2 is not None


# ---------------------------------------------------------------------------
# Public: single-segment calculations
# ---------------------------------------------------------------------------

def calculate_elevation_at(seg: VerticalSegment, sta: float) -> float:
    """Elevation at station sta within one segment.

    lx = sta - seg.sta_start (arc distance from segment start).
    Returns the parabolic (or tangent) elevation at sta.

    For symmetric VC: level = base + (grade_out-grade_in)/(200*l1) * lx²
    For asymmetric VC (two arms l1, l2):
      arm 1 (lx ≤ l1): level = base + e*(lx/l1)²
      arm 2 (lx > l1): level = levPVT - (grade_out/100)*lx2 + e*(lx2/l2)²
      where e = l1*l2/(200*(l1+l2)) * (grade_out-grade_in)  [middle ordinate at VPI, signed]
    """
    lx = sta - seg.sta_start
    base = seg.level + (seg.grade_in / 100.0) * lx   # tangent grade from PVC

    l1 = seg.lvc
    if not l1:
        return base                              # tangent grade segment

    if not _has_second_arm(seg):                # symmetric VC
        return base + (seg.grade_out - seg.grade_in) / (200.0 * l1) * lx * lx

    # Asymmetric (unequal-tangent) VC
    assert seg.lvc2 is not None
    l2 = seg.lvc2
    l_total = l1 + l2
    e = (l1 * l2) / (200.0 * l_total) * (seg.grade_out - seg.grade_in)
    if lx <= l1:
        return base + e * (lx / l1) * (lx / l1)           # arm 1: PVC → VPI
    lev_pvt = seg.level + (seg.grade_in / 100.0) * l1 + (seg.grade_out / 100.0) * l2
    lx2 = seg.sta_end - sta
    return lev_pvt - (seg.grade_out / 100.0) * lx2 + e * (lx2 / l2) * (lx2 / l2)


def calculate_grade_at(seg: VerticalSegment, sta: float) -> float:
    """Instantaneous grade (%) at station sta within one segment.

    Derivative of calculate_elevation_at with respect to sta.
    """
    l1 = seg.lvc
    if not l1:
        return seg.grade_in

    lx = sta - seg.sta_start
    if not _has_second_arm(seg):                # symmetric VC
        return seg.grade_in + (seg.grade_out - seg.grade_in) * (lx / l1)

    assert seg.lvc2 is not None
    l2 = seg.lvc2
    l_total = l1 + l2
    e = (l1 * l2) / (200.0 * l_total) * (seg.grade_out - seg.grade_in)
    if lx <= l1:
        return seg.grade_in + 200.0 * e * lx / (l1 * l1)        # arm 1
    lx2 = seg.sta_end - sta
    return seg.grade_out - 200.0 * e * lx2 / (l2 * l2)           # arm 2


# ---------------------------------------------------------------------------
# Public: profile-level lookup
# ---------------------------------------------------------------------------

def calculate_elevation(segs: list[VerticalSegment], sta: float) -> float | None:
    """Elevation at station sta by searching the full profile.

    Interior segments: covers [sta_start, sta_end).
    Last segment    : covers [sta_start, sta_end] (inclusive at end).
    Returns None when sta lies outside all segments.
    """
    for i, seg in enumerate(segs):
        last = (i == len(segs) - 1)
        if sta >= seg.sta_start and (sta < seg.sta_end or (last and sta <= seg.sta_end)):
            return calculate_elevation_at(seg, sta)
    return None


# ---------------------------------------------------------------------------
# Public: parse
# ---------------------------------------------------------------------------

def parse_vertical_table(rows: list[Any]) -> list[VerticalSegment]:
    """Parse a row-table (first row = headers) into a list of VerticalSegment.

    Expected columns: index, sta_start, sta_end, level, grade_in(%), grade_out(%), lvc, (lvc2).
    Rows where sta_start is empty / non-numeric are skipped.
    Matches the format used in tests/golden/tables.json ["vtable"].
    """
    segs: list[VerticalSegment] = []
    for row in rows[1:]:                         # skip header
        sta_start_raw = row[1]
        is_nan = isinstance(sta_start_raw, float) and math.isnan(sta_start_raw)
        if sta_start_raw in ('', None) or is_nan:
            continue
        try:
            sta_start = float(sta_start_raw)
        except (TypeError, ValueError):
            continue
        lvc_raw = row[6]
        lvc = float(lvc_raw) if lvc_raw not in ('', None) else 0.0
        lvc2_raw = row[7] if len(row) > 7 else None
        lvc2 = float(lvc2_raw) if lvc2_raw is not None and lvc2_raw != '' else None
        segs.append(VerticalSegment(
            sta_start=sta_start,
            sta_end=float(row[2]),
            level=float(row[3]),
            grade_in=float(row[4]),
            grade_out=float(row[5]),
            lvc=lvc,
            lvc2=lvc2,
        ))
    return segs
