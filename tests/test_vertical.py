"""Golden tests for smt.vertical.

Fixtures loaded from tests/golden/tables.json (7-segment vertical profile, 11 vchecks).

vchecks semantics:
  BVP / PVC / PVT / EVP : elevation ON the parabola (or tangent grade).
                           → verified with calculate_elevation(segs, sta).
  PVI                    : elevation at the Vertical Point of Intersection,
                           i.e. the tangent-grade height where G1 meets G2.
                           → NOT the parabolic level; verified as
                             seg.level + (g1/100) * (pvi_sta - seg.sta_start).
"""
import json
import math
from pathlib import Path

import pytest

from smt import vertical as vt

_GOLDEN = Path(__file__).parent / 'golden' / 'tables.json'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def golden():
    with _GOLDEN.open(encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def segs(golden):
    return vt.parse_vertical_table(golden['vtable'])


# ---------------------------------------------------------------------------
# Test 1: parse sanity
# ---------------------------------------------------------------------------

def test_parse_produces_seven_segments(segs):
    assert len(segs) == 7


def test_parse_first_segment(segs):
    s = segs[0]
    assert s.sta_start == 0
    assert s.sta_end == 1100
    assert s.level == 100
    assert s.grade_in == 1.5
    assert s.lvc == 0
    assert s.lvc2 is None


def test_parse_asymmetric_segment(segs):
    # segment [2700, 3000] — asymmetric VC with L1=100, L2=200
    s = next(x for x in segs if x.sta_start == 2700)
    assert s.lvc == 100
    assert s.lvc2 == 200


# ---------------------------------------------------------------------------
# Test 2: vchecks — BVP / PVC / PVT / EVP (parabola / tangent grade)
# ---------------------------------------------------------------------------

def _parabola_checks(golden_data):
    return [
        pytest.param(cp['sta'], cp['elev'], id=f"{cp['name']}@{cp['sta']}")
        for cp in golden_data['vchecks']
        if cp['name'] != 'PVI'
    ]


def test_vcheck_parabola_all(segs, golden):
    """All non-PVI vchecks must match calculate_elevation within 1e-3 m."""
    tol = 1e-3
    failures = []
    for cp in golden['vchecks']:
        if cp['name'] == 'PVI':
            continue
        elev = vt.calculate_elevation(segs, cp['sta'])
        if elev is None or abs(elev - cp['elev']) > tol:
            failures.append(
                f"{cp['name']}@{cp['sta']}: "
                f"got {elev} expected {cp['elev']}"
            )
    assert not failures, 'Elevation failures:\n' + '\n'.join(failures)


@pytest.mark.parametrize(
    'sta,exp_elev',
    [
        (cp['sta'], cp['elev'])
        for cp in json.loads(_GOLDEN.read_text(encoding='utf-8'))['vchecks']
        if cp['name'] != 'PVI'
    ],
    ids=[
        f"{cp['name']}@{cp['sta']}"
        for cp in json.loads(_GOLDEN.read_text(encoding='utf-8'))['vchecks']
        if cp['name'] != 'PVI'
    ],
)
def test_vcheck_parabola_parametrized(segs, sta, exp_elev):
    elev = vt.calculate_elevation(segs, sta)
    assert elev is not None, f'station {sta} not found in profile'
    assert abs(elev - exp_elev) <= 1e-3, f'got {elev:.6f} expected {exp_elev}'


# ---------------------------------------------------------------------------
# Test 3: vchecks — PVI (grade-intersection elevation, not parabola)
# ---------------------------------------------------------------------------

def _find_seg(segs, sta):
    """Return the segment covering sta (same logic as calculate_elevation)."""
    for i, seg in enumerate(segs):
        last = i == len(segs) - 1
        if sta >= seg.sta_start and (sta < seg.sta_end or (last and sta <= seg.sta_end)):
            return seg
    return None


@pytest.mark.parametrize(
    'sta,exp_elev',
    [
        (cp['sta'], cp['elev'])
        for cp in json.loads(_GOLDEN.read_text(encoding='utf-8'))['vchecks']
        if cp['name'] == 'PVI'
    ],
    ids=[
        f"PVI@{cp['sta']}"
        for cp in json.loads(_GOLDEN.read_text(encoding='utf-8'))['vchecks']
        if cp['name'] == 'PVI'
    ],
)
def test_vcheck_pvi_tangent_grade(segs, sta, exp_elev):
    """PVI elevation in vchecks is the tangent-grade intersection height (G1 from PVC)."""
    seg = _find_seg(segs, sta)
    assert seg is not None, f'VPI station {sta} not found in any segment'
    tangent_elev = seg.level + (seg.grade_in / 100.0) * (sta - seg.sta_start)
    assert abs(tangent_elev - exp_elev) <= 1e-3, (
        f'PVI@{sta}: tangent elev {tangent_elev:.6f} expected {exp_elev}'
    )


# ---------------------------------------------------------------------------
# Test 4: calculate_elevation returns None outside all segments
# ---------------------------------------------------------------------------

def test_elevation_outside_returns_none(segs):
    assert vt.calculate_elevation(segs, -1.0) is None
    assert vt.calculate_elevation(segs, 99999.0) is None


# ---------------------------------------------------------------------------
# Test 5: grade at segment boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('idx', [1, 3, 5])   # indices of VC segments in segs list
def test_grade_at_pvc_equals_g1(segs, idx):
    seg = segs[idx]
    grade = vt.calculate_grade_at(seg, seg.sta_start)
    assert math.isclose(grade, seg.grade_in, abs_tol=1e-9)


@pytest.mark.parametrize('idx', [1, 3, 5])
def test_grade_at_pvt_equals_g2(segs, idx):
    seg = segs[idx]
    grade = vt.calculate_grade_at(seg, seg.sta_end)
    assert math.isclose(grade, seg.grade_out, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 6: tangent-grade segment (lvc=0) is a straight line
# ---------------------------------------------------------------------------

def test_tangent_grade_is_linear(segs):
    seg = segs[0]                          # [0, 1100], g1=g2=1.5, lvc=0
    for sta in [0, 100, 550, 1099.9]:
        elev = vt.calculate_elevation_at(seg, sta)
        expected = 100.0 + 1.5 / 100.0 * sta
        assert math.isclose(elev, expected, abs_tol=1e-9), (
            f'sta={sta}: got {elev} expected {expected}'
        )


# ---------------------------------------------------------------------------
# Test 7: symmetric VC — known values
# ---------------------------------------------------------------------------

def test_symmetric_vc_pvc(segs):
    seg = segs[1]   # [1100, 1300], lvc=200
    assert math.isclose(vt.calculate_elevation_at(seg, 1100), 116.5, abs_tol=1e-9)


def test_symmetric_vc_pvt(segs):
    seg = segs[1]
    assert math.isclose(vt.calculate_elevation_at(seg, 1300), 116.875, abs_tol=1e-9)


def test_symmetric_vc_midpoint(segs):
    """Mid-point of symmetric VC: level = (PVC_grade + PVT_grade)/2 projected, plus sag/crest."""
    seg = segs[1]   # crest: g1=1.5, g2=-1.125, L=200, PVC_level=116.5
    # Lx=100: base=118.0, correction=(-2.625/40000)*10000=-0.65625
    expected = 118.0 - 0.65625
    assert math.isclose(vt.calculate_elevation_at(seg, 1200), expected, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 8: asymmetric VC — known values
# ---------------------------------------------------------------------------

def test_asymmetric_vc_pvc(segs):
    seg = segs[3]   # [2700, 3000], L1=100, L2=200
    assert math.isclose(vt.calculate_elevation_at(seg, 2700), 101.125, abs_tol=1e-9)


def test_asymmetric_vc_at_pvi_station(segs):
    """At the VPI station (Lx=L1), arm-1 and arm-2 formulas must agree."""
    seg = segs[3]
    lev_arm1 = vt.calculate_elevation_at(seg, 2800)   # Lx=100 = L1, arm-1 boundary
    # arm-2 check: Lx=100+eps (numerically equiv at boundary)
    lev_via_arm2 = vt.calculate_elevation_at(seg, 2800 + 1e-9)
    assert math.isclose(lev_arm1, lev_via_arm2, abs_tol=1e-6), (
        f'Arm continuity at VPI: arm1={lev_arm1} arm2={lev_via_arm2}'
    )


def test_asymmetric_vc_pvt(segs):
    seg = segs[3]
    assert math.isclose(vt.calculate_elevation_at(seg, 3000), 101.4118, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 9: grade continuity at segment boundaries
# ---------------------------------------------------------------------------

def test_grade_continuity_at_junctions(segs):
    """Exit grade of seg[n] must equal entry grade of seg[n+1]."""
    for i in range(len(segs) - 1):
        g_exit = vt.calculate_grade_at(segs[i], segs[i].sta_end)
        g_entry = segs[i + 1].grade_in
        assert math.isclose(g_exit, g_entry, abs_tol=1e-6), (
            f'Grade gap between seg {i} and {i+1}: '
            f'exit={g_exit:.6f} entry_g1={g_entry:.6f}'
        )


# ---------------------------------------------------------------------------
# Test 10: elevation continuity at segment boundaries
# ---------------------------------------------------------------------------

def test_elevation_continuity_at_junctions(segs):
    """Elevation at exit of seg[n] must match entry level of seg[n+1] within 1e-3 m.

    The stored segment levels are rounded to 4 decimal places, so machine-precision
    continuity is not guaranteed — 1 mm tolerance covers the rounding artefacts.
    """
    for i in range(len(segs) - 1):
        elev_exit = vt.calculate_elevation_at(segs[i], segs[i].sta_end)
        elev_entry = segs[i + 1].level
        assert abs(elev_exit - elev_entry) <= 1e-3, (
            f'Elevation gap between seg {i} and {i+1}: '
            f'exit={elev_exit:.6f} entry_level={elev_entry:.6f}'
        )


# ---------------------------------------------------------------------------
# Part 2 defensive edge-case tests
# ---------------------------------------------------------------------------

class TestDefensiveVertical:
    """Edge-case and error-path coverage for smt.vertical (Part 2)."""

    def test_grade_continuity_at_asymmetric_arm_boundary(self):
        """At the VPI station (lx=L1) both arm formulas must give the same grade."""
        # segs[3]: asymmetric VC [2700,3000], g1=-1.125%, g2≈0.706%, L1=100, L2=200
        seg = vt.VerticalSegment(
            sta_start=2700, sta_end=3000,
            level=101.125, grade_in=-1.125, grade_out=0.706,
            lvc=100, lvc2=200,
        )
        vpi_sta = 2800  # sta_start + L1
        g_before = vt.calculate_grade_at(seg, vpi_sta - 1e-6)   # arm-1
        g_after  = vt.calculate_grade_at(seg, vpi_sta + 1e-6)   # arm-2
        assert abs(g_before - g_after) < 1e-4, (
            f'Grade discontinuity at asymmetric arm boundary: '
            f'{g_before:.9f} vs {g_after:.9f}'
        )

    def test_elevation_empty_segs_returns_none(self):
        assert vt.calculate_elevation([], 0.0) is None
        assert vt.calculate_elevation([], 500.0) is None

    def test_parse_header_only_returns_empty(self):
        rows = [['index', 'sta_start', 'sta_end', 'level', 'g1', 'g2', 'lvc', 'lvc2']]
        assert vt.parse_vertical_table(rows) == []

    def test_parse_nan_sta_start_is_skipped(self):
        rows = [
            ['index', 'sta_start', 'sta_end', 'level', 'g1', 'g2', 'lvc', 'lvc2'],
            [1, math.nan, 1000, 100.0, 1.5, 1.5, 0, None],    # skipped
            [2, 0.0,       500, 100.0, 1.5, 1.5, 0, None],    # kept
        ]
        segs = vt.parse_vertical_table(rows)
        assert len(segs) == 1
        assert segs[0].sta_start == 0.0

    def test_parse_empty_lvc_cell_defaults_to_zero(self):
        rows = [
            ['index', 'sta_start', 'sta_end', 'level', 'g1', 'g2', 'lvc', 'lvc2'],
            [1, 0.0, 500.0, 100.0, 1.5, 1.5, '', None],
        ]
        segs = vt.parse_vertical_table(rows)
        assert len(segs) == 1
        assert segs[0].lvc == 0.0
        assert segs[0].lvc2 is None

    def test_parse_short_row_without_lvc2_column(self):
        # 7-element row (indices 0–6): len=7, NOT > 7 → lvc2_raw=None → lvc2=None
        rows = [
            ['index', 'sta_start', 'sta_end', 'level', 'g1', 'g2', 'lvc'],
            [1, 0.0, 500.0, 100.0, 1.5, 1.5, 200.0],
        ]
        segs = vt.parse_vertical_table(rows)
        assert len(segs) == 1
        assert segs[0].lvc == 200.0
        assert segs[0].lvc2 is None
