# Phase 1 — COSINE arc-length inversion core-engine fix (plan only, not executed)

## Context

`session_logs/investigate_cosine_totaly_theta_export.md` (2026-07-07) proved that
`theta`/`totalY`/`tanShort` for the COSINE (Civil 3D Sine Half-Wave) transition are wrong
at the element's true end (`d=length`) because `_sine_halfwave_point` assumes
`a = x/X` — i.e. it treats the *arc distance* `d` as if it were the *tangent-projected*
coordinate `x`. This is only exact at `x=X` (`a=1`); at `d=length` it costs
0.00178°–0.01029° across the two Civil 3D ground truths we have. This is a **core-engine**
bug (not export-only) because `theta`/exit-azimuth is what the whole element chain uses to
place the next element — patching only `landxml.py` would make files self-inconsistent
(see that report §4).

`session_logs/investigate_cosine_arclength_inversion.md` (2026-07-11) validated the fix:
invert the true arc-length integral `s(a) = ∫₀ᵃ X·√(1+(dy/dx)²) da'` via Simpson quadrature
+ bisection instead of assuming `a=d/X`. This closes the error to 2.27e-06°–4.23e-05°
(≈500–2000× better) at the three ground truths we can check (R=900/L=100, R=250/L=50,
R=500/L=70), even though `s(1) ≠ length` exactly (a genuine small imperfection in
Autodesk's own closed-form `X`, residual 0.036mm/0.187mm, does not shrink with more Simpson
intervals — confirmed not a quadrature-error artifact).

**Policy decision (already agreed, stated here for the record):** when `d` is
(numerically) at the element's own end, i.e. `abs(d - length) < 1e-9`, short-circuit to the
existing exact closed form with `a=1` directly (`theta = atan(X/2R)`,
`y = 0.14867881635766·X²/R`) rather than bisecting — this is provably exact to float64
precision and avoids paying for/depending on bisection convergence at the one point that
already has a clean closed form. For `d < length`, solve `s(a)=d` via cached-table bracket +
bisection.

This plan covers **only** `src/smt/alignment.py` (the point-on-element engine) and its
tests. It explicitly does **not** touch `tests/golden/tables.json`, `reference/tables.json`,
`landxml.py`, or the VBA modules — those are separate phases, noted below.

## Current code (verified against the real file just now)

`src/smt/alignment.py`:
- `_sine_halfwave_point(x, big_x, r)` (lines 135–152): computes `a = x/big_x` then the
  existing `y`/`theta` closed forms, and **returns the input `x` unchanged** as the local
  tangent-projected coordinate (`return x, y, theta`).
- `calculate_point_on_element` (lines 292–312), two call sites:
  - SPIN branch (line 297): `_sine_halfwave_point(d, big_x, r)` — `x=d` (arc distance).
  - SPOUT branch (lines 301–302): `_sine_halfwave_point(length, big_x, r)` for the element's
    own end, and `_sine_halfwave_point(length - d, big_x, r)` for the mirrored point.
- No `functools` import yet in this file; `SPIRAL_STEPS = 48` is the existing module-level
  Simpson-interval constant (reused by the CLOTHOID/BLOSS/SINE Simpson integration below in
  the same function) — Phase 1 reuses it for the new COSINE arc-length table for consistency,
  not a new magic number.

## Diff design

Add three new private helpers just above `_sine_halfwave_point`, then change its signature
and the two call sites.

