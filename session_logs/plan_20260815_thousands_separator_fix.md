# PLAN — CSV thousands-separator fix (FINALIZED — verified in sandbox)
**วันที่:** 2026-08-15
**สำหรับ:** Claude Code — apply diff ตรงๆ ได้เลย (ผ่านการทดสอบจริงแล้วในรอบนี้)
**Base commit:** `c8b37d2` (BOM/utf-8-sig fix, ก่อนหน้านี้)
**สถานะ:** ✅ implement + test แล้วใน sandbox ของ Claude Chat ครบทุกไฟล์ ผ่านเต็มชุด raw output ด้านล่าง

---

## 0) สรุปว่า backlog เดิม ("อาจแก้ไปแล้วโดยไม่ตั้งใจ") ผิด — ยังไม่ได้แก้จริง

Reproduce แล้วว่า `smt build`/`smt fit-radius`/`smt cross-check`/`smt compare-drawing`/`smt station-to-coord`/`smt coord-to-station` **ทุกคำสั่ง crash จริง** ถ้าไฟล์มี thousands-separator comma (เช่น `"685,410.478"`) เหตุผลที่ `HOR_01N01.csv` เคย "คำนวณสำเร็จ" ในการทดสอบก่อนหน้า เพราะตอนนั้นเรียก `split_mixed_alignment_table()` ตรงๆ (ไม่ผ่าน `cli.py`) ซึ่งมี comma-stripping อยู่แล้วในตัว — แต่ `cli.py` ไม่เคยเรียกฟังก์ชันนั้นเลย

## 1) พบจุดที่ 2 — `optimizer.py::fit_radius` อันตรายกว่า (silent, ไม่ crash)

`fit_radius()` มีการอ่าน RADIUS ของตัวเอง (แยกจาก `parse_pi_table`) ห่อด้วย `try/except ValueError: continue` — RADIUS แบบ `"1,500"` ทำให้ PI ตัวนั้นถูกตีความว่า "ไม่มีรัศมี" (angle point) แล้วข้ามไปเงียบๆ **ไม่มี error ให้เห็นเลย** ผลการ optimize จะดูเหมือนรันสำเร็จแต่คำนวณผิดจากข้อมูลที่ขาดหายไปโดยไม่รู้ตัว

## 2) เช็คฝั่ง `.gs` ครบแล้ว — เว็บแอปป้องกันไว้ดีกว่า Python CLI

`GS_TableSplitter.gs` มี comma-stripping ครบ (`NUMERIC_KEYS` ทุกคอลัมน์) **และที่สำคัญ `GS_Pipeline.gs` เรียกมันจริงก่อน parse:**
```javascript
var split = GS_TableSplitter.splitMixedAlignmentTable(rows);
var vertices = GS_PiTableParser.parsePiTable(split.vertexRows);
var built = GS_AlignmentBuilder.buildFromPI(vertices);
```
เว็บแอปจึงไม่มีปัญหานี้เลย — เป็นต้นแบบที่พิสูจน์แล้วว่าการต่อ splitter เข้า pipeline ใช้งานได้จริงบน production

## 3) ลองทำตาม .gs ก่อน (ต่อ splitter เข้า cli.py) — **พังจริง ยกเลิกแนวทางนี้**

ลองแก้ `_read_pi_table()`/`_run_fit_radius()` ให้เรียก `split_mixed_alignment_table()` ก่อนส่งต่อ `parse_pi_table()` ตามแบบ `.gs` — รัน `pytest -q` แล้วพบ **10 เทสพังทันที** (`error: could not convert string to float: ''`)

