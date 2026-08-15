# PLAN — Excel utf-8-sig/BOM handling fix (FINALIZED — verified in sandbox)
**วันที่:** 2026-08-14
**สำหรับ:** Claude Code — apply diff ตรงๆ ได้เลย (ผ่านการทดสอบจริงแล้วในรอบนี้)
**Base commit:** `929ad99` (local = origin/main ตอนเขียนแผนนี้)
**สถานะ:** ✅ implement + test แล้วใน sandbox ของ Claude Chat ครบทุกไฟล์ ผ่านเต็มชุด raw output ด้านล่าง

---

## 0) แก้ไขจากรอบก่อน — เรื่องตัวเลข pytest 529 vs 519

รอบแรกที่ตรวจ HEAD `929ad99` ผมได้ "519 passed, 2 skipped" ไม่ตรงกับ "529 passed" ที่ handoff ระบุ แล้วเดาว่าอาจเป็น typo — **เดาผิด** สาเหตุจริงคือ sandbox ของผมตอนนั้นไม่มี `scipy` ติดตั้ง (`tests/test_optimizer.py`/`tests/test_cli.py::test_fit_radius_basic` ใช้ `pytest.importorskip('scipy', ...)` ข้างในฟังก์ชันเทสเอง ไม่ใช่ mark ระดับไฟล์ ทำให้ยัง collect ครบแต่ skip ตอนรัน) พอติดตั้ง `scipy` แล้วรันซ้ำบน `929ad99` เดิม (ยังไม่แก้อะไร) ได้ `529 passed` **ตรงกับตัวเลขในเอกสารเป๊ะ** — ตัวเลข 529 เดิมถูกต้อง ไม่ใช่ typo ขอโทษที่ทำให้กังวลเรื่องนี้เปล่าๆ

---

## 1) การตัดสินใจที่ยืนยันแล้ว

- **ข้อ 5 (table_splitter.py):** เลือก **(A)** — harden `_parse_header()` ให้ strip BOM เอง ไม่พึ่ง caller
- **ข้อ 6 (BOM-on-write):** ข้าม — อนาคตตารางข้อมูลจะใช้ภาษาอังกฤษล้วน ไม่มีภาษาไทยที่จะเพี้ยนตอนเปิดด้วย Excel โดยตรง

## table_splitter.py มีไว้ทำไม (ตอบคำถามที่ถาม)

เป็น **adapter ที่ยังไม่ได้ต่อเข้า `cli.py`** (เช็คด้วย `grep -rn split_mixed_alignment_table src/` แล้วพบแค่ definition ของมันเอง ไม่มี caller ใน `src/` เลย) — เขียนไว้รองรับสถานการณ์ที่ไฟล์สนามจริงเก็บข้อมูล 2 อย่างปนกันในตารางเดียว:
- แถว BP/PI-n/EP (จุดหมุดที่ใช้สร้างแนวทาง — feed เข้า `parse_pi_table()`)
- แถว PT/PC/TS/SC/CS/ST (จุดควบคุมจากแบบ ใช้เช็คว่าที่สร้างมาตรงแบบไหม — feed เข้า `check_against_drawing()`)

ตัวอย่างจริงคือ `test_data/HOR_ORR_04.csv` — ไฟล์เดียวมีทั้ง 2 แบบปนกัน แต่ `parse_pi_table()`/`check_against_drawing()` แต่ละตัวรับได้แค่ subset ของตัวเอง ฟังก์ชันนี้เลยแยกให้ก่อน มีเทสครบและผ่านมาตลอด แต่ยังไม่ถูกต่อเข้า CLI จริง — เป็นไปได้ว่าเป็นเครื่องมือที่ตั้งใจไว้ใช้แบบ manual/สคริปต์ส่วนตัวเวลาเจอไฟล์สนามแบบผสม หรือรอ wiring เข้า CLI ในอนาคต (backlog แยกต่างหาก ไม่เกี่ยวกับบั๊กนี้)

---

## 2) การเปลี่ยนแปลงจริง (verified diff — ทดสอบแล้ว ไม่ใช่แค่ร่าง)

