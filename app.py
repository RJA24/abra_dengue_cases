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

# --- Aggressive Name Matching Algorithms ---
def get_standard_muni_name(raw_name):
    if not isinstance(raw_name, str): return ""
    raw = raw_name.upper()
    raw = unicodedata.normalize('NFKD', raw).encode('ASCII', 'ignore').decode('utf-8')
    raw = re.sub(r'[^A-Z]', '', raw)
    
    if "LICUAN" in raw or "BAAY" in raw: return "LICUAN-BAAY"
    if "PENAR" in raw: return "PEÑARRUBIA"
    if "PAZ" in raw: return "LA PAZ"
    if "JUAN" in raw: return "SAN JUAN"
    if "ISIDRO" in raw: return "SAN ISIDRO"
    if "QUINTIN" in raw: return "SAN QUINTIN"
    
    for muni in ALL_ABRA_MUNICIPALITIES:
        clean_muni = muni.replace("Ñ", "N").replace("-", "")
        if clean_muni in raw: return muni
    return raw_name

def scan_props_for_muni(props):
    """Scans all property values in a GeoJSON feature to find an Abra municipality match."""
    for val in props.values():
        standardized = get_standard_muni_name(str(val))
        if standardized in ALL_ABRA_MUNICIPALITIES:
            return standardized
    return None

def extract_brgy_name(props):
    """Searches common barangay column names to extract the barangay string."""
    keys_to_check = ['ADM4_EN', 'BGY_NAME', 'BRGY_NAME', 'BARANGAY', 'NAME_4', 'NAME_3']
    props_upper_keys = {str(k).upper(): v for k, v in props.items()}
    
    for key in keys_to_check:
        if key in props_upper_keys:
            return str(props_upper_keys[key]).upper().strip()
            
    # Fallback: Just return the longest string that isn't the province or municipality
    for val in props.values():
        val_str = str(val).upper().strip()
        if val_str not in ["ABRA", "PHILIPPINES"] and get_standard_muni_name(val_str) not in ALL_ABRA_MUNICIPALITIES:
            if len(val_str) > 2: return val_str
    return "UNKNOWN"

def get_polygon_centroid(geometry):
    coords = []
    if geometry['type'] == 'Polygon':
        for ring in geometry['coordinates']: coords.extend(ring)
    elif geometry['type'] == 'MultiPolygon':
        for poly in geometry['coordinates']:
            for ring in poly: coords.extend(ring)
    if not coords: return None, None
    coords = np.array(coords)
    return np.mean(coords[:, 0]), np.mean(coords[:, 1])

# --- Data & GeoJSON Loading ---
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1IHdlNfzNtBAOk3LlDN2LstxlRmoGQNTRgF7vZ2P_t4U"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(csv_url)
    if 'DOnset' in df.columns: df['DOnset'] = pd.to_datetime(df['DOnset'], errors='coerce')
    
    if 'Muncity' in df.columns:
        df['Muncity'] = df['Muncity'].astype(str).str.upper().str.strip()
        df['Muncity'] = df['Muncity'].apply(get_standard_muni_name)
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
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                abra_features = []
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    # Aggressive scan: Is this shape in Abra?
                    muni_match = scan_props_for_muni(props)
                    if muni_match:
                        feature['properties']['Standard_Name'] = muni_match
                        abra_features.append(feature)
                if abra_features:
                    return {"type": "FeatureCollection", "features": abra_features}
        except Exception:
            continue 
    return None

def fetch_barangay_geojson(target_municipality):
    if not os.path.exists("abra_barangays.geojson"):
        return None, "File 'abra_barangays.geojson' not found in the repository."
    try:
        with open("abra_barangays.geojson", "r", encoding="utf-8") as f:
            data = json.load(f)
            features = []
            target = get_standard_muni_name(target_municipality)
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                
                # Check if this shape belongs to our target municipality
                if scan_props_for_muni(props) == target:
                    feature['properties']['Standard_Name'] = extract_brgy_name(props)
                    features.append(feature)
                    
            if not features:
                # DEBUG SAFETY NET: If it fails, pull the first item's properties so the user can see what's wrong.
                sample_props = data.get('features', [{}])[0].get('properties', {})
                debug_msg = f"No barangays matched '{target}'.\n\n**Debug Info - Here are the exact properties inside your GeoJSON file:**\n```json\n{json.dumps(sample_props, indent=2)}\n```"
                return None, debug_msg
                
            return {"type": "FeatureCollection", "features": features}, None
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

df = load_data()

# --- Sidebar: Filters & Refresh Button ---
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

# --- Header & KPIs ---
st.title("Abra PESU: Dengue Surveillance Dashboard")
st.markdown("**Provincial Epidemiology and Surveillance Unit - Official Data Portal**")
st.markdown("---")

total_cases = len(filtered_df)
total_deaths = len(filtered_df[filtered_df["Outcome"] == "D"])
avg_age = round(filtered_df["AgeYears"].mean(), 1) if not filtered_df.empty else 0
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

