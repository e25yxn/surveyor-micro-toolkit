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


@pytest.mark.xfail(
    strict=True,
    reason=(
        'COSINE closed-form fix (session_logs/plan_cosine_sinehalfwave_fix.md, '
        'session_logs/investigate_sinehalfwave_formula.md) intentionally shifts '
        'SC@2249.324 and ST@2554.756 by ~3cm vs the old Simpson-based golden fixture. '
        'Fixture regeneration is the immediate next plan; remove this mark once '
        'tests/golden/tables.json and reference/tables.json are regenerated.'
    ),
)
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
