# รายงาน: การจัดการ PI ที่ไม่มีรัศมีโค้ง (No-Curve / Angle Point)

วันที่: 2026-06-28  
สถานะ: อ่าน/วิเคราะห์เท่านั้น — ไม่มีการแก้โค้ดหรือ test ใดๆ

---

## 1. Oracle (reference/AlignmentBuilder.gs) จัดการอย่างไร

### ข้อมูลจาก header comment (บรรทัด 5-7)

```
 *  รับ: PI polyline = [BP, {PI,...}, ..., EP]
 *    - BP (จุดแรก) / EP (จุดท้าย) = จุดปลาย ไม่มีโค้ง  {sta,n,e}
 *    - จุดกลาง = PI แต่ละโค้ง รองรับ 4 แบบ: ...
```

Oracle **ออกแบบมาเพื่อรองรับเฉพาะ BP/EP เท่านั้น** ที่เป็น "no-curve" —
PI ตรงกลางทุกจุดถูกสมมติว่าต้องมี `R` หรือ `compound` เสมอ

### โค้ดส่วนที่เกี่ยวข้อง: `curveSubs_` (บรรทัด 33-65)

```js
function curveSubs_(vert, absD) {
    var subs = [], issue = null;

    // --- ตรวจ compound ก่อน ---
    if (vert.compound && vert.compound.length) { ... }

    // --- บรรทัด 48: สมมติว่า vert.R มีอยู่เสมอ ---
    var R = Math.abs(vert.R);          // ← ไม่มี guard ใดๆ
    var LsIn  = ...
    var LsOut = ...
    ...
    subs.push({ kind: 'C', R: R, len: R * absD });  // โค้งธรรมดา
    return { subs: subs, issue: issue };
}
```

**ถ้า `vert.R` ไม่มี (undefined):**
- JavaScript คืน `undefined` (ไม่ crash)
- `Math.abs(undefined) = NaN`
- `R = NaN` → `subs = [{kind:'C', R:NaN, len:NaN}]`
- `endDisp_` คำนวณต่อด้วย NaN → คืน `{n:NaN, e:NaN}`
- `d1 = NaN` → `curveStart = {n:NaN, e:NaN}`
- **เรขาคณิตทั้งหมดพัง (NaN propagation) โดยไม่มีข้อความ error**

**กรณีพิเศษ: delta = 0 (PI ตรงแนว / collinear)**
```js
var det = Math.sin(delta);   // = sin(0) = 0
var d1 = (...) / det;        // = Infinity หรือ NaN
```
→ หารด้วยศูนย์ — Oracle ไม่รองรับกรณีนี้ด้วยเช่นกัน

**สรุป Oracle:** ไม่รองรับ no-curve interior PI อย่างชัดเจน
ไม่มีการ reject — แค่ produce ค่า NaN โดยเงียบ

---

## 2. Python (src/smt/builders/alignment_builder.py) reject ที่ไหน

### จุด crash: บรรทัด 86 ใน `_build_curve_sub_elements`

```python
def _build_curve_sub_elements(
    vert: dict[str, Any], abs_delta: float,
) -> tuple[list[dict[str, Any]], str | None]:

    compound = vert.get('compound')
    if compound:                        # บรรทัด 71-84: ออกถ้ามี compound
        ...
        return subs, issue

    R = abs(float(vert['R']))          # ← บรรทัด 86: KeyError ถ้าไม่มี 'R'!
```

**เงื่อนไข:** ถ้า `vert` ไม่มี key `'R'` และไม่มี key `'compound'`
→ Python raise `KeyError: 'R'` ที่บรรทัด 86 ทันที

**ต่างจาก Oracle:** Oracle silent NaN — Python crash ชัดเจน
แต่ทั้งคู่ไม่ได้ "รองรับ" angle point จริงๆ เหมือนกัน

### ตรวจสอบเพิ่มเติม: บรรทัดอื่นที่เกี่ยวข้อง

```python
# บรรทัด 196-201 (ใน build_alignment_from_pi) — 2×2 solve
det = math.sin(delta)
d1  = (v_n * math.sin(azimuth_out) - v_e * math.cos(azimuth_out)) / det
```

