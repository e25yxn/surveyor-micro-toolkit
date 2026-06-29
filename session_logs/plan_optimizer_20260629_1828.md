# แผน: src/smt/optimizer.py + tests/test_optimizer.py
วันที่: 2026-06-29 18:28

---

## Context

โปรเจกต์นี้มี pipeline: PI table CSV → `parse_pi_table` → `build_alignment_from_pi` →
`calculate_station_to_coordinate` → พิกัด N, E  
เมื่อพิกัดที่คำนวณได้ vs พิกัดที่วาดไว้ (drawing_points) มี gap เล็กน้อย (~7.4mm จาก
ramp01n01_SO.csv) optimizer จะหา R ที่ทำให้ sum of squared gaps น้อยที่สุด โดย:
- เก็บ sign ของ R แยก ออปไซเมจ optimize เฉพาะ abs(R) เพื่อไม่ให้ flip ทิศทางเลี้ยว
- ใช้ scipy Nelder-Mead ซึ่งไม่ต้องการ gradient (robust กับ function ที่ไม่ smooth)
- ถ้า build มี issues หรือ station outside alignment → penalty 1e6 per point

**ไฟล์ที่ต้องสร้าง/แก้ไข:**
- `src/smt/optimizer.py` — ใหม่
- `tests/test_optimizer.py` — ใหม่
- `pyproject.toml` — เพิ่ม `[optimize]` optional group

---

## 1. FitResult dataclass

```python
# src/smt/optimizer.py

from dataclasses import dataclass

@dataclass
class FitResult:
    names:       list[str]   # ชื่อ PI ที่ถูก optimize (ไม่รวม fix_names)
    r_initial:   list[float] # signed R เริ่มต้น (จาก CSV)
    r_optimized: list[float] # signed R หลัง optimize (sign เดิม, abs ใหม่)
    gap_before:  float       # √(Σgap²) ก่อน optimize (เมตร)
    gap_after:   float       # √(Σgap²) หลัง optimize (เมตร)
    n_points:    int         # จำนวน drawing points ที่ใช้ใน objective
    iterations:  int         # รอบที่รัน (scipy result.nit หรือ nfev)
    converged:   bool        # scipy result.success
    message:     str         # scipy result.message
```

**หมายเหตุ:** `gap_before` / `gap_after` = L2-norm ของ vector ของ gaps = √(Σgap_i²)
ให้ unit เป็นเมตร และตีความได้ง่าย (≈ RMS × √n)

---

## 2. fit_radius — signature และ logic

```python
def fit_radius(
    pi_rows:        list[Any],             # raw CSV rows รวม header (row[0] = header)
    drawing_points: list[dict[str, Any]],  # [{name, sta, n, e}, ...]
    fix_names:      list[str] | None = None,
    tol:            float = 1e-6,
    max_iter:       int   = 10000,
) -> FitResult:
```

### Logic ทีละขั้น

**ขั้น A — หา Free PIs**

```python
# header analysis
header = [str(c).strip().lower() for c in pi_rows[0]]
point_col = index of 'point' or 'bp'/'ep'/'pi...' marker
r_col     = index of 'r' or 'radius' in header

# scan rows
free_pis = []   # list of (row_idx, pi_name, sign, abs_r_initial)
for i, row in enumerate(pi_rows[1:], start=1):
    point = str(row[point_col]).strip()
    if point in ('BP', 'EP') or not point:
        continue
    r_raw = str(row[r_col]).strip()
    if not r_raw or float(r_raw) == 0.0:
        continue   # angle point → skip
    if fix_names and point in fix_names:
        continue   # fixed → skip
    r_val  = float(r_raw)
    sign   = 1.0 if r_val > 0 else -1.0
    free_pis.append((i, point, sign, abs(r_val)))
```

**ขั้น B — filter drawing points**

```python
active_pts = [
    dp for dp in drawing_points
    if not str(dp.get('name', '')).strip().upper().startswith(('PI', 'HIP'))
]
```

**ขั้น C — objective function**

