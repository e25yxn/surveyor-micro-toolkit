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
  SINE               : f(τ) = τ-sin(2πτ)/(2π)         (zero jerk at both ends)
  COSINE             : Civil 3D "Sine Half-Wavelength Diminishing Tangent Curve" —
                       NOT a curvature-vs-arc-length shape like the three above.
                       Closed form in tangent-projected distance x (approximated here
                       by arc distance s, since x is not independently invertible from
                       s in closed form): with X = L - 0.0226689447*L**3/R**2 and
                       a = x/X,
                         y(x)     = X**2/R * (a**2/4 - (1-cos(pi*a))/(2*pi**2))
                         theta(x) = atan(X/R * (a/2 - sin(pi*a)/(2*pi)))
                       SPIN (k_in=0) uses this directly with x=d. SPOUT (k_out=0)
                       mirrors it via s<->L-s (see `_sine_halfwave_point` and the
                       SPOUT branch in `calculate_point_on_element`), matching the
                       Civil 3D-confirmed invariant that SPIN and SPOUT of equal R,L
                       share the same total turning angle. Verified against 2
                       independent Civil 3D ground-truth points (R=900/L=100,
                       R=250/L=50) — see session_logs/investigate_sinehalfwave_formula.md.
                       Known limitations (documented there, not fixed here):
                       (1) x≈s is an approximation; at the element's own true end
                       (d=L, the point calculate_exit_state actually uses) this costs
                       1.5548mm at R=900/L=100 and 4.5338mm at R=250/L=50 (measured:
                       the gap between evaluating at d=X, where a=1 exactly and the
                       formula matches Civil 3D to machine precision, vs d=L, where
                       L-X is 0.027986m and 0.045338m respectively) — no interior
                       point (d<L) is independently verified at all;
                       (2) the SPOUT mid-curve trace is derived from the boundary
                       mirror only — no independent Civil 3D data confirms a SPOUT
                       interior point, only the shared endpoint invariant;
                       (3) the LandXML export's totalX field (src/smt/landxml.py
                       _spiral_geometry) reports L directly, not the true closed-form
                       X — a natural consequence of the same x≈s approximation above,
                       not a separate bug (see session_logs/
                       investigate_sinehalfwave_formula.md).

Depends on: fpmath, wcb.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, NamedTuple

from . import fpmath, wcb

SPIRAL_STEPS: int = 48   # Simpson intervals for spiral numerical integration (must be even)
_SINE_HALFWAVE_C: float = 0.0226689447   # Civil 3D closed-form tangent-length correction constant


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Element:
    """One horizontal alignment element (tangent, circular, or spiral/transition).

    azimuth   : entry tangent azimuth (radians).
    k_in      : curvature at entry = 1/R_in  (0 for tangent end).
    k_out     : curvature at exit  = 1/R_out (0 for tangent end).
    transition: transition shape string; only affects spiral integration.
    """
    type: str
    sta_start: float
    sta_end: float
    n: float
    e: float
    azimuth: float
    k_in: float
    k_out: float
    transition: str


class ElementState(NamedTuple):
    """Tangent state at a point on an element: position + tangent azimuth."""
    n: float
    e: float
    azimuth: float   # tangent azimuth (radians)


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

def _shape_integral(transition: str, tau: float) -> float:
    """F(τ) = ∫₀^τ f(u) du  (curvature-shape integral for spiral elements).

    f defines how curvature changes with normalised arc position τ = s/L.
    Every shape satisfies f(0)=0, f(1)=1, ∫₀¹ f = 1/2 (equal total turning angle).
    """
    pi = math.pi
    if transition == 'BLOSS':
        return tau ** 3 - tau ** 4 / 2
    if transition == 'COSINE':
        return tau / 2 - math.sin(pi * tau) / (2 * pi)
    if transition == 'SINE':
        return tau ** 2 / 2 - (1 - math.cos(2 * pi * tau)) / (4 * pi ** 2)
    # CLOTHOID (default): f(τ) = τ  →  F(τ) = τ²/2
    return tau ** 2 / 2


def _sine_halfwave_point(x: float, big_x: float, r: float) -> tuple[float, float, float]:
    """Civil 3D Sine Half-Wavelength Diminishing Tangent Curve, canonical (SPIN) form.

    x     : tangent-projected distance from the zero-curvature end (approximated by
            arc distance here — see module docstring "Known limitations").
    big_x : X, the closed-form tangent-projected length at the curve's own full L
            (X = L - 0.0226689447*L**3/R**2), constant for one element.
    r     : signed radius at the curved end (+ right, - left).
    Returns (x, y, theta): local offset y (+ left of entry tangent) and tangent
    angle theta (radians) at x, both measured from the zero-curvature end.
    Reference: Autodesk Civil 3D 2026 Help, "About Transition Definitions" — see
    session_logs/investigate_sinehalfwave_formula.md for the verified derivation.
    """
    a = x / big_x
    y = big_x ** 2 / r * (a ** 2 / 4 - (1 - math.cos(math.pi * a)) / (2 * math.pi ** 2))
    theta = math.atan(big_x / r * (a / 2 - math.sin(math.pi * a) / (2 * math.pi)))
    return x, y, theta


def _calculate_turning_angle_at(el: Element, s: float) -> float:
    """Accumulated turning angle at arc distance s from element start (radians).

    θ(s) = k_in · s + (k_out − k_in) · L · F(s/L)
    """
    L = el.sta_end - el.sta_start
    tau = 0.0 if L == 0 else s / L
    return el.k_in * s + (el.k_out - el.k_in) * L * _shape_integral(el.transition, tau)


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
    trans: str | None = 'CLOTHOID',
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
        azimuth=fpmath.deg_to_rad(az_deg),
        k_in=k_in,
        k_out=k_out,
        transition=tr,
    )


