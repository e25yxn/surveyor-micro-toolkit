# BUNDLE_python_core.md — Python core engine (concatenated)

Generated from the working tree on 2026-07-27. Order: fpmath -> wcb -> alignment
-> check -> builders/table_splitter -> builders/alignment_builder, matching the
module dependency order in CLAUDE.md. The `cli.py` entry at the end is a partial
excerpt (lines 109-168 only: `_radius_from_element` + `_run_build`), not the
full file.

---

## FILE: src/smt/fpmath.py
```python
"""fpmath - FP-safe math utilities (Foundation layer / ชั้นล่างสุด).

พอร์ตจาก reference/FPMath.gs (engine ที่ผ่าน AllTests 45/45)

ปรัชญา (SAFE + SMALL + STABLE):
    1) คำนวณด้วย full IEEE 754 (float) เสมอ -- ห้ามปัดเศษกลางทาง
    2) ปัดเศษเฉพาะตอนส่งออก/แสดงผล
    3) ทุกฟังก์ชันเป็น pure function

หน่วยมาตรฐานภายใน engine:
    - มุม (angle) : radian
    - เก็บ/แสดงมุม: packed DMS เช่น 120.012256 = 120 deg 01' 22.56"

การตั้งชื่อ: ดู docs/naming_convention.md
"""
from __future__ import annotations

import math
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

EPS: float = 1e-9                 # tolerance เริ่มต้นสำหรับเทียบ float
TWO_PI: float = 2.0 * math.pi
DEG_TO_RAD: float = math.pi / 180.0
RAD_TO_DEG: float = 180.0 / math.pi


# --------------------------------------------------------------------------
# ROUNDING -- ใช้ตอนส่งออกเท่านั้น
# --------------------------------------------------------------------------
def round_to(value: float, decimals: int = 3) -> float:
    """ปัดเศษแบบ round-half-away-from-zero (2.5 -> 3, -2.5 -> -3).

    ใช้ Decimal(repr(value)) เพื่อเลี่ยงบั๊ก 1.005 -> 1.00 (เทียบเท่าเทคนิค
    exponential-string ในต้นฉบับ JS).
    """
    if not math.isfinite(value):
        return value
    quantum = Decimal(1).scaleb(-decimals)
    return float(Decimal(repr(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def trunc_to(value: float, decimals: int = 3) -> float:
    """ตัดทศนิยมทิ้ง (ไม่ปัด) -- ใช้กับการแสดง STATION."""
    if not math.isfinite(value):
        return value
    quantum = Decimal(1).scaleb(-decimals)
    return float(Decimal(repr(value)).quantize(quantum, rounding=ROUND_DOWN))


# --------------------------------------------------------------------------
# COMPARISON -- เทียบ float อย่างปลอดภัย
# --------------------------------------------------------------------------
def is_almost_equal(a: float, b: float, eps: float = EPS) -> bool:
    """a ~ b หรือไม่ (ผสม absolute + relative tolerance)."""
    diff = abs(a - b)
    if diff <= eps:
        return True
    return diff <= eps * max(abs(a), abs(b))


def is_in_range(value: float, lo: float, hi: float, eps: float = EPS) -> bool:
    """value อยู่ในช่วง [lo, hi] ไหม (เผื่อ tolerance ที่ขอบ)."""
    return (value >= (lo - eps)) and (value <= (hi + eps))


# --------------------------------------------------------------------------
# MODULAR / ANGLE
# --------------------------------------------------------------------------
def floor_mod(a: float, n: float) -> float:
    """modulo ที่ผลลัพธ์เป็นบวกเสมอ: floor_mod(-1, 4) = 3."""
    return ((a % n) + n) % n


def normalize_angle(rad: float) -> float:
    """บีบมุม (radian) ให้อยู่ในช่วง [0, 2*pi)."""
    return floor_mod(rad, TWO_PI)


def calculate_angle_diff(a: float, b: float) -> float:
    """ผลต่างมุมที่สั้นที่สุด (a - b) ในช่วง (-pi, pi]."""
    return floor_mod(a - b + math.pi, TWO_PI) - math.pi


# --------------------------------------------------------------------------
# SAFE ARITHMETIC -- ลดการสะสมความคลาด (Error Propagation)
# --------------------------------------------------------------------------
def kahan_sum(values: list[float]) -> float:
    """Kahan summation -- บวกเลขชุดยาวโดยชดเชย round-off."""
    total = 0.0
    comp = 0.0
    for v in values:
        y = v - comp
        t = total + y
        comp = (t - total) - y
        total = t
    return total


# --------------------------------------------------------------------------
# CONVERSION -- แปลงหน่วยมุม (idiom <source>_to_<target>)
# --------------------------------------------------------------------------
def deg_to_rad(deg: float) -> float:
    """degrees -> radians. Unit: deg in, rad out."""
    return deg * DEG_TO_RAD


def rad_to_deg(rad: float) -> float:
    """radians -> degrees. Unit: rad in, deg out."""
    return rad * RAD_TO_DEG


def packed_dms_to_rad(packed: float, sec_decimals: int = 4) -> float:
    """packed DMS (D.MMSSsss) -> radian. เช่น 120.012256 -> rad ของ 120 01' 22.56".

    Sign: negative input -> negative output (handles bearings south of equator or west longitudes).
    """
    sign = -1.0 if packed < 0 else 1.0
    a = abs(packed)
    d = math.trunc(a)
    minutes_with_seconds = round_to((a - d) * 100.0, sec_decimals + 2)   # .MMSSsss -> MM.SSsss
    m = math.trunc(minutes_with_seconds)
    s = round_to((minutes_with_seconds - m) * 100.0, sec_decimals)        # .SSsss -> SS.sss
    decimal_deg = d + m / 60.0 + s / 3600.0
    return sign * decimal_deg * DEG_TO_RAD


def rad_to_packed_dms(rad: float, sec_decimals: int = 2) -> float:
    """radian -> packed DMS (D.MMSSsss). ปัดวินาทีแล้วทดเมื่อถึง 60.

    Sign: negative input -> negative output (handles bearings south of equator or west longitudes).
    """
    deg = rad * RAD_TO_DEG
    sign = -1.0 if deg < 0 else 1.0
    deg = abs(deg)
    d = math.trunc(deg)
    m_full = (deg - d) * 60.0
    m = math.trunc(m_full)
    s = round_to((m_full - m) * 60.0, sec_decimals)
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    packed = d + m / 100.0 + s / 10000.0
    return sign * round_to(packed, sec_decimals + 4)


def rad_to_dms_string(rad: float, sec_decimals: int = 2) -> str:
    """radian -> ข้อความ DMS เช่น \"120°01′22.56″\".

    Sign: negative input -> string prefixed with '-' (e.g. \"-45°00′00.00″\").
    """
    deg = rad * RAD_TO_DEG
    sign = "-" if deg < 0 else ""
    deg = abs(deg)
    d = math.trunc(deg)
    m_full = (deg - d) * 60.0
    m = math.trunc(m_full)
    s = round_to((m_full - m) * 60.0, sec_decimals)
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    ss = f"{s:.{sec_decimals}f}"
    if s < 10:
        ss = "0" + ss
    mm = f"{m:02d}"
    return f"{sign}{d}°{mm}′{ss}″"


def dms_to_rad(d: float, m: float = 0.0, s: float = 0.0) -> float:
    """องค์ประกอบ D, M, S -> radian.

    Sign: negative d -> negative output (handles bearings south of equator or west longitudes).
    """
    sign = -1.0 if d < 0 else 1.0
    decimal_deg = abs(d) + m / 60.0 + s / 3600.0
    return sign * decimal_deg * DEG_TO_RAD
```

