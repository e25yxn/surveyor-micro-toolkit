Investigation: LandXML totalX field รายงานค่า L แทนค่า X ปิด (COSINE spiral)
วันที่ 2026-07-06
ประเภทงาน ตรวจสอบ/รายงาน อ่านโค้ดจริง + รันคำนวณจริงเทียบ ยังไม่มีการแก้โค้ดใดๆ ทั้งสิ้น

ที่มา known limitation นี้ถูกบันทึกไว้แล้วใน src/smt/alignment.py docstring (Known
limitations ข้อ 3), session_logs/investigate_sinehalfwave_formula.md, และ
docs/extensions.md หัวข้อ EXT-003 — งานนี้คือการเจาะรายละเอียดโค้ดจุดที่เกิดปัญหาให้ชัดก่อน
วางแผนแก้จริงในรอบถัดไป

---

## 1) `_spiral_geometry` ใน src/smt/landxml.py (บรรทัด 68-82) ทำงานอย่างไร

```python
def _spiral_geometry(R: float, length: float, transition: str, theta_rad: float) -> tuple[float, float, float, float]:
    """(totalX, totalY, tanLong, tanShort) for a spiral, computed canonically:
    a synthetic Element at the origin (n=0, e=0, azimuth=0) curving from
    k_in=0 to k_out=1/R over [0, length], independent of the spiral's real
    position, direction, or SPIN/SPOUT role in the alignment."""
    synthetic = Element(
        type='SPIN', sta_start=0.0, sta_end=length,
        n=0.0, e=0.0, azimuth=0.0,
        k_in=0.0, k_out=1.0 / R, transition=transition,
    )
    state = calculate_point_on_element(synthetic, length)
    total_x, total_y = state.n, state.e
    tan_long = total_x - total_y / math.tan(theta_rad)
    tan_short = total_y / math.sin(theta_rad)
    return total_x, total_y, tan_long, tan_short
```

จุดเรียกใช้: `export_alignment_landxml` บรรทัด 186 (element type `SPIN`) และบรรทัด 207
(element type `SPOUT`) — **ทั้งสองจุดสร้าง `synthetic` เป็น `type='SPIN'` เสมอ** ไม่ว่า
element จริงในแนวเส้นจะเป็น SPIN หรือ SPOUT ก็ตาม เจตนาตามที่ docstring ระบุคือให้
totalX/totalY/tanLong/tanShort เป็นค่า "canonical" ไม่ขึ้นกับตำแหน่ง/ทิศทาง/บทบาทจริงของ
spiral ในแนวเส้น (เทียบเท่ากับสร้าง spiral เดี่ยวๆ ที่จุดกำเนิด azimuth=0 เสมอ)

ผลข้างเคียงของการ hardcode `k_in=0.0` เสมอ: `calculate_point_on_element(synthetic, length)`
จะเข้า **SPIN branch เสมอ** (เพราะ `el.k_in==0`) ไม่ว่า transition จะเป็นอะไร — ดังนั้น
`_spiral_geometry` ไม่เคยเดิน SPOUT branch ของ `calculate_point_on_element` เลย แม้จะเรียก
จาก element จริงที่เป็น SPOUT (บรรทัด 207) ก็ตาม นี่คือพฤติกรรมตั้งใจ ไม่ใช่บั๊ก — ยืนยันแล้ว
ด้วย test ที่มีอยู่ (`test_landxml.py` บรรทัด 297-298: SPIN กับ SPOUT ต้อง totalX/totalY/
tanLong/tanShort ตรงกันเป๊ะ)

## 2) `_sine_halfwave_point` ใน src/smt/alignment.py (บรรทัด 128-144)

```python
def _sine_halfwave_point(x: float, big_x: float, r: float) -> tuple[float, float, float]:
    """..."""
    a = x / big_x
    y = big_x ** 2 / r * (a ** 2 / 4 - (1 - math.cos(math.pi * a)) / (2 * math.pi ** 2))
    theta = math.atan(big_x / r * (a / 2 - math.sin(math.pi * a) / (2 * math.pi)))
    return x, y, theta
```

**ยืนยันแล้ว**: บรรทัดสุดท้าย `return x, y, theta` — ค่า `x` ที่รับเข้ามาเป็นอาร์กิวเมนต์
ถูกคืนกลับตรงๆ เป็นสมาชิกตัวแรกของ tuple โดยไม่ผ่านการคำนวณใดๆ เลย (มีแต่ `y` กับ `theta`
เท่านั้นที่คำนวณจาก `x`) ตรงตามที่บันทึกไว้ในคำถามต้นทาง

