# PLAN — Enrich PI issue messages with real labels — FINALIZED, verified
**วันที่:** 2026-08-15
**สำหรับ:** Claude Code — apply diff ตรงๆ ได้เลย (ผ่านการทดสอบจริงแล้วในรอบนี้)
**Base commit:** `53c651d`
**สถานะ:** ✅ implement + test แล้วใน sandbox ของ Claude Chat ครบทุกไฟล์
**ขอบเขต: ไม่แตะ `parse_pi_table`/`build_alignment_from_pi` เลยแม้แต่บรรทัดเดียว** — แก้ที่ `cli.py` เท่านั้น (จุดที่พิมพ์ error/warning ให้ผู้ใช้เห็น)

---

## 1) ปัญหาจริงที่พบระหว่างวิเคราะห์ (ลึกกว่าที่คิดตอนแรก)

`build_alignment_from_pi`'s error message ทุกจุด (4 จุด) ใช้ `f'PI#{v}'` โดย `v` คือ **ตำแหน่งลำดับในลิสต์ล้วนๆ** — ไม่เกี่ยวกับ label จริงจาก CSV เลย เพราะ `parse_pi_table` **ไม่เก็บ label ไว้ใน vertex dict ที่ return** (มีแค่ n, e, R, Ls ฯลฯ)

**ยืนยันด้วยไฟล์จริง `AL1_test_alignment_PI.csv`** (relabel ไปแล้วรอบก่อน):
```
labels in file order: ['BP', 'IP1', 'IP2', 'PI1', 'PI2', ..., 'PI11', 'EP']
"PI#1" (positional) จริงๆ ตรงกับ CSV label: IP1   ← ไม่ใช่ "PI1"!
```
**การ relabel ที่ทำไปรอบก่อนไม่ได้แก้ปัญหานี้เอง** — ยังต้องมีโค้ดเชื่อม position กับ label จริง

## 2) วิธีที่ใช้จริง — adapter บน `cli.py` เท่านั้น ไม่แตะ protected function

1. `_pi_label_map(vertex_rows)` — เดินตามแถวแบบเดียวกับที่ `parse_pi_table` นับตำแหน่ง (ข้าม BP/EP/blank compound sub-row) → ได้ `{ตำแหน่ง: label จริง}`
2. `_enrich_pi_issues(issues, label_map)` — regex หา `PI#(\d+)` ทุกจุดในข้อความ (รวมจุดที่อ้างถึง PI ก่อนหน้าในข้อความเดียวกันด้วย) แล้วเติม `(label จริง)` ต่อท้าย
3. `_read_pi_table_and_labels(path)` — ฟังก์ชันใหม่ ทำงานเหมือน `_read_pi_table` เดิมทุกประการ **แต่ return label map เพิ่มด้วย** — `_read_pi_table` เดิม**ไม่เปลี่ยน signature เลย** (แค่เรียก `_read_pi_table_and_labels` ภายในแล้วคืนแค่ vertices) ปลอดภัยกับโค้ดอื่นที่อาจเรียกมันอยู่

## 3) รูปแบบข้อความ (ตามที่ตกลง)

```
เดิม:    PI#3: จุดเริ่มโค้ง (curve_start) อยู่หลังจุดจบของ PI#2 ...
ใหม่:    PI#3 (PI1): จุดเริ่มโค้ง (curve_start) อยู่หลังจุดจบของ PI#2 (IP2) ...
```
เก็บ `PI#N` เดิมไว้ (ตำแหน่งที่โปรแกรมคำนวณจริง) **บวก** label จริงจากไฟล์ต่อท้ายในวงเล็บ — ครบทั้งสองแบบ

## 4) ทดสอบยืนยันครบ (raw output)

