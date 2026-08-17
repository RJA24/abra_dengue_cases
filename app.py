import streamlit as st
import pandas as pd
import plotly.express as px
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="Abra PESU | Dengue Surveillance", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for a Professional UI ---
st.markdown("""
    <style>
    /* Adjust top padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Enhanced KPI Metric Cards */
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
    
    /* Custom header text color */
    h1, h2, h3 {
        color: #1e293b;
    }
    </style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("Abra PESU: Dengue Surveillance Dashboard")
st.markdown("**Provincial Epidemiology and Surveillance Unit - Official Data Portal**")
st.markdown("---")

# --- Load Data ---
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1IHdlNfzNtBAOk3LlDN2LstxlRmoGQNTRgF7vZ2P_t4U"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(csv_url)
    
    if 'DOnset' in df.columns:
        df['DOnset'] = pd.to_datetime(df['DOnset'], errors='coerce')
    return df

df = load_data()

# --- Hidden/Collapsible Filters ---
with st.expander("Surveillance Filters", expanded=False):
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        muncity_filter = st.multiselect(
            "Select Municipality:", 
            options=sorted(df["Muncity"].dropna().unique()), 
            default=sorted(df["Muncity"].dropna().unique())
        )
    
    with col_filter2:
        sex_filter = st.multiselect(
            "Select Sex:", 
            options=df["Sex"].dropna().unique(), 
            default=df["Sex"].dropna().unique()
        )

# Apply filters
filtered_df = df.query("Muncity in @muncity_filter & Sex in @sex_filter")

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
    
    # Aggregate data for the map
    map_data = filtered_df.groupby("Muncity").size().reset_index(name="Total Cases")
    
    try:
        # Load the GeoJSON file containing Abra municipality boundaries
        # Ensure 'abra_municipalities.geojson' is uploaded to your GitHub repository
        with open('abra_municipalities.geojson') as f:
            abra_geojson = json.load(f)
            
        fig_map = px.choropleth(
            map_data,
            geojson=abra_geojson,
            locations='Muncity',
            featureidkey='properties.NAME_2', # Update this key based on your GeoJSON properties
            color='Total Cases',
            color_continuous_scale="Reds",
            title="Dengue Case Distribution across Abra",
            labels={'Total Cases': 'Case Count'}
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig_map, use_container_width=True)
        
    except FileNotFoundError:
        st.warning("Map cannot be rendered: 'abra_municipalities.geojson' file is missing from the directory.")
        st.info("To enable this feature, obtain a valid GeoJSON file of Abra's municipalities and upload it to your project folder.")
        
with tab4:
    st.subheader("Surveillance Line List")
    st.caption("Detailed patient records based on current filters. Scroll horizontally to view all columns.")
    
    display_cols = ["PatientNumber", "FullName", "Muncity", "AgeYears", "Sex", "DOnset", "ClinClass", "Outcome"]
    st.dataframe(
        filtered_df[display_cols].sort_values("DOnset", ascending=False), 
        use_container_width=True, 
        hide_index=True
    )
