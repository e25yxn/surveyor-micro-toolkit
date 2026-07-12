# สืบสวนสโคป — พอร์ต Google Apps Script (GAS) ให้ตรงกับ Python engine ปัจจุบัน

วันที่ 2026-07-12
ประเภทงาน สืบสวน/รายงานเท่านั้น ยังไม่สร้างหรือแก้ไฟล์ GAS ใดๆ ทั้งสิ้น

บริบท ต้องการทราบขนาดงานพอร์ตส่วนต่างของ Python (โดยเฉพาะ COSINE closed-form +
arc-length inversion) ไปเป็นไฟล์ GAS ใหม่ที่แยกจาก `reference/*.gs` เดิม (frozen
oracle ผ่าน AllTests 45/45 ห้ามแก้แม้แต่บรรทัดเดียว) ตาม pattern เดียวกับ
`reference/vba/` ที่ทำสำเร็จแล้วสำหรับ Excel/VBA

---

## 1. เทียบ `reference/Alignment.gs` (oracle) กับ `src/smt/alignment.py` ปัจจุบัน (หลัง commit ba5de3c)

**COSINE**: `shapeIntegral_` (`:34-47`) ของ oracle ใช้กลไก Simpson-integral
แบบเดียวกับ CLOTHOID/BLOSS/SINE ทุกประการสำหรับ COSINE ด้วย **และที่สำคัญที่สุด —
ไฟล์ oracle เองมี comment แช่แข็งไว้แล้ว (`:38-42`)**:
```
หมายเหตุ สูตร COSINE ในไฟล์นี้เป็นจุดอ้างอิงประวัติศาสตร์ที่แช่แข็งไว้ตามที่ตกลงกันไว้
ไม่ใช่ค่าที่ตรงกับ Civil 3D จริง... ห้ามใช้ไฟล์นี้เป็นจุดอ้างอิงสำหรับ COSINE
ให้ใช้ src/smt/alignment.py แทน
```
หมายความว่าความต่างนี้**ถูกรับรองไว้แล้วตั้งแต่ต้น** ไม่ใช่สิ่งที่เพิ่งค้นพบใหม่

**จุดอื่นที่ตรวจสอบ**:
- ไม่มีแนวคิด `lru_cache`/arc-length-inversion ใน oracle เลย (สมเหตุสมผล เพราะ
  oracle ไม่มีปัญหา COSINE closed-form ที่ต้องแก้)
- ตรรกะ tangent/circular/generic-spiral ใน `pointOnElement` **เหมือน Python's
  `calculate_point_on_element` ทุกประการเชิงโครงสร้าง** (Simpson pattern
  `SPIRAL_STEPS=48` เดียวกัน, bisection style เดียวกันใน
  `projectToElement`/`calculate_projection_to_element`) — ความสัมพันธ์แบบเดียว
  กับที่ VBA เคยมีก่อน Phase 4 พอดี ยืนยันว่ารูปแบบงานพอร์ตคุ้นเคยดี
- EXT-001 (angle point) **ไม่ต้องแก้ core engine เลย** — `curvatureFromRadius`
  ของ oracle จัดการ R ที่เป็น falsy/0 ให้ k=0 อยู่แล้ว ตรรกะ angle-point ทั้งหมด
  อยู่ใน builder (ดูข้อ 2)
- EXT-002 (`fit_radius`, Nelder-Mead) **ไม่มีใน oracle เลย** — `docs/extensions.md`
  ระบุตรงๆ: "Oracle... ไม่มีความสามารถในการหาค่า R ที่ทำให้ alignment ตรงกับแบบ
  มากที่สุด"
- LandXML export (`src/smt/landxml.py`) **ไม่มี oracle เทียบเท่าเลย** — เป็น
  ฟีเจอร์ Python/interop ล้วนๆ เหมือนที่ไม่เคยพอร์ตไป VBA เช่นกัน

---

## 2. เทียบ `reference/AlignmentBuilder.gs` (oracle) กับ `src/smt/builders/alignment_builder.py`

