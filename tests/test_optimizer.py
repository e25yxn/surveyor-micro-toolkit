"""Tests for smt.optimizer — fit_radius.

Requires scipy (optional dependency):
  pip install 'surveyor-micro-toolkit[optimize]'
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    'scipy',
    reason='scipy not installed; pip install surveyor-micro-toolkit[optimize]',
)

from smt.alignment import calculate_station_to_coordinate
from smt.builders.alignment_builder import build_alignment_from_pi, parse_pi_table
from smt.optimizer import FitResult, fit_radius

_DATA = Path(__file__).parent.parent / 'test_data'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rows(
    bp_n: float, bp_e: float,
    pis: list[tuple[str, float, float, float | str]],
    ep_n: float, ep_e: float,
    sta: float = 0.0,
) -> list[list[object]]:
    """Build minimal pi_rows.  pis = [(name, N, E, R), ...]; R='' for angle point."""
    rows: list[list[object]] = [['POINT', 'N', 'E', 'STA', 'R']]
    rows.append(['BP', bp_n, bp_e, sta, ''])
    for name, n, e, r in pis:
        rows.append([name, n, e, '', r])
    rows.append(['EP', ep_n, ep_e, '', ''])
    return rows


def _draw_pts(elements: list, stations: list[float]) -> list[dict]:
    """Compute drawing points at given stations (skips any outside alignment)."""
    pts = []
    for i, sta in enumerate(stations):
        try:
            pt = calculate_station_to_coordinate(elements, sta)
            pts.append({'name': f'TP{i + 1}', 'sta': sta, 'n': pt.n, 'e': pt.e})
        except ValueError:
            pass
    return pts


# ---------------------------------------------------------------------------
# Test 1 — tangent only: no R to optimise, gap starts at zero
# ---------------------------------------------------------------------------

class TestTangentOnly:
    def test_no_free_radii_gap_zero(self) -> None:
        """Angle-point alignment: no R to optimise; drawing points exactly on alignment."""
        rows  = _rows(0.0, 0.0, [('IP1', 50.0, 50.0, '')], 100.0, 100.0)
        built = build_alignment_from_pi(parse_pi_table(rows))
        sta_end = built.elements[-1].sta_end
        pts = _draw_pts(built.elements, [sta_end * 0.3, sta_end * 0.6])

        res = fit_radius(rows, pts)

        assert isinstance(res, FitResult)
        assert res.names       == []
        assert res.r_initial   == []
        assert res.r_optimized == []
        assert res.n_points    == 2
        assert res.gap_before  < 1e-9
        assert res.gap_after   < 1e-9
        assert res.converged
        assert res.iterations  == 0

    def test_pi_filter_excludes_pi_labels(self) -> None:
        """Drawing points labelled 'PI*' are excluded from active_pts → n_points=0."""
        rows  = _rows(0.0, 0.0, [], 100.0, 0.0)
        built = build_alignment_from_pi(parse_pi_table(rows))
        pts = [{'name': 'PI1', 'sta': 30.0,
                'n': calculate_station_to_coordinate(built.elements, 30.0).n,
                'e': calculate_station_to_coordinate(built.elements, 30.0).e}]

        res = fit_radius(rows, pts)

        assert res.n_points == 0
        assert res.gap_before < 1e-9


# ---------------------------------------------------------------------------
# Test 2 — simple curve: optimizer should converge to correct R
# ---------------------------------------------------------------------------

# Reference geometry: BP(0,0) → PI1(200,100) with R=100 → EP(400,0)
# az_in=26.57°, az_out=333.43°, deflection=-53.14° (left turn), valid curve
_ROWS_REF_T2 = _rows(0.0, 0.0, [('PI1', 200.0, 100.0, 100.0)], 400.0, 0.0)
_BUILT_REF_T2 = build_alignment_from_pi(parse_pi_table(_ROWS_REF_T2))


class TestSimpleCurveConverge:
    def test_recovers_correct_radius(self) -> None:
        """Optimizer should recover R≈100 starting from R=80."""
        sta_end  = _BUILT_REF_T2.elements[-1].sta_end
        stations = [sta_end * i / 11.0 for i in range(1, 11)]
        pts      = _draw_pts(_BUILT_REF_T2.elements, stations)

        rows_bad       = [list(r) for r in _ROWS_REF_T2]
        rows_bad[2][4] = 80.0   # PI1 R → 80 (was 100)

        res = fit_radius(rows_bad, pts)

        assert res.names    == ['PI1']
        assert res.n_points == len(pts)
        assert res.gap_after < res.gap_before
        assert abs(abs(res.r_optimized[0]) - 100.0) < 2.0   # within 2 m of truth

    def test_gap_after_not_worse_than_before(self) -> None:
        """Optimizer must never increase the gap."""
        sta_end  = _BUILT_REF_T2.elements[-1].sta_end
        pts      = _draw_pts(_BUILT_REF_T2.elements,
                             [sta_end * i / 6.0 for i in range(1, 6)])

        rows_bad       = [list(r) for r in _ROWS_REF_T2]
        rows_bad[2][4] = 120.0   # overshoot in the other direction

        res = fit_radius(rows_bad, pts)

        assert res.gap_after <= res.gap_before + 1e-9

    def test_preserves_negative_sign(self) -> None:
        """Sign of R in CSV (negative = left) must be preserved in r_optimized."""
        rows_neg       = [list(r) for r in _ROWS_REF_T2]
        rows_neg[2][4] = -80.0  # negative starting R

        built_neg = build_alignment_from_pi(parse_pi_table(rows_neg))
        sta_end   = built_neg.elements[-1].sta_end
        pts       = _draw_pts(built_neg.elements,
                              [sta_end * 0.3, sta_end * 0.6])

        res = fit_radius(rows_neg, pts)

        assert res.r_initial[0]   < 0.0   # sign from CSV preserved in r_initial
        assert res.r_optimized[0] < 0.0   # sign preserved in r_optimized


# ---------------------------------------------------------------------------
# Test 3 — fix_names: fixed PI unchanged, free PI gets optimised
# ---------------------------------------------------------------------------

_ROWS_REF_T3: list[list[object]] = [
    ['POINT', 'N',    'E',    'STA', 'R'   ],
    ['BP',    0.0,    0.0,    0.0,   ''    ],
    ['PI1',   200.0,  100.0,  '',    50.0  ],
    ['PI2',   400.0,  0.0,    '',    100.0 ],
    ['EP',    600.0,  100.0,  '',    ''    ],
]
_BUILT_REF_T3 = build_alignment_from_pi(parse_pi_table(_ROWS_REF_T3))


class TestFixNames:
    def _perturbed_rows(self) -> list[list[object]]:
        rows       = [list(r) for r in _ROWS_REF_T3]
        rows[3][4] = 70.0   # PI2 R → 70 (was 100)
        return rows

    def _pts(self) -> list[dict]:
        sta_end = _BUILT_REF_T3.elements[-1].sta_end
        return _draw_pts(_BUILT_REF_T3.elements,
                         [sta_end * i / 9.0 for i in range(1, 9)])

    def test_fixed_pi_absent_from_names(self) -> None:
        """PI1 in fix_names → must not appear in res.names."""
        res = fit_radius(self._perturbed_rows(), self._pts(), fix_names=['PI1'])

        assert 'PI1' not in res.names
        assert 'PI2' in res.names
        assert len(res.names) == 1

    def test_fix_all_returns_no_free(self) -> None:
        """Fixing every PI → names=[], early exit."""
        res = fit_radius(self._perturbed_rows(), self._pts(),
                         fix_names=['PI1', 'PI2'])

        assert res.names     == []
        assert res.iterations == 0
        assert res.converged

    def test_gap_does_not_increase(self) -> None:
        """gap_after ≤ gap_before when PI1 is fixed and PI2 is optimised."""
        res = fit_radius(self._perturbed_rows(), self._pts(), fix_names=['PI1'])

        assert res.gap_after <= res.gap_before + 1e-9


# ---------------------------------------------------------------------------
# Test 4 — real data smoke test (skip if files absent)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not (_DATA / 'ramp01n01_SO.csv').exists(),
    reason='test_data/ramp01n01_SO.csv not present',
)
class TestRealData:
    def test_gap_improves_and_r_stable(self) -> None:
        """gap_after ≤ gap_before and all |ΔR| < 1 m (ramp01n01, initial gap ~7.4mm)."""
        import csv as _csv

        with open(_DATA / 'ramp01n01_SO.csv', newline='', encoding='utf-8') as f:
            pi_rows = list(_csv.reader(f))

        crosscheck = _DATA / 'r01n01_so_crosscheck.csv'
        if not crosscheck.exists():
            pytest.skip('r01n01_so_crosscheck.csv not present')

        with open(crosscheck, newline='', encoding='utf-8') as f:
            reader    = _csv.DictReader(f)
            draw_pts  = [
                {'name': row['Name'], 'sta': float(row['STA']),
                 'n': float(row['N']),  'e': float(row['E'])}
                for row in reader
            ]

        res = fit_radius(pi_rows, draw_pts)

        assert res.n_points > 0
        assert res.gap_after <= res.gap_before + 1e-9
        for r_init, r_opt in zip(res.r_initial, res.r_optimized):
            delta = abs(abs(r_opt) - abs(r_init))
            assert delta < 1.0, (
                f'R changed too much: {r_init:.4f} → {r_opt:.4f} (Δ={delta:.4f} m)'
            )