**สาเหตุ:** ไฟล์หลัก `test_data/AL1_test_alignment_PI.csv` (ไฟล์ที่ใช้ตลอด Group A) ใช้ป้ายชื่อ **"PI" เฉยๆ ซ้ำกัน 11 ครั้ง** ไม่ใช่ "PI-1"/"PI-2" แต่ `split_mixed_alignment_table()`'s `_VERTEX_POINT_RE` รองรับแค่ `^(BP|PI-\d+|EP)$` — แถวที่เป็น "PI" เฉยๆ เลยถูกจัดเป็น "drawing point" แทนที่จะเป็น vertex ผิดประเภท ทำให้พังกับ PI table แบบมาตรฐานที่ใช้กันทั่วไปในโปรเจกต์นี้

**สรุป: `.gs` ใช้ได้เพราะข้อมูลจริงบนเว็บแอปใช้ป้าย PI-n ที่มีเลขกำกับเสมอ แต่ไฟล์ Python core ใช้ป้าย "PI" เฉยๆ เป็นหลัก — สองระบบมีข้อมูลจริงคนละแบบ เอาแนวทางเดียวกันมาใช้ตรงๆ ไม่ได้** จึงเปลี่ยนไปใช้วิธีที่ไม่ต้องรู้ชื่อ/รูปแบบคอลัมน์เลย (ข้อ 4)

## 4) วิธีที่ใช้จริง (verified) — strip comma แบบ generic ไม่ต้องรู้โครงสร้างคอลัมน์

สำหรับ `_read_pi_table`/`fit-radius` (ที่ไม่รู้ชื่อคอลัมน์ เพราะ `parse_pi_table` จัดการ header เอง): เช็คทีละเซลล์ว่า **ถ้าตัดคอมมาออกแล้ว parse เป็น float ได้** ก็ใช้ค่าที่ตัดแล้ว ถ้า parse ไม่ได้ (เช่น POINT name, Type code) ก็ปล่อยไว้เหมือนเดิม — ไม่ต้องรู้ว่าคอลัมน์ไหนคือตัวเลข ปลอดภัย 100% กับ text field

สำหรับ `_read_field_csv`/`_read_drawing_csv`/`_read_alignment` (รู้ตำแหน่งคอลัมน์อยู่แล้วเพราะเป็น format ตายตัว): strip comma ตรงจุดที่รู้ว่าเป็นคอลัมน์ตัวเลขได้เลย ง่ายกว่า

**ไม่แตะ `alignment_builder.py`/`vertical_builder.py` (protected functions) เลยแม้แต่บรรทัดเดียว** — แก้ที่ระดับ I/O boundary ใน `cli.py` เท่านั้น + จุดเดียวใน `optimizer.py` (ไม่ใช่ protected function) จึง**ไม่ต้องผ่าน Oracle correction exception**

## 5) ขอบเขตที่จงใจไม่แตะ — ทิ้งไว้เป็น backlog แยก

`HOR_01N01.csv` (ไฟล์ mixed table จริง มี PT/PC/PCC ปนกับ PI) ถ้าป้อนตรงเข้า `_read_pi_table` (ไม่ผ่าน splitter) ตอนนี้**ไม่ crash แล้ว** (comma หายแล้ว) **แต่ยังให้ผลลัพธ์ผิดความหมาย** เพราะ `parse_pi_table` ไม่รู้จัก PT/PC/PCC เป็นพิเศษ (แค่ไม่ใช่ BP/EP ก็ถูกตีความเป็น PI vertex หมด) — **ยืนยันแล้วว่าพฤติกรรมนี้มีอยู่ก่อนหน้าการแก้ครั้งนี้แล้ว ไม่ใช่ regression ใหม่** (ทดสอบด้วยการ stash การแก้แล้ว strip comma มือ ได้ผลเดียวกัน) การจะให้ CLI รองรับไฟล์ผสมแบบนี้ถูกต้องต้องต่อ `split_mixed_alignment_table()` เข้า cli.py อย่างมีการออกแบบ (ต้องคิดเรื่อง PI-label convention ที่ไม่ตรงกันในข้อ 3 ด้วย) — **ทิ้งไว้เป็นการตัดสินใจแยกต่างหาก ไม่ใช่ scope ของบั๊กนี้**

---