จุดเรียกใช้ในกรณี SPIN ที่ `calculate_point_on_element` (บรรทัด 264-269):
```python
if el.transition == 'COSINE' and (el.k_in == 0) != (el.k_out == 0):
    length = el.sta_end - el.sta_start
    if el.k_in == 0:   # SPIN
        r = radius_from_curvature(el.k_out)
        big_x = length - _SINE_HALFWAVE_C * length ** 3 / r ** 2   # ← X ปิดคำนวณไว้แล้วตรงนี้
        x_local, y_local, theta_local = _sine_halfwave_point(d, big_x, r)
```

**ยืนยันแล้ว**: `big_x` (คือค่า X ปิดที่ถูกต้องตามสูตร Civil 3D) **ถูกคำนวณไว้แล้วจริง**
ในบรรทัดนี้ — ปัญหาคือ `_sine_halfwave_point` ถูกเรียกด้วย `d` (ระยะทาง arc ที่ผู้เรียกส่ง
เข้ามา ซึ่งเป็นค่าประมาณของ x ตาม known limitation ข้อ 1 ของโมดูลนี้) เป็นอาร์กิวเมนต์ `x`
ตัวแรก ไม่ใช่ `big_x` ดังนั้นเมื่อถูกเรียกที่ `d = length` (ปลาย element เต็ม — จุดที่
`calculate_exit_state` และ `_spiral_geometry` ใช้งานจริง) `x_local` (สมาชิกตัวแรกของ
tuple ที่คืนกลับ) จึงเท่ากับ `length` เป๊ะ ไม่ใช่ `big_x`

