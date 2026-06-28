"""Golden tests for smt.surface.

surface is the integration layer that combines:
  alignment  →  N, E at (sta, offset)
  vertical   →  centreline elevation
  crossfall  →  crossfall percentage (%)
  formula    →  surface_level = cl_level + |offset| * crossfall_pct / 100

Test data from tests/golden/tables.json.
Cross-fall coverage: xLT [0,2000], xRT [0,2000].
Stations > 2000 with offset != 0 should return level=None (crossfall out of range).
"""
import json
import math
from pathlib import Path

import pytest

from smt import alignment as al
from smt import crossfall as cf
from smt import surface as sf
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
def elements(golden):
    return al.parse_alignment_table(golden['elements'])


@pytest.fixture(scope='module')
def v_segs(golden):
    return vt.parse_vertical_table(golden['vtable'])


@pytest.fixture(scope='module')
def xlt_segs(golden):
    return cf.parse_crossfall_table(golden['xLT'])


@pytest.fixture(scope='module')
def xrt_segs(golden):
    return cf.parse_crossfall_table(golden['xRT'])


# ---------------------------------------------------------------------------
# Test 1: calculate_surface_level — pure formula
# ---------------------------------------------------------------------------

def test_surface_level_negative_crossfall():
    # cl=100, xf=-2.5%, offset=3.5 → 100 + 3.5 * (−2.5) / 100 = 99.9125
    assert math.isclose(sf.calculate_surface_level(100.0, -2.5, 3.5), 99.9125, abs_tol=1e-9)


def test_surface_level_positive_crossfall():
    # cl=100, xf=4%, offset=3.5 → 100 + 3.5 * 4 / 100 = 100.14
    assert math.isclose(sf.calculate_surface_level(100.0, 4.0, 3.5), 100.14, abs_tol=1e-9)


def test_surface_level_zero_crossfall():
    # cl=115.5, xf=0%, offset=5 → 115.5 (no change)
    assert math.isclose(sf.calculate_surface_level(115.5, 0.0, 5.0), 115.5, abs_tol=1e-9)


def test_surface_level_zero_offset():
    # cl=115.5, any xf, offset=0 → 115.5
    assert math.isclose(sf.calculate_surface_level(115.5, -3.0, 0.0), 115.5, abs_tol=1e-9)


def test_surface_level_uses_abs_offset():
    # |+3.5| == |−3.5|, so level must be identical for both signs
    pos = sf.calculate_surface_level(100.0, -2.5, +3.5)
    neg = sf.calculate_surface_level(100.0, -2.5, -3.5)
    assert math.isclose(pos, neg, abs_tol=1e-9)


