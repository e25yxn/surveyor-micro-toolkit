# รายงาน Code Review: src/smt/ ทั้งแพ็กเกจ (2026-08-02)

- ผู้ตรวจ: Claude Code (อ่านครบทั้ง 16 ไฟล์, ~3,280 บรรทัด)
- ขอบเขต: ทุกไฟล์ใน src/smt/ รวม builders, optimizer, cli, landxml, webhelpers —
  เน้นพิเศษ 3 ฟังก์ชัน protected (parse_pi_table, build_alignment_from_pi,
  check_against_drawing) ที่ทุก port (VBA/GAS) verify แบบ diff=0 กับมันมาตลอด
  แต่ตัว Python core ไม่เคยถูกตรวจอิสระ
- สถานะ: รายงานอย่างเดียว **ยังไม่ได้แก้โค้ดแม้แต่บรรทัดเดียว** — รอ Claude (แชท)
  ตรวจก่อนตัดสินใจว่าจะลงมือแก้จุดไหน
- หมายเหตุการยืนยัน: ข้อ #1 ยืนยันจากการอ่านโค้ด (Python float หารด้วย 0.0
  raise ZeroDivisionError แน่นอน และ sin(δ)→0 เมื่อ collinear) ยังไม่ได้รัน
  ทดสอบจริง เพราะคำสั่งรันถูกยกเลิกระหว่างเซสชัน

**สรุปภาพรวม:** critical 0 / major 5 / minor 15 — ไม่พบช่องโหว่ security
ที่มีนัยสำคัญ แต่พบ "บั๊กแฝงที่ทุก port สืบทอดไปด้วย" ในฟังก์ชัน protected
จริงตามที่สงสัย โดยเฉพาะ #1–#4

---

## มิติ 1 — ความถูกต้อง/บั๊ก

### กลุ่ม protected functions (บั๊กที่ VBA/GAS สืบทอดไปแล้ว)

**#1 — major — `builders/alignment_builder.py:391-392` (build_alignment_from_pi)**
`d1 = (...) / det` โดย `det = sin(delta)` ไม่มี guard เลย:
- PI ที่**มี R** แต่สามจุดเรียงเป็นเส้นตรงพอดี (delta=0) → `ZeroDivisionError` ดิบ
  ซึ่ง `cli.py:422` ไม่ catch (catch เฉพาะ ValueError/FileNotFoundError/ImportError)
  → traceback เต็มจอ
- อันตรายกว่านั้นคือกรณี**เกือบ**เรียงเส้นตรง (delta ~ 1e-8 rad ซึ่งเกิดได้จริงจาก
  พิกัดที่ digitize มา): sin(delta) จิ๋วมาก → d1 พุ่งเป็นหลักร้อยล้านเมตร ได้
  geometry ขยะ**แบบเงียบสนิท ไม่มี issue ไม่มี error** — ทาง EXT-001 คุ้มครอง
  เฉพาะกรณี R ว่าง/R=0 เท่านั้น กรณี "มี R + เกือบ collinear" หลุด
- กรณี delta = π (หักกลับ 180°) ก็ det≈0 เช่นกัน

*แนวทางแก้:* ถ้า `abs(sin(delta)) < eps` ให้ append issue แล้ว fallback เป็น
angle point (เส้นทาง EXT-001 ที่มีอยู่แล้ว) หรือ raise ValueError พร้อมชื่อ PI —
ห้ามปล่อยหารต่อ

**#2 — major — `builders/alignment_builder.py:399-407` (build_alignment_from_pi)**
ไม่ตรวจว่า curve start (TS/PC) อยู่**ข้างหน้า**จุดจบของโค้งก่อนหน้า: ถ้า PI สองตัว
ติดกันมี R/Ls ใหญ่จนโค้งซ้อนทับกัน (tangent ระหว่างกลางไม่พอ)
`tan_len = calculate_distance_2d(...)` ยังได้ค่าบวกเสมอ (ระยะทางไม่มีเครื่องหมาย)
→ สร้าง element T ที่ "เดินหน้า" ทั้งที่ TS จริงอยู่**ข้างหลัง** → exit ของ T
ไม่ต่อกับ start ของโค้งถัดไป เกิดรอยแยกใน chain แบบเงียบ ไม่มีรายการใน `issues`
เลย (จะเห็นก็ต่อเมื่อผู้ใช้รัน check_chain เองแยกต่างหาก)
*แนวทางแก้:* เช็ค dot product `(curve_start - prev)·(cos az_in, sin az_in) < 0`
→ append issue "tangent ไม่พอ / โค้งซ้อนทับ PI#v"

