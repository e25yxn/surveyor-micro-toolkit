"""Tests for smt.builders.table_splitter.

Golden fixture: test_data/HOR_ORR_04.csv, a real field table (11 PI, 1 compound-
free clothoid at PI-10) with BP/PI-n/PT/PC/TS/SC/CS/ST/EP rows interleaved.
split_mixed_alignment_table() must separate it into a vertex sub-table (feeds
parse_pi_table() -> build_alignment_from_pi()) and a drawing list (feeds
check_against_drawing()) without either downstream function being touched.

PI-10's NORTHING/EASTING in the CSV were corrected 2026-07-23 (transcription
error, confirmed against the source survey - see
session_logs/investigate_hor_orr04_pi10_typo.md); with that fix, all 22 drawn
control points cross-check within 0.1 m of the built alignment.
"""
import csv
from pathlib import Path

import pytest

from smt.builders.alignment_builder import (
    build_alignment_from_pi,
    check_against_drawing,
    parse_pi_table,
)
from smt.builders.table_splitter import split_mixed_alignment_table

_DATA = Path(__file__).parent.parent.parent / 'test_data'
_HOR_ORR_04 = _DATA / 'HOR_ORR_04.csv'


@pytest.fixture(scope='module')
def raw_rows():
    with _HOR_ORR_04.open(newline='', encoding='utf-8') as f:
        return list(csv.reader(f))


@pytest.fixture(scope='module')
def split(raw_rows):
    return split_mixed_alignment_table(raw_rows)


@pytest.fixture(scope='module')
def vertex_rows(split):
    return split[0]


@pytest.fixture(scope='module')
def drawing(split):
    return split[1]


@pytest.fixture(scope='module')
def build_result(vertex_rows):
    vertices = parse_pi_table(vertex_rows)
    return build_alignment_from_pi(vertices)


# ---------------------------------------------------------------------------
# Test 1: the split itself
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HOR_ORR_04.exists(), reason='test_data/HOR_ORR_04.csv not present')
class TestSplit:

    def test_vertex_rows_count(self, vertex_rows):
        # header + BP + PI-1..PI-11 + EP = 1 + 13
        assert len(vertex_rows) == 14

    def test_drawing_count(self, drawing):
        # PT/PC/TS/SC/CS/ST rows: one PT for PI-1..PI-9 minus PI-1's missing PC,
        # plus TS/SC/CS/ST for PI-10 and the closing PC before PI-11 = 22
        assert len(drawing) == 22

    def test_bp_row_commas_stripped(self, vertex_rows):
        assert vertex_rows[1] == ['BP', '0', '1537772.85', '685314.64', '', '', '', '']

    def test_pi10_row_reflects_corrected_coordinates(self, vertex_rows):
        pi10 = next(row for row in vertex_rows if row[0] == 'PI-10')
        assert pi10 == [
            'PI-10', '2845.636', '1536748.127', '681827.952', '120', '67.5', '67.5', 'CLOTHOID',
        ]

    def test_no_pt_pc_ts_sc_cs_st_leaks_into_vertex_rows(self, vertex_rows):
        leaked = {'PT', 'PC', 'TS', 'SC', 'CS', 'ST'}
        names = {row[0] for row in vertex_rows[1:]}
        assert names.isdisjoint(leaked)

    def test_first_drawing_entry(self, drawing):
        assert drawing[0] == {'name': 'PT', 'sta': 106.854, 'n': 1537746.26, 'e': 685211.36}

    def test_drawing_entries_are_only_control_point_names(self, drawing):
        allowed = {'PT', 'PC', 'TS', 'SC', 'CS', 'ST'}
        assert {d['name'] for d in drawing} <= allowed


# ---------------------------------------------------------------------------
# Test 2: split output feeds parse_pi_table()/build_alignment_from_pi() cleanly
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HOR_ORR_04.exists(), reason='test_data/HOR_ORR_04.csv not present')
class TestBuildFromSplitVertices:

    def test_parsed_vertex_count(self, vertex_rows):
        vertices = parse_pi_table(vertex_rows)
        assert len(vertices) == 13   # BP + 11 PI + EP

    def test_build_has_no_issues(self, build_result):
        assert build_result.issues == []


# ---------------------------------------------------------------------------
# Test 3: cross-check against the full drawing set, golden fixture, real data
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HOR_ORR_04.exists(), reason='test_data/HOR_ORR_04.csv not present')
class TestCrossCheckHorOrr04:

    def test_all_22_points_ok_at_10cm_tolerance(self, build_result, drawing):
        report = check_against_drawing(build_result.control, drawing, tolerance=0.1)
        assert len(report) == 22
        failures = [r for r in report if not r['ok']]
        assert failures == [], (
            f'{len(failures)} point(s) exceed 0.1 m gap:\n'
            + '\n'.join(f"  {r['name']} sta={r['sta_draw']:.3f} gap={r['gap_m']:.4f} m"
                        for r in failures)
        )

    def test_max_gap_is_within_expected_bound(self, build_result, drawing):
        # Real survey noise, not exact closure - worst point measured at ~0.079 m.
        report = check_against_drawing(build_result.control, drawing, tolerance=0.1)
        max_gap = max(r['gap_m'] for r in report)
        assert max_gap < 0.08
