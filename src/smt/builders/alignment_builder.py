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
