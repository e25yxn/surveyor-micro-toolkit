Attribute VB_Name = "SMT_Rotation3D"
Option Explicit

' ============================================================
' SMT_Rotation3D.bas  --  3-D rotation matrices + alignment WCB
' SMT (Surveyor Micro Toolkit)
'
' Part 1 -- 3-D rotation (port of professor's original code, 4 fixes applied):
'   (1) Dim i As Long        (was Integer -- overflows > 32767 rows)
'   (2) nRows As Long        (was Integer)
'   (3) Returns new array    (was ByRef -- no longer mutates the caller's data)
'   (4) cosA / sinA computed once before the loop (not inside every iteration)
'
'   Convention: right-hand rule, standard math CCW rotation.
'   RotX(a): Y' =  cosA*Y - sinA*Z,  Z' =  sinA*Y + cosA*Z
'   RotY(a): X' =  cosA*X + sinA*Z,  Z' = -sinA*X + cosA*Z
'   RotZ(a): X' =  cosA*X - sinA*Y,  Y' =  sinA*X + cosA*Y
'   angle_rad is already in radians -- no conversion needed.
'
' Part 2 -- WCB at a given station (SMT_WCBatSta):
'   Reads from the SMT_Elements Named Range (same 8-col layout as SMT_Align).
'   Returns WCB (azimuth) in decimal degrees, normalised to [0, 360).
'   Dependency: SMT_FPMath (SMT_DegToRad, SMT_RadToDeg, SMT_NormalizeAngle).
' ============================================================

' ============================================================
' Part 1 -- 3-D rotation functions
' pts : 1-based Variant array, n rows x 3 cols (col1=X, col2=Y, col3=Z).
' angle_rad : rotation angle in radians (positive = CCW when viewed along +axis).
' Returns  : new Variant array same size as pts; original is NOT modified.
' ============================================================

Public Function SMT_RotX(pts As Variant, angle_rad As Double) As Variant
    ' Rotation around the X-axis by angle_rad (radians).
    ' X is unchanged; Y and Z rotate in the YZ plane.
    ' Y' =  cos(a)*Y - sin(a)*Z
    ' Z' =  sin(a)*Y + cos(a)*Z
    Dim nRows As Long, i As Long
    Dim cosA As Double, sinA As Double
    Dim result() As Double
    nRows = UBound(pts, 1)
    ReDim result(1 To nRows, 1 To 3)
    cosA = Cos(angle_rad)    ' computed once -- not inside the loop
    sinA = Sin(angle_rad)
    For i = 1 To nRows
        result(i, 1) = pts(i, 1)                              ' X unchanged
        result(i, 2) = cosA * pts(i, 2) - sinA * pts(i, 3)   ' Y'
        result(i, 3) = sinA * pts(i, 2) + cosA * pts(i, 3)   ' Z'
    Next i
    SMT_RotX = result
End Function

Public Function SMT_RotY(pts As Variant, angle_rad As Double) As Variant
    ' Rotation around the Y-axis by angle_rad (radians).
    ' Y is unchanged; X and Z rotate in the XZ plane.
    ' X' =  cos(a)*X + sin(a)*Z
    ' Z' = -sin(a)*X + cos(a)*Z
    Dim nRows As Long, i As Long
    Dim cosA As Double, sinA As Double
    Dim result() As Double
    nRows = UBound(pts, 1)
    ReDim result(1 To nRows, 1 To 3)
    cosA = Cos(angle_rad)
    sinA = Sin(angle_rad)
    For i = 1 To nRows
        result(i, 1) = cosA * pts(i, 1) + sinA * pts(i, 3)   ' X'
        result(i, 2) = pts(i, 2)                              ' Y unchanged
        result(i, 3) = -sinA * pts(i, 1) + cosA * pts(i, 3)  ' Z'
    Next i
    SMT_RotY = result
End Function

Public Function SMT_RotZ(pts As Variant, angle_rad As Double) As Variant
    ' Rotation around the Z-axis by angle_rad (radians).
    ' Z is unchanged; X and Y rotate in the XY plane.
    ' X' =  cos(a)*X - sin(a)*Y
    ' Y' =  sin(a)*X + cos(a)*Y
    Dim nRows As Long, i As Long
    Dim cosA As Double, sinA As Double
    Dim result() As Double
    nRows = UBound(pts, 1)
    ReDim result(1 To nRows, 1 To 3)
    cosA = Cos(angle_rad)
    sinA = Sin(angle_rad)
    For i = 1 To nRows
        result(i, 1) = cosA * pts(i, 1) - sinA * pts(i, 2)   ' X'
        result(i, 2) = sinA * pts(i, 1) + cosA * pts(i, 2)   ' Y'
        result(i, 3) = pts(i, 3)                              ' Z unchanged
    Next i
    SMT_RotZ = result
End Function

' ============================================================
' Part 2 -- WCB (azimuth, decimal degrees) at a given station
' ============================================================