## 6) การเปลี่ยนแปลงจริง (verified diff)

### `src/smt/cli.py`
```diff
diff --git a/src/smt/cli.py b/src/smt/cli.py
index 12e00e2..cb27244 100644
--- a/src/smt/cli.py
+++ b/src/smt/cli.py
@@ -28,6 +28,47 @@ from .builders.alignment_builder import (
 from .landxml import export_alignment_landxml
 
 
+def _strip_commas(value: str) -> str:
+    """Remove thousands-separator commas (e.g. '1,537,772.85' -> '1537772.85').
+
+    Excel/field-survey exports sometimes format large coordinates with commas;
+    csv.reader preserves them verbatim inside quoted cells, but float() does
+    not accept comma-grouped numbers. No-op on values without commas.
+    """
+    return value.replace(',', '')
+
+
+def _strip_thousands_separators_from_rows(rows: list[list[Any]]) -> list[list[Any]]:
+    """Strip thousands-separator commas from data rows, leaving row 0 (header) alone.
+
+    Used ahead of parse_pi_table(), which does its own column-name lookup
+    internally (unlike the other _read_* helpers here, which know column
+    order positionally) - so commas can't be stripped by known-column-index
+    here. Instead, a cell only has its commas removed when doing so leaves a
+    string float() can parse; this is structure-agnostic (no assumption about
+    POINT-label format) and never touches a genuinely non-numeric cell such
+    as a POINT name or Type/Transition code.
+    """
+    if not rows:
+        return rows
+    out: list[list[Any]] = [rows[0]]
+    for row in rows[1:]:
+        cleaned_row = []
+        for cell in row:
+            s = str(cell)
+            if ',' in s:
+                candidate = s.replace(',', '')
+                try:
+                    float(candidate)
+                    cleaned_row.append(candidate)
+                    continue
+                except ValueError:
+                    pass
+            cleaned_row.append(cell)
+        out.append(cleaned_row)
+    return out
+
+
 def _read_alignment(path: str) -> list[alignment.Element]:
     """Read a CSV element table from path into a list of Elements.
 
@@ -48,12 +89,12 @@ def _read_alignment(path: str) -> list[alignment.Element]:
             continue   # tolerate blank lines
         sta_start, sta_end, n, e, az_deg, radius, type_, trans = line[:8]
         rows.append([
-            float(sta_start),
-            float(sta_end),
-            float(n),
-            float(e),
-            float(az_deg),
-            float(radius) if str(radius).strip() != '' else 0.0,
+            float(_strip_commas(sta_start)),
+            float(_strip_commas(sta_end)),
+            float(_strip_commas(n)),
+            float(_strip_commas(e)),
+            float(_strip_commas(az_deg)),
+            float(_strip_commas(radius)) if str(radius).strip() != '' else 0.0,
             type_.strip(),
             trans.strip(),
         ])
@@ -66,7 +107,7 @@ def _read_pi_table(path: str) -> list[dict[str, Any]]:
         rows = list(csv.reader(f))
     if not rows:
         raise ValueError(f'{path} is empty')
-    return parse_pi_table(rows)
+    return parse_pi_table(_strip_thousands_separators_from_rows(rows))
 
 
 def _read_field_csv(path: str) -> list[dict[str, Any]]:
@@ -84,7 +125,7 @@ def _read_field_csv(path: str) -> list[dict[str, Any]]:
             continue
         padded = line + [''] * 5
         name = padded[0].strip()
-        n, e, z = float(padded[1]), float(padded[2]), float(padded[3])
+        n, e, z = float(_strip_commas(padded[1])), float(_strip_commas(padded[2])), float(_strip_commas(padded[3]))
         disc = padded[4].strip()
         points.append({'name': name, 'n': n, 'e': e, 'z': z, 'disc': disc})
     return points
@@ -101,7 +142,7 @@ def _read_drawing_csv(path: str) -> list[dict[str, Any]]:
         if not line or all(c.strip() == '' for c in line):
             continue
         name = line[0].strip()
-        sta, n, e = float(line[1]), float(line[2]), float(line[3])
+        sta, n, e = float(_strip_commas(line[1])), float(_strip_commas(line[2])), float(_strip_commas(line[3]))
         points.append({'name': name, 'sta': sta, 'n': n, 'e': e})
     return points
 
@@ -228,9 +269,10 @@ def _run_fit_radius(args: argparse.Namespace) -> int:
     from .optimizer import fit_radius as _fit_radius
 
     with open(args.alignment, newline='', encoding='utf-8-sig') as f:
-        pi_rows: list[Any] = list(csv.reader(f))
-    if not pi_rows:
+        raw_rows: list[Any] = list(csv.reader(f))
+    if not raw_rows:
         raise ValueError(f'{args.alignment} is empty')
+    pi_rows: list[Any] = _strip_thousands_separators_from_rows(raw_rows)
 
     drawing_points = _read_drawing_csv(args.drawing)
     fix_names_raw = [s.strip() for s in args.fix.split(',') if s.strip()]
```

