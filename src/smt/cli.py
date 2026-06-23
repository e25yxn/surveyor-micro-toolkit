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

from . import alignment


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

    rows: list = [raw[0]]   # keep header row as-is; parse_alignment_table skips it
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

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
