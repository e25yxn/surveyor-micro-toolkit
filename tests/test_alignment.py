"""Golden tests for smt.alignment.

Fixtures loaded from tests/golden/tables.json (30-element alignment, 31 control points).

Two test categories:
  1. control_point: all 31 control points must produce N,E within 1e-3 m.
  2. roundtrip:     forward (sta→coord) then inverse (coord→sta) must
                    recover the original station within 1e-3 m, offset ≈ 0.
"""
import json
import math
from pathlib import Path

import pytest

from smt import alignment as al

# ---------------------------------------------------------------------------
# Fixture: load golden data once
# ---------------------------------------------------------------------------

_GOLDEN = Path(__file__).parent / 'golden' / 'tables.json'


@pytest.fixture(scope='module')
def golden():
    with _GOLDEN.open(encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def elements(golden):
    return al.parse_alignment_table(golden['elements'])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _mid(el: al.Element) -> float:
    """Station at the midpoint of an element."""
    return (el.sta_start + el.sta_end) / 2.0


# ---------------------------------------------------------------------------
# Test 1: chain integrity
# ---------------------------------------------------------------------------

def test_chain_has_no_gaps(elements):
    """Exit state of element[n] must equal entry state of element[n+1]."""
    issues = al.check_chain(elements, tolerance=0.005)
    assert issues == [], f'Chain gaps found: {issues}'


# ---------------------------------------------------------------------------
# Test 2: all 31 control points
# ---------------------------------------------------------------------------

def _control_params(golden_data):
    return [
        pytest.param(cp['sta'], cp['n'], cp['e'], id=f"{cp['name']}@{cp['sta']}")
        for cp in golden_data['controls']
    ]


def test_control_points(elements, golden):
    """All 31 control points must resolve to N,E within 1e-3 m.

    EP is the alignment end-point: its fixture station is the 3-decimal rounding of
    elements[-1].sta_end, so we use the full-precision element station directly.
    """
    tol = 1e-3
    failures = []
    for cp in golden['controls']:
        sta = elements[-1].sta_end if cp['name'] == 'EP' else cp['sta']
        pt = al.calculate_station_to_coordinate(elements, sta, 0.0)
        err_n = abs(pt.n - cp['n'])
        err_e = abs(pt.e - cp['e'])
        if err_n > tol or err_e > tol:
            failures.append(
                f"{cp['name']}@{sta}: "
                f"got ({pt.n:.4f},{pt.e:.4f}) "
                f"expected ({cp['n']:.4f},{cp['e']:.4f}) "
                f"err=({err_n:.6f},{err_e:.6f})"
            )
    assert not failures, 'Control point failures:\n' + '\n'.join(failures)


# Parametrized variant — one test per control point for granular CI output
@pytest.mark.parametrize(
    'sta,exp_n,exp_e,name',
    [
        (cp['sta'], cp['n'], cp['e'], cp['name'])
        for cp in json.loads(_GOLDEN.read_text(encoding='utf-8'))['controls']
    ],
    ids=[
        f"{cp['name']}@{cp['sta']}"
        for cp in json.loads(_GOLDEN.read_text(encoding='utf-8'))['controls']
    ],
)
def test_control_point_parametrized(elements, sta, exp_n, exp_e, name):
    # EP station in the fixture is a 3-decimal rounding of elements[-1].sta_end;
    # use the full-precision element boundary to avoid the 1e-4 tolerance edge.
    actual_sta = elements[-1].sta_end if name == 'EP' else sta
    pt = al.calculate_station_to_coordinate(elements, actual_sta, 0.0)
    assert abs(pt.n - exp_n) <= 1e-3, (
        f'{name}@{actual_sta}: N got {pt.n:.4f} expected {exp_n:.4f}'
    )
    assert abs(pt.e - exp_e) <= 1e-3, (
        f'{name}@{actual_sta}: E got {pt.e:.4f} expected {exp_e:.4f}'
    )


# ---------------------------------------------------------------------------
# Test 3: roundtrip — forward then inverse recovers sta, offset ≈ 0
# ---------------------------------------------------------------------------

def _roundtrip_stations(elements: list[al.Element]) -> list[tuple[str, float]]:
    """One station per element type, solidly inside (not at a boundary)."""
    cases = []
    for el in elements:
        label = f'{el.type}({el.transition})@{el.sta_start:.1f}'
        cases.append((label, _mid(el)))
    return cases


def test_roundtrip_all_element_types(elements):
    """forward(sta) → coord → inverse must recover sta within 1e-3 and offset ≈ 0."""
    tol = 1e-3
    failures = []
    for label, sta in _roundtrip_stations(elements):
        pt = al.calculate_station_to_coordinate(elements, sta, 0.0)
        result = al.calculate_coordinate_to_station(elements, pt.n, pt.e)
        err_sta = abs(result.sta - sta)
        err_off = abs(result.offset)
        if err_sta > tol or err_off > tol:
            failures.append(
                f'{label}: sta_err={err_sta:.6f} off_err={err_off:.6f}'
            )
    assert not failures, 'Roundtrip failures:\n' + '\n'.join(failures)


@pytest.mark.parametrize(
    'label,sta',
    _roundtrip_stations(al.parse_alignment_table(
        json.loads(_GOLDEN.read_text(encoding='utf-8'))['elements']
    )),
)
def test_roundtrip_parametrized(elements, label, sta):
    pt = al.calculate_station_to_coordinate(elements, sta, 0.0)
    result = al.calculate_coordinate_to_station(elements, pt.n, pt.e)
    assert abs(result.sta - sta) <= 1e-3, (
        f'{label}: sta got {result.sta:.4f} expected {sta:.4f}'
    )
    assert abs(result.offset) <= 1e-3, (
        f'{label}: residual offset {result.offset:.6f}'
    )


# ---------------------------------------------------------------------------
# Test 4: unit tests for make_element and curvature helpers
# ---------------------------------------------------------------------------

def test_curvature_from_radius_tangent():
    assert al.curvature_from_radius(0) == 0.0
    assert al.curvature_from_radius(None) == 0.0
    assert al.curvature_from_radius(math.inf) == 0.0


def test_curvature_from_radius_positive():
    assert math.isclose(al.curvature_from_radius(300), 1 / 300)


def test_curvature_from_radius_negative():
    assert math.isclose(al.curvature_from_radius(-400), -1 / 400)


def test_radius_from_curvature_zero():
    assert math.isinf(al.radius_from_curvature(0.0))


def test_make_element_tangent():
    el = al.make_element('T', 0, 100, 0, 0, 90, 0)
    assert el.k_in == 0.0
    assert el.k_out == 0.0
    assert el.type == 'T'


def test_make_element_spin_sets_k_in_zero():
    el = al.make_element('SPIN', 100, 160, 0, 0, 90, 400)
    assert el.k_in == 0.0
    assert math.isclose(el.k_out, 1 / 400)


def test_make_element_spout_sets_k_out_zero():
    el = al.make_element('SPOUT', 160, 220, 0, 0, 95, 400)
    assert math.isclose(el.k_in, 1 / 400)
    assert el.k_out == 0.0


def test_make_element_circular_negative_radius():
    el = al.make_element('C', 200, 300, 0, 0, 90, -400)
    assert math.isclose(el.k_in, -1 / 400)
    assert math.isclose(el.k_out, -1 / 400)


# ---------------------------------------------------------------------------
# Test 5: tangent geometry sanity checks
# ---------------------------------------------------------------------------

def test_point_on_tangent_due_east():
    el = al.make_element('T', 0, 1000, 20000, 10000, 90, 0)
    st = al.calculate_point_on_element(el, 519.6152)
    assert math.isclose(st.n, 20000.0, abs_tol=1e-9)
    assert math.isclose(st.e, 10519.6152, abs_tol=1e-9)


def test_exit_state_matches_next_entry(elements):
    """Exit state of each element must match the n,e,az of the next element."""
    tol_pos = 1e-3   # 1 mm
    tol_az = math.radians(5 / 3600)   # 5 arc-seconds
    for i in range(len(elements) - 1):
        ex = al.calculate_exit_state(elements[i])
        nxt = elements[i + 1]
        assert math.hypot(ex.n - nxt.n, ex.e - nxt.e) < tol_pos, (
            f'Element {i}->{i+1} position gap: '
            f'exit=({ex.n:.4f},{ex.e:.4f}) next=({nxt.n:.4f},{nxt.e:.4f})'
        )
        assert abs(al.fpmath.calculate_angle_diff(ex.azimuth, nxt.azimuth)) < tol_az, (
            f'Element {i}->{i+1} azimuth gap: '
            f'exit_az={math.degrees(ex.azimuth):.6f} next_az={math.degrees(nxt.azimuth):.6f}'
        )


# ---------------------------------------------------------------------------
# Test 6: check_chain detection (previously only "no issues" path was tested)
# ---------------------------------------------------------------------------

def test_check_chain_broken():
    """check_chain must detect a position gap between non-connecting elements.

    Two due-east tangents with el1 starting 1000 m east of where el0 exits:
      el0 exits at (N=0, E=1000); el1 entry is at (N=0, E=2000) → gap = 1000 m.
    """
    el0 = al.make_element('T', 0,    1000, 0.0, 0.0,    90.0, 0)
    el1 = al.make_element('T', 1000, 2000, 0.0, 2000.0, 90.0, 0)
    issues = al.check_chain([el0, el1])
    assert issues, 'check_chain should detect the 1000 m gap'
    assert issues[0]['between'] == '1->2'
    assert issues[0]['gap_mm'] > 900_000   # 1 000 000 mm expected


# ---------------------------------------------------------------------------
# Test 7: calculate_projection_to_element direct unit test (tangent case)
# ---------------------------------------------------------------------------

def test_projection_direct():
    """calculate_projection_to_element on a tangent element: sta, offset, in_range.

    Due-east tangent from (N=0, E=0), sta 0→1000.
    Projection formulae (tangent):
      d   = dN·cos(az) + dE·sin(az)   → arc distance from element start
      off = −dN·sin(az) + dE·cos(az)  → signed perpendicular offset (+right/−left)
    """
    el = al.make_element('T', 0, 1000, 0.0, 0.0, 90.0, 0)

    # Point north of the line (left of east-bound travel) at E=300
    # d = 10*0 + 300*1 = 300;  off = −10*1 + 300*0 = −10 (left → negative)
    pr = al.calculate_projection_to_element(el, 10.0, 300.0)
    assert math.isclose(pr.sta,    300.0, abs_tol=1e-9), f'sta={pr.sta}'
    assert math.isclose(pr.offset, -10.0, abs_tol=1e-9), f'offset={pr.offset}'
    assert pr.in_range is True

    # Point south of the line (right of east-bound travel) at E=700
    # d = 700;  off = −(−5)*1 + 700*0 = +5 (right → positive)
    pr2 = al.calculate_projection_to_element(el, -5.0, 700.0)
    assert math.isclose(pr2.sta,    700.0, abs_tol=1e-9), f'sta={pr2.sta}'
    assert math.isclose(pr2.offset,   5.0, abs_tol=1e-9), f'offset={pr2.offset}'
    assert pr2.in_range is True

    # Point beyond the far end (E=1500) → in_range must be False
    pr3 = al.calculate_projection_to_element(el, 0.0, 1500.0)
    assert pr3.in_range is False


# ---------------------------------------------------------------------------
# Test 8: radius_from_curvature — negative k, unit, near-zero k
# ---------------------------------------------------------------------------

def test_radius_from_curvature_negative_k():
    assert math.isclose(al.radius_from_curvature(-2.0), -0.5, abs_tol=1e-12)


def test_radius_from_curvature_unit():
    assert al.radius_from_curvature(1.0) == 1.0


def test_radius_from_curvature_near_zero():
    R = al.radius_from_curvature(1e-9)
    assert math.isclose(R, 1e9, rel_tol=1e-6)


# ---------------------------------------------------------------------------
# Test 9: make_element — trans variants, trans=None default
# ---------------------------------------------------------------------------

def test_make_element_trans_bloss():
    el = al.make_element('SPIN', 0, 100, 0, 0, 90, 400, None, 'BLOSS')
    assert el.transition == 'BLOSS'


def test_make_element_trans_none_defaults_clothoid():
    el = al.make_element('T', 0, 100, 0, 0, 90, 0, None, None)
    assert el.transition == 'CLOTHOID'


# ---------------------------------------------------------------------------
# Test 10: parse_alignment_table — header-only, empty radius field
# ---------------------------------------------------------------------------

def test_parse_alignment_header_only():
    rows = [['StaStart', 'StaEnd', 'N', 'E', 'Azimuth_deg', 'Radius', 'Type', 'Transition']]
    assert al.parse_alignment_table(rows) == []


def test_parse_alignment_empty_radius():
    rows = [
        ['StaStart', 'StaEnd', 'N', 'E', 'Azimuth_deg', 'Radius', 'Type', 'Transition'],
        [0, 1000, 20000, 10000, 90.0, None, 'T', 'CLOTHOID'],
    ]
    els = al.parse_alignment_table(rows)
    assert len(els) == 1
    assert els[0].k_in == 0.0
    assert els[0].k_out == 0.0


# ---------------------------------------------------------------------------
# Test 11: calculate_point_on_element — d=0 (entry) and d=L (exit)
# ---------------------------------------------------------------------------

def test_point_on_element_d_zero():
    el = al.make_element('T', 0, 1000, 20000, 10000, 90.0, 0)
    st = al.calculate_point_on_element(el, 0.0)
    assert math.isclose(st.n, 20000.0, abs_tol=1e-9)
    assert math.isclose(st.e, 10000.0, abs_tol=1e-9)


def test_point_on_element_d_equals_L():
    el = al.make_element('T', 0, 1000, 20000, 10000, 90.0, 0)
    L = el.sta_end - el.sta_start
    st = al.calculate_point_on_element(el, L)
    ex = al.calculate_exit_state(el)
    assert math.isclose(st.n, ex.n, abs_tol=1e-9)
    assert math.isclose(st.e, ex.e, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 12: get_element_index — empty list, before start, junction boundary
# ---------------------------------------------------------------------------

def test_get_element_index_empty_list():
    assert al.get_element_index([], 100.0) == -1


def test_get_element_index_before_start(elements):
    sta_before = elements[0].sta_start - 1.0
    assert al.get_element_index(elements, sta_before) == -1


def test_get_element_index_at_junction(elements):
    # station exactly at el[0].sta_end: first element wins (loop returns first match)
    sta_j = elements[0].sta_end
    idx = al.get_element_index(elements, sta_j)
    assert idx == 0


# ---------------------------------------------------------------------------
# Test 13: calculate_station_to_coordinate — outside raises, first station ok
# ---------------------------------------------------------------------------

def test_s2c_outside_raises(elements):
    sta_out = elements[-1].sta_end + 100.0
    with pytest.raises(ValueError):
        al.calculate_station_to_coordinate(elements, sta_out, 0.0)


def test_s2c_at_very_first_station(elements):
    sta_first = elements[0].sta_start
    pt = al.calculate_station_to_coordinate(elements, sta_first, 0.0)
    assert math.isclose(pt.n, elements[0].n, abs_tol=1e-6)
    assert math.isclose(pt.e, elements[0].e, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# Test 14: calculate_coordinate_to_station — far point raises ValueError
# ---------------------------------------------------------------------------

def test_c2s_far_point_raises():
    # Single due-east tangent sta 0→100; point behind it (E=-500) cannot project in-range
    el = al.make_element('T', 0, 100, 0.0, 0.0, 90.0, 0)
    with pytest.raises(ValueError):
        al.calculate_coordinate_to_station([el], 0.0, -500.0)


# ---------------------------------------------------------------------------
# Test 15: COSINE closed form (Civil 3D Sine Half-Wavelength Diminishing Tangent
# Curve) — ground truth from session_logs/investigate_sinehalfwave_formula.md,
# itself sourced from Autodesk Civil 3D 2026 Help, "About Transition Definitions"
# (https://help.autodesk.com/cloudhelp/2026/ENG/Civil3D-UserGuide/files/GUID-DD7C0EA1-8465-45BA-9A39-FC05106FD822.htm).
# Evaluated at d=length directly (not d=X as previously) since
# session_logs/investigate_cosine_arclength_inversion.md replaced the x~=d
# approximation with true arc-length inversion (_cosine_solve_a) plus an exact
# a=1 shortcut precisely at d=length -- see alignment.py module docstring
# "Transition shapes" and "Known limitations".
# ---------------------------------------------------------------------------

def _cosine_local_turn_and_offset(el: al.Element, d: float) -> tuple[float, float]:
    """(turning angle deg, perpendicular local offset m) at arc distance d."""
    st = al.calculate_point_on_element(el, d)
    turn_deg = math.degrees(st.azimuth - el.azimuth)
    dn, de = st.n - el.n, st.e - el.e
    local_y = -dn * math.sin(el.azimuth) + de * math.cos(el.azimuth)
    return turn_deg, local_y


@pytest.mark.parametrize('r,length,theta_exact_deg,y_exact', [
    (900.0, 100.0, 3.1789420268894153, 1.6510623161163274),
    (250.0,  50.0, 5.705449190907088,  1.4840930725353705),
    (500.0,  70.0, 4.002399624673551,  1.4557579182062208),
])
def test_cosine_endpoint_matches_a1_closed_form(r, length, theta_exact_deg, y_exact):
    """At d=length, the engine must match the exact a=1 closed form to float64
    precision (not just "close") -- this is the a==1.0 shortcut in
    _sine_halfwave_point, not the general bisection path. Values verified in
    session_logs/plan_cosine_arclength_core_fix.md (Group 1).
    """
    el = al.make_element('SPIN', 0, length, 0.0, 0.0, 90.0, r, None, 'COSINE')
    turn_deg, local_y = _cosine_local_turn_and_offset(el, length)
    assert math.isclose(turn_deg, theta_exact_deg, abs_tol=1e-9)
    assert math.isclose(local_y, y_exact, abs_tol=1e-9)


@pytest.mark.parametrize('r,length,d', [(900.0, 100.0, 40.0), (250.0, 50.0, 20.0), (500.0, 70.0, 55.0)])
def test_cosine_arc_length_inversion_self_consistent(r, length, d):
    """At an interior point (d<length), the a solved by _cosine_solve_a must
    itself satisfy s(a)=d (round-trip through the Simpson arc-length integral).
    """
    big_x = al.calculate_sine_halfwave_tangent_length(length, r)
    a = al._cosine_solve_a(d, big_x, r, length)
    s_check = al._cosine_arc_length(a, big_x, r)
    assert math.isclose(s_check, d, abs_tol=1e-6)


def test_cosine_arc_length_table_cached_across_spin_spout():
    """SPIN and SPOUT of equal length/|R| must share one cached arc-length table
    (mirror symmetry -- see module docstring "Transition shapes")."""
    al._cosine_arc_length_table.cache_clear()
    spin = al.make_element('SPIN', 0, 70.0, 0.0, 0.0, 90.0, 500.0, None, 'COSINE')
    spout = al.make_element('SPOUT', 0, 70.0, 0.0, 0.0, 90.0, 500.0, None, 'COSINE')
    al.calculate_point_on_element(spin, 55.0)
    al.calculate_point_on_element(spout, 55.0)
    info = al._cosine_arc_length_table.cache_info()
    assert info.currsize == 1


@pytest.mark.parametrize('r,length', [(900.0, 100.0), (250.0, 50.0), (500.0, 70.0)])
def test_cosine_solve_a_clamps_gracefully_in_s1_length_gap(r, length):
    """s(1) != length exactly (see session_logs/investigate_cosine_arclength_inversion.md
    section 3) -- any d strictly between s(1) and length has no a<=1 solving
    s(a)=d, and _cosine_solve_a must clamp to a=1.0 rather than error.
    """
    big_x = al.calculate_sine_halfwave_tangent_length(length, r)
    s1 = al._cosine_arc_length(1.0, big_x, r)
    gap = length - s1
    assert gap > 0   # sanity: confirms this test actually exercises the gap
    d_mid = length - gap / 2.0
    a = al._cosine_solve_a(d_mid, big_x, r, length)
    assert a == 1.0


@pytest.mark.parametrize('trans,r,length,d,exp_n,exp_e,exp_az', [
    ('CLOTHOID', 400.0, 60.0, 0.0,  0.0,                    0.0,                 1.5707963267948966),
    ('CLOTHOID', 400.0, 60.0, 15.0, -0.02343746321541169,   14.999967041045013,  1.5754838267948967),
    ('CLOTHOID', 400.0, 60.0, 30.0, -0.18749529162218986,   29.9989453295336,    1.5895463267948964),
    ('CLOTHOID', 400.0, 60.0, 45.0, -0.6327320566067619,    44.99199162569003,   1.6129838267948964),
    ('CLOTHOID', 400.0, 60.0, 60.0, -1.499397428754978,     59.96625878371091,   1.6457963267948967),
    ('BLOSS',    400.0, 60.0, 0.0,  0.0,                    0.0,                 1.5707963267948966),
    ('BLOSS',    400.0, 60.0, 15.0, -0.00791015389733473,   14.99999533039958,   1.572847108044897),
    ('BLOSS',    400.0, 60.0, 30.0, -0.11249847240800069,   29.999539624480274,  1.5848588267948962),
    ('BLOSS',    400.0, 60.0, 45.0, -0.4982850314579719,    44.994167949146686,  1.6103471080448966),
    ('BLOSS',    400.0, 60.0, 60.0, -1.3494424055276184,    59.96920464868514,   1.6457963267948967),
    ('SINE',     500.0, 70.0, 0.0,  0.0,                    0.0,                 1.5707963267948966),
    ('SINE',     500.0, 70.0, 17.5, -0.0029697381528134234, 17.499999311860066,  1.5716250853674145),
    ('SINE',     500.0, 70.0, 35.0, -0.08004763795198576,   34.999762188679995,  1.5812038439399334),
    ('SINE',     500.0, 70.0, 52.5, -0.4633347068139018,    52.49508457246585,   1.6066250853674147),
    ('SINE',     500.0, 70.0, 70.0, -1.38458305097449,      69.96995876779974,   1.6407963267948968),
])
def test_non_cosine_transitions_unaffected_by_cosine_fix(trans, r, length, d, exp_n, exp_e, exp_az):
    """CLOTHOID/BLOSS/SINE never enter the COSINE branch in calculate_point_on_element
    -- baseline values captured against the pre-fix engine, re-asserted here to
    confirm the COSINE arc-length inversion fix changes nothing for these shapes.
    """
    el = al.make_element('SPIN', 0, length, 0.0, 0.0, 90.0, r, None, trans)
    st = al.calculate_point_on_element(el, d)
    assert math.isclose(st.n, exp_n, abs_tol=1e-9)
    assert math.isclose(st.e, exp_e, abs_tol=1e-9)
    assert math.isclose(st.azimuth, exp_az, abs_tol=1e-12)


@pytest.mark.parametrize('r,length', [(900.0, 100.0), (250.0, 50.0), (500.0, 70.0)])
def test_cosine_spin_spout_symmetry_matches_civil3d(r, length):
    """SPIN and SPOUT of equal R,L must share the same total turning angle.

    Confirmed against real Civil 3D data (R=250/L=50, from the now-lost
    SMT_TEST_ALINGMENT2.xml) in session_logs/investigate_sinehalfwave_formula.md:
    SPIN and SPOUT gave identical theta/totalX/totalY/tanLong/tanShort. This test
    operationalizes that invariant for the s<->L-s SPOUT mirror implemented here.
    """
    spin = al.make_element('SPIN', 0, length, 0.0, 0.0, 90.0, r, None, 'COSINE')
    spout = al.make_element('SPOUT', 0, length, 0.0, 0.0, 90.0, r, None, 'COSINE')
    spin_turn = al.calculate_exit_state(spin).azimuth - spin.azimuth
    spout_turn = al.calculate_exit_state(spout).azimuth - spout.azimuth
    assert math.isclose(spin_turn, spout_turn, abs_tol=1e-9)
