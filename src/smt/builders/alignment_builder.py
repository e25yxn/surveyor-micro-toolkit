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
    has_geometric_overlap: bool = False
    """Strict (zero-tolerance) curve-overlap flag: True if ANY
    tan_len_signed was negative, independent of TOL_METERS. `issues` only
    warns past TOL_METERS (tolerates real-world coordinate-rounding noise,
    see Oracle Correction entry in docs/extensions.md); this field exists
    so callers that need a strict geometric-validity signal (e.g.
    optimizer.py's fit_radius, which uses it as a hard search-space
    constraint) are not silently affected by that user-facing noise
    tolerance."""


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
    compound_arcs_first_line: int = 0

    def _flush_pending() -> None:
        nonlocal pending_pi
        if pending_pi is None:
            if compound_arcs:
                raise ValueError(
                    f'compound sub-row (แถวที่ {compound_arcs_first_line}) มีค่า RADIUS '
                    'แต่ไม่มี PI ก่อนหน้าให้ผูก (อยู่ก่อน PI ตัวแรก ก่อน BP, '
                    'หรืออยู่หลัง EP) '
                    'ตรวจสอบลำดับแถวในไฟล์ว่าไม่มีแถวตกหล่นหรือเรียงผิดที่'
                )
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
            if not compound_arcs:
                compound_arcs_first_line = line_no
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

# Threshold for the delta≈π (180° reversal) branch of the singular-deflection
# guard in build_alignment_from_pi (session_logs/plan_20260802_1904.md,
# addendum). Deliberately much wider than fpmath.EPS (1e-9): the delta≈π
# singularity is non-removable (d1 ~ 2R/(π−|delta|) as delta→π — see the plan),
# so its "danger radius" in delta-space is far larger than the well-conditioned
# delta≈0 case. 1e-4 rad (~20 arcsec off exact π) was set from a real-world
# floor, not guessed: CK1024's own Civil 3D drawings round input coordinates to
# 3 decimal places, and re-checking those same drawings at 15-decimal precision
# shows BP/PC pairs that are meant to coincide sitting ~1e-7 m apart purely from
# that rounding — 1e-4 rad sits ~1000x above that noise floor, while staying far
# below the tightest real hairpin curves (~170-175° deflection, sin ≈ 0.087-0.17,
# equivalent to ~0.09-0.17 rad off π) — see docs/extensions.md for the full
# derivation.
_NEAR_PI_EPS: float = 1e-4   # ~20 arcsec from exact pi

# Tolerance for the curve-overlap direction guard's tan_len_signed check
# below (Oracle correction, session_logs/review_src_smt_20260802.md #2,
# changed from threshold=A to B after real field data proved threshold=A
# too strict). Real survey CSVs -- test_data/AL1_test_alignment_PI.csv
# (PI#7/PI#8) and test_data/HOR_01N01.csv (PI#1/BP, PI#7/PI#8) -- produce
# tan_len_signed in the -0.5mm to -1.6mm range from 3-decimal coordinate
# rounding alone (same noise floor documented for _NEAR_PI_EPS above), not
# genuine design overlaps. TOL_METERS=0.02 sits ~12x above the largest
# observed noise (-1.6mm) while staying far below any engineering-meaningful
# overlap (metre-scale). See docs/extensions.md for the full evidence.
TOL_METERS: float = 0.02   # 2 cm


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
    has_geometric_overlap = False
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

        # EXTENSION: beyond oracle (Oracle correction exception, 2026-08-02, review
        # session_logs/review_src_smt_20260802.md #1) — sin(delta)≈0 makes the 2x2
        # tangent-intersection solve below singular in two distinct cases that need
        # two independent checks, not one shared abs(sin(delta)) test (a single
        # threshold on sin(delta) cannot tell "near 0" from "near π" apart, and the
        # two singularities have very different danger radii — see the plan
        # addendum): delta≈0 (collinear — a removable singularity: the analytic
        # limit of d1 is finite, but Python's 0.0/0.0 division doesn't take limits,
        # and the requested curve length R·|delta| is ≈0 anyway, so there is no real
        # curve to place; fpmath.EPS is tight enough here since d1 stays
        # well-conditioned all the way down to true float-zero) and delta≈π (180°
        # reversal — a genuine, non-removable singularity: the same math as the
        # standard circular-curve tangent-length formula T=R·tan(Δ/2), which is
        # undefined at Δ=π; AASHTO Green Book, see EXT-001; d1 ~ 2R/(π−|delta|)
        # diverges well before fpmath.EPS's radius, so this branch needs the much
        # wider _NEAR_PI_EPS instead). Both fall back to the angle-point
        # (tangent-tangent) path below instead of reaching the division. See
        # docs/extensions.md and session_logs/plan_20260802_1904.md + its addendum.
        if subs and (
            abs(math.sin(delta)) < fpmath.EPS
            or abs(math.pi - abs(delta)) < _NEAR_PI_EPS
        ):
            issues.append(
                f'PI#{v}: มุมเบี่ยง {fpmath.rad_to_deg(delta):.6f}° ทำให้หาจุดเริ่มโค้งไม่ได้ '
                '(sin(Δ)≈0 — เรียงเส้นตรงหรือหักกลับ 180°) ใช้ angle point (IP) แทนโค้งที่ระบุ'
            )
            subs = []

        # EXTENSION: beyond oracle — no-curve PI (angle point or collinear).
        # Emits a tangent element to the PI vertex, records it as 'IP', and continues.
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

        # FIX (Oracle correction, session_logs/review_src_smt_20260802.md #2,
        # session_logs/plan_20260804_2014.md): tan_len above is an unsigned
        # distance (hypot) so a curve with too little tangent (overlapping the
        # previous curve/BP) was never detected. prev and curve_start always
        # lie on the same azimuth_in line by construction, so this dot product
        # is a true signed tangent-leg length, not an approximation. Negative
        # means curve_start sits BEHIND prev -> genuine overlap. No fallback
        # fixes this (unlike EXT-001): the problem is the relationship between
        # two curves, not the shape of one curve -- so we only append an issue
        # and leave the geometry unchanged; the user must adjust R/Ls/PI
        # spacing in the input. prev may be BP itself (v == 1), not only a
        # prior PI -- confirmed possible in session_logs/
        # tmp_verify_bug2_curve_overlap.py (PI#1 vs BP there is negative too).
        dn = curve_start_n - prev_n
        de = curve_start_e - prev_e
        tan_len_signed = dn * math.cos(azimuth_in) + de * math.sin(azimuth_in)
        if tan_len_signed < 0:
            has_geometric_overlap = True
        if tan_len_signed < -TOL_METERS:
            prev_label = 'BP' if v == 1 else f'PI#{v - 1}'
            issues.append(
                f'PI#{v}: จุดเริ่มโค้ง (curve_start) อยู่หลังจุดจบของ {prev_label} '
                f'ตามทิศทาง azimuth_in ({fpmath.rad_to_deg(azimuth_in):.4f}°) — '
                f'โค้งซ้อนทับกัน (tan_len_signed = {tan_len_signed:.4f} m, ต้อง >= -{TOL_METERS:.2f} ม.) '
                f'ตรวจสอบ R/Ls หรือระยะห่างระหว่าง {prev_label} และ PI#{v}'
            )

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

    return BuildResult(elements=elements, control=control, issues=issues,
                        has_geometric_overlap=has_geometric_overlap)


