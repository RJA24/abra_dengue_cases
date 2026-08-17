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

# --- Custom CSS for Enforced Light Mode & Professional UI ---
st.markdown("""
    <style>
    /* Force Light Theme Colors Globally */
    :root {
        color-scheme: light;
    }
    
    /* Main App Background & Text */
    .stApp {
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc !important;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Padding & Layout Adjustments */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    
    /* Hide Default Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: visible;}
    
    /* Text Color Fixes */
    h1, h2, h3, h4, h5, h6, span, p, label {
        color: #1e293b !important;
    }
    
    .js-plotly-plot {
        margin-bottom: 2rem;
    }
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

# --- Helper Function for Map Matching ---
def normalize_name(name):
    """Normalizes municipality names, handling enye and encoding quirks."""
    if not isinstance(name, str):
        return ""
    name = name.upper()
    name = name.replace("Ã‘", "N").replace("Ñ", "N")
    name = re.sub(r'\(.*?\)', '', name)
    return re.sub(r'[^A-Z]', '', name)

# --- Data & GeoJSON Loading ---
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1IHdlNfzNtBAOk3LlDN2LstxlRmoGQNTRgF7vZ2P_t4U"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(csv_url)
    
    if 'DOnset' in df.columns:
        df['DOnset'] = pd.to_datetime(df['DOnset'], errors='coerce')
    if 'DAdmit' in df.columns:
        df['DAdmit'] = pd.to_datetime(df['DAdmit'], errors='coerce')
        
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
                                
                        feature['properties']['Standard_Name'] = normalize_name(muni_name)
                        abra_features.append(feature)
                
                if abra_features:
                    return {"type": "FeatureCollection", "features": abra_features}
        except Exception:
            continue 
            
    return None

df = load_data()

# --- Sidebar: Filters & Refresh Button ---
with st.sidebar:
    st.markdown("### Surveillance Filters")
    
    with st.expander("Filter Options", expanded=True):
        muncity_input = st.multiselect(
            "Select Municipality (Leave blank for all):", 
            options=sorted(df["Muncity"].dropna().unique()), 
            default=[]
        )
        
        sex_input = st.multiselect(
            "Select Sex (Leave blank for all):", 
            options=df["Sex"].dropna().unique(), 
            default=[]
        )
        
        clin_input = st.multiselect(
            "Clinical Classification (Leave blank for all):",
            options=df["ClinClass"].dropna().unique(),
            default=[]
        )
        
    st.markdown("---")
    
    st.markdown("### Data Management")
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Apply Filter Logic (Empty = All) ---
muncity_filter = muncity_input if muncity_input else df["Muncity"].dropna().unique()
sex_filter = sex_input if sex_input else df["Sex"].dropna().unique()
clin_filter = clin_input if clin_input else df["ClinClass"].dropna().unique()

filtered_df = df.query("Muncity in @muncity_filter & Sex in @sex_filter & ClinClass in @clin_filter")

# --- Header ---
st.title("Abra PESU: Dengue Surveillance Dashboard")
st.markdown("**Provincial Epidemiology and Surveillance Unit - Official Data Portal**")
st.markdown("---")

# --- HTML KPI Cards ---
total_cases = len(filtered_df)
total_deaths = len(filtered_df[filtered_df["Outcome"] == "D"])
avg_age = round(filtered_df["AgeYears"].mean(), 1) if not filtered_df.empty else 0
affected_muni = filtered_df["Muncity"].nunique()

def create_kpi_card(title, value, border_color):
    return f"""
    <div style="background-color: #ffffff; padding: 22px; border-radius: 10px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; 
                border-left: 6px solid {border_color}; text-align: center;">
        <p style="margin: 0; font-size: 1rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">{title}</p>
        <h2 style="margin: 10px 0 0 0; font-size: 2.6rem; color: #0f172a; font-weight: 800;">{value}</h2>
    </div>
    """

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(create_kpi_card("Total Confirmed Cases", f"{total_cases:,}", "#2563eb"), unsafe_allow_html=True)
with col2:
    st.markdown(create_kpi_card("Total Fatalities", f"{total_deaths:,}", "#ef4444"), unsafe_allow_html=True)
with col3:
    st.markdown(create_kpi_card("Average Age (Years)", avg_age, "#10b981"), unsafe_allow_html=True)
with col4:
    st.markdown(create_kpi_card("Affected Municipalities", f"{affected_muni} / 27", "#f59e0b"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Dashboard Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Epidemiological Trends", 
    "Demographics & Geography", 
    "Clinical & Laboratory", 
    "Choropleth Map", 
    "Raw Line List"
])

plotly_template = "plotly_white"

with tab1:
    cases_by_week = filtered_df.groupby("MorbidityWeek").size().reset_index(name="Case Count")
    fig_line = px.line(
        cases_by_week, x="MorbidityWeek", y="Case Count", markers=True, 
        title="Dengue Epidemic Curve by Morbidity Week",
        labels={"MorbidityWeek": "Morbidity Week", "Case Count": "Number of Cases"},
        template=plotly_template
    )
    fig_line.update_traces(line_color='#2563eb', marker=dict(size=10))
    fig_line.update_layout(height=500)
    st.plotly_chart(fig_line, use_container_width=True)

    month_counts = filtered_df.groupby("MorbidityMonth").size().reset_index(name="Cases")
    fig_month = px.bar(
        month_counts, x="MorbidityMonth", y="Cases", text_auto=True,
        title="Dengue Cases by Morbidity Month",
        labels={"MorbidityMonth": "Month Number", "Cases": "Total Cases"},
        template=plotly_template
    )
    fig_month.update_traces(marker_color='#1d4ed8')
    fig_month.update_layout(height=450)
    st.plotly_chart(fig_month, use_container_width=True)

with tab2:
    muncity_counts = filtered_df["Muncity"].value_counts().reset_index()
    muncity_counts.columns = ["Municipality", "Count"]
    fig_bar = px.bar(
        muncity_counts, x="Municipality", y="Count", 
        title="Total Cases per Municipality", 
        text_auto=True,
        template=plotly_template
    )
    fig_bar.update_traces(marker_color='#2563eb')
    fig_bar.update_layout(xaxis={'categoryorder':'total descending'}, height=500)
    st.plotly_chart(fig_bar, use_container_width=True)

    fig_hist = px.histogram(
        filtered_df, x="AgeYears", nbins=25, 
        title="Age and Sex Distribution of Cases", 
        color="Sex",
        barmode="group",
        labels={"AgeYears": "Age (Years)", "count": "Number of Cases"},
        color_discrete_sequence=["#2563eb", "#ec4899"],
        template=plotly_template
    )
    fig_hist.update_layout(height=500)
    st.plotly_chart(fig_hist, use_container_width=True)

    if 'ipgroup' in filtered_df.columns:
        ip_df = filtered_df['ipgroup'].fillna('Non-IP / Not Specified').value_counts().reset_index()
        ip_df.columns = ['Group', 'Count']
        fig_ip = px.bar(
            ip_df, x='Group', y='Count', text_auto=True,
            title="Dengue Cases by Indigenous Peoples (IP) Group",
            template=plotly_template
        )
        fig_ip.update_traces(marker_color='#059669')
        fig_ip.update_layout(height=450)
        st.plotly_chart(fig_ip, use_container_width=True)

with tab3:
    class_counts = filtered_df["ClinClass"].value_counts().reset_index()
    class_counts.columns = ["Classification", "Count"]
    
    color_map = {
        "NO WARNING SIGNS": "#10b981", 
        "WITH WARNING SIGNS": "#f59e0b", 
        "SEVERE DENGUE": "#ef4444"
    }
    
    fig_pie = px.pie(
        class_counts, names="Classification", values="Count", hole=0.45, 
        title="Clinical Severity Classification",
        color="Classification", color_discrete_map=color_map,
        template=plotly_template
    )
    fig_pie.update_layout(height=500)
    st.plotly_chart(fig_pie, use_container_width=True)

    if 'DRU' in filtered_df.columns:
        dru_counts = filtered_df["DRU"].fillna("Unspecified").value_counts().reset_index()
        dru_counts.columns = ["Facility Type", "Count"]
        fig_dru = px.bar(
            dru_counts, x="Facility Type", y="Count", text_auto=True,
            title="Cases by Disease Reporting Unit (DRU) Type",
            template=plotly_template
        )
        fig_dru.update_traces(marker_color='#6366f1')
        fig_dru.update_layout(height=450)
        st.plotly_chart(fig_dru, use_container_width=True)

    if 'LabTest' in filtered_df.columns and 'LabRes' in filtered_df.columns:
        lab_counts = filtered_df.groupby(['LabTest', 'LabRes']).size().reset_index(name='Count')
        fig_lab = px.bar(
            lab_counts, x="LabTest", y="Count", color="LabRes", barmode="stack",
            title="Diagnostic Modality and Laboratory Results",
            template=plotly_template
        )
        fig_lab.update_layout(height=500)
        st.plotly_chart(fig_lab, use_container_width=True)

with tab4:
    st.subheader("Geographic Heatmap of Dengue Cases")
    
    base_df = pd.DataFrame({"Muncity": ALL_ABRA_MUNICIPALITIES, "Base_Cases": 0})
    curr_cases = filtered_df.groupby("Muncity").size().reset_index(name="Filtered_Cases")
    
    map_data = pd.merge(base_df, curr_cases, on="Muncity", how="left")
    map_data["Total Cases"] = map_data["Filtered_Cases"].fillna(0).astype(int)
    map_data["Join_Key"] = map_data["Muncity"].apply(normalize_name)
    
    abra_geojson = fetch_abra_geojson()
    
    if abra_geojson:
        fig_map = px.choropleth_mapbox(
            map_data,
            geojson=abra_geojson,
            locations='Join_Key',
            featureidkey='properties.Standard_Name', 
            color='Total Cases',
            hover_name='Muncity',
            color_continuous_scale="Reds",
            mapbox_style="carto-positron",
            zoom=8.8,
            center={"lat": 17.58, "lon": 120.83},
            opacity=0.85,
            title="Dengue Incidence Map Across Abra Municipalities",
            labels={'Total Cases': 'Case Count', 'Join_Key': 'Municipality'}
        )
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=700)
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.error("Could not fetch the Abra geographic boundaries from the repository URLs.")

with tab5:
    st.subheader("Surveillance Line List")
    st.caption("Detailed patient records based on current filters. Scroll horizontally to view all columns.")
    
    display_cols = [
        "PatientNumber", "FullName", "Muncity", "AgeYears", "Sex", 
        "DOnset", "DAdmit", "DRU", "ClinClass", "LabTest", "LabRes", "Outcome"
    ]
    available_cols = [col for col in display_cols if col in filtered_df.columns]
    
    st.dataframe(
        filtered_df[available_cols].sort_values("DOnset", ascending=False), 
        use_container_width=True, 
        hide_index=True,
        height=600
    )