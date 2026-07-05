# Plan: Replace COSINE transition with Civil 3D Sine Half-Wave closed form (alignment.py)

## Context

`src/smt/alignment.py`'s `_shape_integral` implements COSINE as
`f(τ)=(1-cos πτ)/2` (a curvature-vs-arc-length shape, integrated via Simpson in
`calculate_point_on_element`). Per `session_logs/investigate_sinehalfwave_formula.md`,
this does NOT match Civil 3D's actual "Sine Half-Wavelength Diminishing Tangent Curve":
Civil 3D defines this curve via a closed-form y(x) where x is tangent-projected
distance, not arc length — a different mechanism entirely, verified against 2
independent Civil 3D ground-truth points (R=900/L=100 and R=250/L=50). BLOSS and SINE
were separately verified to already match Civil 3D exactly; only COSINE is wrong, by
~3 cm at R=900/L=100.

This plan replaces the COSINE branch in `calculate_point_on_element` with the verified
closed form, for both SPIN (k_in=0) and SPOUT (k_out=0), using one canonical function
plus an s↔(L−s) mirror for SPOUT — the same idea already used for CLOTHOID/BLOSS/SINE
(swap k_in/k_out roles through the same function, no separate SPOUT formula).

## Verified formula

Per element (R = whichever of R_in/R_out is finite/nonzero, L = sta_end−sta_start):

```
X        = L - 0.0226689447 * L**3 / R**2
a(x)     = x / X
y(x)     = X**2/R * (a**2/4 - (1-cos(pi*a))/(2*pi**2))
theta(x) = atan( X/R * (a/2 - sin(pi*a)/(2*pi)) )
```

**SPIN** (k_in=0, k_out=1/R): x = d (arc distance from element start, per the
documented x≈s approximation — see Known limits). Local point = `(d, y(d))`, tangent =
`theta(d)`. This is the canonical form, directly verified against both Civil 3D
ground-truth points (X, theta, totalY match to 5-6 significant figures).

**SPOUT** (k_in=1/R, k_out=0): mirror the canonical form via s→L−s. Let
`Θ = theta(L)` (canonical, evaluated with x≈s throughout, consistent with the SPIN
branch), `g(u) = (u, y(u))`. For arc distance d from the SPOUT's own start:

```
gx, gy   = g(L-d)
dx, dy   = g(L).x - gx, g(L).y - gy
local_x  = dx*cos(Θ) + dy*sin(Θ)
local_y  = dx*sin(Θ) - dy*cos(Θ)
theta(d) = Θ - theta(L-d)
```

Derived from requiring θ_SPOUT(d) = Θ − θ_SPIN(L−d) (the s↔L−s mirror pattern) and
integrating the unit tangent; satisfies local(0)=(0,0,0) and theta(L)=Θ by
construction (matches Civil 3D: SPIN and SPOUT of equal R,L give identical
theta/totalX/totalY/tanLong/tanShort — confirmed 2026-07-05 in the investigation doc
with real R=250/L=50 data from the now-lost `SMT_TEST_ALINGMENT2.xml`).

**Known limitation (document, do not try to fix in this pass):** only the SPIN
endpoint is independently verified against Civil 3D at more than one point (the two
ground-truth R/L pairs). The SPOUT *mid-curve* trace is derived purely from the
boundary-condition mirror above — no independent Civil 3D data confirms any SPOUT
interior point, only the endpoint invariant (Θ matches). This is the same category of
gap already flagged in `session_logs/investigate_sinehalfwave_formula.md` for
mid-curve points generally (line 30-31: x≈s approximation, unverified interior). Both
limitations must be stated together in the alignment.py docstring update (see below).

Both branches reduce to the already-verified endpoint quantities (X, θ=atan(X/2R),
totalY=0.14867881635766·X²/R) at d=L.

Compound-COSINE (neither k_in nor k_out is zero — a spiral between two curves of
different sign/radius) is out of scope, same as the existing "spiral + compound
combination unsupported" limitation; that case keeps using the old Simpson path
unchanged, to be revisited alongside the `multicurve.py` solver (Roadmap).

## Known-affected tests (found before touching anything — confirmed exact list, not estimated)

Old Simpson exit vs. new closed-form exit, R=500/L=70 (both COSINE elements in the
golden 30-element fixture):

| point | old (golden, = oracle) | new (closed form) | delta |
|---|---|---|---|
| SC (SPIN-COSINE exit, sta 2249.324) | N=18896.2981, E=11737.4091 | N=18896.281329, E=11737.435334 | 3.11 cm |
| ST (SPOUT-COSINE exit, sta 2554.756) | N=18661.5204, E=11925.8901 | N=18661.495288, E=11925.909767 | 3.19 cm |

`reference/tables.json` is byte-identical to `tests/golden/tables.json` (verified via
`diff`). Both shifts are far outside existing tolerances (1mm/5mm). **Exactly 10 test
functions** are affected (confirmed by reading each test body, not guessed):

