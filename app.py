import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re
import unicodedata
import numpy as np
import json
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Abra PESU | Dengue Surveillance", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    :root { color-scheme: light; }
    .stApp { background-color: #f8fafc !important; color: #0f172a !important; }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    h1, h2, h3, h4, h5, h6, span, p, label { color: #1e293b !important; }
    .js-plotly-plot { margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

ALL_ABRA_MUNICIPALITIES = [
    "BANGUED", "BOLINEY", "BUCAY", "BUCLOC", "DAGUIOMAN", "DANGLAS", "DOLORES",
    "LA PAZ", "LACUB", "LAGANGILANG", "LAGAYAN", "LANGIDEN", "LICUAN-BAAY",
    "LUBA", "MALIBCONG", "MANABO", "PEÑARRUBIA", "PIDIGAN", "PILAR",
    "SALLAPADAN", "SAN ISIDRO", "SAN JUAN", "SAN QUINTIN", "TAYUM", "TINEG",
    "TUBO", "VILLAVICIOSA"
]

# --- Core Matching Algorithms ---
def clean_muni_name(raw_name):
    if not isinstance(raw_name, str): return ""
    raw = str(raw_name).upper()
    raw = unicodedata.normalize('NFKD', raw).encode('ASCII', 'ignore').decode('utf-8')
    raw_alpha = re.sub(r'[^A-Z]', '', raw)
    
    if "LICUAN" in raw_alpha or "BAAY" in raw_alpha: return "LICUAN-BAAY"
    if "PENAR" in raw_alpha or "RUBIA" in raw_alpha: return "PEÑARRUBIA"
    if "PAZ" in raw_alpha: return "LA PAZ"
    if "JUAN" in raw_alpha: return "SAN JUAN"
    if "ISIDRO" in raw_alpha: return "SAN ISIDRO"
    if "QUINTIN" in raw_alpha: return "SAN QUINTIN"
    
    for muni in ALL_ABRA_MUNICIPALITIES:
        if re.sub(r'[^A-Z]', '', muni.replace("Ñ", "N")) in raw_alpha:
            return muni
    return raw_name

def clean_brgy_name(raw_name):
    """Aggressively cleans barangay names to ensure matching."""
    if not isinstance(raw_name, str): return ""
    raw = str(raw_name).upper()
    raw = unicodedata.normalize('NFKD', raw).encode('ASCII', 'ignore').decode('utf-8')
    # Strip common variations and words in parentheses (e.g. "Zone 5 Pob. (Nalasin)" -> "ZONE5")
    raw = re.sub(r'\(.*?\)', '', raw) 
    raw = raw.replace("BARANGAY", "").replace("BRGY", "").replace("POBLACION", "POB").replace("POB.", "POB")
    return re.sub(r'[^A-Z0-9]', '', raw)

def scan_props_for_muni(props):
    for val in props.values():
        standardized = clean_muni_name(str(val))
        if standardized in ALL_ABRA_MUNICIPALITIES:
            return standardized
    return None

def extract_brgy_name(props):
    keys = ['ADM4_EN', 'BGY_NAME', 'BRGY_NAME', 'BARANGAY', 'NAME_4', 'NAME_3']
    upper_props = {str(k).upper(): v for k, v in props.items()}
    for k in keys:
        if k in upper_props: return str(upper_props[k])
    for val in props.values():
        v_str = str(val).upper().strip()
        if v_str not in ["ABRA", "PHILIPPINES"] and clean_muni_name(v_str) not in ALL_ABRA_MUNICIPALITIES:
            if len(v_str) > 2: return v_str
    return "UNKNOWN"

def get_polygon_centroid(geometry):
    try:
        if geometry['type'] == 'Polygon':
            coords = np.array(geometry['coordinates'][0])
        elif geometry['type'] == 'MultiPolygon':
            largest_poly = max(geometry['coordinates'], key=lambda p: len(p[0]))
            coords = np.array(largest_poly[0])
        else:
            return None, None
        return np.mean(coords[:, 0]), np.mean(coords[:, 1])
    except:
        return None, None

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1IHdlNfzNtBAOk3LlDN2LstxlRmoGQNTRgF7vZ2P_t4U"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(csv_url)
    
    if 'DOnset' in df.columns: df['DOnset'] = pd.to_datetime(df['DOnset'], errors='coerce')
    if 'Muncity' in df.columns:
        df['Muncity'] = df['Muncity'].apply(clean_muni_name)
    return df

@st.cache_data(ttl="24h")
def fetch_muncity_geojson():
    urls = [
        "https://raw.githubusercontent.com/macoymejia/geojsonph/master/MuniCities/MuniCities.json",
        "https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/2023/geojson/municities-lowres.json"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'} 
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                features = []
                for f in data.get('features', []):
                    muni = scan_props_for_muni(f.get('properties', {}))
                    if muni:
                        f['properties']['Standard_Name'] = muni
                        features.append(f)
                if features: return {"type": "FeatureCollection", "features": features}
        except: continue
    return None

def fetch_barangay_geojson(target_muni):
    if not os.path.exists("abra_barangays.geojson"):
        return None, "File 'abra_barangays.geojson' not found."
    try:
        with open("abra_barangays.geojson", "r", encoding="utf-8") as f:
            data = json.load(f)
            features = []
            target = clean_muni_name(target_muni)
            for feat in data.get('features', []):
                if scan_props_for_muni(feat.get('properties', {})) == target:
                    raw_brgy = extract_brgy_name(feat.get('properties', {}))
                    # Storing original name for hover and clean name for joining
                    feat['properties']['Original_Name'] = raw_brgy
                    feat['properties']['Standard_Name'] = clean_brgy_name(raw_brgy)
                    features.append(feat)
            if features: return {"type": "FeatureCollection", "features": features}, None
            return None, f"No barangays matched inside {target_muni}."
    except Exception as e:
        return None, str(e)

df = load_data()

# --- Sidebar Filters ---
with st.sidebar:
    st.markdown("### Surveillance Filters")
    with st.expander("Filter Options", expanded=True):
        muncity_input = st.multiselect("Select Municipality:", options=sorted(df["Muncity"].dropna().unique()), default=[])
        sex_input = st.multiselect("Select Sex:", options=df["Sex"].dropna().unique(), default=[])
        clin_input = st.multiselect("Clinical Classification:", options=df["ClinClass"].dropna().unique(), default=[])
        
    st.markdown("---")
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

muncity_filter = muncity_input if muncity_input else df["Muncity"].dropna().unique()
sex_filter = sex_input if sex_input else df["Sex"].dropna().unique()
clin_filter = clin_input if clin_input else df["ClinClass"].dropna().unique()
filtered_df = df.query("Muncity in @muncity_filter & Sex in @sex_filter & ClinClass in @clin_filter")

st.title("Abra PESU: Dengue Surveillance Dashboard")
st.markdown("---")

total_cases = len(filtered_df)
total_deaths = len(filtered_df[filtered_df["Outcome"] == "D"]) if "Outcome" in filtered_df.columns else 0
avg_age = round(filtered_df["AgeYears"].mean(), 1) if not filtered_df.empty and "AgeYears" in filtered_df.columns else 0
affected_muni = filtered_df["Muncity"].nunique()

def create_kpi_card(title, value, border_color):
    return f"""
    <div style="background-color: #ffffff; padding: 22px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; border-left: 6px solid {border_color}; text-align: center;">
        <p style="margin: 0; font-size: 1rem; color: #64748b; font-weight: 600; text-transform: uppercase;">{title}</p>
        <h2 style="margin: 10px 0 0 0; font-size: 2.6rem; color: #0f172a; font-weight: 800;">{value}</h2>
    </div>
    """

col1, col2, col3, col4 = st.columns(4)
with col1: st.markdown(create_kpi_card("Total Confirmed Cases", f"{total_cases:,}", "#2563eb"), unsafe_allow_html=True)
with col2: st.markdown(create_kpi_card("Total Fatalities", f"{total_deaths:,}", "#ef4444"), unsafe_allow_html=True)
with col3: st.markdown(create_kpi_card("Average Age (Years)", avg_age, "#10b981"), unsafe_allow_html=True)
with col4: st.markdown(create_kpi_card("Affected Municipalities", f"{affected_muni} / 27", "#f59e0b"), unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Epidemiological Trends", "Demographics & Geography", "Clinical & Laboratory", "Choropleth Map", "Raw Line List"
])

with tab1:
    if "MorbidityWeek" in filtered_df.columns:
        cases_by_week = filtered_df.groupby("MorbidityWeek").size().reset_index(name="Case Count")
        fig_line = px.line(cases_by_week, x="MorbidityWeek", y="Case Count", markers=True, title="Dengue Epidemic Curve by Morbidity Week")
        fig_line.update_traces(line_color='#2563eb', marker=dict(size=10))
        fig_line.update_layout(height=500)
        st.plotly_chart(fig_line, use_container_width=True)

    if "MorbidityMonth" in filtered_df.columns:
        month_counts = filtered_df.groupby("MorbidityMonth").size().reset_index(name="Cases")
        fig_month = px.bar(month_counts, x="MorbidityMonth", y="Cases", text_auto=True, title="Dengue Cases by Morbidity Month")
        fig_month.update_traces(marker_color='#1d4ed8')
        fig_month.update_layout(height=450)
        st.plotly_chart(fig_month, use_container_width=True)
    
with tab2:
    if "Muncity" in filtered_df.columns:
        muncity_counts = filtered_df["Muncity"].value_counts().reset_index()
        muncity_counts.columns = ["Municipality", "Count"]
        fig_bar = px.bar(muncity_counts, x="Municipality", y="Count", title="Total Cases per Municipality", text_auto=True)
        fig_bar.update_traces(marker_color='#2563eb')
        fig_bar.update_layout(xaxis={'categoryorder':'total descending'}, height=500)
        st.plotly_chart(fig_bar, use_container_width=True)

    if "AgeYears" in filtered_df.columns and "Sex" in filtered_df.columns:
        fig_hist = px.histogram(filtered_df, x="AgeYears", nbins=25, title="Age and Sex Distribution of Cases", color="Sex", barmode="group", color_discrete_sequence=["#2563eb", "#ec4899"])
        fig_hist.update_layout(height=500)
        st.plotly_chart(fig_hist, use_container_width=True)
    
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
    if len(muncity_input) == 1:
        target_muni = muncity_input[0]
        st.subheader(f"Geographic Heatmap: Barangays in {target_muni}")
        brgy_geojson, err = fetch_barangay_geojson(target_muni)
        
        if brgy_geojson and "Barangay" in filtered_df.columns:
            # 1. Create a Baseline of ALL Barangays in the GeoJSON to force them to draw
            all_geojson_brgys = [f['properties']['Standard_Name'] for f in brgy_geojson['features']]
            all_geojson_originals = [f['properties']['Original_Name'] for f in brgy_geojson['features']]
            
            base_df = pd.DataFrame({
                "Join_Key": all_geojson_brgys,
                "Barangay_Display": all_geojson_originals,
                "Base_Cases": 0
            })
            
            # 2. Count actual cases from dataset
            curr_cases = filtered_df.groupby("Barangay").size().reset_index(name="Filtered_Cases")
            curr_cases["Join_Key"] = curr_cases["Barangay"].apply(clean_brgy_name)
            
            # Combine duplicates if clean_brgy_name collapsed multiple spelling variations into one
            curr_cases = curr_cases.groupby("Join_Key")["Filtered_Cases"].sum().reset_index()
            
            # 3. Merge Baseline with Actuals
            map_data = pd.merge(base_df, curr_cases, on="Join_Key", how="left")
            map_data["Total Cases"] = map_data["Filtered_Cases"].fillna(0).astype(int)
            
            # Gather coordinates
            lons, lats, texts = [], [], []
            for feat in brgy_geojson['features']:
                std_name = feat['properties']['Standard_Name']
                match = map_data[map_data['Join_Key'] == std_name]
                cases = match['Total Cases'].values[0] if not match.empty else 0
                lon, lat = get_polygon_centroid(feat['geometry'])
                if lon and lat:
                    lons.append(lon); lats.append(lat); texts.append(str(int(cases)))
            
            # Center camera
            cam_lat = np.mean(lats) if lats else 17.58
            cam_lon = np.mean(lons) if lons else 120.83
            
            fig_map = px.choropleth_mapbox(
                map_data, geojson=brgy_geojson, locations='Join_Key', featureidkey='properties.Standard_Name', 
                color='Total Cases', hover_name='Barangay_Display', color_continuous_scale="Reds",
                mapbox_style="carto-positron", zoom=11.5, center={"lat": cam_lat, "lon": cam_lon}, opacity=0.85
            )
            
            fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textposition='middle center', textfont=dict(size=14, color='black'), hoverinfo='skip', showlegend=False))
            fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=700)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            if err:
                st.error(err)
            else:
                st.error("Barangay column not found in data.")
            
    else:
        st.subheader("Geographic Heatmap: Municipalities in Abra")
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
                if lon and lat:
                    lons.append(lon); lats.append(lat); texts.append(str(int(cases)))
                    
            fig_map = px.choropleth_mapbox(
                map_data, geojson=abra_geojson, locations='Muncity', featureidkey='properties.Standard_Name', 
                color='Total Cases', hover_name='Muncity', color_continuous_scale="Reds",
                mapbox_style="carto-positron", zoom=8.8, center={"lat": 17.58, "lon": 120.83}, opacity=0.85
            )
            fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textposition='middle center', textfont=dict(size=14, color='black'), hoverinfo='skip', showlegend=False))
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.error("Could not fetch the Abra geographic boundaries.")

with tab5:
    st.subheader("Surveillance Line List")
    display_cols = ["PatientNumber", "FullName", "Muncity", "AgeYears", "Sex", "DOnset", "DAdmit", "DRU", "ClinClass", "Outcome"]
    available_cols = [col for col in display_cols if col in filtered_df.columns]
    st.dataframe(filtered_df[available_cols].sort_values("DOnset", ascending=False), use_container_width=True, hide_index=True, height=600)