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
        assert isinstance(r.ok, bool)


def test_check_horizontal_gap_equals_hypot(golden: dict, elements: list) -> None:
    """gap_m must equal hypot(d_n, d_e) for every result."""
    results = ck.check_horizontal(elements, golden['controls'])
    for r in results:
        assert abs(r.gap_m - math.hypot(r.d_n, r.d_e)) < 1e-12


def test_check_horizontal_all_pass(golden: dict, elements: list) -> None:
    """All 31 control points must fall within 2 mm of the alignment engine."""
    results = ck.check_horizontal(elements, golden['controls'], tol=2e-3)
    failures = [r for r in results if not r.ok]
    assert failures == [], (
        f'{len(failures)} point(s) exceeded 2 mm: '
        + ', '.join(f'{r.name}@{r.sta} gap={r.gap_m:.6f} m' for r in failures)
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
        assert isinstance(r.ok, bool)


def test_check_vertical_curve_points_pass(golden: dict, segs: list) -> None:
    """PVC, PVT, BVP, EVP must be within 1 mm of the vertical engine.

    PVI entries are tangent-intersections (not on the parabola) — their
    d_elev is the mid-ordinate; ok=True is not expected and not asserted.
    """
    results = ck.check_vertical(segs, golden['vchecks'], tol=1e-3)
    failures = [r for r in results if r.name != 'PVI' and not r.ok]
    assert failures == [], (
        f'{len(failures)} curve point(s) exceeded 1 mm: '
        + ', '.join(f'{r.name}@{r.sta} d_elev={r.d_elev:.6f} m' for r in failures)
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
            assert abs(r.d_elev) > 0.1, (
                f'PVI@{r.sta}: expected non-zero mid-ordinate, got d_elev={r.d_elev}'
            )


def test_check_vertical_names_preserved(golden: dict, segs: list) -> None:
    """Result names must match the input vchecks list in order."""
    results = ck.check_vertical(segs, golden['vchecks'])
    for r, vc in zip(results, golden['vchecks']):
        assert r.name == vc['name']
        assert r.sta == vc['sta']
