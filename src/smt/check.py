"""check - Horizontal and vertical alignment cross-check engine.

Ports the crossCheck logic from AlignmentBuilder.gs and VerticalBuilder.gs
into standalone pure functions.

Horizontal: for each drawing control point {name, sta, n, e}, computes the
alignment centre-line position at that station and reports the positional gap.

Vertical: for each drawing check point {name, sta, elev}, computes the
parabolic profile elevation at that station and reports the elevation error.

Note on PVI points: a PVI (Vertical Point of Intersection) is the tangent-
intersection of two grades; it does NOT lie on the parabolic curve.  check_vertical
reports its d_elev as the mid-ordinate of the vertical curve (always non-zero for
a crest or sag).  Filter by name != 'PVI' when asserting ok=True.

Depends on: alignment, vertical.
"""
from __future__ import annotations

import math
from typing import NamedTuple

from . import alignment as al
from . import vertical as vt


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class HorizontalCheckResult(NamedTuple):
    """Cross-check result for one horizontal control point.

    d_n   : computed_n − drawing_n  (m; + = engine is north of drawing)
    d_e   : computed_e − drawing_e  (m; + = engine is east of drawing)
    gap_m : hypot(d_n, d_e)  — positional closure in metres
    ok    : True when gap_m ≤ tolerance
    """
    name: str
    sta: float
    d_n: float
    d_e: float
    gap_m: float
    ok: bool


class VerticalCheckResult(NamedTuple):
    """Cross-check result for one vertical check point.

    d_elev : computed_elev − drawing_elev  (m; + = engine is higher)
    ok     : True when |d_elev| ≤ tolerance
    """
    name: str
    sta: float
    d_elev: float
    ok: bool


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _snap_to_alignment_ends(
    sta: float,
    elements: list[al.Element],
    snap: float = 0.01,
) -> float:
    """Snap sta to the nearest alignment endpoint when within snap metres of it."""
    start = elements[0].sta_start
    end = elements[-1].sta_end
    if sta < start and (start - sta) <= snap:
        return start
    if sta > end and (sta - end) <= snap:
        return end
    return sta


def _snap_to_profile_ends(
    sta: float,
    segs: list[vt.VerticalSegment],
    snap: float = 0.01,
) -> float:
    """Snap sta to the nearest profile endpoint when within snap metres of it."""
    start = segs[0].sta_start
    end = segs[-1].sta_end
    if sta < start and (start - sta) <= snap:
        return start
    if sta > end and (sta - end) <= snap:
        return end
    return sta


# ---------------------------------------------------------------------------
# Public: check functions
# ---------------------------------------------------------------------------

def check_horizontal(
    elements: list[al.Element],
    controls: list[dict],
    tol: float = 0.05,
) -> list[HorizontalCheckResult]:
    """Cross-check drawing control points against the horizontal alignment engine.

    For each entry in controls, computes the centre-line position at the drawing
    station (stations within 0.01 m of either alignment end are snapped to that
    end) and measures the positional gap against the drawing N, E.

    controls : list of dicts — keys 'name' (str), 'sta', 'n', 'e' (float).
               Matches the 'controls' array in tests/golden/tables.json.
    tol      : pass/fail threshold on gap_m (metres; default 0.05 m).
    Returns  : one HorizontalCheckResult per input point.
    Raises   : ValueError when a station is outside the alignment by more than
               the snap tolerance (0.01 m).
    """
    results: list[HorizontalCheckResult] = []
    for cp in controls:
        name = str(cp['name'])
        sta_draw = float(cp['sta'])
        n_draw = float(cp['n'])
        e_draw = float(cp['e'])
        sta_eff = _snap_to_alignment_ends(sta_draw, elements)
        calc = al.calculate_station_to_coord(elements, sta_eff, 0.0)
        d_n = calc.n - n_draw
        d_e = calc.e - e_draw
        gap_m = math.hypot(d_n, d_e)
        results.append(HorizontalCheckResult(
            name=name, sta=sta_draw,
            d_n=d_n, d_e=d_e, gap_m=gap_m,
            ok=gap_m <= tol,
        ))
    return results


def check_vertical(
    segs: list[vt.VerticalSegment],
    vchecks: list[dict],
    tol: float = 0.005,
) -> list[VerticalCheckResult]:
    """Cross-check drawing elevation points against the vertical profile engine.

    For each entry in vchecks, computes the parabolic elevation at the drawing
    station (stations within 0.01 m of either profile end are snapped to that
    end) and reports the discrepancy against the drawing elevation.

    PVI entries are tangent-intersection points, not points on the parabolic
    curve.  Their d_elev equals the mid-ordinate of the vertical curve.
    Filter by name != 'PVI' when checking ok=True.

    vchecks : list of dicts — keys 'name' (str), 'sta', 'elev' (float).
              Matches the 'vchecks' array in tests/golden/tables.json.
    tol     : pass/fail threshold on |d_elev| (metres; default 0.005 m).
    Returns : one VerticalCheckResult per input point.
    Raises  : ValueError when a station lies outside the profile.
    """
    results: list[VerticalCheckResult] = []
    for vc in vchecks:
        name = str(vc['name'])
        sta_draw = float(vc['sta'])
        elev_draw = float(vc['elev'])
        sta_eff = _snap_to_profile_ends(sta_draw, segs)
        calc_elev = vt.calculate_elevation(segs, sta_eff)
        if calc_elev is None:
            raise ValueError(f'station {sta_draw} lies outside the vertical profile')
        d_elev = calc_elev - elev_draw
        results.append(VerticalCheckResult(
            name=name, sta=sta_draw,
            d_elev=d_elev,
            ok=abs(d_elev) <= tol,
        ))
    return results
