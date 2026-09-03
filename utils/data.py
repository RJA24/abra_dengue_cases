# utils/data.py
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from utils.constants import SHEET_URL
from utils.cleaning import clean_muni_name

@st.cache_data(ttl=600)
def load_data():
    csv_url = f"{SHEET_URL}/export?format=csv&gid=0"
    df = pd.read_csv(csv_url)
    if 'DOnset' in df.columns: 
        df['DOnset'] = pd.to_datetime(df['DOnset'], errors='coerce')
    if 'Muncity' in df.columns: 
        df['Muncity'] = df['Muncity'].apply(clean_muni_name)
    return df

@st.cache_data(ttl="1h")
def get_tb_targets():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_raw = conn.read(spreadsheet=SHEET_URL, worksheet="Targets", skiprows=0)
        
        if df_raw.empty:
            return {}, pd.DataFrame()
            
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        
        muni_col = "Municipality"
        pop_col = [c for c in df_raw.columns if "POPULATION" in c.upper() and "%" not in c][0]
        screen_col = [c for c in df_raw.columns if "SCREENED" in c.upper()][0]
        test_col = [c for c in df_raw.columns if "TESTED" in c.upper()][0]
        notified_col = [c for c in df_raw.columns if "NOTIFIED" in c.upper()][0]
        
        for col in [pop_col, screen_col, test_col, notified_col]:
            df_raw[col] = pd.to_numeric(
                df_raw[col].astype(str).str.replace(",", "").str.strip(), 
                errors="coerce"
            ).fillna(0)
            
        df_raw[muni_col] = df_raw[muni_col].astype(str).str.strip().str.upper()
        df_raw[muni_col] = df_raw[muni_col].replace({"PENARRUBIA": "PEÑARRUBIA"})
        
        df_abra = df_raw[df_raw[muni_col] == "ABRA"]
        if not df_abra.empty:
            prov_targets = {
                "population": int(df_abra[pop_col].values[0]),
                "screened_target": int(df_abra[screen_col].values[0]),
                "tested_target": int(df_abra[test_col].values[0]),
                "notified_target": int(df_abra[notified_col].values[0])
            }
        else:
            prov_targets = {"population": 251555, "screened_target": 28419, "tested_target": 4861, "notified_target": 1389}
            
        df_munis = df_raw[~df_raw[muni_col].isin(["ABRA", "NAN", "NONE", ""])].copy()
        
        df_muni_targets = df_munis.groupby(muni_col)[[pop_col, screen_col, test_col, notified_col]].sum().reset_index()
        df_muni_targets.rename(columns={
            muni_col: "Muncity",
            pop_col: "Target_Population",
            screen_col: "Target_Screened",
            test_col: "Target_Tested",
            notified_col: "Target_Notified"
        }, inplace=True)
        
        return prov_targets, df_muni_targets
    except Exception as e:
        st.error(f"Error loading TB Targets sheet: {e}")
        return {}, pd.DataFrame()

@st.cache_data(ttl=600)
def load_tb_data(sheet_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=600)
        if 'City/Municipality' in df.columns:
            df['Muncity'] = df['City/Municipality'].apply(clean_muni_name)
        return df
    except Exception as e:
        st.error(f"Error loading {sheet_name}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_all_core_tb():
    d26_ds = load_tb_data("2026 DSTB")
    if not d26_ds.empty: d26_ds['Case_Type'] = 'DSTB'
    d26_dr = load_tb_data("2026 DRTB")
    if not d26_dr.empty: d26_dr['Case_Type'] = 'DRTB'
    d26_mn = load_tb_data("2026 MN")
    if not d26_mn.empty: d26_mn['Case_Type'] = 'MN'
    
    d26 = pd.concat([d26_ds, d26_dr, d26_mn], ignore_index=True)
    d26['Year'] = 2026
    
    h_ds = load_tb_data("DSTB 2015-2025")
    if not h_ds.empty: h_ds['Case_Type'] = 'DSTB'
    h_dr = load_tb_data("DRTB 2015-2025")
    if not h_dr.empty: h_dr['Case_Type'] = 'DRTB'
    h_mn = load_tb_data("MN 2015-2025")
    if not h_mn.empty: h_mn['Case_Type'] = 'MN'
    
    hist = pd.concat([h_ds, h_dr, h_mn], ignore_index=True)
    if not hist.empty: 
        hist['Year'] = pd.to_numeric(hist['Year'], errors='coerce')
    
    return pd.concat([d26, hist], ignore_index=True)

@st.cache_data(ttl=600)
def get_all_tpt_data():
    d26 = load_tb_data("2026 TPT")
    if not d26.empty: d26['Year'] = 2026
    h_tpt = load_tb_data("TPT 2021-2025")
    if not h_tpt.empty: h_tpt['Year'] = pd.to_numeric(h_tpt['Year'], errors='coerce')
    return pd.concat([d26, h_tpt], ignore_index=True)

@st.cache_data(ttl=600)
def get_aux_tb_data(program, selected_year):
    if program == 'TPT':
        if selected_year == 2026:
            df = load_tb_data("2026 TPT")
            df['Year'] = 2026
            return df
        else:
            df = load_tb_data("TPT 2021-2025")
            df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
            return df[df['Year'] == selected_year]
    elif program == 'HIV':
        if selected_year == 2026:
            df = load_tb_data("2026 HIV")
            df['Year'] = 2026
            return df
        else:
            df = load_tb_data("HIV 2021-2025")
            df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
            return df[df['Year'] == selected_year]
