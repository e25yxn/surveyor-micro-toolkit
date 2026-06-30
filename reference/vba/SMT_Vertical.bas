Attribute VB_Name = "SMT_Vertical"
Option Explicit

' ============================================================
' SMT_Vertical.bas  --  VBA port of src/smt/vertical.py
' SMT (Surveyor Micro Toolkit) -- Vertical alignment (profile) lookup
'
' Named Range SMT_Vertical layout (7 columns per row, no header):
'   col1=StaStart   col2=StaEnd    col3=Level (elevation at StaStart, metres)
'   col4=G1 (entry grade %)        col5=G2 (exit grade %)
'   col6=LVC  (VC length metres; 0 = tangent)
'   col7=LVC2 (2nd arm metres for asymmetric/compound VC; 0 = symmetric)
'
' Three segment types:
'   LVC=0              : tangent grade
'   LVC>0, LVC2=0      : symmetric parabolic VC (single-arm parabola)
'   LVC>0, LVC2>0      : asymmetric (compound, unequal-tangent) VC -- two parabolas
'                        joined at StaStart+LVC; middle ordinate shared.
'
' Grade units: percent (%).  Elevation units: metres (same as input).
' No dependency on other SMT modules.
' ============================================================

' ============================================================
' Public: Elevation at station
' ============================================================

Public Function SMT_Elevation(sta As Double, rng As Range) As Variant
    ' Elevation (metres) at station sta along the vertical alignment.
    ' sta : arc distance along alignment (metres).
    ' rng : SMT_Vertical Named Range -- 7 columns, no header row.
    '
    ' Station range rule (matches Python oracle):
    '   Interior segments: sta in [StaStart, StaEnd)  -- exclusive at end
    '   Last segment     : sta in [StaStart, StaEnd]  -- inclusive at end
    ' This prevents a junction station from matching two segments at once.
    '
    ' Returns #VALUE! when sta is outside all segments.
    Dim nRows As Long
    Dim i As Long
    Dim staStart As Double, staEnd As Double
    Dim level As Double, g1 As Double, g2 As Double
    Dim lvc As Double, lvc2 As Double
    Dim isLast As Boolean

    nRows = rng.Rows.Count
    For i = 1 To nRows
        staStart = CDbl(rng.Cells(i, 1).Value)
        staEnd   = CDbl(rng.Cells(i, 2).Value)
        isLast   = (i = nRows)
        If sta >= staStart And (sta < staEnd Or (isLast And sta <= staEnd)) Then
            level = CDbl(rng.Cells(i, 3).Value)
            g1    = CDbl(rng.Cells(i, 4).Value)    ' entry grade (%)
            g2    = CDbl(rng.Cells(i, 5).Value)    ' exit grade  (%)
            lvc   = CDbl(rng.Cells(i, 6).Value)    ' VC length (metres); 0 = tangent
            lvc2  = CDbl(rng.Cells(i, 7).Value)    ' 2nd arm (metres); 0 = symmetric
            SMT_Elevation = SMT_ElevAt(sta, staStart, staEnd, level, g1, g2, lvc, lvc2)
            Exit Function
        End If
    Next i

    SMT_Elevation = CVErr(xlErrValue)   ' sta outside all segments
End Function

' ============================================================
' Private: elevation within one segment
' ============================================================

Private Function SMT_ElevAt(sta As Double, _
                             staStart As Double, staEnd As Double, _
                             level As Double, g1 As Double, g2 As Double, _
                             lvc As Double, lvc2 As Double) As Double
    ' Elevation formula dispatcher for one vertical segment.
    ' sta     : target station (metres).
    ' staStart: segment PVC station (metres).
    ' staEnd  : segment end station (metres).
    ' level   : elevation at PVC / StaStart (metres).
    ' g1      : entry grade (%).  g2: exit grade (%).
    ' lvc     : vertical curve length (metres); 0 = tangent.
    ' lvc2    : second arm for asymmetric VC (metres); 0 = symmetric.
    Dim lx As Double   ' arc distance from StaStart (metres)
    lx = sta - staStart

    If lvc = 0# Then
        SMT_ElevAt = SMT_ElevTangent(level, g1, lx)
    ElseIf lvc2 = 0# Then
        SMT_ElevAt = SMT_ElevSymVC(level, g1, g2, lvc, lx)
    Else
        SMT_ElevAt = SMT_ElevAsymVC(sta, staStart, staEnd, level, g1, g2, lvc, lvc2)
    End If
End Function

' ============================================================
' Private: tangent grade elevation
' ============================================================