**#3 — major — `builders/alignment_builder.py:252-287` (parse_pi_table)**
`compound_arcs` รั่วข้าม vertex ได้: sub-row (POINT ว่าง + R มีค่า) ที่โผล่
**ก่อน PI ตัวแรก** (เช่น หลังแถว BP) หรือหลัง EP — `_flush_pending` return ตั้งแต่
`pending_pi is None` โดย**ไม่เคลียร์ compound_arcs** → arcs ค้างในลิสต์แล้วไป
เกาะ PI ตัวถัดไปที่ไม่เกี่ยวข้อง กลายเป็น compound curve ผิดตัวแบบเงียบ; ส่วน
sub-row ค้างท้ายไฟล์ถูกทิ้งเงียบ นี่คือบั๊กตระกูลเดียวกับที่เคยแก้เมื่อ 2026-07-05
(silent-drop R) แต่คนละเส้นทาง
*แนวทางแก้:* ใน `_flush_pending` ถ้า `pending_pi is None and compound_arcs` ให้
raise ValueError ระบุเลขบรรทัด (สไตล์เดียวกับ fix เดิม) และ raise เมื่อจบไฟล์แล้ว
ยังมี arcs ค้าง

**#4 — major — `builders/alignment_builder.py:472-473` +
`builders/vertical_builder.py:193-195` (check_against_drawing ทั้งสองตัว)**
drawing point ที่มี name แต่ไม่ match control point ใดเลย (เช่น พิมพ์ 'ST1' ผิด
เป็น 'STl') → `best is None` → `continue` **เงียบ ไม่มีแถวในรายงาน** — เครื่องมือ
verify ที่ "ข้ามจุดที่ตรวจไม่ได้แบบเงียบ" อันตรายที่สุด เพราะรายงานที่เหลือดูผ่านหมด
ผู้ใช้เข้าใจว่าตรวจครบ นอกจากนี้การจับคู่ closest-by-station **ไม่มีเพดานระยะ**:
จุดที่ station ห่าง control ที่ใกล้สุดถึง 500 m ก็ยังถูกจับคู่แล้วรายงาน FAIL
ที่ชวนงงแทนที่จะบอกว่า "ไม่มีคู่"
*แนวทางแก้:* append แถว `{name, ok: False, note: 'no matching control point'}`
แทนการ skip และเพิ่ม optional max station distance

### กลุ่มไฟล์อื่น

**#5 — major — `cli.py:40,65,77,95,230` + `webhelpers.py:18` (ทุกจุดอ่าน CSV)**
`encoding='utf-8'` ล้วน ไม่ใช่ `'utf-8-sig'`: ไฟล์ CSV จาก Excel "CSV UTF-8"
จะมี BOM ทำให้ header เซลล์แรกกลายเป็น `﻿POINT` — `str.strip()` **ไม่ตัด**
U+FEFF → `_parse_header` หา column 'point' ไม่เจอ → ทุกแถวถูกมองเป็น
sub-row/ถูกข้าม → ผู้ใช้ได้ error หลอกว่า "ไม่พบข้อมูล PI ในไฟล์" ทั้งที่ไฟล์ถูกต้อง
และไฟล์ cp874 (Thai ANSI จาก Excel เก่า) จะได้ `UnicodeDecodeError` เป็น
traceback ดิบ (ไม่อยู่ใน catch list ของ main)
*แนวทางแก้:* เปลี่ยนเป็น `encoding='utf-8-sig'` ทุกจุด (decode utf-8 ธรรมดาได้
ปกติ ไม่กระทบไฟล์เดิม) + เพิ่ม UnicodeDecodeError ใน catch ของ main พร้อม
ข้อความแนะนำเรื่อง encoding