`tests/test_alignment.py`:
1. `test_control_points` — blanket check over all 31 controls; fails at SC, ST.
2. `test_control_point_parametrized` — only the `SC@2249.324` and `ST@2554.756` param
   cases fail; the other 29 are independent per-point checks and are unaffected.
3. `test_chain_has_no_gaps` — blanket `check_chain`; fails at the SC and ST junctions.
4. `test_exit_state_matches_next_entry` — blanket loop; fails at the same 2 junctions
   (stops at the first one it hits).

`tests/test_check.py`:
5. `test_check_horizontal_all_pass` — same SC/ST control points, same reason.

`tests/builders/test_alignment_builder.py` (this file chains every built element's
position forward through `calculate_exit_state` —
`src/smt/builders/alignment_builder.py:154,390` — so the shift at the COSINE curve
group, `{'R':500,'Ls':70,'trans':'COSINE'}` at line 80, propagates to every element
and control point after it, roughly the back half of the alignment):
6. `test_element_ne_within_tolerance`
7. `test_element_azimuth_within_tolerance`
8. `test_control_ne_within_1mm`
9. `test_ep_ne_exact` (EP is the last control point — still inside the cascade)
10. `test_all_controls_pass_1mm_tolerance`

**Confirmed unaffected** (checked each, not assumed): `test_roundtrip_all_element_types`
/ `test_roundtrip_parametrized` (self-consistency only, no hardcoded numbers);
`tests/test_landxml.py::test_spiral_lx_type_mapping` (string mapping only);
`test_chain_is_continuous` in test_alignment_builder.py (checks the *built* chain
against itself, not against golden — stays self-consistent under any formula);
`test_element_types_match`, `test_spiral_trans_match`, `test_control_names_match`,
`test_element_curvature_correct`, `test_element_stations_within_tolerance`,
`test_bp_exact`, `test_report_length_matches_drawing` (count only, not values),
`test_report_has_required_keys`, `test_unnamed_entry_matches_nearest_station` (uses BP,
upstream of the change), and all of `TestNoCurvePI` / other hand-built-vertex tests
(don't touch the golden fixture at all).

## Decision: fix core now, xfail the 10 tests, regenerate fixture next (binding)

1. Implement the closed form in `alignment.py` now (this plan).
2. Mark all 10 confirmed-affected test functions above with
   `@pytest.mark.xfail(strict=True, reason=...)`, where every reason string cites BOTH
   `session_logs/plan_cosine_sinehalfwave_fix.md` (this plan) AND
   `session_logs/investigate_sinehalfwave_formula.md`, plus a one-line statement of
   which control points/elements are affected. For `test_control_point_parametrized`,
   only the SC and ST `pytest.param(...)` entries get `marks=pytest.mark.xfail(...)`
   (mixed with plain tuples for the other 29 — pytest supports this) so the other 29
   control points keep full regression coverage. `strict=True` so the marks force a
   failure (and tell us to remove them) once the fixture is regenerated.
3. **Binding commitment**: the very next plan after this one executes and is verified
   green (with the 10 xfails passing-as-expected-failures) is fixture regeneration —
   updating `tests/golden/tables.json` and `reference/tables.json` (identical) so SC,
   ST, and everything the builder cascades from them reflect the new closed-form
   output, then removing all 10 xfail marks. This is not an open-ended "someday" item;
   it is scheduled as the immediate follow-up plan.
4. **Before that follow-up plan is approved**, it must display the full raw JSON rows
   (every field, not a summary table) for the SPIN-COSINE and SPOUT-COSINE elements
   (R=500, L=70) in `tests/golden/tables.json`, plus the SC and ST control-point
   entries, so they can be reviewed as real file content before any JSON is rewritten
   (per CLAUDE.md's file-format review rule).

## Implementation steps

1. Copy this plan's final content to `session_logs/plan_cosine_sinehalfwave_fix.md`
   (durable, in-repo path — the xfail comments below reference this path, not the
   ephemeral `~/.claude/plans/...` file used during plan-mode drafting).
2. In `src/smt/alignment.py`:
   - Add module-level constant `_SINE_HALFWAVE_C = 0.0226689447` near `SPIRAL_STEPS`.
   - Add a small helper `_sine_halfwave_point(x: float, X: float, R: float) -> tuple[float, float, float]`
     returning `(x, y(x), theta(x))` per the formula above (docstring: what/units/sign
     convention/reference, per CLAUDE.md coding rules — cite the Autodesk URL already
     in `investigate_sinehalfwave_formula.md`).
   - In `calculate_point_on_element`, add a branch after the circular-arc check and
     before the generic Simpson spiral block:
     `if el.transition == 'COSINE' and (el.k_in == 0) != (el.k_out == 0):` (exactly one
     of k_in/k_out is zero — pure SPIN or SPOUT, excludes compound). Inside: compute
     `L`, pick `R = radius_from_curvature(el.k_out or el.k_in)` (reuse the existing
     `radius_from_curvature` helper — same signed-R convention as everywhere else),
     compute `X`, then branch SPIN (`el.k_in == 0`) vs SPOUT (mirror, per formula
     above) to get `(x_local, y_local, theta_local)`, then apply the SAME
     rotation-to-global step already used by the Simpson branch (`ca, sa =
     cos(el.azimuth), sin(el.azimuth)` → `n=el.n+x*ca-y*sa, e=el.e+x*sa+y*ca,
     azimuth=normalize_angle(el.azimuth+theta_local)`) — reuse, don't duplicate.
   - Update the module docstring's "Transition shapes" block (lines 12-16): COSINE is
     no longer `f(τ)=(1-cos πτ)/2`; describe it as the Civil 3D Sine Half-Wavelength
     Diminishing Tangent Curve, closed-form in tangent-projected distance (not an
     arc-length curvature integral like the other three), cite
     `session_logs/investigate_sinehalfwave_formula.md`, and state both known
     limitations (x≈s mid-curve approximation; SPOUT interior unverified beyond the
     boundary invariant) in one line each.
3. Add new tests to `tests/test_alignment.py` (new section, hardcoded ground truth —
   comment cites `session_logs/investigate_sinehalfwave_formula.md` and the Autodesk
   URL in it):
   - `test_cosine_closed_form_endpoint_r900_l100`: build a SPIN-COSINE element R=900,
     L=100, assert exit turning angle ≈ 3.178942026888° and totalY ≈ 1.651062316115
     (tol matching the 5-6 significant figures already confirmed by hand in the
     investigation doc).
   - `test_cosine_closed_form_endpoint_r250_l50`: same, R=250, L=50, theta ≈
     5.705449190899°, totalY ≈ 1.484093072531, totalX ≈ 49.954662110533.
   - `test_cosine_spin_spout_symmetry_matches_civil3d`: build a SPIN-COSINE and a
     SPOUT-COSINE element, same R, L, same entry azimuth; assert
     `abs(calculate_exit_state(el).azimuth - el.azimuth)` (turning angle magnitude) is
     equal for both to a tight tolerance — this operationalizes the Civil-3D-confirmed
     invariant (same R,L ⇒ same theta for SPIN and SPOUT) as an executable check.
4. Mark the 10 tests xfail per the Decision section above.
5. Verify `src/smt/landxml.py` needs zero changes: confirmed by reading
   `_spiral_geometry` (`src/smt/landxml.py:68-82`) — it already builds a synthetic
   `Element` and calls `calculate_point_on_element`/`calculate_exit_state` from
   `alignment.py` (imported at line 25), always as a canonical SPIN (`k_in=0.0,
   k_out=1.0/R`) regardless of the real element's SPIN/SPOUT role — so it exercises
   only the SPIN branch, which is the directly-verified one. No landxml.py edit
   needed. Confirm live: run `smt export-landxml` against a small fixture containing a
   COSINE spiral at R=900/L=100 (or R=250/L=50) and check the exported `theta`,
   `totalX`/`constant` fields match the ground-truth numbers above.
6. Note only (no action this pass): `reference/vba/SMT_Core.bas` and
   `SMT_Alignment.bas` must get the same closed-form fix in a later, separate commit,
   tested live in Excel, per CLAUDE.md §4.3 VBA parity rule. Renaming `COSINE` to
   something matching Civil 3D's own terminology stays deferred, per CLAUDE.md
   Roadmap, to be done together with the VBA update.

## Verification

- `pytest -q` — expect 10 xfail (not fail), everything else green.
- New tests 3a-3c above pass with the tight ground-truth tolerances.
- `smt export-landxml` smoke test against both R/L ground-truth points, comparing
  theta/totalX/totalY/tanLong/tanShort as described in step 5.
- Manual sanity: `calculate_point_on_element` on a SPIN-COSINE and a SPOUT-COSINE of
  equal R,L must give equal |turning angle| (test 3c) and, for the SPIN case only,
  must reproduce the diff-table numbers above when evaluated at d=L against the R=500,
  L=70 element (i.e. confirms the ~3.1 cm shift is real and matches this plan's
  prediction, not a coding mistake introducing a different, wrong shift).

## Post-execution note (2026-07-05): one planning assumption was wrong

Running the actual test suite after implementation showed the real affected-test
count is **9, not 10** — see `session_logs/report_xfail_mismatch_20260705.md` for the
full comparison and root-cause analysis (that report's own first-draft summary line
also miscounted this as 8, from tallying `test_control_point_parametrized`'s two
separate SC/ST marks as one slot — corrected there too, confirmed by `pytest -rx`
showing exactly 9 xfailed). The specific planning mistake worth keeping
as a lesson: this plan assumed "station values are independent of N/E" as a blanket
rule. That is only true for `parse_alignment_table` (station read directly from the
input table). It is **not** true for `build_alignment_from_pi`, which derives station
by solving the curve group's tangent length (`_calculate_end_displacement` →
`d1 = (v_n·sin(az_out) − v_e·cos(az_out)) / sin(δ)`) from the curve's own geometric
end-displacement — so a position fix there cascades into station values too, amplified
by 1/sin(δ). Future plans touching curve geometry must check both code paths
(direct-table parsing vs. PI-based building) separately for this kind of assumption,
not generalize from one to the other.