```python
from functools import lru_cache   # new import, top of file with math/dataclasses/typing

def _cosine_dydx(a: float, big_x: float, r: float) -> float:
    """dy/dx at normalised parameter a for the COSINE shape — same expression as the
    argument of atan() in the theta closed form (tan(theta) = dy/dx), extracted so the
    arc-length integrand (_cosine_arc_length) and theta formula share one definition.
    """
    return big_x / r * (a / 2 - math.sin(math.pi * a) / (2 * math.pi))


def _cosine_arc_length(a: float, big_x: float, r: float, n_seg: int = SPIRAL_STEPS) -> float:
    """s(a) = integral 0..a of X*sqrt(1+(dy/dx)^2) da', via Simpson quadrature.
    True physical arc length from the zero-curvature end to normalised parameter a.
    Sign of r does not matter (dy/dx is squared) -- caller may pass abs(r).
    """
    h = a / n_seg
    total = 0.0
    for i in range(n_seg + 1):
        ai = i * h
        integrand = big_x * math.hypot(1.0, _cosine_dydx(ai, big_x, r))
        w = 1 if (i == 0 or i == n_seg) else (4 if i % 2 == 1 else 2)
        total += w * integrand
    return total * h / 3.0


@lru_cache(maxsize=256)
def _cosine_arc_length_table(length: float, r_abs: float) -> tuple[float, ...]:
    """Cached s(a_i) at a_i = i/SPIRAL_STEPS, i=0..SPIRAL_STEPS, for one (length, |R|)
    pair. Shared by SPIN and SPOUT of equal length and |R| (mirror symmetry — see module
    docstring), so a compound alignment with both only builds the table once. Used to
    bracket the root of s(a)=d before bisection refinement in _cosine_solve_a.
    """
    big_x = calculate_sine_halfwave_tangent_length(length, r_abs)
    n = SPIRAL_STEPS
    return tuple(_cosine_arc_length(i / n, big_x, r_abs) for i in range(n + 1))


def _cosine_solve_a(d: float, big_x: float, r: float, length: float) -> float:
    """Solve s(a) = d for normalised parameter a: cached-table bracket + bisection
    (same 50-iteration bisection style as calculate_projection_to_element below).
    d must satisfy 0 <= d < length (the d==length case is short-circuited by the caller).
    """
    r_abs = abs(r)
    table = _cosine_arc_length_table(length, r_abs)
    n = SPIRAL_STEPS
    i = 0
    while i < n and table[i + 1] < d:
        i += 1
    # When d lies in (s(1), length) -- i.e. beyond the table's own last entry -- no a<=1
    # solves s(a)=d exactly, because s(1) != length exactly (a genuine small imperfection
    # in Autodesk's closed-form X, not a quadrature artifact -- see
    # session_logs/investigate_cosine_arclength_inversion.md section 3). In that case the
    # while loop above runs to i=n, giving lo=hi=1.0: the bracket is degenerate but the
    # bisection loop below is still safe (mid=1.0 every iteration, converges trivially) --
    # this deliberately clamps to a=1.0, the closest reachable value, instead of raising.
    lo, hi = i / n, min(i + 1, n) / n
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if _cosine_arc_length(mid, big_x, r_abs) < d:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _sine_halfwave_point(d: float, big_x: float, r: float, length: float) -> tuple[float, float, float]:
    """COSINE transition shape, canonical (SPIN) form.

    d      : TRUE arc distance from the zero-curvature end (no longer an x~=s
             approximation -- see _cosine_solve_a).
    big_x  : X, the closed-form tangent-projected length at d=length.
    r      : signed radius at the curved end.
    length : element arc length L; used for the d==length exact shortcut and to key the
             cached arc-length table.
    Returns (x, y, theta): the TRUE tangent-projected x=a*X (previously this returned the
    input d unchanged -- an approximation -- see module docstring update below), local
    offset y, and tangent angle theta, all at arc distance d.
    """
    if abs(d - length) < 1e-9:
        a = 1.0
    else:
        a = _cosine_solve_a(d, big_x, r, length)
    y = big_x ** 2 / r * (a ** 2 / 4 - (1 - math.cos(math.pi * a)) / (2 * math.pi ** 2))
    theta = math.atan(_cosine_dydx(a, big_x, r))
    x = a * big_x
    return x, y, theta
```

Call sites in `calculate_point_on_element` (lines 292–312) gain the new `length` argument:

```python
if el.k_in == 0:   # SPIN
    ...
    x_local, y_local, theta_local = _sine_halfwave_point(d, big_x, r, length)
else:              # SPOUT
    ...
    x_end, y_end, theta_total = _sine_halfwave_point(length, big_x, r, length)
    x_g, y_g, theta_g = _sine_halfwave_point(length - d, big_x, r, length)
    ...  # rest of SPOUT mirror math unchanged
```

