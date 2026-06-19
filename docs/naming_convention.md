# มาตรฐานการตั้งชื่อ — SMT Naming Convention
### แนวทางให้ Claude Code เขียนโค้ดชื่อสม่ำเสมอทุกภาษา (Python = ภาษาหลัก)

> ปรับปรุงจากเอกสาร "Universal Naming Convention" โดยแยกให้ชัดเป็น **2 ชั้น** เพื่อให้
> *ความหมาย* เหมือนกันทุกภาษา ส่วน *การสะกด* ปรับตามภาษา (แก้ประเด็น camelCase กับ Python)

---

## หลักคิดสำคัญ: แยก "ความหมาย" ออกจาก "การสะกด"

| ชั้น | คืออะไร | เหมือนกันทุกภาษาไหม |
|---|---|---|
| **Semantic (ความหมาย)** | โครงสร้างชื่อ + คลังคำ + กฎ 4 ข้อ | เหมือนกันทุกภาษา |
| **Casing (การสะกด)** | camelCase / snake_case / PascalCase | ปรับตามภาษา |

ชื่อ *ตรรกะเดียวกัน* คนละภาษา:
- JS / Apps Script / VBA / Dart : `calculateNorthingFromAzimuth()`
- **Python (SMT core)** : `calculate_northing_from_azimuth()`

> เหตุผล: Python มีมาตรฐาน PEP 8 ใช้ snake_case กับฟังก์ชัน/ตัวแปร/เมธอด ซึ่งสอดคล้องกับที่
> เอกสารต้นฉบับระบุไว้แล้วว่า "ตัวแปรในภาษา Python ใช้ snake_case" — เราแค่ขยายให้ครอบคลุม
> ฟังก์ชัน/เมธอดด้วยเพื่อความสม่ำเสมอ

---

## 1. โครงสร้างสมการชื่อ (Naming Anatomy) — universal
```
[ 1. Action กริยา ] + [ 2. Target เป้าหมาย/ผลลัพธ์ ] + [ 3. Context บริบท/เงื่อนไข ]
```
- ส่วนที่ 3 (Context) ละได้ถ้าบริบทชัดแล้ว
- ตัวอย่าง: `calculate` + `northing` + `from_azimuth` -> `calculate_northing_from_azimuth`

