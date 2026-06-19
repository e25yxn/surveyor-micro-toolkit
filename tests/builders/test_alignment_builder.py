"""Tests for smt.builders.alignment_builder.

Strategy
--------
Golden data (tests/golden/tables.json) stores the 30 elements and 31 control
points produced by the JS oracle (AllTests 45/45).  No PI vertex list is stored,
so PI positions are reconstructed here by intersecting the incoming and outgoing
tangent lines at each curve group:

    d1 = (ΔN·sin(az_out) − ΔE·cos(az_out)) / sin(az_out − az_in)
    PI = TS + d1 · unit(az_in)

where TS/ST come from the golden controls and az_in/az_out from the golden elements.
The resulting PI positions have ~1e-4 m precision (limited by 4-decimal rounding in
the stored N, E values), so element tolerances use:
  - type / trans  : exact match
  - N, E          : abs_tol ≤ 1e-3 m  (control points)  / 2e-3 m  (element entry)
  - station       : abs_tol ≤ 5e-3 m  (accumulated tangent-length error across 9 PIs)
  - azimuth       : abs_tol ≤ 1e-4 rad
"""
import json
import math
from pathlib import Path

import pytest

from smt import alignment as al
from smt.builders import alignment_builder as ab

_GOLDEN = Path(__file__).parent.parent / 'golden' / 'tables.json'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def golden():
    with _GOLDEN.open(encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def golden_elements(golden):
    return al.parse_alignment_table(golden['elements'])


@pytest.fixture(scope='module')
def golden_controls(golden):
    return golden['controls']          # list of {'name', 'sta', 'n', 'e'}


# ---------------------------------------------------------------------------
# PI reconstruction helpers
# ---------------------------------------------------------------------------

def _tangent_intersection(n1, e1, az1, n2, e2, az2):
    """PI from tangent line (n1,e1,→az1) ∩ backward ray from (n2,e2,→az2)."""
    det = math.sin(az2 - az1)
    dn, de = n2 - n1, e2 - e1
    t = (dn * math.sin(az2) - de * math.cos(az2)) / det
    return n1 + t * math.cos(az1), e1 + t * math.sin(az1)


def _make_vertices(elements, controls):
    """Reconstruct the PI vertex list from golden elements and controls.

    For each of the 9 curve groups the PI position is computed as the
    intersection of the entry and exit tangent lines.  Curve parameters
    (R, Ls, trans, compound) are hard-coded from the golden element analysis.
    """
    bp = controls[0]
    ep = controls[-1]

    # (ts_ctrl_idx, st_ctrl_idx, az_in_el_idx, az_out_el_idx, extra_params)
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
        az_in  = elements[az_in_i].az      # radians
        az_out = elements[az_out_i].az
        pi_n, pi_e = _tangent_intersection(
            ts['n'], ts['e'], az_in,
            st['n'], st['e'], az_out,
        )
        vert = {'n': pi_n, 'e': pi_e}
        vert.update(params)
        vertices.append(vert)

    vertices.append({'n': ep['n'], 'e': ep['e']})
    return vertices


@pytest.fixture(scope='module')
def vertices(golden_elements, golden_controls):
    return _make_vertices(golden_elements, golden_controls)


@pytest.fixture(scope='module')
def result(vertices):
    return ab.build_alignment_from_pi(vertices)


# ---------------------------------------------------------------------------
# Test 1: unit tests — simple known geometries
# ---------------------------------------------------------------------------

class TestSimpleAlignments:
    """Small hand-verifiable alignments."""

    def test_two_vertices_gives_one_tangent(self):
        verts = [
            {'n': 0.0, 'e': 0.0, 'sta': 0.0},
            {'n': 0.0, 'e': 1000.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        assert len(r.elements) == 1
        assert r.elements[0].type == 'T'
        assert math.isclose(r.elements[0].sta_end, 1000.0, abs_tol=1e-9)

    def test_two_vertices_control_points(self):
        verts = [
            {'n': 0.0, 'e': 0.0, 'sta': 0.0},
            {'n': 0.0, 'e': 1000.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        assert len(r.control) == 2
        assert r.control[0].name == 'BP'
        assert r.control[1].name == 'EP'

    def test_simple_circle_element_count(self):
        # BP → (north 200m) → PI(200,0) → R=50 right turn → EP(200,500)
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 200.0, 'e': 0.0,   'R': 50},
            {'n': 200.0, 'e': 500.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        assert len(r.elements) == 3        # T, C, T
        assert [el.type for el in r.elements] == ['T', 'C', 'T']

    def test_simple_circle_control_names(self):
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 200.0, 'e': 0.0,   'R': 50},
            {'n': 200.0, 'e': 500.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        names = [c.name for c in r.control]
        assert names == ['BP', 'PC', 'PT', 'EP']

    def test_simple_circle_pc_position(self):
        # T = R·tan(δ/2) = 50·tan(45°) = 50 m
        # PC = PI − T·unit(az_in=0°) = (200,0) − 50·(1,0) = (150, 0)
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 200.0, 'e': 0.0,   'R': 50},
            {'n': 200.0, 'e': 500.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        pc = r.control[1]
        assert math.isclose(pc.n, 150.0, abs_tol=1e-6)
        assert math.isclose(pc.e, 0.0,   abs_tol=1e-6)

    def test_simple_circle_pt_position(self):
        # PT = PI + T·unit(az_out=90°) = (200,0) + 50·(0,1) = (200, 50)
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 200.0, 'e': 0.0,   'R': 50},
            {'n': 200.0, 'e': 500.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        pt = r.control[2]
        assert math.isclose(pt.n, 200.0, abs_tol=1e-6)
        assert math.isclose(pt.e, 50.0,  abs_tol=1e-6)

    def test_simple_circle_arc_length(self):
        # arc = R·π/2 = 50·π/2 = 78.5398...
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 200.0, 'e': 0.0,   'R': 50},
            {'n': 200.0, 'e': 500.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        arc_el = r.elements[1]
        arc_len = arc_el.sta_end - arc_el.sta_start
        assert math.isclose(arc_len, 50 * math.pi / 2, abs_tol=1e-6)

    def test_simple_circle_right_turn_sign(self):
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 200.0, 'e': 0.0,   'R': 50},
            {'n': 200.0, 'e': 500.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        arc_el = r.elements[1]
        assert arc_el.k_in > 0    # right turn → positive curvature

    def test_left_turn_negative_curvature(self):
        # BP=(0,0) heading east (az=90°), PI=(0,200), turn left 90° → EP=(200,200) heading north (az=0°)
        # delta = angle_diff(0°, 90°) = -90° → sgn=-1 → k<0
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 0.0,   'e': 200.0, 'R': 50},
            {'n': 200.0, 'e': 200.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        arc_el = r.elements[1]
        assert arc_el.k_in < 0    # left turn → negative curvature

    def test_no_issues_clean_geometry(self):
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 200.0, 'e': 0.0,   'R': 50},
            {'n': 200.0, 'e': 500.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        assert r.issues == []

    def test_spiral_element_types(self):
        # BP→north, PI right turn 40° with R=400 Ls=60 CLOTHOID, EP
        # az_in=0° (north), az_out=40°
        # PI at intersection of N-axis from origin and az=40° from far point
        # Use (0,0)→(500,0) as BP→PI direction (az=0°), PI=(500,0)
        # EP is in direction az_out=40° from PI
        az_out_rad = math.radians(40)
        verts = [
            {'n': 0.0,                   'e': 0.0,   'sta': 0.0},
            {'n': 500.0,                 'e': 0.0,   'R': 400, 'Ls': 60, 'trans': 'CLOTHOID'},
            {'n': 500 + 500*math.cos(az_out_rad), 'e': 500*math.sin(az_out_rad)},
        ]
        r = ab.build_alignment_from_pi(verts)
        types = [el.type for el in r.elements]
        assert types == ['T', 'SPIN', 'C', 'SPOUT', 'T']

    def test_spiral_control_names(self):
        az_out_rad = math.radians(40)
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 500.0, 'e': 0.0,   'R': 400, 'Ls': 60, 'trans': 'CLOTHOID'},
            {'n': 500 + 500*math.cos(az_out_rad), 'e': 500*math.sin(az_out_rad)},
        ]
        r = ab.build_alignment_from_pi(verts)
        names = [c.name for c in r.control]
        assert names == ['BP', 'TS', 'SC', 'CS', 'ST', 'EP']

    def test_compound_element_types(self):
        # compound: two circular arcs (20° + 30° = 50°)
        az_out_rad = math.radians(50)
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 500.0, 'e': 0.0,   'compound': [{'R': 300, 'delta': 20}, {'R': 150}]},
            {'n': 500 + 500*math.cos(az_out_rad), 'e': 500*math.sin(az_out_rad)},
        ]
        r = ab.build_alignment_from_pi(verts)
        types = [el.type for el in r.elements]
        assert types == ['T', 'C', 'C', 'T']

    def test_compound_control_pcc(self):
        az_out_rad = math.radians(50)
        verts = [
            {'n': 0.0,   'e': 0.0,   'sta': 0.0},
            {'n': 500.0, 'e': 0.0,   'compound': [{'R': 300, 'delta': 20}, {'R': 150}]},
            {'n': 500 + 500*math.cos(az_out_rad), 'e': 500*math.sin(az_out_rad)},
        ]
        r = ab.build_alignment_from_pi(verts)
        names = [c.name for c in r.control]
        assert 'PCC' in names

    def test_starting_station_propagates(self):
        verts = [
            {'n': 0.0, 'e': 0.0, 'sta': 500.0},
            {'n': 0.0, 'e': 1000.0},
        ]
        r = ab.build_alignment_from_pi(verts)
        assert math.isclose(r.control[0].sta, 500.0, abs_tol=1e-9)
        assert math.isclose(r.elements[0].sta_start, 500.0, abs_tol=1e-9)
        assert math.isclose(r.elements[0].sta_end, 1500.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 2: golden data — structural checks
# ---------------------------------------------------------------------------

class TestGoldenStructure:
    def test_element_count(self, result):
        assert len(result.elements) == 30

    def test_control_count(self, result):
        assert len(result.control) == 31

    def test_no_issues(self, result):
        assert result.issues == []

    def test_element_types_match(self, result, golden_elements):
        built_types  = [el.type  for el in result.elements]
        golden_types = [el.type  for el in golden_elements]
        assert built_types == golden_types

    def test_spiral_trans_match(self, result, golden_elements):
        for i, (b_el, g_el) in enumerate(zip(result.elements, golden_elements)):
            if b_el.type in ('SPIN', 'SPOUT'):
                assert b_el.trans == g_el.trans, (
                    f'element[{i}] trans mismatch: built={b_el.trans!r} golden={g_el.trans!r}'
                )

    def test_control_names_match(self, result, golden_controls):
        built_names  = [c.name  for c in result.control]
        golden_names = [c['name'] for c in golden_controls]
        assert built_names == golden_names


# ---------------------------------------------------------------------------
# Test 3: golden data — element geometry
# ---------------------------------------------------------------------------

class TestGoldenElementGeometry:

    def test_element_ne_within_tolerance(self, result, golden_elements):
        for i, (b, g) in enumerate(zip(result.elements, golden_elements)):
            assert math.isclose(b.n, g.n, abs_tol=2e-3), (
                f'element[{i}] N: built={b.n:.6f} golden={g.n:.6f}'
            )
            assert math.isclose(b.e, g.e, abs_tol=2e-3), (
                f'element[{i}] E: built={b.e:.6f} golden={g.e:.6f}'
            )

    def test_element_azimuth_within_tolerance(self, result, golden_elements):
        for i, (b, g) in enumerate(zip(result.elements, golden_elements)):
            az_diff = abs(b.az - g.az)
            # handle wrap-around (should not occur here but guard it)
            az_diff = min(az_diff, 2 * math.pi - az_diff)
            assert az_diff <= 1e-4, (
                f'element[{i}] az: built={math.degrees(b.az):.6f}° golden={math.degrees(g.az):.6f}°'
            )

    def test_element_curvature_correct(self, result, golden_elements):
        for i, (b, g) in enumerate(zip(result.elements, golden_elements)):
            assert math.isclose(b.k_in,  g.k_in,  abs_tol=1e-9), f'k_in  mismatch el[{i}]'
            assert math.isclose(b.k_out, g.k_out, abs_tol=1e-9), f'k_out mismatch el[{i}]'

    def test_element_stations_within_tolerance(self, result, golden_elements):
        # Station values accumulate tangent-length errors across 9 PI groups.
        # Tolerance is 5 mm to accommodate this accumulation.
        for i, (b, g) in enumerate(zip(result.elements, golden_elements)):
            assert math.isclose(b.sta_start, g.sta_start, abs_tol=5e-3), (
                f'element[{i}] sta_start: built={b.sta_start:.6f} golden={g.sta_start:.6f}'
            )
            assert math.isclose(b.sta_end, g.sta_end, abs_tol=5e-3), (
                f'element[{i}] sta_end: built={b.sta_end:.6f} golden={g.sta_end:.6f}'
            )


# ---------------------------------------------------------------------------
# Test 4: golden data — control points
# ---------------------------------------------------------------------------

class TestGoldenControlPoints:

    def test_control_ne_within_1mm(self, result, golden_controls):
        for i, (c, g) in enumerate(zip(result.control, golden_controls)):
            assert math.isclose(c.n, g['n'], abs_tol=1e-3), (
                f'control[{i}] ({c.name}) N: built={c.n:.4f} golden={g["n"]:.4f}'
            )
            assert math.isclose(c.e, g['e'], abs_tol=1e-3), (
                f'control[{i}] ({c.name}) E: built={c.e:.4f} golden={g["e"]:.4f}'
            )

    def test_bp_exact(self, result, golden_controls):
        bp = result.control[0]
        assert bp.name == 'BP'
        assert math.isclose(bp.n, golden_controls[0]['n'], abs_tol=1e-9)
        assert math.isclose(bp.e, golden_controls[0]['e'], abs_tol=1e-9)
        assert math.isclose(bp.sta, 0.0, abs_tol=1e-9)

    def test_ep_ne_exact(self, result, golden_controls):
        # EP coordinates come directly from the input vertex — must be exact.
        ep = result.control[-1]
        g_ep = golden_controls[-1]
        assert math.isclose(ep.n, g_ep['n'], abs_tol=1e-9)
        assert math.isclose(ep.e, g_ep['e'], abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 5: check_against_drawing
# ---------------------------------------------------------------------------

class TestCheckAgainstDrawing:

    def test_all_controls_pass_1mm_tolerance(self, result, golden_controls):
        drawing = golden_controls   # list of {'name', 'sta', 'n', 'e'}
        report = ab.check_against_drawing(result.control, drawing, tolerance=1e-3)
        failures = [r for r in report if not r['ok']]
        assert failures == [], (
            f'{len(failures)} control point(s) exceed 1 mm gap:\n'
            + '\n'.join(f"  {r['name']} gap={r['gap_m']*1000:.2f} mm" for r in failures)
        )

    def test_report_length_matches_drawing(self, result, golden_controls):
        report = ab.check_against_drawing(result.control, golden_controls, tolerance=0.1)
        assert len(report) == len(golden_controls)

    def test_report_has_required_keys(self, result, golden_controls):
        report = ab.check_against_drawing(result.control, golden_controls[:1], tolerance=0.1)
        assert 'name'     in report[0]
        assert 'sta_calc' in report[0]
        assert 'sta_draw' in report[0]
        assert 'gap_m'    in report[0]
        assert 'ok'       in report[0]

    def test_ok_flag_reflects_tolerance(self, result):
        # Tight tolerance → might fail; loose tolerance → all pass.
        drawing = [{'name': 'BP', 'sta': 0.0, 'n': 20000.0, 'e': 10000.0}]
        r_tight = ab.check_against_drawing(result.control, drawing, tolerance=0.0)
        r_loose = ab.check_against_drawing(result.control, drawing, tolerance=1.0)
        assert r_loose[0]['ok'] is True
        # tight tolerance on exact BP should still be true (gap == 0)
        assert math.isclose(r_tight[0]['gap_m'], 0.0, abs_tol=1e-9)

    def test_name_filter_selects_correct_point(self, result):
        # Only TS (first one at sta ≈ 1020) should be matched by name
        drawing = [{'name': 'TS', 'sta': 1020.0, 'n': 19787.8595, 'e': 10967.4379}]
        report = ab.check_against_drawing(result.control, drawing, tolerance=1e-3)
        assert len(report) == 1
        assert report[0]['name'] == 'TS'
        assert report[0]['ok'] is True

    def test_unnamed_entry_matches_nearest_station(self, result, golden_controls):
        # Without a name, the entry with sta=0 should match BP (nearest station 0).
        bp = golden_controls[0]
        drawing = [{'name': '', 'sta': bp['sta'], 'n': bp['n'], 'e': bp['e']}]
        report = ab.check_against_drawing(result.control, drawing, tolerance=0.01)
        assert report[0]['ok'] is True

    def test_empty_drawing_gives_empty_report(self, result):
        report = ab.check_against_drawing(result.control, [], tolerance=0.05)
        assert report == []


# ---------------------------------------------------------------------------
# Test 6: chain continuity (exit of element[i] == entry of element[i+1])
# ---------------------------------------------------------------------------

class TestChainContinuity:

    def test_chain_is_continuous(self, result):
        from smt.alignment import calculate_exit_state
        elements = result.elements
        for i in range(len(elements) - 1):
            ex = calculate_exit_state(elements[i])
            nxt = elements[i + 1]
            assert math.isclose(ex.n, nxt.n, abs_tol=1e-9), (
                f'Chain break N at boundary {i}→{i+1}: {ex.n:.9f} vs {nxt.n:.9f}'
            )
            assert math.isclose(ex.e, nxt.e, abs_tol=1e-9), (
                f'Chain break E at boundary {i}→{i+1}: {ex.e:.9f} vs {nxt.e:.9f}'
            )
