"""Verify session_logs/review_src_smt_20260802.md bug #2:
build_alignment_from_pi does not check that curve_start (TS/PC) lies AHEAD of
the previous curve's exit point along az_in -- when two adjacent PIs have R/Ls
too large for the tangent between them, tan_len (calculate_distance_2d) still
comes out positive (unsigned distance), silently producing a backward-facing
tangent element and a station/chain discontinuity with NO issue reported.

Run: python session_logs/tmp_verify_bug2_curve_overlap.py
"""
import math

from smt.builders.alignment_builder import build_alignment_from_pi

# BP -> PI1 -> PI2 -> EP, both PIs have large R with tight tangent legs so the
# two curves are geometrically forced to overlap.
vertices = [
    {'n': 0.0,   'e': 0.0,   'sta': 0.0},          # BP
    {'n': 200.0, 'e': 0.0,   'R': 500.0},           # PI1
    {'n': 250.0, 'e': 80.0,  'R': 500.0},           # PI2 -- close to PI1
    {'n': 400.0, 'e': 150.0},                       # EP
]

result = build_alignment_from_pi(vertices)

print('=== issues reported by build_alignment_from_pi ===')
if not result.issues:
    print('(none)')
else:
    for i in result.issues:
        print(' -', i)

print()
print('=== control points ===')
for c in result.control:
    print(f'{c.name:>4s}  sta={c.sta:10.3f}  n={c.n:10.3f}  e={c.e:10.3f}')

print()
print('=== elements (kind, sta_start, sta_end, len) ===')
for el in result.elements:
    length = el.sta_end - el.sta_start
    flag = '  <-- NEGATIVE LENGTH (station runs backward)' if length < 0 else ''
    print(f'{el.type:>5s}  sta_start={el.sta_start:10.3f}  sta_end={el.sta_end:10.3f}  len={length:8.3f}{flag}')

print()
print('=== station continuity check (chain discontinuity) ===')
# NOTE: station accumulates additively (sta_cs = prev_sta + tan_len, always
# >= prev_sta since tan_len is an unsigned distance), so this check is
# expected to find NO gap even when the bug is present -- the chain stays
# "continuous" in station terms while folding back on itself in real N/E
# space. Kept only as a secondary signal. Primary evidence is (a) issues
# empty + (c) dot product negative below.
prev_end = None
found_gap = False
for el in result.elements:
    if prev_end is not None and abs(el.sta_start - prev_end) > 1e-9:
        found_gap = True
        print(f'  GAP/OVERLAP detected: element {el.kind} starts at sta={el.sta_start:.3f} '
              f'but previous element ended at sta={prev_end:.3f} '
              f'(discontinuity = {el.sta_start - prev_end:.3f} m)')
    prev_end = el.sta_end
if not found_gap:
    print('  (no station-domain gap found -- expected even if the bug is present, '
          'see NOTE above. Real evidence is the dot-product sign check below.)')

print()
print('=== manual re-derivation of tan_len / dot product for PI2 curve start ===')
# Reproduce the internal computation for PI2 by hand to confirm tan_len > 0
# even though curve_start for PI2 lies BEHIND the exit of PI1's own curve.
from smt import wcb, fpmath

az_in_pi2 = wcb.calculate_azimuth(200.0, 0.0, 250.0, 80.0)
az_out_pi2 = wcb.calculate_azimuth(250.0, 80.0, 400.0, 150.0)
delta_pi2 = fpmath.calculate_angle_diff(az_out_pi2, az_in_pi2)
print(f'PI2 az_in={fpmath.rad_to_deg(az_in_pi2):.4f} deg, az_out={fpmath.rad_to_deg(az_out_pi2):.4f} deg, '
      f'delta={fpmath.rad_to_deg(delta_pi2):.4f} deg')

# Both PI1 and PI2 are plain circular curves (no spiral), so both produce a
# 'PC'/'PT' pair. There are TWO 'PC' control points in the full list -- the
# first belongs to PI1, the second to PI2. Collect ALL occurrences explicitly
# and index into the second one, instead of breaking on the first match.
curve_start_matches = [
    (idx, c) for idx, c in enumerate(result.control) if c.name in ('PC', 'TS')
]
print(f'found {len(curve_start_matches)} curve-start control point(s) named PC/TS: '
      f'{[c.name + "@sta=" + f"{c.sta:.3f}" for _, c in curve_start_matches]}')

if len(curve_start_matches) < 2:
    print('  --> fewer than 2 curve-start points found; PI1 and/or PI2 fell back to '
          'angle-point (IP). Adjust test vertices (R/delta) and re-run.')
else:
    idx, pi2_curve_start = curve_start_matches[1]   # second occurrence = PI2's curve start
    prev_cp = result.control[idx - 1]
    dn = pi2_curve_start.n - prev_cp.n
    de = pi2_curve_start.e - prev_cp.e
    tan_len_unsigned = math.hypot(dn, de)
    dot = dn * math.cos(az_in_pi2) + de * math.sin(az_in_pi2)
    print(f'prev control point: {prev_cp.name} sta={prev_cp.sta:.3f}  n={prev_cp.n:.3f}  e={prev_cp.e:.3f}')
    print(f'PI2 curve_start control point: {pi2_curve_start.name} sta={pi2_curve_start.sta:.3f}  '
          f'n={pi2_curve_start.n:.3f}  e={pi2_curve_start.e:.3f}')
    print(f'tan_len (unsigned, what the code actually uses) = {tan_len_unsigned:.4f} m  (always >= 0)')
    print(f'dot product (curve_start - prev) . (cos az_in, sin az_in) = {dot:.4f}')
    if dot < 0:
        print('  --> NEGATIVE: curve_start is BEHIND prev along az_in => backward-facing '
              'tangent element, confirmed silent overlap. No issue was raised for this.')
    else:
        print('  --> positive: no overlap in this geometry, need to adjust test vertices.')