**Demo สด (จำลองโครงสร้างแบบ AL1 จริง — IP1/IP2 ก่อน PI1/PI2 แล้วให้ 2 โค้งซ้อนทับกัน):**
```
label_map: {1: 'IP1', 2: 'IP2', 3: 'PI1', 4: 'PI2'}

RAW (เดิม):
  PI#3: จุดเริ่มโค้ง...อยู่หลังจุดจบของ PI#2 ...ระหว่าง PI#2 และ PI#3
  PI#4: จุดเริ่มโค้ง...อยู่หลังจุดจบของ PI#3 ...ระหว่าง PI#3 และ PI#4

ENRICHED (ใหม่ — สิ่งที่ผู้ใช้เห็นจริง):
  PI#3 (PI1): จุดเริ่มโค้ง...อยู่หลังจุดจบของ PI#2 (IP2) ...ระหว่าง PI#2 (IP2) และ PI#3 (PI1)
  PI#4 (PI2): จุดเริ่มโค้ง...อยู่หลังจุดจบของ PI#3 (PI1) ...ระหว่าง PI#3 (PI1) และ PI#4 (PI2)
```
ทุกจุดที่อ้างถึง PI ในข้อความเดียวกัน (รวม PI ก่อนหน้า) ถูกเติม label ครบ ไม่ตกหล่นจุดไหน

**เทสใหม่ 4 ตัว + `pytest -q` เต็มชุด:**
```
545 passed in 1.22s
```
(541 baseline + 4 เทสใหม่)

**Smoke-test อีก 2 subcommand ที่แก้ด้วย (`cross-check`, `export-landxml`):** รันจริงทั้งคู่ exit code 0 ปกติ ไม่พัง

**`git diff --stat`:**
```
 src/smt/cli.py    | 77 +++++++++++++++++++++++++++++++++++++++++++++++++-----
 tests/test_cli.py | 78 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 148 insertions(+), 7 deletions(-)
```
ไม่แตะ `alignment_builder.py`/`vertical_builder.py` เลยแม้แต่บรรทัดเดียว — ไม่ต้องผ่าน Oracle correction exception

---

## 5) การเปลี่ยนแปลงจริง (verified diff)

