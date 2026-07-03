# รายงานทดสอบ: Compound Curve Pattern ใน SettingOutTest.csv

วันที่: 2026-07-03 16:17
ประเภทงาน: ตรวจสอบ/รายงาน (อ่านโค้ดเท่านั้น — ยังไม่มีการแก้ไฟล์หรือรัน test)

---

## 1. สิ่งที่ตรวจสอบ

ผู้ใช้พบ pattern ใน `test_data/SettingOutTest.csv` ที่สงสัยว่าเป็นการเข้ารหัส compound curve:

```
PI7,,1565169.659,680911.287,300,,,,,20
,,,,150,,,,,
```

ขอให้ยืนยันก่อนนำ pattern นี้ไปสร้างไฟล์ทดสอบ compound curve ใหม่ โดยตรวจสอบ:
1. โค้ดตรวจจับ/ประมวลผล compound curve ใน `src/smt/builders/alignment_builder.py`
2. ความถูกต้องของการตีความ (RADIUS ในแถวว่าง = R ตัวที่สอง ตามทิศทาง BP→EP)
3. test case ที่มีอยู่แล้วใน `tests/builders/test_alignment_builder.py`

---

## 2. โค้ดที่เกี่ยวข้อง (`src/smt/builders/alignment_builder.py`)

### 2.1 การ parse แต่ละแถว (บรรทัด 247–297)

```python
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
    ...
    # PI vertex
    pi_dict: dict[str, Any] = {'n': n, 'e': e}
    r_raw = _g(row, 'radius')
    if r_raw and float(r_raw) != 0.0:
        pi_dict['R'] = float(r_raw)
        ...
    # else: R absent or 0 → angle point (no 'R' key); may gain 'compound' later
    pending_pi = pi_dict
```

**หมายเหตุสำคัญ:** โค้ดส่วนแถว PI (บรรทัด 276-294) **ไม่มีการอ่านคอลัมน์ `delta` เลย** — `delta`
ถูกอ่านเฉพาะตอน parse แถว sub-row (blank POINT) เท่านั้น

### 2.2 การ flush (บรรทัด 234–245) — จุดที่พบปัญหา

```python
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
```

เมื่อ `compound_arcs` ไม่ว่าง โค้ดจะสร้าง vertex ใหม่จาก `n`, `e`, และ `compound` เท่านั้น
**ไม่ดึงค่า `R` (หรือคีย์อื่น) ที่เคยตั้งไว้ใน `pending_pi` มารวมด้วย**

---

## 3. ผลการไล่โค้ดด้วยมือ (manual trace) — ยังไม่ได้รัน pytest จริง

ป้อนแถว PI7 จาก `test_data/SettingOutTest.csv` เข้า `parse_pi_table` ตามลำดับ column
`POINT,STA,NORTHING,EASTING,RADIUS,Ls,LsIn,LsOut,Transition,Delta`:

| ขั้นตอน | แถว | สถานะภายใน |
|---|---|---|
| 1 | `PI7,,1565169.659,680911.287,300,,,,,20` | `pending_pi = {'n':1565169.659,'e':680911.287,'R':300.0}` — **Delta=20 ไม่ถูกอ่าน** |
| 2 | `,,,,150,,,,,` | `compound_arcs = [{'R':150.0}]` |
| 3 | `PI8,,...` (แถวถัดไป, ไม่ว่าง) → เรียก `_flush_pending()` | `v = {'n':1565169.659,'e':680911.287,'compound':[{'R':150.0}]}` — **R=300.0 ของ PI7 หายไป** |

**ผลลัพธ์สุทธิ:** vertex ของ PI7 ที่ถูกส่งต่อไปยัง `build_alignment_from_pi` จะเหลือแค่
`compound: [{'R': 150.0}]` — arc แรก (R=300, delta=20) หายไปทั้งคู่ และ compound ที่ได้
มีแค่ 1 arc ซึ่งไม่ใช่ compound curve ที่ถูกต้อง (ต้องมี ≥2 arc ตาม docstring บรรทัด 16-18)

---

## 4. เทียบกับ test case ที่มีอยู่จริง (`tests/builders/test_alignment_builder.py:809`)

```python
def test_compound(self):
    rows = _rows(
        ['BP', '1000', '2000', '0', '', '', '', '', '', ''],
        ['PI', '1100', '2100', '',  '', '', '', '', '', ''],      # no R → compound
        ['',   '',     '',     '',  '300', '', '', '', '', '20'], # arc 1 with delta
        ['',   '',     '',     '',  '150', '', '', '', '', ''],   # arc 2 (last, no delta)
        ['EP', '1200', '2200', '',  '', '', '', '', '', ''],
    )
    verts = ab.parse_pi_table(rows)
    pi = verts[1]
    assert 'compound' in pi
    assert 'R' not in pi
    assert len(pi['compound']) == 2
    assert pi['compound'][0] == {'R': 300.0, 'delta': 20.0}
    assert pi['compound'][1] == {'R': 150.0}
```