```python
def objective(x: np.ndarray) -> float:
    # สร้าง rows ชั่วคราว — แก้ R column ตาม x
    rows = [list(r) for r in pi_rows]
    for k, (row_idx, _, sign, _) in enumerate(free_pis):
        rows[row_idx][r_col] = str(sign * float(x[k]))

    try:
        vertices = parse_pi_table(rows)
        result   = build_alignment_from_pi(vertices)
    except Exception:
        return 1e6 * len(active_pts)

    if result.issues:
        return 1e6 * len(result.issues) + 1e6 * len(active_pts)

    total_sq = 0.0
    for dp in active_pts:
        try:
            pt  = calculate_station_to_coordinate(result.elements, float(dp['sta']))
            gap = math.hypot(pt.n - float(dp['n']), pt.e - float(dp['e']))
            total_sq += gap * gap
        except ValueError:
            total_sq += 1e6
    return total_sq
```

**ขั้น D — compute gap_before**

```python
x0          = np.array([abs_r for (_, _, _, abs_r) in free_pis])
obj_before  = objective(x0)
gap_before  = math.sqrt(obj_before) if obj_before < 1e12 else obj_before
```

**ขั้น E — ถ้าไม่มี free PIs → return ทันที**

```python
if not free_pis:
    return FitResult(
        names=[], r_initial=[], r_optimized=[],
        gap_before=gap_before, gap_after=gap_before,
        n_points=len(active_pts), iterations=0,
        converged=True, message='no free radii to optimize',
    )
```

**ขั้น F — scipy.optimize.minimize**

```python
from scipy.optimize import minimize

result = minimize(
    objective, x0,
    method  = 'Nelder-Mead',
    options = {'xatol': tol, 'fatol': tol**2, 'maxiter': max_iter, 'disp': False},
    bounds  = [(1.0, None)] * len(x0),   # scipy >= 1.7 รองรับ bounds + Nelder-Mead
)
```

**ขั้น G — build FitResult**

```python
gap_after   = math.sqrt(result.fun) if result.fun < 1e12 else result.fun
r_initial   = [sign * abs_r   for (_, _, sign, abs_r) in free_pis]
r_optimized = [sign * float(result.x[k]) for k, (_, _, sign, _) in enumerate(free_pis)]
names       = [pi_name for (_, pi_name, _, _) in free_pis]

return FitResult(
    names=names, r_initial=r_initial, r_optimized=r_optimized,
    gap_before=gap_before, gap_after=gap_after,
    n_points=len(active_pts),
    iterations=int(result.nit),
    converged=bool(result.success),
    message=str(result.message),
)
```

---

## 3. pyproject.toml — เพิ่ม optional group

```toml
[project.optional-dependencies]
dev      = ["pytest>=7", "hypothesis>=6", "mypy>=1.5", "ruff>=0.4"]
docs     = ["mkdocs-material"]
notebook = ["jupyter", "matplotlib"]
optimize = ["scipy>=1.10"]
```

---

## 4. Tests (tests/test_optimizer.py)

### Import pattern (ตาม existing tests)
```python
import math, csv, io
from pathlib import Path
import pytest
from smt.optimizer import fit_radius, FitResult
from smt.builders.alignment_builder import parse_pi_table, build_alignment_from_pi
from smt.alignment import calculate_station_to_coordinate
```

### Helper — build minimal pi_rows ในรูป list[list]
```python
def _make_rows(bp_n, bp_e, pis, ep_n, ep_e, sta=0.0):
    """pis = list of (name, n, e, r) — r=0 for angle point"""
    rows = [['POINT', 'N', 'E', 'STA', 'R']]
    rows.append(['BP', bp_n, bp_e, sta, ''])
    for name, n, e, r in pis:
        rows.append([name, n, e, '', r if r else ''])
    rows.append(['EP', ep_n, ep_e, '', ''])
    return rows
```

### Test 1 — Tangent only: ไม่มี R → gap=0, ไม่มี PI ที่จะ optimize

```python
def test_tangent_only():
    """Straight alignment: no free radii, gap starts at 0."""
    rows = _make_rows(0.0, 0.0, [('IP1', 50.0, 50.0, 0)], 100.0, 100.0)
    vertices = parse_pi_table(rows)
    build   = build_alignment_from_pi(vertices)
    # drawing points at known stations, exactly on alignment
    pts = [{'name': 'TP1', 'sta': 20.0,
            'n': calculate_station_to_coordinate(build.elements, 20.0).n,
            'e': calculate_station_to_coordinate(build.elements, 20.0).e}]
    res = fit_radius(rows, pts)
    assert res.names == []
    assert res.n_points == 1
    assert res.gap_before < 1e-9
    assert res.gap_after  < 1e-9
    assert res.converged
```