### `src/smt/cli.py`
```diff
diff --git a/src/smt/cli.py b/src/smt/cli.py
index 10beda4..d88e046 100644
--- a/src/smt/cli.py
+++ b/src/smt/cli.py
@@ -17,6 +17,7 @@ from __future__ import annotations
 import argparse
 import csv
 import math
+import re
 import sys
 from typing import Any
 
@@ -102,6 +103,58 @@ def _read_alignment(path: str) -> list[alignment.Element]:
     return alignment.parse_alignment_table(rows)
 
 
+def _pi_label_map(vertex_rows: list[list[Any]]) -> dict[int, str]:
+    """Map 1-based PI position -> the row's real POINT label from the file.
+
+    build_alignment_from_pi()'s issue messages identify a PI only by its
+    positional index ("PI#7") since parse_pi_table() doesn't carry the
+    original label through into the vertex dicts it returns - so "PI#7"
+    may not correspond to a row actually labelled "PI7" in the source file
+    (e.g. AL1_test_alignment_PI.csv has IP1/IP2 ahead of PI1..PI11, so
+    "PI#1" there is really the IP1 row). This walks vertex_rows the same
+    way parse_pi_table() counts positions (every non-blank row other than
+    BP/EP advances the count by one; blank-POINT compound sub-rows don't)
+    so the two numbering schemes always agree.
+    """
+    if not vertex_rows:
+        return {}
+    header = vertex_rows[0]
+    point_col = next(
+        (i for i, c in enumerate(header) if str(c).strip().lower() == 'point'), None
+    )
+    if point_col is None:
+        return {}
+    label_map: dict[int, str] = {}
+    position = 0
+    for row in vertex_rows[1:]:
+        if point_col >= len(row):
+            continue
+        point = str(row[point_col]).strip()
+        if not point or point in ('BP', 'EP'):
+            continue
+        position += 1
+        label_map[position] = point
+    return label_map
+
+
+def _enrich_pi_issues(issues: list[str], label_map: dict[int, str]) -> list[str]:
+    """Append each issue's real PI label(s) next to its "PI#N" reference(s),
+    e.g. 'PI#7: ...' -> 'PI#7 (PI7): ...'. A message may reference more than
+    one PI (e.g. the curve-overlap issue also cites the previous PI); every
+    "PI#N" occurrence is enriched independently. Positions with no mapped
+    label (map empty, or index absent) are left unchanged.
+    """
+    if not label_map:
+        return issues
+
+    def _sub(m: re.Match[str]) -> str:
+        n = int(m.group(1))
+        label = label_map.get(n)
+        return f'PI#{n} ({label})' if label else m.group(0)
+
+    return [re.sub(r'PI#(\d+)', _sub, issue) for issue in issues]
+
+
 def _read_pi_table(path: str) -> list[dict[str, Any]]:
     """Read a PI-table CSV and return a vertex list for build_alignment_from_pi.
 
@@ -113,6 +166,15 @@ def _read_pi_table(path: str) -> list[dict[str, Any]]:
     first as defense-in-depth for any column the splitter's header-name
     lookup doesn't recognise.
     """
+    vertices, _label_map = _read_pi_table_and_labels(path)
+    return vertices
+
+
+def _read_pi_table_and_labels(path: str) -> tuple[list[dict[str, Any]], dict[int, str]]:
+    """Same as _read_pi_table(), but also returns the PI label map (see
+    _pi_label_map()) so a caller can enrich build_alignment_from_pi()'s
+    issue messages with the file's real labels via _enrich_pi_issues().
+    """
     with open(path, newline='', encoding='utf-8-sig') as f:
         rows = list(csv.reader(f))
     if not rows:
@@ -120,7 +182,8 @@ def _read_pi_table(path: str) -> list[dict[str, Any]]:
     vertex_rows, _drawing = split_mixed_alignment_table(
         _strip_thousands_separators_from_rows(rows)
     )
-    return parse_pi_table(vertex_rows)
+    return parse_pi_table(vertex_rows), _pi_label_map(vertex_rows)
+
 
 
 def _read_field_csv(path: str) -> list[dict[str, Any]]:
@@ -172,11 +235,11 @@ def _radius_from_element(el: alignment.Element) -> float:
 def _run_build(args: argparse.Namespace) -> int:
     """build: PI table CSV -> elements_output.csv + controls_so_output.csv."""
     import os
-    vertices = _read_pi_table(args.alignment)
+    vertices, label_map = _read_pi_table_and_labels(args.alignment)
     if not vertices:
         raise ValueError('ไม่พบข้อมูล PI ในไฟล์ หรือไฟล์ไม่ใช่ PI table format')
     build_result = build_alignment_from_pi(vertices)
-    for issue in build_result.issues:
+    for issue in _enrich_pi_issues(build_result.issues, label_map):
         print(f'warning: {issue}', file=sys.stderr)
 
     out_dir = args.out_dir if args.out_dir else os.path.dirname(os.path.abspath(args.alignment))
@@ -224,9 +287,9 @@ def _run_build(args: argparse.Namespace) -> int:
 
 def _run_cross_check(args: argparse.Namespace) -> int:
     """cross-check: PI CSV + field CSV -> station/offset table."""
-    vertices = _read_pi_table(args.alignment)
+    vertices, label_map = _read_pi_table_and_labels(args.alignment)
     build_result = build_alignment_from_pi(vertices)
-    for issue in build_result.issues:
+    for issue in _enrich_pi_issues(build_result.issues, label_map):
         print(f'warning: {issue}', file=sys.stderr)
     field_points = _read_field_csv(args.field)
     rows = check.bulk_cross_check(build_result.elements, field_points)
@@ -368,11 +431,11 @@ def _run_inv(args: argparse.Namespace) -> int:
 
 def _run_export_landxml(args: argparse.Namespace) -> int:
     """export-landxml: PI table CSV -> LandXML 1.2 XML string or file."""
-    vertices = _read_pi_table(args.alignment)
+    vertices, label_map = _read_pi_table_and_labels(args.alignment)
     if not vertices:
         raise ValueError('ไม่พบข้อมูล PI ในไฟล์')
     result = build_alignment_from_pi(vertices)
-    for issue in result.issues:
+    for issue in _enrich_pi_issues(result.issues, label_map):
         print(f'warning: {issue}', file=sys.stderr)
     xml_str = export_alignment_landxml(result, name=args.name)
     if args.out:
```

