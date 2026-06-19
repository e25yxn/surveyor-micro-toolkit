"""alignment - Horizontal alignment engine (Domain layer).

Port from reference/Alignment.gs (validated engine, AllTests 45/45).

Model: alignment = ordered list of Element, each describing one segment.
Point-forwarding rule: exit state of element[n] == entry state of element[n+1].

Curvature: k = 1/R (signed).  k > 0 = right turn (azimuth increases); k < 0 = left.
Offset:    + = right of direction of travel;  - = left;  0 = centre line.
Angles:    radians internally; degrees only at the make_element boundary.

Transition shapes (spiral elements only):
  CLOTHOID (default) : linear curvature change        f(τ) = τ
  BLOSS              : f(τ) = 3τ²-2τ³                 (zero jerk at both ends)
  COSINE             : f(τ) = (1-cos πτ)/2            (zero jerk at both ends)
  SINE               : f(τ) = τ-sin(2πτ)/(2π)         (zero jerk at both ends)

Depends on: fpmath, wcb.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

from . import fpmath
from . import wcb

SPIRAL_STEPS: int = 48   # Simpson intervals for spiral numerical integration (must be even)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Element:
    """One horizontal alignment element (tangent, circular, or spiral/transition).

    az   : entry tangent azimuth (radians).
    k_in : curvature at entry = 1/R_in  (0 for tangent end).
    k_out: curvature at exit  = 1/R_out (0 for tangent end).
    trans: transition shape string; only affects spiral integration.
    """
    type: str
    sta_start: float
    sta_end: float
    n: float
    e: float
    az: float
    k_in: float
    k_out: float
    trans: str


class ElementState(NamedTuple):
    """Tangent state at a point on an element: position + tangent azimuth."""
    n: float
    e: float
    az: float   # tangent azimuth (radians)


class Projection(NamedTuple):
    """Foot-of-perpendicular from an external point onto one element."""
    sta: float
    offset: float   # + right, - left
    d: float        # arc distance from element start to foot
    in_range: bool  # True when foot lies within [sta_start, sta_end]


class StationOffset(NamedTuple):
    """Chainage (station) and signed perpendicular offset."""
    sta: float
    offset: float


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _shape_integral(trans: str, tau: float) -> float:
    """F(τ) = ∫₀^τ f(u) du  (curvature-shape integral for spiral elements).

    f defines how curvature changes with normalised arc position τ = s/L.
    Every shape satisfies f(0)=0, f(1)=1, ∫₀¹ f = 1/2 (equal total turning angle).
    """
    pi = math.pi
    if trans == 'BLOSS':
        return tau ** 3 - tau ** 4 / 2
    if trans == 'COSINE':
        return tau / 2 - math.sin(pi * tau) / (2 * pi)
    if trans == 'SINE':
        return tau ** 2 / 2 - (1 - math.cos(2 * pi * tau)) / (4 * pi ** 2)
    # CLOTHOID (default): f(τ) = τ  →  F(τ) = τ²/2
    return tau ** 2 / 2


def _theta_at(el: Element, s: float) -> float:
    """Accumulated turning angle at arc distance s from element start (radians).

    θ(s) = k_in · s + (k_out − k_in) · L · F(s/L)
    """
    L = el.sta_end - el.sta_start
    tau = 0.0 if L == 0 else s / L
    return el.k_in * s + (el.k_out - el.k_in) * L * _shape_integral(el.trans, tau)


# ---------------------------------------------------------------------------
# Public: radius / curvature
# ---------------------------------------------------------------------------

def curvature_from_radius(r: float | None) -> float:
    """Signed curvature k = 1/R.  Tangent (R=0/None/±inf) → k=0."""
    if not r or not math.isfinite(r):
        return 0.0
    return 1.0 / r


def radius_from_curvature(k: float) -> float:
    """Signed radius R = 1/k.  Tangent (k=0) → ±inf."""
    return math.inf if k == 0 else 1.0 / k


# ---------------------------------------------------------------------------
# Public: constructors
# ---------------------------------------------------------------------------

def make_element(
    type: str,
    sta_start: float,
    sta_end: float,
    n: float,
    e: float,
    az_deg: float,
    r_in: float | None = None,
    r_out: float | None = None,
    trans: str = 'CLOTHOID',
) -> Element:
    """Create one Element from boundary parameters.

    az_deg : entry azimuth in decimal degrees (WCB: north=0, clockwise).
    r_in   : entry radius (signed: + right, - left; 0 or None = tangent end).
    r_out  : exit  radius.  When None, type string (T/C/SPIN/SPOUT) decides
             which end is zero:  SPIN → k_in=0; SPOUT → k_out=0; T/C → both equal.
    trans  : CLOTHOID (default) / BLOSS / COSINE / SINE.
    """
    t = str(type).strip().upper()
    if r_out is None:
        k = curvature_from_radius(r_in)
        if t == 'SPIN':
            k_in, k_out = 0.0, k
        elif t == 'SPOUT':
            k_in, k_out = k, 0.0
        else:
            k_in = k_out = k
    else:
        k_in = curvature_from_radius(r_in)
        k_out = curvature_from_radius(r_out)
    tr = str(trans).strip().upper() if trans else 'CLOTHOID'
    return Element(
        type=t,
        sta_start=sta_start,
        sta_end=sta_end,
        n=n,
        e=e,
        az=fpmath.deg_to_rad(az_deg),
        k_in=k_in,
        k_out=k_out,
        trans=tr,
    )


def parse_alignment_table(rows: list) -> list[Element]:
    """Parse a row-table (first row = headers) into a list of Elements.

    Expected columns: StaStart, StaEnd, N, E, Azimuth_deg, Radius, Type, Transition.
    Matches the format used in tests/golden/tables.json ["elements"].
    """
    elements: list[Element] = []
    for row in rows[1:]:   # skip header row
        sta_start, sta_end, n, e, az_deg, radius, type_, trans = row
        elements.append(
            make_element(type_, sta_start, sta_end, n, e, az_deg, radius, None, trans or 'CLOTHOID')
        )
    return elements


# ---------------------------------------------------------------------------
# Public: element geometry
# ---------------------------------------------------------------------------

def calculate_point_on_element(el: Element, d: float) -> ElementState:
    """Position and tangent azimuth at arc distance d from element start.

    d is measured along the element's centre line.
    Returns ElementState(n, e, az) where az is the tangent direction (radians).
    """
    # Tangent: k_in == k_out == 0 → straight line
    if el.k_in == 0 and el.k_out == 0:
        pt = wcb.calculate_forward(el.n, el.e, el.az, d)
        return ElementState(n=pt.n, e=pt.e, az=el.az)

    # Circular: constant curvature → chord-and-half-angle formula
    if el.k_in == el.k_out:
        k = el.k_in
        theta = k * d                                         # signed arc angle
        chord = 2.0 / abs(k) * abs(math.sin(theta / 2))     # chord length
        chord_az = el.az + theta / 2                         # chord bisects arc angle
        pt = wcb.calculate_forward(el.n, el.e, chord_az, chord)
        return ElementState(n=pt.n, e=pt.e, az=fpmath.normalize_angle(el.az + theta))

    # Spiral: variable curvature → Simpson integration of (cos θ, sin θ)
    #   Local frame: x along entry tangent, y perpendicular (left).
    #   x(d) = ∫₀ᵈ cos θ(s) ds,  y(d) = ∫₀ᵈ sin θ(s) ds
    n_seg = SPIRAL_STEPS
    h = d / n_seg
    sum_x = sum_y = 0.0
    for i in range(n_seg + 1):
        s = i * h
        th = _theta_at(el, s)
        w = 1 if (i == 0 or i == n_seg) else (4 if i % 2 == 1 else 2)
        sum_x += w * math.cos(th)
        sum_y += w * math.sin(th)
    x = sum_x * h / 3
    y = sum_y * h / 3
    ca, sa = math.cos(el.az), math.sin(el.az)
    return ElementState(
        n=el.n + x * ca - y * sa,
        e=el.e + x * sa + y * ca,
        az=fpmath.normalize_angle(el.az + _theta_at(el, d)),
    )


def calculate_exit_state(el: Element) -> ElementState:
    """Tangent state at the far end of this element (entry of the next element)."""
    return calculate_point_on_element(el, el.sta_end - el.sta_start)


# ---------------------------------------------------------------------------
# Public: alignment-level lookup
# ---------------------------------------------------------------------------

def get_element_index(elements: list[Element], sta: float) -> int:
    """Index of the element whose [sta_start, sta_end] covers sta.  -1 if none."""
    for i, el in enumerate(elements):
        if fpmath.is_in_range(sta, el.sta_start, el.sta_end, 1e-4):
            return i
    return -1


def calculate_station_to_coord(
    elements: list[Element],
    sta: float,
    offset: float = 0.0,
) -> wcb.Point:
    """Station + perpendicular offset → grid coordinate {n, e}.

    offset: + = right of direction of travel, - = left, 0 = centre line.
    Raises ValueError when sta lies outside all elements.
    """
    i = get_element_index(elements, sta)
    if i < 0:
        raise ValueError(f'station {sta} is outside the alignment')
    st = calculate_point_on_element(elements[i], sta - elements[i].sta_start)
    if not offset:
        return wcb.Point(n=st.n, e=st.e)
    off_az = fpmath.normalize_angle(st.az + math.pi / 2.0)
    pt = wcb.calculate_forward(st.n, st.e, off_az, offset)
    return wcb.Point(n=pt.n, e=pt.e)


def calculate_projection_to_element(el: Element, pn: float, pe: float) -> Projection:
    """Project external point (pn, pe) onto one element.

    Returns Projection(sta, offset, d, in_range).
    offset: + = right, - = left (matches stationToCoord convention).
    in_range is True when the foot of perpendicular lies within the element.
    """
    L = el.sta_end - el.sta_start

    # Tangent: foot via dot-product projection
    if el.k_in == 0 and el.k_out == 0:
        dn, de = pn - el.n, pe - el.e
        ca, sa = math.cos(el.az), math.sin(el.az)
        d = dn * ca + de * sa
        off = -dn * sa + de * ca
        return Projection(
            sta=el.sta_start + d,
            offset=off,
            d=d,
            in_range=fpmath.is_in_range(d, 0, L, 1e-4),
        )

    # Circular: angle swept from centre of curvature
    if el.k_in == el.k_out:
        k = el.k_in
        R = 1.0 / k
        cn = el.n - R * math.sin(el.az)
        ce = el.e + R * math.cos(el.az)
        rho = math.hypot(pn - cn, pe - ce)
        phi0 = math.atan2(el.e - ce, el.n - cn)
        phi_p = math.atan2(pe - ce, pn - cn)
        d_arc = fpmath.angle_diff(phi_p, phi0) / k
        off = (1 if k > 0 else -1) * (abs(R) - rho)
        return Projection(
            sta=el.sta_start + d_arc,
            offset=off,
            d=d_arc,
            in_range=fpmath.is_in_range(d_arc, 0, L, 1e-4),
        )

    # Spiral: bisection on g(s) = (P - Q(s)) · tangent(s) = 0
    def g(s: float) -> float:
        q = calculate_point_on_element(el, s)
        return (pn - q.n) * math.cos(q.az) + (pe - q.e) * math.sin(q.az)

    g0, g_L = g(0.0), g(L)
    in_range = (g0 == 0.0) or (g_L == 0.0) or ((g0 > 0) != (g_L > 0))
    if in_range:
        lo, hi = 0.0, L
        g_lo = g0
        for _ in range(50):
            mid = (lo + hi) / 2.0
            gm = g(mid)
            if (g_lo > 0) == (gm > 0):
                lo = mid
                g_lo = gm
            else:
                hi = mid
        s_star = (lo + hi) / 2.0
    else:
        s_star = 0.0 if abs(g0) < abs(g_L) else L
    qs = calculate_point_on_element(el, s_star)
    off = -(pn - qs.n) * math.sin(qs.az) + (pe - qs.e) * math.cos(qs.az)
    return Projection(sta=el.sta_start + s_star, offset=off, d=s_star, in_range=in_range)


def calculate_coord_to_station(
    elements: list[Element],
    pn: float,
    pe: float,
) -> StationOffset:
    """Grid coordinate → closest centre-line station + offset.

    Iterates every element, keeps projection where foot is in-range and |offset| is minimum.
    Raises ValueError when no element can absorb the projection.
    """
    best: Projection | None = None
    for el in elements:
        pr = calculate_projection_to_element(el, pn, pe)
        if not pr.in_range:
            continue
        if best is None or abs(pr.offset) < abs(best.offset):
            best = pr
    if best is None:
        raise ValueError('point projects outside all elements')
    return StationOffset(sta=best.sta, offset=best.offset)


def check_chain(
    elements: list[Element],
    tolerance: float = 0.005,
) -> list[dict]:
    """Check tangency continuity at every element junction.

    Returns a list of dicts for junctions where position gap > tolerance (metres)
    or azimuth discontinuity > 5 arc-seconds.

    Dict keys: 'between' (e.g. '1->2'), 'gap_mm', 'az_arcsec'.
    """
    issues: list[dict] = []
    for i in range(len(elements) - 1):
        a, b = elements[i], elements[i + 1]
        ex = calculate_exit_state(a)
        gap = math.hypot(ex.n - b.n, ex.e - b.e)
        d_az = abs(fpmath.rad_to_deg(fpmath.angle_diff(ex.az, b.az)) * 3600)
        if gap > tolerance or d_az > 5:
            issues.append({
                'between': f'{i + 1}->{i + 2}',
                'gap_mm': gap * 1000,
                'az_arcsec': d_az,
            })
    return issues