Private Function SMT_ElevTangent(level As Double, g1 As Double, _
                                  lx As Double) As Double
    ' Tangent grade: elevation = level + (G1/100) * lx.
    ' level: elevation at segment start (metres).
    ' g1   : grade (%).  lx: arc distance from start (metres).
    SMT_ElevTangent = level + (g1 / 100#) * lx
End Function

' ============================================================
' Private: symmetric (single-arm) parabolic VC
' ============================================================

Private Function SMT_ElevSymVC(level As Double, g1 As Double, g2 As Double, _
                                lvc As Double, lx As Double) As Double
    ' Symmetric parabolic VC:
    '   base      = level + (G1/100)*lx             [tangent grade from PVC]
    '   elevation = base + (G2-G1) / (200*LVC) * lx^2
    '
    ' level: PVC elevation (metres).  g1,g2: entry/exit grades (%).
    ' lvc  : total VC length (metres).  lx: arc distance from PVC (metres).
    Dim base As Double
    base = level + (g1 / 100#) * lx
    SMT_ElevSymVC = base + (g2 - g1) / (200# * lvc) * lx * lx
End Function

' ============================================================
' Private: asymmetric (compound, unequal-tangent) parabolic VC
' ============================================================

Private Function SMT_ElevAsymVC(sta As Double, _
                                 staStart As Double, staEnd As Double, _
                                 level As Double, g1 As Double, g2 As Double, _
                                 lvc As Double, lvc2 As Double) As Double
    ' Asymmetric (compound) VC: two parabolas joined at StaStart+LVC (VPI station).
    '
    ' l1     = LVC   (first arm, PVC to VPI, metres)
    ' l2     = LVC2  (second arm, VPI to PVT, metres)
    ' e      = l1*l2/(200*(l1+l2)) * (G2-G1)   [middle ordinate at VPI, metres; signed]
    '
    ' Arm 1 (lx <= l1), PVC to VPI:
    '   base      = level + (G1/100)*lx
    '   elevation = base + e*(lx/l1)^2
    '
    ' Arm 2 (lx > l1), VPI to PVT:
    '   lev_pvt   = level + (G1/100)*l1 + (G2/100)*l2    [PVT elevation]
    '   lx2       = StaEnd - sta                          [arc distance back from PVT]
    '   elevation = lev_pvt - (G2/100)*lx2 + e*(lx2/l2)^2
    '
    ' level: PVC elevation (metres).  g1,g2: entry/exit grades (%).
    ' lvc,lvc2: first and second arm lengths (metres).
    Dim l1 As Double, l2 As Double, lTotal As Double
    Dim e As Double
    Dim lx As Double, lx2 As Double
    Dim base As Double, levPVT As Double

    l1 = lvc
    l2 = lvc2
    lTotal = l1 + l2
    e = (l1 * l2) / (200# * lTotal) * (g2 - g1)  ' middle ordinate (metres)
    lx = sta - staStart

    If lx <= l1 Then
        ' Arm 1: PVC -> VPI
        base = level + (g1 / 100#) * lx
        SMT_ElevAsymVC = base + e * (lx / l1) * (lx / l1)
    Else
        ' Arm 2: VPI -> PVT (computed backwards from PVT for symmetry)
        levPVT = level + (g1 / 100#) * l1 + (g2 / 100#) * l2
        lx2 = staEnd - sta
        SMT_ElevAsymVC = levPVT - (g2 / 100#) * lx2 + e * (lx2 / l2) * (lx2 / l2)
    End If
End Function

' ============================================================
' Expected values -- verified against Python (src/smt/vertical.py)
' using the golden dataset (tests/golden/tables.json "vtable"):
'
' Segment layout (col1-col7):
'   [0]  sta=0-1100      level=100     g1=1.5   g2=1.5    lvc=0   lvc2=0  (tangent)
'   [1]  sta=1100-1300   level=116.5   g1=1.5   g2=-1.125 lvc=200 lvc2=0  (sym VC)
'   [2]  sta=1300-2700   level=116.875 g1=-1.125 g2=-1.125 lvc=0  lvc2=0  (tangent)
'   [3]  sta=2700-3000   level=101.125 g1=-1.125 g2=0.7059 lvc=100 lvc2=200 (asym VC)
'
'   SMT_Elevation(0,    SMT_Vertical) = 100.0          (tangent)
'   SMT_Elevation(100,  SMT_Vertical) = 101.5          (tangent)
'   SMT_Elevation(1200, SMT_Vertical) = 117.34375       (symmetric VC, mid-curve)
'   SMT_Elevation(1300, SMT_Vertical) = 116.875         (symmetric VC, exit = seg[2] start)
'   SMT_Elevation(2750, SMT_Vertical) = 100.715075      (asymmetric VC, arm 1)
'   SMT_Elevation(2900, SMT_Vertical) = 100.858475      (asymmetric VC, arm 2)
'   SMT_Elevation(3000, SMT_Vertical) = 101.4118        (asymmetric VC, PVT = seg[4] start)
' ============================================================