# ---------------------------------------------------------------------------
# Public: cross-check
# ---------------------------------------------------------------------------

def check_against_drawing(
    control: list[ControlPoint],
    drawing: list[dict[str, Any]],
    tolerance: float = 0.05,
    max_sta_distance: float | None = 10.0,
) -> list[dict[str, Any]]:
    """Cross-check computed control points against drawn / surveyed coordinates.

    For each entry in drawing, finds the closest-by-station control point
    (filtered by name when drawing entry has a non-empty 'name' key), then
    computes the 2-D spatial gap.

    FIX (Oracle correction, session_logs/review_src_smt_20260802.md #4,
    session_logs/plan_<TBD>.md): check_against_drawing has no port in
    reference/gsheet/ or reference/vba/ at all -- the function those mirror
    is check.py::check_horizontal(), a different algorithm (evaluates the
    alignment directly at the drawing station instead of searching a control
    list). Condition (1) of the Oracle correction exception is therefore N/A
    here: there is no oracle implementation of this specific matching
    algorithm to diverge from. Previously a drawing point with no matching
    name (best is None) was silently dropped with `continue`, and
    closest-by-station matching had no distance ceiling, so a point far from
    every control point still got matched and reported as a confusing FAIL.
    Both are now reported as an explicit row (ok=False, note explains why)
    instead of vanishing or misleadingly failing.

    drawing entries: {'name' (optional), 'sta', 'n', 'e'}.
    Returns list of dicts: {name, sta_calc, sta_draw, gap_m, ok, note}.
    ok is True when gap_m ≤ tolerance. sta_calc/gap_m are None and ok is
    False when no matching control point was found (name mismatch, or the
    closest candidate exceeds max_sta_distance when that is set); note then
    explains why. note is '' for a normal matched row.
    max_sta_distance defaults to 10.0m (typical field/setting-out tolerance
    is at most a few metres; a genuine match should never be this far off by
    station -- 10m safely separates real deviations from name typos/mismatches
    that would otherwise land on an unrelated control point far away). Pass
    None to disable the ceiling entirely (restores pre-fix matching).
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
            report.append({
                'name':     d_name,
                'sta_calc': None,
                'sta_draw': d_sta,
                'gap_m':    None,
                'ok':       False,
                'note':     'ไม่พบจุดควบคุมที่ชื่อตรงกัน',
            })
            continue
        if max_sta_distance is not None and best_d > max_sta_distance:
            report.append({
                'name':     d_name or best.name,
                'sta_calc': None,
                'sta_draw': d_sta,
                'gap_m':    None,
                'ok':       False,
                'note': (
                    f'จุดควบคุมที่ใกล้สุด ({best.name}) ห่างตามสถานี '
                    f'{best_d:.3f} ม. เกินเพดาน {max_sta_distance:.3f} ม.'
                ),
            })
            continue
        gap = math.hypot(best.n - float(d['n']), best.e - float(d['e']))
        report.append({
            'name':     d_name or best.name,
            'sta_calc': best.sta,
            'sta_draw': d_sta,
            'gap_m':    gap,
            'ok':       gap <= tolerance,
            'note':     '',
        })
    return report