Pattern ที่ผ่าน test นี้ **ต้องมี RADIUS ว่างเปล่าในแถว PI เอง** แล้วให้ทุก arc
(รวม arc แรกที่มี delta) ไปอยู่ในแถวว่างที่ตามมาทั้งหมด — ต่างจากแถว PI7 ใน
SettingOutTest.csv ที่ RADIUS/Delta ของ arc แรกอยู่ในแถว PI เอง

---

## 5. เอกสารที่ขัดแย้งกันเอง

`docs/SMT_CLI_Manual.md` บรรทัด 63-70 ใช้ตัวอย่าง CSV เดียวกับ SettingOutTest.csv
(รวมแถว PI7) เป็นตัวอย่างมาตรฐาน แต่บรรทัด 91 อธิบายว่า:

> "Compound curve: PI row ตามด้วยแถวที่ POINT ว่างแต่มี RADIUS **และ DELTA**"

คำอธิบายนี้ขัดกับตัวอย่างของตัวเอง เพราะแถวว่างในตัวอย่างมีแค่ RADIUS (150) ไม่มี DELTA
ส่วน DELTA (20) อยู่ในแถว PI7 เอง

---

## 6. สรุปผลการตรวจสอบ

| ประเด็น | ผล |
|---|---|
| การตีความทิศทาง arc (เรียงตาม BP→EP, arc สุดท้ายไม่มี delta) | **ถูกต้อง** — ตรงกับ docstring และโค้ด build (บรรทัด 71-84) |
| RADIUS ในแถวว่าง = R ตัวที่สอง ต่อจาก R ของแถว PI ก่อนหน้า | **ไม่ตรงกับโค้ดจริง** — โค้ดปัจจุบันไม่รองรับการมี R ในแถว PI ร่วมกับ compound sub-row ตามมา |
| Pattern ใน SettingOutTest.csv (PI7 มี R+Delta, แถวว่างมี R อย่างเดียว) | **ทำให้ข้อมูล arc แรกหายเงียบ** เมื่อผ่าน `parse_pi_table` ปัจจุบัน (พิสูจน์ด้วย manual trace ข้อ 3) |
| เอกสาร SMT_CLI_Manual.md | คำอธิบาย compound curve ขัดกับตัวอย่างของตัวเอง |
| Test ที่ผ่านจริง (`test_compound`) | ต้องให้แถว PI มี RADIUS ว่างเปล่า แล้ว arc ทั้งหมด (รวม arc แรก) อยู่ในแถวว่างที่ตามมา |

**สถานะ:** ยังไม่ยืนยัน pattern ที่ผู้ใช้เสนอ — พบว่าไฟล์ตัวอย่างจริง (SettingOutTest.csv)
และเอกสารคู่มือ (SMT_CLI_Manual.md) ใช้ pattern ที่ **ไม่ผ่านการ parse ถูกต้องตามโค้ดปัจจุบัน**
ยังไม่พบเงื่อนไขเรื่อง spiral/transition ร่วมกับ compound หรือข้อจำกัดจำนวนแถวว่างต่อกัน
(compound มากกว่า 2 โค้ง) — โค้ดดูรองรับหลายแถวว่างต่อกันได้ในทางทฤษฎี แต่ยังไม่มี test ยืนยัน

---

## 7. ข้อเสนอ (รอการตัดสินใจ — ยังไม่ลงมือทำ)

ต้องเลือกทางใดทางหนึ่งก่อนสร้างไฟล์ทดสอบ compound curve ใหม่:

- **(ก)** แก้ CSV/เอกสารตัวอย่างให้ตรงกับโค้ดปัจจุบัน — ย้าย R=300,Delta=20 ออกจากแถว PI7
  ไปเป็นแถวว่างแยกต่างหาก (ตาม pattern ของ `test_compound`)
- **(ข)** แก้โค้ด `parse_pi_table`/`_flush_pending` ให้รองรับ pattern ที่แถว PI มี R ของ
  arc แรกได้โดยตรง — ต้องผ่านวงจร plan-review ตาม CLAUDE.md ส่วนที่ 3 ก่อนแก้จริง

ไม่มีการแก้ไฟล์หรือรัน pytest ในรายงานฉบับนี้