**ยืนยันด้วยการรันโค้ดจริง** (ไม่ใช่แค่อ่าน):
```
R=900, L=100:
  total_x (calculate_point_on_element @ d=L)  = 100.0     (เท่ากับ L เป๊ะ, ==True)
  X ปิดที่ถูกต้องจริง (big_x)                  = 99.972014
  ส่วนต่าง L - X                                = 0.027986 m

R=250, L=50:
  total_x                                       = 50.0    (เท่ากับ L เป๊ะ)
  X ปิดที่ถูกต้องจริง                             = 49.954662
  ส่วนต่าง L - X                                = 0.045338 m
```
ตัวเลขส่วนต่างตรงกับที่บันทึกไว้ใน `alignment.py` docstring เป๊ะ ("L-X is 0.027986m and
0.045338m respectively") → **ยืนยัน bug ตรงตามที่บันทึกไว้ 100%: totalX ที่ export ออกไป
เท่ากับ L เป๊ะ ไม่ใช่ X ปิด**

## 3) แนวทางแก้ที่เป็นไปได้ (ยังไม่เลือก — เสนอไว้ให้ตัดสินใจต่อ)

### ทางเลือก A — คำนวณ X ปิดตรงๆ ใน `landxml.py::_spiral_geometry` เฉพาะกรณี COSINE
เพิ่มเงื่อนไข `if transition == 'COSINE':` แล้วคำนวณ
`big_x = length - 0.0226689447 * length**3 / R**2` ใช้แทนค่า `total_x` ที่ตอนนี้มาจาก
`state.n` ตรงๆ (สูตรเดียวกับค่าคงที่ `_SINE_HALFWAVE_C` ใน `alignment.py`)

ข้อดี:
- จุดแก้เล็ก จำกัดอยู่ในไฟล์ `landxml.py` ไฟล์เดียว ไม่แตะ `alignment.py`/core engine

ข้อเสีย:
- **duplicate ค่าคงที่ `0.0226689447` ไว้ 2 ที่ในโปรเจกต์** เสี่ยงหลุด sync ในอนาคตถ้าแก้
  ค่าคงที่ที่เดียวแล้วลืมอีกที่ — ขัดกับกฎ CLAUDE.md ที่ห้าม "เดาสูตรจากความจำ" ทั้งที่
  `alignment.py` มีค่านี้อยู่แล้วในตัวแปร `_SINE_HALFWAVE_C` (private, ยังไม่ export ให้ไฟล์
  อื่นใช้)
- **ผลกระทบต่อเนื่องที่ต้องตัดสินใจ**: ถ้าแก้แค่ `total_x` แต่ปล่อย `total_y`/`theta_rad`
  ไว้เหมือนเดิม (theta_rad มาจาก exit azimuth จริงของ alignment ซึ่งยังคำนวณที่ d=L แบบเดิม
  ตาม known limitation ข้อ 1) จะเกิดความไม่สอดคล้องเล็กน้อยระหว่าง totalX (ค่าที่ a=1 พอดี)
  กับ totalY/tanLong/tanShort (ยังเป็นค่าที่ d=L) — ยืนยันด้วยตัวเลขจริง R=400, L=60:
  ```
  totalX ปัจจุบัน (d=L)        = 60.000000
  totalX ที่แก้แล้ว (a=1 พอดี)  = 59.969397   (ต่างกัน 3.06 ซม.)
  totalY ปัจจุบัน (d=L)        = 1.339040
  totalY ที่ a=1 พอดี          = 1.336745    (ต่างกันแค่ ~2.3 มม.)
  theta ปัจจุบัน (d=L)         = 0.07489789 rad
  theta ที่ a=1 พอดี           = 0.07482181 rad   (ต่างกัน ~0.0044°)
  ```
  ส่วนต่างของ totalY/theta คือ known limitation ข้อ 1 ที่บันทึกไว้แล้วใน `alignment.py`
  docstring (the "x≈s approximation") ซึ่งเป็นคนละประเด็นจาก totalX แต่เชื่อมโยงกันทาง
  คณิตศาสตร์ — ต้องตัดสินใจว่าจะแก้ totalX อย่างเดียว (ตรงตาม scope ที่ EXT-003/คำถามนี้ระบุ)
  หรือแก้ totalY/theta พร้อมกันไปด้วย (ขยาย scope เกินคำถามเดิม)

### ทางเลือก B — Export ฟังก์ชัน/ค่าคงที่จาก `alignment.py` ให้ `landxml.py` เรียกตรง
เปลี่ยน `_SINE_HALFWAVE_C` เป็นค่าคงที่สาธารณะ (ตัดขีดล่างนำหน้าออก) และ/หรือเพิ่มฟังก์ชัน
สาธารณะเล็กๆ เช่น `calculate_sine_halfwave_big_x(length, r)` ใน `alignment.py` แล้วให้
`landxml.py` import มาใช้ตรง (มี import บรรทัด 25 จาก `.alignment` อยู่แล้ว เพิ่มชื่อเข้าไป
ในรายการได้เลย)

ข้อดี:
- ไม่ duplicate ค่าคงที่/สูตร มีจุดความจริงเดียว (single source of truth) ตรงตามหลัก
  SAFE-SMALL-STABLE-MODULAR ของโปรเจกต์

ข้อเสีย:
- เพิ่ม public surface เล็กน้อยใน `alignment.py` (ต้องตั้งชื่อตาม naming convention ของ
  โปรเจกต์ — verb catalog ปัจจุบันมี `calculate_`/`get_`/`make_`/`build_` ฯลฯ) และเปลี่ยน
  "ขอบเขต" ของโมดูล core เล็กน้อย (จากที่ตอนนี้ `_SINE_HALFWAVE_C`/`_sine_halfwave_point`
  เป็น private ทั้งคู่)
- ยังเจอปัญหา totalY/theta consistency เดียวกันกับทางเลือก A (เป็นคนละแกนกับเรื่อง
  private/public — ทั้งสองทางเลือกต้องตัดสินใจเรื่องนี้เหมือนกัน)

หมายเหตุ: ทั้งสองทางเลือกไม่กระทบ `alignment.py::calculate_point_on_element` หรือ core
engine ของการคำนวณ station-to-coordinate ใดๆ เลย เป็นการแก้เฉพาะจุด export LandXML
เท่านั้น (ยกเว้นถ้าเลือกขยาย scope ไปแก้ totalY/theta ด้วยตามที่กล่าวข้างต้น)

## 4) Test ที่มีอยู่ที่ assert `totalX`

grep คำว่า `totalX` ทั่วโปรเจกต์ พบเฉพาะใน `tests/test_landxml.py` 3 จุด:

| บรรทัด | รายละเอียด | ค่าที่ assert | Transition ที่ใช้ |
|---|---|---|---|
| 284 | ค่า totalX ของ spiral | `totalX ≈ 59.966259` (abs_tol 1e-3) | CLOTHOID (default) |
| 297-298 | SPIN vs SPOUT totalX ต้องตรงกัน | เทียบ SPIN กับ SPOUT ไม่ใช่ค่าคงที่ | CLOTHOID (default) |
| 304 | totalX ต้องเป็นบวก | `> 0` เท่านั้น | CLOTHOID (default) |

ทุก test ข้างต้นเรียกผ่าน helper `_verts_spiral()` (บรรทัด 56-61 ปัจจุบัน) ซึ่ง**ไม่ระบุ
`Transition` เลย** จึง default เป็น `CLOTHOID` เสมอ (ยืนยันด้วย grep คำว่า COSINE/BLOSS/
SINE ทั้งไฟล์ — เจอแค่ที่ unit test ของ `_spiral_lx_type()` บรรทัด 226-228 ซึ่งทดสอบแค่
string mapping ชื่อ transition → spiType เฉยๆ ไม่เกี่ยวกับ `_spiral_geometry` เลย)

**สรุป: ไม่มี test ใดในโปรเจกต์ที่ assert ค่า totalX ของ COSINE โดยเฉพาะ** — การแก้ตาม
ทางเลือก A หรือ B จะไม่กระทบ test ที่มีอยู่แม้แต่ตัวเดียว (ทั้ง 3 test ข้างต้นใช้ CLOTHOID
ซึ่งไม่ผ่าน code path ที่จะแก้เลย) แต่หมายความว่าตอนนี้**ไม่มี regression coverage สำหรับ
COSINE totalX เลย** — ควรเพิ่ม test ใหม่เป็นส่วนหนึ่งของแผนแก้ในรอบถัดไป

## 5) ยืนยันว่า CLOTHOID/BLOSS/SINE ไม่กระทบ — ด้วยการคำนวณจริง (ไม่ใช่แค่อ้างเหตุผล)

รันจริงเทียบ R=400, L=60 ทั้ง 4 transition ผ่านโค้ดปัจจุบัน (θ_true = L/2R = 0.075 rad
เท่ากันทุก shape เพราะทุก shape ออกแบบให้ ∫₀¹f(τ)dτ = 1/2 เท่ากันหมด):

| Shape | total_x (จากโค้ดปัจจุบัน) | เท่ากับ L (=60.0) เป๊ะหรือไม่ |
|---|---|---|
| CLOTHOID | 59.966259 | ไม่ (ตรงกับค่าที่ test บรรทัด 284 assert ไว้จริง) |
| BLOSS    | 59.969205 | ไม่ |
| SINE     | 59.970442 | ไม่ |
| COSINE   | **60.000000** | **ใช่ เป๊ะ — นี่คือบั๊ก** |

เหตุผลเชิงโครงสร้างที่ยืนยันว่าการแก้จะไม่กระทบ 3 shape แรก: CLOTHOID/BLOSS/SINE ไม่เข้า
เงื่อนไข `if el.transition == 'COSINE'` (บรรทัด 264 ของ `alignment.py`) เลย จึงตกไปที่
Simpson integration branch (บรรทัด 286 เป็นต้นไป) เสมอ — เป็นคนละ code path จากจุดที่
ทางเลือก A/B จะแก้ (ซึ่งแก้เฉพาะใน branch บรรทัด 264-284 ของ `alignment.py` หรือเฉพาะ
กรณี `transition=='COSINE'` ใน `landxml.py`) ตัวเลขจริงข้างบนยืนยันเชิงประจักษ์ด้วยว่า
3 shape นี้ไม่ได้บังเอิญมีค่าเท่ากับ L อยู่แล้วในปัจจุบัน (ถ้าการแก้ในอนาคตพลาดไปกระทบ
3 shape นี้ ตัวเลขจะขยับจาก 59.966259/59.969205/59.970442 — เป็นสัญญาณเตือนทันทีว่าแก้
ผิดจุด)

---

## สรุปสถานะ

ยืนยันบั๊กตรงตามที่บันทึกไว้ 100%: `_sine_halfwave_point` คืนค่า `x` อินพุตกลับตรงๆ โดยไม่
ปรับเป็น `big_x`, และ `_spiral_geometry` เรียกด้วย `d=length` เสมอ ทำให้ totalX ที่ export
เท่ากับ L เป๊ะ ไม่ใช่ X ปิดตามสูตร Civil 3D — มีทางแก้ที่เป็นไปได้ 2 ทาง (A: duplicate สูตร
ใน landxml.py, B: export ฟังก์ชัน/ค่าคงที่จาก alignment.py) ทั้งสองทางไม่กระทบ test ที่มีอยู่
(ไม่มี test COSINE totalX อยู่เลย) และไม่กระทบ CLOTHOID/BLOSS/SINE (ยืนยันด้วยตัวเลขจริง)
แต่ทั้งสองทางต้องตัดสินใจเพิ่มว่าจะแก้ totalY/theta (known limitation ข้อ 1) ไปพร้อมกันหรือ
ไม่ — ยังไม่มีการแก้โค้ดใดๆ ในรอบนี้ รอ plan-review-approve รอบถัดไปตามกฎ CLAUDE.md ส่วนที่ 3
ก่อนตัดสินใจเลือกทางและลงมือแก้จริง