ถ้า `delta = 0` (collinear PI): `det = 0` → `ZeroDivisionError`
กรณีนี้จะยังไม่ถึงเพราะ KeyError ที่บรรทัด 86 มาก่อน —
แต่ถ้าแก้บรรทัด 86 แล้ว ยังต้องระวังบรรทัดนี้ด้วย

---

## 3. วิเคราะห์: ถ้าจะรองรับ no-curve PI ต้องแก้อะไรบ้าง

> ย้ำ: นี่คือการวิเคราะห์เท่านั้น ยังไม่ได้เขียนโค้ด

### 3.1 นิยาม: "no-curve PI" คืออะไร

| กรณี | delta | ความหมาย |
|------|-------|-----------|
| Angle Point | ≠ 0 | มีมุมหักแต่ไม่มีโค้ง เช่น preliminary design |
| Collinear PI | = 0 | PI ตรงแนว ไม่มีมุมหัก ไม่มีโค้ง (สถานีอ้างอิงบนเส้นตรง) |

เงื่อนไขที่ vertex ต้อง detect: `'R'` ไม่อยู่ใน dict และ `'compound'` ไม่อยู่ใน dict

---

### 3.2 ไฟล์และฟังก์ชันที่ต้องแก้

#### A. `_build_curve_sub_elements` (บรรทัด 59-107)

เพิ่ม guard ต้นฟังก์ชัน หลังจากตรวจ compound แล้ว:

```
ถ้าไม่มี 'R' และไม่มี 'compound'
→ คืน ([], None)   ← empty subs = สัญญาณว่าเป็น angle point
```

---

#### B. `_get_control_names` (บรรทัด 110-124)

ปัจจุบัน:
```python
start = 'TS' if subs[0]['kind'] == 'SPIN' else 'PC'   # ← IndexError ถ้า subs=[]
end   = 'ST' if subs[-1]['kind'] == 'SPOUT' else 'PT'  # ← IndexError ถ้า subs=[]
```

ต้องเพิ่ม guard: ถ้า `subs` ว่าง ให้คืน `None` หรือ skip การเรียก

---

#### C. `build_alignment_from_pi` (บรรทัด 154-243)

ส่วนที่ต้องเพิ่ม branch อยู่ที่บรรทัด 189-231 คือหลัง:
```python
subs, issue = _build_curve_sub_elements(vertices[v], abs_delta)
```

ต้องเพิ่ม branch:
```
if not subs:   # angle point — ไม่มีโค้ง
    - ไม่เรียก _calculate_end_displacement
    - ไม่เรียก _get_control_names
    - ไม่ทำ 2×2 solve
    - emit tangent: prev → vertex_pi
    - control.append(ControlPoint('IP', sta_pi, vertex_n, vertex_e))
    - prev = vertex_pi
    - continue
```

ชื่อจุด control ที่แนะนำ: `'IP'` (Intersection Point) ซึ่งเป็น survey term มาตรฐาน

---

#### D. `_calculate_end_displacement` (บรรทัด 127-147)

กรณี `subs = []`:
- ลูป `for s in subs` ไม่วน → คืน `(0.0, 0.0)` โดยธรรมชาติ
- **ปลอดภัยอยู่แล้ว** ไม่ต้องแก้

---

### 3.3 จุดเสี่ยงที่ต้องระวัง

#### ความเสี่ยงที่ 1: `det = sin(delta) = 0` เมื่อ delta = 0

```python
det = math.sin(delta)   # บรรทัด 197
d1  = (...) / det       # ZeroDivisionError ถ้า delta=0
```

กรณี collinear PI (delta=0) ถ้าผ่านมาถึงบรรทัดนี้จะ crash —
แต่ถ้าเรา handle `subs=[]` ก่อน (branch ใหม่) จะ skip บรรทัดนี้ได้

ถ้าต้องการป้องกันเพิ่มเติม: ควรเพิ่ม guard `if abs_delta < epsilon: handle_collinear()`
แยกออกมา ไม่ว่าจะมีโค้งหรือไม่

