# tb/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Import our modularized utilities
from utils.constants import ALL_ABRA_MUNICIPALITIES, ABRA_BRGY_COUNTS
from utils.data import get_all_core_tb, get_tb_targets, get_aux_tb_data, get_all_tpt_data
from utils.geo import fetch_barangay_geojson, fetch_muncity_geojson, get_polygon_centroid, apply_label_nudges
from utils.cleaning import clean_brgy_name

def render_tb():
    df_all_raw = get_all_core_tb()
    CASE_COLORS = {"DSTB": "#3b82f6", "DRTB": "#ef4444", "MN": "#f59e0b", "TPT": "#10b981"}

    with st.sidebar:
        if st.button("Back to Menu", icon=":material/arrow_back:", use_container_width=True):
            st.session_state.active_program = None
            st.rerun()
        st.markdown("<hr style='margin: 15px 0; border: none; border-bottom: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #0f172a; margin: 0 0 15px 0;'><i class='fa-solid fa-folder-open' style='color: #475569;'></i> TB Controls</h4>", unsafe_allow_html=True)
        
        available_years = list(range(2026, 2014, -1))
        selected_year = st.selectbox("Select Year", options=available_years, index=0)

        case_type_input = st.multiselect(
            "Filter Case Type", 
            options=["DSTB", "DRTB", "MN", "TPT"], 
            default=["DSTB", "DRTB", "MN", "TPT"]
        )

        if not df_all_raw.empty and "Muncity" in df_all_raw.columns:
            raw_munis = df_all_raw["Muncity"].dropna().unique().tolist()
            valid_munis = [m for m in raw_munis if str(m).strip().upper() in ALL_ABRA_MUNICIPALITIES]
            muni_options = ["All Municipalities"] + sorted(valid_munis)
            muncity_input = st.selectbox("Filter Municipality", options=muni_options, index=0)
        else: muncity_input = "All Municipalities"
            
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("Refresh Data", icon=":material/refresh:", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    active_types = [t for t in case_type_input if t != "TPT"]
    
    if muncity_input != "All Municipalities": df_all_filtered = df_all_raw[(df_all_raw["Muncity"] == muncity_input) & (df_all_raw["Case_Type"].isin(active_types))]
    else: df_all_filtered = df_all_raw[df_all_raw["Case_Type"].isin(active_types)]

    df_combined = df_all_filtered[df_all_filtered['Year'] == selected_year]
    df_prev_year = df_all_filtered[df_all_filtered['Year'] == (selected_year - 1)]
    
    df_hiv = get_aux_tb_data('HIV', selected_year)

    with st.sidebar:
        if not df_combined.empty:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            csv_data = df_combined.to_csv(index=False).encode('utf-8')
            st.download_button(label=f"Download {selected_year} Data", data=csv_data, file_name=f"Abra_TB_Data_{selected_year}.csv", mime="text/csv", icon=":material/download:", use_container_width=True)

    st.title("Abra PESU: Tuberculosis Control Program")
    st.markdown("---")

    curr_cases = len(df_combined)
    prev_cases = len(df_prev_year)
    case_delta = curr_cases - prev_cases

    def get_success_count(df):
        if "Outcome/Status" in df.columns: return len(df[df["Outcome/Status"].str.upper().isin(["CURED", "TREATMENT COMPLETED"])])
        return 0

    curr_success = get_success_count(df_combined)
    prev_success = get_success_count(df_prev_year)
    success_delta = curr_success - prev_success

    if muncity_input == "All Municipalities":
        geo_kpi_title = "Affected Municipalities"
        if 'Muncity' in df_combined.columns: curr_geo = df_combined[df_combined['Muncity'].isin(ALL_ABRA_MUNICIPALITIES)]['Muncity'].nunique()
        else: curr_geo = 0
        if 'Muncity' in df_prev_year.columns: prev_geo = df_prev_year[df_prev_year['Muncity'].isin(ALL_ABRA_MUNICIPALITIES)]['Muncity'].nunique()
        else: prev_geo = 0
        geo_delta = curr_geo - prev_geo
        geo_val = f"{curr_geo} / 27"
    else:
        geo_kpi_title = "Affected Barangays"
        curr_geo = df_combined['Brgy'].nunique() if 'Brgy' in df_combined.columns else 0
        prev_geo = df_prev_year['Brgy'].nunique() if 'Brgy' in df_prev_year.columns else 0
        geo_delta = curr_geo - prev_geo
        total_brgy = ABRA_BRGY_COUNTS.get(muncity_input, "?")
        geo_val = f"{curr_geo} / {total_brgy}"

    def create_yoy_card(title, value, border_color, delta_val, inverse_color=False):
        if delta_val > 0:
            arrow = "↑"
            text_color = "#dc2626" if inverse_color else "#16a34a"
            bg_color = "#fee2e2" if inverse_color else "#dcfce3"
        elif delta_val < 0:
            arrow = "↓"
            text_color = "#16a34a" if inverse_color else "#dc2626" 
            bg_color = "#dcfce3" if inverse_color else "#fee2e2"
        else:
            arrow = "→"
            text_color = "#64748b"
            bg_color = "#f1f5f9"
        return f"""<div style="background-color: #ffffff; padding: 22px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-left: 8px solid {border_color}; text-align: center;"><p style="margin: 0; font-size: 1rem; color: #64748b; font-weight: 600; text-transform: uppercase;">{title}</p><h2 style="margin: 10px 0 10px 0; font-size: 2.6rem; color: #0f172a; font-weight: 800;">{value}</h2><span style="color: {text_color}; font-size: 0.85rem; font-weight: 700; background-color: {bg_color}; padding: 4px 10px; border-radius: 20px;">{arrow} {abs(delta_val)} vs prev year</span></div>"""

    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(create_yoy_card(f"Total Cases ({selected_year})", f"{curr_cases:,}", "#2563eb", case_delta, inverse_color=True), unsafe_allow_html=True)
    with col2: st.markdown(create_yoy_card(f"Successful Outcomes", f"{curr_success:,}", "#10b981", success_delta, inverse_color=False), unsafe_allow_html=True)
    with col3: st.markdown(create_yoy_card(geo_kpi_title, geo_val, "#f59e0b", geo_delta, inverse_color=True), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Epidemiological Trends", 
        "Program Performance", 
        "Demographics", 
        "Clinical & Outcomes", 
        "TB-HIV Collaboration", 
        "Choropleth Map", 
        "Raw Line List"
    ])

    with tab1:
        st.subheader("TB All Forms and TPT Enrollment (2021-2026)")
        
        combo_tb = df_all_raw[(df_all_raw['Year'] >= 2021) & (df_all_raw['Case_Type'] == 'DSTB')].copy()
        
        if 'Bacteriologic Status' in combo_tb.columns:
            combo_tb['Bac_Clean'] = combo_tb['Bacteriologic Status'].fillna('UNKNOWN').astype(str).str.upper()
            bc_mask = combo_tb['Bac_Clean'].str.contains('BACTERIOLOGIC|BC', regex=True)
            cd_mask = combo_tb['Bac_Clean'].str.contains('CLINICAL|CD', regex=True)
            bc_counts = combo_tb[bc_mask].groupby('Year').size()
            cd_counts = combo_tb[cd_mask].groupby('Year').size()
        else:
            bc_counts, cd_counts = pd.Series(dtype=int), pd.Series(dtype=int)
            st.warning("Could not locate 'Bacteriologic Status' column in DSTB data.")
            
        tpt_all = get_all_tpt_data()
        if not tpt_all.empty: tpt_counts = tpt_all[tpt_all['Year'] >= 2021].groupby('Year').size()
        else: tpt_counts = pd.Series(dtype=int)
            
        combo_years = sorted(list(set(bc_counts.index).union(set(cd_counts.index)).union(set(tpt_counts.index))))
        combo_years = [int(y) for y in combo_years if pd.notna(y)]
        
        if combo_years:
            fig_combo = go.Figure()
            y_bc = [bc_counts.get(y, 0) for y in combo_years]
            y_cd = [cd_counts.get(y, 0) for y in combo_years]
            y_tpt = [tpt_counts.get(y, 0) for y in combo_years]
            
            fig_combo.add_trace(go.Bar(x=combo_years, y=y_bc, name="BC", marker_color="#ff0000", text=y_bc, textposition="inside", textfont=dict(color="white")))
            fig_combo.add_trace(go.Bar(x=combo_years, y=y_cd, name="CD", marker_color="#b2d89b", text=y_cd, textposition="inside", textfont=dict(color="black")))
            fig_combo.add_trace(go.Scatter(x=combo_years, y=y_tpt, name="TPT", mode="lines+markers+text", marker_color="#3b82f6", line=dict(width=3), marker=dict(size=8), text=y_tpt, textposition="top center", textfont=dict(color="#3b82f6", size=14, family="Arial Black")))
            
            fig_combo.update_layout(barmode='stack', height=500, xaxis=dict(tickmode='array', tickvals=combo_years), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            st.plotly_chart(fig_combo, use_container_width=True)
        else:
            st.info("No data available to plot the Multi-Year Combo Chart.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader(f"Monthly Case Detection ({selected_year})")
        if "Date of Diagnosis" in df_combined.columns and not df_combined.empty:
            df_combined['Diag_Date'] = pd.to_datetime(df_combined['Date of Diagnosis'], errors='coerce')
            df_combined['Month'] = df_combined['Diag_Date'].dt.month
            month_map = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
            
            monthly_trend = df_combined.dropna(subset=['Month']).groupby(['Month', 'Case_Type']).size().reset_index(name='Cases')
            monthly_trend['Month Name'] = monthly_trend['Month'].map(month_map)
            
            if not monthly_trend.empty:
                fig_trend = px.bar(monthly_trend, x='Month Name', y='Cases', color='Case_Type', text_auto=True, color_discrete_map=CASE_COLORS)
                fig_trend.update_layout(height=400, xaxis_title="Month", yaxis_title="Number of Cases")
                st.plotly_chart(fig_trend, use_container_width=True)
            else: st.info(f"Insufficient date data for monthly trend analysis in {selected_year}.")

    with tab2:
        st.subheader(f"Program Performance Overview ({selected_year})")
        st.markdown("---")
        
        prov_targets, df_muni_targets = get_tb_targets()
        
        if muncity_input == "All Municipalities":
            active_population = prov_targets.get("population", 251555)
            active_screened_target = prov_targets.get("screened_target", 28419)
            active_notified_target = prov_targets.get("notified_target", 1389)
            target_scope_label = "Abra Province"
        else:
            muni_target_row = df_muni_targets[df_muni_targets["Muncity"] == muncity_input.upper()]
            if not muni_target_row.empty:
                active_population = int(muni_target_row["Target_Population"].values[0])
                active_screened_target = int(muni_target_row["Target_Screened"].values[0])
                active_notified_target = int(muni_target_row["Target_Notified"].values[0])
            else:
                active_population = 0
                active_screened_target = 0
                active_notified_target = 0
            target_scope_label = muncity_input.title()

        total_notified_cases = len(df_combined)
        
        col_tc, col_cnr = st.columns(2, gap="large")
        
        with col_tc:
            st.markdown("### Total Cases")
            if not df_combined.empty and "Case_Type" in df_combined.columns:
                case_counts = df_combined["Case_Type"].value_counts().reset_index()
                case_counts.columns = ["Case Type", "Count"]
                total_cases_donut = case_counts["Count"].sum()
                
                fig_total_cases = px.pie(
                    case_counts, names="Case Type", values="Count", hole=0.5,
                    title=f"Total Cases Breakdown ({selected_year})",
                    color_discrete_map={"DSTB": "#3b82f6", "DRTB": "#ef4444", "MN": "#f59e0b"}
                )
                fig_total_cases.update_traces(textinfo='value')
                fig_total_cases.update_layout(
                    height=380, 
                    margin=dict(t=40, b=10, l=10, r=10),
                    annotations=[dict(
                        text=f"<b>{total_cases_donut:,}</b>", 
                        x=0.5, y=0.5, 
                        font=dict(size=36, color="#0f172a"), 
                        showarrow=False
                    )]
                )
                st.plotly_chart(fig_total_cases, use_container_width=True)
            else:
                st.info(f"No case data available for {selected_year}.")
                
        with col_cnr:
            st.markdown("### Case Notification Rate (CNR)")
            st.caption(f"Measures notified TB cases per 100,000 population ({target_scope_label})")
            
            cnr_val = (total_notified_cases / active_population * 100000) if active_population > 0 else 0
            
            c_cnr1, c_cnr2 = st.columns(2)
            with c_cnr1:
                st.metric("Total Notified Cases", f"{total_notified_cases:,}")
            with c_cnr2:
                st.metric("CNR (per 100k Pop)", f"{cnr_val:.1f}", f"Pop: {active_population:,}", delta_color="off")
                
            if muncity_input == "All Municipalities" and not df_muni_targets.empty and "Muncity" in df_combined.columns:
                df_cases_muni = df_combined.groupby("Muncity").size().reset_index(name="Notified_Cases")
                df_cases_muni["Muncity"] = df_cases_muni["Muncity"].str.upper()
                df_cnr_muni = pd.merge(df_muni_targets, df_cases_muni, on="Muncity", how="left").fillna(0)
                df_cnr_muni["CNR"] = df_cnr_muni.apply(
                    lambda r: (r["Notified_Cases"] / r["Target_Population"] * 100000) if r["Target_Population"] > 0 else 0, 
                    axis=1
                )
                df_cnr_muni = df_cnr_muni.sort_values("CNR", ascending=True)
                
                fig_cnr = px.bar(
                    df_cnr_muni, x="CNR", y="Muncity", orientation="h", text_auto=".1f",
                    title="Case Notification Rate per 100k Pop by Municipality",
                    color_discrete_sequence=["#3b82f6"]
                )
                fig_cnr.update_layout(height=300, margin=dict(t=40, b=10, l=10, r=10), xaxis_title="CNR per 100k", yaxis_title="")
                st.plotly_chart(fig_cnr, use_container_width=True)

        st.markdown("<hr style='margin: 30px 0; border: none; border-bottom: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

        col_mort, col_ts = st.columns(2, gap="large")
        
        with col_mort:
            st.markdown("### Mortality")
            if not df_combined.empty and "Outcome/Status" in df_combined.columns:
                df_died = df_combined[df_combined["Outcome/Status"].str.upper().str.contains("DIED", na=False)]
                
                if not df_died.empty:
                    if "Outcome Reason" in df_died.columns:
                        mort_counts = df_died["Outcome Reason"].fillna("Unspecified").value_counts().reset_index()
                        mort_counts.columns = ["Reason", "Count"]
                    else:
                        mort_counts = pd.DataFrame({"Reason": ["Unspecified"], "Count": [len(df_died)]})
                        
                    total_deaths = mort_counts["Count"].sum()
                    
                    fig_mort = px.pie(
                        mort_counts, names="Reason", values="Count", hole=0.5,
                        title=f"Mortality Breakdown ({selected_year})",
                        color_discrete_sequence=["#ef4444", "#f97316", "#dc2626", "#8b5cf6"]
                    )
                    fig_mort.update_traces(textinfo='value')
                    fig_mort.update_layout(
                        height=380, 
                        margin=dict(t=40, b=10, l=10, r=10),
                        annotations=[dict(
                            text=f"<b>{total_deaths:,}</b>", 
                            x=0.5, y=0.5, 
                            font=dict(size=36, color="#0f172a"), 
                            showarrow=False
                        )]
                    )
                    st.plotly_chart(fig_mort, use_container_width=True)
                else:
                    st.success(f"No recorded mortality outcomes for {selected_year}.")
            else:
                st.info("Outcome data not available.")
                
        with col_ts:
            st.markdown("### Treatment Success")
            st.caption("Based on previous cohort evaluation (2025 / 1-year lag)")
            
            df_2025 = df_all_raw[df_all_raw['Year'] == 2025]
            if not df_2025.empty and "Outcome/Status" in df_2025.columns:
                outcomes = df_2025["Outcome/Status"].fillna("Unknown").value_counts().reset_index()
                outcomes.columns = ["Outcome", "Count"]
                
                success_outcomes = df_2025[df_2025["Outcome/Status"].str.upper().isin(["CURED", "TREATMENT COMPLETED"])]
                success_rate = (len(success_outcomes) / len(df_2025) * 100) if len(df_2025) > 0 else 0
                
                fig_ts = px.pie(
                    outcomes, names="Outcome", values="Count", hole=0.6,
                    title="2025 Treatment Outcomes Cohort",
                    color_discrete_sequence=["#facc15", "#3b82f6", "#ec4899", "#10b981", "#64748b"]
                )
                fig_ts.update_traces(textinfo='value')
                fig_ts.update_layout(
                    height=380, 
                    margin=dict(t=40, b=10, l=10, r=10),
                    annotations=[dict(
                        text=f"<b>{success_rate:.1f}%</b><br><span style='font-size:14px; color:#64748b'>Success Rate</span>", 
                        x=0.5, y=0.5, 
                        font=dict(size=36, color="#0f172a"), 
                        showarrow=False
                    )]
                )
                st.plotly_chart(fig_ts, use_container_width=True)
            else:
                st.info("Awaiting 2025 cohort outcome records.")

        st.markdown("<hr style='margin: 30px 0; border: none; border-bottom: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

        st.markdown("### Case Detection Rate (CDR)")
        st.caption(f"Calculated as Total Notified Cases against the 2026 Notified TB Cases Target ({target_scope_label})")
        
        cdr_pct = (total_notified_cases / active_notified_target * 100) if active_notified_target > 0 else 0
        
        c_cdr_gauge, c_cdr_bar = st.columns([1, 2], gap="large")
        
        with c_cdr_gauge:
            fig_cdr_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=cdr_pct,
                number={'suffix': "%", 'valueformat': ".1f", 'font': {'size': 38, 'color': '#0f172a'}},
                title={'text': "<b>Accomplishment vs Notified Target</b>", 'font': {'size': 16}},
                gauge={
                    'axis': {'range': [0, max(100, int(cdr_pct) + 10)]},
                    'bar': {'color': "#10b981"},
                    'bgcolor': "#f1f5f9",
                    'threshold': {'line': {'color': "#16a34a", 'width': 4}, 'thickness': 0.8, 'value': 100}
                }
            ))
            fig_cdr_gauge.update_layout(height=320, margin=dict(t=50, b=10, l=20, r=20))
            st.plotly_chart(fig_cdr_gauge, use_container_width=True)
            st.metric("Total Cases / Notified Target", f"{total_notified_cases:,} / {active_notified_target:,}")

        with c_cdr_bar:
            if muncity_input == "All Municipalities" and not df_muni_targets.empty and "Muncity" in df_combined.columns:
                df_cases_muni = df_combined.groupby("Muncity").size().reset_index(name="Notified_Cases")
                df_cases_muni["Muncity"] = df_cases_muni["Muncity"].str.upper()
                df_cdr_muni = pd.merge(df_muni_targets, df_cases_muni, on="Muncity", how="left").fillna(0)
                
                df_cdr_muni["CDR %"] = df_cdr_muni.apply(
                    lambda r: (r["Notified_Cases"] / r["Target_Notified"] * 100) if r["Target_Notified"] > 0 else 0, 
                    axis=1
                )
                df_cdr_muni = df_cdr_muni.sort_values("CDR %", ascending=True)
                
                fig_cdr_bar = px.bar(
                    df_cdr_muni, x="CDR %", y="Muncity", orientation="h", text_auto=".1f",
                    title="Case Detection Rate (%) by Municipality",
                    color_discrete_sequence=["#10b981"]
                )
                fig_cdr_bar.update_traces(textposition="outside", cliponaxis=False)
                fig_cdr_bar.update_layout(
                    height=max(400, len(df_cdr_muni) * 22),
                    margin=dict(t=40, b=10, l=10, r=40),
                    xaxis_title="Accomplishment (%)",
                    yaxis_title=""
                )
                st.plotly_chart(fig_cdr_bar, use_container_width=True)
            else:
                st.info(f"Target breakdown for {target_scope_label}: {total_notified_cases:,} cases detected out of {active_notified_target:,} target.")

    with tab3:
        st.subheader(f"Demographic Distribution ({selected_year})")
        if "Muncity" in df_combined.columns and muncity_input == "All Municipalities":
            muncity_counts = df_combined.groupby(["Muncity", "Case_Type"]).size().reset_index(name="Count")
            fig_bar = px.bar(muncity_counts, x="Muncity", y="Count", color="Case_Type", title="Total TB Cases per Municipality", text_auto=True, color_discrete_map=CASE_COLORS)
            fig_bar.update_layout(xaxis={'categoryorder':'total descending'}, barmode='stack', height=500)
            st.plotly_chart(fig_bar, use_container_width=True)

        if "Age" in df_combined.columns and "Sex" in df_combined.columns:
            df_combined['Age_Clean'] = pd.to_numeric(df_combined['Age'], errors='coerce').fillna(-1)
            bins = [-1, 0.99, 4, 9, 14, 19, 44, 59, 200]
            age_labels = ['< 1 y/o', '1-4 y/o', '5-9 y/o', '10-14 y/o', '15-19 y/o', '20-44 y/o', '45-59 y/o', '60 y/o & above']
            df_pyr = df_combined.copy()
            df_pyr['AgeGroup'] = pd.cut(df_pyr['Age_Clean'], bins=bins, labels=age_labels, right=True)
            pyr_data = df_pyr.groupby(['AgeGroup', 'Sex']).size().reset_index(name='Count')
            
            males = pyr_data[pyr_data['Sex'].astype(str).str.upper().str.startswith('M')].groupby('AgeGroup')['Count'].sum().reindex(age_labels).fillna(0)
            females = pyr_data[pyr_data['Sex'].astype(str).str.upper().str.startswith('F')].groupby('AgeGroup')['Count'].sum().reindex(age_labels).fillna(0)
            males_negative = males * -1

            fig_pyr = go.Figure()
            fig_pyr.add_trace(go.Bar(y=age_labels, x=males_negative, name='Male', orientation='h', marker_color='#2563eb', text=males.astype(int), hovertemplate="Male: %{text}<extra></extra>"))
            fig_pyr.add_trace(go.Bar(y=age_labels, x=females, name='Female', orientation='h', marker_color='#ec4899', text=females.astype(int), hovertemplate="Female: %{text}<extra></extra>"))
            max_val = int(max(males.max(), females.max())) if not males.empty and not females.empty else 10
            if max_val == 0: max_val = 10
            step = max(1, max_val // 5)
            tick_vals = list(range(-((max_val // step) * step + step), ((max_val // step) * step + step) + step, step))
            tick_text = [str(abs(v)) for v in tick_vals]
            fig_pyr.update_layout(title="Age and Sex Distribution of TB Cases", barmode='relative', bargap=0.1, height=500, xaxis=dict(tickvals=tick_vals, ticktext=tick_text, title="No. of Cases"), yaxis=dict(title="Age Group"))
            st.plotly_chart(fig_pyr, use_container_width=True)
            
    with tab4:
        st.subheader(f"Clinical & Treatment Outcomes ({selected_year})")
        c1, c2 = st.columns(2)
        with c1:
            if "Outcome/Status" in df_combined.columns:
                outcome_counts = df_combined["Outcome/Status"].fillna("Unknown").value_counts().reset_index()
                outcome_counts.columns = ["Outcome", "Count"]
                fig_pie_out = px.pie(outcome_counts, names="Outcome", values="Count", hole=0.45, title="Treatment Outcomes")
                st.plotly_chart(fig_pie_out, use_container_width=True)
        with c2:
            if "Registration Group" in df_combined.columns:
                reg_counts = df_combined["Registration Group"].fillna("Unknown").value_counts().reset_index()
                reg_counts.columns = ["Registration Group", "Count"]
                fig_pie_reg = px.pie(reg_counts, names="Registration Group", values="Count", hole=0.45, title="Patient Registration Group")
                st.plotly_chart(fig_pie_reg, use_container_width=True)

        c_site, c_bac = st.columns(2)
        with c_site:
            if "Anatomical Site" in df_combined.columns:
                site_counts = df_combined["Anatomical Site"].fillna("Unknown").value_counts().reset_index()
                site_counts.columns = ["Site", "Count"]
                fig_site = px.pie(site_counts, names="Site", values="Count", hole=0.45, title="Anatomical Site (P vs. EP)")
                fig_site.update_traces(marker_colors=['#0ea5e9', '#8b5cf6'])
                st.plotly_chart(fig_site, use_container_width=True)

        with c_bac:
            if "Bacteriologic Status" in df_combined.columns:
                bac_counts = df_combined["Bacteriologic Status"].fillna("Unknown").value_counts().reset_index()
                bac_counts.columns = ["Bacteriologic Status", "Count"]
                # Swapped out the bar chart for a clean donut chart here!
                fig_pie_bac = px.pie(bac_counts, names="Bacteriologic Status", values="Count", hole=0.45, title="Bacteriologic Status")
                st.plotly_chart(fig_pie_bac, use_container_width=True)

    with tab5:
        st.subheader(f"TB-HIV Collaborative Activities ({selected_year})")
        if not df_hiv.empty:
            num_col = "All Reg Group 15 above TB Cases Tested or with Known HIV Status"
            den_col = "All Reg Group 15 above TB Cases"
            
            if "Facility" in df_hiv.columns and "Quarter" in df_hiv.columns and num_col in df_hiv.columns and den_col in df_hiv.columns:
                total_tb_15 = df_hiv[den_col].sum()
                total_tested = df_hiv[num_col].sum()
                testing_rate = (total_tested / total_tb_15 * 100) if total_tb_15 > 0 else 0
                
                c5, c6 = st.columns(2)
                c5.metric("Eligible TB Patients (15+ yrs)", f"{int(total_tb_15):,}")
                c6.metric("Tested for HIV", f"{int(total_tested):,}", f"{testing_rate:.1f}% Coverage")
                st.markdown("<hr>", unsafe_allow_html=True)
                
                df_hiv_clean = df_hiv.copy()
                df_hiv_clean['Quarter'] = pd.to_numeric(df_hiv_clean['Quarter'], errors='coerce')
                df_hiv_clean = df_hiv_clean.dropna(subset=['Quarter'])
                df_hiv_clean['Quarter'] = df_hiv_clean['Quarter'].astype(int).apply(lambda x: f"Q{x}")
                
                grouped = df_hiv_clean.groupby(['Facility', 'Quarter'])[[num_col, den_col]].sum().reset_index()
                
                def format_coverage(row):
                    n = int(row[num_col])
                    d = int(row[den_col])
                    pct = (n / d * 100) if d > 0 else 0
                    if d == 0 and n == 0: return "-"
                    return f"{n} / {d} ({pct:.1f}%)"
                    
                grouped['Coverage'] = grouped.apply(format_coverage, axis=1)
                pivot_hiv = grouped.pivot(index='Facility', columns='Quarter', values='Coverage').fillna('-')
                
                st.markdown("##### HIV Testing Coverage by Facility and Quarter")
                st.dataframe(pivot_hiv, use_container_width=True)
            else:
                st.error("HIV Data columns do not match the expected ITIS export format.")
        else: st.info(f"No HIV data available for {selected_year}.")

    with tab6:
        if muncity_input != "All Municipalities":
            st.subheader(f"Geographic Heatmap: Barangays in {muncity_input} ({selected_year})")
            brgy_geojson, err = fetch_barangay_geojson(muncity_input)
            if brgy_geojson and "Brgy" in df_combined.columns:
                all_geojson_brgys = [f['properties']['Standard_Name'] for f in brgy_geojson['features']]
                all_geojson_originals = [f['properties']['Original_Name'] for f in brgy_geojson['features']]
                base_df = pd.DataFrame({"Join_Key": all_geojson_brgys, "Barangay_Display": all_geojson_originals, "Base_Cases": 0})
                curr_cases = df_combined.groupby("Brgy").size().reset_index(name="Filtered_Cases")
                curr_cases["Join_Key"] = curr_cases["Brgy"].apply(clean_brgy_name)
                curr_cases = curr_cases.groupby("Join_Key")["Filtered_Cases"].sum().reset_index()
                
                map_data = pd.merge(base_df, curr_cases, on="Join_Key", how="left")
                map_data["Total Cases"] = map_data["Filtered_Cases"].fillna(0).astype(int)
                
                lons, lats, texts = [], [], []
                for feat in brgy_geojson['features']:
                    std_name = feat['properties']['Standard_Name']
                    display_name = feat['properties'].get('Original_Name', std_name)
                    match = map_data[map_data['Join_Key'] == std_name]
                    cases = match['Total Cases'].values[0] if not match.empty else 0
                    lon, lat = get_polygon_centroid(feat['geometry'])
                    if lon is not None and lat is not None:
                        lons.append(float(lon)); lats.append(float(lat))
                        texts.append(f"{display_name.title()}<br>{int(cases)}")
                
                cam_lat = float(np.mean(lats)) if lats else 17.58
                cam_lon = float(np.mean(lons)) if lons else 120.83
                
                if not map_data.empty and "Total Cases" in map_data.columns:
                    try:
                        max_val = max(1, int(map_data["Total Cases"].max()))
                        
                        fig_map = px.choropleth_map(
                            map_data, geojson=brgy_geojson, locations='Join_Key', featureidkey='properties.Standard_Name', 
                            color='Total Cases', color_continuous_scale="Blues", range_color=[0, max_val], map_style="white-bg",
                            zoom=11.5, center={"lat": cam_lat, "lon": cam_lon}, opacity=0.7, hover_name='Barangay_Display',
                            hover_data={'Join_Key': False, 'Total Cases': ':,', 'Barangay_Display': False}
                        )
                        fig_map.add_trace(go.Scattermap(
                            lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=9, color='black'), hoverinfo='skip', showlegend=False
                        ))
                        fig_map.update_layout(
                            dragmode=False,
                            margin={"r":0,"t":0,"l":0,"b":0}, 
                            coloraxis_colorbar=dict(title="Cases"), 
                            height=600,
                            map=dict(layers=[dict(below="traces", sourcetype="raster", source=["https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"])])
                        )
                        st.plotly_chart(
                            fig_map, 
                            use_container_width=True,
                            key="tb_brgy_map",
                            config={
                                'scrollZoom': False, 
                                'displayModeBar': True, 
                                'toImageButtonOptions': {'format': 'png', 'filename': f'TB_Map_{muncity_input}', 'scale': 4}
                            }
                        )
                    except Exception as e:
                        st.error(f"Plotly error rendering Barangay map: {e}")
                else: st.warning("No geographic mapping data available for the selected filters.")
            else: st.error(err if err else "Barangay column (Brgy) missing in data.")
                
        else:
            st.subheader(f"Geographic Heatmap: Municipalities in Abra ({selected_year})")
            base_df = pd.DataFrame({"Muncity": ALL_ABRA_MUNICIPALITIES, "Base_Cases": 0})
            curr_cases = df_combined.groupby("Muncity").size().reset_index(name="Filtered_Cases")
            map_data = pd.merge(base_df, curr_cases, on="Muncity", how="left")
            map_data["Total Cases"] = map_data["Filtered_Cases"].fillna(0).astype(int)
            
            abra_geojson = fetch_muncity_geojson()
            if abra_geojson:
                lons, lats, texts = [], [], []
                for feat in abra_geojson['features']:
                    std_name = feat['properties']['Standard_Name']
                    match = map_data[map_data['Muncity'] == std_name]
                    cases = match['Total Cases'].values[0] if not match.empty else 0
                    lon, lat = get_polygon_centroid(feat['geometry'])
                    
                    if lon is not None and lat is not None:
                        lat, lon = apply_label_nudges(std_name, lat, lon)
                        lons.append(lon)
                        lats.append(lat)
                        texts.append(f"{std_name.title()}<br>{int(cases)}")
                
                if not map_data.empty and "Total Cases" in map_data.columns:
                    try:
                        max_val = max(1, int(map_data["Total Cases"].max()))
                        
                        fig_map = px.choropleth_map(
                            map_data, geojson=abra_geojson, locations='Muncity', featureidkey='properties.Standard_Name', 
                            color='Total Cases', color_continuous_scale="Blues", range_color=[0, max_val], map_style="white-bg",
                            zoom=9.2, center={"lat": 17.58, "lon": 120.80}, opacity=0.7, hover_name='Muncity',
                            hover_data={'Muncity': False, 'Total Cases': ':,'}
                        )
                        fig_map.add_trace(go.Scattermap(
                            lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=9, color='black'), hoverinfo='skip', showlegend=False
                        ))
                        fig_map.update_layout(
                            dragmode=False,
                            margin={"r":0,"t":0,"l":0,"b":0}, 
                            coloraxis_colorbar=dict(title="Cases"), 
                            height=600,
                            map=dict(layers=[dict(below="traces", sourcetype="raster", source=["https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"])])
                        )
                        st.plotly_chart(
                            fig_map, 
                            use_container_width=True,
                            key="tb_muni_map",
                            config={
                                'scrollZoom': False, 
                                'displayModeBar': True, 
                                'toImageButtonOptions': {'format': 'png', 'filename': 'TB_Map_Abra', 'scale': 4}
                            }
                        )
                    except Exception as e:
                        st.error(f"Plotly error rendering Municipality map: {e}")
                else: st.warning("No geographic mapping data available for the selected filters.")
            else: st.error("Could not fetch the Abra geographic boundaries.")

    with tab7:
        st.subheader(f"Filtered TB Registry ({selected_year})")
        st.caption("Showing key programmatic columns. Use the Download button in the sidebar for the full dataset.")
        clean_cols = ["TB/TPT Case No.", "Case_Type", "First Name", "Last Name", "Age", "Sex", "Brgy", "Muncity", "Bacteriologic Status", "Outcome/Status", "Date Started Tx"]
        available_cols = [col for col in clean_cols if col in df_combined.columns]
        
        safe_df = df_combined.copy()
        for col in safe_df.columns:
            safe_df[col] = safe_df[col].astype(str)
            
        if available_cols: st.dataframe(safe_df[available_cols], use_container_width=True, hide_index=True, height=600)
        else: st.dataframe(safe_df, use_container_width=True, hide_index=True, height=600)