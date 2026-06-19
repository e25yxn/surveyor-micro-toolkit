"""Tests for smt.builders.vertical_builder.

Golden fixture: tests/golden/tables.json — 'vtable' (7 segments) and 'vchecks' (11 points).

VPI list derived from the golden data:
    BVP  sta=0         elev=100
    VPI1 sta=1200      elev=118    L=200           (symmetric VC)
    VPI2 sta=2800      elev=100    L1=100  L2=200  (asymmetric VC)
    VPI3 sta=4500      elev=112    L=300           (symmetric VC)
    EVP  sta=5887.622  elev=105

Grades (computed from the VPI elevations, not supplied):
    g1 = (118-100)/(1200-0)*100           =  1.5 %
    g2 = (100-118)/(2800-1200)*100        = -1.125 %
    g3 = (112-100)/(4500-2800)*100        =  12/17 % ≈ 0.7059 %
    g4 = (105-112)/(5887.622-4500)*100    = -7/1387.622 % ≈ -0.5045 %

Golden vtable values are rounded to 4 dp; all test tolerances are set to account
for that rounding.  Core functions are not adjusted for tolerance; only the test
thresholds reflect stored-value precision.
"""
import json
from pathlib import Path

import pytest

from smt.builders import vertical_builder as vb

_GOLDEN = Path(__file__).parent.parent / 'golden' / 'tables.json'

_VPIS: list[dict] = [
    {'sta': 0,         'elev': 100},
    {'sta': 1200,      'elev': 118, 'L': 200},
    {'sta': 2800,      'elev': 100, 'L1': 100, 'L2': 200},
    {'sta': 4500,      'elev': 112, 'L': 300},
    {'sta': 5887.622,  'elev': 105},
]