### Test 2 — Simple curve convergence: R_initial=80, ควร converge ไป R≈100

```python
def test_simple_curve_converge():
    """Optimizer should recover R=100 from a wrong start of R=80."""
    # Build reference alignment with R=100
    rows_ref = _make_rows(0.0, 0.0, [('PI1', 100.0, 50.0, 100)], 200.0, 0.0)
    build_ref = build_alignment_from_pi(parse_pi_table(rows_ref))
    # Compute drawing points at 5 evenly spaced stations inside curve
    sta_end = build_ref.elements[-1].sta_end
    draw_pts = []
    for sta in [30.0, 60.0, 90.0, 120.0, 150.0]:
        if sta > sta_end:
            break
        pt = calculate_station_to_coordinate(build_ref.elements, sta)
        draw_pts.append({'name': f'TP{sta:.0f}', 'sta': sta, 'n': pt.n, 'e': pt.e})

    # Perturbed start: R=80 instead of 100
    rows_bad = _make_rows(0.0, 0.0, [('PI1', 100.0, 50.0, 80)], 200.0, 0.0)
    res = fit_radius(rows_bad, draw_pts)

    assert res.converged or res.gap_after < res.gap_before
    assert len(res.names) == 1
    assert res.names[0] == 'PI1'
    assert abs(abs(res.r_optimized[0]) - 100.0) < 2.0   # ≤ 2m ห่างจากค่าจริง
    assert res.gap_after < res.gap_before
```

### Test 3 — fix_names: PI1 fixed, PI2 ควร optimize

```python
def test_fix_names_keeps_first_radius():
    """PI1 in fix_names must not change; PI2 is free to move."""
    # Reference alignment: PI1=50, PI2=100
    rows_ref = [
        ['POINT', 'N', 'E', 'STA', 'R'],
        ['BP',    0.0,  0.0,  0.0,  ''],
        ['PI1',  80.0, 40.0,  '',   50],
        ['PI2', 160.0, 80.0,  '',  100],
        ['EP',  240.0, 0.0,   '',   ''],
    ]
    build_ref = build_alignment_from_pi(parse_pi_table(rows_ref))
    sta_end   = build_ref.elements[-1].sta_end
    draw_pts  = []
    for sta in [30.0, 80.0, 130.0, 180.0]:
        if sta > sta_end:
            break
        pt = calculate_station_to_coordinate(build_ref.elements, sta)
        draw_pts.append({'name': f'TP{sta:.0f}', 'sta': sta, 'n': pt.n, 'e': pt.e})

    # Perturb PI2's R to 70
    rows_bad = [list(r) for r in rows_ref]
    rows_bad[3][4] = 70   # PI2 R → 70

    res = fit_radius(rows_bad, draw_pts, fix_names=['PI1'])

    assert 'PI1' not in res.names
    assert 'PI2' in res.names
    pi1_idx = next(i for i, n in enumerate(res.names) if n == 'PI1') \
              if 'PI1' in res.names else None
    if pi1_idx is not None:
        assert abs(abs(res.r_optimized[pi1_idx]) - 50.0) < 1e-9
    assert res.gap_after < res.gap_before + 1e-9   # ดีขึ้นหรือเท่าเดิม
```

### Test 4 (bonus) — Real data smoke test

```python
_DATA_DIR = Path(__file__).parent.parent / 'test_data'

@pytest.mark.skipif(
    not (_DATA_DIR / 'ramp01n01_SO.csv').exists(),
    reason='test data not present'
)
def test_real_data_gap_improves():
    """Gap after optimization should not exceed gap before (ramp01n01 data)."""
    import csv as _csv
    with open(_DATA_DIR / 'ramp01n01_SO.csv', newline='', encoding='utf-8') as f:
        pi_rows = list(_csv.reader(f))
    with open(_DATA_DIR / 'r01n01_so_crosscheck.csv', newline='', encoding='utf-8') as f:
        reader = _csv.DictReader(f)
        draw_pts = [{'name': r['Name'], 'sta': float(r['STA']),
                     'n': float(r['N']), 'e': float(r['E'])} for r in reader]

    res = fit_radius(pi_rows, draw_pts)

    assert res.n_points > 0
    assert res.gap_after <= res.gap_before + 1e-9
    # R ไม่ควรเปลี่ยนเกิน 1.0m เพราะ gap เริ่มต้นแค่ ~7.4mm
    for r_init, r_opt in zip(res.r_initial, res.r_optimized):
        assert abs(abs(r_opt) - abs(r_init)) < 1.0, \
            f'R changed too much: {r_init:.3f} → {r_opt:.3f}'
```

