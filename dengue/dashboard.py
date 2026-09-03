# dengue/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Import our modularized utilities
from utils.constants import ALL_ABRA_MUNICIPALITIES, ABRA_BRGY_COUNTS
from utils.data import load_data
from utils.geo import fetch_barangay_geojson, fetch_muncity_geojson, get_polygon_centroid, apply_label_nudges
from utils.cleaning import clean_brgy_name

def render_dengue():
    df = load_data()

    with st.sidebar:
        if st.button("Back to Menu", icon=":material/arrow_back:", use_container_width=True):
            st.session_state.active_program = None
            st.rerun()
            
        st.markdown("<hr style='margin: 15px 0; border: none; border-bottom: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #0f172a; margin: 0 0 15px 0;'><i class='fa-solid fa-arrow-down-short-wide' style='color: #475569;'></i> Filters</h4>", unsafe_allow_html=True)
        
        muni_options = ["All Municipalities"] + sorted(df["Muncity"].dropna().unique().tolist())
        muncity_input = st.selectbox("Municipality", options=muni_options, index=0)
        sex_input = st.multiselect("Sex", options=df["Sex"].dropna().unique(), default=[])
        clin_input = st.multiselect("Clinical Class", options=df["ClinClass"].dropna().unique(), default=[])
            
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("Refresh Data", icon=":material/refresh:", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    muncity_filter = df["Muncity"].dropna().unique() if muncity_input == "All Municipalities" else [muncity_input]
    sex_filter = sex_input if sex_input else df["Sex"].dropna().unique()
    clin_filter = clin_input if clin_input else df["ClinClass"].dropna().unique()
    filtered_df = df.query("Muncity in @muncity_filter & Sex in @sex_filter & ClinClass in @clin_filter")

    # --- DOWNLOAD BUTTON LOGIC ---
    with st.sidebar:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if not filtered_df.empty:
            dengue_csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Filtered Data",
                data=dengue_csv,
                file_name=f"Abra_Dengue_Data_{muncity_input.replace(' ', '_')}.csv",
                mime="text/csv",
                icon=":material/download:",
                use_container_width=True
            )

    st.title("Abra PESU: Dengue Surveillance Dashboard")
    st.caption("As of Morbidity Week: " + str(filtered_df["MorbidityWeek"].max()) if "MorbidityWeek" in filtered_df.columns else "No Morbidity Week Data Available")
    st.markdown("---")

    total_cases = len(filtered_df)
    total_deaths = len(filtered_df[filtered_df["Outcome"] == "D"]) if "Outcome" in filtered_df.columns else 0
    avg_age = round(filtered_df["AgeYears"].mean(), 1) if not filtered_df.empty and "AgeYears" in filtered_df.columns else 0
    
    if muncity_input == "All Municipalities":
        geo_kpi_title = "Affected Municipalities"
        geo_kpi_value = f"{filtered_df['Muncity'].nunique()} / 27"
    else:
        geo_kpi_title = "Affected Barangays"
        affected_brgy = filtered_df['Barangay'].nunique() if 'Barangay' in filtered_df.columns else 0
        total_brgy = ABRA_BRGY_COUNTS.get(muncity_input, "?")
        geo_kpi_value = f"{affected_brgy} / {total_brgy}"

    def create_kpi_card(title, value, border_color):
        return f"""
        <div style="background-color: #ffffff; padding: 22px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-left: 8px solid {border_color}; text-align: center;">
            <p style="margin: 0; font-size: 1rem; color: #64748b; font-weight: 600; text-transform: uppercase;">{title}</p>
            <h2 style="margin: 10px 0 0 0; font-size: 2.6rem; color: #0f172a; font-weight: 800;">{value}</h2>
        </div>
        """

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(create_kpi_card("Total Confirmed Cases", f"{total_cases:,}", "#2563eb"), unsafe_allow_html=True)
    with col2: st.markdown(create_kpi_card("Total Fatalities", f"{total_deaths:,}", "#ef4444"), unsafe_allow_html=True)
    with col3: st.markdown(create_kpi_card("Average Age (Years)", avg_age, "#10b981"), unsafe_allow_html=True)
    with col4: st.markdown(create_kpi_card(geo_kpi_title, geo_kpi_value, "#f59e0b"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Epidemiological Trends", "Demographics & Geography", "Clinical & Laboratory", "Choropleth Map", "Raw Line List"
    ])

    with tab1:
        if "MorbidityWeek" in filtered_df.columns:
            cases_by_week = filtered_df.groupby("MorbidityWeek").size().reset_index(name="Case Count")
            fig_line = px.line(cases_by_week, x="MorbidityWeek", y="Case Count", markers=True, title="Dengue Trend by Morbidity Week")
            fig_line.update_traces(line_color='#eba925', marker=dict(size=10))
            fig_line.update_layout(height=500)
            st.plotly_chart(fig_line, use_container_width=True)

        if "MorbidityMonth" in filtered_df.columns:
            month_counts = filtered_df.groupby("MorbidityMonth").size().reset_index(name="Cases")
            fig_month = px.bar(month_counts, x="MorbidityMonth", y="Cases", text_auto=True, title="Dengue Cases by Morbidity Month")
            fig_month.update_traces(marker_color='#b300cf')
            fig_month.update_layout(height=450)
            st.plotly_chart(fig_month, use_container_width=True)
        
    with tab2:
        if "Muncity" in filtered_df.columns:
            muncity_counts = filtered_df["Muncity"].value_counts().reset_index()
            muncity_counts.columns = ["Municipality", "Count"]
            fig_bar = px.bar(muncity_counts, x="Municipality", y="Count", title="Total Cases per Municipality", text_auto=True)
            fig_bar.update_traces(marker_color="#eb2525")
            fig_bar.update_layout(xaxis={'categoryorder':'total descending'}, height=500)
            st.plotly_chart(fig_bar, use_container_width=True)

        if "AgeYears" in filtered_df.columns and "Sex" in filtered_df.columns:
            bins = [-1, 0.99, 4, 9, 14, 19, 44, 59, 200]
            age_labels = ['< 1 y/o', '1-4 y/o', '5-9 y/o', '10-14 y/o', '15-19 y/o', '20-44 y/o', '45-59 y/o', '60 y/o & above']
            df_pyr = filtered_df.copy()
            df_pyr['AgeGroup'] = pd.cut(df_pyr['AgeYears'], bins=bins, labels=age_labels, right=True)
            pyr_data = df_pyr.groupby(['AgeGroup', 'Sex']).size().reset_index(name='Count')
            
            males = pyr_data[pyr_data['Sex'].str.upper().str.startswith('M')].groupby('AgeGroup')['Count'].sum().reindex(age_labels).fillna(0)
            females = pyr_data[pyr_data['Sex'].str.upper().str.startswith('F')].groupby('AgeGroup')['Count'].sum().reindex(age_labels).fillna(0)
            males_negative = males * -1

            fig_pyr = go.Figure()
            fig_pyr.add_trace(go.Bar(
                y=age_labels, x=males_negative, name='Male', orientation='h', marker_color='#2563eb',
                text=males.astype(int), hovertemplate="Male: %{text}<extra></extra>"
            ))
            fig_pyr.add_trace(go.Bar(
                y=age_labels, x=females, name='Female', orientation='h', marker_color='#ec4899',
                text=females.astype(int), hovertemplate="Female: %{text}<extra></extra>"
            ))

            max_val = int(max(males.max(), females.max()))
            if max_val == 0: max_val = 10
            step = max(1, max_val // 5)
            tick_vals = list(range(-((max_val // step) * step + step), ((max_val // step) * step + step) + step, step))
            tick_text = [str(abs(v)) for v in tick_vals]

            fig_pyr.update_layout(
                title="Age and Sex Distribution of Cases", barmode='relative', bargap=0.1, height=500,
                xaxis=dict(tickvals=tick_vals, ticktext=tick_text, title="No. of Cases"),
                yaxis=dict(title="Age Group")
            )
            st.plotly_chart(fig_pyr, use_container_width=True)

        if "MorbidityWeek" in df.columns and "Barangay" in filtered_df.columns and "Muncity" in filtered_df.columns:
            st.markdown("<hr style='margin: 30px 0; border: none; border-bottom: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
            st.subheader("Clustering Barangay")
            
            try:
                global_df = df.copy()
                global_df['MW_Clean'] = pd.to_numeric(global_df['MorbidityWeek'], errors='coerce')
                global_weeks = sorted(global_df['MW_Clean'].dropna().astype(int).unique())
                
                previous_weeks = global_weeks[:-1] if len(global_weeks) > 1 else []
                default_weeks = previous_weeks[-4:] if len(previous_weeks) >= 4 else previous_weeks
                
                selected_weeks = st.multiselect(
                    "Select Morbidity Weeks for Clustering", 
                    options=global_weeks, 
                    default=default_weeks,
                    help="The current (latest) week is excluded by default as its data is usually incomplete."
                )
                
                clean_df = filtered_df.copy()
                clean_df['MW_Clean'] = pd.to_numeric(clean_df['MorbidityWeek'], errors='coerce')
                clean_df = clean_df.dropna(subset=['MW_Clean'])
                clean_df['MW_Clean'] = clean_df['MW_Clean'].astype(int)
                
                if selected_weeks:
                    cluster_df = clean_df[clean_df["MW_Clean"].isin(selected_weeks)]
                    selected_weeks = sorted(selected_weeks)
                    
                    if not cluster_df.empty:
                        pivot_cluster = pd.crosstab(
                            index=[cluster_df['Muncity'], cluster_df['Barangay']],
                            columns=cluster_df['MW_Clean']
                        ).fillna(0).astype(int)
                        
                        for w in selected_weeks:
                            if w not in pivot_cluster.columns:
                                pivot_cluster[w] = 0
                        pivot_cluster = pivot_cluster[selected_weeks]
                        
                        pivot_cluster['Total'] = pivot_cluster.sum(axis=1)
                        pivot_cluster = pivot_cluster[pivot_cluster['Total'] >= 3].reset_index()
                        
                        if not pivot_cluster.empty:
                            pivot_cluster['Sort_Key'] = pivot_cluster['Muncity'].str.replace('Ñ', 'N')
                            pivot_cluster = pivot_cluster.sort_values(by=['Sort_Key', 'Barangay']).drop(columns=['Sort_Key'])
                            
                            rename_dict = {w: f"MW{w}" for w in selected_weeks}
                            pivot_cluster = pivot_cluster.rename(columns=rename_dict)
                            pivot_cluster.rename(columns={'Muncity': 'Municipality'}, inplace=True)
                            
                            def apply_green_color(val):
                                try:
                                    if int(val) > 0:
                                        return 'background-color: #8bc34a; color: #0f172a; font-weight: bold;' 
                                    return ''
                                except:
                                    return ''
                                    
                            color_cols = [f"MW{w}" for w in selected_weeks]
                            
                            if hasattr(pivot_cluster.style, 'map'):
                                styled_df = pivot_cluster.style.map(apply_green_color, subset=color_cols)
                            else: 
                                styled_df = pivot_cluster.style.applymap(apply_green_color, subset=color_cols)
                            
                            st.dataframe(styled_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No clustering barangays (≥ 3 cases) detected in the selected morbidity weeks.")
                    else:
                        st.info("No case data available for the selected morbidity weeks.")
                else:
                    st.info("Please select at least one Morbidity Week from the dropdown above.")
            except Exception as e:
                st.error(f"Error generating clustering table: {e}")

    with tab3:
        if "ClinClass" in filtered_df.columns:
            class_counts = filtered_df["ClinClass"].value_counts().reset_index()
            class_counts.columns = ["Classification", "Count"]
            color_map = {"NO WARNING SIGNS": "#10b981", "WITH WARNING SIGNS": "#f59e0b", "SEVERE DENGUE": "#ef4444"}
            fig_pie = px.pie(class_counts, names="Classification", values="Count", hole=0.45, title="Clinical Severity Classification", color="Classification", color_discrete_map=color_map)
            fig_pie.update_layout(height=500)
            st.plotly_chart(fig_pie, use_container_width=True)

        if 'DRU' in filtered_df.columns:
            dru_counts = filtered_df["DRU"].fillna("Unspecified").value_counts().reset_index()
            dru_counts.columns = ["Facility Type", "Count"]
            fig_dru = px.bar(dru_counts, x="Facility Type", y="Count", text_auto=True, title="Cases by Disease Reporting Unit (DRU) Type")
            fig_dru.update_traces(marker_color='#6366f1')
            fig_dru.update_layout(height=450)
            st.plotly_chart(fig_dru, use_container_width=True)

    with tab4:
        st.subheader("Geographic Heatmap" if muncity_input == "All Municipalities" else f"Geographic Heatmap: Barangays in {muncity_input}")
        
        brgy_col = "Barangay" if "Barangay" in filtered_df.columns else ("Brgy" if "Brgy" in filtered_df.columns else None)
        
        if muncity_input != "All Municipalities":
            brgy_geojson, err = fetch_barangay_geojson(muncity_input)
            
            if brgy_geojson and brgy_col:
                all_geojson_brgys = [f['properties']['Standard_Name'] for f in brgy_geojson['features']]
                all_geojson_originals = [f['properties']['Original_Name'] for f in brgy_geojson['features']]
                
                base_df = pd.DataFrame({"Join_Key": all_geojson_brgys, "Barangay_Display": all_geojson_originals, "Base_Cases": 0})
                
                curr_cases = filtered_df.groupby(brgy_col).size().reset_index(name="Filtered_Cases")
                curr_cases["Join_Key"] = curr_cases[brgy_col].apply(clean_brgy_name)
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
                            color='Total Cases', color_continuous_scale="Reds", range_color=[0, max_val], map_style="white-bg",
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
                            key="dengue_brgy_map",
                            config={
                                'scrollZoom': False, 
                                'displayModeBar': True, 
                                'toImageButtonOptions': {'format': 'png', 'filename': f'Dengue_Map_{muncity_input}', 'scale': 4}
                            }
                        )
                    except Exception as e:
                        st.error(f"Plotly encountered an internal error rendering the Barangay map: {e}")
                else:
                    st.warning("No geographic mapping data available for the selected filters.")
            else:
                st.error(err if err else "Barangay column missing in Dengue dataset (Expected 'Barangay').")
                
        else:
            base_df = pd.DataFrame({"Muncity": ALL_ABRA_MUNICIPALITIES, "Base_Cases": 0})
            curr_cases = filtered_df.groupby("Muncity").size().reset_index(name="Filtered_Cases")
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
                            color='Total Cases', color_continuous_scale="Reds", range_color=[0, max_val], map_style="white-bg",
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
                            key="dengue_muni_map",
                            config={
                                'scrollZoom': False, 
                                'displayModeBar': True, 
                                'toImageButtonOptions': {'format': 'png', 'filename': 'Dengue_Map_Abra', 'scale': 4}
                            }
                        )
                    except Exception as e:
                        st.error(f"Plotly encountered an internal error rendering the Municipality map: {e}")
                else:
                    st.warning("No geographic mapping data available for the selected filters.")
            else:
                st.error("Could not fetch the Abra geographic boundaries.")

    with tab5:
        st.subheader("Surveillance Line List")
        display_cols = ["PatientNumber", "FullName", "Muncity", "AgeYears", "Sex", "DOnset", "DAdmit", "DRU", "ClinClass", "Outcome"]
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        st.dataframe(filtered_df[available_cols].sort_values("DOnset", ascending=False), use_container_width=True, hide_index=True, height=600)
