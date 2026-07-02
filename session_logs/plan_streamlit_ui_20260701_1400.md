# Plan: Streamlit web UI (app.py) — 5 tabs wrapping the SMT CLI commands

## Context
The SMT core engine is complete (`src/smt/`) and exposed via a CLI (`smt build`,
`smt cross-check`, `smt compare-drawing`, `smt fit-radius`, `smt export-landxml`).
The user wants a browser UI (`app.py` at the project root, run with
`streamlit run app.py`) so a non-CLI user can upload CSVs, run each of these 5
operations, see the result as a table, and download it — without touching the
terminal. The UI must call `src/smt` functions directly (no `subprocess`/CLI
shell-out), since the CLI's own file-reading helpers (`_read_pi_table`,
`_read_field_csv`, `_read_drawing_csv`, `_read_alignment` in `src/smt/cli.py`)
are private, path-based (`open(path)`), and not reusable for Streamlit's
in-memory uploaded files.

This is revision 2 of the plan, correcting 3 issues found on review of
revision 1 before implementation started:
1. `parse_field_points`'s `disc` default must match `cli.py::_read_field_csv`
   exactly (empty string `''`, not `0.0`).
2. The Fit Radius tab's verification table must carry a separate `status`
   column (`OK` / `OUTSIDE_ALIGNMENT`) instead of stuffing the string
   `OUTSIDE_ALIGNMENT` into the numeric `calc_N`/`calc_E`/`gap_m` columns —
   the CLI can mix text into a printed column, but a `st.dataframe` needs
   uniform column dtypes.
3. The 4 pure CSV-parsing helpers move out of `app.py` into a new
   `src/smt/webhelpers.py` that never imports `streamlit`, so tests don't
   depend on Streamlit's import-outside-runtime behaviour.

No code has been written yet — this is still the spec to review before
implementation begins.

## File layout
- New file: `src/smt/webhelpers.py` — the 4 pure CSV-parsing helpers
  (`read_csv_rows`, `parse_field_points`, `parse_drawing_points`,
  `parse_element_rows`). No `import streamlit` anywhere in this file.