**#6 — minor — `builders/alignment_builder.py:74-83` (_build_curve_sub_elements)**
compound sub-row ที่ไม่ใช่แถวสุดท้ายแต่ delta ว่าง → `arc['delta']` KeyError
(ไม่ถูก catch ใน CLI → traceback); และเมื่อ delta รวมเกินมุมเลี้ยว มีการ append
issue ก็จริง แต่ยังสร้าง element ที่ `len` ติดลบ (sta_end < sta_start) ต่อไป —
ผู้ใช้ที่ไม่อ่าน warning ได้ตารางที่ station เดินถอยหลัง
*แนวทางแก้:* validate ว่า non-last arc ต้องมี delta (raise ValueError ระบุ
บรรทัด) และ clamp/ตัด element ติดลบพร้อม issue

**#7 — minor — `alignment.py:373` (calculate_point_on_element, circular branch)**
`chord = 2.0/abs(k) * abs(sin(theta/2))` ทิ้งเครื่องหมายของ sin: เมื่อ d ติดลบ
เล็กน้อย (เข้ามาได้จริงผ่าน tolerance 1e-4 ของ `get_element_index`) จุดจะถูก
เลื่อน**ไปข้างหน้า**แทนที่จะถอยหลัง คลาด ~2|d| (สูงสุด ~0.2 mm) — ผลกระทบต่ำ
แต่เป็น sign bug แท้ๆ ที่ port ไป VBA แล้วด้วย (`SMT_StaToN/E`)
*แนวทางแก้:* ใช้รูป signed `(2.0/k) * sin(theta/2)` ตรงๆ (ให้ผลบวกเองเมื่อ d>0
ทั้งเลี้ยวซ้าย/ขวา และถูกต้องเมื่อ d<0)

**#8 — minor — `vertical.py:84-91` (calculate_elevation_at, asymmetric VC)**
สูตร arm 2 ใช้ `lx2 = seg.sta_end - sta` โดย**สมมติ**ว่า
`sta_end == sta_start + l1 + l2` เป๊ะ — ตารางที่มาจาก builder การันตี แต่ตาราง
ที่พิมพ์มือ/แก้ใน Excel ที่ไม่ consistent จะได้ระดับผิดแบบเงียบ และ symmetric VC
ที่ segment ยาวกว่า lvc จะ extrapolate พาราโบลาเกินปลายโค้งเงียบๆ
*แนวทางแก้:* validate ใน `parse_vertical_table` (l1+l2 ≈ sta_end−sta_start
ภายใน tolerance, lvc ≤ ความยาว segment) แล้ว raise/เตือน

**#9 — minor — `builders/vertical_builder.py:93,96,133` (build_vertical_from_vpi)**
(ก) VPI สอง station ซ้ำกัน → หารศูนย์ตอนคิด grade → ZeroDivisionError ดิบ;
(ข) EVP ที่ station อยู่**ก่อน** PVT สุดท้าย → เงื่อนไข `ep_sta > end_sta` ไม่จริง
→ ไม่สร้างแถวสุดท้ายและ**ไม่ append issue ใดๆ** — profile ถูกตัดท้ายเงียบ
*แนวทางแก้:* guard + append issue ทั้งสองกรณี

**#10 — minor — `fpmath.py:112-124` (packed_dms_to_rad)**
ไม่ validate ว่า minutes/seconds < 60: input พิมพ์ผิดเช่น `120.7530` (75 นาที)
ถูกแปลงเงียบเป็น 121°15′30″ — งาน survey ที่กรอก DMS ด้วยมือเจอ typo แบบนี้
บ่อย ตัว engine ควรจับให้
*แนวทางแก้:* raise ValueError (หรือเพิ่ม parameter `strict=True`) เมื่อ m≥60
หรือ s≥60

**#11 — minor — `optimizer.py:105-108` + `cli.py:207` (filter ชื่อจุด)**
`startswith(('PI', 'HIP'))` ตัดจุดชื่อจริงอย่าง `PIER-1`, `PILE3` ออกจาก
objective/ตารางเปรียบเทียบแบบเงียบ
*แนวทางแก้:* ใช้ regex `^(PI|HIP)[-_]?\d*$` แทน prefix match

