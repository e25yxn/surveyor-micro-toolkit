"""table_splitter - Split a mixed PI/drawing-point table into its two feeds.

Some field CSVs (e.g. test_data/HOR_ORR_04.csv) list BP/PI-n/EP vertex rows and
PT/PC/TS/SC/CS/ST drawn control-point rows in one table, interleaved. Neither
parse_pi_table() nor check_against_drawing() accept that shape directly - each
wants only its own subset. split_mixed_alignment_table() is the adapter that
sits in front of both, unchanged.

Depends on: none (pure string/dict reshaping; no geometry).
"""
from __future__ import annotations

import re
from typing import Any

_VERTEX_POINT_RE = re.compile(r'^(BP|PI-\d+|EP)$')

# Maps lowercased header cell text -> canonical column key (mirrors the subset
# of alignment_builder._COL_ALIASES this module needs).
_COL_ALIASES: dict[str, str] = {
    'point':      'point',
    'sta':        'sta',
    'chainage':   'sta',
    'n':          'northing',
    'northing':   'northing',
    'e':          'easting',
    'easting':    'easting',
    'r':          'radius',
    'radius':     'radius',
    'ls':         'ls',
    'spiral':     'ls',
    'lsin':       'lsin',
    'lsout':      'lsout',
    'delta':      'delta',
    'trans':      'trans',
    'transition': 'trans',
}

# Columns that may carry thousands-separator commas (e.g. "1,537,772.85") in
# quoted CSV cells - stripped before handing rows to parse_pi_table(), whose
# float() calls don't tolerate them.
_NUMERIC_KEYS: tuple[str, ...] = (
    'sta', 'northing', 'easting', 'radius', 'ls', 'lsin', 'lsout', 'delta',
)


def _parse_header(header_row: list[Any]) -> dict[str, int]:
    """Return canonical-key -> column-index mapping from the header row."""
    col_map: dict[str, int] = {}
    for i, cell in enumerate(header_row):
        key = _COL_ALIASES.get(str(cell).strip().lower())
        if key is not None and key not in col_map:
            col_map[key] = i
    return col_map


def _strip_thousands_separators(value: str) -> str:
    return value.replace(',', '')


def split_mixed_alignment_table(
    rows: list[list[Any]],
) -> tuple[list[list[Any]], list[dict[str, Any]]]:
    """Split a mixed BP/PI-n/PT/PC/TS/SC/CS/ST/EP table into (vertex_rows, drawing).

    rows[0] is the header row (matched case-insensitively via _COL_ALIASES).

    vertex_rows : [header] + every row whose POINT cell matches ^(BP|PI-\\d+|EP)$,
                  plus any blank-POINT row (a compound sub-row that parse_pi_table()
                  attaches to the preceding PI). Feed straight into parse_pi_table().
    drawing     : {'name', 'sta', 'n', 'e'} dicts built from every remaining
                  non-blank row (PT/PC/TS/SC/CS/ST in practice). Feed straight
                  into check_against_drawing().

    Numeric cells in vertex_rows (sta/northing/easting/radius/ls/lsin/lsout/delta)
    and the sta/n/e values read into drawing have thousands-separator commas
    stripped first, since csv.reader returns quoted "1,537,772.85"-style cells
    as literal strings and neither parse_pi_table() nor float() accept them.
    Fully blank rows (every cell empty) are skipped from both outputs.
    """
    header = rows[0]
    col_map = _parse_header(header)
    vertex_rows: list[list[Any]] = [header]
    drawing: list[dict[str, Any]] = []

    def cell(row: list[Any], key: str) -> str:
        idx = col_map.get(key)
        if idx is None or idx >= len(row):
            return ''
        return str(row[idx]).strip()

    for row in rows[1:]:
        if not row or all(str(c).strip() == '' for c in row):
            continue

        point = cell(row, 'point')
        if not point or _VERTEX_POINT_RE.match(point):
            cleaned = list(row)
            for key in _NUMERIC_KEYS:
                idx = col_map.get(key)
                if idx is not None and idx < len(cleaned):
                    cleaned[idx] = _strip_thousands_separators(str(cleaned[idx]).strip())
            vertex_rows.append(cleaned)
        else:
            drawing.append({
                'name': point,
                'sta': float(_strip_thousands_separators(cell(row, 'sta'))),
                'n':   float(_strip_thousands_separators(cell(row, 'northing'))),
                'e':   float(_strip_thousands_separators(cell(row, 'easting'))),
            })

    return vertex_rows, drawing