---

## FILE: src/smt/wcb.py
```python
"""wcb - Azimuth / Coordinate Geometry (Foundation layer).

พอร์ตจาก reference/WCB.gs

Azimuth (WCB = Whole Circle Bearing): เริ่ม 0 ที่ทิศเหนือ วนขวาตามเข็มนาฬิกา
    เหนือ=0, ตะวันออก=90, ใต้=180, ตะวันตก=270 (องศา)

เทียบ Casio fx-5800p:
    calculate_inverse ~ Pol(dN, dE)   (สองจุด -> มุม + ระยะ)
    calculate_forward ~ Rec(d, az)    (มุม + ระยะ -> พิกัด)

หน่วยมุมภายใน = radian
การตั้งชื่อ: ดู docs/naming_convention.md
"""
from __future__ import annotations

import math
from typing import NamedTuple

from . import fpmath


class Point(NamedTuple):
    """พิกัดราบ (Northing, Easting)."""
    n: float
    e: float


class Inverse(NamedTuple):
    """ผลการคำนวณย้อน: azimuth (radian) + ระยะราบ."""
    azimuth: float
    distance: float


def calculate_azimuth(n1: float, e1: float, n2: float, e2: float) -> float:
    """azimuth (radian) จากจุด1 ไปจุด2, วัดจากเหนือวนขวา, ช่วง [0, 2*pi).

    ใช้ atan2(dE, dN) ไม่ใช่ atan2(dN, dE).
    """
    az = math.atan2(e2 - e1, n2 - n1)
    return fpmath.normalize_angle(az)


def calculate_distance_2d(n1: float, e1: float, n2: float, e2: float) -> float:
    """ระยะราบระหว่างสองจุด (ใช้ math.hypot กัน overflow/underflow).

    Args: n, e in metres.  Returns: plan distance in metres.
    """
    return math.hypot(n2 - n1, e2 - e1)


def calculate_distance_3d(n1: float, e1: float, z1: float,
                          n2: float, e2: float, z2: float) -> float:
    """ระยะตรง (slope distance) รวมความต่างระดับ.

    Args: n, e, z in metres.  Returns: slope distance in metres.
    """
    return math.hypot(n2 - n1, e2 - e1, z2 - z1)


def calculate_forward(n1: float, e1: float, azimuth: float, distance: float) -> Point:
    """จุดตั้ง + azimuth(radian) + ระยะ -> จุดใหม่.

    Args: n1, e1 in metres; azimuth in radians (WCB); distance in metres.
    Returns: Point(n, e) in metres.
    dN = d*cos(az), dE = d*sin(az)  (เทียบ Casio: Rec(distance, azimuth)).
    """
    return Point(
        n=n1 + distance * math.cos(azimuth),
        e=e1 + distance * math.sin(azimuth),
    )


def calculate_inverse(n1: float, e1: float, n2: float, e2: float) -> Inverse:
    """สองจุด -> azimuth(radian) + ระยะ (เทียบ Casio: Pol).

    Args: n, e in metres.  Returns: Inverse(azimuth in radians, distance in metres).
    """
    return Inverse(
        azimuth=calculate_azimuth(n1, e1, n2, e2),
        distance=calculate_distance_2d(n1, e1, n2, e2),
    )


def calculate_offset_point(n1: float, e1: float, azimuth: float,
                           along: float, offset: float = 0.0) -> Point:
    """เดินตาม azimuth เป็นระยะ along แล้วเยื้องตั้งฉาก offset.

    Args: n1, e1 in metres; azimuth in radians (WCB); along in metres; offset in metres.
    Returns: Point(n, e) in metres.
    offset: + = ขวามือของทิศเดิน, - = ซ้ายมือ. ขวามือ = azimuth + 90 องศา.
    """
    centerline_point = calculate_forward(n1, e1, azimuth, along)
    if not offset:
        return centerline_point
    offset_azimuth = fpmath.normalize_angle(azimuth + math.pi / 2.0)
    return calculate_forward(centerline_point.n, centerline_point.e, offset_azimuth, offset)
```

---

