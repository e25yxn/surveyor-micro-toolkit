"""vertical_builder - Build vertical alignment from a VPI (Vertical Point of Intersection) list.

Port from reference/VerticalBuilder.gs (validated engine, AllTests 45/45).

Vertical twin of alignment_builder, operating in the station-elevation plane.
  VPI  ~ PI,  grade (%)  ~ azimuth,  parabolic VC  ~ circular arc,  LVC  ~ arc length.

Input vpis = [BVP, {VPI...}, ..., EVP]
  BVP (first) / EVP (last)    : {'sta', 'elev'}              — no curve
  Interior VPI symmetric       : {'sta', 'elev', 'L'}         — symmetric VC, total length L
  Interior VPI asymmetric      : {'sta', 'elev', 'L1', 'L2'} — asymmetric VC, arms L1 / L2

Grades are computed from consecutive VPI elevations; they do not need to be supplied.

Returns VerticalBuildResult(rows, control, issues).
  rows    = list of VerticalRow ready for use with VLEVEL
  control = list of VControlPoint (BVP / PVC / PVI / PVT / EVP)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------

@dataclass
class VerticalRow:
    """One vertical alignment segment.

    level    : elevation at sta_start (PVC level for curve rows).
    grade_in : entry grade (%).
    grade_out: exit grade  (%).
    lvc      : 0 for tangent; total L for symmetric VC; L1 for asymmetric VC.
    lvc2     : None for tangent or symmetric VC; L2 for asymmetric VC.
    """
    sta_start: float
    sta_end: float
    level: float
    grade_in: float
    grade_out: float
    lvc: float
    lvc2: float | None


@dataclass
class VControlPoint:
    """Named station-elevation control point produced by the builder."""
    name: str
    sta: float
    elev: float


class VerticalBuildResult(NamedTuple):
    """Output of build_vertical_from_vpi."""
    rows: list[VerticalRow]
    control: list[VControlPoint]
    issues: list[str]


# ---------------------------------------------------------------------------
# Public: builder
# ---------------------------------------------------------------------------

def build_vertical_from_vpi(vpis: list[dict]) -> VerticalBuildResult:
    """Build vertical alignment segment list from a VPI list.

    vpis[0]    = BVP — {'sta', 'elev'}.  Sets the starting chainage and elevation.
    vpis[1:-1] = interior VPI — curve parameters as described in the module docstring.
    vpis[-1]   = EVP — {'sta', 'elev'}.

    Returns VerticalBuildResult(rows, control, issues).  Geometry errors (e.g. overlapping
    curves) are appended to issues rather than raised.
    """
    rows: list[VerticalRow] = []
    control: list[VControlPoint] = []
    issues: list[str] = []
    N = len(vpis)

    end_sta = float(vpis[0]['sta'])
    end_elev = float(vpis[0]['elev'])
    control.append(VControlPoint(name='BVP', sta=end_sta, elev=end_elev))

    for i in range(1, N - 1):
        v = vpis[i]
        v_sta = float(v['sta'])
        v_elev = float(v['elev'])

        g_in = (v_elev - float(vpis[i - 1]['elev'])) / (v_sta - float(vpis[i - 1]['sta'])) * 100
        g_out = (float(vpis[i + 1]['elev']) - v_elev) / (float(vpis[i + 1]['sta']) - v_sta) * 100

        sym = v.get('L1') is None and v.get('L2') is None
        L1 = float(v.get('L') or 0) / 2 if sym else float(v.get('L1') or 0)
        L2 = float(v.get('L') or 0) / 2 if sym else float(v.get('L2') or 0)

        pvc_sta = v_sta - L1
        pvt_sta = v_sta + L2
        pvc_elev = v_elev - g_in * L1 / 100
        pvt_elev = v_elev + g_out * L2 / 100

        if pvc_sta > end_sta + 1e-9:
            rows.append(VerticalRow(
                sta_start=end_sta, sta_end=pvc_sta, level=end_elev,
                grade_in=g_in, grade_out=g_in, lvc=0, lvc2=None,
            ))
        elif pvc_sta < end_sta - 1e-6:
            issues.append(
                f'VPI#{i} (STA {v_sta}): vertical curve overlaps previous segment (LVC too long)'
            )

        control.append(VControlPoint(name='PVC', sta=pvc_sta, elev=pvc_elev))
        rows.append(VerticalRow(
            sta_start=pvc_sta, sta_end=pvt_sta, level=pvc_elev,
            grade_in=g_in, grade_out=g_out,
            lvc=float(v.get('L') or 0) if sym else L1,
            lvc2=None if sym else L2,
        ))
        control.append(VControlPoint(name='PVI', sta=v_sta, elev=v_elev))
        control.append(VControlPoint(name='PVT', sta=pvt_sta, elev=pvt_elev))

        end_sta = pvt_sta
        end_elev = pvt_elev

    ep = vpis[-1]
    ep_sta = float(ep['sta'])
    ep_elev = float(ep['elev'])
    if ep_sta > end_sta + 1e-9:
        g_end = (ep_elev - end_elev) / (ep_sta - end_sta) * 100
        rows.append(VerticalRow(
            sta_start=end_sta, sta_end=ep_sta, level=end_elev,
            grade_in=g_end, grade_out=g_end, lvc=0, lvc2=None,
        ))
    control.append(VControlPoint(name='EVP', sta=ep_sta, elev=ep_elev))

    return VerticalBuildResult(rows=rows, control=control, issues=issues)


# ---------------------------------------------------------------------------
# Public: table conversion
# ---------------------------------------------------------------------------

def to_table(rows: list[VerticalRow]) -> list[list]:
    """Convert VerticalRow list to a 2-D table (columns: sta_start..lvc2).

    lvc2 is '' when None, matching the spreadsheet column convention.
    """
    return [
        [r.sta_start, r.sta_end, r.level, r.grade_in, r.grade_out, r.lvc,
         '' if r.lvc2 is None else r.lvc2]
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Public: cross-check
# ---------------------------------------------------------------------------

def check_against_drawing(
    control: list[VControlPoint],
    drawing: list[dict],
    tolerance_sta: float = 0.01,
    tolerance_elev: float = 0.005,
) -> list[dict]:
    """Cross-check computed control points against drawing / survey values.

    For each entry in drawing, finds the closest-by-station control point
    (filtered by name when drawing entry has a non-empty 'name' key), then
    computes station and elevation deviations.

    drawing entries: {'name' (optional), 'sta', 'elev'}.
    Returns list of dicts: {name, sta, d_sta, d_elev, ok}.
    ok is True when d_sta ≤ tolerance_sta and d_elev ≤ tolerance_elev.
    """
    report: list[dict] = []
    for d in drawing:
        d_name = str(d.get('name') or '').strip()
        d_sta = float(d['sta'])
        best: VControlPoint | None = None
        best_dist = float('inf')
        for c in control:
            if d_name and c.name != d_name:
                continue
            dist = abs(c.sta - d_sta)
            if dist < best_dist:
                best_dist = dist
                best = c
        if best is None:
            continue
        d_sta_diff = abs(best.sta - d_sta)
        d_elev_diff = abs(best.elev - float(d['elev']))
        report.append({
            'name': d_name or best.name,
            'sta': best.sta,
            'd_sta': d_sta_diff,
            'd_elev': d_elev_diff,
            'ok': d_sta_diff <= tolerance_sta and d_elev_diff <= tolerance_elev,
        })
    return report
