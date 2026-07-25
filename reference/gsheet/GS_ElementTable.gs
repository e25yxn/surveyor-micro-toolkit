/**
 * GS_ElementTable — flattens GS_AlignmentBuilder.buildFromPI()'s `elements`
 * array into Table-1 rows for Sheet export.
 * Mirrors src/smt/cli.py::_run_build (lines 118-168) and
 * _radius_from_element() (lines 109-115).
 *
 * Columns: StaStart, StaEnd, N, E, Azimuth (deg), Radius, Type, Transition
 * Cells are real numbers (not .6f-formatted strings) per 2026-07-25 decision —
 * easier to sort/sum/use in Sheet formulas; decimal display is a Sheet
 * number-format concern, not this function's.
 * Transition is blanked to '' for T/C elements (only SPIN/SPOUT show it),
 * mirroring _run_build's `'' if el.type in ('T','C') else el.transition`.
 */
if (typeof FPMath === 'undefined' && typeof require !== 'undefined') { var FPMath = require('../FPMath.gs'); }

var GS_ElementTable = (function () {
  'use strict';

  var HEADER = ['StaStart', 'StaEnd', 'N', 'E', 'Azimuth', 'Radius', 'Type', 'Transition'];

  // mirrors _radius_from_element(el): signed design radius, 0 = tangent
  function radiusFromElement_(el) {
    if (el.kIn !== 0) return 1.0 / el.kIn;
    if (el.kOut !== 0) return 1.0 / el.kOut;
    return 0.0;
  }

  // elements -> array of row arrays (header NOT included; caller prepends HEADER)
  function elementsToRows(elements) {
    var rows = [];
    for (var i = 0; i < elements.length; i++) {
      var el = elements[i];
      var transitionVal = (el.type === 'T' || el.type === 'C') ? '' : el.trans;
      rows.push([
        el.staStart,
        el.staEnd,
        el.n,
        el.e,
        FPMath.radToDeg(el.az),
        radiusFromElement_(el),
        el.type,
        transitionVal,
      ]);
    }
    return rows;
  }

  return { HEADER: HEADER, elementsToRows: elementsToRows, radiusFromElement_: radiusFromElement_ };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = GS_ElementTable;