### `src/smt/builders/table_splitter.py`
```diff
 def _parse_header(header_row: list[Any]) -> dict[str, int]:
-    """Return canonical-key -> column-index mapping from the header row."""
+    """Return canonical-key -> column-index mapping from the header row.
+
+    Strips a leading BOM (U+FEFF) before matching, since Excel's "CSV UTF-8"
+    export prepends one to the file - and hence to the first header cell -
+    which str.strip() alone does not remove.
+    """
     col_map: dict[str, int] = {}
     for i, cell in enumerate(header_row):
-        key = _COL_ALIASES.get(str(cell).strip().lower())
+        key = _COL_ALIASES.get(str(cell).lstrip('\ufeff').strip().lower())
         if key is not None and key not in col_map:
             col_map[key] = i
     return col_map
```

### `src/smt/cli.py` — 5 จุดอ่าน (ไม่แตะจุดเขียน บรรทัด 146/153/323)
บรรทัด ~40 (`_read_alignment`), ~65 (`_read_pi_table`), ~77 (`_read_field_csv`), ~95 (`_read_drawing_csv`), ~230 (`_run_fit_radius`) — ทุกจุดเปลี่ยนแบบเดียวกัน:
```diff
-    with open(path, newline='', encoding='utf-8') as f:
+    with open(path, newline='', encoding='utf-8-sig') as f:
```
(จุดที่ 230 ตัวแปรชื่อ `args.alignment` ไม่ใช่ `path` แต่ pattern เดียวกัน)

**Mechanical check หลังแก้:** `grep -c "encoding='utf-8'" src/smt/cli.py` ต้องได้ **3** (146, 153, 323 — เขียนทั้งหมด) และ `grep -c "encoding='utf-8-sig'" src/smt/cli.py` ต้องได้ **5**

### `src/smt/webhelpers.py`
```diff
 def read_csv_rows(raw_bytes: bytes) -> list[list[str]]:
-    """Decode uploaded CSV bytes (utf-8) into a list of row lists."""
-    text = io.StringIO(raw_bytes.decode('utf-8'))
+    """Decode uploaded CSV bytes (utf-8, tolerates a leading BOM) into a list of row lists."""
+    text = io.StringIO(raw_bytes.decode('utf-8-sig'))
     return list(csv.reader(text))
```

### `tests/test_cli.py` — เพิ่ม fixture + 2 เทส
เพิ่มหลัง fixture `pi_csv` เดิม (บรรทัด ~129):
```python
@pytest.fixture()
def pi_csv_bom(tmp_path):
    """Same PI table, but saved the way Excel's 'CSV UTF-8' export does (leading BOM)."""
    p = tmp_path / 'pi_bom.csv'
    p.write_text(_PI_TABLE, encoding='utf-8-sig')
    return str(p)
```
เพิ่มหลัง `test_build_default_out_dir` เดิม:
```python
def test_build_with_bom_header_succeeds(pi_csv_bom, tmp_path, capsys):
    """Excel's 'CSV UTF-8' export prepends a BOM to the POINT header cell -
    must not break parse_pi_table()'s column lookup."""
    rc = cli.main(['build', pi_csv_bom, '--out-dir', str(tmp_path)])
    assert rc == 0
    assert (tmp_path / 'elements_output.csv').exists()
```
เพิ่มหลัง `test_fit_radius_basic` เดิม:
```python
def test_fit_radius_with_bom_header_succeeds(pi_csv_bom, drawing_csv, capsys):
    """Same BOM concern as smt build - fit_radius() locates POINT/RADIUS by
    header name too."""
    pytest.importorskip('scipy', reason='scipy not installed; pip install surveyor-micro-toolkit[optimize]')
    rc = cli.main(['fit-radius', pi_csv_bom, drawing_csv])
    assert rc == 0
```

### `tests/builders/test_table_splitter.py` — เพิ่มเทสท้าย `TestColumnAliases`
เพิ่มหลัง `test_station_header_recognized_as_sta` เดิม (ท้ายไฟล์):
```python
    def test_bom_prefixed_point_header_recognized(self):
        # Excel's "CSV UTF-8" export prepends a BOM (U+FEFF) to the file, which
        # lands on the first header cell (e.g. '\ufeffPOINT'). str.strip() alone
        # does not remove it, so the column lookup used to silently fail to find
        # 'point' - every row's point cell then read as '', collapsing the whole
        # drawing list to empty instead of raising anything.
        rows = [
            ['\ufeffPOINT', 'STA', 'N', 'E'],
            ['BP', '0', '1000', '2000'],
            ['PC', '50', '1050', '2000'],
            ['PT', '150', '1100', '2050'],
            ['EP', '200', '1100', '2100'],
        ]
        vertex_rows, drawing = split_mixed_alignment_table(rows)
        assert drawing == [
            {'name': 'PC', 'sta': 50.0, 'n': 1050.0, 'e': 2000.0},
            {'name': 'PT', 'sta': 150.0, 'n': 1100.0, 'e': 2050.0},
        ]
```