## FILE: src/smt/alignment.py
```python
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
                       Closed form in tangent-projected distance x: with
                       X = L - 0.0226689447*L**3/R**2 and a = x/X,
                         y(x)     = X**2/R * (a**2/4 - (1-cos(pi*a))/(2*pi**2))
                         theta(x) = atan(X/R * (a/2 - sin(pi*a)/(2*pi)))
                       `a` is recovered from the true arc distance `d` (not
                       approximated as `d/X`) by inverting the arc-length integral
                       s(a) = integral[0..a] X*sqrt(1+(dy/dx)^2) da' via Simpson
                       quadrature + bisection (`_cosine_solve_a`) — except exactly at
                       d=length, where a=1 is used directly (exact closed form, see
                       `_sine_halfwave_point`). SPIN (k_in=0) uses this directly with
                       d as given. SPOUT (k_out=0) mirrors it via s<->L-s (see
                       `_sine_halfwave_point` and the SPOUT branch in
                       `calculate_point_on_element`), matching the Civil
                       3D-confirmed invariant that SPIN and SPOUT of equal R,L share
                       the same total turning angle. Verified against 3 independent
                       Civil 3D ground-truth points (R=900/L=100, R=250/L=50,
                       R=500/L=70) — see session_logs/investigate_sinehalfwave_formula.md
                       and session_logs/investigate_cosine_arclength_inversion.md.
                       Known limitations (documented there, not fixed here):
                       (1) s(1) != length exactly — a genuine small imperfection in
                       Autodesk's own closed-form X, not a quadrature artifact
                       (residual 0.036mm at R=900/L=100, 0.187mm at R=250/L=50,
                       stable from 48 to 48,000 Simpson intervals). Any d strictly
                       between s(1) and length has no a<=1 solving s(a)=d;
                       `_cosine_solve_a` clamps to a=1.0 in that gap rather than
                       erroring (see its own comment for the mechanics);
                       (2) the SPOUT mid-curve trace is derived from the boundary
                       mirror only — no independent Civil 3D data confirms a SPOUT
                       interior point, only the shared endpoint invariant;
                       (3) RESOLVED, not an open item: `landxml.py`'s
                       `_spiral_geometry` was originally expected to need a matching
                       follow-up fix for totalY/tanShort — verified in Phase 2
                       (session_logs/investigate_landxml_phase2_totaly_export.md)
                       that this was unnecessary. totalY/tanShort there have no
                       override or formula of their own; they already flow
                       correctly from this module's fix with zero code changes,
                       confirmed against real Civil 3D ground truth.

Naming note: 'COSINE' is this project's internal name for the shape Civil 3D
calls the Sine Half-Wavelength Diminishing Tangent Curve (spiType="sineHalfWave"
in LandXML) -- the same shape, not a different one. The name 'COSINE' stays in
code and in the CSV Transition column for backward compatibility with existing
files; see session_logs/investigate_sinehalfwave_formula.md and
docs/extensions.md EXT-003 for the formula derivation.

Depends on: fpmath, wcb.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
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


def _cosine_dydx(a: float, big_x: float, r: float) -> float:
    """dy/dx at normalised parameter a for the COSINE shape — the same expression
    as the argument of atan() in the theta closed form (tan(theta) = dy/dx),
    extracted so the arc-length integrand (`_cosine_arc_length`) and the theta
    formula in `_sine_halfwave_point` share one definition.
    """
    return big_x / r * (a / 2 - math.sin(math.pi * a) / (2 * math.pi))


def _cosine_arc_length(a: float, big_x: float, r: float, n_seg: int = SPIRAL_STEPS) -> float:
    """s(a) = integral[0..a] X*sqrt(1+(dy/dx)^2) da'  via Simpson quadrature.

    True physical arc length from the zero-curvature end to normalised parameter a.
    Sign of r does not matter (dy/dx is squared inside the root) -- callers building
    the cached table pass abs(r).
    """
    h = a / n_seg
    total = 0.0
    for i in range(n_seg + 1):
        ai = i * h
        integrand = big_x * math.hypot(1.0, _cosine_dydx(ai, big_x, r))
        w = 1 if (i == 0 or i == n_seg) else (4 if i % 2 == 1 else 2)
        total += w * integrand
    return total * h / 3.0


@lru_cache(maxsize=256)
def _cosine_arc_length_table(length: float, r_abs: float) -> tuple[float, ...]:
    """Cached s(a_i) at a_i = i/SPIRAL_STEPS, i=0..SPIRAL_STEPS, for one
    (length, |R|) pair.

    Shared by SPIN and SPOUT of equal length and |R| (mirror symmetry — see module
    docstring), so a compound alignment using both only builds the table once. Used
    to bracket the root of s(a)=d before bisection refinement in `_cosine_solve_a`.
    """
    big_x = calculate_sine_halfwave_tangent_length(length, r_abs)
    n = SPIRAL_STEPS
    return tuple(_cosine_arc_length(i / n, big_x, r_abs) for i in range(n + 1))


def _cosine_solve_a(d: float, big_x: float, r: float, length: float) -> float:
    """Solve s(a) = d for normalised parameter a: cached-table bracket + bisection
    (same 50-iteration bisection style as `calculate_projection_to_element` below).

    d must satisfy 0 <= d < length (the d==length case is short-circuited by the
    caller, `_sine_halfwave_point`).
    """
    r_abs = abs(r)
    table = _cosine_arc_length_table(length, r_abs)
    n = SPIRAL_STEPS
    i = 0
    while i < n and table[i + 1] < d:
        i += 1
    # When d lies in (s(1), length) -- i.e. beyond the table's own last entry -- no
    # a<=1 solves s(a)=d exactly, because s(1) != length exactly (a genuine small
    # imperfection in Autodesk's closed-form X, not a quadrature artifact -- see
    # session_logs/investigate_cosine_arclength_inversion.md section 3). In that
    # case the while loop above runs to i=n, giving lo=hi=1.0: the bracket is
    # degenerate but the bisection loop below is still safe (mid=1.0 every
    # iteration, converges trivially) -- this deliberately clamps to a=1.0, the
    # closest reachable value, instead of raising.
    lo, hi = i / n, min(i + 1, n) / n
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if _cosine_arc_length(mid, big_x, r_abs) < d:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _sine_halfwave_point(d: float, big_x: float, r: float, length: float) -> tuple[float, float, float]:
    """COSINE transition shape (Civil 3D Sine Half-Wave -- see module docstring
    "Transition shapes"), canonical (SPIN) form.

    d     : true arc distance from the zero-curvature end (station distance along
            the element's centre line).
    big_x : X, the closed-form tangent-projected length at the curve's own full L
            (X = L - 0.0226689447*L**3/R**2), constant for one element.
    r     : signed radius at the curved end (+ right, - left).
    length: element arc length L; used for the d==length exact shortcut and to key
            the cached arc-length table (`_cosine_arc_length_table`).
    Returns (x, y, theta): the true tangent-projected coordinate x=a*X, local offset
    y (+ left of entry tangent), and tangent angle theta (radians) at d, all
    measured from the zero-curvature end.
    Reference: Autodesk Civil 3D 2026 Help, "About Transition Definitions" — see
    session_logs/investigate_sinehalfwave_formula.md and
    session_logs/investigate_cosine_arclength_inversion.md for the verified
    derivation and the arc-length inversion respectively.
    """
    if abs(d - length) < 1e-9:
        a = 1.0
    else:
        a = _cosine_solve_a(d, big_x, r, length)
    y = big_x ** 2 / r * (a ** 2 / 4 - (1 - math.cos(math.pi * a)) / (2 * math.pi ** 2))
    theta = math.atan(_cosine_dydx(a, big_x, r))
    x = a * big_x
    return x, y, theta


def calculate_sine_halfwave_tangent_length(length: float, r: float) -> float:
    """Closed-form tangent-projected length X for the COSINE transition shape
    (Civil 3D Sine Half-Wave -- see module docstring "Transition shapes"), at
    the element's own true end (arc length = `length`).

    length : element arc length L (m); always positive.
    r      : signed radius at the curved end (m); sign does not affect the
             result since only r**2 appears in the formula.
    Returns X = L - 0.0226689447*L**3/R**2 (m) — the tangent-projected
    distance from the zero-curvature end, NOT equal to L except in the
    R -> infinity limit. Single source of truth for the closed-form constant
    used both by `_sine_halfwave_point` (point-on-element geometry) and by
    `landxml.py::_spiral_geometry` (LandXML totalX export).
    Reference: Autodesk Civil 3D 2026 Help, "About Transition Definitions";
    see session_logs/investigate_sinehalfwave_formula.md and
    session_logs/investigate_totalx_landxml_fix.md.
    """
    return length - _SINE_HALFWAVE_C * length ** 3 / r ** 2


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
            big_x = calculate_sine_halfwave_tangent_length(length, r)
            x_local, y_local, theta_local = _sine_halfwave_point(d, big_x, r, length)
        else:   # SPOUT: curvature 1/R -> 0, mirror canonical form via s <-> L-d
            r = radius_from_curvature(el.k_in)
            big_x = calculate_sine_halfwave_tangent_length(length, r)
            x_end, y_end, theta_total = _sine_halfwave_point(length, big_x, r, length)
            x_g, y_g, theta_g = _sine_halfwave_point(length - d, big_x, r, length)
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
```

