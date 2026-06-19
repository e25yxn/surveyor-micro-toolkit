"""vertical - Vertical alignment (profile) engine (Domain layer).

Port from reference/Vertical.gs (validated engine, AllTests 45/45).

Model: profile = ordered list of VerticalSegment, each covering [sta_start, sta_end].

Grade units : percent (%).  Elevation units: same as input (metres).
LVC conventions
  lvc = 0, lvc2 = None : tangent grade (no vertical curve)
  lvc > 0, lvc2 = None : symmetric parabolic VC  (total length = lvc)
  lvc > 0, lvc2 > 0    : asymmetric (unequal-tangent) VC — arms lvc (L1) and lvc2 (L2)

Segment table column order (matches tables.json "vtable"):
  [index] | sta_start | sta_end | level | g1 | g2 | lvc | (lvc2)

Standalone module (no dependency on fpmath, wcb, or alignment).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data type
# ---------------------------------------------------------------------------

@dataclass
class VerticalSegment:
    """One vertical alignment segment.

    level : elevation at sta_start (PVC level).
    g1    : entry grade (%).
    g2    : exit grade  (%).
    lvc   : vertical curve length (0 = tangent grade; >0 = VC length).
            For asymmetric VC this is the first arm L1.
    lvc2  : second arm L2 for asymmetric VC; None for symmetric or tangent.
    """
    sta_start: float
    sta_end: float
    level: float
    g1: float
    g2: float
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

    Lx = sta - seg.sta_start (arc distance from segment start).
    Returns the parabolic (or tangent) elevation at sta.

    For symmetric VC: level = base + (g2-g1)/(200*L) * Lx²
    For asymmetric VC (two arms L1, L2):
      arm 1 (Lx ≤ L1): level = base + e*(Lx/L1)²
      arm 2 (Lx > L1): level = levPVT - (g2/100)*Lx2 + e*(Lx2/L2)²
      where e = L1*L2/(200*(L1+L2)) * (g2-g1)  [middle ordinate at VPI, signed]
    """
    Lx = sta - seg.sta_start
    base = seg.level + (seg.g1 / 100.0) * Lx   # tangent grade from PVC

    L1 = seg.lvc
    if not L1:
        return base                              # tangent grade segment

    if not _has_second_arm(seg):                # symmetric VC
        return base + (seg.g2 - seg.g1) / (200.0 * L1) * Lx * Lx

    # Asymmetric (unequal-tangent) VC
    L2 = seg.lvc2
    Ltot = L1 + L2
    e = (L1 * L2) / (200.0 * Ltot) * (seg.g2 - seg.g1)   # VPI middle ordinate (signed)
    if Lx <= L1:
        return base + e * (Lx / L1) * (Lx / L1)           # arm 1: PVC → VPI
    lev_pvt = seg.level + (seg.g1 / 100.0) * L1 + (seg.g2 / 100.0) * L2
    Lx2 = seg.sta_end - sta
    return lev_pvt - (seg.g2 / 100.0) * Lx2 + e * (Lx2 / L2) * (Lx2 / L2)   # arm 2: VPI → PVT


def calculate_grade_at(seg: VerticalSegment, sta: float) -> float:
    """Instantaneous grade (%) at station sta within one segment.

    Derivative of calculate_elevation_at with respect to sta.
    """
    L1 = seg.lvc
    if not L1:
        return seg.g1

    Lx = sta - seg.sta_start
    if not _has_second_arm(seg):                # symmetric VC
        return seg.g1 + (seg.g2 - seg.g1) * (Lx / L1)

    L2 = seg.lvc2
    Ltot = L1 + L2
    e = (L1 * L2) / (200.0 * Ltot) * (seg.g2 - seg.g1)
    if Lx <= L1:
        return seg.g1 + 200.0 * e * Lx / (L1 * L1)        # arm 1
    Lx2 = seg.sta_end - sta
    return seg.g2 - 200.0 * e * Lx2 / (L2 * L2)           # arm 2


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

def parse_vertical_table(rows: list) -> list[VerticalSegment]:
    """Parse a row-table (first row = headers) into a list of VerticalSegment.

    Expected columns: index, sta_start, sta_end, level, g1(%), g2(%), lvc, (lvc2).
    Rows where sta_start is empty / non-numeric are skipped.
    Matches the format used in tests/golden/tables.json ["vtable"].
    """
    segs: list[VerticalSegment] = []
    for row in rows[1:]:                         # skip header
        sta_start_raw = row[1]
        if sta_start_raw in ('', None) or (isinstance(sta_start_raw, float) and math.isnan(sta_start_raw)):
            continue
        try:
            sta_start = float(sta_start_raw)
        except (TypeError, ValueError):
            continue
        lvc_raw = row[6]
        lvc = float(lvc_raw) if lvc_raw not in ('', None) else 0.0
        lvc2_raw = row[7] if len(row) > 7 else None
        lvc2 = float(lvc2_raw) if lvc2_raw not in ('', None) else None
        segs.append(VerticalSegment(
            sta_start=sta_start,
            sta_end=float(row[2]),
            level=float(row[3]),
            g1=float(row[4]),
            g2=float(row[5]),
            lvc=lvc,
            lvc2=lvc2,
        ))
    return segs