**Important correctness note not previously called out in the investigation reports:**
`_sine_halfwave_point` no longer returns the input `d` as `x` — it returns the true
`x = a*X`. This means the fix changes the (N,E) position at **every interior point**
of a COSINE element, not only theta/Y at the endpoint — this is in fact the whole point
of closing known-limitation (1) in the module docstring ("no interior point (d<L) is
independently verified at all"), but it means position-based assertions at any `d`
(not just `d=length`) will change too, and must be accounted for below.

`_sine_halfwave_point`'s signature is private (leading underscore) and per grep only
called from within `alignment.py` itself (the two `calculate_point_on_element` sites) —
safe to change without a compatibility shim.

Module docstring (lines 16–53) needs updating to describe the new arc-length-inversion
method and retire known-limitation (1) (x≈s approximation) and the "no interior point
verified" caveat in (2), replacing them with the new residual described in the
investigation report (s(1)≠L by 0.036mm/0.187mm, not eliminated by more Simpson
intervals) and a note that `landxml.py`'s totalY/tanShort will still be wrong until
Phase 2 (export layer) picks up the corrected engine — `_spiral_geometry` currently
overrides only `totalX`, not `totalY`/`tanShort` (docstring at `landxml.py:94-102`).

## New/changed tests (`tests/test_alignment.py`)

### Existing tests that must be REWRITTEN, not just left alone

`test_cosine_closed_form_endpoint_r900_l100` and `_r250_l50` (lines 427–443) currently
evaluate `_cosine_local_turn_and_offset(el, d=big_x)` — i.e. **at `d=X`, not `d=length`**.
That was a deliberate workaround (see their own docstring, lines 410–415) to get an exact
check under the *old* x≈s approximation, since evaluating at the true end (`d=length`) was
known-wrong. Under the Phase 1 fix, `d=big_x` is an ordinary interior point (`big_x < length`
always) and will bisect to some `a` noticeably less than 1 (since `s(1) ≈ length`, not
`big_x`) — these two tests' asserted numbers will no longer hold, **and are no longer
testing the right thing** (the workaround is obsolete now that `d=length` is exact).
**Plan: replace both with the new "Group 1" tests below, which assert at the true
`d=length`.** Confirmed via ground-truth computation just now that current values at
`d=big_x` (3.178942026888°, 1.651062316115) differ from what `d=length` will produce.

### Group 1 — exact endpoint match (3 ground truths, floating-point precision)

```python
@pytest.mark.parametrize('r,length,theta_exact_deg,y_exact', [
    (900.0, 100.0, 3.1789420268894153, 1.6510623161163274),
    (250.0,  50.0, 5.705449190907088,  1.4840930725353705),
    (500.0,  70.0, 4.002399624673551,  1.4557579182062208),
])
def test_cosine_endpoint_matches_a1_closed_form(r, length, theta_exact_deg, y_exact):
    el = al.make_element('SPIN', 0, length, 0.0, 0.0, 90.0, r, None, 'COSINE')
    turn_deg, local_y = _cosine_local_turn_and_offset(el, length)
    assert math.isclose(turn_deg, theta_exact_deg, abs_tol=1e-9)
    assert math.isclose(local_y, y_exact, abs_tol=1e-9)
```
(third row's `theta_exact_deg`/`y_exact` computed just now with the same closed form as the
first two, for R=500/L=70 — not yet in any doc; will cite this plan as source.)

### Group 2 — self-consistency at an interior point (d < length)

```python
@pytest.mark.parametrize('r,length,d', [(900.0, 100.0, 40.0), (250.0, 50.0, 20.0), (500.0, 70.0, 55.0)])
def test_cosine_arc_length_inversion_self_consistent(r, length, d):
    big_x = al.calculate_sine_halfwave_tangent_length(length, r)
    a = al._cosine_solve_a(d, big_x, r, length)
    s_check = al._cosine_arc_length(a, big_x, r)
    assert math.isclose(s_check, d, abs_tol=1e-6)
```

### Group 3 — cache sharing between SPIN and SPOUT of equal length/|R|

```python
def test_cosine_arc_length_table_cached_across_spin_spout():
    al._cosine_arc_length_table.cache_clear()
    spin = al.make_element('SPIN', 0, 70.0, 0.0, 0.0, 90.0, 500.0, None, 'COSINE')
    spout = al.make_element('SPOUT', 0, 70.0, 0.0, 0.0, 90.0, 500.0, None, 'COSINE')
    al.calculate_point_on_element(spin, 55.0)
    al.calculate_point_on_element(spout, 55.0)
    info = al._cosine_arc_length_table.cache_info()
    assert info.currsize == 1   # one table built, reused for both
```

### Group 5 — graceful clamp to a=1.0 when d falls in the (s(1), length) gap

`s(1) != length` exactly (proven in the investigation report, not a quadrature artifact —
residuals 3.578673e-05m / 1.873914e-04m / 6.309920e-05m at the three ground truths, stable
from 48 to 48,000 Simpson intervals). Any `d` strictly between `s(1)` and `length` has no
`a<=1` solving `s(a)=d`; `_cosine_solve_a` must clamp to `a=1.0` rather than error. Verified
just now by simulating the exact bracket+bisection algorithm above against the real
`calculate_sine_halfwave_tangent_length`: the bracket search runs `i` to `n` (=48), giving
`lo=hi=1.0`, and the bisection loop converges trivially to `1.0` — confirmed graceful for
all three ground truths, both at the gap midpoint and near its edge:

| R | L | s(1) | gap = L−s(1) | d = L − gap/2 | a returned |
|---|---|---|---|---|---|
| 900 | 100 | 99.9999642132682 | 3.578673180015812e-05 | 99.99998210663409 | 1.0 |
| 250 | 50  | 49.99981260855977 | 1.8739144022816845e-04 | 49.99990630427989 | 1.0 |
| 500 | 70  | 69.99993690080412 | 6.309919588431967e-05 | 69.99996845040206 | 1.0 |

```python
@pytest.mark.parametrize('r,length', [(900.0, 100.0), (250.0, 50.0), (500.0, 70.0)])
def test_cosine_solve_a_clamps_gracefully_in_s1_length_gap(r, length):
    big_x = al.calculate_sine_halfwave_tangent_length(length, r)
    s1 = al._cosine_arc_length(1.0, big_x, r)
    gap = length - s1
    assert gap > 0   # sanity: confirms this test actually exercises the gap
    d_mid = length - gap / 2.0
    a = al._cosine_solve_a(d_mid, big_x, r, length)
    assert a == 1.0
```
(table above computed just now with the real `calculate_sine_halfwave_tangent_length` and
a faithful simulation of the bracket+bisection algorithm above — not a projection.)

### Group 4 — CLOTHOID/BLOSS/SINE unaffected (real numbers, computed now against current
main, to be re-run after the diff and confirmed byte-for-byte unchanged)