- New file: `app.py` (project root, single file, per user's request) —
  imports the 4 helpers from `smt.webhelpers`; contains only Streamlit UI
  code (tabs, widgets, dataframes) plus the CLI-derived formatting logic that
  is Streamlit-specific (e.g. the Build tab's `_radius_from_element`
  reimplementation).
- Edit: `pyproject.toml` — add `[project.optional-dependencies] ui = ["streamlit>=1.30"]`
- New file: `tests/test_app_helpers.py` — unit tests for the 4 pure helpers,
  imported directly from `smt.webhelpers` (`from smt.webhelpers import ...`),
  not from `app`.
- Log as usual to `session_logs/latest.md` per CLAUDE.md §1 once implementation starts.

## src/smt/webhelpers.py

```python
"""webhelpers - pure CSV-parsing helpers shared by app.py and its tests.

No streamlit import. Mirrors the row-parsing bodies of the private CLI
helpers in cli.py (_read_field_csv, _read_drawing_csv, _read_alignment) but
operates on already-decoded row lists / raw bytes instead of a filesystem
path, so callers can feed it Streamlit's in-memory uploaded-file content
without either side depending on the other.
"""
from __future__ import annotations
import csv, io
from typing import Any

def read_csv_rows(raw_bytes: bytes) -> list[list[str]]:
    text = io.StringIO(raw_bytes.decode("utf-8"))
    return list(csv.reader(text))

def parse_field_points(rows: list[list[str]]) -> list[dict[str, Any]]:
    ...  # mirrors cli.py::_read_field_csv body exactly:
    # padded = line + [''] * 5; name/n/e/z as before;
    # disc = padded[4].strip()  -> default '' (empty string), NOT 0.0

def parse_drawing_points(rows: list[list[str]]) -> list[dict[str, Any]]: ...
def parse_element_rows(rows: list[list[str]]) -> list[list[Any]]: ...  # numeric coercion, mirrors _read_alignment
```

These are plain functions — no Streamlit import, no `st.*` calls — so
`tests/test_app_helpers.py` can `from smt.webhelpers import ...` and call them
directly, independent of whether Streamlit is installed.

## app.py structure

```python
"""app - Streamlit web UI over the SMT core engine (Application/boundary layer).

Thin wrapper: parses uploaded CSVs into the same in-memory structures the CLI
builds, then delegates to src/smt. Does NO geometry maths itself.
"""
from __future__ import annotations
import math

import streamlit as st

from smt import alignment, check, fpmath
from smt.builders.alignment_builder import build_alignment_from_pi, parse_pi_table
from smt.landxml import export_alignment_landxml
from smt.webhelpers import (
    read_csv_rows, parse_field_points, parse_drawing_points, parse_element_rows,
)
# optimizer.fit_radius is imported lazily inside the fit-radius tab (scipy optional)

# ---- Streamlit page ---------------------------------------------------------
st.set_page_config(page_title="SMT Toolkit", layout="wide")
st.title("Surveyor Micro Toolkit")

tab_build, tab_xc, tab_cd, tab_fr, tab_lx = st.tabs(
    ["Build", "Cross-Check", "Compare Drawing", "Fit Radius", "Export LandXML"]
)

with tab_build: ...   # see per-tab spec below
with tab_xc: ...
with tab_cd: ...
with tab_fr: ...
with tab_lx: ...
```

At each upload site, `app.py` adapts Streamlit's `UploadedFile` to the pure
helper's `bytes` signature: `rows = read_csv_rows(uploaded_file.getvalue())`.

## Per-tab spec

### 1. Build tab
- Uploader: 1 file — PI table CSV (`st.file_uploader("PI table CSV", type="csv", key="build_pi")`)
- Run button → on click:
  ```python
  rows = read_csv_rows(uploaded.getvalue())
  vertices = parse_pi_table(rows)          # builders/alignment_builder.py
  result = build_alignment_from_pi(vertices)  # -> BuildResult(elements, control, issues)
  ```
- Show `result.issues` as `st.warning(...)` per item (mirrors CLI's `print(f'warning: ...', file=sys.stderr)`)
- Build two `st.dataframe`s:
  - Elements: columns `StaStart, StaEnd, N, E, Azimuth, Radius, Type, Transition`
    (same formatting logic as `cli.py::_run_build` — `fpmath.rad_to_deg(el.azimuth)`,
    a local `_radius_from_element(el)` reimplementation for signed radius, `''`
    for Transition when `el.type in ('T','C')`)
  - Control points: columns `Name, STA, N, E` from `result.control`
- Two `st.download_button`s, one per dataframe, `file_name="elements_output.csv"`
  / `"controls_so_output.csv"`, using `dataframe.to_csv(index=False)` — matching
  the CLI's own output file names/headers exactly.

### 2. Cross-Check tab
- Uploaders: 2 files — PI table CSV, field survey CSV (`NAME,N,E,Z,DISC`)
- Run:
  ```python
  vertices = parse_pi_table(read_csv_rows(pi_file.getvalue()))
  result = build_alignment_from_pi(vertices)
  field_points = parse_field_points(read_csv_rows(field_file.getvalue()))  # smt.webhelpers
  rows = check.bulk_cross_check(result.elements, field_points)  # -> list[FieldCrossCheckResult]
  ```
- `st.dataframe` columns: `NAME, STA, OFFSET, N, E, Z, DISC` (from `FieldCrossCheckResult`
  fields `name, sta, offset, n, e, z, disc`). `DISC` cells will be `''` when the
  source CSV omitted the column, matching CLI behaviour exactly.
- `st.download_button` → CSV of that table.

### 3. Compare Drawing tab
- Uploaders: 2 files — element table CSV (`StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition`),
  drawing control-point CSV (`Name,STA,N,E`)
- `st.number_input("tolerance (m)", value=0.010, format="%.3f")` — matches CLI `--tol` default
- Run:
  ```python
  elements = alignment.parse_alignment_table(parse_element_rows(read_csv_rows(elements_file.getvalue())))
  points = parse_drawing_points(read_csv_rows(drawing_file.getvalue()))  # smt.webhelpers
  ```
  For each point: skip (mark `HIP`) if name starts with `PI`/`HIP` (case-insensitive,
  same rule as CLI); else `alignment.calculate_station_to_coordinate(elements, sta, 0.0)`,
  compute `delta_n, delta_e, gap_m = hypot(...)`, `OK`/`FAIL` against tolerance.
- `st.dataframe` columns: `Name, STA, draw_N, draw_E, calc_N, calc_E, delta_N, delta_E, gap_m, status`
- `st.download_button` → CSV.

### 4. Fit Radius tab
- **scipy check first**, before showing the run button:
  ```python
  try:
      import scipy  # noqa: F401
      scipy_available = True
  except ImportError:
      scipy_available = False
      st.error("scipy not installed — fit-radius requires it. "
               "Install with: pip install 'surveyor-micro-toolkit[optimize]'")
  ```
  Disable/hide the run button when `scipy_available` is False (`st.button(..., disabled=not scipy_available)`).
- Uploaders: 2 files — PI table CSV, drawing control-point CSV
- Inputs: `st.text_input("fix names (comma-separated)", value="")`,
  `st.number_input("tol", value=1e-6, format="%.2e")`,
  `st.number_input("max_iter", value=10000, step=1000)`
- Run:
  ```python
  from smt.optimizer import fit_radius
  pi_rows = read_csv_rows(pi_file.getvalue())            # raw rows, NOT parsed — fit_radius wants raw csv rows
  drawing_points = parse_drawing_points(read_csv_rows(drawing_file.getvalue()))
  fix_names = [s.strip() for s in fix_text.split(',') if s.strip()] or None
  result = fit_radius(pi_rows, drawing_points, fix_names, tol, max_iter)  # -> FitResult
  ```
  Wrap the call itself in `try/except ImportError` too (belt-and-braces — the
  upfront check covers the common case, but this catches it if scipy import
  fails deeper inside optimizer.py).
- Show: a small metrics row (`st.metric("gap_before", ...)`, `st.metric("gap_after", ...)`,
  converged/iterations as text), then `st.dataframe` of
  `PI, R_initial, R_optimized` (from `result.names, result.r_initial, result.r_optimized`).
- Optional verification table (gap after optimisation per drawing point) —
  reimplement the CLI's patch-and-rebuild block (`cli.py` lines 252–291): patch
  `pi_rows` with optimized R values, `parse_pi_table` + `build_alignment_from_pi`,
  then `alignment.calculate_station_to_coordinate` per non-PI/HIP drawing point.
  **Columns: `Name, STA, calc_N, calc_E, gap_m, status`** — a dedicated `status`
  column holding `'OK'` or `'OUTSIDE_ALIGNMENT'`, kept separate from the
  numeric columns (unlike the CLI's text-only print at `cli.py` line 289,
  which puts the literal string `OUTSIDE_ALIGNMENT` where the numbers would
  go). When `calculate_station_to_coordinate` raises `ValueError`/`IndexError`
  for a point, set `status = 'OUTSIDE_ALIGNMENT'` and leave `calc_N`,
  `calc_E`, `gap_m` as `None` for that row (not the string) so the dataframe
  column stays numeric/`NaN`-typed instead of mixed-type. Show as a second
  `st.dataframe`. Wrap the whole block in try/except like the CLI does
  (`warning: verification table failed: ...` → `st.warning(...)`).
- `st.download_button` → CSV of the R_initial/R_optimized table.

### 5. Export LandXML tab
- Uploader: 1 file — PI table CSV
- Inputs: `st.text_input("alignment name", value="alignment")`
- Run:
  ```python
  vertices = parse_pi_table(read_csv_rows(pi_file.getvalue()))
  result = build_alignment_from_pi(vertices)
  xml_str = export_alignment_landxml(result, name=name)  # -> str
  ```
- Show `result.issues` as `st.warning(...)`.
- Display: `st.code(xml_str, language="xml")` (a table doesn't apply to XML text
  output, so this tab shows code + download instead of a dataframe — call this
  out explicitly since it's the one tab that isn't primarily a CSV round-trip).
- `st.download_button("Download LandXML", xml_str, file_name=f"{name}.xml", mime="application/xml")`.

## Shared parsing helpers — exact CLI parity

`smt.webhelpers` reproduces each CLI helper's row→dict/row→float conversion
exactly:
- `parse_pi_table(rows)` — pass raw rows straight through to the existing
  public function in `builders/alignment_builder.py` (already accepts `list[Any]`).
- `parse_field_points(rows)` — reimplementation of `cli.py::_read_field_csv`'s
  body (`name/n/e/z/disc`, blank-line tolerant). **`disc` defaults to `''`
  (empty string), matching `padded[4].strip()` in `cli.py` line 88 — not
  `0.0`.** (`_read_field_csv`'s docstring says "defaults to 0.0", but that's
  stale relative to its own implementation; `webhelpers.py` must match the
  actual code, not the stale docstring.)
- `parse_drawing_points(rows)` — reimplementation of `cli.py::_read_drawing_csv`'s
  body (`name/sta/n/e`, blank-line tolerant).
- `parse_element_rows(rows)` — reimplementation of `cli.py::_read_alignment`'s
  numeric-coercion loop (float StaStart/StaEnd/N/E/Azimuth/Radius, blank Radius→0.0,
  Type/Transition as stripped strings), returning rows for `alignment.parse_alignment_table`.

## Error handling (every tab)

Wrap each tab's "Run" button body in `try/except Exception as exc: st.error(f"...: {exc}")`
so a bad CSV (wrong column count, non-numeric cell, empty file) or a geometry
error (`ValueError` from core functions) shows a red banner instead of crashing
the app. Catch broadly here (unlike the core engine, which must stay
exception-precise) since this is the outermost UI boundary — matches the
CLI's own top-level `try/except` in `main()`.

## Dependency addition

`pyproject.toml` — add a new optional-dependency group, consistent with the
existing `dev`/`docs`/`notebook`/`optimize` groups:
```toml
[project.optional-dependencies]
...
ui = ["streamlit>=1.30"]
```
Run with: `pip install -e ".[ui]"` then `streamlit run app.py`.
(`fit-radius` tab additionally needs `pip install -e ".[optimize]"` for scipy —
already an existing extras group, just needs both installed together for that tab.)

## Tests

`tests/test_app_helpers.py` — unit tests (pytest, no Streamlit test harness
needed, no Streamlit dependency at all) for the 4 pure helpers in
`smt.webhelpers`, using small in-memory CSV byte strings (`b"..."`) to stand
in for uploaded-file content:
- `read_csv_rows` — round-trips a simple 2-row CSV.
- `parse_field_points` — with a DISC column, and without one (asserts the
  missing-DISC default is `''`, not `0.0`); blank-line tolerance.
- `parse_drawing_points` — standard `Name,STA,N,E` rows; blank-line tolerance.
- `parse_element_rows` — numeric coercion incl. blank Radius → 0.0.

Follows the existing `tests/test_*.py` naming/style already in the repo
(`tests/test_cli.py` is the closest analog).

## Verification (after implementation)

1. `pytest tests/test_app_helpers.py -q` — new helper tests green (importable
   with or without `streamlit` installed, since `smt.webhelpers` has no
   Streamlit dependency).
2. `pytest -q` — full suite still 407+/407 green (no core files touched).
3. `pip install -e ".[ui,optimize]"` then `streamlit run app.py` — manually
   exercise all 5 tabs against files in `test_data/` (e.g. the PI table and
   `test_data/build_out/elements_output.csv` / `controls_so_output.csv` already
   in the repo) and confirm each produces a table + working download button;
   confirm the Fit Radius verification table shows a clean `status` column
   (no text bleeding into numeric columns) when a drawing point falls outside
   the alignment; and confirm an intentionally malformed CSV shows `st.error`
   instead of crashing.
4. Confirm `smt` CLI commands still behave identically (no changes to `src/smt/cli.py`).