---

## 3) ผลทดสอบจริงใน sandbox (raw output — ก่อนส่งให้ Claude Code)

เต็มชุดหลังแก้ครบทุกจุดข้างบน:
```
532 passed in 1.65s
```
(529 baseline ที่ยืนยันแล้วในข้อ 0 + 3 เทสใหม่ = 532 ตรงเป๊ะ)

เฉพาะเทสใหม่:
```
$ pytest -q -k bom -v
tests/builders/test_table_splitter.py .                                  [ 33%]
tests/test_cli.py ..                                                     [100%]
3 passed, 529 deselected in 0.48s
```

`git diff --stat`:
```
 src/smt/builders/table_splitter.py    |  9 +++++++--
 src/smt/cli.py                        | 10 +++++-----
 src/smt/webhelpers.py                 |  4 ++--
 tests/builders/test_table_splitter.py | 19 +++++++++++++++++++
 tests/test_cli.py                     | 24 ++++++++++++++++++++++++
 5 files changed, 57 insertions(+), 9 deletions(-)
```
ตรงตามขอบเขตที่วางแผนไว้ ไม่มีไฟล์อื่นติดมา — **ไม่แตะ `alignment_builder.py`/`vertical_builder.py` เลยแม้แต่บรรทัดเดียว**

---

## 4) ขั้นตอนสำหรับ Claude Code

1. Apply diff 5 ไฟล์ตามข้อ 2 เป๊ะๆ (ไม่ต้องคิด/compose อะไรเพิ่ม เนื้อหา verified แล้ว)
2. รัน mechanical check: `grep -c "encoding='utf-8'" src/smt/cli.py` (ต้องได้ 3) และ `grep -c "encoding='utf-8-sig'" src/smt/cli.py` (ต้องได้ 5)
3. รัน `pytest -q` เต็มชุด — ส่ง raw output ที่ลงท้ายด้วยตัวเลขจริงมาให้ CK1024/Claude Chat ดู (คาดว่าจะได้ `532 passed` ถ้า scipy ติดตั้งอยู่ หรือ `522 passed, 2 skipped` ถ้าไม่มี scipy — ทั้งสองแบบถือว่าผ่าน ไม่ต้องกังวลถ้าเห็น skipped 2 ตัวเพราะ scipy)
4. `git diff --stat` ต้องเห็นแค่ 5 ไฟล์ตามข้อ 3 พอดี
5. Commit message ผ่าน heredoc ตามกฎ 3.4:

```
fix(cli): read CSV files with utf-8-sig to tolerate Excel's BOM export

Excel's "CSV UTF-8 (Comma delimited)" export prepends a BOM, which
corrupts the first header cell (e.g. POINT -> \ufeffPOINT) since
str.strip() doesn't remove \ufeff. Header-name column lookups then
silently fail to find that column.

Confirmed 3 affected paths via live repro against real fixtures:
- parse_pi_table() via `smt build`: misleading orphan-compound-row
  ValueError, unrelated to the true cause
- fit_radius() via `smt fit-radius`: missing-column ValueError
- split_mixed_alignment_table(): silent - drawing list emptied out,
  no exception at that layer

Fix is I/O-boundary only (open()/decode() encoding) plus a defensive
lstrip('\ufeff') in table_splitter._parse_header (not a protected
function). No protected function (parse_pi_table/build_alignment_
from_pi/check_against_drawing) touched. Also applied to 3 currently-
unaffected positional read paths in cli.py and webhelpers.py's
Streamlit upload path for consistency - utf-8-sig is a no-op on
non-BOM files.

Adds 3 regression tests: test_build_with_bom_header_succeeds,
test_fit_radius_with_bom_header_succeeds, and
test_bom_prefixed_point_header_recognized.
```

6. ก่อน push: raw `git log -N --oneline` ยืนยัน local/origin ตรงกัน (กฎ 3.4)
7. `git add` เฉพาะ 5 ไฟล์นี้เท่านั้น ห้าม `-A`/`.`

ไม่มีจุดไหนที่ต้องรอถาม CK1024 เพิ่มแล้ว (ข้อ 5/6 ตัดสินใจแล้ว) — พร้อมให้ Claude Code เริ่มได้เลย
