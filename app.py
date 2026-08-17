import streamlit as st
import pandas as pd
import plotly.express as px

# --- Page Configuration ---
st.set_page_config(
    page_title="Abra PESU | Dengue Surveillance", 
    page_icon="📊", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- Custom CSS for a Professional UI ---
st.markdown("""
    <style>
    /* Adjust top padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Style the metric cards */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #0056b3; /* DOH Blue accent */
    }
    /* Hide default Streamlit elements for a clean app feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* Custom header text color */
    h1, h2, h3 {
        color: #2c3e50;
    }
    </style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("📊 Abra PESU: Dengue Surveillance Dashboard")
st.markdown("**Provincial Epidemiology and Surveillance Unit - Official Data Portal**")
st.markdown("---")

# --- Load Data ---
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1IHdlNfzNtBAOk3LlDN2LstxlRmoGQNTRgF7vZ2P_t4U"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(csv_url)
    # Ensure dates are datetime objects for better filtering
    if 'DOnset' in df.columns:
        df['DOnset'] = pd.to_datetime(df['DOnset'], errors='coerce')
    return df

df = load_data()

# --- Sidebar Filters ---
with st.sidebar:
    st.markdown("### 🔍 Surveillance Filters")
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
    
    st.markdown("---")
    st.caption("Data is pulled directly from the official PESU registry.")

# Apply filters
filtered_df = df.query("Muncity in @muncity_filter & Sex in @sex_filter")

# --- Top Key Metrics ---
total_cases = len(filtered_df)
total_deaths = len(filtered_df[filtered_df["Outcome"] == "D"])
avg_age = round(filtered_df["AgeYears"].mean(), 1) if not filtered_df.empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Confirmed Cases", f"{total_cases:,}")
col2.metric("Total Fatalities", f"{total_deaths:,}")
col3.metric("Average Age (Years)", avg_age)
col4.metric("Affected Municipalities", filtered_df["Muncity"].nunique())

st.markdown("<br>", unsafe_allow_html=True)

# --- Dashboard Tabs ---
tab1, tab2, tab3 = st.tabs(["📈 Epidemiological Trends", "🗺️ Demographics & Geography", "📋 Raw Line List"])

# Chart Template
plotly_template = "plotly_white"

with tab1:
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Cases over time
        cases_by_week = filtered_df.groupby("MorbidityWeek").size().reset_index(name="Case Count")
        fig_line = px.line(
            cases_by_week, x="MorbidityWeek", y="Case Count", markers=True, 
            title="Dengue Morbidity Trend by Week",
            labels={"MorbidityWeek": "Morbidity Week", "Case Count": "Number of Cases"},
            template=plotly_template
        )
        fig_line.update_traces(line_color='#0056b3', marker=dict(size=8))
        st.plotly_chart(fig_line, use_container_width=True)

    with col_right:
        # Clinical Classification
        class_counts = filtered_df["ClinClass"].value_counts().reset_index()
        class_counts.columns = ["Classification", "Count"]
        
        # Color mapping for severity
        color_map = {
            "NO WARNING SIGNS": "#28a745", 
            "WITH WARNING SIGNS": "#ffc107", 
            "SEVERE DENGUE": "#dc3545"
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
        # Cases by Municipality
        muncity_counts = filtered_df["Muncity"].value_counts().reset_index()
        muncity_counts.columns = ["Municipality", "Count"]
        fig_bar = px.bar(
            muncity_counts.head(15), x="Municipality", y="Count", 
            title="Top 15 Municipalities by Case Volume", 
            text_auto=True,
            template=plotly_template
        )
        fig_bar.update_traces(marker_color='#0056b3')
        fig_bar.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        # Age Distribution
        fig_hist = px.histogram(
            filtered_df, x="AgeYears", nbins=15, 
            title="Age & Sex Demographics", 
            color="Sex",
            barmode="group",
            labels={"AgeYears": "Age (Years)", "count": "Number of Cases"},
            color_discrete_sequence=["#0056b3", "#e83e8c"],
            template=plotly_template
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with tab3:
    st.subheader("Surveillance Line List")
    st.caption("Detailed patient records based on current filters. Scroll horizontally to view all columns.")
    
    display_cols = ["PatientNumber", "FullName", "Muncity", "AgeYears", "Sex", "DOnset", "ClinClass", "Outcome"]
    # Provide a clean dataframe view without the index
    st.dataframe(
        filtered_df[display_cols].sort_values("DOnset", ascending=False), 
        use_container_width=True, 
        hide_index=True
    )
