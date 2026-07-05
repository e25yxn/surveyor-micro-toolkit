# Plan: Fix `_flush_pending` silently discarding a PI's RADIUS when a compound sub-row follows

## Context

`CLAUDE.md` Known limits (recorded 2026-07-03) flags that `alignment_builder.py::parse_pi_table`'s
`_flush_pending` silently drops a PI vertex's own `RADIUS` whenever a compound sub-row
follows it, with no error — and that `test_data/SettingOutTest.csv`'s PI7 is affected and
must not be used as a reference until fixed. This plan fixes the root cause (a defensive
`ValueError` instead of silent data loss), fixes the affected CSV row, and adds
regression tests — verified end-to-end via real, in-memory computation before writing
anything (all commands below were actually run, not assumed).

## One — current code, confirmed to match the known-bug description

`src/smt/builders/alignment_builder.py` lines 246-302 (`parse_pi_table`, the relevant
slice):

```python
vertices: list[dict[str, Any]] = []
pending_pi: dict[str, Any] | None = None
compound_arcs: list[dict[str, Any]] = []

def _flush_pending() -> None:
    nonlocal pending_pi
    if pending_pi is None:
        return
    if compound_arcs:
        v: dict[str, Any] = {'n': pending_pi['n'], 'e': pending_pi['e']}
        v['compound'] = compound_arcs.copy()
        compound_arcs.clear()
    else:
        v = dict(pending_pi)
    vertices.append(v)
    pending_pi = None

for row in rows[1:]:            # skip header row
    point = _g(row, 'point')

    if not point:
        # compound sub-row — only meaningful when R is non-blank
        r_raw = _g(row, 'radius')
        if not r_raw:
            continue
        arc: dict[str, Any] = {'R': float(r_raw)}
        delta_raw = _g(row, 'delta')
        if delta_raw:
            arc['delta'] = float(delta_raw)
        compound_arcs.append(arc)
        continue

    _flush_pending()

    n = float(_g(row, 'northing'))
    e = float(_g(row, 'easting'))
    ...
    # PI vertex
    pi_dict: dict[str, Any] = {'n': n, 'e': e}
    r_raw = _g(row, 'radius')
    if r_raw and float(r_raw) != 0.0:
        pi_dict['R'] = float(r_raw)
        ...
    pending_pi = pi_dict
```