---

## FILE: src/smt/check.py
```python
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
    disc   : survey discrepancy carried through from input as raw string
    """
    name: str
    n: float
    e: float
    z: float
    sta: float
    offset: float
    disc: str


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

    field_points : list of dicts — keys 'name' (str), 'n', 'e', 'z' (float), 'disc' (any).
                   'disc' is converted to str; defaults to '' when absent.
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
        disc = str(fp.get('disc', ''))
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
```

---

## FILE: src/smt/builders/table_splitter.py
```python
"""table_splitter - Split a mixed PI/drawing-point table into its two feeds.

Some field CSVs (e.g. test_data/HOR_ORR_04.csv) list BP/PI-n/EP vertex rows and
PT/PC/TS/SC/CS/ST drawn control-point rows in one table, interleaved. Neither
parse_pi_table() nor check_against_drawing() accept that shape directly - each
wants only its own subset. split_mixed_alignment_table() is the adapter that
sits in front of both, unchanged.

Depends on: none (pure string/dict reshaping; no geometry).
"""
from __future__ import annotations

import re
from typing import Any

_VERTEX_POINT_RE = re.compile(r'^(BP|PI-\d+|EP)$')

# Maps lowercased header cell text -> canonical column key (mirrors the subset
# of alignment_builder._COL_ALIASES this module needs).
_COL_ALIASES: dict[str, str] = {
    'point':      'point',
    'sta':        'sta',
    'chainage':   'sta',
    'n':          'northing',
    'northing':   'northing',
    'e':          'easting',
    'easting':    'easting',
    'r':          'radius',
    'radius':     'radius',
    'ls':         'ls',
    'spiral':     'ls',
    'lsin':       'lsin',
    'lsout':      'lsout',
    'delta':      'delta',
    'trans':      'trans',
    'transition': 'trans',
}

# Columns that may carry thousands-separator commas (e.g. "1,537,772.85") in
# quoted CSV cells - stripped before handing rows to parse_pi_table(), whose
# float() calls don't tolerate them.
_NUMERIC_KEYS: tuple[str, ...] = (
    'sta', 'northing', 'easting', 'radius', 'ls', 'lsin', 'lsout', 'delta',
)


def _parse_header(header_row: list[Any]) -> dict[str, int]:
    """Return canonical-key -> column-index mapping from the header row."""
    col_map: dict[str, int] = {}
    for i, cell in enumerate(header_row):
        key = _COL_ALIASES.get(str(cell).strip().lower())
        if key is not None and key not in col_map:
            col_map[key] = i
    return col_map


def _strip_thousands_separators(value: str) -> str:
    return value.replace(',', '')


def split_mixed_alignment_table(
    rows: list[list[Any]],
) -> tuple[list[list[Any]], list[dict[str, Any]]]:
    """Split a mixed BP/PI-n/PT/PC/TS/SC/CS/ST/EP table into (vertex_rows, drawing).

    rows[0] is the header row (matched case-insensitively via _COL_ALIASES).

    vertex_rows : [header] + every row whose POINT cell matches ^(BP|PI-\\d+|EP)$,
                  plus any blank-POINT row (a compound sub-row that parse_pi_table()
                  attaches to the preceding PI). Feed straight into parse_pi_table().
    drawing     : {'name', 'sta', 'n', 'e'} dicts built from every remaining
                  non-blank row (PT/PC/TS/SC/CS/ST in practice). Feed straight
                  into check_against_drawing().

    Numeric cells in vertex_rows (sta/northing/easting/radius/ls/lsin/lsout/delta)
    and the sta/n/e values read into drawing have thousands-separator commas
    stripped first, since csv.reader returns quoted "1,537,772.85"-style cells
    as literal strings and neither parse_pi_table() nor float() accept them.
    Fully blank rows (every cell empty) are skipped from both outputs.
    """
    header = rows[0]
    col_map = _parse_header(header)
    vertex_rows: list[list[Any]] = [header]
    drawing: list[dict[str, Any]] = []

    def cell(row: list[Any], key: str) -> str:
        idx = col_map.get(key)
        if idx is None or idx >= len(row):
            return ''
        return str(row[idx]).strip()

    for row in rows[1:]:
        if not row or all(str(c).strip() == '' for c in row):
            continue

        point = cell(row, 'point')
        if not point or _VERTEX_POINT_RE.match(point):
            cleaned = list(row)
            for key in _NUMERIC_KEYS:
                idx = col_map.get(key)
                if idx is not None and idx < len(cleaned):
                    cleaned[idx] = _strip_thousands_separators(str(cleaned[idx]).strip())
            vertex_rows.append(cleaned)
        else:
            drawing.append({
                'name': point,
                'sta': float(_strip_thousands_separators(cell(row, 'sta'))),
                'n':   float(_strip_thousands_separators(cell(row, 'northing'))),
                'e':   float(_strip_thousands_separators(cell(row, 'easting'))),
            })

    return vertex_rows, drawing
```