### `src/smt/optimizer.py`
```diff
diff --git a/src/smt/optimizer.py b/src/smt/optimizer.py
index 655a112..ce56fc0 100644
--- a/src/smt/optimizer.py
+++ b/src/smt/optimizer.py
@@ -87,7 +87,7 @@ def fit_radius(
         point = str(row[point_col]).strip()
         if not point or point in ('BP', 'EP'):
             continue
-        r_raw = str(row[r_col]).strip()
+        r_raw = str(row[r_col]).strip().replace(',', '')
         if not r_raw:
             continue
         try:
```

### `tests/test_cli.py` + `tests/test_optimizer.py`
```diff
diff --git a/tests/test_cli.py b/tests/test_cli.py
index e28b17d..3ea62ad 100644
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -20,6 +20,11 @@ StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
 0,100,1000,2000,90,0,T,
 """
 
+_TABLE_COMMAS = """\
+StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
+0,100,"1,000","2,000",90,0,T,
+"""
+
 _EMPTY_TABLE = """\
 StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
 """
@@ -32,6 +37,14 @@ def table(tmp_path: Path) -> str:
     return str(p)
 
 
+@pytest.fixture
+def table_commas(tmp_path: Path) -> str:
+    """Same geometry as `table`, but N/E use Excel's thousands-separator format."""
+    p = tmp_path / 'line_commas.csv'
+    p.write_text(_TABLE_COMMAS, encoding='utf-8')
+    return str(p)
+
+
 def test_fwd_centerline(table, capsys):
     rc = cli.main(['station-to-coord', table, '40'])
     assert rc == 0
@@ -40,6 +53,16 @@ def test_fwd_centerline(table, capsys):
     assert math.isclose(float(e_str), 2040.0, abs_tol=1e-6)
 
 
+def test_fwd_centerline_with_thousands_separator(table_commas, capsys):
+    """Excel-formatted N/E ('1,000', '2,000') in the element table must not
+    break _read_alignment()'s float() parsing."""
+    rc = cli.main(['station-to-coord', table_commas, '40'])
+    assert rc == 0
+    n_str, e_str = capsys.readouterr().out.strip().split(',')
+    assert math.isclose(float(n_str), 1000.0, abs_tol=1e-6)
+    assert math.isclose(float(e_str), 2040.0, abs_tol=1e-6)
+
+
 def test_fwd_with_offset(table, capsys):
     # +10 offset = right of east-bound travel = south (N decreases by 10)
     rc = cli.main(['station-to-coord', table, '40', '--offset', '10'])
@@ -114,6 +137,11 @@ NAME,N,E,Z,DISC
 PT01,1000,2250,85.000,0.001
 """
 
+_FIELD_CSV_COMMAS = """\
+NAME,N,E,Z,DISC
+PT01,"1,000","2,250",85.000,0.001
+"""
+
 _PI_TABLE_ANGLE = """\
 POINT,N,E,Sta,R,Ls,LsIn,LsOut,Trans,Delta
 BP,1000,2000,0,,,,,,
@@ -137,6 +165,22 @@ def pi_csv_bom(tmp_path):
     return str(p)
 
 
+_PI_TABLE_COMMAS = """\
+POINT,N,E,Sta,R,Ls,LsIn,LsOut,Trans,Delta
+BP,"1,000",2000,0,,,,,,
+PI,"1,000","2,500",,"1,500",,,,,
+EP,"1,500","2,500",,,,,,,
+"""
+
+
+@pytest.fixture()
+def pi_csv_commas(tmp_path):
+    """Same shape as pi_csv, but N/E/R cells use Excel's thousands-separator format."""
+    p = tmp_path / 'pi_commas.csv'
+    p.write_text(_PI_TABLE_COMMAS, encoding='utf-8')
+    return str(p)
+
+
 @pytest.fixture()
 def field_csv(tmp_path):
     p = tmp_path / 'field.csv'
@@ -144,6 +188,13 @@ def field_csv(tmp_path):
     return str(p)
 
 
+@pytest.fixture()
+def field_csv_commas(tmp_path):
+    p = tmp_path / 'field_commas.csv'
+    p.write_text(_FIELD_CSV_COMMAS, encoding='utf-8')
+    return str(p)
+
+
 def test_cross_check_basic(pi_csv, field_csv, capsys):
     rc = cli.main(['cross-check', pi_csv, field_csv])
     assert rc == 0
@@ -153,6 +204,16 @@ def test_cross_check_basic(pi_csv, field_csv, capsys):
     assert 'PT01' in out
 
 
+def test_cross_check_with_thousands_separator_succeeds(pi_csv_commas, field_csv_commas, capsys):
+    """Excel-formatted large coordinates ('1,000' etc.) in both the PI table and
+    the field CSV must not break parsing - exercises _read_pi_table() and
+    _read_field_csv() together."""
+    rc = cli.main(['cross-check', pi_csv_commas, field_csv_commas])
+    assert rc == 0
+    out = capsys.readouterr().out
+    assert 'PT01' in out
+
+
 def test_cross_check_missing_alignment(tmp_path, field_csv, capsys):
     rc = cli.main(['cross-check', str(tmp_path / 'no_such.csv'), field_csv])
     err = capsys.readouterr().err
@@ -232,6 +293,14 @@ def test_build_with_bom_header_succeeds(pi_csv_bom, tmp_path, capsys):
     assert (tmp_path / 'elements_output.csv').exists()
 
 
+def test_build_with_thousands_separator_succeeds(pi_csv_commas, tmp_path, capsys):
+    """Excel-formatted large coordinates/radius ('1,000', '1,500') must not
+    break _read_pi_table()'s float() parsing."""
+    rc = cli.main(['build', pi_csv_commas, '--out-dir', str(tmp_path)])
+    assert rc == 0
+    assert (tmp_path / 'elements_output.csv').exists()
+
+
 # ---------------------------------------------------------------------------
 # compare-drawing subcommand
 # ---------------------------------------------------------------------------
@@ -244,6 +313,13 @@ PI,50,1000,2050
 CP1,80,1000,2080
 """
 
+_DRAWING_CSV_COMMAS = """\
+Name,STA,N,E
+BP,0,"1,000","2,000"
+PI,50,"1,000","2,050"
+CP1,80,"1,000","2,080"
+"""
+
 
 @pytest.fixture()
 def drawing_csv(tmp_path: Path) -> str:
@@ -252,6 +328,13 @@ def drawing_csv(tmp_path: Path) -> str:
     return str(p)
 
 
+@pytest.fixture()
+def drawing_csv_commas(tmp_path: Path) -> str:
+    p = tmp_path / 'drawing_commas.csv'
+    p.write_text(_DRAWING_CSV_COMMAS, encoding='utf-8')
+    return str(p)
+
+
 def test_compare_drawing_basic(table, drawing_csv, capsys):
     rc = cli.main(['compare-drawing', table, drawing_csv])
     assert rc == 0
@@ -263,6 +346,16 @@ def test_compare_drawing_basic(table, drawing_csv, capsys):
     assert 'OK' in out
 
 
+def test_compare_drawing_with_thousands_separator_succeeds(table_commas, drawing_csv_commas, capsys):
+    """Excel-formatted N/E ('1,000' etc.) in the drawing CSV must not break
+    _read_drawing_csv()'s float() parsing."""
+    rc = cli.main(['compare-drawing', table_commas, drawing_csv_commas])
+    assert rc == 0
+    out = capsys.readouterr().out
+    assert 'CP1' in out
+    assert 'OK' in out
+
+
 def test_compare_drawing_missing_file(table, capsys):
     rc = cli.main(['compare-drawing', table, 'no_such_drawing.csv'])
     err = capsys.readouterr().err
diff --git a/tests/test_optimizer.py b/tests/test_optimizer.py
index 3d831f5..30084fd 100644
--- a/tests/test_optimizer.py
+++ b/tests/test_optimizer.py
@@ -90,6 +90,25 @@ class TestTangentOnly:
         assert res.gap_before < 1e-9
 
 
+class TestThousandsSeparatorRadius:
+    def test_comma_formatted_radius_not_silently_skipped(self) -> None:
+        """A RADIUS cell like '1,500' (Excel thousands-separator export) must be
+        recognised as a free PI, not silently treated as an angle point.
+
+        fit_radius() scans pi_rows for its own POINT/R columns (separate from
+        parse_pi_table()'s internal parsing) wrapped in a bare
+        `except ValueError: continue` - before the fix, a comma-formatted R
+        failed float() there and the PI vanished from the optimisation with
+        no error at all.
+        """
+        rows = _rows(0.0, 0.0, [('PI1', 50.0, 50.0, '1,500')], 100.0, 0.0)
+
+        res = fit_radius(rows, [])
+
+        assert res.names == ['PI1']
+        assert res.r_initial == [1500.0]
+
+
 # ---------------------------------------------------------------------------
 # Test 2 — simple curve: optimizer should converge to correct R
 # ---------------------------------------------------------------------------
```

