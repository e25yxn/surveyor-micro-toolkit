# Plan: Bulk Field Cross-Check Feature

## Context

ฟีเจอร์นี้เป็น workflow สำหรับวิศวกรสำรวจ: รับ PI table จาก CSV → สร้าง alignment อัตโนมัติ
→ นำ field points (N, E, Z, disc ที่วัดในสนาม) มาหา station/offset บน alignment → แสดงผลเป็นตาราง
ปัจจุบัน `build_alignment_from_pi` รับ vertex list เป็น Python dict โดยตรง ยังไม่มีทางอ่านจาก CSV
และ `check.py` มีแค่ `check_horizontal` (ตรวจ control points ที่รู้ station แล้ว) ยังไม่มี inverse
สำหรับ field points ที่รู้แค่ N/E

---

## Files to modify

| File | Action |
|------|--------|
| `src/smt/builders/alignment_builder.py` | ADD `parse_pi_table(rows)` |
| `src/smt/check.py` | ADD `FieldCrossCheckResult` + `bulk_cross_check()` |
| `src/smt/cli.py` | ADD `_read_pi_table()`, `_read_field_csv()`, `_run_cross_check()`, register subcommand |
| `tests/builders/test_alignment_builder.py` | ADD `TestParsePiTable` class |
| `tests/test_check.py` | ADD `TestBulkCrossCheck` class |
| `tests/test_cli.py` | ADD cross-check CLI tests |

---

## Part 1 — `parse_pi_table(rows)` in `builders/alignment_builder.py`

### CSV column order (position-based, names ignored)

```
col  0: POINT      — 'BP' | 'EP' | any non-blank string = PI | blank = compound sub-row
col  1: N          — northing (blank for compound sub-rows)
col  2: E          — easting  (blank for compound sub-rows)
col  3: Sta        — starting chainage (BP only; blank elsewhere)
col  4: R          — radius in metres; blank or '0' = angle point (EXT-001)
col  5: Ls         — symmetric spiral length (blank = 0)
col  6: LsIn       — entry spiral length (overrides Ls when non-blank)
col  7: LsOut      — exit spiral length (overrides Ls when non-blank)
col  8: Trans      — CLOTHOID (default) | BLOSS | COSINE | SINE
col  9: Delta      — arc deflection in degrees (compound sub-rows only;
                     blank on LAST arc = takes remainder)
```

**Row classification:**
- POINT non-blank → new vertex (BP / PI / EP)
- POINT blank + R non-blank → compound sub-arc for the preceding PI vertex

**Vertex dict produced per classification:**

| Row type | vertex dict keys |
|----------|-----------------|
| BP | `{'n', 'e', 'sta'}` |
| EP | `{'n', 'e'}` |
| Simple circle PI | `{'n', 'e', 'R'}` |
| Symmetric spiral PI | `{'n', 'e', 'R', 'Ls'}` |
| Asymmetric spiral PI | `{'n', 'e', 'R', 'LsIn', 'LsOut'}` |
| Angle point (R=0 or blank) | `{'n', 'e'}` (no 'R' key → builder treats as angle point) |
| Compound PI + sub-rows | `{'n', 'e', 'compound': [{'R', 'delta'}, ..., {'R'}]}` |

---

## Part 2 — `bulk_cross_check()` in `check.py`

New `FieldCrossCheckResult(NamedTuple)`: name, n, e, z, sta, offset, disc

`bulk_cross_check(elements, field_points)` → runs inverse (N,E → sta,offset) per point,
carries disc through unchanged. Raises ValueError for out-of-alignment points.

---

## Part 3 — CLI: `smt cross-check <alignment_pi.csv> <field.csv>`

New subcommand via argparse. Reads PI CSV with `_read_pi_table()`, builds alignment,
reads field CSV with `_read_field_csv()`, calls `bulk_cross_check()`, prints fixed-width table.

Field CSV columns: NAME, N, E, Z, DISC (DISC optional, defaults 0.0)

---

## Part 4 — Tests

- `TestParsePiTable` in `tests/builders/test_alignment_builder.py` (11 cases)
- `TestBulkCrossCheck` in `tests/test_check.py` (8 cases)
- CLI tests in `tests/test_cli.py` (4 cases)

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Compound sub-row with blank R → blank line confusion | Only collect arc when r_raw non-empty |
| Delta in degrees vs radians | parse_pi_table passes degrees; builder calls deg_to_rad internally |
| New CLI imports → circular deps? | builders → alignment → fpmath (no circle) |
| Regression on 341 tests | All new code additive; run pytest after each part |
