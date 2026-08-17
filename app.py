import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuration ---
st.set_page_config(page_title="Abra Dengue Dashboard", page_icon="🦟", layout="wide")
st.title("🦟 Abra Dengue Cases Dashboard")
st.markdown("Interactive dashboard for Dengue cases in Abra as of August 13, 2026.")

# --- Load Data ---
@st.cache_data
def load_data():
    # Load the specific sheet 'ABRA' from the Excel file
    filepath = "ABRA_DENGUE cases as of August 13, 2026.xlsx"
    df = pd.read_excel(filepath, sheet_name="ABRA")
    return df

df = load_data()

# --- Sidebar Filters ---
st.sidebar.header("Filter Data")
muncity_filter = st.sidebar.multiselect(
    "Select Municipality:", 
    options=df["Muncity"].dropna().unique(), 
    default=df["Muncity"].dropna().unique()
)

sex_filter = st.sidebar.multiselect(
    "Select Sex:", 
    options=df["Sex"].dropna().unique(), 
    default=df["Sex"].dropna().unique()
)

# Apply filters
filtered_df = df.query("Muncity in @muncity_filter & Sex in @sex_filter")

# --- Top Key Metrics ---
total_cases = len(filtered_df)
total_deaths = len(filtered_df[filtered_df["Outcome"] == "D"])
avg_age = round(filtered_df["AgeYears"].mean(), 1)

col1, col2, col3 = st.columns(3)
col1.metric("Total Cases", total_cases)
col2.metric("Total Deaths", total_deaths)
col3.metric("Average Age (Years)", avg_age)

st.markdown("---")

# --- Visualizations ---
col_left, col_right = st.columns(2)

with col_left:
    # 1. Cases over time (Morbidity Week)
    st.subheader("Cases by Morbidity Week")
    cases_by_week = filtered_df.groupby("MorbidityWeek").size().reset_index(name="Case Count")
    fig_line = px.line(cases_by_week, x="MorbidityWeek", y="Case Count", markers=True, 
                       title="Dengue Trend over Time")
    st.plotly_chart(fig_line, use_container_width=True)

    # 2. Case Classification
    st.subheader("Clinical Classification")
    class_counts = filtered_df["ClinClass"].value_counts().reset_index()
    class_counts.columns = ["Classification", "Count"]
    fig_pie = px.pie(class_counts, names="Classification", values="Count", hole=0.4, 
                     title="Distribution of Case Classifications")
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    # 3. Cases by Municipality
    st.subheader("Cases by Municipality")
    muncity_counts = filtered_df["Muncity"].value_counts().reset_index()
    muncity_counts.columns = ["Municipality", "Count"]
    fig_bar = px.bar(muncity_counts, x="Municipality", y="Count", 
                     title="Total Cases per Municipality", color="Count")
    st.plotly_chart(fig_bar, use_container_width=True)

    # 4. Age Distribution
    st.subheader("Age Distribution")
    fig_hist = px.histogram(filtered_df, x="AgeYears", nbins=20, 
                            title="Age of Dengue Patients", color="Sex")
    st.plotly_chart(fig_hist, use_container_width=True)

# --- Raw Data ---
st.markdown("---")
st.subheader("Raw Data Preview")
st.dataframe(filtered_df[["PatientNumber", "Muncity", "AgeYears", "Sex", "DOnset", "ClinClass", "Outcome"]].head(100))