## 2. การสะกดตามภาษา (Casing)
| สิ่งที่ตั้งชื่อ | Python (core) | JS / Apps Script / VBA / Dart | DB column / ชื่อไฟล์ |
|---|---|---|---|
| ฟังก์ชัน / เมธอด / ตัวแปร | `snake_case` | `camelCase` | `snake_case` |
| คลาส / โมเดล / หน้าจอ UI | `PascalCase` | `PascalCase` | - |
| ค่าคงที่ (Constant) | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` | - |

## 3. คลังคำกริยา (Approved Verbs) — "หนึ่งความหมาย หนึ่งคำ" (กฎข้อ 2)
| ความหมาย | ใช้ | ห้ามสลับไปใช้ |
|---|---|---|
| คำนวณค่าทางคณิตศาสตร์ / ค่าอนุพันธ์ | `calculate_` | compute, evaluate |
| ดึงค่าที่มีอยู่ / ค้นหา (lookup) | `get_` | fetch, retrieve |
| สร้างวัตถุชิ้นเดียว | `make_` | create, new |
| ประกอบหลายชิ้นเป็นชุด | `build_` | assemble, generate |
| อ่านตาราง/ข้อความ -> โครงสร้าง | `parse_` | read, load |
| ปรับให้อยู่รูปมาตรฐาน | `normalize_` | fix, clean |
| ปัด / ตัดเลข | `round_` / `trunc_` | - |
| ตรวจสอบ / cross-check (คืนรายงาน) | `check_` | verify, validate |
| ค่าความจริง (boolean) | `is_` / `has_` / `in_` | - |

**idiom พิเศษ — การแปลงหน่วย** ใช้รูป `<source>_to_<target>` เพราะอ่านลื่นกว่า เช่น
`deg_to_rad`, `rad_to_dms_string`, `packed_dms_to_rad` (ไม่ต้องเป็น `convert_...`)

## 4. คลังคำนามของโดเมน (Ubiquitous Language) — พูดภาษาผู้เชี่ยวชาญ (กฎข้อ 3)
ใช้ศัพท์สำรวจจริง ไม่ใช้คำพื้นๆ:
`alignment, element, station(sta), offset, northing(n), easting(e), level/elevation,
azimuth(WCB), bearing, curvature(k), radius(R), tangent, circular, spiral,
transition(clothoid/bloss/cosine/sine), deflection, chord, vertical_curve, grade,
crossfall, superelevation, PI, VPI, PC, PT, SC, CS, TS, ST, control_point, deviation,
profile, traverse, project`

**ตัวย่อที่อนุญาตเท่านั้น** (เพราะเป็นศัพท์สากลของสายงาน):
`N . E . sta . R . k . PI . VPI . PC . PT . SC . CS . TS . ST . WCB . LVC . dms`
- นอกเหนือจากรายการนี้ ให้สะกดเต็มเสมอ (เช่น `azimuth` ไม่ใช่ `az`, `distance` ไม่ใช่ `dist`)

## 5. กฎเหล็ก 4 ข้อ (จากเอกสารต้นฉบับ — universal)
1. **ความชัดเจน > ความสั้น** — `calculate_new_northing()` ไม่ใช่ `cal_n()`
2. **คำศัพท์มาตรฐานเดียวกัน** — เลือก `calculate` แล้วใช้ทั้งโปรเจกต์ (ดูคลังข้อ 3)
3. **พูดภาษาผู้เชี่ยวชาญ** — `azimuth`, `traverse`, `project` ไม่ใช่ `angle`, `move_point`, `job`
4. **ตัดความซ้ำซ้อนตามบริบท** — ในคลาส `Coordinate` ใช้ `.calculate_northing()`
   ไม่ใช่ `.calculate_coordinate_northing()`

## 6. ตัวอย่างปรับใช้กับโค้ด SMT ปัจจุบัน
| ชื่อปัจจุบัน | สถานะ | แนะนำ |
|---|---|---|
| `normalize_angle` | ตรงมาตรฐาน | คงไว้ |
| `round_to` / `trunc_to` | ตรงมาตรฐาน | คงไว้ |
| `deg_to_rad`, `rad_to_dms_string`, `dms_to_rad` | idiom x_to_y | คงไว้ |
| `kahan_sum` | ชื่ออัลกอริทึมสากล | คงไว้ |
| `almost_equal`, `in_range` | boolean ควรขึ้นต้น is_/in_ | `is_almost_equal`, `is_in_range` |
| `mod` | สั้นเกิน/ไม่สื่อ | `floor_mod` (ชัดว่าได้ผลบวกเสมอ) |
| `forward_compute`, `inverse_compute` | ไม่มีกริยานำ | `calculate_forward`, `calculate_inverse` |
| `azimuth_from_coords` | ไม่มีกริยานำ | `calculate_azimuth` (Context ละได้) |
| `distance_2d`, `distance_3d` | ไม่มีกริยานำ | `calculate_distance_2d`, `calculate_distance_3d` |

> สถานะ: คอลัมน์ "แนะนำ" ด้านบน **ปรับใช้แล้วใน v0.3** (fpmath/wcb + เทสต์ 14/14) ตารางนี้คงไว้เป็น before/after เพื่อการเรียนรู้
> ก่อนโค้ดจะโตขึ้น — ทำพร้อมอัปเดตเทสต์ในคราวเดียว

## 7. บล็อกพร้อมวางใน CLAUDE.md (สั่ง Claude Code)
```
## Naming (full guide: docs/naming_convention.md)
- Anatomy (all languages): name = [verb Action] + [Target] + [Context],
  e.g. calculate_northing_from_azimuth. Context may be dropped if obvious.
- Casing (Python core): snake_case for functions/methods/variables; PascalCase for
  classes; UPPER_SNAKE_CASE for constants. (JS/VBA mirror uses camelCase for funcs/vars.)
- Approved verbs (one per concept, use consistently): calculate_ (math), get_ (lookup),
  make_ (one object), build_ (assemble many), parse_ (table->struct), normalize_,
  round_/trunc_, check_ (cross-check), is_/has_/in_ (boolean).
  Unit conversion uses the idiom <source>_to_<target> (deg_to_rad).
- Ubiquitous language: use survey terms (alignment, station, offset, azimuth/WCB,
  curvature, radius, tangent, spiral, transition, vertical_curve, grade, crossfall,
  PI, VPI, PC, PT, control_point, deviation, profile).
- Allowed abbreviations ONLY: N, E, sta, R, k, PI, VPI, PC, PT, SC, CS, TS, ST, WCB,
  LVC, dms. Spell out everything else (azimuth not az, distance not dist).
- 4 senior rules: clarity > brevity; one verb per concept; speak the expert's language;
  don't repeat the class/module name inside a method.
```

## 8. Checklist รีวิวชื่อ (ก่อน commit)
- [ ] ขึ้นต้นด้วยกริยาจากคลัง (ข้อ 3) — ยกเว้น idiom `x_to_y`
- [ ] casing ตรงกับภาษา (Python = snake_case)
- [ ] ใช้ศัพท์โดเมน (ข้อ 4) ไม่ย่อนอกเหนือรายการอนุญาต
- [ ] boolean ขึ้นต้น `is_` / `has_` / `in_`
- [ ] ค่าคงที่เป็น `UPPER_SNAKE_CASE`
- [ ] ไม่เอาชื่อคลาส/โมดูลมาตั้งซ้ำในเมธอด (กฎข้อ 4)
- [ ] อ่านชื่อแล้วเข้าใจโดยไม่ต้องดูคอมเมนต์ (กฎข้อ 1)