**#12 — minor — `check.py:79-106,150-178`**
(ก) `_snap_to_alignment_ends`/`_snap_to_profile_ends` พังด้วย IndexError ถ้า
list ว่าง (ควรเป็น ValueError ที่สื่อความ); (ข) `bulk_cross_check` จุดเดียว
project ไม่ได้ → ValueError ล้มทั้ง batch — งานสนาม 100 จุดมี outlier 1 จุด
รายงานทั้งใบหาย
*แนวทางแก้:* guard list ว่าง + จับ error รายจุดแล้วรายงานเป็นแถว "OUTSIDE"
แทน (แบบเดียวกับที่ `_run_fit_radius` ทำอยู่แล้วใน cli.py:288-289)

**#13 — minor — `builders/alignment_builder.py:335-353` (build_alignment_from_pi)**
ไม่ validate ว่า vertices[0] เป็น BP จริง: ถ้าไฟล์ไม่มีแถว BP แถว PI แรก
(พร้อม R) จะถูกใช้เป็นจุดตั้งต้นเงียบๆ โดย R ถูกทิ้ง — ควร raise/เตือนเมื่อ
vertices[0] มี key 'R' หรือ 'compound'

---

## มิติ 2 — Code quality / ออกแบบ (SAFE + SMALL + STABLE + MODULAR)

ภาพรวม: คุณภาพสูงกว่ามาตรฐานทั่วไปมาก — pure functions จริง, type hints ครบ,
docstring ระบุหน่วย/sign convention สม่ำเสมอ, no rounding in core ทำได้จริง
ข้อสังเกตที่เหลือ:

**#14 — minor — duplication ของ header-parsing 4 ชุด**
`_COL_ALIASES`+`_parse_header` ใน `alignment_builder.py:181-208` ถูก copy ไป
`table_splitter.py:20-54`, `optimizer.py:14-37` (`_find_col`), และ inline ใน
`cli.py:254-259` — และ drift เกิดขึ้นแล้วจริง: docstring `cli.py:75` บอก
"DISC defaults to 0.0" แต่โค้ด (และ `webhelpers.py:27` ที่ mirror กัน) ใช้ `''`
— หลักฐานว่า mirror-by-copy เริ่มไม่ตรงกันแล้ว
*แนวทางแก้:* รวมเป็นโมดูลกลาง (เช่น `smt/tabling.py`) แบบ add-don't-break +
แก้ docstring ที่ drift

**#15 — minor — `alignment.py:82-99`**
`Element` เป็น dataclass ธรรมดา (mutable) ทั้งที่ปรัชญา core คือ pure/immutable
และ `make_element` ใช้ parameter ชื่อ `type` shadow builtin
*แนวทางแก้:* `@dataclass(frozen=True)` (ต้องรัน test ยืนยันว่าไม่มีใคร mutate)
และเปลี่ยนชื่อ param เป็น `element_type` ในรุ่นหน้า (breaking — ชั่งน้ำหนักก่อน)

**#16 — minor — `landxml.py:31,177`**
docstring ประกาศ "Pure function; no I/O" แต่เรียก `datetime.now()` → output
ไม่ deterministic ทดสอบ byte-diff ไม่ได้
*แนวทางแก้:* เพิ่ม parameter `timestamp: datetime | None = None`

**#17 — minor — tolerance กระจัดกระจายไม่มีชื่อ**
`1e-4` (alignment.py:437,482,500), `0.01` snap (check.py), `5` arcsec
(alignment.py:568), `1e-9`/`1e-6` (vertical_builder.py:107,112) — ควรยกเป็น
named constants ระดับโมดูล พร้อม docstring ว่าทำไมค่านั้น

**#18 — minor — `builders/__init__.py`**
ไม่ export `table_splitter` ทั้งที่เป็น public adapter — ไม่สม่ำเสมอ