Public Function SMT_WCBatSta(sta As Double, rng As Range) As Variant
    ' WCB (whole-circle bearing / azimuth) of the alignment centre-line tangent
    ' at station sta, in decimal degrees, normalised to [0, 360).
    '
    ' sta : arc distance along alignment (metres).
    ' rng : SMT_Elements Named Range -- 8 columns, no header:
    '         col1=StaStart  col2=StaEnd  col3=N  col4=E
    '         col5=Azimuth(decimal deg)   col6=Radius(signed m)
    '         col7=Type(T/C/SPIN/SPOUT)   col8=Transition
    '
    ' Type formulas (d = sta - StaStart, L = StaEnd - StaStart):
    '   T    : WCB = Azimuth  (constant tangent)
    '   C    : theta = d / R                       [rad]; R = signed radius
    '   SPIN : theta = d^2 / (2*R*L)               [rad]; clothoid k(s)=s/(R*L)
    '   SPOUT: theta = d/R - d^2 / (2*R*L)         [rad]; clothoid k_in=1/R -> k_out=0
    '   WCB  = Azimuth_deg + SMT_RadToDeg(theta), then normalised to [0, 360).
    '
    ' Sign: R>0 = right curve = azimuth increases; R<0 = left = azimuth decreases.
    ' Returns #VALUE! when sta is outside all elements.
    Dim nRows As Long, i As Long
    Dim staStart As Double, staEnd As Double
    Dim azDeg As Double, radius As Double
    Dim typStr As String
    Dim isLast As Boolean
    Dim d As Double, L As Double
    Dim theta_rad As Double, wcb_raw As Double

    nRows = rng.Rows.Count
    For i = 1 To nRows
        staStart = CDbl(rng.Cells(i, 1).Value)
        staEnd   = CDbl(rng.Cells(i, 2).Value)
        isLast   = (i = nRows)
        If sta >= staStart And (sta < staEnd Or (isLast And sta <= staEnd)) Then
            azDeg  = CDbl(rng.Cells(i, 5).Value)   ' entry azimuth at StaStart (degrees)
            radius = CDbl(rng.Cells(i, 6).Value)   ' signed radius (m); 0 = tangent
            typStr = CStr(rng.Cells(i, 7).Value)
            d = sta - staStart
            L = staEnd - staStart

            Select Case UCase(Trim(typStr))
                Case "T"
                    theta_rad = 0#   ' tangent: azimuth is constant

                Case "C"
                    ' Circular arc: uniform curvature k = 1/R
                    ' theta = d / R  (radians; sign follows R: +right, -left)
                    If radius <> 0# Then
                        theta_rad = d / radius
                    Else
                        theta_rad = 0#
                    End If

                Case "SPIN"
                    ' Clothoid spiral-in (tangent -> curve):
                    ' k(s) = s / (R*L),  theta = integral_0^d k ds = d^2 / (2*R*L)
                    If radius <> 0# And L <> 0# Then
                        theta_rad = (d * d) / (2# * radius * L)
                    Else
                        theta_rad = 0#
                    End If

                Case "SPOUT"
                    ' Clothoid spiral-out (curve -> tangent):
                    ' k(s) = 1/R - s/(R*L),  theta = d/R - d^2 / (2*R*L)
                    If radius <> 0# And L <> 0# Then
                        theta_rad = d / radius - (d * d) / (2# * radius * L)
                    Else
                        theta_rad = 0#
                    End If

                Case Else
                    theta_rad = 0#   ' unknown type: treat as tangent
            End Select

            wcb_raw = azDeg + SMT_RadToDeg(theta_rad)
            ' Normalise to [0, 360) via radians round-trip
            SMT_WCBatSta = SMT_RadToDeg(SMT_NormalizeAngle(SMT_DegToRad(wcb_raw)))
            Exit Function
        End If
    Next i

    SMT_WCBatSta = CVErr(xlErrValue)   ' sta outside all elements
End Function

' ============================================================
' Expected values -- verified against Python / manual calculation
'
' --- Part 1: rotation (angle_rad = pi/2 = 90 deg) ---
'   pts = [[1, 0, 0]]  (1-row, 3-col, 1-based)
'
'   SMT_RotZ(pts, pi/2)(1,1) = 0.0   X' = cos(90)*1 - sin(90)*0 = 0
'   SMT_RotZ(pts, pi/2)(1,2) = 1.0   Y' = sin(90)*1 + cos(90)*0 = 1
'   SMT_RotZ(pts, pi/2)(1,3) = 0.0   Z' = Z = 0
'   Result point: (0, 1, 0)  -- (1,0,0) rotated 90 deg CCW around Z-axis
'
'   SMT_RotX(pts, pi/2)(1,1) = 1.0   X' = X = 1
'   SMT_RotX(pts, pi/2)(1,2) = 0.0   Y' = cos(90)*0 - sin(90)*0 = 0
'   SMT_RotX(pts, pi/2)(1,3) = 0.0   Z' = sin(90)*0 + cos(90)*0 = 0
'   (X-axis point is unchanged by RotX, as expected)
'
' --- Part 2: WCB at station ---
'   Using the project dataset in SMT_Elements Named Range:
'   First element: sta=0, Type=T, Azimuth=90 deg (pointing East)
'
'   SMT_WCBatSta(0, SMT_Elements) = 90.0
'     d=0, theta=0 -> WCB = 90.0 + 0 = 90.0 deg
'
'   For a C element with R=300, az=90, sta=StaStart+157.08 (quarter circle):
'     theta = 157.08/300 = 0.5236 rad = 30.0 deg -> WCB = 120.0 deg
' ============================================================
