"""check - Horizontal and vertical alignment cross-check engine.

Ports the crossCheck logic from AlignmentBuilder.gs and VerticalBuilder.gs
into standalone pure functions.

Horizontal: for each drawing control point {name, sta, n, e}, computes the
alignment centre-line position at that station and reports the positional gap.

Vertical: for each drawing check point {name, sta, elev}, computes the
parabolic profile elevation at that station and reports the elevation error.

Note on PVI points: a PVI (Vertical Point of Intersection) is the tangent-
intersection of two grades; it does NOT lie on the parabolic curve.  check_vertical
reports its delta_elevation as the mid-ordinate of the vertical curve (always
non-zero for a crest or sag).  Filter by name != 'PVI' when asserting is_ok=True.

Depends on: alignment, vertical.
"""
from __future__ import annotations

import math
from typing import Any, NamedTuple

from . import alignment as al
from . import vertical as vt

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class HorizontalCheckResult(NamedTuple):
    """Cross-check result for one horizontal control point.

    delta_n    : computed_n − drawing_n  (m; + = engine is north of drawing)
    delta_e    : computed_e − drawing_e  (m; + = engine is east of drawing)
    gap_metres : hypot(delta_n, delta_e)  — positional closure in metres
    is_ok      : True when gap_metres ≤ tolerance
    """
    name: str
    sta: float
    delta_n: float
    delta_e: float
    gap_metres: float
    is_ok: bool


class VerticalCheckResult(NamedTuple):
    """Cross-check result for one vertical check point.

    delta_elevation : computed_elev − drawing_elev  (m; + = engine is higher)
    is_ok           : True when |delta_elevation| ≤ tolerance
    """
    name: str
    sta: float
    delta_elevation: float
    is_ok: bool


class FieldCrossCheckResult(NamedTuple):
    """Inverse result for one field survey point located on the alignment.

    sta    : chainage of the foot-of-perpendicular on the centre-line (m)
    offset : perpendicular offset — +right, −left (m)
    disc   : survey discrepancy carried through from input (m; sign from fieldbook)
    """
    name: str
    n: float
    e: float
    z: float
    sta: float
    offset: float
    disc: float


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
    controls: list[dict[str, Any]],
    tol: float = 0.05,
) -> list[HorizontalCheckResult]:
    """Cross-check drawing control points against the horizontal alignment engine.

    For each entry in controls, computes the centre-line position at the drawing
    station (stations within 0.01 m of either alignment end are snapped to that
    end) and measures the positional gap against the drawing N, E.

    controls : list of dicts — keys 'name' (str), 'sta', 'n', 'e' (float).
               Matches the 'controls' array in tests/golden/tables.json.
    tol      : pass/fail threshold on gap_metres (metres; default 0.05 m).
    Returns  : one HorizontalCheckResult per input point.
    Raises   : ValueError when a station is outside the alignment by more than
               the snap tolerance (0.01 m).
    """
    results: list[HorizontalCheckResult] = []
    for control_point in controls:
        name = str(control_point['name'])
        sta_draw = float(control_point['sta'])
        n_draw = float(control_point['n'])
        e_draw = float(control_point['e'])
        sta_eff = _snap_to_alignment_ends(sta_draw, elements)
        calc = al.calculate_station_to_coordinate(elements, sta_eff, 0.0)
        delta_n = calc.n - n_draw
        delta_e = calc.e - e_draw
        gap_metres = math.hypot(delta_n, delta_e)
        results.append(HorizontalCheckResult(
            name=name, sta=sta_draw,
            delta_n=delta_n, delta_e=delta_e, gap_metres=gap_metres,
            is_ok=gap_metres <= tol,
        ))
    return results


def bulk_cross_check(
    elements: list[al.Element],
    field_points: list[dict[str, Any]],
) -> list[FieldCrossCheckResult]:
    """Locate field survey points on the horizontal alignment.

    Runs an inverse calculation (N, E → sta, offset) for each point and
    returns the result enriched with alignment position.  The disc value
    (survey closure discrepancy) is carried through unchanged.

    field_points : list of dicts — keys 'name' (str), 'n', 'e', 'z', 'disc' (float).
                   'disc' defaults to 0.0 when absent.
    Returns      : one FieldCrossCheckResult per input point, in input order.
    Raises       : ValueError when a point cannot be projected onto the alignment
                   (propagated from calculate_coordinate_to_station).
    """
    results: list[FieldCrossCheckResult] = []
    for fp in field_points:
        name = str(fp['name'])
        n    = float(fp['n'])
        e    = float(fp['e'])
        z    = float(fp['z'])
        disc = float(fp.get('disc', 0.0))
        so   = al.calculate_coordinate_to_station(elements, n, e)
        results.append(FieldCrossCheckResult(
            name=name, n=n, e=e, z=z,
            sta=so.sta, offset=so.offset, disc=disc,
        ))
    return results


def check_vertical(
    segs: list[vt.VerticalSegment],
    vchecks: list[dict[str, Any]],
    tol: float = 0.005,
) -> list[VerticalCheckResult]:
    """Cross-check drawing elevation points against the vertical profile engine.

    For each entry in vchecks, computes the parabolic elevation at the drawing
    station (stations within 0.01 m of either profile end are snapped to that
    end) and reports the discrepancy against the drawing elevation.

    PVI entries are tangent-intersection points, not points on the parabolic
    curve.  Their delta_elevation equals the mid-ordinate of the vertical curve.
    Filter by name != 'PVI' when checking is_ok=True.

    vchecks : list of dicts — keys 'name' (str), 'sta', 'elev' (float).
              Matches the 'vchecks' array in tests/golden/tables.json.
    tol     : pass/fail threshold on |delta_elevation| (metres; default 0.005 m).
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
        delta_elevation = calc_elev - elev_draw
        results.append(VerticalCheckResult(
            name=name, sta=sta_draw,
            delta_elevation=delta_elevation,
            is_ok=abs(delta_elevation) <= tol,
        ))
    return results