`curveSubs_` (`:33-65`) ใช้สูตรมุมเลี้ยวเชิงเส้นแบบเดียวกัน `thIn=LsIn/(2R)`,
`thOut=LsOut/(2R)` ที่ Python builder **เคยใช้ก่อนแก้เองด้วย** พิสูจน์ทางคณิตศาสตร์
ในรอบนี้ว่าสูตรเชิงเส้นนี้**ถูกต้องเป๊ะสำหรับ CLOTHOID/BLOSS/SINE** (ทุกชนิดมี
F(1)=0.5 เหมือนกัน) ดังนั้น builder ของ oracle **สอดคล้องกับตัวเองอยู่แล้ว** —
การแก้ builder ฝั่ง Python เป็นผลสืบเนื่องจากการแก้ COSINE closed-form เท่านั้น
ไม่ใช่บั๊กอิสระ

การรองรับ compound curve **เทียบเท่ากันในปัจจุบัน**: oracle ใช้ array
`vert.compound` ของ `{R,delta}` ส่วน Python ใช้แถว compound sub-row ใน PI CSV —
ทั้งคู่ต้องให้ผู้ใช้ป้อน delta ต่อ sub-arc เอง ยังไม่มีตัวไหนมี floating-length
auto-solver ตาม roadmap (`multicurve.py` ยังไม่มีอยู่จริงแม้แต่ในฝั่ง Python)
**ไม่มีอะไรต้องพอร์ตในส่วนนี้ตอนนี้**

---

## 3. ค้นพบสำคัญ — EXT-001 ถูกพอร์ตไป GAS แล้วบางส่วน

`reference/AlignmentBuilderV2.gs` มีอยู่แล้วจริง (commit `7846cb6`,
2026-06-28, บันทึกไว้ใน `session_logs/latest.md:800-810`) — เป็น**สำเนาของ
`AlignmentBuilder.gs` พร้อม patch เพิ่ม 3 จุดสำหรับ angle-point** (`curveSubs_`
early-return, `names_` IP guard, `buildFromPI` angle-point branch), มี header
comment ระบุชัดว่าอ้างอิง Python commit `cdf896d` และ **ไม่แตะ
`AlignmentBuilder.gs` ต้นฉบับเลย**

นี่คือตัวอย่างจริงของ pattern "copy oracle แล้ว patch เพิ่ม ไม่แตะต้นฉบับ" ที่
ผู้ใช้ต้องการทำให้เป็นทางการ — แต่ตอนนี้ไฟล์นี้อยู่ที่ `reference/` root ตรงๆ
(ไม่ใช่ subfolder) และตั้งชื่อแบบ `V2` suffix ไม่ใช่ prefix แบบ `SMT_`/`GS_` —
เป็นความไม่สอดคล้องด้าน naming/placement ที่ควรพิจารณาตอนวางแผนจริง

---

## 4. ความสามารถของ environment GAS