# --- Dashboard Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Epidemiological Trends", "Demographics & Geography", "Clinical & Laboratory", "Choropleth Map", "Raw Line List"
])

with tab1:
    cases_by_week = filtered_df.groupby("MorbidityWeek").size().reset_index(name="Case Count")
    fig_line = px.line(cases_by_week, x="MorbidityWeek", y="Case Count", markers=True, title="Dengue Epidemic Curve by Morbidity Week")
    fig_line.update_traces(line_color='#2563eb', marker=dict(size=10))
    fig_line.update_layout(height=500)
    st.plotly_chart(fig_line, use_container_width=True)

    month_counts = filtered_df.groupby("MorbidityMonth").size().reset_index(name="Cases")
    fig_month = px.bar(month_counts, x="MorbidityMonth", y="Cases", text_auto=True, title="Dengue Cases by Morbidity Month")
    fig_month.update_traces(marker_color='#1d4ed8')
    fig_month.update_layout(height=450)
    st.plotly_chart(fig_month, use_container_width=True)

with tab2:
    muncity_counts = filtered_df["Muncity"].value_counts().reset_index()
    muncity_counts.columns = ["Municipality", "Count"]
    fig_bar = px.bar(muncity_counts, x="Municipality", y="Count", title="Total Cases per Municipality", text_auto=True)
    fig_bar.update_traces(marker_color='#2563eb')
    fig_bar.update_layout(xaxis={'categoryorder':'total descending'}, height=500)
    st.plotly_chart(fig_bar, use_container_width=True)

    fig_hist = px.histogram(filtered_df, x="AgeYears", nbins=25, title="Age and Sex Distribution of Cases", color="Sex", barmode="group", color_discrete_sequence=["#2563eb", "#ec4899"])
    fig_hist.update_layout(height=500)
    st.plotly_chart(fig_hist, use_container_width=True)

with tab3:
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
        
        brgy_geojson, err_msg = fetch_barangay_geojson(target_muni)
        
        if brgy_geojson:
            map_data = filtered_df.groupby("Barangay").size().reset_index(name="Total Cases")
            map_data["Join_Key"] = map_data["Barangay"].astype(str).str.upper().str.strip()
            
            fig_map = px.choropleth_mapbox(
                map_data, geojson=brgy_geojson, locations='Join_Key', featureidkey='properties.Standard_Name', 
                color='Total Cases', hover_name='Barangay', color_continuous_scale="Reds",
                mapbox_style="carto-positron", zoom=11.5, opacity=0.85
            )
            
            lons, lats, texts = [], [], []
            for feature in brgy_geojson['features']:
                std_name = feature['properties']['Standard_Name']
                match = map_data[map_data['Join_Key'] == std_name]
                cases = match['Total Cases'].values[0] if not match.empty else 0
                lon, lat = get_polygon_centroid(feature['geometry'])
                if lon and lat:
                    lons.append(lon); lats.append(lat); texts.append(str(int(cases)))
            
            fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=14, color='black', family="Arial Black"), hoverinfo='skip'))
            fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=700)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.error(err_msg)
            
    else:
        st.subheader("Geographic Heatmap: Municipalities in Abra")
        base_df = pd.DataFrame({"Muncity": ALL_ABRA_MUNICIPALITIES, "Base_Cases": 0})
        curr_cases = filtered_df.groupby("Muncity").size().reset_index(name="Filtered_Cases")
        map_data = pd.merge(base_df, curr_cases, on="Muncity", how="left")
        map_data["Total Cases"] = map_data["Filtered_Cases"].fillna(0).astype(int)
        
        abra_geojson = fetch_muncity_geojson()
        
        if abra_geojson:
            fig_map = px.choropleth_mapbox(
                map_data, geojson=abra_geojson, locations='Muncity', featureidkey='properties.Standard_Name', 
                color='Total Cases', hover_name='Muncity', color_continuous_scale="Reds",
                mapbox_style="carto-positron", zoom=8.8, center={"lat": 17.58, "lon": 120.83}, opacity=0.85
            )
            
            lons, lats, texts = [], [], []
            for feature in abra_geojson['features']:
                std_name = feature['properties']['Standard_Name']
                match = map_data[map_data['Muncity'] == std_name]
                cases = match['Total Cases'].values[0] if not match.empty else 0
                lon, lat = get_polygon_centroid(feature['geometry'])
                if lon and lat:
                    lons.append(lon); lats.append(lat); texts.append(str(int(cases)))
            
            fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=14, color='black', family="Arial Black"), hoverinfo='skip'))
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.error("Could not fetch the Abra geographic boundaries.")

with tab5:
    st.subheader("Surveillance Line List")
    display_cols = ["PatientNumber", "FullName", "Muncity", "AgeYears", "Sex", "DOnset", "DAdmit", "DRU", "ClinClass", "Outcome"]
    available_cols = [col for col in display_cols if col in filtered_df.columns]
    st.dataframe(filtered_df[available_cols].sort_values("DOnset", ascending=False), use_container_width=True, hide_index=True, height=600)