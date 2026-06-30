Attribute VB_Name = "SMT_Align"
Option Explicit

' ============================================================
' SMT_Align.bas  --  VBA port of src/smt/alignment.py
' SMT (Surveyor Micro Toolkit) -- Horizontal alignment lookup
'
' Named Range SMT_Elements layout (8 columns per row, no header):
'   col1=StaStart  col2=StaEnd  col3=N       col4=E
'   col5=Azimuth(decimal degrees)  col6=Radius(signed metres)
'   col7=Type(T/C/SPIN/SPOUT)     col8=Transition(CLOTHOID/BLOSS/COSINE/SINE)
'
' Sign convention:
'   offset: +right of travel / -left.  radius: +right curve / -left curve.
'   k = 1/R (signed curvature).
'   Azimuth in col5 is decimal degrees; converted to radians immediately on read.
' Dependency: SMT_FPMath and SMT_WCB modules must be imported in the same workbook.
' ============================================================

Private Const SMT_SPIRAL_STEPS As Long = 48  ' Simpson intervals (must be even)
Private Const SMT_STA_TOL As Double = 0.0001 ' station range tolerance (metres)

' ============================================================
' Private: atan2(y, x)
' Duplicated here because SMT_WCB version is Private.
' Returns angle of vector (x, y) from +x axis, range (-pi, pi].
' ============================================================