---

## 7) ผลทดสอบจริงใน sandbox (raw output)

เต็มชุดหลังแก้ครบทุกจุด + เทสใหม่ 5 ตัว:
```
537 passed in 1.42s
```
(532 baseline จาก BOM fix + 5 เทสใหม่ = 537 ตรงเป๊ะ)

`git diff --stat`:
```
 src/smt/cli.py          | 64 ++++++++++++++++++++++++++++------
 src/smt/optimizer.py    |  2 +-
 tests/test_cli.py       | 93 +++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_optimizer.py | 19 ++++++++++
 4 files changed, 166 insertions(+), 12 deletions(-)
```
ตรงตามขอบเขตที่วางแผนไว้ — **ไม่มี `alignment_builder.py`/`vertical_builder.py` ในรายการเลย**

---

## 8) ขั้นตอนสำหรับ Claude Code

1. Apply diff ทั้ง 4 ไฟล์ตามข้อ 6 เป๊ะๆ (เนื้อหา verified แล้ว ไม่ต้อง compose เพิ่ม)
2. Mechanical check: `grep -c "_strip_commas\|_strip_thousands_separators_from_rows" src/smt/cli.py` ควรได้ตัวเลข > 0 หลายจุด (ใช้ตรวจว่า apply ครบ ไม่ใช่เลขตายตัว ให้ดูว่าตรงกับ diff)
3. รัน `pytest -q` เต็มชุด — คาดว่าได้ `537 passed` (ถ้ามี scipy) หรือใกล้เคียงถ้าไม่มี scipy (baseline ต่างกัน 2 ตามที่เจอมาก่อนหน้า) ส่ง raw output จริงมาให้ดู
4. `git diff --stat` ต้องเห็นแค่ 4 ไฟล์ตามข้อ 7 พอดี
5. Commit message ผ่าน heredoc (กฎ 3.4) — **สำคัญ: ใช้ `cat > .git/smt_commit_msg.txt << 'EOF'` เขียนทับให้เรียบร้อย อย่าให้เหลือข้อความ commit เก่าปนมา (เคยเกิดปัญหานี้มาก่อน) แล้ว `cat -A`/`wc -l` เช็คก่อน `-F` เสมอ:**

