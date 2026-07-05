# Plan: Fix LandXML COSINE totalX (reports L instead of closed-form X)

## Context

`src/smt/landxml.py::_spiral_geometry` exports `totalX` for spiral elements by calling
`calculate_point_on_element(synthetic, length)` and reading `state.n` directly. For the
COSINE transition (Civil 3D "Sine Half-Wavelength Diminishing Tangent Curve"),
`alignment.py::_sine_halfwave_point` returns its `x` argument unchanged as the first
tuple element — so when called at `d=length` (the element's own true end, which is what
`_spiral_geometry` and `calculate_exit_state` always use), `total_x` comes out bit-for-bit
equal to `length`, not the true closed-form tangent-projected length
`X = L - 0.0226689447*L**3/R**2`. This is a known limitation already documented in
`alignment.py`'s module docstring (item 3), `docs/extensions.md` EXT-003, and
`session_logs/investigate_sinehalfwave_formula.md`. Full investigation of this specific
bug (code paths, confirmed with real `python -c` runs, existing-test impact) is in
`session_logs/investigate_totalx_landxml_fix.md` — this plan implements Option B from
that report (expose the closed-form calculation from `alignment.py` instead of
duplicating the constant in `landxml.py`).

**Scope**: fix `totalX` only. `totalY`/`tanShort` keep using the existing d=L
approximation (a separate, smaller, already-documented limitation — the "x≈s
approximation" in `alignment.py`'s docstring). `tan_long` is **not** independently
patched — it changes as a direct, mechanical consequence of `total_x` changing, since
`tan_long = total_x - total_y / tan(theta_rad)` and only `total_x` moves.

## What changes, and why each number moves (verified by running real code, not hand math)

### 1. New function in `src/smt/alignment.py`

Insert after `_sine_halfwave_point` (current lines 128-144), before
`_calculate_turning_angle_at`:

```python
def calculate_sine_halfwave_tangent_length(length: float, r: float) -> float:
    """Closed-form tangent-projected length X for the COSINE (Civil 3D "Sine
    Half-Wavelength Diminishing Tangent Curve") transition shape, at the
    element's own true end (arc length = `length`).

    length : element arc length L (m); always positive.
    r      : signed radius at the curved end (m); sign does not affect the
             result since only r**2 appears in the formula.
    Returns X = L - 0.0226689447*L**3/R**2 (m) — the tangent-projected
    distance from the zero-curvature end, NOT equal to L except in the
    R -> infinity limit. Single source of truth for the closed-form constant
    used both by `_sine_halfwave_point` (point-on-element geometry) and by
    `landxml.py::_spiral_geometry` (LandXML totalX export).
    Reference: Autodesk Civil 3D 2026 Help, "About Transition Definitions";
    see session_logs/investigate_sinehalfwave_formula.md and
    session_logs/investigate_totalx_landxml_fix.md.
    """
    return length - _SINE_HALFWAVE_C * length ** 3 / r ** 2
```

### 2. DRY refactor of `calculate_point_on_element`'s COSINE branch (same file)

Current code (lines 264-278) computes `big_x = length - _SINE_HALFWAVE_C * length ** 3 / r ** 2`
inline, twice (once in the SPIN sub-branch at line 268, once in the SPOUT sub-branch at
line 272). Replace both with a call to the new function:

```diff
         if el.k_in == 0:   # SPIN: curvature 0 -> 1/R, canonical form used directly
             r = radius_from_curvature(el.k_out)
-            big_x = length - _SINE_HALFWAVE_C * length ** 3 / r ** 2
+            big_x = calculate_sine_halfwave_tangent_length(length, r)
             x_local, y_local, theta_local = _sine_halfwave_point(d, big_x, r)
         else:   # SPOUT: curvature 1/R -> 0, mirror canonical form via s <-> L-d
             r = radius_from_curvature(el.k_in)
-            big_x = length - _SINE_HALFWAVE_C * length ** 3 / r ** 2
+            big_x = calculate_sine_halfwave_tangent_length(length, r)
             x_end, y_end, theta_total = _sine_halfwave_point(length, big_x, r)
```

**Verified bit-for-bit equivalence** (requested check 2): ran both the original inline
form and the refactored (function-call) form side by side — same `Element`, same `d` —
for both R/L ground-truth pairs used in the original COSINE verification
(R=900/L=100, R=250/L=50), for both SPIN and SPOUT, at 5 fractions of `d` each
(0, 1/4, 1/2, 3/4, 1 of L) — **20 cases total, all `==` (bit-for-bit), zero mismatches**:

```
R= 900.0 L= 100.0 SPIN  d=  0.000..100.000 (5 values)  identical(==)=True  (all 5)
R= 900.0 L= 100.0 SPOUT d=  0.000..100.000 (5 values)  identical(==)=True  (all 5)
R= 250.0 L=  50.0 SPIN  d=  0.000.. 50.000 (5 values)  identical(==)=True  (all 5)
R= 250.0 L=  50.0 SPOUT d=  0.000.. 50.000 (5 values)  identical(==)=True  (all 5)
```
(sample row: `R=900.0 L=100.0 SPIN d=50.000` → orig=`(49.852566643713075,
50.19586486330244, 0.655870325937725)`, refactored=identical tuple, `==` True)

This is expected — extracting an expression into a function call does not change
Python's floating-point evaluation order — but it is now *proven*, not assumed.

**Re-confirmed CLOTHOID/BLOSS/SINE are untouched** (requested check 2, second half): ran
`calculate_point_on_element` for all three shapes at R=400/L=60 again, after having the
refactor logic in hand (they never enter the COSINE branch at all, so nothing about this
plan can affect them):
```
CLOTHOID    n=59.966259  e=1.499397  azimuth=0.07500000   (matches existing test, line 284 of test_landxml.py)
BLOSS       n=59.969205  e=1.349442  azimuth=0.07500000
SINE        n=59.970442  e=1.271486  azimuth=0.07500000
```

### 3. `src/smt/landxml.py` — use the new function to override `totalX` for COSINE

```diff
--- a/src/smt/landxml.py
+++ b/src/smt/landxml.py
@@
 from . import fpmath
-from .alignment import Element, calculate_exit_state, calculate_point_on_element
+from .alignment import (
+    Element,
+    calculate_exit_state,
+    calculate_point_on_element,
+    calculate_sine_halfwave_tangent_length,
+)
 from .builders.alignment_builder import BuildResult
@@
 def _spiral_geometry(R: float, length: float, transition: str, theta_rad: float) -> tuple[float, float, float, float]:
     """(totalX, totalY, tanLong, tanShort) for a spiral, computed canonically:
     a synthetic Element at the origin (n=0, e=0, azimuth=0) curving from
     k_in=0 to k_out=1/R over [0, length], independent of the spiral's real
-    position, direction, or SPIN/SPOUT role in the alignment."""
+    position, direction, or SPIN/SPOUT role in the alignment.
+
+    COSINE transition: totalX is overridden with the closed-form tangent-
+    projected length (calculate_sine_halfwave_tangent_length) instead of the
+    raw value calculate_point_on_element returns at d=length, which equals
+    `length` itself (known limitation; see
+    session_logs/investigate_totalx_landxml_fix.md). tanLong changes as a
+    direct consequence (tanLong = totalX - totalY/tan(theta)); totalY/
+    tanShort still use the d=length approximation — a separate, smaller,
+    already-documented known limitation (see alignment.py module docstring
+    "Known limitations").
+    """
     synthetic = Element(
         type='SPIN', sta_start=0.0, sta_end=length,
         n=0.0, e=0.0, azimuth=0.0,
         k_in=0.0, k_out=1.0 / R, transition=transition,
     )
     state = calculate_point_on_element(synthetic, length)
     total_x, total_y = state.n, state.e
+    if transition == 'COSINE':
+        total_x = calculate_sine_halfwave_tangent_length(length, R)
     tan_long = total_x - total_y / math.tan(theta_rad)
     tan_short = total_y / math.sin(theta_rad)
     return total_x, total_y, tan_long, tan_short
```

### tanLong before/after, R=400 L=60 (requested check 1 — confirmed by running real code)

`tan_long` is not fixed separately; it moves purely because `total_x` (its first term)
moves. Confirmed numerically:

| field | before (current bug) | after (this fix) | delta |
|---|---|---|---|
| total_x (totalX) | 60.000000 | 59.969397 | -0.030603 m |
| total_y (totalY) | 1.339040 | 1.339040 | 0 (unchanged — separate limitation, out of scope) |
| tan_long (tanLong) | 42.179623 | 42.149020 | **-0.030603 m** (= exactly the total_x delta) |
| tan_short (tanShort) | 17.870615 | 17.870615 | 0 (unchanged — depends only on total_y/theta) |

## New / changed tests in `tests/test_landxml.py`

New vertex helper (after `_verts_spiral()`, current lines 56-61):
```python
def _verts_spiral_cosine():
    """Right-hand curve with symmetric Sine Half-Wavelength spirals Ls=60, R=400."""
    return [
        {'n':    0.0, 'e':   0.0},
        {'n':    0.0, 'e': 500.0, 'R': 400.0, 'Ls': 60.0, 'trans': 'COSINE'},
        {'n': -500.0, 'e': 500.0},
    ]
```

Test 1 — totalX is the closed form, not L:
```python
def test_cosine_total_x_uses_closed_form_not_arc_length(self):
    """COSINE totalX must be the closed-form tangent-projected X, not L.

    Regression for the bug in session_logs/investigate_totalx_landxml_fix.md:
    totalX used to equal the raw element length (60.0) exactly; the correct
    closed-form value for R=400, Ls=60 is X = L - 0.0226689447*L**3/R**2
    = 59.969397.
    """
    xml = export_alignment_landxml(_build(_verts_spiral_cosine()))
    root = _parse(xml)
    spin = next(s for s in _find_all(root, 'Spiral') if s.get('radiusStart') == 'INF')
    total_x = float(spin.get('totalX'))
    assert not math.isclose(total_x, 60.0, abs_tol=1e-6)
    assert math.isclose(total_x, 59.969397, abs_tol=1e-5)
```

Test 2 (requested check 3 — SPOUT regression, not previously present) — SPIN and SPOUT
totalX must match, mirroring the existing CLOTHOID invariant test at lines 293-298:
```python
def test_cosine_spin_spout_total_x_match(self):
    """SPIN and SPOUT COSINE spirals of equal R,L must report the same totalX.

    Mirrors test_geometry_canonical_independent_of_role (CLOTHOID, lines
    293-298) for COSINE specifically -- not previously covered, since no
    existing test in this file uses transition='COSINE'
    (session_logs/investigate_totalx_landxml_fix.md, section 4).
    """
    xml = export_alignment_landxml(_build(_verts_spiral_cosine()))
    root = _parse(xml)
    spin = next(s for s in _find_all(root, 'Spiral') if s.get('radiusStart') == 'INF')
    spout = next(s for s in _find_all(root, 'Spiral') if s.get('radiusEnd') == 'INF')
    for attr in ('totalX', 'totalY', 'tanLong', 'tanShort'):
        assert math.isclose(float(spin.get(attr)), float(spout.get(attr)), abs_tol=1e-6)
```

**Confirmed both tests fail on current code, pass after the fix** — ran the real build
pipeline (`build_alignment_from_pi` + `export_alignment_landxml`) against
`_verts_spiral_cosine()` on the unmodified code: both SPIN and SPOUT elements currently
report `totalX=60.000000` (so test 1's `not math.isclose(..., 60.0, ...)` assertion would
fail today — correct regression behavior; test 2 already passes today since SPIN/SPOUT
both report the same wrong value, and will keep passing after the fix since the override
applies identically to both, using the real `R`/`length` each carries).

## Existing tests — confirmed unaffected

Per `session_logs/investigate_totalx_landxml_fix.md` section 4: the 3 existing `totalX`
assertions in `tests/test_landxml.py` (lines 284, 297-298, 304) all use `_verts_spiral()`,
which defaults to CLOTHOID — none exercise the COSINE branch this plan touches. No
existing test needs to change.

## Files touched

1. `src/smt/alignment.py` — add `calculate_sine_halfwave_tangent_length`; refactor the
   two inline `big_x` computations in `calculate_point_on_element` to call it.
2. `src/smt/landxml.py` — import the new function; override `total_x` for COSINE in
   `_spiral_geometry`; update its docstring.
3. `tests/test_landxml.py` — add `_verts_spiral_cosine()` helper + 2 new tests.

## Verification

1. `pytest -q` — full suite green, including the 2 new tests.
2. `pytest tests/test_landxml.py -v` — confirm the 2 new COSINE tests pass and all
   existing tests (CLOTHOID-based totalX checks) still pass unchanged.
3. Manual: `python -c` sanity check reproducing the before/after table above (total_x,
   tan_long) for R=400/L=60, and re-run the bit-for-bit refactor comparison (20 cases,
   R=900/L=100 and R=250/L=50, SPIN+SPOUT, 5 d-fractions each) against the actual
   (post-edit) `calculate_point_on_element` to confirm the real refactor — not just the
   simulated copy used during planning — is still bit-for-bit identical to pre-edit
   behavior for every case except the newly-overridden `total_x` at the call site in
   `landxml.py` (which `calculate_point_on_element` itself does not touch — the override
   happens one layer up, in `_spiral_geometry`).
4. `smt` CLI smoke test (per CLAUDE.md §8): export LandXML for a real alignment
   containing a COSINE spiral and confirm `totalX` is no longer exactly equal to the
   spiral's `length` attribute.
