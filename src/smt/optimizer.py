"""optimizer — fit alignment radius values to minimise coordinate residuals.

EXTENSION: beyond oracle — no oracle equivalent; new capability.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .alignment import calculate_station_to_coordinate
from .builders.alignment_builder import build_alignment_from_pi, parse_pi_table

_POINT_ALIASES: frozenset[str] = frozenset({'point'})
_R_ALIASES:     frozenset[str] = frozenset({'r', 'radius'})


@dataclass
class FitResult:
    """Result returned by fit_radius."""
    names:        list[str]    # PI names that were optimised
    r_initial:    list[float]  # signed R before optimisation (from CSV)
    r_optimized:  list[float]  # signed R after optimisation (sign preserved)
    gap_before:   float        # √(Σgap_i²) before — metres
    gap_after:    float        # √(Σgap_i²) after  — metres
    n_points:     int          # drawing points used in objective
    iterations:   int          # scipy nit
    converged:    bool
    message:      str


def _find_col(header: list[Any], aliases: frozenset[str]) -> int | None:
    """Return first column index whose lowercased cell text is in aliases."""
    for i, cell in enumerate(header):
        if str(cell).strip().lower() in aliases:
            return i
    return None


def fit_radius(
    pi_rows: list[Any],
    drawing_points: list[dict[str, Any]],
    fix_names: list[str] | None = None,
    tol: float = 1e-6,
    max_iter: int = 10000,
) -> FitResult:
    """Find PI radii that minimise Σgap² between calculated and drawing coordinates.

    pi_rows        : raw CSV rows; pi_rows[0] must be the header row
    drawing_points : [{'name', 'sta', 'n', 'e'}, ...]  target coordinates
    fix_names      : PI names whose R value is held constant (not optimised)
    tol            : Nelder-Mead xatol; fatol = tol²
    max_iter       : maximum Nelder-Mead iterations

    gap_before / gap_after = √(Σgap_i²) in metres (L2-norm of the gap vector).
    Points with name starting 'PI' or 'HIP' are excluded from the objective.
    Sign of R is taken from pi_rows; only abs(R) is varied.
    Penalty 1e6 per point for stations outside the alignment or build issues.

    Raises ImportError when scipy is not installed
    (pip install 'surveyor-micro-toolkit[optimize]').

    EXTENSION: beyond oracle
    """
    try:
        from scipy.optimize import minimize as _minimize  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "scipy is required for fit_radius. "
            "Install with: pip install 'surveyor-micro-toolkit[optimize]'"
        ) from exc

    # A: locate POINT and R columns from header
    header    = pi_rows[0]
    point_col = _find_col(header, _POINT_ALIASES)
    r_col     = _find_col(header, _R_ALIASES)
    if point_col is None or r_col is None:
        raise ValueError("pi_rows header must contain POINT and R/RADIUS columns")

    fix_set = set(fix_names) if fix_names else set()

    # (row_idx, pi_name, sign, abs_r_initial)
    free_pis: list[tuple[int, str, float, float]] = []
    for i, row in enumerate(pi_rows[1:], start=1):
        if point_col >= len(row) or r_col >= len(row):
            continue
        point = str(row[point_col]).strip()
        if not point or point in ('BP', 'EP'):
            continue
        r_raw = str(row[r_col]).strip()
        if not r_raw:
            continue
        try:
            r_val = float(r_raw)
        except ValueError:
            continue
        if r_val == 0.0:
            continue  # angle point — skip
        if point in fix_set:
            continue
        sign = 1.0 if r_val > 0.0 else -1.0
        free_pis.append((i, point, sign, abs(r_val)))

    # B: filter drawing points (exclude PI / HIP labels)
    active_pts = [
        dp for dp in drawing_points
        if not str(dp.get('name', '')).strip().upper().startswith(('PI', 'HIP'))
    ]

    # C: objective — sum of squared coordinate gaps
    def objective(x: Any) -> float:
        rows = [list(r) for r in pi_rows]
        for k, (row_idx, _, sign, _) in enumerate(free_pis):
            rows[row_idx][r_col] = str(sign * float(x[k]))
        try:
            vertices = parse_pi_table(rows)
            built    = build_alignment_from_pi(vertices)
        except Exception:
            return 1e6 * max(len(active_pts), 1)
        if built.issues:
            return 1e6 * len(built.issues) + 1e6 * max(len(active_pts), 1)
        total_sq = 0.0
        for dp in active_pts:
            try:
                pt  = calculate_station_to_coordinate(built.elements, float(dp['sta']))
                gap = math.hypot(pt.n - float(dp['n']), pt.e - float(dp['e']))
                total_sq += gap * gap
            except (ValueError, IndexError):
                total_sq += 1e6
        return total_sq

    # D: gap before optimisation
    x0         = [abs_r for (_, _, _, abs_r) in free_pis]
    gap_before = math.sqrt(objective(x0))

    # E: nothing to optimise
    if not free_pis:
        return FitResult(
            names=[], r_initial=[], r_optimized=[],
            gap_before=gap_before, gap_after=gap_before,
            n_points=len(active_pts), iterations=0,
            converged=True, message='no free radii to optimise',
        )

    # F: Nelder-Mead
    sp_result = _minimize(
        objective, x0,
        method='Nelder-Mead',
        bounds=[(1.0, None)] * len(x0),
        options={'xatol': tol, 'fatol': tol ** 2, 'maxiter': max_iter, 'disp': False},
    )

    # G: assemble output
    gap_after   = math.sqrt(float(sp_result.fun))
    names       = [pi_name for (_, pi_name, _, _) in free_pis]
    r_initial   = [sign * abs_r for (_, _, sign, abs_r) in free_pis]
    r_optimized = [
        sign * float(sp_result.x[k])
        for k, (_, _, sign, _) in enumerate(free_pis)
    ]
    return FitResult(
        names=names,
        r_initial=r_initial,
        r_optimized=r_optimized,
        gap_before=gap_before,
        gap_after=gap_after,
        n_points=len(active_pts),
        iterations=int(sp_result.nit),
        converged=bool(sp_result.success),
        message=str(sp_result.message),
    )