def parse_alignment_table(rows: list[Any]) -> list[Element]:
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
    Returns ElementState(n, e, azimuth) where azimuth is the tangent direction (radians).
    """
    # Tangent: k_in == k_out == 0 → straight line
    if el.k_in == 0 and el.k_out == 0:
        pt = wcb.calculate_forward(el.n, el.e, el.azimuth, d)
        return ElementState(n=pt.n, e=pt.e, azimuth=el.azimuth)

    # Circular: constant curvature → chord-and-half-angle formula
    if el.k_in == el.k_out:
        k = el.k_in
        theta = k * d                                         # signed arc angle
        chord = 2.0 / abs(k) * abs(math.sin(theta / 2))     # chord length
        chord_azimuth = el.azimuth + theta / 2               # chord bisects arc angle
        pt = wcb.calculate_forward(el.n, el.e, chord_azimuth, chord)
        return ElementState(n=pt.n, e=pt.e, azimuth=fpmath.normalize_angle(el.azimuth + theta))

    # COSINE spiral (pure SPIN or SPOUT only — exactly one of k_in/k_out is zero):
    # Civil 3D Sine Half-Wavelength closed form, not the Simpson integration below.
    # See module docstring "Transition shapes" and _sine_halfwave_point.
    if el.transition == 'COSINE' and (el.k_in == 0) != (el.k_out == 0):
        length = el.sta_end - el.sta_start
        if el.k_in == 0:   # SPIN: curvature 0 -> 1/R, canonical form used directly
            r = radius_from_curvature(el.k_out)
            big_x = length - _SINE_HALFWAVE_C * length ** 3 / r ** 2
            x_local, y_local, theta_local = _sine_halfwave_point(d, big_x, r)
        else:   # SPOUT: curvature 1/R -> 0, mirror canonical form via s <-> L-d
            r = radius_from_curvature(el.k_in)
            big_x = length - _SINE_HALFWAVE_C * length ** 3 / r ** 2
            x_end, y_end, theta_total = _sine_halfwave_point(length, big_x, r)
            x_g, y_g, theta_g = _sine_halfwave_point(length - d, big_x, r)
            dx, dy = x_end - x_g, y_end - y_g
            x_local = dx * math.cos(theta_total) + dy * math.sin(theta_total)
            y_local = dx * math.sin(theta_total) - dy * math.cos(theta_total)
            theta_local = theta_total - theta_g
        ca, sa = math.cos(el.azimuth), math.sin(el.azimuth)
        return ElementState(
            n=el.n + x_local * ca - y_local * sa,
            e=el.e + x_local * sa + y_local * ca,
            azimuth=fpmath.normalize_angle(el.azimuth + theta_local),
        )

    # Spiral: variable curvature → Simpson integration of (cos θ, sin θ)
    #   Local frame: x along entry tangent, y perpendicular (left).
    #   x(d) = ∫₀ᵈ cos θ(s) ds,  y(d) = ∫₀ᵈ sin θ(s) ds
    n_seg = SPIRAL_STEPS
    h = d / n_seg
    sum_x = sum_y = 0.0
    for i in range(n_seg + 1):
        s = i * h
        th = _calculate_turning_angle_at(el, s)
        w = 1 if (i == 0 or i == n_seg) else (4 if i % 2 == 1 else 2)
        sum_x += w * math.cos(th)
        sum_y += w * math.sin(th)
    x = sum_x * h / 3
    y = sum_y * h / 3
    ca, sa = math.cos(el.azimuth), math.sin(el.azimuth)
    return ElementState(
        n=el.n + x * ca - y * sa,
        e=el.e + x * sa + y * ca,
        azimuth=fpmath.normalize_angle(el.azimuth + _calculate_turning_angle_at(el, d)),
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


def calculate_station_to_coordinate(
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
    off_az = fpmath.normalize_angle(st.azimuth + math.pi / 2.0)
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
        ca, sa = math.cos(el.azimuth), math.sin(el.azimuth)
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
        center_n = el.n - R * math.sin(el.azimuth)
        center_e = el.e + R * math.cos(el.azimuth)
        rho = math.hypot(pn - center_n, pe - center_e)
        phi0 = math.atan2(el.e - center_e, el.n - center_n)
        phi_p = math.atan2(pe - center_e, pn - center_n)
        d_arc = fpmath.calculate_angle_diff(phi_p, phi0) / k
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
        return (pn - q.n) * math.cos(q.azimuth) + (pe - q.e) * math.sin(q.azimuth)

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
    off = -(pn - qs.n) * math.sin(qs.azimuth) + (pe - qs.e) * math.cos(qs.azimuth)
    return Projection(sta=el.sta_start + s_star, offset=off, d=s_star, in_range=in_range)


def calculate_coordinate_to_station(
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
) -> list[dict[str, Any]]:
    """Check tangency continuity at every element junction.

    Returns a list of dicts for junctions where position gap > tolerance (metres)
    or azimuth discontinuity > 5 arc-seconds.

    Dict keys: 'between' (e.g. '1->2'), 'gap_mm', 'az_arcsec'.
    """
    issues: list[dict[str, Any]] = []
    for i in range(len(elements) - 1):
        a, b = elements[i], elements[i + 1]
        ex = calculate_exit_state(a)
        gap = math.hypot(ex.n - b.n, ex.e - b.e)
        d_az = abs(fpmath.rad_to_deg(fpmath.calculate_angle_diff(ex.azimuth, b.azimuth)) * 3600)
        if gap > tolerance or d_az > 5:
            issues.append({
                'between': f'{i + 1}->{i + 2}',
                'gap_mm': gap * 1000,
                'az_arcsec': d_az,
            })
    return issues
