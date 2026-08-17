import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import re

# --- Page Configuration ---
st.set_page_config(
    page_title="Abra PESU | Dengue Surveillance", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- Custom CSS for a Professional UI ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        text-align: center;
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
    }
    div[data-testid="metric-container"] label {
        font-size: 1.1rem !important;
        color: #64748b !important;
        font-weight: 600 !important;
        margin-bottom: 0.5rem;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        font-size: 2.75rem !important;
        color: #0f172a !important;
        font-weight: 800 !important;
    }
    
    h1, h2, h3 {
        color: #1e293b;
    }
    </style>
""", unsafe_allow_html=True)

# --- Helper Function for Map Matching ---
def normalize_name(name):
    """Strips special characters, spaces, and hyphens for a 100% geographic match."""
    if not isinstance(name, str):
        return ""
    name = name.upper().replace("Ñ", "N")
    return re.sub(r'[^A-Z]', '', name)

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
def fetch_abra_geojson():
    urls = [
        "https://raw.githubusercontent.com/macoymejia/geojsonph/master/MuniCities/MuniCities.json",
        "https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/2023/geojson/municities-lowres.json"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'} 
    
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
                        muni_keys = ['ADM3_EN', 'NAME_3', 'MUN_NAME', 'NAME_2', 'MUNICIPALITY']
                        muni_name = ""
                        
                        for k in muni_keys:
                            if k in props_upper and props_upper[k] not in ['ABRA', 'PHILIPPINES']:
                                muni_name = props_upper[k]
                                break
                                
                        # Use the normalizer to clean the geojson properties
                        feature['properties']['Standard_Name'] = normalize_name(muni_name)
                        abra_features.append(feature)
                
                if abra_features:
                    return {"type": "FeatureCollection", "features": abra_features}
        except Exception:
            continue 
            
    return None

df = load_data()

# --- Sidebar Elements ---
with st.sidebar:
    st.markdown("### Data Management")
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("---")
    
    with st.expander("Surveillance Filters", expanded=True):
        muncity_filter = st.multiselect(
            "Select Municipality:", 
            options=sorted(df["Muncity"].dropna().unique()), 
            default=sorted(df["Muncity"].dropna().unique())
        )
        
        sex_filter = st.multiselect(
            "Select Sex:", 
            options=df["Sex"].dropna().unique(), 
            default=df["Sex"].dropna().unique()
        )

# Apply filters
filtered_df = df.query("Muncity in @muncity_filter & Sex in @sex_filter")

# --- Header ---
st.title("Abra PESU: Dengue Surveillance Dashboard")
st.markdown("**Provincial Epidemiology and Surveillance Unit - Official Data Portal**")
st.markdown("---")

# --- Enhanced Key Metrics ---
total_cases = len(filtered_df)
total_deaths = len(filtered_df[filtered_df["Outcome"] == "D"])
avg_age = round(filtered_df["AgeYears"].mean(), 1) if not filtered_df.empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Confirmed Cases", f"{total_cases:,}")
col2.metric("Total Fatalities", f"{total_deaths:,}")
col3.metric("Average Age (Years)", avg_age)
col4.metric("Affected Municipalities", filtered_df["Muncity"].nunique())

st.markdown("<br><br>", unsafe_allow_html=True)

# --- Dashboard Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Epidemiological Trends", "Demographics & Geography", "Choropleth Map", "Raw Line List"])

plotly_template = "plotly_white"

with tab1:
    col_left, col_right = st.columns(2)
    
    with col_left:
        cases_by_week = filtered_df.groupby("MorbidityWeek").size().reset_index(name="Case Count")
        fig_line = px.line(
            cases_by_week, x="MorbidityWeek", y="Case Count", markers=True, 
            title="Dengue Morbidity Trend by Week",
            labels={"MorbidityWeek": "Morbidity Week", "Case Count": "Number of Cases"},
            template=plotly_template
        )
        fig_line.update_traces(line_color='#2563eb', marker=dict(size=8))
        st.plotly_chart(fig_line, use_container_width=True)

    with col_right:
        class_counts = filtered_df["ClinClass"].value_counts().reset_index()
        class_counts.columns = ["Classification", "Count"]
        
        color_map = {
            "NO WARNING SIGNS": "#10b981", 
            "WITH WARNING SIGNS": "#f59e0b", 
            "SEVERE DENGUE": "#ef4444"
        }
        
        fig_pie = px.pie(
            class_counts, names="Classification", values="Count", hole=0.45, 
            title="Clinical Case Classification",
            color="Classification", color_discrete_map=color_map,
            template=plotly_template
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    col_left, col_right = st.columns(2)
    
    with col_left:
        muncity_counts = filtered_df["Muncity"].value_counts().reset_index()
        muncity_counts.columns = ["Municipality", "Count"]
        fig_bar = px.bar(
            muncity_counts.head(15), x="Municipality", y="Count", 
            title="Top 15 Municipalities by Case Volume", 
            text_auto=True,
            template=plotly_template
        )
        fig_bar.update_traces(marker_color='#2563eb')
        fig_bar.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        fig_hist = px.histogram(
            filtered_df, x="AgeYears", nbins=15, 
            title="Age & Sex Demographics", 
            color="Sex",
            barmode="group",
            labels={"AgeYears": "Age (Years)", "count": "Number of Cases"},
            color_discrete_sequence=["#2563eb", "#ec4899"],
            template=plotly_template
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with tab3:
    st.subheader("Geographic Heatmap of Dengue Cases")
    
    map_data = filtered_df.groupby("Muncity").size().reset_index(name="Total Cases")
    
    # Create a normalized join key to match the GeoJSON exactly
    map_data["Join_Key"] = map_data["Muncity"].apply(normalize_name)
    
    abra_geojson = fetch_abra_geojson()
    
    if abra_geojson:
        fig_map = px.choropleth_mapbox(
            map_data,
            geojson=abra_geojson,
            locations='Join_Key',
            featureidkey='properties.Standard_Name', 
            color='Total Cases',
            hover_name='Muncity', # Still show the beautiful, proper name on hover
            color_continuous_scale="Reds",
            mapbox_style="carto-positron",
            zoom=8.5,
            center={"lat": 17.58, "lon": 120.83},
            opacity=0.8,
            title="Dengue Case Distribution across Abra",
            labels={'Total Cases': 'Case Count', 'Join_Key': 'Municipality'}
        )
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.error("Could not fetch the Abra geographic boundaries from the provided URLs.")
        
with tab4:
    st.subheader("Surveillance Line List")
    st.caption("Detailed patient records based on current filters. Scroll horizontally to view all columns.")
    
    display_cols = ["PatientNumber", "FullName", "Muncity", "AgeYears", "Sex", "DOnset", "ClinClass", "Outcome"]
    st.dataframe(
        filtered_df[display_cols].sort_values("DOnset", ascending=False), 
        use_container_width=True, 
        hide_index=True
    )