---

## FILE: src/smt/builders/alignment_builder.py
```python
"""alignment_builder - Build horizontal alignment from a PI (Point of Intersection) list.

Port from reference/AlignmentBuilder.gs (validated engine, AllTests 45/45).

Workflow
  1. Accept a PI polyline:  [BP, {PI₁, ...}, ..., EP]
  2. For each interior PI vertex, decompose the curve into sub-elements (SPIN / C / SPOUT),
     solve the 2×2 linear system to find where TS/PC sits on the incoming tangent, then
     propagate forward to build each Element and its control-point coordinates.
  3. Return BuildResult(elements, control, issues).

Supported curve types at each PI vertex
  Simple circle        : {'n', 'e', 'R'}
  Symmetric spiral     : {'n', 'e', 'R', 'Ls'}              Ls_in = Ls_out
  Asymmetric spiral    : {'n', 'e', 'R', 'LsIn', 'LsOut'}   Ls_in ≠ Ls_out
  Compound (2+ arcs)   : {'n', 'e', 'compound': [{'R', 'delta'}, ..., {'R'}]}
                         delta in degrees; last arc takes the remainder
  Plus optional 'trans' / 'transIn' / 'transOut' keys for transition shape
  (CLOTHOID / BLOSS / COSINE / SINE, default CLOTHOID).

R is always positive in the vertex dict.  Turn direction (left/right) is inferred from
the deflection angle δ = calculate_angle_diff(az_out, az_in).

Depends on: fpmath, wcb, alignment.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, NamedTuple

from .. import fpmath, wcb
from ..alignment import Element, calculate_exit_state, make_element

# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------

@dataclass
class ControlPoint:
    """Named chainage–coordinate triplet produced by the builder."""
    name: str
    sta: float
    n: float
    e: float


class BuildResult(NamedTuple):
    """Output of build_alignment_from_pi."""
    elements: list[Element]
    control: list[ControlPoint]
    issues: list[str]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_curve_sub_elements(
    vert: dict[str, Any], abs_delta: float,
) -> tuple[list[dict[str, Any]], str | None]:
    """Decompose a PI vertex into ordered sub-element specifications.

    abs_delta : absolute deflection angle (radians, always ≥ 0).
    Returns (subs, issue) where each sub is a dict with keys
    'kind', 'R', 'len', and optionally 'trans'.
    """
    subs: list[dict[str, Any]] = []
    issue: str | None = None

    compound = vert.get('compound')
    if compound:
        used = 0.0
        for i, arc in enumerate(compound):
            r_circular = abs(float(arc['R']))
            if i < len(compound) - 1:
                delta = fpmath.deg_to_rad(float(arc['delta']))
                used += delta
            else:
                delta = abs_delta - used
            if delta < 0:
                issue = 'compound: ผลรวม delta เกินมุมเลี้ยว'
            subs.append({'kind': 'C', 'R': r_circular, 'len': r_circular * delta})
        return subs, issue

    # EXTENSION: beyond oracle — treat missing R or R=0 as an angle point.
    # Oracle would produce NaN; we return empty subs to signal a no-curve PI.
    if not vert.get('R'):
        return [], None

    R = abs(float(vert['R']))
    ls_in  = float(vert['LsIn']  if vert.get('LsIn')  is not None else (vert.get('Ls') or 0.0))
    ls_out = float(vert['LsOut'] if vert.get('LsOut') is not None else (vert.get('Ls') or 0.0))

    if ls_in > 0 or ls_out > 0:
        trans     = vert.get('trans')
        trans_in  = vert.get('transIn') or trans
        trans_out = vert.get('transOut') or trans
        # EXTENSION: beyond oracle — reference/AlignmentBuilder.gs (lines 53-54) still
        # assumes theta=Ls/(2R); real turning angle needed for the COSINE closed form.
        theta_in  = _spiral_turning_angle(R, ls_in, trans_in)   if ls_in  > 0 else 0.0
        theta_out = _spiral_turning_angle(R, ls_out, trans_out) if ls_out > 0 else 0.0
        delta_circular = abs_delta - theta_in - theta_out
        if delta_circular < 0:
            issue = 'spiral ยาวเกินมุมเลี้ยว (Δ < θsIn+θsOut)'
        if ls_in > 0:
            subs.append({'kind': 'SPIN',  'R': R, 'len': ls_in,  'trans': trans_in})
        subs.append({'kind': 'C', 'R': R, 'len': R * delta_circular})
        if ls_out > 0:
            subs.append({'kind': 'SPOUT', 'R': R, 'len': ls_out, 'trans': trans_out})
        return subs, issue

    subs.append({'kind': 'C', 'R': R, 'len': R * abs_delta})
    return subs, issue


def _get_control_names(subs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return control-point name scheme for a curve group.

    Returns dict with keys 'start', 'end', 'jct' (list of junction names).
    """
    # EXTENSION: beyond oracle — defensive guard against IndexError when subs is
    # empty (angle point).  build_alignment_from_pi handles 'IP' naming directly
    # and never calls this function for empty subs, but guard here for safety.
    if not subs:
        return {'start': 'IP', 'end': 'IP', 'jct': []}
    start = 'TS' if subs[0]['kind'] == 'SPIN' else 'PC'
    end   = 'ST' if subs[-1]['kind'] == 'SPOUT' else 'PT'
    jct: list[str] = []
    for i in range(len(subs) - 1):
        a, b = subs[i]['kind'], subs[i + 1]['kind']
        if   a == 'SPIN'  and b == 'C':     jct.append('SC')
        elif a == 'C'     and b == 'SPOUT': jct.append('CS')
        elif a == 'C'     and b == 'C':     jct.append('PCC')
        else:                                jct.append('JCT')
    return {'start': start, 'end': end, 'jct': jct}


def _spiral_turning_angle(R: float, length: float, trans: str | None) -> float:
    """Real accumulated turning angle (radians) of one spiral, R/length/shape only.

    Built via a synthetic SPIN element at the origin (k_in=0, k_out=1/R, entry azimuth
    0) — same canonical-SPIN technique as landxml.py::_spiral_geometry and
    _calculate_end_displacement below. Replaces the linear approximation length/(2R),
    which is exact for CLOTHOID/BLOSS/SINE (F(1)=1/2 in alignment._shape_integral) but
    not for COSINE's closed-form turning angle (see session_logs/
    investigate_build_curve_sub_elements_fix.md).
    """
    el = make_element('SPIN', 0.0, length, 0.0, 0.0, 0.0, R, None, trans)
    return calculate_exit_state(el).azimuth - el.azimuth


def _calculate_end_displacement(
    subs: list[dict[str, Any]], azimuth_in: float, sign: float,
) -> tuple[float, float]:
    """End-displacement (ΔN, ΔE) of the curve group starting at the global origin.

    Builds each sub as an Element starting at (0, 0) with entry azimuth azimuth_in, then
    propagates forward.  The returned value equals (ST.N − TS.N, ST.E − TS.E) when the
    group is placed at any origin in a global frame without rotation.
    """
    cur_n, cur_e, current_azimuth = 0.0, 0.0, azimuth_in
    sta = 0.0
    for s in subs:
        el = make_element(
            s['kind'], sta, sta + s['len'],
            cur_n, cur_e, fpmath.rad_to_deg(current_azimuth),
            sign * s['R'], None, s.get('trans'),
        )
        state = calculate_exit_state(el)
        cur_n, cur_e, current_azimuth = state.n, state.e, state.azimuth
        sta += s['len']
    return cur_n, cur_e


# ---------------------------------------------------------------------------
# Public: parser
# ---------------------------------------------------------------------------

# Maps lowercased header cell text → canonical column key.
_COL_ALIASES: dict[str, str] = {
    'point':      'point',
    'n':          'northing',
    'northing':   'northing',
    'e':          'easting',
    'easting':    'easting',
    'sta':        'sta',
    'chainage':   'sta',
    'r':          'radius',
    'radius':     'radius',
    'ls':         'ls',
    'spiral':     'ls',
    'lsin':       'lsin',
    'lsout':      'lsout',
    'trans':      'trans',
    'transition': 'trans',
    'delta':      'delta',
}


def _parse_header(header_row: list[Any]) -> dict[str, int]:
    """Return canonical-key → column-index mapping from the header row."""
    col_map: dict[str, int] = {}
    for i, cell in enumerate(header_row):
        key = _COL_ALIASES.get(str(cell).strip().lower())
        if key is not None and key not in col_map:
            col_map[key] = i
    return col_map


def _get_cell(row: list[Any], col_map: dict[str, int], key: str) -> str:
    """Return stripped cell string; '' when column is absent or row is too short."""
    idx = col_map.get(key)
    if idx is None or idx >= len(row):
        return ''
    return str(row[idx]).strip()


def parse_pi_table(rows: list[Any]) -> list[dict[str, Any]]:
    """Parse a PI-table (first row = headers) into a vertex list for
    build_alignment_from_pi.

    Column names are matched case-insensitively from the header row:
      POINT / (same)         — 'BP' | 'EP' | PI label | blank = compound sub-row
      N / NORTHING           — northing
      E / EASTING            — easting
      STA / CHAINAGE         — starting chainage (BP only; default 0.0)
      R / RADIUS             — radius metres; blank or '0' = angle point (EXT-001)
      LS / SPIRAL            — symmetric spiral length
      LSIN                   — entry spiral length (overrides LS when non-blank)
      LSOUT                  — exit spiral length (overrides LS when non-blank)
      TRANS / TRANSITION     — CLOTHOID (default) | BLOSS | COSINE | SINE
      DELTA                  — arc deflection degrees (compound sub-rows; blank on last arc)

    Columns not present in the header use defaults (STA → 0.0; others → blank).
    Blank-POINT rows with a non-blank R are compound sub-arcs attached to the
    preceding PI vertex.  Blank-POINT rows with blank R are ignored (blank lines).

    Raises ValueError for malformed numeric cells (propagated from float()).
    """
    col_map = _parse_header(rows[0])

    def _g(row: list[Any], key: str) -> str:
        return _get_cell(row, col_map, key)

    vertices: list[dict[str, Any]] = []
    pending_pi: dict[str, Any] | None = None
    pending_pi_label: str = ''
    pending_pi_line: int = 0
    compound_arcs: list[dict[str, Any]] = []

    def _flush_pending() -> None:
        nonlocal pending_pi
        if pending_pi is None:
            return
        if compound_arcs:
            if 'R' in pending_pi:
                raise ValueError(
                    f'PI "{pending_pi_label}" (แถวที่ {pending_pi_line}) มีทั้งค่า RADIUS '
                    f'({pending_pi["R"]}) และมี compound sub-row ตามมา '
                    'กำกวมว่าจะใช้ค่ารัศมีไหน '
                    'ให้ปล่อย RADIUS ของแถว PI นี้ว่างไว้ '
                    'แล้วย้ายค่า RADIUS (และ Delta ถ้ามี) '
                    'ไปเป็นแถว compound sub-row แยกต่างหากแทน'
                )
            v: dict[str, Any] = {'n': pending_pi['n'], 'e': pending_pi['e']}
            v['compound'] = compound_arcs.copy()
            compound_arcs.clear()
        else:
            v = dict(pending_pi)
        vertices.append(v)
        pending_pi = None

    for line_no, row in enumerate(rows[1:], start=2):   # start=2: row 1 is the header
        point = _g(row, 'point')

        if not point:
            # compound sub-row — only meaningful when R is non-blank
            r_raw = _g(row, 'radius')
            if not r_raw:
                continue
            arc: dict[str, Any] = {'R': float(r_raw)}
            delta_raw = _g(row, 'delta')
            if delta_raw:
                arc['delta'] = float(delta_raw)
            compound_arcs.append(arc)
            continue

        _flush_pending()

        n = float(_g(row, 'northing'))
        e = float(_g(row, 'easting'))

        if point == 'BP':
            sta_raw = _g(row, 'sta')
            vertices.append({'n': n, 'e': e, 'sta': float(sta_raw) if sta_raw else 0.0})
            continue

        if point == 'EP':
            vertices.append({'n': n, 'e': e})
            continue

        # PI vertex
        pi_dict: dict[str, Any] = {'n': n, 'e': e}
        r_raw = _g(row, 'radius')
        if r_raw and float(r_raw) != 0.0:
            pi_dict['R'] = float(r_raw)
            ls_raw    = _g(row, 'ls')
            lsin_raw  = _g(row, 'lsin')
            lsout_raw = _g(row, 'lsout')
            if lsin_raw or lsout_raw:
                if lsin_raw:
                    pi_dict['LsIn'] = float(lsin_raw)
                if lsout_raw:
                    pi_dict['LsOut'] = float(lsout_raw)
            elif ls_raw:
                pi_dict['Ls'] = float(ls_raw)
            trans = _g(row, 'trans')
            if trans:
                pi_dict['trans'] = trans
        # else: R absent or 0 → angle point (no 'R' key); may gain 'compound' later

        pending_pi = pi_dict
        pending_pi_label = point
        pending_pi_line = line_no

    _flush_pending()
    return vertices


# ---------------------------------------------------------------------------
# Public: builder
# ---------------------------------------------------------------------------

def build_alignment_from_pi(vertices: list[dict[str, Any]]) -> BuildResult:
    """Build a horizontal alignment element list from a PI vertex polyline.

    vertices[0]  = BP  — {'n', 'e', 'sta'}.  sta sets the starting chainage.
    vertices[1:-1] = PI — curve parameters as described in the module docstring.
    vertices[-1] = EP  — {'n', 'e'}.

    Returns BuildResult(elements, control, issues).  Geometry errors (e.g. spiral
    longer than deflection angle) are appended to issues rather than raised.
    """
    elements: list[Element] = []
    control:  list[ControlPoint] = []
    issues:   list[str] = []
    N = len(vertices)

    prev_n   = float(vertices[0]['n'])
    prev_e   = float(vertices[0]['e'])
    prev_sta = float(vertices[0].get('sta', 0.0))
    control.append(ControlPoint(name='BP', sta=prev_sta, n=prev_n, e=prev_e))

    for v in range(1, N - 1):
        vertex_n = float(vertices[v]['n'])
        vertex_e = float(vertices[v]['e'])

        azimuth_in  = wcb.calculate_azimuth(
            float(vertices[v - 1]['n']), float(vertices[v - 1]['e']), vertex_n, vertex_e
        )
        azimuth_out = wcb.calculate_azimuth(
            vertex_n, vertex_e, float(vertices[v + 1]['n']), float(vertices[v + 1]['e'])
        )

        delta     = fpmath.calculate_angle_diff(azimuth_out, azimuth_in)
        sign      = 1.0 if delta >= 0 else -1.0
        abs_delta = abs(delta)

        subs, issue = _build_curve_sub_elements(vertices[v], abs_delta)
        if issue:
            issues.append(f'PI#{v}: {issue}')

        # EXTENSION: beyond oracle — no-curve PI (angle point or collinear).
        # Emits a tangent element to the PI vertex, records it as 'IP', and continues.
        # This also avoids ZeroDivisionError when det = sin(delta) = 0 (collinear case).
        if not subs:
            tan_len = wcb.calculate_distance_2d(prev_n, prev_e, vertex_n, vertex_e)
            sta_pi  = prev_sta + tan_len
            elements.append(make_element(
                'T', prev_sta, sta_pi, prev_n, prev_e, fpmath.rad_to_deg(azimuth_in), 0,
            ))
            control.append(ControlPoint(name='IP', sta=sta_pi, n=vertex_n, e=vertex_e))
            prev_n, prev_e, prev_sta = vertex_n, vertex_e, sta_pi
            continue

        # Solve 2×2 system: d1·uIn + d2·uOut = V
        # where V = end displacement of curve group placed at origin.
        # Solution: d1 = (V.n·sin(az_out) − V.e·cos(az_out)) / sin(δ)
        v_n, v_e = _calculate_end_displacement(subs, azimuth_in, sign)
        det = math.sin(delta)                              # = sin(az_out − az_in)
        d1  = (v_n * math.sin(azimuth_out) - v_e * math.cos(azimuth_out)) / det

        curve_start_n = vertex_n - d1 * math.cos(azimuth_in)   # curve start (TS / PC)
        curve_start_e = vertex_e - d1 * math.sin(azimuth_in)

        name_scheme = _get_control_names(subs)

        # Tangent element: previous exit → curve start
        tan_len = wcb.calculate_distance_2d(prev_n, prev_e, curve_start_n, curve_start_e)
        sta_cs  = prev_sta + tan_len
        elements.append(make_element(
            'T', prev_sta, sta_cs, prev_n, prev_e, fpmath.rad_to_deg(azimuth_in), 0,
        ))
        control.append(ControlPoint(
            name=name_scheme['start'], sta=sta_cs, n=curve_start_n, e=curve_start_e,
        ))

        # Sub-elements: propagate forward from curve start
        cur_n, cur_e, cur_az = curve_start_n, curve_start_e, azimuth_in
        sta = sta_cs
        for i, s in enumerate(subs):
            el = make_element(
                s['kind'], sta, sta + s['len'],
                cur_n, cur_e, fpmath.rad_to_deg(cur_az),
                sign * s['R'], None, s.get('trans'),
            )
            elements.append(el)
            state = calculate_exit_state(el)
            cur_n, cur_e, cur_az = state.n, state.e, state.azimuth
            sta += s['len']
            pt_name = name_scheme['jct'][i] if i < len(subs) - 1 else name_scheme['end']
            control.append(ControlPoint(name=pt_name, sta=sta, n=cur_n, e=cur_e))

        prev_n, prev_e, prev_sta = cur_n, cur_e, sta

    # Final tangent: last curve exit → EP
    ep_n  = float(vertices[-1]['n'])
    ep_e  = float(vertices[-1]['e'])
    az_ep = wcb.calculate_azimuth(prev_n, prev_e, ep_n, ep_e)
    ep_len = wcb.calculate_distance_2d(prev_n, prev_e, ep_n, ep_e)
    elements.append(make_element(
        'T', prev_sta, prev_sta + ep_len, prev_n, prev_e, fpmath.rad_to_deg(az_ep), 0,
    ))
    control.append(ControlPoint(name='EP', sta=prev_sta + ep_len, n=ep_n, e=ep_e))

    return BuildResult(elements=elements, control=control, issues=issues)


# ---------------------------------------------------------------------------
# Public: cross-check
# ---------------------------------------------------------------------------

def check_against_drawing(
    control: list[ControlPoint],
    drawing: list[dict[str, Any]],
    tolerance: float = 0.05,
) -> list[dict[str, Any]]:
    """Cross-check computed control points against drawn / surveyed coordinates.

    For each entry in drawing, finds the closest-by-station control point
    (filtered by name when drawing entry has a non-empty 'name' key), then
    computes the 2-D spatial gap.

    drawing entries: {'name' (optional), 'sta', 'n', 'e'}.
    Returns list of dicts: {name, sta_calc, sta_draw, gap_m, ok}.
    ok is True when gap_m ≤ tolerance.
    """
    report: list[dict[str, Any]] = []
    for d in drawing:
        d_name = str(d.get('name') or '').strip()
        d_sta  = float(d['sta'])
        best:   ControlPoint | None = None
        best_d  = math.inf
        for c in control:
            if d_name and c.name != d_name:
                continue
            dist = abs(c.sta - d_sta)
            if dist < best_d:
                best_d = dist
                best = c
        if best is None:
            continue
        gap = math.hypot(best.n - float(d['n']), best.e - float(d['e']))
        report.append({
            'name':     d_name or best.name,
            'sta_calc': best.sta,
            'sta_draw': d_sta,
            'gap_m':    gap,
            'ok':       gap <= tolerance,
        })
    return report
```

