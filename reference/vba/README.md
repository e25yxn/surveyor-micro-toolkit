# SMT VBA Reference — Excel Integration

## Files in this folder

| File | Purpose |
|------|---------|
| `SMT_FPMath.bas` | VBA port of `src/smt/fpmath.py` — angle math utilities |
| `SMT_WCB.bas` | VBA port of `src/smt/wcb.py` — azimuth / coordinate geometry |
| `SMT_Align.bas` | VBA port of `src/smt/alignment.py` — forward + inverse alignment lookup |
| `SMT_Vertical.bas` | VBA port of `src/smt/vertical.py` — elevation at any station |
| `SMT_Crossfall.bas` | VBA port of `src/smt/crossfall.py` — crossfall / superelevation at any station |
| `SMT_LocalCoord.bas` | Local ↔ Global coordinate conversion (port of CHOStoNE / NEtoCHOS) |
| `SMT_Calcuator.xlsm` | Example workbook (macro-enabled) |

---

## How to import a .bas module into Excel

1. Open your workbook in Excel.
2. Press **Alt + F11** to open the VBA Editor (VBE).
3. In the VBE menu: **File → Import File...**
4. Navigate to this folder, select `SMT_FPMath.bas`, and click **Open**.
5. The module `SMT_FPMath` will appear in the **Modules** folder in the Project Explorer.
6. Close the VBE and save the workbook as **macro-enabled** (`.xlsm`).

> Repeat for each `.bas` file you want to add.

---

## SMT_Elements column mapping

When reading the element table output (from `smt build` or `SMT_AlignmentBuilder`),
columns are assigned as follows:

| Column | Header | Description |
|--------|--------|-------------|
| B | `StaStart` | Start station of element (metres) |
| C | `StaEnd` | End station of element (metres) |
| D | `N` | Northing at element start (metres) |
| E | `E` | Easting at element start (metres) |
| F | `Azimuth` | Forward azimuth at start, in **decimal degrees** |
| G | `Radius` | Signed radius (metres); see sign convention below |
| H | `Type` | Element type: `LINE`, `ARC`, `SPIRAL` |
| I | `Transition` | Transition length (metres); 0 for non-spiral elements |

Column A is typically the element index (1-based).

---

## Sign convention

| Quantity | Positive (+) | Negative (-) |
|----------|--------------|--------------|
| Offset | Right of travel direction | Left of travel direction |
| Radius (column G) | Curve turns right (clockwise) | Curve turns left (counter-clockwise) |
| Azimuth (column F) | Stored in degrees, 0-360 (bearing from North, clockwise) | N/A — normalised to [0, 360) |

> Inside the VBA/Python engine, all angles are stored as **radians**.
> Degrees appear only at the input/output boundary (column F, DMS strings, etc.).

---

## SMT_FPMath function reference

| Function | Arguments | Returns | Notes |
|----------|-----------|---------|-------|
| `SMT_Pi()` | — | `Double` | pi ~= 3.14159265358979 |
| `SMT_DegToRad(deg)` | deg: Double | `Double` (rad) | Decimal degrees to radians |
| `SMT_RadToDeg(rad)` | rad: Double | `Double` (deg) | Radians to decimal degrees |
| `SMT_NormalizeAngle(az)` | az: Double (rad) | `Double` (rad) | Wraps to [0, 2*pi) |
| `SMT_AngleDiff(a, b)` | a, b: Double (rad) | `Double` (rad) | Shortest (a-b), range (-pi, pi] |

### Example usage in a cell formula

```vba
=SMT_DegToRad(A2)                          ' convert degrees in A2 to radians
=SMT_NormalizeAngle(B2)                    ' wrap angle in B2 to [0, 2*pi)
=SMT_RadToDeg(SMT_AngleDiff(C2, D2))      ' angle diff in degrees
```

---

## SMT_Align function reference

Requires: `SMT_FPMath` and `SMT_WCB` modules imported in the same workbook.

Named Range **SMT_Elements** must have 8 columns per row (no header row):

| Col | Field | Unit / Notes |
|-----|-------|--------------|
| 1 | StaStart | metres |
| 2 | StaEnd | metres |
| 3 | N | Northing (metres) at element start |
| 4 | E | Easting (metres) at element start |
| 5 | Azimuth | **decimal degrees** — converted to radians internally |
| 6 | Radius | signed metres (+right curve / -left curve); 0 for tangent |
| 7 | Type | `T` / `C` / `SPIN` / `SPOUT` |
| 8 | Transition | `CLOTHOID` / `BLOSS` / `COSINE` / `SINE` (blank = CLOTHOID) |

| Function | Arguments | Returns | Notes |
|----------|-----------|---------|-------|
| `SMT_StaToN(sta, offset, rng)` | sta, offset: Double; rng: Range | `Double` (metres) | Forward: sta+offset → Northing |
| `SMT_StaToE(sta, offset, rng)` | sta, offset: Double; rng: Range | `Double` (metres) | Forward: sta+offset → Easting |
| `SMT_CoordToSta(n, e, rng)` | n, e: Double; rng: Range | `Double` (metres) | Inverse: N,E → station |
| `SMT_CoordToOffset(n, e, rng)` | n, e: Double; rng: Range | `Double` (metres) | Inverse: N,E → offset (+right/-left) |

