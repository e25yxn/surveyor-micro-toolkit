"""Tests for smt.check — horizontal and vertical cross-check engine.

Golden data loaded from tests/golden/tables.json:
  'controls'  — 31 horizontal control points (name, sta, n, e)
  'vchecks'   — 11 vertical check points     (name, sta, elev)

Horizontal tolerance (tol=2e-3):
  test_alignment.py verifies all 31 control points to within 1e-3 m per
  coordinate, so gap_m < sqrt(2) * 1e-3 ≈ 1.41 mm < 2 mm for every point.
  EP station (5887.623) overshoots the last element end (5887.6228) by
  0.0002 m — check_horizontal snaps it automatically.

Vertical tolerance (tol=1e-3):
  PVC, PVT, BVP, EVP are on the parabolic curve; the engine matches them
  to within rounding of the 4-decimal vtable values (<< 1 mm).
  PVI points are tangent-intersections, not curve points — their d_elev is
  the mid-ordinate of the vertical curve.  The test skips their ok assertion.
"""
import json
import math
from pathlib import Path

import pytest

from smt import alignment as al
from smt import vertical as vt
from smt import check as ck
from smt.builders.alignment_builder import ControlPoint

_GOLDEN = Path(__file__).parent / 'golden' / 'tables.json'


@pytest.fixture(scope='module')
def golden() -> dict:
    with _GOLDEN.open(encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def elements(golden: dict) -> list[al.Element]:
    return al.parse_alignment_table(golden['elements'])


@pytest.fixture(scope='module')
def segs(golden: dict) -> list[vt.VerticalSegment]:
    return vt.parse_vertical_table(golden['vtable'])


# ---------------------------------------------------------------------------
# check_horizontal
# ---------------------------------------------------------------------------

def test_check_horizontal_result_count(golden: dict, elements: list) -> None:
    results = ck.check_horizontal(elements, golden['controls'])
    assert len(results) == len(golden['controls'])


def test_check_horizontal_result_type(golden: dict, elements: list) -> None:
    results = ck.check_horizontal(elements, golden['controls'])
    for r in results:
        assert isinstance(r, ck.HorizontalCheckResult)
        assert isinstance(r.is_ok, bool)


def test_check_horizontal_gap_equals_hypot(golden: dict, elements: list) -> None:
    """gap_metres must equal hypot(delta_n, delta_e) for every result."""
    results = ck.check_horizontal(elements, golden['controls'])
    for r in results:
        assert abs(r.gap_metres - math.hypot(r.delta_n, r.delta_e)) < 1e-12


def test_check_horizontal_all_pass(golden: dict, elements: list) -> None:
    """All 31 control points must fall within 2 mm of the alignment engine."""
    results = ck.check_horizontal(elements, golden['controls'], tol=2e-3)
    failures = [r for r in results if not r.is_ok]
    assert failures == [], (
        f'{len(failures)} point(s) exceeded 2 mm: '
        + ', '.join(f'{r.name}@{r.sta} gap={r.gap_metres:.6f} m' for r in failures)
    )


def test_check_horizontal_names_preserved(golden: dict, elements: list) -> None:
    """Result names must match the input control list in order."""
    results = ck.check_horizontal(elements, golden['controls'])
    for r, cp in zip(results, golden['controls']):
        assert r.name == cp['name']
        assert r.sta == cp['sta']


# ---------------------------------------------------------------------------
# check_vertical
# ---------------------------------------------------------------------------

def test_check_vertical_result_count(golden: dict, segs: list) -> None:
    results = ck.check_vertical(segs, golden['vchecks'])
    assert len(results) == len(golden['vchecks'])


def test_check_vertical_result_type(golden: dict, segs: list) -> None:
    results = ck.check_vertical(segs, golden['vchecks'])
    for r in results:
        assert isinstance(r, ck.VerticalCheckResult)
        assert isinstance(r.is_ok, bool)


def test_check_vertical_curve_points_pass(golden: dict, segs: list) -> None:
    """PVC, PVT, BVP, EVP must be within 1 mm of the vertical engine.

    PVI entries are tangent-intersections (not on the parabola) — their
    d_elev is the mid-ordinate; ok=True is not expected and not asserted.
    """
    results = ck.check_vertical(segs, golden['vchecks'], tol=1e-3)
    failures = [r for r in results if r.name != 'PVI' and not r.is_ok]
    assert failures == [], (
        f'{len(failures)} curve point(s) exceeded 1 mm: '
        + ', '.join(f'{r.name}@{r.sta} delta_elevation={r.delta_elevation:.6f} m' for r in failures)
    )


def test_check_vertical_pvi_count(golden: dict, segs: list) -> None:
    """The golden vchecks contain exactly 3 PVI entries."""
    results = ck.check_vertical(segs, golden['vchecks'])
    pvi = [r for r in results if r.name == 'PVI']
    assert len(pvi) == 3


def test_check_vertical_pvi_nonzero_d_elev(golden: dict, segs: list) -> None:
    """PVI d_elev is the mid-ordinate — always non-zero for a proper VC."""
    results = ck.check_vertical(segs, golden['vchecks'])
    for r in results:
        if r.name == 'PVI':
            assert abs(r.delta_elevation) > 0.1, (
                f'PVI@{r.sta}: expected non-zero mid-ordinate, got delta_elevation={r.delta_elevation}'
            )


def test_check_vertical_names_preserved(golden: dict, segs: list) -> None:
    """Result names must match the input vchecks list in order."""
    results = ck.check_vertical(segs, golden['vchecks'])
    for r, vc in zip(results, golden['vchecks']):
        assert r.name == vc['name']
        assert r.sta == vc['sta']


# ---------------------------------------------------------------------------
# Part 2 defensive edge-case tests
# ---------------------------------------------------------------------------

def test_check_horizontal_empty_controls_returns_empty(elements: list) -> None:
    assert ck.check_horizontal(elements, []) == []


def test_check_horizontal_far_outside_raises(elements: list) -> None:
    """Station far outside snap tolerance (0.01 m) propagates ValueError from alignment."""
    far_outside = [{'name': 'X', 'sta': -1000.0, 'n': 0.0, 'e': 0.0}]
    with pytest.raises(ValueError):
        ck.check_horizontal(elements, far_outside)


def test_check_vertical_empty_vchecks_returns_empty(segs: list) -> None:
    assert ck.check_vertical(segs, []) == []


def test_check_vertical_far_outside_raises(segs: list) -> None:
    """Station far outside profile raises ValueError (calculate_elevation returns None)."""
    far_outside = [{'name': 'X', 'sta': -1000.0, 'elev': 100.0}]
    with pytest.raises(ValueError):
        ck.check_vertical(segs, far_outside)


# ---------------------------------------------------------------------------
# TestBulkCrossCheck
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def tangent_elements() -> list[al.Element]:
    """Single east-running tangent: sta 0–200, entry (N=1000, E=2000, az=90°)."""
    return al.parse_alignment_table([
        ['StaStart', 'StaEnd', 'N', 'E', 'Azimuth', 'Radius', 'Type', 'Transition'],
        [0.0, 200.0, 1000.0, 2000.0, 90.0, 0.0, 'T', ''],
    ])


class TestBulkCrossCheck:
    def test_empty_returns_empty(self, tangent_elements):
        assert ck.bulk_cross_check(tangent_elements, []) == []

    def test_centerline_point(self, tangent_elements):
        # Point on centre-line at E=2100 → sta=100, offset=0
        fp = [{'name': 'PT01', 'n': 1000.0, 'e': 2100.0, 'z': 85.0, 'disc': 0.0}]
        rows = ck.bulk_cross_check(tangent_elements, fp)
        assert len(rows) == 1
        r = rows[0]
        assert r.name == 'PT01'
        assert math.isclose(r.sta,    100.0, abs_tol=1e-6)
        assert math.isclose(r.offset,   0.0, abs_tol=1e-6)

    def test_right_offset(self, tangent_elements):
        # East-running tangent: south (+5 m) is left, north (−5 m) is right
        # az=90° → right = south (N−5), left = north (N+5) per sign convention
        fp = [{'name': 'PT02', 'n': 995.0, 'e': 2050.0, 'z': 85.0, 'disc': 0.0}]
        r = ck.bulk_cross_check(tangent_elements, fp)[0]
        assert r.offset > 0.0   # right of travel

    def test_left_offset(self, tangent_elements):
        fp = [{'name': 'PT03', 'n': 1005.0, 'e': 2050.0, 'z': 85.0, 'disc': 0.0}]
        r = ck.bulk_cross_check(tangent_elements, fp)[0]
        assert r.offset < 0.0   # left of travel

    def test_disc_carried_through(self, tangent_elements):
        fp = [{'name': 'PT04', 'n': 1000.0, 'e': 2050.0, 'z': 85.0, 'disc': '0.013'}]
        r = ck.bulk_cross_check(tangent_elements, fp)[0]
        assert r.disc == '0.013'

    def test_disc_defaults_to_empty(self, tangent_elements):
        fp = [{'name': 'PT05', 'n': 1000.0, 'e': 2050.0, 'z': 85.0}]
        r = ck.bulk_cross_check(tangent_elements, fp)[0]
        assert r.disc == ''

    def test_result_type(self, tangent_elements):
        fp = [{'name': 'PT06', 'n': 1000.0, 'e': 2050.0, 'z': 85.0, 'disc': 0.0}]
        r = ck.bulk_cross_check(tangent_elements, fp)[0]
        assert isinstance(r, ck.FieldCrossCheckResult)

    def test_outside_alignment_raises(self, tangent_elements):
        # Point far to the west (E=1000) cannot project onto sta 0–200
        fp = [{'name': 'FAR', 'n': 1000.0, 'e': 1000.0, 'z': 85.0, 'disc': 0.0}]
        with pytest.raises(ValueError):
            ck.bulk_cross_check(tangent_elements, fp)


# ---------------------------------------------------------------------------
# normalize_ip_names / add_pcc_control_points (session_logs/review_src_smt_20260802.md
# #4 follow-up adapters)
# ---------------------------------------------------------------------------

def test_normalize_ip_names_strips_number() -> None:
    drawing = [
        {'name': 'IP1', 'sta': 100.0, 'n': 0.0, 'e': 0.0},
        {'name': 'IP2', 'sta': 200.0, 'n': 0.0, 'e': 0.0},
        {'name': 'IP10', 'sta': 300.0, 'n': 0.0, 'e': 0.0},
    ]
    out = ck.normalize_ip_names(drawing)
    assert [d['name'] for d in out] == ['IP', 'IP', 'IP']


def test_normalize_ip_names_leaves_others_unchanged() -> None:
    drawing = [
        {'name': 'PC', 'sta': 100.0, 'n': 0.0, 'e': 0.0},
        {'name': 'IP', 'sta': 200.0, 'n': 0.0, 'e': 0.0},   # already bare
        {'name': 'PI1', 'sta': 300.0, 'n': 0.0, 'e': 0.0},  # curve PI, not IP
    ]
    out = ck.normalize_ip_names(drawing)
    assert [d['name'] for d in out] == ['PC', 'IP', 'PI1']


def test_normalize_ip_names_does_not_mutate_input() -> None:
    drawing = [{'name': 'IP1', 'sta': 100.0, 'n': 0.0, 'e': 0.0}]
    ck.normalize_ip_names(drawing)
    assert drawing[0]['name'] == 'IP1'


def test_add_pcc_control_points_inserts_at_coincident_pair() -> None:
    control = [
        ControlPoint(name='PT', sta=100.000, n=10.0, e=20.0),
        ControlPoint(name='PC', sta=100.004, n=10.0, e=20.0),
    ]
    out = ck.add_pcc_control_points(control)
    assert len(out) == 3
    pcc = out[-1]
    assert pcc.name == 'PCC'
    assert pcc.sta == pytest.approx(100.002)
    assert pcc.n == 10.0 and pcc.e == 20.0


def test_add_pcc_control_points_ignores_distant_pt_pc() -> None:
    # A genuine PT...PC with a real tangent between them (not a compound
    # junction) must not spawn a synthetic PCC.
    control = [
        ControlPoint(name='PT', sta=100.0, n=0.0, e=0.0),
        ControlPoint(name='PC', sta=250.0, n=0.0, e=0.0),
    ]
    out = ck.add_pcc_control_points(control)
    assert len(out) == 2


def test_add_pcc_control_points_does_not_mutate_input() -> None:
    control = [
        ControlPoint(name='PT', sta=100.000, n=0.0, e=0.0),
        ControlPoint(name='PC', sta=100.001, n=0.0, e=0.0),
    ]
    ck.add_pcc_control_points(control)
    assert len(control) == 2