def test_surface_level_large_offset():
    # cl=100, xf=-3%, offset=10 → 100 + 10*(−3)/100 = 99.7
    assert math.isclose(sf.calculate_surface_level(100.0, -3.0, 10.0), 99.7, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 2: calculate_point_3d — component consistency
#
# For every (sta, offset) pair: verify that N, E, cl_level, crossfall, and
# level computed by calculate_point_3d exactly agree with the corresponding
# sub-functions.  No hard-coded magic numbers — all expected values are
# derived inline from the same modules.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('sta,off', [
    # constant-crossfall zone for both tables
    (100.0,   0.0),
    (100.0,   3.5),
    (100.0,  -3.5),
    (500.0,   0.0),
    (500.0,   3.5),
    (500.0,  -3.5),
    # xLT S-curve transition [1000,1060] — crossfall varies by station
    (1020.0, -3.5),
    (1030.0, -3.5),
    (1050.0, -3.5),
    # xLT post-transition constant zone (xf=4%)
    (1500.0,  -3.5),
    (1500.0,   3.5),
    # right side only
    (1800.0,   3.5),
    (1800.0,   0.0),
])
def test_point3d_all_components_consistent(
    elements, v_segs, xlt_segs, xrt_segs, sta, off
):
    p = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, sta, off)

    # N, E must match alignment directly
    ne = al.calculate_station_to_coordinate(elements, sta, off)
    assert math.isclose(p.n, ne.n, abs_tol=1e-9), f'N mismatch at sta={sta} off={off}'
    assert math.isclose(p.e, ne.e, abs_tol=1e-9), f'E mismatch at sta={sta} off={off}'

    # centreline level
    cl = vt.calculate_elevation(v_segs, sta)
    if cl is None:
        assert p.centerline_level is None
        assert p.level is None
        return
    assert math.isclose(p.centerline_level, cl, abs_tol=1e-9), (
        f'cl_level mismatch at sta={sta}'
    )

    if off == 0.0:
        # on centre line: level = cl, crossfall = None
        assert p.crossfall is None
        assert math.isclose(p.level, cl, abs_tol=1e-9), f'level != cl at sta={sta}'
        return

    # determine which crossfall table is expected (mirrors JS oracle logic)
    primary  = xlt_segs if off < 0 else xrt_segs
    fallback = xrt_segs if off < 0 else xlt_segs
    x_segs = primary if primary else (fallback if fallback else None)
    xf = cf.calculate_crossfall(x_segs, sta) if x_segs is not None else None

    if xf is None:
        assert p.crossfall is None
        assert p.level is None
        return

    assert math.isclose(p.crossfall, xf, abs_tol=1e-9), (
        f'crossfall mismatch at sta={sta} off={off}'
    )
    expected_level = sf.calculate_surface_level(cl, xf, off)
    assert math.isclose(p.level, expected_level, abs_tol=1e-9), (
        f'level mismatch at sta={sta} off={off}'
    )


# ---------------------------------------------------------------------------
# Test 3: crossfall values at specific golden stations
#
# xLT S-curve at sta=1030: t=0.5, f=0.5, xf = -2.5 + 6.5*0.5 = 0.75%
# xLT constant zone:  sta<1000 → −2.5%,  sta>1060 → 4%
# xRT everywhere:     −2.5%
# ---------------------------------------------------------------------------

def test_point3d_left_s_curve_crossfall_value(elements, v_segs, xlt_segs, xrt_segs):
    p = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 1030.0, -3.5)
    assert math.isclose(p.crossfall, 0.75, abs_tol=1e-9)


def test_point3d_left_normal_crown_crossfall_value(elements, v_segs, xlt_segs, xrt_segs):
    p = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 500.0, -3.5)
    assert math.isclose(p.crossfall, -2.5, abs_tol=1e-9)


def test_point3d_left_superelevated_crossfall_value(elements, v_segs, xlt_segs, xrt_segs):
    p = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 1500.0, -3.5)
    assert math.isclose(p.crossfall, 4.0, abs_tol=1e-9)


def test_point3d_right_crossfall_always_normal_crown(elements, v_segs, xlt_segs, xrt_segs):
    for sta in (100.0, 500.0, 1030.0, 1500.0, 1800.0):
        p = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, sta, 3.5)
        assert math.isclose(p.crossfall, -2.5, abs_tol=1e-9), f'xRT mismatch at sta={sta}'


# ---------------------------------------------------------------------------
# Test 4: fallback logic — empty primary table → use the other side's table
# ---------------------------------------------------------------------------

def test_point3d_fallback_rt_when_lt_empty(elements, v_segs, xrt_segs):
    # offset=-3.5 (left), xlt_segs=[] → falls back to xrt_segs
    p_fb = sf.calculate_point_3d(elements, v_segs, [], xrt_segs, 500.0, -3.5)
    # expected: xRT at sta=500 = −2.5%
    assert p_fb.crossfall is not None
    assert math.isclose(p_fb.crossfall, -2.5, abs_tol=1e-9)
    assert p_fb.level is not None


