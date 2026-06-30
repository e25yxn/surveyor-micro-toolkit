"""Tests for smt.landxml.export_alignment_landxml."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from smt.builders.alignment_builder import build_alignment_from_pi
from smt.landxml import export_alignment_landxml

NS = 'http://www.landxml.org/schema/LandXML-1.2'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build(vertices):
    return build_alignment_from_pi(vertices)


def _parse(xml_str: str) -> ET.Element:
    return ET.fromstring(xml_str)


def _find_all(root: ET.Element, tag: str) -> list[ET.Element]:
    return root.findall(f'.//{{{NS}}}{tag}')


def _ne(el: ET.Element, tag: str) -> tuple[float, float]:
    text = el.find(f'{{{NS}}}{tag}').text
    n_str, e_str = text.split()
    return float(n_str), float(e_str)


# ---------------------------------------------------------------------------
# PI vertex helpers — construct vertex dicts directly (no CSV parsing needed)
# ---------------------------------------------------------------------------

def _verts_line():
    """Straight alignment: BP(0,0) → EP(0,100)."""
    return [
        {'n': 0.0,   'e': 0.0},
        {'n': 0.0,   'e': 100.0},
    ]


def _verts_curve():
    """Right-hand circular curve R=300: BP(0,0) → PI(0,500) → EP(-500,500)."""
    return [
        {'n':    0.0, 'e':   0.0},
        {'n':    0.0, 'e': 500.0, 'R': 300.0},
        {'n': -500.0, 'e': 500.0},
    ]


def _verts_spiral():
    """Right-hand curve with symmetric clothoid spirals Ls=60, R=400."""
    return [
        {'n':    0.0, 'e':   0.0},
        {'n':    0.0, 'e': 500.0, 'R': 400.0, 'Ls': 60.0},
        {'n': -500.0, 'e': 500.0},
    ]


def _verts_angle_point():
    """Angle point (R=0 / no R key): BP(0,0) → IP(0,500) → EP(500,1000)."""
    return [
        {'n':   0.0, 'e':   0.0},
        {'n':   0.0, 'e': 500.0},   # no 'R' key → angle point
        {'n': 500.0, 'e': 1000.0},
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTangentOnly:
    def test_produces_one_line_tag(self):
        xml = export_alignment_landxml(_build(_verts_line()))
        root = _parse(xml)
        assert len(_find_all(root, 'Line')) == 1

    def test_no_curve_or_spiral(self):
        xml = export_alignment_landxml(_build(_verts_line()))
        root = _parse(xml)
        assert _find_all(root, 'Curve')  == []
        assert _find_all(root, 'Spiral') == []

    def test_start_end_coords(self):
        xml = export_alignment_landxml(_build(_verts_line()))
        root = _parse(xml)
        line = _find_all(root, 'Line')[0]
        sn, se = _ne(line, 'Start')
        en, ee = _ne(line, 'End')
        assert math.isclose(sn, 0.0, abs_tol=1e-6)
        assert math.isclose(se, 0.0, abs_tol=1e-6)
        assert math.isclose(en, 0.0, abs_tol=1e-6)
        assert math.isclose(ee, 100.0, abs_tol=1e-3)

    def test_xml_declaration_present(self):
        xml = export_alignment_landxml(_build(_verts_line()))
        assert xml.startswith('<?xml version="1.0" encoding="utf-8"?>')

    def test_landxml_namespace(self):
        xml = export_alignment_landxml(_build(_verts_line()))
        assert 'LandXML-1.2' in xml

    def test_alignment_name_default(self):
        xml = export_alignment_landxml(_build(_verts_line()))
        root = _parse(xml)
        align = _find_all(root, 'Alignment')[0]
        assert align.get('name') == 'alignment'

    def test_alignment_name_custom(self):
        xml = export_alignment_landxml(_build(_verts_line()), name='MyRoad')
        root = _parse(xml)
        align = _find_all(root, 'Alignment')[0]
        assert align.get('name') == 'MyRoad'


class TestSimpleCurve:
    def test_curve_tag_present(self):
        xml = export_alignment_landxml(_build(_verts_curve()))
        root = _parse(xml)
        assert len(_find_all(root, 'Curve')) == 1

    def test_curve_has_center_tag(self):
        xml = export_alignment_landxml(_build(_verts_curve()))
        root = _parse(xml)
        curve = _find_all(root, 'Curve')[0]
        assert curve.find(f'{{{NS}}}Center') is not None

    def test_center_at_radius_from_start(self):
        xml = export_alignment_landxml(_build(_verts_curve()))
        root = _parse(xml)
        curve = _find_all(root, 'Curve')[0]
        cn, ce = _ne(curve, 'Center')
        sn, se = _ne(curve, 'Start')
        assert math.isclose(math.hypot(cn - sn, ce - se), 300.0, abs_tol=1e-3)

    def test_center_at_radius_from_end(self):
        xml = export_alignment_landxml(_build(_verts_curve()))
        root = _parse(xml)
        curve = _find_all(root, 'Curve')[0]
        cn, ce = _ne(curve, 'Center')
        en, ee = _ne(curve, 'End')
        assert math.isclose(math.hypot(cn - en, ce - ee), 300.0, abs_tol=1e-3)

    def test_rotation_right(self):
        xml = export_alignment_landxml(_build(_verts_curve()))
        root = _parse(xml)
        curve = _find_all(root, 'Curve')[0]
        assert curve.get('rot') == 'right'

    def test_radius_attribute(self):
        xml = export_alignment_landxml(_build(_verts_curve()))
        root = _parse(xml)
        curve = _find_all(root, 'Curve')[0]
        assert math.isclose(float(curve.get('radius')), 300.0, abs_tol=1e-6)

    def test_left_turn_rotation(self):
        """Curve that goes left must have rot='left'."""
        verts = [
            {'n':    0.0, 'e':   0.0},
            {'n':    0.0, 'e': 500.0, 'R': 300.0},
            {'n':  500.0, 'e': 500.0},   # left deflection from East
        ]
        xml = export_alignment_landxml(_build(verts))
        root = _parse(xml)
        curve = _find_all(root, 'Curve')[0]
        assert curve.get('rot') == 'left'


class TestSpiralIn:
    def test_spiral_tag_present(self):
        xml = export_alignment_landxml(_build(_verts_spiral()))
        root = _parse(xml)
        assert len(_find_all(root, 'Spiral')) >= 1

    def test_spin_radius_start_is_inf(self):
        xml = export_alignment_landxml(_build(_verts_spiral()))
        root = _parse(xml)
        spin = next(
            s for s in _find_all(root, 'Spiral')
            if s.get('spiType') == 'toCurve'
        )
        assert spin.get('radiusStart') == 'INF'

    def test_spin_radius_end_correct(self):
        xml = export_alignment_landxml(_build(_verts_spiral()))
        root = _parse(xml)
        spin = next(
            s for s in _find_all(root, 'Spiral')
            if s.get('spiType') == 'toCurve'
        )
        assert math.isclose(float(spin.get('radiusEnd')), 400.0, abs_tol=1e-6)

    def test_spin_spi_type(self):
        xml = export_alignment_landxml(_build(_verts_spiral()))
        root = _parse(xml)
        spirals = _find_all(root, 'Spiral')
        spi_types = {s.get('spiType') for s in spirals}
        assert 'toCurve' in spi_types

    def test_spout_spi_type(self):
        xml = export_alignment_landxml(_build(_verts_spiral()))
        root = _parse(xml)
        spirals = _find_all(root, 'Spiral')
        spi_types = {s.get('spiType') for s in spirals}
        assert 'fromCurve' in spi_types

    def test_spiral_type_clothoid(self):
        xml = export_alignment_landxml(_build(_verts_spiral()))
        root = _parse(xml)
        for spiral in _find_all(root, 'Spiral'):
            assert spiral.get('type') == 'clothoid'

    def test_spiral_length(self):
        xml = export_alignment_landxml(_build(_verts_spiral()))
        root = _parse(xml)
        spin = next(
            s for s in _find_all(root, 'Spiral')
            if s.get('spiType') == 'toCurve'
        )
        assert math.isclose(float(spin.get('length')), 60.0, abs_tol=1e-3)

    def test_spiral_has_start_end_tags(self):
        xml = export_alignment_landxml(_build(_verts_spiral()))
        root = _parse(xml)
        for spiral in _find_all(root, 'Spiral'):
            assert spiral.find(f'{{{NS}}}Start') is not None
            assert spiral.find(f'{{{NS}}}End') is not None
            assert spiral.find(f'{{{NS}}}Center') is None


class TestAnglePoint:
    def test_no_crash(self):
        xml = export_alignment_landxml(_build(_verts_angle_point()))
        assert xml is not None

    def test_no_curve_tag(self):
        xml = export_alignment_landxml(_build(_verts_angle_point()))
        root = _parse(xml)
        assert _find_all(root, 'Curve') == []

    def test_no_spiral_tag(self):
        xml = export_alignment_landxml(_build(_verts_angle_point()))
        root = _parse(xml)
        assert _find_all(root, 'Spiral') == []

    def test_only_line_tags(self):
        xml = export_alignment_landxml(_build(_verts_angle_point()))
        root = _parse(xml)
        assert len(_find_all(root, 'Line')) >= 1

    def test_valid_xml(self):
        xml = export_alignment_landxml(_build(_verts_angle_point()))
        _parse(xml)   # raises if not well-formed
