"""webhelpers - pure CSV-parsing helpers shared by app.py and its tests.

No streamlit import. Mirrors the row-parsing bodies of the private CLI
helpers in cli.py (_read_field_csv, _read_drawing_csv, _read_alignment) but
operates on already-decoded row lists / raw bytes instead of a filesystem
path, so callers can feed it Streamlit's in-memory uploaded-file content
without either side depending on the other.
"""
from __future__ import annotations

import csv
import io
from typing import Any


def read_csv_rows(raw_bytes: bytes) -> list[list[str]]:
    """Decode uploaded CSV bytes (utf-8) into a list of row lists."""
    text = io.StringIO(raw_bytes.decode('utf-8'))
    return list(csv.reader(text))


def parse_field_points(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Parse a field survey CSV (NAME,N,E,Z,DISC) into vertex dicts.

    Mirrors cli.py::_read_field_csv. DISC is optional and defaults to ''
    (empty string) — not 0.0 — matching padded[4].strip().
    """
    if not rows:
        raise ValueError('field CSV is empty')
    points = []
    for line in rows[1:]:
        if not line or all(c.strip() == '' for c in line):
            continue
        padded = line + [''] * 5
        name = padded[0].strip()
        n, e, z = float(padded[1]), float(padded[2]), float(padded[3])
        disc = padded[4].strip()
        points.append({'name': name, 'n': n, 'e': e, 'z': z, 'disc': disc})
    return points


def parse_drawing_points(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Parse a drawing control-point CSV (Name,STA,N,E) into vertex dicts.

    Mirrors cli.py::_read_drawing_csv.
    """
    if not rows:
        raise ValueError('drawing CSV is empty')
    points = []
    for line in rows[1:]:
        if not line or all(c.strip() == '' for c in line):
            continue
        name = line[0].strip()
        sta, n, e = float(line[1]), float(line[2]), float(line[3])
        points.append({'name': name, 'sta': sta, 'n': n, 'e': e})
    return points


def parse_element_rows(rows: list[list[str]]) -> list[list[Any]]:
    """Coerce a raw element-table CSV into rows for alignment.parse_alignment_table.

    Mirrors cli.py::_read_alignment's numeric-coercion loop. Columns:
    StaStart, StaEnd, N, E, Azimuth, Radius, Type, Transition. Blank Radius
    is treated as 0.0 (tangent); Type/Transition stay as stripped strings.
    Returns the header row followed by coerced data rows.
    """
    if not rows:
        raise ValueError('element table CSV is empty')
    out: list[list[Any]] = [rows[0]]
    for line in rows[1:]:
        if not line or all(cell.strip() == '' for cell in line):
            continue
        sta_start, sta_end, n, e, az_deg, radius, type_, trans = line[:8]
        out.append([
            float(sta_start),
            float(sta_end),
            float(n),
            float(e),
            float(az_deg),
            float(radius) if str(radius).strip() != '' else 0.0,
            type_.strip(),
            trans.strip(),
        ])
    return out