```python
@pytest.mark.parametrize('trans,r,length,d,exp_n,exp_e,exp_az', [
    ('CLOTHOID', 400.0, 60.0, 0.0,  0.0,                 0.0,                 1.5707963267948966),
    ('CLOTHOID', 400.0, 60.0, 15.0, -0.02343746321541169, 14.999967041045013, 1.5754838267948967),
    ('CLOTHOID', 400.0, 60.0, 30.0, -0.18749529162218986, 29.9989453295336,   1.5895463267948964),
    ('CLOTHOID', 400.0, 60.0, 45.0, -0.6327320566067619,  44.99199162569003,  1.6129838267948964),
    ('CLOTHOID', 400.0, 60.0, 60.0, -1.499397428754978,   59.96625878371091,  1.6457963267948967),
    ('BLOSS',    400.0, 60.0, 0.0,  0.0,                 0.0,                 1.5707963267948966),
    ('BLOSS',    400.0, 60.0, 15.0, -0.00791015389733473, 14.99999533039958,  1.572847108044897),
    ('BLOSS',    400.0, 60.0, 30.0, -0.11249847240800069, 29.999539624480274, 1.5848588267948962),
    ('BLOSS',    400.0, 60.0, 45.0, -0.4982850314579719,  44.994167949146686, 1.6103471080448966),
    ('BLOSS',    400.0, 60.0, 60.0, -1.3494424055276184,  59.96920464868514,  1.6457963267948967),
    ('SINE',     500.0, 70.0, 0.0,  0.0,                 0.0,                 1.5707963267948966),
    ('SINE',     500.0, 70.0, 17.5, -0.0029697381528134234, 17.499999311860066, 1.5716250853674145),
    ('SINE',     500.0, 70.0, 35.0, -0.08004763795198576, 34.999762188679995, 1.5812038439399334),
    ('SINE',     500.0, 70.0, 52.5, -0.4633347068139018,  52.49508457246585,  1.6066250853674147),
    ('SINE',     500.0, 70.0, 70.0, -1.38458305097449,    69.96995876779974,  1.6407963267948968),
])
def test_non_cosine_transitions_unaffected_by_cosine_fix(trans, r, length, d, exp_n, exp_e, exp_az):
    el = al.make_element('SPIN', 0, length, 0.0, 0.0, 90.0, r, None, trans)
    st = al.calculate_point_on_element(el, d)
    assert math.isclose(st.n, exp_n, abs_tol=1e-9)
    assert math.isclose(st.e, exp_e, abs_tol=1e-9)
    assert math.isclose(st.azimuth, exp_az, abs_tol=1e-12)
```
(all 15 numbers above were just computed against the current, unmodified engine — this
table is the actual baseline, not a placeholder.)

