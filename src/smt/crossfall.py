"""crossfall - Cross-fall / superelevation engine (Domain layer).

Port from reference/CrossFall.gs (validated engine, AllTests 45/45).

Model: crossfall profile = ordered list of CrossfallSegment, each covering
[sta_start, sta_end] with a start value x_start (%) and end value x_end (%).

Transition types:
  'N' (Normal/constant) : crossfall = x_start throughout
  'V' (Variable/linear) : linear interpolation  f(t) = t
  'S' (S-curve/smooth)  : Bloss smoothstep      f(t) = 3t²-2t³  (zero rate at both ends)
  Any other value       : treated as 'V' (matches JS oracle behaviour)

t = (sta - sta_start) / (sta_end - sta_start) = normalised position in segment.
When x_start == x_end the value is constant regardless of type.

Standalone module (no dependency on fpmath, wcb, alignment, or vertical).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data type
# ---------------------------------------------------------------------------

@dataclass
class CrossfallSegment:
    """One crossfall / superelevation segment.

    x_start, x_end : crossfall percentages at the start and end stations.
    type            : transition shape — 'N', 'V', or 'S' (default 'V').
    """
    sta_start: float
    sta_end: float
    x_start: float
    x_end: float
    type: str = field(default='V')


# ---------------------------------------------------------------------------
# Private helper: normalise type string (mirrors JS `String(seg.type||'V').trim().toUpperCase()`)
# ---------------------------------------------------------------------------

def _norm_type(raw: str | None) -> str:
    return str(raw or 'V').strip().upper()


# ---------------------------------------------------------------------------
# Public: single-segment calculations
# ---------------------------------------------------------------------------

def calculate_crossfall_at(seg: CrossfallSegment, sta: float) -> float:
    """Cross-fall (%) at station sta within one segment.

    Uses the segment's transition type to interpolate between x_start and x_end.
    Returns x_start immediately when type is 'N' or x_start == x_end.
    """
    x1, x2 = seg.x_start, seg.x_end
    t_type = _norm_type(seg.type)
    if t_type == 'N' or x1 == x2:
        return x1
    L = seg.sta_end - seg.sta_start
    if L == 0:
        return x1
    t = (sta - seg.sta_start) / L
    f = t * t * (3.0 - 2.0 * t) if t_type == 'S' else t   # S-curve or linear (V)
    return x1 + (x2 - x1) * f


def calculate_crossfall_rate_at(seg: CrossfallSegment, sta: float) -> float:
    """Rate of crossfall change (%/m) at station sta within one segment.

    Derivative of calculate_crossfall_at with respect to sta.
    Returns 0 for constant segments (type N, or x_start == x_end, or L == 0).
    """
    t_type = _norm_type(seg.type)
    L = seg.sta_end - seg.sta_start
    if t_type == 'N' or seg.x_start == seg.x_end or L == 0:
        return 0.0
    t = (sta - seg.sta_start) / L
    dx = seg.x_end - seg.x_start
    dfdt = 6.0 * t * (1.0 - t) if t_type == 'S' else 1.0   # d/dt of shape function
    return dx * dfdt / L


# ---------------------------------------------------------------------------
# Public: profile-level lookup
# ---------------------------------------------------------------------------

def calculate_crossfall(segs: list[CrossfallSegment], sta: float) -> float | None:
    """Cross-fall (%) at station sta by searching the full crossfall profile.

    Interior segments: covers [sta_start, sta_end).
    Last segment    : covers [sta_start, sta_end] (inclusive at end).
    Returns None when sta lies outside all segments.
    """
    for i, seg in enumerate(segs):
        last = (i == len(segs) - 1)
        if sta >= seg.sta_start and (sta < seg.sta_end or (last and sta <= seg.sta_end)):
            return calculate_crossfall_at(seg, sta)
    return None


# ---------------------------------------------------------------------------
# Public: parse
# ---------------------------------------------------------------------------

def parse_crossfall_table(rows: list) -> list[CrossfallSegment]:
    """Parse a row-table (first row = headers) into a list of CrossfallSegment.

    Expected columns: index, sta_start, sta_end, x_start(%), x_end(%), type.
    Rows where sta_start is empty / non-numeric are skipped.
    Matches the format used in tests/golden/tables.json ["xLT"] and ["xRT"].
    """
    segs: list[CrossfallSegment] = []
    for row in rows[1:]:                  # skip header
        sta_start_raw = row[1]
        if sta_start_raw in ('', None):
            continue
        try:
            sta_start = float(sta_start_raw)
        except (TypeError, ValueError):
            continue
        if math.isnan(sta_start):
            continue
        type_raw = row[5] if len(row) > 5 else None
        segs.append(CrossfallSegment(
            sta_start=sta_start,
            sta_end=float(row[2]),
            x_start=float(row[3]),
            x_end=float(row[4]),
            type=_norm_type(type_raw),
        ))
    return segs
