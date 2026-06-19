"""Golden tests for smt.alignment.

Fixtures loaded from tests/golden/tables.json (30-element alignment, 31 control points).

Two test categories:
  1. control_point: all 31 control points must produce N,E within 1e-3 m.
  2. roundtrip:     forward (sta→coord) then inverse (coord→sta) must
                    recover the original station within 1e-3 m, offset ≈ 0.
"""
import json
import math
from pathlib import Path

import pytest

from smt import alignment as al

# ---------------------------------------------------------------------------
# Fixture: load golden data once
# ---------------------------------------------------------------------------

_GOLDEN = Path(__file__).parent / 'golden' / 'tables.json'


@pytest.fixture(scope='module')
def golden():
    with _GOLDEN.open(encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def elements(golden):
    return al.parse_alignment_table(golden['elements'])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _mid(el: al.Element) -> float:
    """Station at the midpoint of an element."""
    return (el.sta_start + el.sta_end) / 2.0


# ---------------------------------------------------------------------------
# Test 1: chain integrity
# ---------------------------------------------------------------------------

def test_chain_has_no_gaps(elements):
    """Exit state of element[n] must equal entry state of element[n+1]."""
    issues = al.check_chain(elements, tolerance=0.005)
    assert issues == [], f'Chain gaps found: {issues}'


# ---------------------------------------------------------------------------
# Test 2: all 31 control points
# ---------------------------------------------------------------------------

def _control_params(golden_data):
    return [
        pytest.param(cp['sta'], cp['n'], cp['e'], id=f"{cp['name']}@{cp['sta']}")
        for cp in golden_data['controls']
    ]


def test_control_points(elements, golden):
    """All 31 control points must resolve to N,E within 1e-3 m.

    EP is the alignment end-point: its fixture station is the 3-decimal rounding of
    elements[-1].sta_end, so we use the full-precision element station directly.
    """
    tol = 1e-3
    failures = []
    for cp in golden['controls']:
        sta = elements[-1].sta_end if cp['name'] == 'EP' else cp['sta']
        pt = al.calculate_station_to_coord(elements, sta, 0.0)
        err_n = abs(pt.n - cp['n'])
        err_e = abs(pt.e - cp['e'])
        if err_n > tol or err_e > tol:
            failures.append(
                f"{cp['name']}@{sta}: "
                f"got ({pt.n:.4f},{pt.e:.4f}) "
                f"expected ({cp['n']:.4f},{cp['e']:.4f}) "
                f"err=({err_n:.6f},{err_e:.6f})"
            )
    assert not failures, 'Control point failures:\n' + '\n'.join(failures)


# Parametrized variant — one test per control point for granular CI output
@pytest.mark.parametrize(
    'sta,exp_n,exp_e,name',
    [
        (cp['sta'], cp['n'], cp['e'], cp['name'])
        for cp in json.loads(_GOLDEN.read_text(encoding='utf-8'))['controls']
    ],
    ids=[
        f"{cp['name']}@{cp['sta']}"
        for cp in json.loads(_GOLDEN.read_text(encoding='utf-8'))['controls']
    ],
)
def test_control_point_parametrized(elements, sta, exp_n, exp_e, name):
    # EP station in the fixture is a 3-decimal rounding of elements[-1].sta_end;
    # use the full-precision element boundary to avoid the 1e-4 tolerance edge.
    actual_sta = elements[-1].sta_end if name == 'EP' else sta
    pt = al.calculate_station_to_coord(elements, actual_sta, 0.0)
    assert abs(pt.n - exp_n) <= 1e-3, (
        f'{name}@{actual_sta}: N got {pt.n:.4f} expected {exp_n:.4f}'
    )
    assert abs(pt.e - exp_e) <= 1e-3, (
        f'{name}@{actual_sta}: E got {pt.e:.4f} expected {exp_e:.4f}'
    )


# ---------------------------------------------------------------------------
# Test 3: roundtrip — forward then inverse recovers sta, offset ≈ 0
# ---------------------------------------------------------------------------

def _roundtrip_stations(elements: list[al.Element]) -> list[tuple[str, float]]:
    """One station per element type, solidly inside (not at a boundary)."""
    cases = []
    for el in elements:
        label = f'{el.type}({el.trans})@{el.sta_start:.1f}'
        cases.append((label, _mid(el)))
    return cases


def test_roundtrip_all_element_types(elements):
    """forward(sta) → coord → inverse must recover sta within 1e-3 and offset ≈ 0."""
    tol = 1e-3
    failures = []
    for label, sta in _roundtrip_stations(elements):
        pt = al.calculate_station_to_coord(elements, sta, 0.0)
        result = al.calculate_coord_to_station(elements, pt.n, pt.e)
        err_sta = abs(result.sta - sta)
        err_off = abs(result.offset)
        if err_sta > tol or err_off > tol:
            failures.append(
                f'{label}: sta_err={err_sta:.6f} off_err={err_off:.6f}'
            )
    assert not failures, 'Roundtrip failures:\n' + '\n'.join(failures)


@pytest.mark.parametrize(
    'label,sta',
    _roundtrip_stations(al.parse_alignment_table(
        json.loads(_GOLDEN.read_text(encoding='utf-8'))['elements']
    )),
)
def test_roundtrip_parametrized(elements, label, sta):
    pt = al.calculate_station_to_coord(elements, sta, 0.0)
    result = al.calculate_coord_to_station(elements, pt.n, pt.e)
    assert abs(result.sta - sta) <= 1e-3, (
        f'{label}: sta got {result.sta:.4f} expected {sta:.4f}'
    )
    assert abs(result.offset) <= 1e-3, (
        f'{label}: residual offset {result.offset:.6f}'
    )


# ---------------------------------------------------------------------------
# Test 4: unit tests for make_element and curvature helpers
# ---------------------------------------------------------------------------

def test_curvature_from_radius_tangent():
    assert al.curvature_from_radius(0) == 0.0
    assert al.curvature_from_radius(None) == 0.0
    assert al.curvature_from_radius(math.inf) == 0.0


def test_curvature_from_radius_positive():
    assert math.isclose(al.curvature_from_radius(300), 1 / 300)


def test_curvature_from_radius_negative():
    assert math.isclose(al.curvature_from_radius(-400), -1 / 400)


def test_radius_from_curvature_zero():
    assert math.isinf(al.radius_from_curvature(0.0))


def test_make_element_tangent():
    el = al.make_element('T', 0, 100, 0, 0, 90, 0)
    assert el.k_in == 0.0
    assert el.k_out == 0.0
    assert el.type == 'T'


def test_make_element_spin_sets_k_in_zero():
    el = al.make_element('SPIN', 100, 160, 0, 0, 90, 400)
    assert el.k_in == 0.0
    assert math.isclose(el.k_out, 1 / 400)


def test_make_element_spout_sets_k_out_zero():
    el = al.make_element('SPOUT', 160, 220, 0, 0, 95, 400)
    assert math.isclose(el.k_in, 1 / 400)
    assert el.k_out == 0.0


def test_make_element_circular_negative_radius():
    el = al.make_element('C', 200, 300, 0, 0, 90, -400)
    assert math.isclose(el.k_in, -1 / 400)
    assert math.isclose(el.k_out, -1 / 400)


# ---------------------------------------------------------------------------
# Test 5: tangent geometry sanity checks
# ---------------------------------------------------------------------------

def test_point_on_tangent_due_east():
    el = al.make_element('T', 0, 1000, 20000, 10000, 90, 0)
    st = al.calculate_point_on_element(el, 519.6152)
    assert math.isclose(st.n, 20000.0, abs_tol=1e-9)
    assert math.isclose(st.e, 10519.6152, abs_tol=1e-9)


def test_exit_state_matches_next_entry(elements):
    """Exit state of each element must match the n,e,az of the next element."""
    tol_pos = 1e-3   # 1 mm
    tol_az = math.radians(5 / 3600)   # 5 arc-seconds
    for i in range(len(elements) - 1):
        ex = al.calculate_exit_state(elements[i])
        nxt = elements[i + 1]
        assert math.hypot(ex.n - nxt.n, ex.e - nxt.e) < tol_pos, (
            f'Element {i}->{i+1} position gap: '
            f'exit=({ex.n:.4f},{ex.e:.4f}) next=({nxt.n:.4f},{nxt.e:.4f})'
        )
        assert abs(al.fpmath.angle_diff(ex.az, nxt.az)) < tol_az, (
            f'Element {i}->{i+1} azimuth gap: '
            f'exit_az={math.degrees(ex.az):.6f} next_az={math.degrees(nxt.az):.6f}'
        )