def test_point3d_fallback_lt_when_rt_empty(elements, v_segs, xlt_segs):
    # offset=+3.5 (right), xrt_segs=[] → falls back to xlt_segs
    p_fb = sf.calculate_point_3d(elements, v_segs, xlt_segs, [], 500.0, 3.5)
    # expected: xLT at sta=500 = −2.5%
    assert p_fb.crossfall is not None
    assert math.isclose(p_fb.crossfall, -2.5, abs_tol=1e-9)
    assert p_fb.level is not None


def test_point3d_fallback_result_matches_explicit_table(elements, v_segs, xlt_segs, xrt_segs):
    # When lt is empty for a left offset the fallback (RT) must give the same level
    # as explicitly passing xrt_segs as the left table (same data, so same result).
    p_with_lt = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 500.0, -3.5)
    p_fallback = sf.calculate_point_3d(elements, v_segs, [], xrt_segs, 500.0, -3.5)
    # xLT[500] = −2.5% == xRT[500] = −2.5% → levels must be identical
    assert math.isclose(p_with_lt.level, p_fallback.level, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 5: level = None when crossfall table does not cover the station
# ---------------------------------------------------------------------------

def test_point3d_level_none_when_crossfall_out_of_range(elements, v_segs, xlt_segs, xrt_segs):
    # sta=2500: in alignment and vertical, but outside xLT/xRT [0,2000]
    p = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 2500.0, 3.5)
    assert p.crossfall is None
    assert p.level is None
    # but N, E and cl_level are still valid
    assert p.n is not None
    assert p.centerline_level is not None


def test_point3d_level_none_when_both_tables_empty(elements, v_segs):
    # no crossfall tables at all → level = None for any non-zero offset
    p = sf.calculate_point_3d(elements, v_segs, [], [], 500.0, 3.5)
    assert p.crossfall is None
    assert p.level is None


# ---------------------------------------------------------------------------
# Test 6: centre-line behaviour
# ---------------------------------------------------------------------------

def test_point3d_at_centerline_crossfall_is_none(elements, v_segs, xlt_segs, xrt_segs):
    p = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 500.0, 0.0)
    assert p.crossfall is None


def test_point3d_at_centerline_level_equals_cl_level(elements, v_segs, xlt_segs, xrt_segs):
    p = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 500.0, 0.0)
    assert math.isclose(p.level, p.centerline_level, abs_tol=1e-9)


def test_point3d_at_centerline_default_offset_is_zero(elements, v_segs, xlt_segs, xrt_segs):
    p_default = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 500.0)
    p_zero    = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 500.0, 0.0)
    assert p_default == p_zero


# ---------------------------------------------------------------------------
# Test 7: Point3D is a NamedTuple — field access and unpacking
# ---------------------------------------------------------------------------

def test_point3d_named_fields(elements, v_segs, xlt_segs, xrt_segs):
    p = sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, 500.0, 3.5)
    assert hasattr(p, 'n')
    assert hasattr(p, 'e')
    assert hasattr(p, 'level')
    assert hasattr(p, 'centerline_level')
    assert hasattr(p, 'crossfall')


def test_point3d_unpack(elements, v_segs, xlt_segs, xrt_segs):
    n, e, level, cl_level, xfall = sf.calculate_point_3d(
        elements, v_segs, xlt_segs, xrt_segs, 500.0, 3.5
    )
    assert isinstance(n, float)
    assert isinstance(e, float)
    assert isinstance(level, float)
    assert isinstance(cl_level, float)
    assert isinstance(xfall, float)


# ---------------------------------------------------------------------------
# Part 2 defensive edge-case tests
# ---------------------------------------------------------------------------

def test_point3d_outside_alignment_raises_value_error(elements, v_segs, xlt_segs, xrt_segs):
    """Raises ValueError when sta lies outside the alignment (propagated from alignment)."""
    with pytest.raises(ValueError):
        sf.calculate_point_3d(elements, v_segs, xlt_segs, xrt_segs, sta=-1000.0, offset=0.0)
