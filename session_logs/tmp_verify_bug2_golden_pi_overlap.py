"""Plan step (session_logs/plan_20260804_2014.md, section 5): before touching
build_alignment_from_pi for bug #2, check whether the golden PI-table fixture
used by TestBuildFromGoldenPI (tests/builders/test_alignment_builder.py:77-85,
reconstructed from tests/golden/tables.json, 9 real curve groups: R=300, 400,
400, 500, 500, 400, compound 300/150, R=50, R=40) would trip the new
tan_len_signed < 0 check unintentionally.

This mirrors the internal loop of build_alignment_from_pi using the module's
own private helpers (_build_curve_sub_elements, _calculate_end_displacement)
so the math is not re-derived by hand -- it reuses the real, current
implementation exactly, then adds the proposed tan_len_signed dot-product
check as a side computation, without modifying alignment_builder.py.

Run: python session_logs/tmp_verify_bug2_golden_pi_overlap.py
"""
import json
import math
from pathlib import Path

from smt import fpmath, wcb
from smt.builders import alignment_builder as ab

_GOLDEN = Path(__file__).parent.parent / 'tests' / 'golden' / 'tables.json'


def _tangent_intersection(n1, e1, az1, n2, e2, az2):
    det = math.sin(az2 - az1)
    dn, de = n2 - n1, e2 - e1
    t = (dn * math.sin(az2) - de * math.cos(az2)) / det
    return n1 + t * math.cos(az1), e1 + t * math.sin(az1)


def _make_vertices(elements, controls):
    bp = controls[0]
    ep = controls[-1]
    groups = [
        (1,  2,   0,  2,  {'R': 300}),
        (3,  6,   2,  6,  {'R': 400, 'Ls': 60,  'trans': 'CLOTHOID'}),
        (7,  10,  6,  10, {'R': 400, 'Ls': 60,  'trans': 'BLOSS'}),
        (11, 14,  10, 14, {'R': 500, 'Ls': 70,  'trans': 'COSINE'}),
        (15, 18,  14, 18, {'R': 500, 'Ls': 70,  'trans': 'SINE'}),
        (19, 22,  18, 22, {'R': 400, 'LsIn': 50, 'LsOut': 90, 'trans': 'CLOTHOID'}),
        (23, 25,  22, 25, {'compound': [{'R': 300, 'delta': 20}, {'R': 150}]}),
        (26, 27,  25, 27, {'R': 50}),
        (28, 29,  27, 29, {'R': 40}),
    ]
    vertices = [{'n': bp['n'], 'e': bp['e'], 'sta': bp['sta']}]
    for ts_i, st_i, az_in_i, az_out_i, params in groups:
        ts = controls[ts_i]
        st = controls[st_i]
        az_in = elements[az_in_i].azimuth
        az_out = elements[az_out_i].azimuth
        pi_n, pi_e = _tangent_intersection(ts['n'], ts['e'], az_in, st['n'], st['e'], az_out)
        vert = {'n': pi_n, 'e': pi_e}
        vert.update(params)
        vertices.append(vert)
    vertices.append({'n': ep['n'], 'e': ep['e']})
    return vertices


with _GOLDEN.open(encoding='utf-8') as f:
    golden = json.load(f)

from smt import alignment as al
golden_elements = al.parse_alignment_table(golden['elements'])
golden_controls = golden['controls']

vertices = _make_vertices(golden_elements, golden_controls)

print(f'=== reconstructed {len(vertices)} vertices (BP + 9 PI + EP) ===')
for i, v in enumerate(vertices):
    print(f'  [{i}] {v}')

print()
print('=== replaying build_alignment_from_pi internal loop, computing tan_len_signed per PI ===')

N = len(vertices)
prev_n = float(vertices[0]['n'])
prev_e = float(vertices[0]['e'])
prev_sta = float(vertices[0].get('sta', 0.0))

any_negative = False

for v in range(1, N - 1):
    vertex_n = float(vertices[v]['n'])
    vertex_e = float(vertices[v]['e'])

    azimuth_in = wcb.calculate_azimuth(
        float(vertices[v - 1]['n']), float(vertices[v - 1]['e']), vertex_n, vertex_e
    )
    azimuth_out = wcb.calculate_azimuth(
        vertex_n, vertex_e, float(vertices[v + 1]['n']), float(vertices[v + 1]['e'])
    )
    delta = fpmath.calculate_angle_diff(azimuth_out, azimuth_in)
    sign = 1.0 if delta >= 0 else -1.0
    abs_delta = abs(delta)

    subs, issue = ab._build_curve_sub_elements(vertices[v], abs_delta)
    if issue:
        print(f'  PI#{v}: _build_curve_sub_elements issue: {issue}')

    if not subs:
        # angle-point path -- no curve_start, no tan_len_signed check applies
        tan_len = wcb.calculate_distance_2d(prev_n, prev_e, vertex_n, vertex_e)
        sta_pi = prev_sta + tan_len
        print(f'  PI#{v}: angle-point (no curve) -- skipped from overlap check, tan_len={tan_len:.4f}')
        prev_n, prev_e, prev_sta = vertex_n, vertex_e, sta_pi
        continue

    v_n, v_e = ab._calculate_end_displacement(subs, azimuth_in, sign)
    det = math.sin(delta)
    d1 = (v_n * math.sin(azimuth_out) - v_e * math.cos(azimuth_out)) / det

    curve_start_n = vertex_n - d1 * math.cos(azimuth_in)
    curve_start_e = vertex_e - d1 * math.sin(azimuth_in)

    tan_len = wcb.calculate_distance_2d(prev_n, prev_e, curve_start_n, curve_start_e)

    dn = curve_start_n - prev_n
    de = curve_start_e - prev_e
    tan_len_signed = dn * math.cos(azimuth_in) + de * math.sin(azimuth_in)

    prev_label = 'BP' if v == 1 else f'PI#{v - 1}'
    flag = '  <-- NEGATIVE (would trigger new issue)' if tan_len_signed < 0 else ''
    if tan_len_signed < 0:
        any_negative = True
    print(f'  PI#{v}: prev={prev_label:<6s} tan_len(unsigned)={tan_len:10.4f}  '
          f'tan_len_signed={tan_len_signed:10.4f}{flag}')

    # propagate forward exactly like build_alignment_from_pi does
    cur_n, cur_e, cur_az = curve_start_n, curve_start_e, azimuth_in
    sta = prev_sta + tan_len
    for s in subs:
        el = ab.make_element(
            s['kind'], sta, sta + s['len'], cur_n, cur_e,
            fpmath.rad_to_deg(cur_az), sign * s['R'], None, s.get('trans'),
        )
        state = ab.calculate_exit_state(el)
        cur_n, cur_e, cur_az = state.n, state.e, state.azimuth
        sta += s['len']
    prev_n, prev_e, prev_sta = cur_n, cur_e, sta

print()
if any_negative:
    print('RESULT: at least one PI in the golden fixture has tan_len_signed < 0 -- '
          'the new check WOULD add an unexpected issue to this fixture. Must decide '
          'before implementing (see plan section 5).')
else:
    print('RESULT: no negative tan_len_signed found in the golden fixture -- '
          'the new check would NOT add any new issue here. test_no_issues should '
          'remain unaffected.')

print()
print('=== sanity check: does build_alignment_from_pi (current, unmodified) report any issues today? ===')
real_result = ab.build_alignment_from_pi(vertices)
print(f'issues = {real_result.issues!r}')