```
fix(cli): strip thousands-separator commas before float() parsing

Excel/field-survey exports sometimes format large coordinates with
commas (e.g. "685,410.478"). csv.reader preserves them verbatim in
quoted cells, but float() rejects comma-grouped numbers.

Confirmed every cli.py read path crashed on real/synthetic comma
data: _read_alignment, _read_pi_table, _read_field_csv,
_read_drawing_csv (all ValueError). Separately, optimizer.py's
fit_radius() has its own POINT/R column scan wrapped in a bare
except ValueError: continue - a comma-formatted radius was silently
treated as an angle point and dropped from optimisation with no
error at all, which is more dangerous than a crash.

Tried wiring split_mixed_alignment_table() into _read_pi_table()
first (mirroring the live GAS pipeline, which already does this and
is unaffected). This broke 10 existing tests: the project's main PI
table (AL1_test_alignment_PI.csv) uses a bare repeated "PI" label,
not the numbered "PI-1"/"PI-2" convention split_mixed_alignment_
table()'s VERTEX_POINT_RE expects, so real PI rows were
misclassified as drawing points. Reverted; used a structure-agnostic
fix instead - _read_pi_table/fit-radius strip commas from any cell
that becomes a valid float once stripped (no column-name knowledge
needed), and the three positional _read_* helpers strip commas at
their known numeric columns directly. optimizer.py's own R-column
read strips commas the same way.

No protected function (parse_pi_table/build_alignment_from_pi/
check_against_drawing) touched - fix is I/O-boundary only plus one
line in optimizer.py (not a protected function).

Adds 5 regression tests across test_cli.py and test_optimizer.py.

Deliberately out of scope: HOR_01N01.csv (a real mixed PI/drawing
table) no longer crashes when read via _read_pi_table but still
produces semantically-wrong vertices (PT/PC/PCC treated as PI
labels) since parse_pi_table only special-cases BP/EP - confirmed
this predates this fix (unrelated to commas). Wiring
split_mixed_alignment_table() into the CLI properly - accounting
for the bare-"PI" vs "PI-n" convention mismatch found here - is a
separate decision, not made in this commit.
```

6. `git add` เฉพาะ 4 ไฟล์:
```
git add src/smt/cli.py src/smt/optimizer.py tests/test_cli.py tests/test_optimizer.py
git status --short
```
7. `git commit -F .git/smt_commit_msg.txt` → `git log -1 --oneline` → เห็น raw `git log -3 --oneline` ยืนยัน local ตรงก่อน push → `git push`

---

## 9) เหลือให้ CK1024 ตัดสินใจภายหลัง (ไม่ใช่ของ commit นี้)

ต่อ `split_mixed_alignment_table()` เข้า `cli.py` อย่างถูกต้อง (ให้ `smt build` รองรับไฟล์ mixed table แบบ `HOR_01N01.csv`/`HOR_ORR_04.csv` ได้ตรงๆ) — ต้องคิดเรื่อง `_VERTEX_POINT_RE` ที่ไม่รองรับป้าย "PI" เฉยๆ ก่อน (ไฟล์หลักของโปรเจกต์ใช้แบบนี้) อาจต้องขยาย regex หรือแยกเป็น flag/คำสั่งใหม่ ไม่กระทบ `_read_pi_table` เดิม