---

## 5. ตัวอย่าง Input/Output (real data)

**Input:** `test_data/ramp01n01_SO.csv` (PI table, 5 PI + 1 IP angle point)
- Free PIs: PI1(R=-150), PI2(R=150), PI3(R=100), PI4(R=-100), PI5(R=-500)  → 5 ตัว
- Angle point: IP1(R=0) → skip

**Drawing points:** `test_data/r01n01_so_crosscheck.csv` ({Name, STA, N, E})
- Exclude: rows ที่ Name ขึ้นต้น "PI" หรือ "HIP"
- Include: BP, PC, PT, TS, ST, SC, CS, EP, etc.

**Expected output:**
| field | value |
|-------|-------|
| names | ['PI1', 'PI2', 'PI3', 'PI4', 'PI5'] |
| gap_before | ~0.0074 m (7.4mm) |
| gap_after | ≤ gap_before |
| R changes | ≤ 1.0m each |
| converged | True |

---

## 6. ความเสี่ยงและข้อควรระวัง

| ความเสี่ยง | มาตรการป้องกัน |
|-----------|--------------|
| scipy ไม่ได้ติดตั้ง | wrap import ใน try/except; raise ImportError ชัดเจน |
| R optimized ≤ 0 | bounds=(1.0, None) ทุก R |
| R flip sign | เก็บ sign แยก, optimize abs(R) เท่านั้น |
| build มี issues | penalty = 1e6 per issue |
| station outside alignment | penalty = 1e6 per point |
| Nelder-Mead ไม่ converge | max_iter=10000 คุ้มครอง; converged=False report ให้ user |

---

## 7. Verification Steps

```bash
# 1. Install scipy
pip install "surveyor-micro-toolkit[optimize]"

# 2. Run all tests (เดิม 387 ยังผ่าน + test_optimizer ใหม่ผ่านด้วย)
pytest tests/test_optimizer.py -v
pytest -q

# 3. Smoke test with real data
python -c "
import csv
from smt.optimizer import fit_radius
with open('test_data/ramp01n01_SO.csv') as f:
    pi_rows = list(csv.reader(f))
with open('test_data/r01n01_so_crosscheck.csv') as f:
    import csv as c; r = list(c.DictReader(f))
    pts = [{'name': x['Name'], 'sta': float(x['STA']), 'n': float(x['N']), 'e': float(x['E'])} for x in r]
res = fit_radius(pi_rows, pts)
print(f'gap_before={res.gap_before*1000:.2f}mm gap_after={res.gap_after*1000:.2f}mm')
print(f'R changes: {[round(abs(o)-abs(i),4) for i,o in zip(res.r_initial, res.r_optimized)]}')
print(f'converged={res.converged} iters={res.iterations}')
"

# 4. mypy / ruff
mypy src/smt/optimizer.py
ruff check src/smt/optimizer.py
```

---

## 8. ไฟล์ที่แก้

| ไฟล์ | การเปลี่ยนแปลง |
|------|-------------|
| `src/smt/optimizer.py` | ใหม่ทั้งไฟล์ (~130 บรรทัด) |
| `tests/test_optimizer.py` | ใหม่ทั้งไฟล์ (~120 บรรทัด) |
| `pyproject.toml` | เพิ่ม 1 บรรทัด ใน [project.optional-dependencies] |

**ไฟล์ที่ต้องใช้ (import แต่ไม่แก้):**
- `src/smt/builders/alignment_builder.py` — `parse_pi_table`, `build_alignment_from_pi`
- `src/smt/alignment.py` — `calculate_station_to_coordinate`

---

*แผนบันทึกแล้วที่ session_logs/plan_optimizer_20260629_1828.md*
*กรุณา upload ไฟล์นี้ให้ Claude (แชท) ตรวจก่อนกดทางเลือก*