### Example usage in a cell formula

```vba
=SMT_StaToN(A2, 0, SMT_Elements)          ' centre-line Northing at station in A2
=SMT_StaToE(A2, B2, SMT_Elements)         ' Easting with offset B2 (+ right, - left)
=SMT_CoordToSta(C2, D2, SMT_Elements)     ' station for grid point (C2=N, D2=E)
=SMT_CoordToOffset(C2, D2, SMT_Elements)  ' offset from centre line
```

---

## SMT_Vertical function reference

No dependency on other SMT modules.

Named Range **SMT_Vertical** must have 7 columns per row (no header row):

| Col | Field | Unit / Notes |
|-----|-------|--------------|
| 1 | StaStart | metres |
| 2 | StaEnd | metres |
| 3 | Level | elevation at StaStart (metres) |
| 4 | G1 | entry grade (%) |
| 5 | G2 | exit grade (%) |
| 6 | LVC | VC length (metres); 0 = tangent grade segment |
| 7 | LVC2 | 2nd arm for asymmetric/compound VC (metres); 0 = symmetric |

Segment types determined by LVC and LVC2:

| LVC | LVC2 | Type |
|-----|------|------|
| 0 | — | Tangent grade |
| > 0 | 0 | Symmetric parabolic VC |
| > 0 | > 0 | Asymmetric (compound, unequal-tangent) VC |

| Function | Arguments | Returns | Notes |
|----------|-----------|---------|-------|
| `SMT_Elevation(sta, rng)` | sta: Double; rng: Range | `Double` (metres) | Elevation at station sta |

### Example usage in a cell formula

```vba
=SMT_Elevation(A2, SMT_Vertical)          ' elevation at station in A2
```

---

## SMT_Crossfall function reference

No dependency on other SMT modules.

Named Range **SMT_Crossfall** must have 6 columns per row (no header row):

| Col | Field | Unit / Notes |
|-----|-------|--------------|
| 1 | StaStart | metres |
| 2 | StaEnd | metres |
| 3 | CF_L_Start | left crossfall at StaStart (%) |
| 4 | CF_L_End | left crossfall at StaEnd (%) |
| 5 | CF_R_Start | right crossfall at StaStart (%) |
| 6 | CF_R_End | right crossfall at StaEnd (%) |

Sign convention: **negative** = falls away from centre line (normal drainage); **positive** = falls toward centre line (superelevation).

Interpolation: linear within each segment. When CF_Start = CF_End the value is constant.

| Function | Arguments | Returns | Notes |
|----------|-----------|---------|-------|
| `SMT_CrossfallLeft(sta, rng)` | sta: Double; rng: Range | `Double` (%) | Left crossfall at sta |
| `SMT_CrossfallRight(sta, rng)` | sta: Double; rng: Range | `Double` (%) | Right crossfall at sta |

### Example usage in a cell formula

```vba
=SMT_CrossfallLeft(A2,  SMT_Crossfall)    ' left crossfall (%) at station in A2
=SMT_CrossfallRight(A2, SMT_Crossfall)    ' right crossfall (%) at station in A2
```

---

## SMT_LocalCoord function reference

Requires: `SMT_FPMath` module. No Named Range needed — all inputs are cell values.

**Local coordinate system:** origin (N0, E0); X-axis along AziBEG; Chainage = distance along X; Offset = perpendicular (+right / −left).

AziBEG is always in **decimal degrees** (survey: 0=North, clockwise+); converted to radians internally.

| Function | Arguments | Returns | Notes |
|----------|-----------|---------|-------|
| `SMT_LocalToN(n0,e0,aziBEG,chn,ofs)` | all Double | `Double` (metres) | Local (chn, ofs) → global Northing |
| `SMT_LocalToE(n0,e0,aziBEG,chn,ofs)` | all Double | `Double` (metres) | Local (chn, ofs) → global Easting |
| `SMT_GlobalToChn(n0,e0,aziBEG,n,e)` | all Double | `Double` (metres) | Global (N, E) → Chainage |
| `SMT_GlobalToOfs(n0,e0,aziBEG,n,e)` | all Double | `Double` (metres) | Global (N, E) → Offset (+right/−left) |

### Example usage in a cell formula

```vba
=SMT_LocalToN($B$1,$B$2,$B$3,A6,B6)   ' local (chn=A6,ofs=B6) -> Northing
=SMT_LocalToE($B$1,$B$2,$B$3,A6,B6)   ' local (chn=A6,ofs=B6) -> Easting
=SMT_GlobalToChn($B$1,$B$2,$B$3,C6,D6)' global (N=C6,E=D6)  -> Chainage
=SMT_GlobalToOfs($B$1,$B$2,$B$3,C6,D6)' global (N=C6,E=D6)  -> Offset
```