### `tests/test_cli.py`
```diff
diff --git a/tests/test_cli.py b/tests/test_cli.py
index 4abd97c..88079a6 100644
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -331,6 +331,84 @@ def test_build_with_mixed_table_succeeds(pi_csv_mixed, tmp_path, capsys):
     assert len(rows) == 4   # header + 3 elements (tangent, curve, tangent)
 
 
+# ---------------------------------------------------------------------------
+# PI issue-message label enrichment (2026-08-15)
+#
+# build_alignment_from_pi()'s "PI#N" issue messages identify a PI only by
+# its 1-based position, since parse_pi_table() doesn't carry the file's
+# original label through into the vertex dicts it returns. When a file has
+# IP1/IP2-style angle points ahead of the numbered PI-n curves (as
+# AL1_test_alignment_PI.csv genuinely does), "PI#1" in an issue is actually
+# the IP1 row, not "PI1" - misleading anyone trying to find that row in
+# their own file. _pi_label_map()/_enrich_pi_issues() fix this at the
+# cli.py boundary only; parse_pi_table()/build_alignment_from_pi() (both
+# protected functions) are untouched.
+# ---------------------------------------------------------------------------
+
+def test_pi_label_map_matches_parse_pi_table_position_counting():
+    """Position numbering must skip BP/EP and blank compound sub-rows
+    exactly like parse_pi_table()'s own vertex count - including counting
+    IP-labelled angle points, which are ordinary PI vertices to
+    parse_pi_table() even though they aren't numbered "PI-n"."""
+    rows = [
+        ['POINT', 'N', 'E', 'R'],
+        ['BP', '0', '0', ''],
+        ['IP1', '50', '50', ''],
+        ['IP2', '100', '100', ''],
+        ['PI1', '200', '100', '150'],
+        ['', '', '', '80'],          # blank-POINT compound sub-row - no new position
+        ['PI2', '300', '100', '100'],
+        ['EP', '400', '0', ''],
+    ]
+    label_map = cli._pi_label_map(rows)
+    assert label_map == {1: 'IP1', 2: 'IP2', 3: 'PI1', 4: 'PI2'}
+
+
+def test_enrich_pi_issues_appends_real_label():
+    label_map = {2: 'IP2', 3: 'PI1'}
+    issues = ['PI#3: overlaps PI#2 somehow']
+    enriched = cli._enrich_pi_issues(issues, label_map)
+    assert enriched == ['PI#3 (PI1): overlaps PI#2 (IP2) somehow']
+
+
+def test_enrich_pi_issues_leaves_unmapped_position_unchanged():
+    enriched = cli._enrich_pi_issues(['PI#9: something'], {1: 'PI1'})
+    assert enriched == ['PI#9: something']
+
+
+_PI_TABLE_OVERLAP_WITH_IP = """\
+POINT,N,E,R
+BP,0,0,
+IP1,50,50,
+IP2,100,100,
+PI1,200,100,150
+PI2,199.9999999,100.0000002,100
+EP,300,0,
+"""
+
+
+@pytest.fixture()
+def pi_csv_overlap_with_ip(tmp_path):
+    """Reproduces AL1's real IP1/IP2-before-PI1 layout with two PIs placed
+    to trigger a real curve-overlap issue, so "PI#3"/"PI#4" (positional)
+    diverge from "PI1"/"PI2" (the file's actual labels)."""
+    p = tmp_path / 'pi_overlap_ip.csv'
+    p.write_text(_PI_TABLE_OVERLAP_WITH_IP, encoding='utf-8')
+    return str(p)
+
+
+def test_build_warning_shows_real_label_not_just_position(pi_csv_overlap_with_ip, tmp_path, capsys):
+    """End-to-end: smt build's printed warning for a curve-overlap issue at
+    the file's PI1 (position #3, since IP1/IP2 take positions #1/#2) must
+    show "PI1", not just the positional "PI#3" a user can't map back to
+    their own file without counting rows by hand."""
+    rc = cli.main(['build', pi_csv_overlap_with_ip, '--out-dir', str(tmp_path)])
+    assert rc == 0
+    err = capsys.readouterr().err
+    assert 'PI#3 (PI1)' in err
+    assert 'PI#2 (IP2)' in err
+
+
 # ---------------------------------------------------------------------------
 # compare-drawing subcommand
 # ---------------------------------------------------------------------------
```