## Impact on existing tests — verified by actually running the diff, not predicted

Earlier drafts of this section predicted impact by reasoning about the code; that
prediction has since been **superseded by an actual run of the diff** (methodology: a
full scratch copy of `src/` + `tests/`, with `alignment.py` replaced by the diff above,
executed via `PYTHONPATH` forced to the scratch copy's `src/` and sanity-checked via
`al.__file__` before trusting any result — an earlier attempt using `cd scratch_copy &&
pytest` silently ran the *original* unmodified package instead, because `smt` is
editable-installed and resolves independent of cwd; that false-negative run is discarded).

Verified command: `PYTHONPATH=<scratch>/src python -m pytest -q` → **11 failed, 455
passed, 1 skipped** (baseline before the diff: 466 passed, 1 skipped, 0 failed).

**Single root cause for 8 of the 11 failures:** a **31.110mm position gap** at the
SPIN(COSINE, R=500/L=70) exit -> next element junction (golden element index 11->12,
control point `SC@2249.25`). Independently verified: `L - X` at R=500/L=70 =
`70 - 69.9688982078716` = `0.031102m` = **31.102mm**, matching the observed 31.110mm gap
to within 0.009mm (the small residual is expected — the exit azimuth shifts slightly too,
so the offset isn't a pure L-X translation). This is **exactly** the behaviour flagged
in this plan's own "Important correctness note" above (`_sine_halfwave_point` now
returns the true `x=a*X` instead of echoing the input `d` back unchanged) — not a new
defect. `alignment_builder.py`'s PI-reconstruction still places the next element using
the old approximation, so it now disagrees with the newly-correct `calculate_exit_state`
by the full `L-X` gap. This is precisely the cascading golden-fixture mismatch
anticipated in the "Explicit non-goals" section (non-goal #1) — expected to persist
until Phase 3 regenerates `tests/golden/tables.json` / `reference/tables.json` and
reconciles the builder.

**The 11 verified failures:**
- `tests/test_alignment.py::test_cosine_closed_form_endpoint_r900_l100` — obsolete, tests
  at `d=big_x` not `d=length` (see "Existing tests that must be REWRITTEN" above).
- `tests/test_alignment.py::test_cosine_closed_form_endpoint_r250_l50` — obsolete, same reason.
- `tests/test_alignment.py::test_chain_has_no_gaps` — 31.110mm junction gap at 11->12,
  the L-X shift above.
- `tests/test_alignment.py::test_exit_state_matches_next_entry` — same junction, same cause.
- `tests/test_alignment.py::test_control_points` — same cause (SC control point).
- `tests/test_alignment.py::test_control_point_parametrized[SC@2249.25]` — same.
- `tests/builders/test_alignment_builder.py::TestGoldenElementGeometry::test_element_ne_within_tolerance` — same.
- `tests/builders/test_alignment_builder.py::TestGoldenElementGeometry::test_element_stations_within_tolerance` —
  station accumulates the same shift (`sta_end` off by ~0.062m at element[12], roughly 2x
  L-X, consistent with the shift propagating through both ends of the curve group).
- `tests/builders/test_alignment_builder.py::TestGoldenControlPoints::test_control_ne_within_1mm` — same.
- `tests/builders/test_alignment_builder.py::TestCheckAgainstDrawing::test_all_controls_pass_1mm_tolerance` — same.
- `tests/test_check.py::test_check_horizontal_all_pass` — same (`SC@2249.25 gap=0.031110m` > 2mm tol).

**Correction to this plan's own earlier prediction:** `test_element_azimuth_within_tolerance`
was predicted above ("Existing tests that must be REWRITTEN" era of this plan) to fail
because its passing margin was "only 17% under tolerance" — **it actually still passes**.
The fix does not push the R=500/L=70 azimuth error past the 1e-4 rad tolerance at this
R/L. The real, verified breakage is entirely in position (N/E) and accumulated station,
not azimuth — a single-root-cause (L-X translation) story, simpler than the originally
guessed "cascades through every downstream element via azimuth drift."

**Confirmed still passing, as predicted:**
- `test_cosine_spin_spout_symmetry_matches_civil3d` (all 3 parametrizations).
- `test_cosine_total_x_uses_closed_form_not_arc_length`, `test_cosine_spin_spout_total_x_match`
  (tests/test_landxml.py) — `_spiral_geometry`'s totalX override is unaffected.
- `test_element_azimuth_within_tolerance` (see correction above).
- `test_element_curvature_correct` (k_in/k_out only, unaffected as expected).

## Explicit non-goals for Phase 1 (confirmed, not touched)

1. `tests/golden/tables.json` / `reference/tables.json` — **not regenerated in this phase.**
   The cascading test failures in `test_alignment_builder.py` described above are the
   expected, temporary state until Phase 3 regenerates the fixtures — this is not a new bug
   to chase down, and this phase must not be committed while masking that fact.
2. `landxml.py` (`_spiral_geometry`'s `totalY`/`tanShort` still use the `d=length`
   approximation this phase fixes structurally, but the export layer itself isn't touched
   here) — Phase 2.
3. `SMT_Core.bas`/`SMT_Alignment.bas` VBA mirror — must be updated in the same round per
   CLAUDE.md §4.3, but scheduled for whichever phase actually lands in `main` (this plan's
   author defers to the user on whether Phase 1+3 land as one commit or two, per the
   open question already on record in the investigation report).
4. This plan file itself is step (a) of the project's Plan-Review-Approve rule — it must
   be uploaded to Claude (chat) for a second review before `src/smt/alignment.py` is
   touched. No code has been changed as part of producing this plan.

## Verification (once approved and implemented)

1. `pytest tests/test_alignment.py -k cosine -v` — Groups 1–4 above all green.
2. `pytest tests/test_alignment.py tests/test_landxml.py -v` — confirm the two
   `test_cosine_total_x_*` tests and `test_cosine_spin_spout_symmetry_matches_civil3d`
   still pass.
3. `pytest tests/builders/test_alignment_builder.py -k Golden -v` — capture and report
   which assertions now fail (expected, per non-goal #1), do not attempt to fix them here.
4. Full `pytest -q` run — report the before/after pass count delta so the user sees the
   exact blast radius before deciding whether to proceed to Phase 3 in the same sitting.
