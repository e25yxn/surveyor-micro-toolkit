"""surface - 3-D road surface point engine (Domain layer).

Port from reference/Surface3D.gs (validated engine, AllTests 45/45).

Combines horizontal alignment, vertical profile, and crossfall to produce
the full 3-D position and surface elevation of any point on the road.

Formula
    surface_level = centerline_level + |offset| * crossfall_pct / 100

Crossfall sign convention (same as crossfall.py)
    negative (−) = edge lower than centreline  (normal crown, outer lane during cant)
    positive (+) = edge higher than centreline (inner lane during superelevation)

Offset sign convention (same as alignment.py)
    offset < 0 : left  of direction of travel → uses xlt_segs (primary)
    offset > 0 : right of direction of travel → uses xrt_segs (primary)
    offset = 0 : centre line → level = centerline_level, crossfall = None

One-sided fallback: if the primary crossfall table is empty the other table is
used for both sides (matches JS oracle behaviour).

Depends on: alignment, vertical, crossfall.
"""
from __future__ import annotations

from typing import NamedTuple

from . import alignment
from . import crossfall as cf
from . import vertical


class Point3D(NamedTuple):
    """Full 3-D position of a road surface point.

    level           : surface elevation at (sta, offset).  None when data is unavailable.
    centerline_level: elevation at the centre line.        None when outside the profile.
    crossfall       : crossfall (%) applied to reach offset.  None at centre line or when
                      the crossfall table does not cover the station.
    """
    n: float
    e: float
    level: float | None
    centerline_level: float | None
    crossfall: float | None


def calculate_surface_level(
    centerline_level: float,
    crossfall_pct: float,
    offset: float,
) -> float:
    """Surface elevation at a perpendicular offset from the centre line.

    surface_level = centerline_level + |offset| * crossfall_pct / 100

    crossfall_pct: signed percentage (− = lower edge, + = higher edge than CL).
    offset       : signed metres — only |offset| is used for the distance.
    """
    return centerline_level + abs(offset) * crossfall_pct / 100.0


def calculate_point_3d(
    elements: list[alignment.Element],
    v_segs: list[vertical.VerticalSegment],
    xlt_segs: list[cf.CrossfallSegment],
    xrt_segs: list[cf.CrossfallSegment],
    sta: float,
    offset: float = 0.0,
) -> Point3D:
    """Full 3-D road surface point at (sta, offset).

    elements : horizontal alignment element list.
    v_segs   : vertical profile segment list.
    xlt_segs : left-side crossfall segments  (primary when offset < 0).
    xrt_segs : right-side crossfall segments (primary when offset > 0).
    sta      : chainage (station).
    offset   : perpendicular offset from centre line (+ right, − left, 0 = CL).

    Returns Point3D(n, e, level, centerline_level, crossfall).
    level is None when the vertical profile or crossfall table has no data for sta.
    Raises ValueError when sta lies outside the alignment (propagated from alignment).
    """
    offset = float(offset)
    plan_point = alignment.calculate_station_to_coordinate(elements, sta, offset)
    centerline_elevation = vertical.calculate_elevation(v_segs, sta)

    crossfall_value: float | None = None
    surface_elevation: float | None

    if centerline_elevation is None:
        surface_elevation = None
    elif offset == 0.0:
        surface_elevation = centerline_elevation
    else:
        primary = xlt_segs if offset < 0 else xrt_segs
        fallback = xrt_segs if offset < 0 else xlt_segs
        x_segs = primary if primary else (fallback if fallback else None)
        crossfall_value = cf.calculate_crossfall(x_segs, sta) if x_segs is not None else None
        surface_elevation = calculate_surface_level(centerline_elevation, crossfall_value, offset) if crossfall_value is not None else None

    return Point3D(n=plan_point.n, e=plan_point.e, level=surface_elevation, centerline_level=centerline_elevation, crossfall=crossfall_value)
