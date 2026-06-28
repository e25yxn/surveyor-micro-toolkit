"""cli - minimal command-line interface for SMT (Application/boundary layer).

Thin wrapper over the alignment core engine.  Does NO geometry maths itself —
it only reads a CSV element table and delegates to alignment.py, then formats
the result for stdout.

Subcommands:
  smt fwd <table.csv> <sta> [--offset 0]   station(+offset) -> N,E
  smt inv <table.csv> <n> <e>              N,E -> sta,offset

CSV format matches the element table (header row required):
  StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
"""
from __future__ import annotations

import argparse
import csv
import sys
from typing import Any

from . import alignment, check
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


def _run_fwd(args: argparse.Namespace) -> int:
    """fwd: station (+offset) -> grid coordinate N,E."""
    elements = _read_alignment(args.table)
    pt = alignment.calculate_station_to_coordinate(elements, args.sta, args.offset)
    print(f'{pt.n},{pt.e}')
    return 0


def _run_inv(args: argparse.Namespace) -> int:
    """inv: grid coordinate N,E -> station,offset."""
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

    parser_forward = sub.add_parser('fwd', help='station (+offset) -> N,E')
    parser_forward.add_argument('table', help='path to CSV element table')
    parser_forward.add_argument('sta', type=float, help='station (chainage)')
    parser_forward.add_argument('--offset', type=float, default=0.0,
                                help='perpendicular offset (+ right, - left); default 0')
    parser_forward.set_defaults(func=_run_fwd)

    parser_inverse = sub.add_parser('inv', help='N,E -> station,offset')
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

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ValueError, FileNotFoundError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
