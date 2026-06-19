"""Golden tests for smt.crossfall.

Fixtures from tests/golden/tables.json keys "xLT" and "xRT".

xLT: 3 segments — [0,1000] N(-2.5), [1000,1060] S(-2.5→4), [1060,2000] N(4)
xRT: 1 segment  — [0,2000] N(-2.5)
"""
import json
import math
from pathlib import Path

import pytest

from smt import crossfall as cf

_GOLDEN = Path(__file__).parent / 'golden' / 'tables.json'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def golden():
    with _GOLDEN.open(encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def segs_lt(golden):
    return cf.parse_crossfall_table(golden['xLT'])


@pytest.fixture(scope='module')
def segs_rt(golden):
    return cf.parse_crossfall_table(golden['xRT'])


# ---------------------------------------------------------------------------
# Test 1: parse
# ---------------------------------------------------------------------------

def test_parse_xlt_produces_three_segments(segs_lt):
    assert len(segs_lt) == 3


def test_parse_xrt_produces_one_segment(segs_rt):
    assert len(segs_rt) == 1


def test_parse_xlt_first_segment(segs_lt):
    s = segs_lt[0]
    assert s.sta_start == 0
    assert s.sta_end == 1000
    assert s.x_start == -2.5
    assert s.x_end == -2.5
    assert s.type == 'N'


def test_parse_xlt_s_curve_segment(segs_lt):
    s = segs_lt[1]
    assert s.sta_start == 1000
    assert s.sta_end == 1060
    assert s.x_start == -2.5
    assert s.x_end == 4.0
    assert s.type == 'S'


def test_parse_xrt_single_segment(segs_rt):
    s = segs_rt[0]
    assert s.sta_start == 0
    assert s.sta_end == 2000
    assert s.x_start == -2.5
    assert s.x_end == -2.5
    assert s.type == 'N'


# ---------------------------------------------------------------------------
# Test 2: type N — constant regardless of station
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('sta', [0, 500, 999.9, 1000])
def test_type_n_is_constant_xlt_seg0(segs_lt, sta):
    assert math.isclose(cf.calculate_crossfall_at(segs_lt[0], sta), -2.5, abs_tol=1e-9)


def test_type_n_is_constant_xlt_seg2(segs_lt):
    for sta in [1060, 1500, 2000]:
        assert math.isclose(cf.calculate_crossfall_at(segs_lt[2], sta), 4.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 3: type S — smoothstep interpolation
# ---------------------------------------------------------------------------

def test_s_curve_at_start(segs_lt):
    seg = segs_lt[1]                       # [1000, 1060]
    assert math.isclose(cf.calculate_crossfall_at(seg, 1000), -2.5, abs_tol=1e-9)


def test_s_curve_at_end(segs_lt):
    seg = segs_lt[1]
    assert math.isclose(cf.calculate_crossfall_at(seg, 1060), 4.0, abs_tol=1e-9)


def test_s_curve_at_midpoint(segs_lt):
    # t=0.5: f = 3*0.25-2*0.125 = 0.5  →  -2.5 + 6.5*0.5 = 0.75
    seg = segs_lt[1]
    result = cf.calculate_crossfall_at(seg, 1030)
    assert math.isclose(result, 0.75, abs_tol=1e-9)


@pytest.mark.parametrize('t,expected_f', [
    (0.0, 0.0),
    (0.25, 0.15625),   # 3*0.0625 - 2*0.015625 = 0.1875-0.03125 = 0.15625
    (0.5,  0.5),
    (0.75, 0.84375),
    (1.0,  1.0),
])
def test_s_curve_shape_function(segs_lt, t, expected_f):
    seg = segs_lt[1]   # L=60, x1=-2.5, x2=4.0
    sta = seg.sta_start + t * (seg.sta_end - seg.sta_start)
    result = cf.calculate_crossfall_at(seg, sta)
    expected = seg.x_start + (seg.x_end - seg.x_start) * expected_f
    assert math.isclose(result, expected, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 4: type V — linear interpolation
# ---------------------------------------------------------------------------

def test_type_v_linear():
    seg = cf.CrossfallSegment(sta_start=0, sta_end=100, x_start=-2.5, x_end=4.0, type='V')
    assert math.isclose(cf.calculate_crossfall_at(seg, 0), -2.5, abs_tol=1e-9)
    assert math.isclose(cf.calculate_crossfall_at(seg, 50), 0.75, abs_tol=1e-9)
    assert math.isclose(cf.calculate_crossfall_at(seg, 100), 4.0, abs_tol=1e-9)


def test_type_v_is_default_for_unknown_type():
    seg = cf.CrossfallSegment(sta_start=0, sta_end=100, x_start=0.0, x_end=10.0, type='X')
    assert math.isclose(cf.calculate_crossfall_at(seg, 50), 5.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 5: equal x_start and x_end → constant even for S/V
# ---------------------------------------------------------------------------

def test_equal_endpoints_gives_constant():
    for t_type in ('N', 'V', 'S'):
        seg = cf.CrossfallSegment(sta_start=0, sta_end=200, x_start=3.0, x_end=3.0, type=t_type)
        for sta in (0, 100, 200):
            assert math.isclose(cf.calculate_crossfall_at(seg, sta), 3.0, abs_tol=1e-9), (
                f'type={t_type} sta={sta}'
            )


# ---------------------------------------------------------------------------
# Test 6: calculate_crossfall (full-table lookup)
# ---------------------------------------------------------------------------

def test_calculate_crossfall_xlt_constant_zone(segs_lt):
    assert math.isclose(cf.calculate_crossfall(segs_lt, 0), -2.5, abs_tol=1e-9)
    assert math.isclose(cf.calculate_crossfall(segs_lt, 500), -2.5, abs_tol=1e-9)


def test_calculate_crossfall_xlt_transition_start(segs_lt):
    assert math.isclose(cf.calculate_crossfall(segs_lt, 1000), -2.5, abs_tol=1e-9)


def test_calculate_crossfall_xlt_transition_mid(segs_lt):
    assert math.isclose(cf.calculate_crossfall(segs_lt, 1030), 0.75, abs_tol=1e-9)


def test_calculate_crossfall_xlt_transition_end(segs_lt):
    assert math.isclose(cf.calculate_crossfall(segs_lt, 1060), 4.0, abs_tol=1e-9)


def test_calculate_crossfall_xlt_last_segment_end(segs_lt):
    # last segment — inclusive at sta_end
    assert math.isclose(cf.calculate_crossfall(segs_lt, 2000), 4.0, abs_tol=1e-9)


def test_calculate_crossfall_xrt_constant(segs_rt):
    for sta in (0, 1000, 2000):
        assert math.isclose(cf.calculate_crossfall(segs_rt, sta), -2.5, abs_tol=1e-9)


def test_calculate_crossfall_outside_returns_none(segs_lt):
    assert cf.calculate_crossfall(segs_lt, -1.0) is None
    assert cf.calculate_crossfall(segs_lt, 2001.0) is None


# ---------------------------------------------------------------------------
# Test 7: interior boundary — sta at seg_end of non-last segment goes to NEXT seg
# ---------------------------------------------------------------------------

def test_interior_boundary_uses_next_segment(segs_lt):
    # sta=1000 is the end of seg[0] AND start of seg[1]
    # seg[0] boundary: sta < seg.sta_end → 1000 < 1000 = False (not last) → falls through
    # seg[1] boundary: sta >= 1000 and 1000 < 1060 → True → uses seg[1]
    # seg[1] at t=0: crossfall = x_start = -2.5 (same as seg[0] value, continuity ✓)
    val = cf.calculate_crossfall(segs_lt, 1000)
    assert math.isclose(val, -2.5, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 8: calculate_crossfall_rate_at
# ---------------------------------------------------------------------------

def test_rate_type_n_is_zero(segs_lt):
    assert cf.calculate_crossfall_rate_at(segs_lt[0], 500) == 0.0


def test_rate_type_s_zero_at_endpoints(segs_lt):
    seg = segs_lt[1]   # S-curve [1000,1060]
    assert math.isclose(cf.calculate_crossfall_rate_at(seg, 1000), 0.0, abs_tol=1e-9)
    assert math.isclose(cf.calculate_crossfall_rate_at(seg, 1060), 0.0, abs_tol=1e-9)


def test_rate_type_s_max_at_midpoint(segs_lt):
    # t=0.5: dfdt = 6*0.5*0.5=1.5, dx=6.5, L=60 → rate=6.5*1.5/60=0.1625
    seg = segs_lt[1]
    rate = cf.calculate_crossfall_rate_at(seg, 1030)
    assert math.isclose(rate, 6.5 * 1.5 / 60.0, abs_tol=1e-9)


def test_rate_type_v_constant():
    seg = cf.CrossfallSegment(sta_start=0, sta_end=100, x_start=0.0, x_end=10.0, type='V')
    # rate = dx/L = 10/100 = 0.1 at any station
    for sta in (0, 50, 100):
        assert math.isclose(cf.calculate_crossfall_rate_at(seg, sta), 0.1, abs_tol=1e-9)


def test_rate_equal_endpoints_is_zero():
    seg = cf.CrossfallSegment(sta_start=0, sta_end=100, x_start=3.0, x_end=3.0, type='S')
    assert cf.calculate_crossfall_rate_at(seg, 50) == 0.0


# ---------------------------------------------------------------------------
# Test 9: zero-length segment edge case
# ---------------------------------------------------------------------------

def test_zero_length_segment_returns_x_start():
    seg = cf.CrossfallSegment(sta_start=100, sta_end=100, x_start=-2.5, x_end=4.0, type='S')
    assert cf.calculate_crossfall_at(seg, 100) == -2.5
    assert cf.calculate_crossfall_rate_at(seg, 100) == 0.0
