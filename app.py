"""app - Streamlit web UI over the SMT core engine (Application/boundary layer).

Thin wrapper: parses uploaded CSVs into the same in-memory structures the CLI
builds, then delegates to src/smt. Does NO geometry maths itself.

Run with: streamlit run app.py  (requires: pip install -e ".[ui]")
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from smt import alignment, check, fpmath
from smt.builders.alignment_builder import build_alignment_from_pi, parse_pi_table
from smt.landxml import export_alignment_landxml
from smt.webhelpers import (
    parse_drawing_points,
    parse_element_rows,
    parse_field_points,
    read_csv_rows,
)
# optimizer.fit_radius is imported lazily inside the Fit Radius tab (scipy optional)


def _radius_from_element(el: alignment.Element) -> float:
    """Return signed design radius for output (0 = tangent). Mirrors cli.py."""
    if el.k_in != 0:
        return 1.0 / el.k_in
    if el.k_out != 0:
        return 1.0 / el.k_out
    return 0.0


st.set_page_config(page_title='SMT Toolkit', layout='wide')
st.title('Surveyor Micro Toolkit')

tab_build, tab_xc, tab_cd, tab_fr, tab_lx = st.tabs(
    ['Build', 'Cross-Check', 'Compare Drawing', 'Fit Radius', 'Export LandXML']
)

# ---------------------------------------------------------------------------
# 1. Build tab
# ---------------------------------------------------------------------------
with tab_build:
    st.header('Build alignment from PI table')
    pi_file = st.file_uploader('PI table CSV', type='csv', key='build_pi')
    if st.button('Run', key='build_run', disabled=pi_file is None):
        try:
            rows = read_csv_rows(pi_file.getvalue())
            vertices = parse_pi_table(rows)
            result = build_alignment_from_pi(vertices)
            for issue in result.issues:
                st.warning(issue)

            el_rows = []
            for el in result.elements:
                transition_val = '' if el.type in ('T', 'C') else el.transition
                el_rows.append({
                    'StaStart': el.sta_start,
                    'StaEnd': el.sta_end,
                    'N': el.n,
                    'E': el.e,
                    'Azimuth': fpmath.rad_to_deg(el.azimuth),
                    'Radius': _radius_from_element(el),
                    'Type': el.type,
                    'Transition': transition_val,
                })
            elements_df = pd.DataFrame(el_rows)

            cp_rows = [{'Name': cp.name, 'STA': cp.sta, 'N': cp.n, 'E': cp.e}
                       for cp in result.control]
            control_df = pd.DataFrame(cp_rows)

            st.subheader(f'Elements ({len(elements_df)} rows)')
            st.dataframe(elements_df)
            st.download_button(
                'Download elements_output.csv',
                elements_df.to_csv(index=False),
                file_name='elements_output.csv',
                key='build_dl_elements',
            )

            st.subheader(f'Control Points ({len(control_df)} rows)')
            st.dataframe(control_df)
            st.download_button(
                'Download controls_so_output.csv',
                control_df.to_csv(index=False),
                file_name='controls_so_output.csv',
                key='build_dl_control',
            )
        except Exception as exc:
            st.error(f'build failed: {exc}')

# ---------------------------------------------------------------------------
# 2. Cross-Check tab
# ---------------------------------------------------------------------------
with tab_xc:
    st.header('Cross-check field survey points against alignment')
    xc_pi_file = st.file_uploader('PI table CSV', type='csv', key='xc_pi')
    xc_field_file = st.file_uploader('Field survey CSV (NAME,N,E,Z,DISC)', type='csv', key='xc_field')
    xc_ready = xc_pi_file is not None and xc_field_file is not None
    if st.button('Run', key='xc_run', disabled=not xc_ready):
        try:
            vertices = parse_pi_table(read_csv_rows(xc_pi_file.getvalue()))
            result = build_alignment_from_pi(vertices)
            for issue in result.issues:
                st.warning(issue)
            field_points = parse_field_points(read_csv_rows(xc_field_file.getvalue()))
            rows = check.bulk_cross_check(result.elements, field_points)

            xc_df = pd.DataFrame([{
                'NAME': r.name, 'STA': r.sta, 'OFFSET': r.offset,
                'N': r.n, 'E': r.e, 'Z': r.z, 'DISC': r.disc,
            } for r in rows])
            st.dataframe(xc_df)
            st.download_button(
                'Download cross_check.csv',
                xc_df.to_csv(index=False),
                file_name='cross_check.csv',
                key='xc_dl',
            )
        except Exception as exc:
            st.error(f'cross-check failed: {exc}')

# ---------------------------------------------------------------------------
# 3. Compare Drawing tab
# ---------------------------------------------------------------------------
with tab_cd:
    st.header('Compare drawing control points against calculated coordinates')
    cd_elements_file = st.file_uploader(
        'Element table CSV (StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition)',
        type='csv', key='cd_elements',
    )
    cd_drawing_file = st.file_uploader('Drawing control-point CSV (Name,STA,N,E)', type='csv', key='cd_drawing')
    cd_tol = st.number_input('tolerance (m)', value=0.010, format='%.3f', key='cd_tol')
    cd_ready = cd_elements_file is not None and cd_drawing_file is not None
    if st.button('Run', key='cd_run', disabled=not cd_ready):
        try:
            elements = alignment.parse_alignment_table(
                parse_element_rows(read_csv_rows(cd_elements_file.getvalue()))
            )
            points = parse_drawing_points(read_csv_rows(cd_drawing_file.getvalue()))

            cd_rows = []
            for pt in points:
                name = pt['name']
                sta = pt['sta']
                draw_n = pt['n']
                draw_e = pt['e']
                upper = name.upper()
                if upper.startswith('PI') or upper.startswith('HIP'):
                    cd_rows.append({
                        'Name': name, 'STA': sta, 'draw_N': draw_n, 'draw_E': draw_e,
                        'calc_N': None, 'calc_E': None, 'delta_N': None, 'delta_E': None,
                        'gap_m': None, 'status': 'HIP',
                    })
                    continue
                calc = alignment.calculate_station_to_coordinate(elements, sta, 0.0)
                delta_n = calc.n - draw_n
                delta_e = calc.e - draw_e
                gap_m = math.sqrt(delta_n ** 2 + delta_e ** 2)
                status = 'OK' if gap_m <= cd_tol else 'FAIL'
                cd_rows.append({
                    'Name': name, 'STA': sta, 'draw_N': draw_n, 'draw_E': draw_e,
                    'calc_N': calc.n, 'calc_E': calc.e, 'delta_N': delta_n, 'delta_E': delta_e,
                    'gap_m': gap_m, 'status': status,
                })
            cd_df = pd.DataFrame(cd_rows)
            st.dataframe(cd_df)
            st.download_button(
                'Download compare_drawing.csv',
                cd_df.to_csv(index=False),
                file_name='compare_drawing.csv',
                key='cd_dl',
            )
        except Exception as exc:
            st.error(f'compare-drawing failed: {exc}')

# ---------------------------------------------------------------------------
# 4. Fit Radius tab
# ---------------------------------------------------------------------------
with tab_fr:
    st.header('Fit radius — optimise PI radii against drawing points')
    try:
        import scipy  # noqa: F401
        scipy_available = True
    except ImportError:
        scipy_available = False
        st.error(
            "scipy not installed — fit-radius requires it. "
            "Install with: pip install 'surveyor-micro-toolkit[optimize]'"
        )

    fr_pi_file = st.file_uploader('PI table CSV', type='csv', key='fr_pi')
    fr_drawing_file = st.file_uploader('Drawing control-point CSV (Name,STA,N,E)', type='csv', key='fr_drawing')
    fr_fix_text = st.text_input('fix names (comma-separated)', value='', key='fr_fix')
    fr_tol = st.number_input('tol', value=1e-6, format='%.2e', key='fr_tol')
    fr_max_iter = st.number_input('max_iter', value=10000, step=1000, key='fr_max_iter')

    fr_ready = scipy_available and fr_pi_file is not None and fr_drawing_file is not None
    if st.button('Run', key='fr_run', disabled=not fr_ready):
        try:
            try:
                from smt.optimizer import fit_radius
            except ImportError as exc:
                st.error(f'scipy not available: {exc}')
                st.stop()

            pi_rows = read_csv_rows(fr_pi_file.getvalue())
            drawing_points = parse_drawing_points(read_csv_rows(fr_drawing_file.getvalue()))
            fix_names = [s.strip() for s in fr_fix_text.split(',') if s.strip()] or None
            result = fit_radius(pi_rows, drawing_points, fix_names, fr_tol, int(fr_max_iter))

            st.write(f'{len(result.names)} free PI(s), {result.n_points} drawing point(s)')
            col1, col2, col3 = st.columns(3)
            col1.metric('gap_before (m)', f'{result.gap_before:.6f}')
            col2.metric('gap_after (m)', f'{result.gap_after:.6f}')
            col3.write(f'iterations: {result.iterations}  \nconverged: {result.converged}')

            fr_df = pd.DataFrame({
                'PI': result.names,
                'R_initial': result.r_initial,
                'R_optimized': result.r_optimized,
            })
            st.dataframe(fr_df)
            st.download_button(
                'Download fit_radius.csv',
                fr_df.to_csv(index=False),
                file_name='fit_radius.csv',
                key='fr_dl',
            )

            if result.names and drawing_points:
                try:
                    header = pi_rows[0]
                    point_col = next(
                        (i for i, c in enumerate(header) if str(c).strip().lower() == 'point'), None
                    )
                    r_col = next(
                        (i for i, c in enumerate(header) if str(c).strip().lower() in ('r', 'radius')), None
                    )
                    if point_col is not None and r_col is not None:
                        name_to_r = dict(zip(result.names, result.r_optimized))
                        patched = [list(row) for row in pi_rows]
                        for row in patched[1:]:
                            if point_col < len(row):
                                pname = str(row[point_col]).strip()
                                if pname in name_to_r and r_col < len(row):
                                    row[r_col] = str(name_to_r[pname])
                        vertices = parse_pi_table(patched)
                        built = build_alignment_from_pi(vertices)
                        active_pts = [
                            dp for dp in drawing_points
                            if not str(dp.get('name', '')).strip().upper().startswith(('PI', 'HIP'))
                        ]
                        verify_rows = []
                        for dp in active_pts:
                            try:
                                pt = alignment.calculate_station_to_coordinate(
                                    built.elements, float(dp['sta'])
                                )
                                gap = math.hypot(pt.n - float(dp['n']), pt.e - float(dp['e']))
                                verify_rows.append({
                                    'Name': dp['name'], 'STA': float(dp['sta']),
                                    'calc_N': pt.n, 'calc_E': pt.e, 'gap_m': gap,
                                    'status': 'OK',
                                })
                            except (ValueError, IndexError):
                                verify_rows.append({
                                    'Name': dp['name'], 'STA': float(dp['sta']),
                                    'calc_N': None, 'calc_E': None, 'gap_m': None,
                                    'status': 'OUTSIDE_ALIGNMENT',
                                })
                        st.subheader('Verification (gap after optimisation)')
                        st.dataframe(pd.DataFrame(verify_rows))
                except Exception as exc:
                    st.warning(f'verification table failed: {exc}')
        except Exception as exc:
            st.error(f'fit-radius failed: {exc}')

# ---------------------------------------------------------------------------
# 5. Export LandXML tab
# ---------------------------------------------------------------------------
with tab_lx:
    st.header('Export LandXML')
    lx_pi_file = st.file_uploader('PI table CSV', type='csv', key='lx_pi')
    lx_name = st.text_input('alignment name', value='alignment', key='lx_name')
    if st.button('Run', key='lx_run', disabled=lx_pi_file is None):
        try:
            vertices = parse_pi_table(read_csv_rows(lx_pi_file.getvalue()))
            result = build_alignment_from_pi(vertices)
            for issue in result.issues:
                st.warning(issue)
            xml_str = export_alignment_landxml(result, name=lx_name)
            st.code(xml_str, language='xml')
            st.download_button(
                'Download LandXML',
                xml_str,
                file_name=f'{lx_name}.xml',
                mime='application/xml',
                key='lx_dl',
            )
        except Exception as exc:
            st.error(f'export-landxml failed: {exc}')