Private Function SMT_Atan2(y As Double, x As Double) As Double
    Dim PI As Double
    PI = SMT_Pi()
    If x > 0# Then
        SMT_Atan2 = Atn(y / x)
    ElseIf x < 0# And y >= 0# Then
        SMT_Atan2 = Atn(y / x) + PI
    ElseIf x < 0# And y < 0# Then
        SMT_Atan2 = Atn(y / x) - PI
    ElseIf x = 0# And y > 0# Then
        SMT_Atan2 = PI / 2#
    ElseIf x = 0# And y < 0# Then
        SMT_Atan2 = -(PI / 2#)
    Else
        SMT_Atan2 = 0#  ' coincident: undefined; matches Python math.atan2(0,0)
    End If
End Function

' ============================================================
' Private: curvature shape integral F(tau) for spiral transitions
' F(tau) = integral_0^tau f(u) du
' f defines how curvature changes with normalised arc position tau = s/L.
' All shapes satisfy f(0)=0, f(1)=1, integral_0^1 f = 0.5.
' Unit: dimensionless (tau in [0,1]).
' ============================================================

Private Function SMT_ShapeIntegral(transition As String, tau As Double) As Double
    Dim PI As Double
    PI = SMT_Pi()
    Select Case UCase(Trim(transition))
        Case "BLOSS"
            SMT_ShapeIntegral = tau ^ 3# - tau ^ 4# / 2#
        Case "COSINE"
            SMT_ShapeIntegral = tau / 2# - Sin(PI * tau) / (2# * PI)
        Case "SINE"
            SMT_ShapeIntegral = tau ^ 2# / 2# - (1# - Cos(2# * PI * tau)) / (4# * PI ^ 2#)
        Case Else  ' CLOTHOID (default): f(tau)=tau -> F(tau)=tau^2/2
            SMT_ShapeIntegral = tau ^ 2# / 2#
    End Select
End Function

' ============================================================
' Private: accumulated turning angle at arc distance s from element start
' theta(s) = k_in*s + (k_out - k_in)*L*F(s/L)
' Unit: rad.  Sign: positive = right turn (azimuth increases clockwise).
' ============================================================

Private Function SMT_TurningAngle(kIn As Double, kOut As Double, L As Double, _
                                   transition As String, s As Double) As Double
    Dim tau As Double
    If L = 0# Then
        SMT_TurningAngle = kIn * s
    Else
        tau = s / L
        SMT_TurningAngle = kIn * s + (kOut - kIn) * L * SMT_ShapeIntegral(transition, tau)
    End If
End Function

' ============================================================
' Private: resolve signed curvatures k_in, k_out from Type + Radius
' SPIN : k_in=0 (tangent entry),  k_out=1/R (circular exit)
' SPOUT: k_in=1/R (circular entry), k_out=0 (tangent exit)
' C    : k_in=k_out=1/R
' T    : k_in=k_out=0
' Unit: radius in metres -> k in rad/m.
' ============================================================

Private Sub SMT_GetCurvatures(typStr As String, radius As Double, _
                               ByRef kIn As Double, ByRef kOut As Double)
    Dim k As Double
    If radius = 0# Then
        k = 0#
    Else
        k = 1# / radius
    End If
    Select Case UCase(Trim(typStr))
        Case "SPIN"
            kIn = 0#
            kOut = k
        Case "SPOUT"
            kIn = k
            kOut = 0#
        Case "C"
            kIn = k
            kOut = k
        Case Else  ' T or unknown: tangent
            kIn = 0#
            kOut = 0#
    End Select
End Sub

' ============================================================
' Private: position and tangent azimuth at arc distance d from element start
' Returns Variant Array: (0)=N  (1)=E  (2)=tangentAzimuth(rad)
'
' Tangent (k_in=k_out=0): straight line.
' Circular (k_in=k_out=k): chord-and-half-angle formula.
' Spiral (k_in<>k_out): Simpson integration of (cos theta, sin theta),
'   48 intervals -- matches Python oracle exactly for all 4 transition shapes.
' ============================================================

Private Function SMT_PointOnElement(n0 As Double, e0 As Double, az0 As Double, _
                                     kIn As Double, kOut As Double, L As Double, _
                                     transition As String, d As Double) As Variant
    Dim res(2) As Double
    Dim k As Double, theta As Double, chord As Double, chordAz As Double
    Dim nSeg As Long, i As Long, w As Long
    Dim h As Double, sumX As Double, sumY As Double
    Dim s As Double, th As Double
    Dim ca As Double, sa As Double, x As Double, y As Double

    If kIn = 0# And kOut = 0# Then
        ' Tangent: straight line along entry azimuth
        res(0) = n0 + d * Cos(az0)
        res(1) = e0 + d * Sin(az0)
        res(2) = az0

    ElseIf kIn = kOut Then
        ' Circular: constant curvature; chord bisects the arc angle
        k = kIn
        theta = k * d
        chord = (2# / Abs(k)) * Abs(Sin(theta / 2#))
        chordAz = az0 + theta / 2#
        res(0) = n0 + chord * Cos(chordAz)
        res(1) = e0 + chord * Sin(chordAz)
        res(2) = SMT_NormalizeAngle(az0 + theta)

    Else
        ' Spiral: Simpson integration in local frame (x=along entry tangent, y=left)
        nSeg = SMT_SPIRAL_STEPS
        h = d / CDbl(nSeg)
        sumX = 0#
        sumY = 0#
        For i = 0 To nSeg
            s = CDbl(i) * h
            th = SMT_TurningAngle(kIn, kOut, L, transition, s)
            If i = 0 Or i = nSeg Then
                w = 1
            ElseIf (i Mod 2) = 1 Then
                w = 4
            Else
                w = 2
            End If
            sumX = sumX + CDbl(w) * Cos(th)
            sumY = sumY + CDbl(w) * Sin(th)
        Next i
        x = sumX * h / 3#
        y = sumY * h / 3#
        ca = Cos(az0)
        sa = Sin(az0)
        res(0) = n0 + x * ca - y * sa
        res(1) = e0 + x * sa + y * ca
        res(2) = SMT_NormalizeAngle(az0 + SMT_TurningAngle(kIn, kOut, L, transition, d))
    End If

    SMT_PointOnElement = res
End Function

' ============================================================
' Private: project external point (pN, pE) onto one element
' Returns Variant Array: (0)=sta  (1)=offset  (2)=d  (3)=inRange(1/0)
' offset: +right of travel / -left.
'
' Tangent  : dot-product foot.
' Circular : angle swept from centre of curvature.
' Spiral   : bisection on g(s) = (P - Q(s)) . tangentDir(s) = 0 (50 iterations).
' ============================================================

Private Function SMT_ProjectOnElement(staStart As Double, staEnd As Double, _
                                       n0 As Double, e0 As Double, az0 As Double, _
                                       kIn As Double, kOut As Double, L As Double, _
                                       transition As String, _
                                       pN As Double, pE As Double) As Variant
    Dim res(3) As Double
    Dim dN As Double, dE As Double, ca As Double, sa As Double
    Dim d As Double, off As Double
    Dim k As Double, R As Double
    Dim centerN As Double, centerE As Double, rho As Double
    Dim phi0 As Double, phiP As Double, dArc As Double
    Dim g0 As Double, gL As Double, gMid As Double, gLo As Double
    Dim lo As Double, hi As Double, mid As Double
    Dim iter As Long
    Dim pt As Variant
    Dim sN As Double, sE As Double, sAz As Double, sStar As Double
    Dim inRange As Boolean

    If kIn = 0# And kOut = 0# Then
        ' Tangent: foot via dot-product projection onto the infinite line
        dN = pN - n0
        dE = pE - e0
        ca = Cos(az0)
        sa = Sin(az0)
        d = dN * ca + dE * sa
        off = -dN * sa + dE * ca
        res(0) = staStart + d
        res(1) = off
        res(2) = d
        If d >= -SMT_STA_TOL And d <= L + SMT_STA_TOL Then
            res(3) = 1#
        Else
            res(3) = 0#
        End If

    ElseIf kIn = kOut Then
        ' Circular: angle swept from centre of curvature
        ' centre = (n - R*sin(az), e + R*cos(az))  -- perpendicular right for k>0
        k = kIn
        R = 1# / k
        centerN = n0 - R * Sin(az0)
        centerE = e0 + R * Cos(az0)
        rho = Sqr((pN - centerN) ^ 2# + (pE - centerE) ^ 2#)
        phi0 = SMT_Atan2(e0 - centerE, n0 - centerN)
        phiP = SMT_Atan2(pE - centerE, pN - centerN)
        dArc = SMT_AngleDiff(phiP, phi0) / k
        If k > 0# Then
            off = Abs(R) - rho   ' +inside arc (right side) for right curve
        Else
            off = -(Abs(R) - rho)
        End If
        res(0) = staStart + dArc
        res(1) = off
        res(2) = dArc
        If dArc >= -SMT_STA_TOL And dArc <= L + SMT_STA_TOL Then
            res(3) = 1#
        Else
            res(3) = 0#
        End If

    Else
        ' Spiral: bisection on g(s) = (P - Q(s)) . tangentDir(s) = 0
        pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transition, 0#)
        g0 = (pN - pt(0)) * Cos(pt(2)) + (pE - pt(1)) * Sin(pt(2))
        pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transition, L)
        gL = (pN - pt(0)) * Cos(pt(2)) + (pE - pt(1)) * Sin(pt(2))

        inRange = (g0 = 0#) Or (gL = 0#) Or ((g0 > 0#) <> (gL > 0#))

        If inRange Then
            lo = 0#
            hi = L
            gLo = g0
            For iter = 1 To 50
                mid = (lo + hi) / 2#
                pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transition, mid)
                gMid = (pN - pt(0)) * Cos(pt(2)) + (pE - pt(1)) * Sin(pt(2))
                If (gLo > 0#) = (gMid > 0#) Then
                    lo = mid
                    gLo = gMid
                Else
                    hi = mid
                End If
            Next iter
            sStar = (lo + hi) / 2#
        Else
            If Abs(g0) < Abs(gL) Then
                sStar = 0#
            Else
                sStar = L
            End If
        End If

        pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transition, sStar)
        sN = pt(0)
        sE = pt(1)
        sAz = pt(2)
        off = -(pN - sN) * Sin(sAz) + (pE - sE) * Cos(sAz)

        res(0) = staStart + sStar
        res(1) = off
        res(2) = sStar
        If inRange Then
            res(3) = 1#
        Else
            res(3) = 0#
        End If
    End If

    SMT_ProjectOnElement = res
End Function

' ============================================================
' Private: forward solve -- sta + offset -> (N, E) across all elements
' Returns Variant Array (0)=N  (1)=E, or CVErr(xlErrValue) if sta out of range.
' ============================================================

Private Function SMT_SolveForward(sta As Double, offset As Double, _
                                   rng As Range) As Variant
    Dim nRows As Long, i As Long
    Dim staStart As Double, staEnd As Double
    Dim n0 As Double, e0 As Double
    Dim azDeg As Double, az0 As Double
    Dim radius As Double, typStr As String, transStr As String
    Dim kIn As Double, kOut As Double, L As Double, d As Double
    Dim pt As Variant, offAz As Double
    Dim res(1) As Double

    nRows = rng.Rows.Count
    For i = 1 To nRows
        staStart = CDbl(rng.Cells(i, 1).Value)
        staEnd = CDbl(rng.Cells(i, 2).Value)
        If sta >= staStart - SMT_STA_TOL And sta <= staEnd + SMT_STA_TOL Then
            n0 = CDbl(rng.Cells(i, 3).Value)
            e0 = CDbl(rng.Cells(i, 4).Value)
            azDeg = CDbl(rng.Cells(i, 5).Value)
            az0 = SMT_DegToRad(azDeg)  ' degrees -> radians immediately on read
            radius = CDbl(rng.Cells(i, 6).Value)
            typStr = CStr(rng.Cells(i, 7).Value)
            transStr = CStr(rng.Cells(i, 8).Value)
            If Len(Trim(transStr)) = 0 Then transStr = "CLOTHOID"
            kIn = 0#
            kOut = 0#
            SMT_GetCurvatures typStr, radius, kIn, kOut
            L = staEnd - staStart
            d = sta - staStart
            If d < 0# Then d = 0#  ' clamp tolerance overshoot at element start
            pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transStr, d)
            If offset <> 0# Then
                offAz = SMT_NormalizeAngle(pt(2) + SMT_Pi() / 2#)
                res(0) = pt(0) + offset * Cos(offAz)
                res(1) = pt(1) + offset * Sin(offAz)
            Else
                res(0) = pt(0)
                res(1) = pt(1)
            End If
            SMT_SolveForward = res
            Exit Function
        End If
    Next i
    SMT_SolveForward = CVErr(xlErrValue)
End Function

' ============================================================
' Private: inverse solve -- (N, E) -> (sta, offset) across all elements
' Iterates every element; keeps in-range projection with minimum |offset|.
' Returns Variant Array (0)=sta  (1)=offset, or CVErr(xlErrValue) if no projection.
' ============================================================

Private Function SMT_SolveInverse(pN As Double, pE As Double, _
                                   rng As Range) As Variant
    Dim nRows As Long, i As Long
    Dim staStart As Double, staEnd As Double
    Dim n0 As Double, e0 As Double
    Dim azDeg As Double, az0 As Double
    Dim radius As Double, typStr As String, transStr As String
    Dim kIn As Double, kOut As Double, L As Double
    Dim pr As Variant
    Dim bestSta As Double, bestOff As Double, hasBest As Boolean
    Dim res(1) As Double

    hasBest = False
    nRows = rng.Rows.Count
    For i = 1 To nRows
        staStart = CDbl(rng.Cells(i, 1).Value)
        staEnd = CDbl(rng.Cells(i, 2).Value)
        n0 = CDbl(rng.Cells(i, 3).Value)
        e0 = CDbl(rng.Cells(i, 4).Value)
        azDeg = CDbl(rng.Cells(i, 5).Value)
        az0 = SMT_DegToRad(azDeg)  ' degrees -> radians immediately on read
        radius = CDbl(rng.Cells(i, 6).Value)
        typStr = CStr(rng.Cells(i, 7).Value)
        transStr = CStr(rng.Cells(i, 8).Value)
        If Len(Trim(transStr)) = 0 Then transStr = "CLOTHOID"
        kIn = 0#
        kOut = 0#
        SMT_GetCurvatures typStr, radius, kIn, kOut
        L = staEnd - staStart
        pr = SMT_ProjectOnElement(staStart, staEnd, n0, e0, az0, _
                                   kIn, kOut, L, transStr, pN, pE)
        If pr(3) = 1# Then
            If Not hasBest Or Abs(pr(1)) < Abs(bestOff) Then
                bestSta = pr(0)
                bestOff = pr(1)
                hasBest = True
            End If
        End If
    Next i

    If hasBest Then
        res(0) = bestSta
        res(1) = bestOff
        SMT_SolveInverse = res
    Else
        SMT_SolveInverse = CVErr(xlErrValue)
    End If
End Function

' ============================================================
' Public: Forward -- station + offset -> Northing
' ============================================================

Public Function SMT_StaToN(sta As Double, offset As Double, rng As Range) As Variant
    ' Forward: station + perpendicular offset -> Northing (metres).
    ' sta   : arc distance along alignment centre line (metres).
    ' offset: +right of travel / -left (metres); 0 for centre line.
    ' rng   : SMT_Elements Named Range -- 8 columns, no header row.
    '         col5 Azimuth must be decimal degrees; converted to rad internally.
    ' Returns #VALUE! when sta is outside the alignment.
    Dim pt As Variant
    pt = SMT_SolveForward(sta, offset, rng)
    If IsError(pt) Then
        SMT_StaToN = pt
    Else
        SMT_StaToN = pt(0)
    End If
End Function

' ============================================================
' Public: Forward -- station + offset -> Easting
' ============================================================

Public Function SMT_StaToE(sta As Double, offset As Double, rng As Range) As Variant
    ' Forward: station + perpendicular offset -> Easting (metres).
    ' sta   : arc distance along alignment centre line (metres).
    ' offset: +right of travel / -left (metres); 0 for centre line.
    ' rng   : SMT_Elements Named Range -- 8 columns, no header row.
    '         col5 Azimuth must be decimal degrees; converted to rad internally.
    ' Returns #VALUE! when sta is outside the alignment.
    Dim pt As Variant
    pt = SMT_SolveForward(sta, offset, rng)
    If IsError(pt) Then
        SMT_StaToE = pt
    Else
        SMT_StaToE = pt(1)
    End If
End Function

' ============================================================
' Public: Inverse -- N, E -> Station
' ============================================================

Public Function SMT_CoordToSta(n As Double, e As Double, rng As Range) As Variant
    ' Inverse: grid coordinate -> closest alignment station (metres).
    ' n, e  : Northing and Easting (metres).
    ' rng   : SMT_Elements Named Range -- 8 columns, no header row.
    '         col5 Azimuth must be decimal degrees; converted to rad internally.
    ' Projects onto every element; returns station where |offset| is minimum.
    ' Returns #VALUE! when the point projects outside all elements.
    Dim pr As Variant
    pr = SMT_SolveInverse(n, e, rng)
    If IsError(pr) Then
        SMT_CoordToSta = pr
    Else
        SMT_CoordToSta = pr(0)
    End If
End Function

' ============================================================
' Public: Inverse -- N, E -> Offset
' ============================================================

Public Function SMT_CoordToOffset(n As Double, e As Double, rng As Range) As Variant
    ' Inverse: grid coordinate -> signed perpendicular offset from centre line (metres).
    ' n, e  : Northing and Easting (metres).
    ' rng   : SMT_Elements Named Range -- 8 columns, no header row.
    '         col5 Azimuth must be decimal degrees; converted to rad internally.
    ' offset: +right of travel / -left.
    ' Returns #VALUE! when the point projects outside all elements.
    Dim pr As Variant
    pr = SMT_SolveInverse(n, e, rng)
    If IsError(pr) Then
        SMT_CoordToOffset = pr
    Else
        SMT_CoordToOffset = pr(1)
    End If
End Function

' ============================================================
' Expected values -- verified against Python (src/smt/alignment.py)
' using the project dataset loaded into the SMT_Elements Named Range:
'
'   SMT_StaToN(0, 0, SMT_Elements)                  = 1568000.0
'   SMT_StaToE(519.615, 0, SMT_Elements)             = 678519.615
'   SMT_CoordToSta(1568000, 678000, SMT_Elements)    = 0.0
'   SMT_CoordToOffset(1568000, 678000, SMT_Elements) = 0.0
' ============================================================