#### ความเสี่ยงที่ 2: Control naming ชน

ถ้ามีหลาย PI ที่เป็น angle point พร้อมกัน control list จะมีชื่อ `'IP'` ซ้ำหลายครั้ง
`check_against_drawing` กรอง by name — หลาย `'IP'` จะ match กับ `d.sta` closest เท่านั้น
แต่ถ้า user ระบุ `d.name = 'IP'` จะ ambiguous หากมีหลายจุด
**แนวทาง:** ใช้ `'IP1'`, `'IP2'` หรือ `'IP'` เพียงชื่อเดียวขึ้นอยู่กับนโยบาย

#### ความเสี่ยงที่ 3: `_curve_subs` กับ vert ที่มี R=0

`R = 0` ≠ "ไม่มี R" — `vert['R'] = 0` จะผ่าน KeyError แต่จะทำให้
`R = abs(float(0)) = 0.0` และ `len = 0.0` → element ความยาวศูนย์
ต้องตัดสินใจว่า `R=0` ควรถือเป็น tangent (no curve) หรือ error

#### ความเสี่ยงที่ 4: End displacement ≠ 0 สำหรับ angle point

สำหรับ angle point ที่มี `delta ≠ 0` และ `subs = []`:
- `_calculate_end_displacement([],...)` คืน `(0, 0)` ✓
- `d1 = (0 * sin - 0 * cos) / sin(delta) = 0`
- `curve_start = vertex_pi` — ถูกต้อง PI point = จุดหักมุม
- แต่ tangent ออกจาก prev จะมุ่งตรงไปยัง PI ส่วน tangent ถัดไปออกจาก PI ไปยัง
  ทิศทาง `azimuth_out` → ถ้า PI coordinates ที่ user ป้อนมีความคลาดเคลื่อนเล็กน้อย
  จากเส้นตรงจริง จะเกิด "ช่องว่าง" เล็กน้อยในเรขาคณิต (ไม่ใช่ปัญหาของโค้ด
  แต่เป็นปัญหาคุณภาพข้อมูล)

#### ความเสี่ยงที่ 5: Golden test ไม่มี fixture สำหรับ angle point

`tests/golden/tables.json` และ test ทั้งหมดใน `test_alignment_builder.py` ใช้
fixture 30 elements / 31 control ที่ **ทุก PI มีโค้ง** (9 curve groups, zero angle points)
การเพิ่ม feature ต้องเขียน test ใหม่แยกต่างหาก — ไม่กระทบ golden test เดิม

#### ความเสี่ยงที่ 6: `_get_control_names([])` IndexError ยังคงอยู่

ถ้า flow เข้า `_get_control_names` โดย subs ว่าง (ไม่ว่าจะด้วยเหตุใด):
```python
start = 'TS' if subs[0]['kind'] == 'SPIN' else 'PC'  # IndexError!
```
ต้องเพิ่ม guard ใน function นี้เสมอ ไม่ว่าจะเรียกหรือไม่เรียกจาก branch ใหม่

---

## สรุปโดยย่อ

| ประเด็น | Oracle (.gs) | Python (.py) |
|---------|-------------|--------------|
| BP/EP (no-curve) | รองรับ (ออกแบบมาตรง) | รองรับ (ออกแบบมาตรง) |
| Interior no-curve PI (angle point) | ไม่รองรับ — NaN propagation | ไม่รองรับ — `KeyError` บรรทัด 86 |
| Collinear PI (delta=0, no curve) | ไม่รองรับ — division by zero | ไม่รองรับ — `KeyError` บรรทัด 86 (ก่อนถึง /0) |

**ถ้าจะ implement:** จุดเข้าหลักคือ 3 ที่ ได้แก่
`_build_curve_sub_elements` (เพิ่ม early return), `_get_control_names` (guard empty),
และ `build_alignment_from_pi` (branch ใหม่สำหรับ `subs=[]`)
โดยไม่แตะ oracle, golden fixture, หรือ test เดิมแม้แต่บรรทัดเดียว
