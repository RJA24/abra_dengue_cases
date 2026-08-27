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
import hashlib
from streamlit_gsheets import GSheetsConnection
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium

# --- Page Configuration ---
st.set_page_config(
    page_title="Abra PESU Portal", 
    page_icon="https://github.com/RJA24/abra_sia_2026/blob/main/PHO%20logo.png?raw=true", 
    layout="wide", 
    initial_sidebar_state="auto")

# Inject FontAwesome Library
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

# --- Clean, Professional CSS tailored to your TOML ---
st.markdown("""
    <style>
    /* Hide Deploy button */
    .stDeployButton, [data-testid="stAppDeployButton"] { display: none !important; }

    /* SURGICAL FIX: Make ONLY the header background transparent so the mountain shows through */
    header[data-testid="stHeader"] { 
        background: transparent !important; 
    }

    /* Adjust padding to pull content up slightly */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    /* Hide standard footer */
    #MainMenu, footer { visibility: hidden; } 
    
    .js-plotly-plot { margin-bottom: 2rem; }
    div.row-widget.stRadio > div { flex-direction: row; align-items: center; justify-content: center; background: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; }
    
    /* Global standard button cleanup */
    .stButton > button, .stPopover > button {
        color: #1e293b !important;
        border-color: #cbd5e1 !important;
        background-color: white !important;
    }
    .stButton > button:hover, .stPopover > button:hover,
    .stButton > button:focus, .stPopover > button:focus,
    .stButton > button:active, .stPopover > button:active {
        border-color: #1e293b !important;
        color: #1e293b !important;
        background-color: #f1f5f9 !important;
        box-shadow: none !important;
    }

    /* ---------------------------------------------------- */
    /* SLEEK SIDEBAR NAVIGATION (Coinbase/Upwork Style)     */
    /* ---------------------------------------------------- */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }
    
    /* Brutally force the internal Streamlit text to the left */
    section[data-testid="stSidebar"] .stButton > button div[data-testid="stMarkdownContainer"] {
        display: flex !important;
        width: 100% !important;
        justify-content: flex-start !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button p {
        font-size: 15px !important;
        font-weight: 500 !important;
        color: #334155 !important;
        margin: 0 !important;
        text-align: left !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #f1f5f9 !important; /* Subtle hover effect */
    }
    section[data-testid="stSidebar"] .stButton > button:hover p {
        color: #0f172a !important;
    }
    /* ---------------------------------------------------- */

    /* Glassmorphism Giant Program Buttons styling */
    div.element-container:has(.big-btn-marker) + div.element-container button {
        height: 110px !important;
        border-radius: 55px !important; /* Creates the perfect pill shape */
        border: 2px solid rgba(255, 255, 255, 0.5) !important; /* Soft white border */
        background: rgba(255, 255, 255, 0.35) !important; /* Translucent white fill */
        backdrop-filter: blur(12px) !important; /* The frosted glass blur effect */
        -webkit-backdrop-filter: blur(12px) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1) !important;
        transition: all 0.3s ease-in-out !important;
        justify-content: center !important; 
    }
    div.element-container:has(.big-btn-marker) + div.element-container button div[data-testid="stMarkdownContainer"] {
        justify-content: center !important;
        text-align: center !important;
    }
    div.element-container:has(.big-btn-marker) + div.element-container button p {
        font-size: 22px !important;
        font-weight: 900 !important;
        color: #000000 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        text-align: center !important;
    }
    div.element-container:has(.big-btn-marker) + div.element-container button:hover {
        border-color: rgba(255, 255, 255, 0.9) !important;
        background: rgba(255, 255, 255, 0.6) !important;
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.2) !important;
        transform: translateY(-3px) !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# GOOGLE SHEETS DATABASE FUNCTIONS
# ==========================================

SHEET_URL = "https://docs.google.com/spreadsheets/d/1IHdlNfzNtBAOk3LlDN2LstxlRmoGQNTRgF7vZ2P_t4U"

def get_users_df():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Users", usecols=[0, 1, 2, 3], ttl=0)
    df = df.dropna(subset=['username'])
    
    df['username'] = df['username'].astype(str).str.strip()
    df['password'] = df['password'].astype(str).str.strip()
    df['role'] = df['role'].astype(str).str.strip()
    df['status'] = df['status'].astype(str).str.strip()
    
    return df

def save_users_df(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=df)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    df = get_users_df()
    if username.strip() in df['username'].values:
        return False
    new_row = pd.DataFrame({
        'username': [username.strip()], 
        'password': [hash_password(password)], 
        'role': ['user'], 
        'status': ['pending']
    })
    updated_df = pd.concat([df, new_row], ignore_index=True)
    save_users_df(updated_df)
    return True

def authenticate(username, password):
    if username.strip() == 'admin' and password == 'admin123':
        return 'admin', 'approved'
        
    df = get_users_df()
    user_row = df[df['username'] == username.strip()]
    if not user_row.empty:
        if user_row.iloc[0]['password'] == hash_password(password):
            return user_row.iloc[0]['role'], user_row.iloc[0]['status']
    return None, None

def get_all_users():
    df = get_users_df()
    return df[df['username'] != 'admin']

def update_user_status(username, new_status):
    df = get_users_df()
    df.loc[df['username'] == username, 'status'] = new_status
    save_users_df(df)

def update_user_role(username, new_role):
    df = get_users_df()
    df.loc[df['username'] == username, 'role'] = new_role
    save_users_df(df)

def delete_user(username):
    df = get_users_df()
    df = df[df['username'] != username]
    save_users_df(df)

def update_credentials(old_username, new_username, new_password):
    df = get_users_df()
    clean_new_user = new_username.strip()
    
    if clean_new_user != old_username and clean_new_user in df['username'].values:
        return False
    
    if new_password:
        df.loc[df['username'] == old_username, ['username', 'password']] = [clean_new_user, hash_password(new_password)]
    else:
        df.loc[df['username'] == old_username, 'username'] = clean_new_user
    
    save_users_df(df)
    return True

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ''
if 'role' not in st.session_state: st.session_state.role = ''
if 'current_page' not in st.session_state: st.session_state.current_page = 'login'
if 'active_program' not in st.session_state: st.session_state.active_program = None

def navigate(page):
    st.session_state.current_page = page
    st.rerun()

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ''
    st.session_state.role = ''
    st.session_state.active_program = None
    navigate('login')

# ==========================================
# DENGUE DASHBOARD CORE FUNCTIONS
# ==========================================
ALL_ABRA_MUNICIPALITIES = [
    "BANGUED", "BOLINEY", "BUCAY", "BUCLOC", "DAGUIOMAN", "DANGLAS", "DOLORES",
    "LA PAZ", "LACUB", "LAGANGILANG", "LAGAYAN", "LANGIDEN", "LICUAN-BAAY",
    "LUBA", "MALIBCONG", "MANABO", "PEÑARRUBIA", "PIDIGAN", "PILAR",
    "SALLAPADAN", "SAN ISIDRO", "SAN JUAN", "SAN QUINTIN", "TAYUM", "TINEG",
    "TUBO", "VILLAVICIOSA"
]

def clean_muni_name(raw_name):
    if not isinstance(raw_name, str): return ""
    raw = str(raw_name).upper()
    
    # NEW: Intercept Excel's broken 'Ñ' encoding glitch and standard 'Ñ's
    raw = raw.replace("Ã‘", "N").replace("Ñ", "N")
    
    raw = unicodedata.normalize('NFKD', raw).encode('ASCII', 'ignore').decode('utf-8')
    raw = raw.replace("(CAPITAL)", "").replace("CAPITAL", "").strip()
    
    raw_alpha = re.sub(r'[^A-Z]', '', raw)
    
    # 1. Exact Match Check (Safest)
    for muni in ALL_ABRA_MUNICIPALITIES:
        if raw_alpha == re.sub(r'[^A-Z]', '', muni.replace("Ñ", "N")):
            return muni
            
    # 2. Strict Aliases (Added 'PEAARRUBIA' as a failsafe)
    if raw_alpha in ["LICUANBAAY", "LICUAN", "BAAY"]: return "LICUAN-BAAY"
    if raw_alpha in ["PENARRUBIA", "PENARUBIA", "PEAARRUBIA", "PENAR", "RUBIA", "PEÃ‘ARRUBIA"]: return "PEÑARRUBIA"
    if raw_alpha in ["LAPAZ", "PAZ"]: return "LA PAZ"
    if raw_alpha in ["SANJUAN", "JUAN"]: return "SAN JUAN"
    if raw_alpha in ["SANISIDRO", "ISIDRO"]: return "SAN ISIDRO"
    if raw_alpha in ["SANQUINTIN", "QUINTIN"]: return "SAN QUINTIN"
    
    return raw_name

def clean_brgy_name(raw_name):
    if not isinstance(raw_name, str): return ""
    raw = str(raw_name).upper()
    raw = unicodedata.normalize('NFKD', raw).encode('ASCII', 'ignore').decode('utf-8')
    raw = re.sub(r'\(.*?\)', '', raw) 
    raw = raw.replace("BARANGAY", "").replace("BRGY", "").replace("POBLACION", "POB").replace("POB.", "POB")
    return re.sub(r'[^A-Z0-9]', '', raw)

def get_muni_name_from_props(props):
    keys = ['ADM3_EN', 'MUN_NAME', 'NAME_3', 'MUNICIPALITY']
    upper_props = {str(k).upper(): str(v) for k, v in props.items()}
    
    # Check explicit municipality keys first
    for k in keys:
        if k in upper_props:
            std = clean_muni_name(upper_props[k])
            if std in ALL_ABRA_MUNICIPALITIES: return std
            
    # Safe Fallback: Process all values using our now-perfectly-strict clean_muni_name
    for val in props.values():
        std = clean_muni_name(str(val))
        if std in ALL_ABRA_MUNICIPALITIES: 
            return std
            
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
        coords = []
        if geometry['type'] == 'Polygon':
            for ring in geometry['coordinates']: coords.extend(ring)
        elif geometry['type'] == 'MultiPolygon':
            for poly in geometry['coordinates']:
                for ring in poly: coords.extend(ring)
        if not coords: return None, None
        coords = np.array(coords)
        return float(np.mean(coords[:, 0])), float(np.mean(coords[:, 1]))
    except: return None, None

@st.cache_data(ttl=600)
def load_data():
    csv_url = f"{SHEET_URL}/export?format=csv&gid=0"
    df = pd.read_csv(csv_url)
    if 'DOnset' in df.columns: df['DOnset'] = pd.to_datetime(df['DOnset'], errors='coerce')
    if 'Muncity' in df.columns: df['Muncity'] = df['Muncity'].apply(clean_muni_name)
    return df

@st.cache_data(ttl=600)
def load_tb_data(sheet_name):
    try:
        # Use your already-configured Google Sheets Service Account connection!
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=600)
        
        # Standardize the City/Municipality column to match our geojson logic
        if 'City/Municipality' in df.columns:
            df['Muncity'] = df['City/Municipality'].apply(clean_muni_name)
        return df
    except Exception as e:
        st.error(f"Error loading {sheet_name}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_all_core_tb():
    # Load 2026 Data & Tag Case Types
    d26_ds = load_tb_data("2026 DSTB")
    if not d26_ds.empty: d26_ds['Case_Type'] = 'DSTB'
    d26_dr = load_tb_data("2026 DRTB")
    if not d26_dr.empty: d26_dr['Case_Type'] = 'DRTB'
    d26_mn = load_tb_data("2026 MN")
    if not d26_mn.empty: d26_mn['Case_Type'] = 'MN'
    
    d26 = pd.concat([d26_ds, d26_dr, d26_mn], ignore_index=True)
    d26['Year'] = 2026
    
    # Load Historical Data (2015-2025) & Tag
    h_ds = load_tb_data("DSTB 2015-2025")
    if not h_ds.empty: h_ds['Case_Type'] = 'DSTB'
    h_dr = load_tb_data("DRTB 2015-2025")
    if not h_dr.empty: h_dr['Case_Type'] = 'DRTB'
    h_mn = load_tb_data("MN 2015-2025")
    if not h_mn.empty: h_mn['Case_Type'] = 'MN'
    
    hist = pd.concat([h_ds, h_dr, h_mn], ignore_index=True)
    if not hist.empty: hist['Year'] = pd.to_numeric(hist['Year'], errors='coerce')
    
    return pd.concat([d26, hist], ignore_index=True)

@st.cache_data(ttl=600)
def get_all_tpt_data():
    # Fetches all TPT data specifically for the combo trend chart
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
                    props = f.get('properties', {})
                    if any('ABRA' in str(v).upper() for v in props.values()):
                        muni = get_muni_name_from_props(props)
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
                if get_muni_name_from_props(feat.get('properties', {})) == target:
                    raw_brgy = extract_brgy_name(feat.get('properties', {}))
                    feat['properties']['Original_Name'] = raw_brgy
                    feat['properties']['Standard_Name'] = clean_brgy_name(raw_brgy)
                    features.append(feat)
            if features: return {"type": "FeatureCollection", "features": features}, None
            return None, f"No barangays matched inside {target_muni}."
    except Exception as e: return None, str(e)


# ==========================================
# PAGE RENDERERS
# ==========================================

def render_login():
    st.markdown("<h2 style='text-align: center;'>Abra Provincial Epidemiology and Surveillance Unit</h2>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("### Secure Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", use_container_width=True)
            
            if submitted:
                role, status = authenticate(username, password)
                if role:
                    if status == 'approved':
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = role
                        navigate('main_menu')
                    else:
                        st.error("Your account is pending admin approval.")
                else:
                    st.error("Invalid username or password.")
        
        if st.button("Create new account", use_container_width=True):
            navigate('register')

def render_register():
    st.markdown("<h2 style='text-align: center;'>Create an Account</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("register_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Request Access", use_container_width=True)
            
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_username) < 3 or len(new_password) < 6:
                    st.error("Username (min 3) and Password (min 6) must be longer.")
                else:
                    if create_user(new_username, new_password):
                        st.success("Account created! Please wait for an admin to approve your access.")
                    else:
                        st.error("Username already exists.")
                        
        if st.button("Back to Login", use_container_width=True):
            navigate('login')

def render_admin_panel():
    st.markdown("### <i class='fa-solid fa-screwdriver-wrench' style='color: #475569;'></i> Admin Control Panel", unsafe_allow_html=True)
    
    tab_users, tab_db = st.tabs(["User Management", "Database Uploader"])
    
    with tab_users:
        st.caption("Manage user access and edit roles.")
        try:
            users_df = get_all_users()
            if not users_df.empty:
                for index, row in users_df.iterrows():
                    with st.container():
                        col_user, col_role, col_actions = st.columns([2, 2, 3])
                        with col_user:
                            st.write(f"**{row['username']}**")
                            if row['status'] == 'pending': st.warning("PENDING")
                            else: st.success("APPROVED")
                        with col_role:
                            role_options = ["user", "admin"]
                            current_idx = role_options.index(row['role']) if row['role'] in role_options else 0
                            selected_role = st.selectbox("Role Assignment", options=role_options, index=current_idx, key=f"role_{row['username']}", label_visibility="collapsed")
                            if selected_role != row['role']:
                                if st.button("Save New Role", key=f"save_role_{row['username']}"):
                                    update_user_role(row['username'], selected_role)
                                    st.rerun()
                        with col_actions:
                            c1, c2 = st.columns(2)
                            with c1:
                                if row['status'] == 'pending':
                                    if st.button("Approve", key=f"app_{row['username']}", use_container_width=True):
                                        update_user_status(row['username'], 'approved')
                                        update_user_role(row['username'], selected_role)
                                        st.rerun()
                            with c2:
                                if st.button("Delete User", key=f"del_{row['username']}", use_container_width=True):
                                    delete_user(row['username'])
                                    st.rerun()
                        st.markdown("---")
            else:
                st.info("No other users found in the database.")
        except Exception as e:
            st.error("Could not load users. Please check your Google Service Account configuration.")

    with tab_db:
        st.caption("Upload cumulative 2026 export files to overwrite and update the master Google Sheets. Historical data (2015–2025) is excluded and protected.")
        
        # Exact report mapping to your Google Sheet tab names
        report_mapping = {
            "Dengue Cases": "Dengue Cases",
            "2026 MN": "2026 MN",
            "DSTB": "2026 DSTB",
            "DRTB": "2026 DRTB",
            "TPT": "2026 TPT",
            "HIV": "2026 HIV",
            "2026 Report 5": "2026 Report 5"
        }
        
        selected_report = st.selectbox("1. Select Report to Update", options=list(report_mapping.keys()))
        target_worksheet = report_mapping[selected_report]
        
        st.info(f"Target Google Sheet Tab: **{target_worksheet}**")
        
        uploaded_file = st.file_uploader("2. Upload Cumulative Export File (.csv or .xlsx)", type=['csv', 'xlsx'])
        
        if uploaded_file is not None:
            # Quick preview to verify data before uploading
            try:
                if uploaded_file.name.endswith('.csv'):
                    preview_df = pd.read_csv(uploaded_file)
                else:
                    preview_df = pd.read_excel(uploaded_file)
                
                st.write(f"📁 **File Preview:** {len(preview_df):,} rows found.")
                with st.expander("View first few rows"):
                    st.dataframe(preview_df.head(3), use_container_width=True)
                
                if st.button("Clear Old Data & Upload New Records", type="primary", use_container_width=True):
                    with st.spinner(f"Updating '{target_worksheet}' in Google Sheets..."):
                        try:
                            conn = st.connection("gsheets", type=GSheetsConnection)
                            
                            # Safely clear old data first
                            try:
                                conn.clear(spreadsheet=SHEET_URL, worksheet=target_worksheet)
                            except:
                                pass
                                
                            # Push new cumulative dataset
                            conn.update(spreadsheet=SHEET_URL, worksheet=target_worksheet, data=preview_df)
                            
                            # Nuke app cache so dashboards instantly reflect the new data
                            st.cache_data.clear()
                            
                            st.success(f"✅ Successfully replaced data in '{target_worksheet}' with {len(preview_df):,} records!")
                        except Exception as e:
                            st.error(f"Error updating Google Sheet: {e}")
            except Exception as e:
                st.error(f"Could not read the uploaded file: {e}")

def render_settings():
    st.markdown("### <i class='fa-solid fa-gear' style='color: #475569;'></i> Account Settings", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.form("settings_form"):
            st.subheader("Update Credentials")
            new_username = st.text_input("New Username", value=st.session_state.username)
            new_password = st.text_input("New Password (leave blank to keep current)", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Update Account"):
                if new_password and new_password != confirm_password:
                    st.error("New passwords do not match.")
                else:
                    if st.session_state.username == 'admin' and new_username != 'admin':
                        st.error("You cannot change the master admin username.")
                    else:
                        success = update_credentials(st.session_state.username, new_username, new_password)
                        if success:
                            st.success("Credentials updated! Please log in again.")
                            logout()
                        else:
                            st.error("Username already taken.")

def render_main_menu():
    # --- BACKGROUND IMAGE INJECTION (No White Overlay) ---
    bg_css = """
    <style>
    .stApp {
        background: url("https://github.com/RJA24/abra_sia_2026/blob/main/Abra%20(2).png?raw=true") !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }
    
    /* Custom Title Styling with shadow for readability over the background */
    .main-title {
        text-align: center; 
        font-size: 3.2rem; 
        font-weight: 900;
        color: #0f172a;
        margin-top: 10px;
        margin-bottom: 70px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        text-shadow: 0px 2px 4px rgba(255,255,255,0.9), 0px 4px 15px rgba(255,255,255,0.7);
    }
    </style>
    """
    st.markdown(bg_css, unsafe_allow_html=True)
    # ----------------------------------

    # Inject the Abra Logo centered above the title
    st.markdown(f"""
    <div style='text-align: center; margin-bottom: 10px;'>
        <img src="https://upload.wikimedia.org/wikipedia/commons/1/1a/Abra_provincial_seal.png?utm_source=commons.wikimedia.org&utm_campaign=index&utm_content=thumbnail_unscaled&_=20170706162937?raw=true" width="100" style="filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.3));">
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='main-title'>Abra Provincial Epidemiology<br>and Surveillance Unit</h1>", unsafe_allow_html=True)
    
    # Use spacer columns (the 1s on the ends) to squeeze the buttons inward slightly
    _, col1, col2, col3, _ = st.columns([1, 4, 4, 4, 1], gap="medium")
    
    with col1:
        st.markdown('<span class="big-btn-marker"></span>', unsafe_allow_html=True)
        if st.button("DENGUE", use_container_width=True):
            st.session_state.active_program = 'dengue'
            st.rerun()
            
    with col2:
        st.markdown('<span class="big-btn-marker"></span>', unsafe_allow_html=True)
        if st.button("TUBERCULOSIS", use_container_width=True):
            st.session_state.active_program = 'tb'
            st.rerun()
            
    with col3:
        st.markdown('<span class="big-btn-marker"></span>', unsafe_allow_html=True)
        if st.button("NEXT PROGRAM", use_container_width=True):
            pass

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
        # Replaced Emoji with FontAwesome Shortcode Equivalent
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
    # ------------------------------------

    st.title("Abra PESU: Dengue Surveillance Dashboard")
    st.caption("As of Morbidity Week: " + str(filtered_df["MorbidityWeek"].max()) if "MorbidityWeek" in filtered_df.columns else "No Morbidity Week Data Available")
    st.markdown("---")

    total_cases = len(filtered_df)
    total_deaths = len(filtered_df[filtered_df["Outcome"] == "D"]) if "Outcome" in filtered_df.columns else 0
    avg_age = round(filtered_df["AgeYears"].mean(), 1) if not filtered_df.empty and "AgeYears" in filtered_df.columns else 0
    
    # --- DYNAMIC GEO KPI LOGIC ---
    ABRA_BRGY_COUNTS = {
        "BANGUED": 31, "BOLINEY": 8, "BUCAY": 21, "BUCLOC": 4, "DAGUIOMAN": 4, 
        "DANGLAS": 7, "DOLORES": 15, "LA PAZ": 12, "LACUB": 6, "LAGANGILANG": 17, 
        "LAGAYAN": 5, "LANGIDEN": 6, "LICUAN-BAAY": 11, "LUBA": 8, "MALIBCONG": 12, 
        "MANABO": 11, "PEÑARRUBIA": 9, "PIDIGAN": 15, "PILAR": 19, "SALLAPADAN": 9, 
        "SAN ISIDRO": 9, "SAN JUAN": 19, "SAN QUINTIN": 6, "TAYUM": 11, "TINEG": 10, 
        "TUBO": 10, "VILLAVICIOSA": 8
    }

    if muncity_input == "All Municipalities":
        geo_kpi_title = "Affected Municipalities"
        geo_kpi_value = f"{filtered_df['Muncity'].nunique()} / 27"
    else:
        geo_kpi_title = "Affected Barangays"
        affected_brgy = filtered_df['Barangay'].nunique() if 'Barangay' in filtered_df.columns else 0
        total_brgy = ABRA_BRGY_COUNTS.get(muncity_input, "?")
        geo_kpi_value = f"{affected_brgy} / {total_brgy}"
    # -----------------------------

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
            
            # --- POPULATION PYRAMID LOGIC ---
            # 1. Define custom age bins exactly like your reference image
            bins = [-1, 0.99, 4, 9, 14, 19, 44, 59, 200]
            age_labels = ['< 1 y/o', '1-4 y/o', '5-9 y/o', '10-14 y/o', '15-19 y/o', '20-44 y/o', '45-59 y/o', '60 y/o & above']
            
            df_pyr = filtered_df.copy()
            df_pyr['AgeGroup'] = pd.cut(df_pyr['AgeYears'], bins=bins, labels=age_labels, right=True)
            
            # 2. Group the data by Age Group and Sex
            pyr_data = df_pyr.groupby(['AgeGroup', 'Sex']).size().reset_index(name='Count')
            
            # 3. Split Male and Female securely
            males = pyr_data[pyr_data['Sex'].str.upper().str.startswith('M')].groupby('AgeGroup')['Count'].sum().reindex(age_labels).fillna(0)
            females = pyr_data[pyr_data['Sex'].str.upper().str.startswith('F')].groupby('AgeGroup')['Count'].sum().reindex(age_labels).fillna(0)
            
            # 4. Invert Male values to draw the bars backwards to the left
            males_negative = males * -1

            # 5. Build the Plotly Figure
            fig_pyr = go.Figure()
            
            # Add Male trace (Left Side)
            fig_pyr.add_trace(go.Bar(
                y=age_labels,
                x=males_negative,
                name='Male',
                orientation='h',
                marker_color='#2563eb', # Blue
                text=males.astype(int), # Keep the real positive number for hover data
                hovertemplate="Male: %{text}<extra></extra>"
            ))
            
            # Add Female trace (Right Side)
            fig_pyr.add_trace(go.Bar(
                y=age_labels,
                x=females,
                name='Female',
                orientation='h',
                marker_color='#ec4899', # Pink/Orange
                text=females.astype(int),
                hovertemplate="Female: %{text}<extra></extra>"
            ))

            # 6. Dynamically fix the X-axis so the negative side displays as absolute positive numbers
            max_val = int(max(males.max(), females.max()))
            if max_val == 0: max_val = 10
            step = max(1, max_val // 5)
            
            # Generate symmetrical ticks for aesthetic balance
            tick_vals = list(range(-((max_val // step) * step + step), ((max_val // step) * step + step) + step, step))
            tick_text = [str(abs(v)) for v in tick_vals]

            fig_pyr.update_layout(
                title="Age and Sex Distribution of Cases",
                barmode='relative',
                bargap=0.1,
                height=500,
                xaxis=dict(
                    tickvals=tick_vals,
                    ticktext=tick_text,
                    title="No. of Cases"
                ),
                yaxis=dict(title="Age Group")
            )
            
            st.plotly_chart(fig_pyr, use_container_width=True)

        # --- CLUSTERING BARANGAY TABLE ---
        if "MorbidityWeek" in df.columns and "Barangay" in filtered_df.columns and "Muncity" in filtered_df.columns:
            st.markdown("<hr style='margin: 30px 0; border: none; border-bottom: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
            st.subheader("Clustering Barangay")
            
            try:
                # 1. ANCHOR TIMELINE: Get all available weeks
                global_df = df.copy()
                global_df['MW_Clean'] = pd.to_numeric(global_df['MorbidityWeek'], errors='coerce')
                global_weeks = sorted(global_df['MW_Clean'].dropna().astype(int).unique())
                
                # 2. Exclude the absolute latest week (incomplete data) and grab the 4 before it for the default
                previous_weeks = global_weeks[:-1] if len(global_weeks) > 1 else []
                default_weeks = previous_weeks[-4:] if len(previous_weeks) >= 4 else previous_weeks
                
                # 3. Add the Dropdown for the user to choose
                selected_weeks = st.multiselect(
                    "Select Morbidity Weeks for Clustering", 
                    options=global_weeks, 
                    default=default_weeks,
                    help="The current (latest) week is excluded by default as its data is usually incomplete."
                )
                
                # 4. Clean the CURRENTLY FILTERED dataset
                clean_df = filtered_df.copy()
                clean_df['MW_Clean'] = pd.to_numeric(clean_df['MorbidityWeek'], errors='coerce')
                clean_df = clean_df.dropna(subset=['MW_Clean'])
                clean_df['MW_Clean'] = clean_df['MW_Clean'].astype(int)
                
                if selected_weeks:
                    # 5. Filter data explicitly to the selected weeks
                    cluster_df = clean_df[clean_df["MW_Clean"].isin(selected_weeks)]
                    selected_weeks = sorted(selected_weeks) # Keep columns chronological
                    
                    if not cluster_df.empty:
                        # 6. Create the Pivot Table
                        pivot_cluster = pd.crosstab(
                            index=[cluster_df['Muncity'], cluster_df['Barangay']],
                            columns=cluster_df['MW_Clean']
                        ).fillna(0).astype(int)
                        
                        # Guarantee all selected weeks exist as columns
                        for w in selected_weeks:
                            if w not in pivot_cluster.columns:
                                pivot_cluster[w] = 0
                        pivot_cluster = pivot_cluster[selected_weeks]
                        
                        # 7. Calculate Total and apply clustering threshold (Total >= 3)
                        pivot_cluster['Total'] = pivot_cluster.sum(axis=1)
                        pivot_cluster = pivot_cluster[pivot_cluster['Total'] >= 3].reset_index()
                        
                        if not pivot_cluster.empty:
                            # 8. Sort alphabetically and format
                            pivot_cluster['Sort_Key'] = pivot_cluster['Muncity'].str.replace('Ñ', 'N')
                            pivot_cluster = pivot_cluster.sort_values(by=['Sort_Key', 'Barangay']).drop(columns=['Sort_Key'])
                            
                            rename_dict = {w: f"MW{w}" for w in selected_weeks}
                            pivot_cluster = pivot_cluster.rename(columns=rename_dict)
                            pivot_cluster.rename(columns={'Muncity': 'Municipality'}, inplace=True)
                            
                            # 9. Styling
                            def apply_green_color(val):
                                try:
                                    if int(val) > 0:
                                        return 'background-color: #8bc34a; color: #0f172a; font-weight: bold;' 
                                    return ''
                                except:
                                    return ''
                                    
                            color_cols = [f"MW{w}" for w in selected_weeks]
                            
                            # Pandas 2.1+ uses .map() for element-wise styling
                            if hasattr(pivot_cluster.style, 'map'):
                                styled_df = pivot_cluster.style.map(apply_green_color, subset=color_cols)
                            else: # Fallback for older pandas versions
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
        map_style_choice = st.radio("Select Map Theme:", ["Light", "Street", "Satellite", "Dark"], horizontal=True, key="dengue_map_theme")
        style_map = {"Light": "carto-positron-nolabels", "Street": "open-street-map", "Dark": "carto-darkmatter-nolabels", "Satellite": "white-bg"}
        label_color = '#ffffff' if map_style_choice == "Satellite" else '#000000'
        
        # Dynamically determine the correct column name for Dengue
        brgy_col = "Barangay" if "Barangay" in filtered_df.columns else ("Brgy" if "Brgy" in filtered_df.columns else None)
        
        if muncity_input != "All Municipalities":
            st.subheader(f"Geographic Heatmap: Barangays in {muncity_input}")
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
                    max_cases = int(map_data["Total Cases"].max())
                    safe_max = max(1, max_cases)
                    
                    try:
                        # --- BULLETPROOF GRAPH OBJECTS ENGINE (BARANGAY) ---
                        fig_map = go.Figure(go.Choroplethmap(
                            geojson=brgy_geojson, 
                            locations=map_data['Join_Key'], 
                            featureidkey='properties.Standard_Name', 
                            z=map_data['Total Cases'], 
                            text=map_data['Barangay_Display'],
                            hovertemplate="<b>%{text}</b><br>Total Cases: %{z}<extra></extra>",
                            colorscale="Reds",
                            zmin=0, 
                            zmax=safe_max,
                            marker={"opacity": 1.0, "line": {"width": 0.5, "color": "gray"}}
                        ))
                        
                        fig_map.update_layout(
                            map_style=style_map[map_style_choice],
                            map_zoom=11.5,
                            map_center={"lat": cam_lat, "lon": cam_lon},
                            margin={"r":0,"t":20,"l":0,"b":0}, height=850
                        )
                        
                        if map_style_choice == "Satellite":
                            fig_map.update_layout(map_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}])
                        
                        fig_map.add_trace(go.Scattermap(lon=lons, lat=lats, mode='markers+text', text=texts, textposition='middle center',textfont=dict(size=12, color=label_color), marker=dict(allowoverlap=True, size=0, opacity=0), hoverinfo='skip', showlegend=False))
                        st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': False})
                    except Exception as e:
                        st.error(f"Plotly encountered an internal error rendering the Barangay map: {e}")
                else:
                    st.warning("No geographic mapping data available for the selected filters.")
            else:
                st.error(err if err else "Barangay column missing in Dengue dataset (Expected 'Barangay').")
                
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
                    if lon is not None and lat is not None:
                        lons.append(float(lon)); lats.append(float(lat))
                        texts.append(f"{std_name.title()}<br>{int(cases)}")
                
                if not map_data.empty and "Total Cases" in map_data.columns:
                    max_cases = int(map_data["Total Cases"].max())
                    safe_max = max(1, max_cases)
                            
                    try:
                        # --- BULLETPROOF GRAPH OBJECTS ENGINE (MUNICIPALITY) ---
                        fig_map = go.Figure(go.Choroplethmap(
                            geojson=abra_geojson, 
                            locations=map_data['Muncity'], 
                            featureidkey='properties.Standard_Name', 
                            z=map_data['Total Cases'], 
                            text=map_data['Muncity'],
                            hovertemplate="<b>%{text}</b><br>Total Cases: %{z}<extra></extra>",
                            colorscale="Reds",
                            zmin=0, 
                            zmax=safe_max,
                            marker={"opacity": 1.0, "line": {"width": 0.5, "color": "gray"}}
                        ))
                        
                        fig_map.update_layout(
                            map_style=style_map[map_style_choice],
                            map_zoom=8.8,
                            map_center={"lat": 17.58, "lon": 120.83},
                            margin={"r":0,"t":20,"l":0,"b":0}, height=850
                        )
                        
                        if map_style_choice == "Satellite":
                            fig_map.update_layout(map_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}])

                        fig_map.add_trace(go.Scattermap(lon=lons, lat=lats, mode='markers+text', text=texts, textposition='middle center',textfont=dict(size=12, color=label_color), marker=dict(allowoverlap=True, size=0, opacity=0), hoverinfo='skip', showlegend=False))
                        st.plotly_chart(
                            fig_map, 
                            use_container_width=True, 
                            config={
                                'scrollZoom': False,
                                'toImageButtonOptions': {
                                    'format': 'png', 
                                    'filename': 'Abra_Choropleth_Map',
                                    'height': 1080,
                                    'width': 1920,
                                    'scale': 3
                                }
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

# ==========================================
# MAIN ROUTING LOGIC
# ==========================================

def render_tb():
    df_all_raw = get_all_core_tb()
    CASE_COLORS = {"DSTB": "#3b82f6", "DRTB": "#ef4444", "MN": "#f59e0b", "TPT": "#10b981"}

    with st.sidebar:
        if st.button("Back to Menu", icon=":material/arrow_back:", use_container_width=True):
            st.session_state.active_program = None
            st.rerun()
        st.markdown("<hr style='margin: 15px 0; border: none; border-bottom: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #0f172a; margin: 0 0 15px 0;'><i class='fa-solid fa-folder-open' style='color: #475569;'></i> TB Controls</h4>", unsafe_allow_html=True)
        
        available_years = list(range(2026, 2014, -1))
        selected_year = st.selectbox("Select Year", options=available_years, index=0)

        # Global Case Type Filter
        case_type_input = st.multiselect(
            "Filter Case Type", 
            options=["DSTB", "DRTB", "MN", "TPT"], 
            default=["DSTB", "DRTB", "MN", "TPT"]
        )

        if not df_all_raw.empty and "Muncity" in df_all_raw.columns:
            muni_options = ["All Municipalities"] + sorted(df_all_raw["Muncity"].dropna().unique().tolist())
            muncity_input = st.selectbox("Filter Municipality", options=muni_options, index=0)
        else: muncity_input = "All Municipalities"
            
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("Refresh Data", icon=":material/refresh:", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Apply Filters (Keep TPT isolated from the main df_combined)
    active_types = [t for t in case_type_input if t != "TPT"]
    
    if muncity_input != "All Municipalities": df_all_filtered = df_all_raw[(df_all_raw["Muncity"] == muncity_input) & (df_all_raw["Case_Type"].isin(active_types))]
    else: df_all_filtered = df_all_raw[df_all_raw["Case_Type"].isin(active_types)]

    df_combined = df_all_filtered[df_all_filtered['Year'] == selected_year]
    df_prev_year = df_all_filtered[df_all_filtered['Year'] == (selected_year - 1)]
    
    if "TPT" in case_type_input: df_tpt = get_aux_tb_data('TPT', selected_year)
    else: df_tpt = pd.DataFrame()
    
    df_hiv = get_aux_tb_data('HIV', selected_year)

    with st.sidebar:
        if not df_combined.empty:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            csv_data = df_combined.to_csv(index=False).encode('utf-8')
            st.download_button(label=f"Download {selected_year} Data", data=csv_data, file_name=f"Abra_TB_Data_{selected_year}.csv", mime="text/csv", icon=":material/download:", use_container_width=True)

    st.title("Abra PESU: Tuberculosis Control Program")
    st.markdown("---")

    # YOY Metrics (TPT is safely excluded from curr_cases)
    curr_cases = len(df_combined)
    prev_cases = len(df_prev_year)
    case_delta = curr_cases - prev_cases

    def get_success_count(df):
        if "Outcome/Status" in df.columns: return len(df[df["Outcome/Status"].str.upper().isin(["CURED", "TREATMENT COMPLETED"])])
        return 0

    curr_success = get_success_count(df_combined)
    prev_success = get_success_count(df_prev_year)
    success_delta = curr_success - prev_success

    ABRA_BRGY_COUNTS = {"BANGUED": 31, "BOLINEY": 8, "BUCAY": 21, "BUCLOC": 4, "DAGUIOMAN": 4, "DANGLAS": 7, "DOLORES": 15, "LA PAZ": 12, "LACUB": 6, "LAGANGILANG": 17, "LAGAYAN": 5, "LANGIDEN": 6, "LICUAN-BAAY": 11, "LUBA": 8, "MALIBCONG": 12, "MANABO": 11, "PEÑARRUBIA": 9, "PIDIGAN": 15, "PILAR": 19, "SALLAPADAN": 9, "SAN ISIDRO": 9, "SAN JUAN": 19, "SAN QUINTIN": 6, "TAYUM": 11, "TINEG": 10, "TUBO": 10, "VILLAVICIOSA": 8}

    if muncity_input == "All Municipalities":
        geo_kpi_title = "Affected Municipalities"
        if 'Muncity' in df_combined.columns: curr_geo = df_combined[df_combined['Muncity'].isin(ALL_ABRA_MUNICIPALITIES)]['Muncity'].nunique()
        else: curr_geo = 0
        if 'Muncity' in df_prev_year.columns: prev_geo = df_prev_year[df_prev_year['Muncity'].isin(ALL_ABRA_MUNICIPALITIES)]['Muncity'].nunique()
        else: prev_geo = 0
        geo_delta = curr_geo - prev_geo
        geo_val = f"{curr_geo} / 27"
    else:
        geo_kpi_title = "Affected Barangays"
        curr_geo = df_combined['Brgy'].nunique() if 'Brgy' in df_combined.columns else 0
        prev_geo = df_prev_year['Brgy'].nunique() if 'Brgy' in df_prev_year.columns else 0
        geo_delta = curr_geo - prev_geo
        total_brgy = ABRA_BRGY_COUNTS.get(muncity_input, "?")
        geo_val = f"{curr_geo} / {total_brgy}"

    def create_yoy_card(title, value, border_color, delta_val, inverse_color=False):
        if delta_val > 0:
            arrow = "↑"
            text_color = "#dc2626" if inverse_color else "#16a34a"
            bg_color = "#fee2e2" if inverse_color else "#dcfce3"
        elif delta_val < 0:
            arrow = "↓"
            text_color = "#16a34a" if inverse_color else "#dc2626" 
            bg_color = "#dcfce3" if inverse_color else "#fee2e2"
        else:
            arrow = "→"
            text_color = "#64748b"
            bg_color = "#f1f5f9"
        return f"""<div style="background-color: #ffffff; padding: 22px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-left: 8px solid {border_color}; text-align: center;"><p style="margin: 0; font-size: 1rem; color: #64748b; font-weight: 600; text-transform: uppercase;">{title}</p><h2 style="margin: 10px 0 10px 0; font-size: 2.6rem; color: #0f172a; font-weight: 800;">{value}</h2><span style="color: {text_color}; font-size: 0.85rem; font-weight: 700; background-color: {bg_color}; padding: 4px 10px; border-radius: 20px;">{arrow} {abs(delta_val)} vs prev year</span></div>"""

    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(create_yoy_card(f"Total Cases ({selected_year})", f"{curr_cases:,}", "#2563eb", case_delta, inverse_color=True), unsafe_allow_html=True)
    with col2: st.markdown(create_yoy_card(f"Successful Outcomes", f"{curr_success:,}", "#10b981", success_delta, inverse_color=False), unsafe_allow_html=True)
    with col3: st.markdown(create_yoy_card(geo_kpi_title, geo_val, "#f59e0b", geo_delta, inverse_color=True), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Epidemiological Trends", "Demographics", "Clinical & Outcomes", "Preventive Treatment (TPT)", "TB-HIV Collaboration", "Choropleth Map", "Raw Line List"])

    with tab1:
        # --- FEATURE 4: COMBO CHART ---
        st.subheader("TB All Forms and TPT Enrollment (2021-2026)")
        
        combo_tb = df_all_raw[(df_all_raw['Year'] >= 2021) & (df_all_raw['Case_Type'] == 'DSTB')].copy()
        
        # --- FIX: Bulletproof Bacteriologic Status Matching ---
        if 'Bacteriologic Status' in combo_tb.columns:
            combo_tb['Bac_Clean'] = combo_tb['Bacteriologic Status'].fillna('UNKNOWN').astype(str).str.upper()
            
            # Widen the search net to catch 'BACTERIOLOGICAL', 'BACTERIOLOGICALLY', 'CLINICAL', 'CLINICALLY', etc.
            bc_mask = combo_tb['Bac_Clean'].str.contains('BACTERIOLOGIC|BC', regex=True)
            cd_mask = combo_tb['Bac_Clean'].str.contains('CLINICAL|CD', regex=True)
            
            bc_counts = combo_tb[bc_mask].groupby('Year').size()
            cd_counts = combo_tb[cd_mask].groupby('Year').size()
        else:
            bc_counts, cd_counts = pd.Series(dtype=int), pd.Series(dtype=int)
            st.warning("Could not locate 'Bacteriologic Status' column in DSTB data.")
            
        tpt_all = get_all_tpt_data()
        if not tpt_all.empty: tpt_counts = tpt_all[tpt_all['Year'] >= 2021].groupby('Year').size()
        else: tpt_counts = pd.Series(dtype=int)
            
        combo_years = sorted(list(set(bc_counts.index).union(set(cd_counts.index)).union(set(tpt_counts.index))))
        combo_years = [int(y) for y in combo_years if pd.notna(y)]
        
        if combo_years:
            fig_combo = go.Figure()
            y_bc = [bc_counts.get(y, 0) for y in combo_years]
            y_cd = [cd_counts.get(y, 0) for y in combo_years]
            y_tpt = [tpt_counts.get(y, 0) for y in combo_years]
            
            # Add traces
            fig_combo.add_trace(go.Bar(x=combo_years, y=y_bc, name="BC", marker_color="#ff0000", text=y_bc, textposition="inside", textfont=dict(color="white")))
            fig_combo.add_trace(go.Bar(x=combo_years, y=y_cd, name="CD", marker_color="#b2d89b", text=y_cd, textposition="inside", textfont=dict(color="black")))
            fig_combo.add_trace(go.Scatter(x=combo_years, y=y_tpt, name="TPT", mode="lines+markers+text", marker_color="#3b82f6", line=dict(width=3), marker=dict(size=8), text=y_tpt, textposition="top center", textfont=dict(color="#3b82f6", size=14, family="Arial Black")))
            
            fig_combo.update_layout(barmode='stack', height=500, xaxis=dict(tickmode='array', tickvals=combo_years), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            st.plotly_chart(fig_combo, use_container_width=True)
        else:
            st.info("No data available to plot the Multi-Year Combo Chart.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader(f"Monthly Case Detection ({selected_year})")
        if "Date of Diagnosis" in df_combined.columns and not df_combined.empty:
            df_combined['Diag_Date'] = pd.to_datetime(df_combined['Date of Diagnosis'], errors='coerce')
            df_combined['Month'] = df_combined['Diag_Date'].dt.month
            month_map = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
            
            # Group by Case Type for unified colors
            monthly_trend = df_combined.dropna(subset=['Month']).groupby(['Month', 'Case_Type']).size().reset_index(name='Cases')
            monthly_trend['Month Name'] = monthly_trend['Month'].map(month_map)
            
            if not monthly_trend.empty:
                fig_trend = px.bar(monthly_trend, x='Month Name', y='Cases', color='Case_Type', text_auto=True, color_discrete_map=CASE_COLORS)
                fig_trend.update_layout(height=400, xaxis_title="Month", yaxis_title="Number of Cases")
                st.plotly_chart(fig_trend, use_container_width=True)
            else: st.info(f"Insufficient date data for monthly trend analysis in {selected_year}.")

    with tab2:
        st.subheader(f"Demographic Distribution ({selected_year})")
        if "Muncity" in df_combined.columns and muncity_input == "All Municipalities":
            muncity_counts = df_combined.groupby(["Muncity", "Case_Type"]).size().reset_index(name="Count")
            fig_bar = px.bar(muncity_counts, x="Muncity", y="Count", color="Case_Type", title="Total TB Cases per Municipality", text_auto=True, color_discrete_map=CASE_COLORS)
            fig_bar.update_layout(xaxis={'categoryorder':'total descending'}, barmode='stack', height=500)
            st.plotly_chart(fig_bar, use_container_width=True)

        if "Age" in df_combined.columns and "Sex" in df_combined.columns:
            df_combined['Age_Clean'] = pd.to_numeric(df_combined['Age'], errors='coerce').fillna(-1)
            bins = [-1, 0.99, 4, 9, 14, 19, 44, 59, 200]
            age_labels = ['< 1 y/o', '1-4 y/o', '5-9 y/o', '10-14 y/o', '15-19 y/o', '20-44 y/o', '45-59 y/o', '60 y/o & above']
            df_pyr = df_combined.copy()
            df_pyr['AgeGroup'] = pd.cut(df_pyr['Age_Clean'], bins=bins, labels=age_labels, right=True)
            pyr_data = df_pyr.groupby(['AgeGroup', 'Sex']).size().reset_index(name='Count')
            
            males = pyr_data[pyr_data['Sex'].astype(str).str.upper().str.startswith('M')].groupby('AgeGroup')['Count'].sum().reindex(age_labels).fillna(0)
            females = pyr_data[pyr_data['Sex'].astype(str).str.upper().str.startswith('F')].groupby('AgeGroup')['Count'].sum().reindex(age_labels).fillna(0)
            males_negative = males * -1

            fig_pyr = go.Figure()
            fig_pyr.add_trace(go.Bar(y=age_labels, x=males_negative, name='Male', orientation='h', marker_color='#2563eb', text=males.astype(int), hovertemplate="Male: %{text}<extra></extra>"))
            fig_pyr.add_trace(go.Bar(y=age_labels, x=females, name='Female', orientation='h', marker_color='#ec4899', text=females.astype(int), hovertemplate="Female: %{text}<extra></extra>"))
            max_val = int(max(males.max(), females.max())) if not males.empty and not females.empty else 10
            if max_val == 0: max_val = 10
            step = max(1, max_val // 5)
            tick_vals = list(range(-((max_val // step) * step + step), ((max_val // step) * step + step) + step, step))
            tick_text = [str(abs(v)) for v in tick_vals]
            fig_pyr.update_layout(title="Age and Sex Distribution of TB Cases", barmode='relative', bargap=0.1, height=500, xaxis=dict(tickvals=tick_vals, ticktext=tick_text, title="No. of Cases"), yaxis=dict(title="Age Group"))
            st.plotly_chart(fig_pyr, use_container_width=True)
            
    with tab3:
        st.subheader(f"Clinical & Treatment Outcomes ({selected_year})")
        c1, c2 = st.columns(2)
        with c1:
            if "Outcome/Status" in df_combined.columns:
                outcome_counts = df_combined["Outcome/Status"].fillna("Unknown").value_counts().reset_index()
                outcome_counts.columns = ["Outcome", "Count"]
                fig_pie_out = px.pie(outcome_counts, names="Outcome", values="Count", hole=0.45, title="Treatment Outcomes")
                st.plotly_chart(fig_pie_out, use_container_width=True)
        with c2:
            if "Registration Group" in df_combined.columns:
                reg_counts = df_combined["Registration Group"].fillna("Unknown").value_counts().reset_index()
                reg_counts.columns = ["Registration Group", "Count"]
                fig_pie_reg = px.pie(reg_counts, names="Registration Group", values="Count", hole=0.45, title="Patient Registration Group")
                st.plotly_chart(fig_pie_reg, use_container_width=True)

        # --- FEATURE 2: Referral Source Removed, Replaced cleanly by Bacteriologic Status ---
        c_site, c_bac = st.columns(2)
        with c_site:
            if "Anatomical Site" in df_combined.columns:
                site_counts = df_combined["Anatomical Site"].fillna("Unknown").value_counts().reset_index()
                site_counts.columns = ["Site", "Count"]
                fig_site = px.pie(site_counts, names="Site", values="Count", hole=0.45, title="Anatomical Site (P vs. EP)")
                fig_site.update_traces(marker_colors=['#0ea5e9', '#8b5cf6'])
                st.plotly_chart(fig_site, use_container_width=True)

        with c_bac:
            if "Bacteriologic Status" in df_combined.columns:
                bac_counts = df_combined["Bacteriologic Status"].fillna("Unknown").value_counts().reset_index()
                bac_counts.columns = ["Bacteriologic Status", "Count"]
                fig_bar_bac = px.bar(bac_counts, x="Bacteriologic Status", y="Count", text_auto=True, title="Bacteriologic Status")
                fig_bar_bac.update_traces(marker_color='#10b981')
                st.plotly_chart(fig_bar_bac, use_container_width=True)

    with tab4:
        st.subheader(f"Preventive Treatment (TPT) Analytics ({selected_year})")
        if not df_tpt.empty:
            st.metric(f"Total Patients on TPT ({selected_year})", len(df_tpt))
            c3, c4 = st.columns(2)
            with c3:
                if "Indication for TPT" in df_tpt.columns:
                    ind_counts = df_tpt["Indication for TPT"].fillna("Unknown").value_counts().reset_index()
                    ind_counts.columns = ["Indication", "Count"]
                    fig_ind = px.pie(ind_counts, names="Indication", values="Count", hole=0.4, title="Indication for TPT")
                    st.plotly_chart(fig_ind, use_container_width=True)
            with c4:
                if "TPT Regimen" in df_tpt.columns:
                    reg_tpt_counts = df_tpt["TPT Regimen"].fillna("Unknown").value_counts().reset_index()
                    reg_tpt_counts.columns = ["Regimen", "Count"]
                    fig_reg_tpt = px.bar(reg_tpt_counts, x="Regimen", y="Count", text_auto=True, title="TPT Regimen Distribution")
                    fig_reg_tpt.update_traces(marker_color='#8b5cf6')
                    st.plotly_chart(fig_reg_tpt, use_container_width=True)
        else:
            st.info(f"No TPT data available for {selected_year} or TPT filter is disabled.")

    with tab5:
        # --- FEATURE 3: HIV Pivot Table ---
        st.subheader(f"TB-HIV Collaborative Activities ({selected_year})")
        if not df_hiv.empty:
            num_col = "All Reg Group 15 above TB Cases Tested or with Known HIV Status"
            den_col = "All Reg Group 15 above TB Cases"
            
            if "Facility" in df_hiv.columns and "Quarter" in df_hiv.columns and num_col in df_hiv.columns and den_col in df_hiv.columns:
                total_tb_15 = df_hiv[den_col].sum()
                total_tested = df_hiv[num_col].sum()
                testing_rate = (total_tested / total_tb_15 * 100) if total_tb_15 > 0 else 0
                
                c5, c6 = st.columns(2)
                c5.metric("Eligible TB Patients (15+ yrs)", f"{int(total_tb_15):,}")
                c6.metric("Tested for HIV", f"{int(total_tested):,}", f"{testing_rate:.1f}% Coverage")
                st.markdown("<hr>", unsafe_allow_html=True)
                
                # --- FIX: Format Quarters Cleanly (e.g. '1.0' becomes 'Q1') ---
                df_hiv_clean = df_hiv.copy()
                df_hiv_clean['Quarter'] = pd.to_numeric(df_hiv_clean['Quarter'], errors='coerce')
                df_hiv_clean = df_hiv_clean.dropna(subset=['Quarter'])
                df_hiv_clean['Quarter'] = df_hiv_clean['Quarter'].astype(int).apply(lambda x: f"Q{x}")
                
                # Dynamic Pivot Table
                grouped = df_hiv_clean.groupby(['Facility', 'Quarter'])[[num_col, den_col]].sum().reset_index()
                
                def format_coverage(row):
                    n = int(row[num_col])
                    d = int(row[den_col])
                    pct = (n / d * 100) if d > 0 else 0
                    if d == 0 and n == 0: return "-"
                    return f"{n} / {d} ({pct:.1f}%)"
                    
                grouped['Coverage'] = grouped.apply(format_coverage, axis=1)
                pivot_hiv = grouped.pivot(index='Facility', columns='Quarter', values='Coverage').fillna('-')
                
                st.markdown("##### HIV Testing Coverage by Facility and Quarter")
                st.dataframe(pivot_hiv, use_container_width=True)
            else:
                st.error("HIV Data columns do not match the expected ITIS export format.")
        else: st.info(f"No HIV data available for {selected_year}.")

    with tab6:
        map_style_choice = st.radio("Select Map Theme:", ["Light", "Street", "Satellite", "Dark"], horizontal=True, key="tb_map_theme")
        style_map = {"Light": "carto-positron-nolabels", "Street": "open-street-map", "Dark": "carto-darkmatter-nolabels", "Satellite": "white-bg"}
        label_color = '#ffffff' if map_style_choice == "Satellite" else '#000000'

        if muncity_input != "All Municipalities":
            st.subheader(f"Geographic Heatmap: Barangays in {muncity_input} ({selected_year})")
            brgy_geojson, err = fetch_barangay_geojson(muncity_input)
            if brgy_geojson and "Brgy" in df_combined.columns:
                all_geojson_brgys = [f['properties']['Standard_Name'] for f in brgy_geojson['features']]
                all_geojson_originals = [f['properties']['Original_Name'] for f in brgy_geojson['features']]
                base_df = pd.DataFrame({"Join_Key": all_geojson_brgys, "Barangay_Display": all_geojson_originals, "Base_Cases": 0})
                curr_cases = df_combined.groupby("Brgy").size().reset_index(name="Filtered_Cases")
                curr_cases["Join_Key"] = curr_cases["Brgy"].apply(clean_brgy_name)
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
                    max_cases = int(map_data["Total Cases"].max())
                    safe_max = max(1, max_cases)
                    try:
                        # 1. Map Theme Router
                        if map_style_choice == "Dark":
                            tiles = "CartoDB dark_matter"
                            attr = "CartoDB"
                            text_col, outline_col = "white", "black"
                        elif map_style_choice == "Satellite":
                            tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                            attr = "Esri"
                            text_col, outline_col = "white", "black"
                        else:
                            tiles = "CartoDB positron"
                            attr = "CartoDB"
                            text_col, outline_col = "black", "white"
                            
                        # 2. Initialize the Canvas
                        m = folium.Map(location=[17.58, 120.83], zoom_start=9.2, tiles=tiles, attr=attr)
                        
                        # 3. Draw the Choropleth Polygons
                        folium.Choropleth(
                            geo_data=abra_geojson,
                            name="choropleth",
                            data=map_data,
                            columns=["Muncity", "Total Cases"],
                            key_on="feature.properties.Standard_Name",
                            fill_color="Blues",
                            fill_opacity=0.85,
                            line_opacity=0.8,
                            line_color="gray",
                            legend_name="Total TB Cases"
                        ).add_to(m)
                        
                        # 4. INJECT HTML LABELS (Forces 100% Visibility)
                        for i in range(len(lons)):
                            # Use inline-block so the div tightly hugs the text, preventing invisible overlaps
                            html_label = f'''
                                <div style="display: inline-block; font-size: 11pt; font-weight: bold; font-family: Arial; color: {text_col}; text-align: center; line-height: 1.1; 
                                text-shadow: -1.5px -1.5px 0 {outline_col}, 1.5px -1.5px 0 {outline_col}, -1.5px 1.5px 0 {outline_col}, 1.5px 1.5px 0 {outline_col}; white-space: nowrap;">
                                    {texts[i]}
                                </div>
                            '''
                            folium.map.Marker(
                                [lats[i], lons[i]],
                                icon=DivIcon(
                                    # Shrink the physical icon boundary to be incredibly small so they don't block each other
                                    icon_size=(10, 10), 
                                    icon_anchor=(0, 0), # Centers the div natively based on text size
                                    html=html_label,
                                    # Give it a CSS class to center transform it perfectly over the coordinate
                                    class_name="custom-div-icon" 
                                )
                            ).add_to(m)
                            
                        # Inject CSS to center the DivIcon exactly over the anchor point
                        m.get_root().html.add_child(folium.Element("<style>.custom-div-icon { transform: translate(-50%, -50%); }</style>"))
                            
                        # 5. Render to Streamlit without triggering reruns
                        st_folium(m, use_container_width=True, height=850, returned_objects=[])
                        
                    except Exception as e:
                        st.error(f"Folium encountered an error rendering the map: {e}")
                else: st.warning("No geographic mapping data available for the selected filters.")
            else: st.error(err if err else "Barangay column (Brgy) missing in data.")
                
        else:
            st.subheader(f"Geographic Heatmap: Municipalities in Abra ({selected_year})")
            base_df = pd.DataFrame({"Muncity": ALL_ABRA_MUNICIPALITIES, "Base_Cases": 0})
            curr_cases = df_combined.groupby("Muncity").size().reset_index(name="Filtered_Cases")
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
                        lons.append(float(lon)); lats.append(float(lat))
                        texts.append(f"{std_name.title()}<br>{int(cases)}")
                
                if not map_data.empty and "Total Cases" in map_data.columns:
                    max_cases = int(map_data["Total Cases"].max())
                    safe_max = max(1, max_cases)
                    try:
                        fig_map = go.Figure(go.Choroplethmap(
                            geojson=abra_geojson, 
                            locations=map_data['Muncity'], 
                            featureidkey='properties.Standard_Name', 
                            z=map_data['Total Cases'], 
                            text=map_data['Muncity'],
                            hovertemplate="<b>%{text}</b><br>Total Cases: %{z}<extra></extra>",
                            colorscale="Blues",
                            zmin=0, 
                            zmax=safe_max,
                            marker={"opacity": 1.0, "line": {"width": 0.5, "color": "gray"}}
                        ))
                        fig_map.update_layout(
                            map_style=style_map[map_style_choice],
                            map_zoom=8.8,
                            map_center={"lat": 17.58, "lon": 120.83},
                            margin={"r":0,"t":20,"l":0,"b":0}, height=850
                        )
                        if map_style_choice == "Satellite": fig_map.update_layout(map_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}])
                        fig_map.add_trace(go.Scattermap(lon=lons, lat=lats, mode='markers+text', text=texts, textposition='middle center',textfont=dict(size=12, color=label_color), marker=dict(allowoverlap=True, size=0, opacity=0), hoverinfo='skip', showlegend=False))
                        st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': False})
                    except Exception as e: st.error(f"Plotly encountered an error rendering the map: {e}")
                else: st.warning("No geographic mapping data available for the selected filters.")
            else: st.error("Could not fetch the Abra geographic boundaries.")

    with tab7:
        st.subheader(f"Filtered TB Registry ({selected_year})")
        st.caption("Showing key programmatic columns. Use the Download button in the sidebar for the full dataset.")
        clean_cols = ["TB/TPT Case No.", "Case_Type", "First Name", "Last Name", "Age", "Sex", "Brgy", "Muncity", "Bacteriologic Status", "Outcome/Status", "Date Started Tx"]
        available_cols = [col for col in clean_cols if col in df_combined.columns]
        
        # FIX: Force PyArrow to treat mixed-type columns as strings to prevent crashes
        safe_df = df_combined.copy()
        for col in safe_df.columns:
            safe_df[col] = safe_df[col].astype(str)
            
        if available_cols: st.dataframe(safe_df[available_cols], use_container_width=True, hide_index=True, height=600)
        else: st.dataframe(safe_df, use_container_width=True, hide_index=True, height=600)

def main():
    if not st.session_state.logged_in:
        if st.session_state.current_page == 'register':
            render_register()
        else:
            render_login()
    else:
        # Determine which profile image to show based on context
        if st.session_state.active_program == 'dengue':
            profile_img_url = "https://github.com/RJA24/abra_dengue_cases/blob/main/dengue.png?raw=true"
        else:
            profile_img_url = "https://github.com/RJA24/abra_sia_2026/blob/main/PHO%20logo.png?raw=true"

        # --- Clean, professional sidebar matching the Upwork/Coinbase styling ---
        with st.sidebar:
            
            # Centered profile block utilizing dynamic image
            st.markdown(f"""
            <div style="text-align: center; padding-bottom: 20px; border-bottom: 1px solid #e2e8f0; margin-bottom: 15px;">
                <img src="{profile_img_url}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: contain; margin-bottom: 10px; background-color: #f8fafc; padding: 5px; border: 1px solid #e2e8f0;">
                <h3 style="margin: 0; color: #0f172a; font-size: 1.2rem;">{st.session_state.username}</h3>
                <p style="margin: 0; color: #64748b; font-size: 0.9rem;">{st.session_state.role.title()}</p>
            </div>
            """, unsafe_allow_html=True)
            
            
            if st.session_state.role == 'admin':
                if st.button("Admin Panel", icon=":material/build:", use_container_width=True): navigate('admin')
            if st.button("Profile & Settings", icon=":material/settings:", use_container_width=True): navigate('settings')
            if st.button("Sign out", icon=":material/logout:", use_container_width=True): logout()

        # --- Routing Logic ---
        if st.session_state.current_page == 'admin' and st.session_state.role == 'admin':
            if st.button("Back to Menu", icon=":material/arrow_back:"): navigate('main_menu')
            render_admin_panel()
        elif st.session_state.current_page == 'settings':
            if st.button("Back to Menu", icon=":material/arrow_back:"): navigate('main_menu')
            render_settings()
        else:
            if st.session_state.active_program == 'dengue':
                render_dengue()
            elif st.session_state.active_program == 'tb':
                render_tb()
            else:
                render_main_menu()

if __name__ == "__main__":
    main()