Confirmed the bug directly (read-only, no files written): parsing the current
`test_data/SettingOutTest.csv` gives PI7's vertex as
`{'n': 1565169.659, 'e': 680911.287, 'compound': [{'R': 150.0}]}` — the PI row's own
`R=300` (and its `Delta=20`, which `parse_pi_table` never even reads for a PI row) are
gone with no trace, no error. Building it: `result.issues == []`, and the actual element
at that location is a **single** `C, R=150.0` circular arc spanning the entire PI7
deflection (`sta 4364.414-4495.314`) — matching the reported behavior exactly ("became
one R=150 circle covering the whole angle").

## Two — defensive check design (FULL, exact code to be inserted)

Add the check where `_flush_pending` currently discards `pending_pi['R']`, plus PI
label/line tracking (not currently kept anywhere) so the error message can name the
offending row. This is the complete replacement for the current
`vertices`/`pending_pi`/`compound_arcs`/`_flush_pending`/parse-loop block inside
`parse_pi_table`:

```python
    vertices: list[dict[str, Any]] = []
    pending_pi: dict[str, Any] | None = None
    pending_pi_label: str = ''
    pending_pi_line: int = 0
    compound_arcs: list[dict[str, Any]] = []

    def _flush_pending() -> None:
        nonlocal pending_pi
        if pending_pi is None:
            return
        if compound_arcs:
            if 'R' in pending_pi:
                raise ValueError(
                    f'PI "{pending_pi_label}" (แถวที่ {pending_pi_line}) มีทั้งค่า RADIUS '
                    f'({pending_pi["R"]}) และมี compound sub-row ตามมา '
                    'กำกวมว่าจะใช้ค่ารัศมีไหน '
                    'ให้ปล่อย RADIUS ของแถว PI นี้ว่างไว้ '
                    'แล้วย้ายค่า RADIUS (และ Delta ถ้ามี) '
                    'ไปเป็นแถว compound sub-row แยกต่างหากแทน'
                )
            v: dict[str, Any] = {'n': pending_pi['n'], 'e': pending_pi['e']}
            v['compound'] = compound_arcs.copy()
            compound_arcs.clear()
        else:
            v = dict(pending_pi)
        vertices.append(v)
        pending_pi = None

    for line_no, row in enumerate(rows[1:], start=2):   # start=2: row 1 is the header
        point = _g(row, 'point')

        if not point:
            # compound sub-row — only meaningful when R is non-blank
            r_raw = _g(row, 'radius')
            if not r_raw:
                continue
            arc: dict[str, Any] = {'R': float(r_raw)}
            delta_raw = _g(row, 'delta')
            if delta_raw:
                arc['delta'] = float(delta_raw)
            compound_arcs.append(arc)
            continue

        _flush_pending()

        n = float(_g(row, 'northing'))
        e = float(_g(row, 'easting'))

        if point == 'BP':
            sta_raw = _g(row, 'sta')
            vertices.append({'n': n, 'e': e, 'sta': float(sta_raw) if sta_raw else 0.0})
            continue

        if point == 'EP':
            vertices.append({'n': n, 'e': e})
            continue

        # PI vertex
        pi_dict: dict[str, Any] = {'n': n, 'e': e}
        r_raw = _g(row, 'radius')
        if r_raw and float(r_raw) != 0.0:
            pi_dict['R'] = float(r_raw)
            ls_raw    = _g(row, 'ls')
            lsin_raw  = _g(row, 'lsin')
            lsout_raw = _g(row, 'lsout')
            if lsin_raw or lsout_raw:
                if lsin_raw:
                    pi_dict['LsIn'] = float(lsin_raw)
                if lsout_raw:
                    pi_dict['LsOut'] = float(lsout_raw)
            elif ls_raw:
                pi_dict['Ls'] = float(ls_raw)
            trans = _g(row, 'trans')
            if trans:
                pi_dict['trans'] = trans
        # else: R absent or 0 → angle point (no 'R' key); may gain 'compound' later

        pending_pi = pi_dict
        pending_pi_label = point
        pending_pi_line = line_no

    _flush_pending()
    return vertices
```

Changed lines vs. current code, precisely:
- Added `pending_pi_label: str = ''` and `pending_pi_line: int = 0` (new local state).
- Inside `_flush_pending`, added the `if 'R' in pending_pi: raise ValueError(...)` guard
  before the existing `v = {...}; v['compound'] = ...` lines.
- Changed `for row in rows[1:]:` to `for line_no, row in enumerate(rows[1:], start=2):`.
- Added `pending_pi_label = point` and `pending_pi_line = line_no` right after
  `pending_pi = pi_dict`.
- Everything else in the loop (BP/EP handling, R/Ls/LsIn/LsOut/trans parsing) is
  byte-for-byte unchanged.

**Verified in-memory** (exact simulation of this code, not a hypothetical): raises
`PI "PI" (แถวที่ 3) มีทั้ง RADIUS (300.0) และมี compound sub-row ตามมา` for an ambiguous
PI+compound row; does **not** raise for `R=0` explicit + compound (returns
`{'n':1100.0,'e':2100.0,'compound':[{'R':300.0,'delta':20.0},{'R':150.0}]}` correctly);
and against the **current, unfixed** `SettingOutTest.csv`, raises
`PI "PI7" (แถวที่ 9) มีทั้ง RADIUS (300.0) และมี compound sub-row ตามมา` — line 9 matches
the real file exactly, confirming the fix must land together with the CSV fix (step 4)
or `smt build` on the current file breaks hard instead of silently mis-building.

## Three — new regression tests, FULL text (`tests/builders/test_alignment_builder.py`,
## to be added inside `TestParsePiTable`, right after `test_compound_last_arc_no_delta`)

```python
    def test_pi_radius_with_compound_raises_value_error(self):
        # PI row itself has a non-blank, non-zero RADIUS *and* is followed by a
        # compound sub-row -- ambiguous which radius applies. Regression test for the
        # _flush_pending bug (CLAUDE.md Known limits; test_data/SettingOutTest.csv PI7).
        rows = _rows(
            ['BP', '1000', '2000', '0',  '', '', '', '', '', ''],
            ['PI', '1100', '2100', '',  '300', '', '', '', '', '20'],
            ['',   '',     '',     '',  '150', '', '', '', '', ''],
            ['EP', '1200', '2200', '',  '', '', '', '', '', ''],
        )
        with pytest.raises(ValueError):
            ab.parse_pi_table(rows)

    def test_pi_radius_zero_with_compound_still_works(self):
        # R=0 (explicit angle point) on the PI row, followed by a compound sub-row,
        # is the *correct* way to write this and must not raise -- same pattern
        # already proven by test_compound(), checked here explicitly against R=0
        # (not just blank).
        rows = _rows(
            ['BP', '1000', '2000', '0',  '', '', '', '', '', ''],
            ['PI', '1100', '2100', '',  '0', '', '', '', '', ''],
            ['',   '',     '',     '',  '300', '', '', '', '', '20'],
            ['',   '',     '',     '',  '150', '', '', '', '', ''],
            ['EP', '1200', '2200', '',  '', '', '', '', '', ''],
        )
        pi = ab.parse_pi_table(rows)[1]
        assert 'R' not in pi
        assert pi['compound'] == [{'R': 300.0, 'delta': 20.0}, {'R': 150.0}]
```

(`test_compound` and `test_compound_last_arc_no_delta`, both already passing, already
cover the blank-`R` + compound case — cited as existing coverage, not duplicated.)

## Four — `test_data/SettingOutTest.csv` PI7 fix, FULL before/after diff

Current file, lines 9-10 (out of the whole file, unchanged elsewhere):
```
PI7,,1565169.659,680911.287,300,,,,,20
,,,,150,,,,,
```

New (3 lines replacing the above 2; matches the `test_compound()`-validated pattern —
PI row's own RADIUS/Delta blank, both arcs as sub-rows):
```
PI7,,1565169.659,680911.287,,,,,,
,,,,300,,,,,20
,,,,150,,,,,
```

Unified diff view:
```diff
-PI7,,1565169.659,680911.287,300,,,,,20
-,,,,150,,,,,
+PI7,,1565169.659,680911.287,,,,,,
+,,,,300,,,,,20
+,,,,150,,,,,
```

Every other line in `test_data/SettingOutTest.csv` (BP, PI1-PI6, PI8-PI11, EP, and the
trailing blank lines) stays byte-for-byte identical — only these 2 lines become 3.

**Verified in-memory** with the fixed parser + this exact row substitution: PI7 parses
to `{'n': 1565169.659, 'e': 680911.287, 'compound': [{'R': 300.0, 'delta': 20.0}, {'R': 150.0}]}`,
`build_alignment_from_pi` reports `issues == []`, and the built elements at that station
range are now **two** circular arcs — `C R=300.0` (sta 4320.702-4425.421) then
`C R=150.0` (sta 4425.421-4503.961) — replacing the old single `C R=150.0` spanning the
entire deflection.

## Five — live CLI verification (to run after the code+CSV changes land)

```
smt build test_data/SettingOutTest.csv --out-dir test_data/build_out
```
Show the PI7-area elements from the output and compare directly against the "before"
evidence in section One (single R=150 arc) — confirmed compound R=300→R=150 replaces it,
matching section Four's in-memory prediction exactly.

## Six — no existing test depends on `SettingOutTest.csv` (verified, not assumed)

Grepped the whole repo (`Grep` tool, not a guess) for the literal string
`SettingOutTest`: 9 files match, **all** are docs/session-log prose or generated
`.xml`/nothing under `tests/` — `CLAUDE.md`, `docs/SMT_CLI_Manual.md`,
`docs/SMT_Python_Manual.md`, `session_logs/latest.md`,
`session_logs/plan_build_20260628_1902.md`, `session_logs/plan_landxml_20260630_1200.md`,
`session_logs/test_compound_030726_1617.md`, `test_data/SettingOutTest.xml`,
`test_data/SettingOutTest2.xml`. Separately confirmed no test reads `test_data/`
generically either: the only `test_data` reference in any `tests/*.py` file is
`tests/test_optimizer.py`, and it only ever opens `ramp01n01_SO.csv` /
`r01n01_so_crosscheck.csv` — never `SettingOutTest.csv`. **No pytest test is affected
by this fix.**

## Note on how this plan was produced (transparency)

While researching sections One/Five, I mistakenly ran
`smt build --out-dir test_data/build_out_before_check` (a real file-writing command)
while supposed to be in a read-only investigation phase under plan mode. Caught it
immediately, confirmed via `git status` that the output directory is gitignored and
untracked (no tracked file was affected), and deleted it. All evidence in this plan from
that point on (sections One, Two, Four) was re-derived using pure in-memory Python
(parsing + building without writing any file).

## Verification (after implementation)

- `pytest -q` — full suite, expect the 2 new tests to pass and nothing else to change
  (confirmed above that no other test touches this code path with a compound+R PI).
- The live CLI run in step Five, comparing before/after PI7 elements directly.