---

## FILE: src/smt/cli.py (excerpt — lines 109-168 only: `_radius_from_element` + `_run_build`)
```python
def _radius_from_element(el: alignment.Element) -> float:
    """Return signed design radius for output CSV (0 = tangent)."""
    if el.k_in != 0:
        return 1.0 / el.k_in
    if el.k_out != 0:
        return 1.0 / el.k_out
    return 0.0


def _run_build(args: argparse.Namespace) -> int:
    """build: PI table CSV -> elements_output.csv + controls_so_output.csv."""
    import os
    vertices = _read_pi_table(args.alignment)
    if not vertices:
        raise ValueError('ไม่พบข้อมูล PI ในไฟล์ หรือไฟล์ไม่ใช่ PI table format')
    build_result = build_alignment_from_pi(vertices)
    for issue in build_result.issues:
        print(f'warning: {issue}', file=sys.stderr)

    out_dir = args.out_dir if args.out_dir else os.path.dirname(os.path.abspath(args.alignment))
    os.makedirs(out_dir, exist_ok=True)

    el_path = os.path.join(out_dir, 'elements_output.csv')
    el_header = ['StaStart', 'StaEnd', 'N', 'E', 'Azimuth', 'Radius', 'Type', 'Transition']
    el_rows = []
    for el in build_result.elements:
        transition_val = '' if el.type in ('T', 'C') else el.transition
        el_rows.append([
            f'{el.sta_start:.6f}',
            f'{el.sta_end:.6f}',
            f'{el.n:.6f}',
            f'{el.e:.6f}',
            f'{fpmath.rad_to_deg(el.azimuth):.6f}',
            f'{_radius_from_element(el):.6f}',
            el.type,
            transition_val,
        ])
    with open(el_path, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([el_header] + el_rows)

    cp_path = os.path.join(out_dir, 'controls_so_output.csv')
    cp_header = ['Name', 'STA', 'N', 'E']
    cp_rows = [[cp.name, f'{cp.sta:.6f}', f'{cp.n:.6f}', f'{cp.e:.6f}']
               for cp in build_result.control]
    with open(cp_path, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([cp_header] + cp_rows)

    print(f'\n=== Elements ({len(build_result.elements)} rows) -> {el_path} ===')
    print(f'{"StaStart":>10} {"StaEnd":>10} {"N":>12} {"E":>12} {"Az(deg)":>12} {"Radius":>10} {"Type":<6} {"Trans"}')
    print('-' * 90)
    for row in el_rows:
        print(f'{row[0]:>10} {row[1]:>10} {row[2]:>12} {row[3]:>12} {row[4]:>12} {row[5]:>10} {row[6]:<6} {row[7]}')

    print(f'\n=== Control Points ({len(build_result.control)} rows) -> {cp_path} ===')
    print(f'{"Name":<6} {"STA":>12} {"N":>14} {"E":>14}')
    print('-' * 50)
    for row in cp_rows:
        print(f'{row[0]:<6} {row[1]:>12} {row[2]:>14} {row[3]:>14}')

    return 0
```