---

## 6) ขั้นตอนสำหรับ Claude Code

1. Apply diff ในหัวข้อ 5 ตรงตามที่ระบุ (2 ไฟล์)
2. รัน `pytest -q` เต็มชุด — คาดว่าได้ `545 passed`
3. Smoke-test 3 subcommand ที่แก้ (ต้อง exit code 0 ทั้งหมด):
```
python -m smt.cli build test_data/AL1_test_alignment_PI.csv --out-dir /tmp/verify_build
python -m smt.cli cross-check test_data/AL1_test_alignment_PI.csv <field_csv_path>
python -m smt.cli export-landxml test_data/AL1_test_alignment_PI.csv
```
4. `git diff --stat` ต้องเห็นแค่ 2 ไฟล์ตามข้อ 5 พอดี
5. Commit message ผ่าน heredoc (`cat >` เขียนทับ) แล้ว `wc -l -w -c` เช็คก่อน commit เสมอ:

```
feat(cli): enrich PI issue messages with the file's real labels

build_alignment_from_pi()'s "PI#N" issue messages identify a PI only
by its 1-based position, since parse_pi_table() doesn't carry the
original label through into the vertex dicts it returns. When a
file has IP1/IP2-style angle points ahead of the numbered PI-n
curves - as AL1_test_alignment_PI.csv genuinely does - "PI#1" in an
issue is actually the IP1 row, not "PI1", misleading anyone trying
to find that row in their own file.

Adds _pi_label_map() (walks vertex_rows counting positions exactly
like parse_pi_table() does - BP/EP and blank compound sub-rows don't
advance the count) and _enrich_pi_issues() (regex-appends the real
label next to every "PI#N" reference in an issue string, including
references to a previous PI within the same message). Wired into
the three cli.py subcommands that print build_alignment_from_pi's
issues: build, cross-check, export-landxml.

_read_pi_table()'s own signature is untouched (still returns just
vertices) - it now delegates to a new _read_pi_table_and_labels()
that also returns the label map, so nothing else calling
_read_pi_table() is affected.

No protected function (parse_pi_table/build_alignment_from_pi/
check_against_drawing) touched - purely a cli.py presentation-layer
adapter, output format: "PI#3 (PI1): ..." (position kept, real label
appended).

Adds 4 regression tests: label-map position counting (matches
parse_pi_table()'s own vertex counting, including IP-labelled angle
points), enrichment appending the real label, an unmapped-position
no-op case, and an end-to-end smt build test reproducing AL1's real
IP1/IP2-before-PI1 layout with an actual curve-overlap issue.
```

6. `git add` เฉพาะ 2 ไฟล์:
```
git add src/smt/cli.py tests/test_cli.py
git status --short
```
7. `git commit -F .git/smt_commit_msg.txt` → `git log -3 --oneline` ยืนยัน local → `git push`
8. Append `session_logs/latest.md` ผ่าน `cat >>` heredoc เท่านั้น (ห้าม Update/Edit tool)