@pytest.fixture(scope='module')
def golden() -> dict:
    with _GOLDEN.open(encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def result() -> vb.VerticalBuildResult:
    return vb.build_vertical_from_vpi(_VPIS)


# ---------------------------------------------------------------------------
# build_vertical_from_vpi — row structure
# ---------------------------------------------------------------------------

def test_row_count(result: vb.VerticalBuildResult) -> None:
    assert len(result.rows) == 7


def test_no_issues(result: vb.VerticalBuildResult) -> None:
    assert result.issues == []


def test_rows_match_vtable(result: vb.VerticalBuildResult, golden: dict) -> None:
    # vtable[0] is header ["index", "Sta.Start", "Sta.End", "Level", "G1", "G2", "LVC", "LVC2"]
    # vtable[1:] are data rows in ascending station order; index column is ignored here
    tol_sta   = 1e-6
    tol_grade = 5e-4
    tol_level = 5e-4

    for idx, row in enumerate(result.rows):
        _, g_start, g_end, g_level, g_g1, g_g2, g_lvc, g_lvc2 = golden['vtable'][idx + 1]

        assert abs(row.sta_start - g_start) <= tol_sta,   f'row {idx}: sta_start'
        assert abs(row.sta_end   - g_end)   <= tol_sta,   f'row {idx}: sta_end'
        assert abs(row.level     - g_level) <= tol_level, f'row {idx}: level'
        assert abs(row.g1        - g_g1)    <= tol_grade, f'row {idx}: g1'
        assert abs(row.g2        - g_g2)    <= tol_grade, f'row {idx}: g2'
        assert abs(row.lvc       - g_lvc)   <= tol_sta,   f'row {idx}: lvc'

        if g_lvc2 == '' or g_lvc2 is None:
            assert row.lvc2 is None, f'row {idx}: lvc2 should be None'
        else:
            assert row.lvc2 is not None, f'row {idx}: lvc2 should not be None'
            assert abs(row.lvc2 - float(g_lvc2)) <= tol_sta, f'row {idx}: lvc2'


# ---------------------------------------------------------------------------
# build_vertical_from_vpi — control points
# ---------------------------------------------------------------------------

def test_control_count(result: vb.VerticalBuildResult) -> None:
    # BVP + 3×(PVC + PVI + PVT) + EVP = 11
    assert len(result.control) == 11


def test_control_names(result: vb.VerticalBuildResult) -> None:
    expected = ['BVP', 'PVC', 'PVI', 'PVT', 'PVC', 'PVI', 'PVT', 'PVC', 'PVI', 'PVT', 'EVP']
    assert [c.name for c in result.control] == expected


def test_cross_check_against_vchecks(result: vb.VerticalBuildResult, golden: dict) -> None:
    report = vb.check_against_drawing(
        result.control,
        golden['vchecks'],
        tolerance_sta=0.001,
        tolerance_elev=0.001,
    )
    assert len(report) == len(golden['vchecks'])
    failed = [r for r in report if not r['ok']]
    assert failed == [], f'vchecks failed: {failed}'


# ---------------------------------------------------------------------------
# to_table
# ---------------------------------------------------------------------------

def test_to_table_shape(result: vb.VerticalBuildResult) -> None:
    table = vb.to_table(result.rows)
    assert len(table) == 7
    assert all(len(row) == 7 for row in table)


def test_to_table_lvc2_sentinel(result: vb.VerticalBuildResult) -> None:
    table = vb.to_table(result.rows)
    assert table[0][6] == ''                       # tangent row → ''
    assert isinstance(table[3][6], (int, float))   # asymmetric VC row 3 → numeric


def test_to_table_values_match_rows(result: vb.VerticalBuildResult) -> None:
    table = vb.to_table(result.rows)
    for i, row in enumerate(result.rows):
        assert table[i][0] == row.sta_start
        assert table[i][2] == row.level
        assert table[i][5] == row.lvc


# ---------------------------------------------------------------------------
# check_against_drawing
# ---------------------------------------------------------------------------

def test_check_against_drawing_all_ok(result: vb.VerticalBuildResult) -> None:
    drawing = [
        {'name': 'BVP', 'sta': 0,         'elev': 100},
        {'name': 'EVP', 'sta': 5887.622,   'elev': 105},
    ]
    report = vb.check_against_drawing(result.control, drawing)
    assert all(r['ok'] for r in report)


def test_check_against_drawing_fail_on_large_error(result: vb.VerticalBuildResult) -> None:
    bad = [{'name': 'PVI', 'sta': 1200, 'elev': 999}]
    report = vb.check_against_drawing(result.control, bad)
    assert report[0]['ok'] is False


def test_check_against_drawing_report_fields(result: vb.VerticalBuildResult) -> None:
    drawing = [{'name': 'BVP', 'sta': 0, 'elev': 100}]
    report = vb.check_against_drawing(result.control, drawing)
    assert set(report[0].keys()) == {'name', 'sta', 'd_sta', 'd_elev', 'ok'}


# ---------------------------------------------------------------------------
# Symmetric VC fields
# ---------------------------------------------------------------------------

def test_symmetric_lvc_fields(result: vb.VerticalBuildResult) -> None:
    vc_row = result.rows[1]   # symmetric VC, L=200
    assert vc_row.lvc == 200
    assert vc_row.lvc2 is None


def test_asymmetric_lvc_fields(result: vb.VerticalBuildResult) -> None:
    vc_row = result.rows[3]   # asymmetric VC, L1=100, L2=200
    assert vc_row.lvc == 100
    assert vc_row.lvc2 == 200


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_pure_tangent_no_vpi() -> None:
    vpis = [{'sta': 0, 'elev': 100}, {'sta': 1000, 'elev': 115}]
    res = vb.build_vertical_from_vpi(vpis)
    assert len(res.rows) == 1
    assert res.rows[0].lvc == 0
    assert res.rows[0].lvc2 is None
    assert res.issues == []
    assert len(res.control) == 2   # BVP + EVP


def test_overlap_reported_as_issue() -> None:
    vpis = [
        {'sta': 0,    'elev': 100},
        {'sta': 500,  'elev': 110, 'L': 1200},   # PVC would be at -100 < 0
        {'sta': 1000, 'elev': 120},
    ]
    res = vb.build_vertical_from_vpi(vpis)
    assert len(res.issues) == 1
    assert 'VPI#1' in res.issues[0]