**V8 runtime** (จาก https://developers.google.com/apps-script/guides/v8-runtime):
`let`/`const`, arrow function, และ class มีเอกสารยืนยันว่ารองรับชัดเจน

**`Map`/`Set` ยืนยันแล้วจริงว่าใช้งานได้ใน GAS V8 runtime** — ตรวจสอบเพิ่มเติมนอกเหนือ
จากเอกสาร Google official แล้ว ไม่ใช่แค่การคาดเดาจากการที่ V8 เป็น JS engine
เต็มรูปแบบ **สรุปว่าใช้ `Map` แทน Python's `lru_cache`-backed table ได้จริง**
โดยไม่ต้องออกแบบกลไก caching เองจากศูนย์แบบที่ VBA ต้องทำ (VBA ไม่มี native
key-value store ต้องใช้ `Scripting.Dictionary` ซึ่งเป็นคนละ API และคนละข้อจำกัด)

**ข้อจำกัด custom function** (จาก
https://developers.google.com/apps-script/guides/sheets/functions):
- parameter เซลล์เดี่ยวส่งค่าดิบ, parameter range กลายเป็น 2D JavaScript array
  อัตโนมัติ (ไม่ต้องผ่าน `.Cells(i,j).Value` แบบ VBA)
- argument ต้อง deterministic (ห้ามใช้ NOW()/RAND())
- ค่าที่คืนเป็น 2D array จะ overflow ลงเซลล์ว่างข้างเคียง หรือ error ถ้ามีข้อมูลขวาง
- **ต้องรันจบภายใน 30 วินาที** (ข้อจำกัดจริงที่ VBA ไม่มี แต่ต้นทุนต่อการเรียกครั้ง
  เดียวของ Simpson 48 จุด + bisection 50 รอบอยู่ระดับไมโครวินาที จึงไม่น่าเป็นปัญหา
  จริงในทางปฏิบัติ)
- custom function แก้เซลล์อื่นไม่ได้ เรียก service ที่ต้องขออนุญาตไม่ได้

**สำคัญที่สุด: JavaScript/GAS ไม่มีแนวคิด ByRef/ByVal parameter แยกกันเลย** บั๊ก
ประเภทที่เจอใน VBA Phase 4 (`SMT_WCBatSta`'s "ByRef argument type mismatch"
จากการส่ง element ของ Variant array ตรงๆ เข้า Double parameter) **เกิดขึ้นไม่ได้
เลยเชิงโครงสร้างใน GAS** ไม่มี pitfall แบบเดียวกันให้ต้องระวัง

---

## 5. Test harness — ยืนยันว่าไม่มีจริง (เหมือน VBA) แต่มีโอกาสที่ VBA ไม่เคยมี

grep หา test function/assertion/QUnit ทั่ว `reference/*.gs` ทุกไฟล์ — **ไม่พบเลย
สักไฟล์เดียว** "AllTests 45/45" น่าจะรันในสภาพแวดล้อม GAS IDE จริงในอดีต ไม่มี
harness เก็บไว้ใน repo นี้เลย

**แต่พบโอกาสจริงที่ VBA ไม่เคยมี**: ทุกไฟล์ oracle `.gs` ลงท้ายด้วย
`if (typeof module !== 'undefined' && module.exports) module.exports = X;`
(ยืนยันแล้วทั้ง `Alignment.gs:268` และ `AlignmentBuilder.gs:175`) หมายความว่า
ไฟล์เหล่านี้**เป็น Node-requireable อยู่แล้ว**ในฐานะ CommonJS module ธรรมดา
เป็นไปได้จริงที่จะสร้าง automated test harness จริง (Node + Jest, `require()`
ไฟล์ .gs ตรงๆ แล้ว assert เทียบกับ golden fixture ชุดเดียวกับที่ Python/VBA ใช้)
**ซึ่ง VBA ไม่มีทางทำได้เลย** — ควรพิจารณาลงทุนทำถ้าต้องการ verification ที่ดีกว่า
manual-Excel-only ของ VBA

---

## 6. ประเมินขนาดงานเทียบกับ VBA Phase 4 — ขึ้นกับขอบเขตที่เลือก ไม่ใช่ตัวเลขเดียว

**ถ้ากำหนดขอบเขตเหมือน VBA Phase 4 เป๊ะ** (COSINE closed-form + arc-length
inversion เท่านั้น แตะแค่ไฟล์เทียบเท่า `Alignment.gs`): **เล็กกว่า VBA** เพราะ
(ก) GAS เป็นตระกูลภาษาเดียวกับ oracle ไม่มีความเสี่ยงข้ามภาษาแบบ Python→VBA
(ข) `lru_cache` เทียบเท่าคือ native `Map` (ยืนยันใช้งานได้จริงแล้วตามข้อ 4) แทนที่จะ
ต้องออกแบบ `Scripting.Dictionary` จากศูนย์แบบ VBA
(ค) ไม่มี pitfall ประเภท ByRef เลย
(ง) เป็นไปได้จริงที่จะมี automated test harness (Node+Jest) ต่างจาก VBA ที่ทำได้
แค่ manual เท่านั้น

**ถ้ากำหนดขอบเขตรวม EXT-002 (`fit_radius`/Nelder-Mead) เพื่อ feature parity เต็ม**:
**ใหญ่กว่า VBA Phase 4** เพราะเป็นงานพอร์ต algorithm จากศูนย์ (`optimizer.py`
171 บรรทัด, scipy Nelder-Mead ไม่มี built-in เทียบเท่าใน GAS ต้องเขียน
Nelder-Mead เองใน JS) ไม่มีตัวอย่างมาก่อนเลยในโปรเจกต์นี้แม้แต่ฝั่ง VBA (VBA
Phase 4 ก็ไม่เคยแตะ `fit_radius` เช่นกัน)

**แนะนำ**: กำหนดขอบเขตงานพอร์ต GAS รอบแรกให้เหมือน VBA Phase 4 เป๊ะ (COSINE
closed-form + arc-length inversion ในไฟล์เทียบเท่า `Alignment.gs` เท่านั้น) ไม่รวม
EXT-002 เว้นแต่ผู้ใช้ต้องการ feature parity เต็มรูปแบบชัดเจน

---

## 7. โครงสร้างไฟล์/โฟลเดอร์ที่เสนอ (ตาม pattern `reference/vba/`)

- โฟลเดอร์ใหม่: `reference/gsheet/`
- ตั้งชื่อไฟล์ด้วย prefix `GS_` เทียบเท่า prefix `SMT_` ของ VBA — เช่น
  `GS_Alignment.gs` (mirror `Alignment.gs` + เพิ่มฟังก์ชัน COSINE closed-form/
  arc-length-inversion), `GS_AlignmentBuilder.gs` เฉพาะเมื่อจำเป็นต้องแก้
  turning-angle ระดับ builder ด้วย (จำเป็นจริง ด้วยเหตุผลเดียวกับที่ Python
  builder ต้องแก้ — พอ COSINE ได้ closed form แล้ว สูตรเชิงเส้น thIn/thOut
  จะผิดเฉพาะ COSINE)
- **คำถามเปิดที่ควรพิจารณาตอนวางแผนจริง ไม่ใช่ตัดสินใจตอนนี้**: จะทำอย่างไรกับ
  `reference/AlignmentBuilderV2.gs` เดิม (EXT-001 ที่พอร์ตไป GAS แล้ว อยู่ที่
  `reference/` root ไม่ใช่ subfolder) — ย้ายเข้า `reference/gsheet/` เป็นส่วนหนึ่ง
  ของงานนี้ หรือปล่อยไว้เป็น legacy แล้ววางงานใหม่จริงๆ ในโฟลเดอร์ใหม่เท่านั้น
- ตามขอบเขตที่ผู้ใช้ระบุไว้ชัดเจน (ข้อหนึ่งจำกัดการเทียบไว้แค่
  `Alignment.gs`/`AlignmentBuilder.gs`) รายงานนี้**ไม่เสนอ**
  `GS_Vertical.gs`/`GS_Crossfall.gs`/ฯลฯ เพราะยังไม่ได้สืบสวนหรือพบความต่างใดๆ
  สำหรับโมดูลเหล่านั้นในรอบนี้

---

## สรุป

ยังไม่มีการเขียนแผนพอร์ตจริงในรอบนี้ตามคำสั่งของผู้ใช้ รายงานนี้ระบุแค่ข้อเท็จจริง
และประเมินขนาดงานเท่านั้น

## อ้างอิง

- https://developers.google.com/apps-script/guides/v8-runtime
- https://developers.google.com/apps-script/guides/sheets/functions
- `session_logs/latest.md:800-810` (การเพิ่ม `AlignmentBuilderV2.gs`, commit `7846cb6`)
- `docs/extensions.md` (EXT-001, EXT-002, EXT-003)
