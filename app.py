import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re
import unicodedata
import numpy as np
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="Abra PESU | Dengue Surveillance", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Enforced Light Mode & UI Polish ---
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

# List of all 27 official municipalities in Abra
ALL_ABRA_MUNICIPALITIES = [
    "BANGUED", "BOLINEY", "BUCAY", "BUCLOC", "DAGUIOMAN", "DANGLAS", "DOLORES",
    "LA PAZ", "LACUB", "LAGANGILANG", "LAGAYAN", "LANGIDEN", "LICUAN-BAAY",
    "LUBA", "MALIBCONG", "MANABO", "PEÑARRUBIA", "PIDIGAN", "PILAR",
    "SALLAPADAN", "SAN ISIDRO", "SAN JUAN", "SAN QUINTIN", "TAYUM", "TINEG",
    "TUBO", "VILLAVICIOSA"
]

# --- Helper Functions ---
def normalize_name(name):
    """Safely strips accents (e.g., Ñ to N), parentheses, and spaces for matching."""
    if not isinstance(name, str):
        return ""
    name = str(name).upper()
    # Normalize unicode to separate characters from their accents, then drop the accents
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    name = re.sub(r'\(.*?\)', '', name)
    return re.sub(r'[^A-Z]', '', name)

def get_polygon_centroid(geometry):
    """Calculates the center coordinate of a GeoJSON polygon to place text labels."""
    coords = []
    if geometry['type'] == 'Polygon':
        for ring in geometry['coordinates']:
            coords.extend(ring)
    elif geometry['type'] == 'MultiPolygon':
        for poly in geometry['coordinates']:
            for ring in poly:
                coords.extend(ring)
    if not coords:
        return None, None
    coords = np.array(coords)
    return np.mean(coords[:, 0]), np.mean(coords[:, 1]) # lon, lat

# --- Data & GeoJSON Loading ---
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1IHdlNfzNtBAOk3LlDN2LstxlRmoGQNTRgF7vZ2P_t4U"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(csv_url)
    if 'DOnset' in df.columns:
        df['DOnset'] = pd.to_datetime(df['DOnset'], errors='coerce')
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
                    props_upper = {str(k).upper(): str(v).upper() for k, v in props.items()}
                    if 'ABRA' in props_upper.values():
                        muni_name = props_upper.get('ADM3_EN', props_upper.get('NAME_3', props_upper.get('MUN_NAME', '')))
                        feature['properties']['Standard_Name'] = normalize_name(muni_name)
                        abra_features.append(feature)
                if abra_features:
                    return {"type": "FeatureCollection", "features": abra_features}
        except Exception:
            continue 
    return None

@st.cache_data(ttl="24h")
def fetch_barangay_geojson(municipality):
    """Attempts to load a local barangay geojson file uploaded to your repo."""
    try:
        with open("abra_barangays.geojson", "r") as f:
            data = json.load(f)
            features = []
            target_muni = normalize_name(municipality)
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                props_upper = {str(k).upper(): str(v).upper() for k, v in props.items()}
                
                # Check if this barangay belongs to the target municipality
                if target_muni in normalize_name(str(props_upper.values())):
                    brgy_name = props_upper.get('BGY_NAME', props_upper.get('NAME_4', props_upper.get('BARANGAY', '')))
                    feature['properties']['Standard_Name'] = normalize_name(brgy_name)
                    features.append(feature)
            return {"type": "FeatureCollection", "features": features} if features else None
    except FileNotFoundError:
        return None

df = load_data()

# --- Sidebar: Filters & Refresh Button ---
with st.sidebar:
    st.markdown("### Surveillance Filters")
    with st.expander("Filter Options", expanded=True):
        muncity_input = st.multiselect("Select Municipality (Leave blank for all):", options=sorted(df["Muncity"].dropna().unique()), default=[])
        sex_input = st.multiselect("Select Sex (Leave blank for all):", options=df["Sex"].dropna().unique(), default=[])
        clin_input = st.multiselect("Clinical Classification:", options=df["ClinClass"].dropna().unique(), default=[])
        
    st.markdown("---")
    st.markdown("### Data Management")
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Apply Filters
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

# (Tabs 1, 2, 3, 5 remain the same as previous iterations; omitting here for brevity, keep your existing code for those tabs)

with tab4:
    # Check if we should render Municipality Level or Barangay Level
    if len(muncity_input) == 1:
        target_muni = muncity_input[0]
        st.subheader(f"Geographic Heatmap: Barangays in {target_muni}")
        
        brgy_geojson = fetch_barangay_geojson(target_muni)
        
        if brgy_geojson:
            map_data = filtered_df.groupby("Barangay").size().reset_index(name="Total Cases")
            map_data["Join_Key"] = map_data["Barangay"].apply(normalize_name)
            
            fig_map = px.choropleth_mapbox(
                map_data, geojson=brgy_geojson, locations='Join_Key', featureidkey='properties.Standard_Name', 
                color='Total Cases', hover_name='Barangay', color_continuous_scale="Reds",
                mapbox_style="carto-positron", zoom=11.5, opacity=0.85
            )
            
            # Add text labels on map
            lons, lats, texts = [], [], []
            for feature in brgy_geojson['features']:
                std_name = feature['properties']['Standard_Name']
                match = map_data[map_data['Join_Key'] == std_name]
                cases = match['Total Cases'].values[0] if not match.empty else 0
                lon, lat = get_polygon_centroid(feature['geometry'])
                if lon and lat:
                    lons.append(lon); lats.append(lat); texts.append(f"<b>{cases}</b>")
            
            fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=13, color='black'), hoverinfo='skip'))
            fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=700)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info(f"To view Barangay-level data for {target_muni}, please upload an `abra_barangays.geojson` file to your GitHub repository.")
            
    else:
        st.subheader("Geographic Heatmap: Municipalities in Abra")
        
        base_df = pd.DataFrame({"Muncity": ALL_ABRA_MUNICIPALITIES, "Base_Cases": 0})
        curr_cases = filtered_df.groupby("Muncity").size().reset_index(name="Filtered_Cases")
        
        map_data = pd.merge(base_df, curr_cases, on="Muncity", how="left")
        map_data["Total Cases"] = map_data["Filtered_Cases"].fillna(0).astype(int)
        map_data["Join_Key"] = map_data["Muncity"].apply(normalize_name)
        
        abra_geojson = fetch_muncity_geojson()
        
        if abra_geojson:
            fig_map = px.choropleth_mapbox(
                map_data, geojson=abra_geojson, locations='Join_Key', featureidkey='properties.Standard_Name', 
                color='Total Cases', hover_name='Muncity', color_continuous_scale="Reds",
                mapbox_style="carto-positron", zoom=8.8, center={"lat": 17.58, "lon": 120.83}, opacity=0.85
            )
            
            # Add text labels on map
            lons, lats, texts = [], [], []
            for feature in abra_geojson['features']:
                std_name = feature['properties']['Standard_Name']
                match = map_data[map_data['Join_Key'] == std_name]
                cases = match['Total Cases'].values[0] if not match.empty else 0
                lon, lat = get_polygon_centroid(feature['geometry'])
                if lon and lat:
                    lons.append(lon); lats.append(lat); texts.append(f"<b>{cases}</b>")
            
            fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=14, color='black'), hoverinfo='skip'))
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.error("Could not fetch the Abra geographic boundaries from the repository URLs.")