**#19 — minor — `cli.py:422` error boundary แคบ**
catch แค่ 3 ชนิด — KeyError (#6), ZeroDivisionError (#1, #9),
UnicodeDecodeError (#5), IndexError หลุดเป็น traceback ทั้งหมด ขัดกับทิศทาง
friendly-error ที่เพิ่งทำใน F.5/F.6 ฝั่ง gsheet
*แนวทางแก้:* ขยาย catch + ข้อความภาษาคน (หลังแก้ต้นเหตุ #1/#6 แล้ว ชั้นนี้เป็น
safety net)

**#20 — minor — `optimizer.py:117-121,134`**
(ก) `except Exception` กว้าง — บั๊กจริงใน builder จะถูกกลืนเป็น penalty เงียบๆ
ทำให้ optimizer "ลู่เข้า" ไปคำตอบขยะได้; (ข) `gap_before = sqrt(objective(x0))`
— ถ้า initial build มี issues ค่า penalty 1e6 ถูก sqrt แล้วรายงานเป็น "เมตร"
(~หลักพัน) ชวนเข้าใจผิด; (ค) verification ใน `cli.py:261-267` patch ตาราง
**ตามชื่อ** PI — ถ้ามีชื่อ PI ซ้ำจะ patch ไม่ตรงกับที่ optimizer มองเป็นรายแถว
*แนวทางแก้:* catch เฉพาะ (ValueError, ZeroDivisionError, KeyError), รายงาน
gap_before = None/'build failed' เมื่อมี penalty, patch ตาม row index

---

## มิติ 3 — Security

ตรวจแล้ว**ไม่พบ** eval/exec/pickle/subprocess/os.system/shell=True ใดๆ ในทั้ง
แพ็กเกจ; XML สร้างผ่าน ElementTree ซึ่ง escape attribute อัตโนมัติ (ชื่อ
alignment จาก `--name` ปลอดภัย); ไม่มี network I/O; อ่าน/เขียนไฟล์ตาม path
ที่ผู้ใช้ระบุเองซึ่งเป็นพฤติกรรมปกติของ CLI ท้องถิ่น — ความเสี่ยงรวมอยู่ระดับ**ต่ำ**
เหลือข้อแนะนำเชิงป้องกันล่วงหน้า 2 ข้อ:

**#21 — minor (advisory) — LandXML import ที่กำลังจะทำ (roadmap "Next: LandXML I/O")**
ตอนนี้มีแต่ export ปัญหา XXE จึงยังไม่เกิด แต่เมื่อเริ่ม**อ่าน** .xml จากภายนอก
(ไฟล์จาก Civil 3D เครื่องอื่น) ห้ามใช้ `xml.etree.ElementTree.parse` ดิบ —
ให้ใช้ `defusedxml` หรืออย่างน้อยปิด entity resolution ตั้งแต่ design แรก

**#22 — minor (advisory) — CSV formula injection**
output CSV ปัจจุบัน (elements/controls) เป็นค่าคำนวณ+ชื่อ fixed ทั้งหมด จึงยัง
ปลอดภัย แต่ถ้าอนาคตมี output ที่พาชื่อจุดจาก input ของผู้ใช้ลง CSV (เช่น
cross-check report เป็นไฟล์) ต้อง escape เซลล์ที่ขึ้นต้นด้วย `=`, `+`, `-`, `@`
ก่อน เพราะจะถูก Excel ตีความเป็นสูตร

---

## ลำดับความสำคัญที่เสนอ (สำหรับ Claude แชท พิจารณา)

1. **#1, #2, #3, #4** — บั๊กแฝงใน protected functions ที่ทุก port สืบทอด
   (ตรงโจทย์ที่สุด) — แก้ต้องผ่านวงจร Plan-Review-Approve และถ้าแก้ #1/#2
   ต้องเทียบพฤติกรรม oracle .gs ก่อนตัดสินว่าจะ "ตรง oracle" หรือ "ดีกว่า
   oracle" (ต้อง mark EXT ตาม Extension policy)
2. **#5** — utf-8-sig แก้ง่าย ความเสี่ยงต่ำ คุ้มทันทีสำหรับผู้ใช้ Excel ไทย
3. ที่เหลือเป็น minor เลือกทำเป็นรอบๆ ได้

ทุกข้อเป็น**ข้อเสนอเท่านั้น ยังไม่ได้แตะโค้ด** — การแก้จริงต้องรอ Claude (แชท)
อนุมัติแผนก่อนตามมาตรฐานส่วนที่ 3
