"""cli - minimal command-line interface for SMT (Application/boundary layer).

Thin wrapper over the alignment core engine.  Does NO geometry maths itself —
it only reads a CSV element table and delegates to alignment.py, then formats
the result for stdout.

Subcommands:
  smt station-to-coord <table.csv> <sta> [--offset 0]   station(+offset) -> N,E
  smt coord-to-station <table.csv> <n> <e>              N,E -> sta,offset
  smt compare-drawing  <elements.csv> <drawing.csv>     drawing coords vs calculated

CSV format matches the element table (header row required):
  StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from typing import Any

from . import alignment, check, fpmath
from .builders.alignment_builder import (
    build_alignment_from_pi,
    parse_pi_table,
)


def _read_alignment(path: str) -> list[alignment.Element]:
    """Read a CSV element table from path into a list of Elements.

    First row is the header (column names are ignored; column ORDER matters).
    Numeric columns (StaStart, StaEnd, N, E, Azimuth, Radius) are parsed as
    floats; an empty Radius cell is treated as 0 (tangent).  Type and
    Transition stay as strings.  Delegates the actual construction to
    alignment.parse_alignment_table.
    """
    with open(path, newline='', encoding='utf-8') as f:
        raw = list(csv.reader(f))
    if not raw:
        raise ValueError(f'{path} is empty')

    rows: list[Any] = [raw[0]]   # keep header row as-is; parse_alignment_table skips it
    for line in raw[1:]:
        if not line or all(cell.strip() == '' for cell in line):
            continue   # tolerate blank lines
        sta_start, sta_end, n, e, az_deg, radius, type_, trans = line[:8]
        rows.append([
            float(sta_start),
            float(sta_end),
            float(n),
            float(e),
            float(az_deg),
            float(radius) if str(radius).strip() != '' else 0.0,
            type_.strip(),
            trans.strip(),
        ])
    return alignment.parse_alignment_table(rows)


def _read_pi_table(path: str) -> list[dict[str, Any]]:
    """Read a PI-table CSV and return a vertex list for build_alignment_from_pi."""
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError(f'{path} is empty')
    return parse_pi_table(rows)


def _read_field_csv(path: str) -> list[dict[str, Any]]:
    """Read a field survey CSV.

    Column order: NAME, N, E, Z, DISC.  DISC is optional (defaults to 0.0).
    """
    with open(path, newline='', encoding='utf-8') as f:
        raw = list(csv.reader(f))
    if not raw:
        raise ValueError(f'{path} is empty')
    points = []
    for line in raw[1:]:
        if not line or all(c.strip() == '' for c in line):
            continue
        padded = line + [''] * 5
        name = padded[0].strip()
        n, e, z = float(padded[1]), float(padded[2]), float(padded[3])
        disc = padded[4].strip()
        points.append({'name': name, 'n': n, 'e': e, 'z': z, 'disc': disc})
    return points


def _read_drawing_csv(path: str) -> list[dict[str, Any]]:
    """Read a drawing control-point CSV (Name,STA,N,E) into a list of dicts."""
    with open(path, newline='', encoding='utf-8') as f:
        raw = list(csv.reader(f))
    if not raw:
        raise ValueError(f'{path} is empty')
    points = []
    for line in raw[1:]:
        if not line or all(c.strip() == '' for c in line):
            continue
        name = line[0].strip()
        sta, n, e = float(line[1]), float(line[2]), float(line[3])
        points.append({'name': name, 'sta': sta, 'n': n, 'e': e})
    return points


def _radius_from_element(el: alignment.Element) -> float:
    """Return signed design radius for output CSV (0 = tangent)."""
    if el.k_in != 0:
        return 1.0 / el.k_in
    if el.k_out != 0:
        return 1.0 / el.k_out
    return 0.0


def _run_build(args: argparse.Namespace) -> int:
    """build: PI table CSV -> elements_output.csv + controls_so_output.csv."""
    import os
    vertices = _read_pi_table(args.alignment)
    if not vertices:
        raise ValueError('ไม่พบข้อมูล PI ในไฟล์ หรือไฟล์ไม่ใช่ PI table format')
    build_result = build_alignment_from_pi(vertices)
    for issue in build_result.issues:
        print(f'warning: {issue}', file=sys.stderr)

    out_dir = args.out_dir if args.out_dir else os.path.dirname(os.path.abspath(args.alignment))
    os.makedirs(out_dir, exist_ok=True)

    el_path = os.path.join(out_dir, 'elements_output.csv')
    el_header = ['StaStart', 'StaEnd', 'N', 'E', 'Azimuth', 'Radius', 'Type', 'Transition']
    el_rows = []
    for el in build_result.elements:
        transition_val = '' if el.type in ('T', 'C') else el.transition
        el_rows.append([
            f'{el.sta_start:.6f}',
            f'{el.sta_end:.6f}',
            f'{el.n:.6f}',
            f'{el.e:.6f}',
            f'{fpmath.rad_to_deg(el.azimuth):.6f}',
            f'{_radius_from_element(el):.6f}',
            el.type,
            transition_val,
        ])
    with open(el_path, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([el_header] + el_rows)

    cp_path = os.path.join(out_dir, 'controls_so_output.csv')
    cp_header = ['Name', 'STA', 'N', 'E']
    cp_rows = [[cp.name, f'{cp.sta:.6f}', f'{cp.n:.6f}', f'{cp.e:.6f}']
               for cp in build_result.control]
    with open(cp_path, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([cp_header] + cp_rows)

    print(f'\n=== Elements ({len(build_result.elements)} rows) -> {el_path} ===')
    print(f'{"StaStart":>10} {"StaEnd":>10} {"N":>12} {"E":>12} {"Az(deg)":>12} {"Radius":>10} {"Type":<6} {"Trans"}')
    print('-' * 90)
    for row in el_rows:
        print(f'{row[0]:>10} {row[1]:>10} {row[2]:>12} {row[3]:>12} {row[4]:>12} {row[5]:>10} {row[6]:<6} {row[7]}')

    print(f'\n=== Control Points ({len(build_result.control)} rows) -> {cp_path} ===')
    print(f'{"Name":<6} {"STA":>12} {"N":>14} {"E":>14}')
    print('-' * 50)
    for row in cp_rows:
        print(f'{row[0]:<6} {row[1]:>12} {row[2]:>14} {row[3]:>14}')

    return 0


def _run_cross_check(args: argparse.Namespace) -> int:
    """cross-check: PI CSV + field CSV -> station/offset table."""
    vertices = _read_pi_table(args.alignment)
    build_result = build_alignment_from_pi(vertices)
    for issue in build_result.issues:
        print(f'warning: {issue}', file=sys.stderr)
    field_points = _read_field_csv(args.field)
    rows = check.bulk_cross_check(build_result.elements, field_points)
    print(f'{"NAME":<12} {"STA":>10} {"OFFSET":>10} {"N":>12} {"E":>12} {"Z":>9} {"DISC":>8}')
    print('-' * 77)
    for r in rows:
        print(
            f'{r.name:<12} {r.sta:>10.3f} {r.offset:>10.3f}'
            f' {r.n:>12.3f} {r.e:>12.3f} {r.z:>9.3f} {r.disc:>8}'
        )
    return 0


def _run_compare_drawing(args: argparse.Namespace) -> int:
    """compare-drawing: elements CSV + drawing CSV -> coordinate comparison table."""
    elements = _read_alignment(args.elements)
    points = _read_drawing_csv(args.drawing)
    tol = args.tol

    print(
        f'{"Name":<8} {"STA":>12} {"draw_N":>14} {"draw_E":>14}'
        f' {"calc_N":>14} {"calc_E":>14} {"delta_N":>10} {"delta_E":>10} {"gap_m":>10}  OK'
    )
    print('-' * 116)

    for pt in points:
        name = pt['name']
        sta = pt['sta']
        draw_n = pt['n']
        draw_e = pt['e']
        upper = name.upper()
        if upper.startswith('PI') or upper.startswith('HIP'):
            print(
                f'{name:<8} {sta:>12.6f} {draw_n:>14.6f} {draw_e:>14.6f}'
                f' {"":>14} {"":>14} {"":>10} {"":>10} {"":>10}  HIP'
            )
            continue
        calc = alignment.calculate_station_to_coordinate(elements, sta, 0.0)
        delta_n = calc.n - draw_n
        delta_e = calc.e - draw_e
        gap_m = math.sqrt(delta_n ** 2 + delta_e ** 2)
        ok = 'OK' if gap_m <= tol else 'FAIL'
        print(
            f'{name:<8} {sta:>12.6f} {draw_n:>14.6f} {draw_e:>14.6f}'
            f' {calc.n:>14.6f} {calc.e:>14.6f}'
            f' {delta_n:>10.6f} {delta_e:>10.6f} {gap_m:>10.6f}  {ok}'
        )
    return 0


def _run_fit_radius(args: argparse.Namespace) -> int:
    """fit-radius: optimise PI radii to minimise coordinate residuals against drawing points."""
    from .optimizer import fit_radius as _fit_radius

    with open(args.alignment, newline='', encoding='utf-8') as f:
        pi_rows: list[Any] = list(csv.reader(f))
    if not pi_rows:
        raise ValueError(f'{args.alignment} is empty')

    drawing_points = _read_drawing_csv(args.drawing)
    fix_names_raw = [s.strip() for s in args.fix.split(',') if s.strip()]
    fix_names = fix_names_raw if fix_names_raw else None

    result = _fit_radius(pi_rows, drawing_points, fix_names, args.tol, args.max_iter)

    print(f'\n=== fit-radius: {len(result.names)} free PI(s), {result.n_points} drawing point(s) ===')
    if result.names:
        print(f'{"PI":<12} {"R_initial":>14} {"R_optimized":>14}')
        print('-' * 42)
        for name, r0, ro in zip(result.names, result.r_initial, result.r_optimized):
            print(f'{name:<12} {r0:>14.6f} {ro:>14.6f}')

    print(f'\ngap_before: {result.gap_before:.6f} m')
    print(f'gap_after:  {result.gap_after:.6f} m')
    print(f'iterations: {result.iterations}  converged: {result.converged}')

    if result.names and drawing_points:
        header = pi_rows[0]
        point_col: int | None = next(
            (i for i, c in enumerate(header) if str(c).strip().lower() == 'point'), None
        )
        r_col: int | None = next(
            (i for i, c in enumerate(header) if str(c).strip().lower() in ('r', 'radius')), None
        )
        if point_col is not None and r_col is not None:
            name_to_r = dict(zip(result.names, result.r_optimized))
            patched = [list(row) for row in pi_rows]
            for row in patched[1:]:
                if point_col < len(row):
                    pname = str(row[point_col]).strip()
                    if pname in name_to_r and r_col < len(row):
                        row[r_col] = str(name_to_r[pname])
            try:
                vertices = parse_pi_table(patched)
                built = build_alignment_from_pi(vertices)
                active_pts = [
                    dp for dp in drawing_points
                    if not str(dp.get('name', '')).strip().upper().startswith(('PI', 'HIP'))
                ]
                print('\n=== Verification (gap after optimisation) ===')
                print(f'{"Name":<10} {"STA":>12} {"calc_N":>14} {"calc_E":>14} {"gap_m":>10}')
                print('-' * 64)
                for dp in active_pts:
                    try:
                        pt = alignment.calculate_station_to_coordinate(
                            built.elements, float(dp['sta'])
                        )
                        gap = math.hypot(pt.n - float(dp['n']), pt.e - float(dp['e']))
                        print(
                            f'{dp["name"]:<10} {float(dp["sta"]):>12.6f}'
                            f' {pt.n:>14.6f} {pt.e:>14.6f} {gap:>10.6f}'
                        )
                    except (ValueError, IndexError):
                        print(f'{dp["name"]:<10} {"OUTSIDE_ALIGNMENT":>30}')
            except Exception as exc:
                print(f'warning: verification table failed: {exc}', file=sys.stderr)

    return 0


def _run_fwd(args: argparse.Namespace) -> int:
    """station-to-coord: station (+offset) -> grid coordinate N,E."""
    elements = _read_alignment(args.table)
    pt = alignment.calculate_station_to_coordinate(elements, args.sta, args.offset)
    print(f'{pt.n},{pt.e}')
    return 0


def _run_inv(args: argparse.Namespace) -> int:
    """coord-to-station: grid coordinate N,E -> station,offset."""
    elements = _read_alignment(args.table)
    so = alignment.calculate_coordinate_to_station(elements, args.n, args.e)
    print(f'{so.sta},{so.offset}')
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='smt',
        description='Surveyor Micro Toolkit - alignment command-line interface.',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    parser_forward = sub.add_parser('station-to-coord', help='station (+offset) -> N,E')
    parser_forward.add_argument('table', help='path to CSV element table')
    parser_forward.add_argument('sta', type=float, help='station (chainage)')
    parser_forward.add_argument('--offset', type=float, default=0.0,
                                help='perpendicular offset (+ right, - left); default 0')
    parser_forward.set_defaults(func=_run_fwd)

    parser_inverse = sub.add_parser('coord-to-station', help='N,E -> station,offset')
    parser_inverse.add_argument('table', help='path to CSV element table')
    parser_inverse.add_argument('n', type=float, help='northing')
    parser_inverse.add_argument('e', type=float, help='easting')
    parser_inverse.set_defaults(func=_run_inv)

    parser_xc = sub.add_parser(
        'cross-check',
        help='locate field survey points on a PI-defined alignment',
    )
    parser_xc.add_argument('alignment', help='PI table CSV (POINT,N,E,Sta,R,Ls,...)')
    parser_xc.add_argument('field',     help='field survey CSV (NAME,N,E,Z,DISC)')
    parser_xc.set_defaults(func=_run_cross_check)

    parser_build = sub.add_parser(
        'build',
        help='build element table + control points from PI table CSV',
    )
    parser_build.add_argument('alignment', help='PI table CSV (POINT,N,E,R,Ls,...)')
    parser_build.add_argument(
        '--out-dir',
        default=None,
        help='output folder (default: same folder as input file)',
    )
    parser_build.set_defaults(func=_run_build)

    parser_cd = sub.add_parser(
        'compare-drawing',
        help='compare drawing control points against calculated coordinates',
    )
    parser_cd.add_argument('elements', help='element table CSV (StaStart,StaEnd,N,E,...)')
    parser_cd.add_argument('drawing',  help='drawing control-point CSV (Name,STA,N,E)')
    parser_cd.add_argument(
        '--tol', type=float, default=0.010,
        help='gap closure tolerance in metres (default 0.010)',
    )
    parser_cd.set_defaults(func=_run_compare_drawing)

    parser_fr = sub.add_parser(
        'fit-radius',
        help='optimise PI radii to minimise coordinate residuals (requires scipy)',
    )
    parser_fr.add_argument('alignment', help='PI table CSV (POINT,N,E,R,...)')
    parser_fr.add_argument('drawing',   help='drawing control-point CSV (Name,STA,N,E)')
    parser_fr.add_argument(
        '--fix', default='',
        help='comma-separated PI names to hold constant (not optimised)',
    )
    parser_fr.add_argument(
        '--tol', type=float, default=1e-6,
        help='Nelder-Mead xatol tolerance (default 1e-6)',
    )
    parser_fr.add_argument(
        '--max-iter', type=int, default=10000,
        help='maximum Nelder-Mead iterations (default 10000)',
    )
    parser_fr.set_defaults(func=_run_fit_radius)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ValueError, FileNotFoundError, ImportError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
