# SMT VBA Reference — Excel Integration

## Files in this folder

| File | Purpose |
|------|---------|
| `SMT_FPMath.bas` | VBA port of `src/smt/fpmath.py` — angle math utilities |
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
