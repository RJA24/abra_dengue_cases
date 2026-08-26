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

# --- Page Configuration ---
st.set_page_config(
    page_title="Abra PESU Portal", 
    page_icon="https://github.com/RJA24/abra_sia_2026/blob/main/PHO%20logo.png?raw=true", 
    layout="wide", 
    initial_sidebar_state="Auto")

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
    # Load 2026 Data
    d26_ds = load_tb_data("2026 DSTB")
    d26_dr = load_tb_data("2026 DRTB")
    d26 = pd.concat([d26_ds, d26_dr], ignore_index=True)
    d26['Year'] = 2026
    
    # Load Historical Data (2015-2025)
    h_ds = load_tb_data("DSTB 2015-2025")
    h_dr = load_tb_data("DRTB 2015-2025")
    hist = pd.concat([h_ds, h_dr], ignore_index=True)
    hist['Year'] = pd.to_numeric(hist['Year'], errors='coerce')
    
    # Combine everything into one master dataframe
    combined = pd.concat([d26, hist], ignore_index=True)
    return combined

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
    st.caption("Manage user access and edit roles.")
    
    try:
        users_df = get_all_users()
        
        if not users_df.empty:
            for index, row in users_df.iterrows():
                with st.container():
                    col_user, col_role, col_actions = st.columns([2, 2, 3])
                    
                    with col_user:
                        st.write(f"**{row['username']}**")
                        if row['status'] == 'pending':
                            st.warning("PENDING")
                        else:
                            st.success("APPROVED")
                            
                    with col_role:
                        role_options = ["user", "admin"]
                        current_idx = role_options.index(row['role']) if row['role'] in role_options else 0
                        
                        selected_role = st.selectbox(
                            "Role Assignment", 
                            options=role_options, 
                            index=current_idx, 
                            key=f"role_{row['username']}",
                            label_visibility="collapsed"
                        )
                        
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

    # Inject the PHO Logo centered above the title
    st.markdown(f"""
    <div style='text-align: center; margin-bottom: 10px;'>
        <img src="https://github.com/RJA24/abra_sia_2026/blob/main/PHO%20logo.png?raw=true" width="85" style="filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.3));">
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
                # 1. ANCHOR TIMELINE: Get the latest 4 weeks from the GLOBAL dataset, not the filtered one.
                # This prevents the columns from time-traveling backward when a specific municipality is selected.
                global_df = df.copy()
                global_df['MW_Clean'] = pd.to_numeric(global_df['MorbidityWeek'], errors='coerce')
                global_weeks = sorted(global_df['MW_Clean'].dropna().astype(int).unique())
                latest_weeks = global_weeks[-4:] if len(global_weeks) >= 4 else global_weeks
                
                # 2. Clean the CURRENTLY FILTERED dataset
                clean_df = filtered_df.copy()
                clean_df['MW_Clean'] = pd.to_numeric(clean_df['MorbidityWeek'], errors='coerce')
                clean_df = clean_df.dropna(subset=['MW_Clean'])
                clean_df['MW_Clean'] = clean_df['MW_Clean'].astype(int)
                
                if latest_weeks:
                    # 3. Filter data explicitly to the global top 4 weeks
                    cluster_df = clean_df[clean_df["MW_Clean"].isin(latest_weeks)]
                    
                    if not cluster_df.empty:
                        # 4. Create the Pivot Table (Rows: Muncity/Barangay | Cols: MWs)
                        pivot_cluster = pd.crosstab(
                            index=[cluster_df['Muncity'], cluster_df['Barangay']],
                            columns=cluster_df['MW_Clean']
                        ).fillna(0).astype(int)
                        
                        # Guarantee all 4 weeks exist as columns
                        for w in latest_weeks:
                            if w not in pivot_cluster.columns:
                                pivot_cluster[w] = 0
                        pivot_cluster = pivot_cluster[latest_weeks]
                        
                        # 5. Calculate Total
                        pivot_cluster['Total'] = pivot_cluster.sum(axis=1)
                        
                        # 6. Apply the Epidemiological Clustering threshold (Total >= 3)
                        pivot_cluster = pivot_cluster[pivot_cluster['Total'] >= 3].reset_index()
                        
                        if not pivot_cluster.empty:
                            # 7. Force correct alphabetical sorting including 'Ñ'
                            pivot_cluster['Sort_Key'] = pivot_cluster['Muncity'].str.replace('Ñ', 'N')
                            pivot_cluster = pivot_cluster.sort_values(by=['Sort_Key', 'Barangay']).drop(columns=['Sort_Key'])
                            
                            # 8. Format column names for presentation
                            rename_dict = {w: f"MW{w}" for w in latest_weeks}
                            pivot_cluster = pivot_cluster.rename(columns=rename_dict)
                            pivot_cluster.rename(columns={'Muncity': 'Municipality'}, inplace=True)
                            
                            # 9. Pure Python/CSS Custom Color (Solid Green for any value > 0)
                            def apply_green_color(val):
                                try:
                                    if int(val) > 0:
                                        return 'background-color: #8bc34a; color: #0f172a; font-weight: bold;' 
                                    return ''
                                except:
                                    return ''
                                    
                            color_cols = [f"MW{w}" for w in latest_weeks]
                            
                            # Pandas 2.1+ uses .map() for element-wise styling
                            if hasattr(pivot_cluster.style, 'map'):
                                styled_df = pivot_cluster.style.map(apply_green_color, subset=color_cols)
                            else: # Fallback for older pandas versions
                                styled_df = pivot_cluster.style.applymap(apply_green_color, subset=color_cols)
                            
                            st.dataframe(styled_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No clustering barangays (≥ 3 cases) detected in the last 4 morbidity weeks.")
                    else:
                        st.info("No case data available for the latest 4 morbidity weeks.")
                else:
                    st.info("Not enough numeric morbidity week data to calculate clustering.")
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
        map_style_choice = st.radio("Select Map Theme:", ["Light", "Street", "Satellite", "Dark"], horizontal=True)
        
        style_map = {
            "Light": "carto-positron",
            "Street": "open-street-map",
            "Dark": "carto-darkmatter",
            "Satellite": "white-bg" 
        }
        label_color = 'white' if map_style_choice in ["Dark", "Satellite"] else 'black'

        if muncity_input != "All Municipalities":
            st.subheader(f"Geographic Heatmap: Barangays in {muncity_input}")
            brgy_geojson, err = fetch_barangay_geojson(muncity_input)
            
            if brgy_geojson and "Barangay" in filtered_df.columns:
                all_geojson_brgys = [f['properties']['Standard_Name'] for f in brgy_geojson['features']]
                all_geojson_originals = [f['properties']['Original_Name'] for f in brgy_geojson['features']]
                
                base_df = pd.DataFrame({"Join_Key": all_geojson_brgys, "Barangay_Display": all_geojson_originals, "Base_Cases": 0})
                curr_cases = filtered_df.groupby("Barangay").size().reset_index(name="Filtered_Cases")
                curr_cases["Join_Key"] = curr_cases["Barangay"].apply(clean_brgy_name)
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
                        lons.append(lon); lats.append(lat)
                        texts.append(f"{display_name.title()}<br>{int(cases)}")
                
                cam_lat = np.mean(lats) if lats else 17.58
                cam_lon = np.mean(lons) if lons else 120.83
                
                fig_map = px.choropleth_mapbox(
                    map_data, geojson=brgy_geojson, locations='Join_Key', featureidkey='properties.Standard_Name', 
                    color='Total Cases', hover_name='Barangay_Display', color_continuous_scale="Reds",
                    mapbox_style=style_map[map_style_choice], zoom=11.5, center={"lat": cam_lat, "lon": cam_lon}, opacity=0.85
                )
                
                if map_style_choice == "Satellite":
                    fig_map.update_layout(mapbox_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}])
                
                fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=12, color=label_color), hoverinfo='skip', showlegend=False))
                fig_map.update_layout(margin={"r":0,"t":20,"l":0,"b":0}, height=700)
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.error(err if err else "Barangay column missing in data.")
                
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
                        lons.append(lon); lats.append(lat)
                        texts.append(f"{std_name.title()}<br>{int(cases)}")
                        
                fig_map = px.choropleth_mapbox(
                    map_data, geojson=abra_geojson, locations='Muncity', featureidkey='properties.Standard_Name', 
                    color='Total Cases', hover_name='Muncity', color_continuous_scale="Reds",
                    mapbox_style=style_map[map_style_choice], zoom=8.8, center={"lat": 17.58, "lon": 120.83}, opacity=0.85
                )
                
                if map_style_choice == "Satellite":
                    fig_map.update_layout(mapbox_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}])

                fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=12, color=label_color), hoverinfo='skip', showlegend=False))
                fig_map.update_layout(margin={"r":0,"t":20,"l":0,"b":0}, height=700)
                st.plotly_chart(fig_map, use_container_width=True)
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
    # 1. Load Universal Masterlist Data
    df_all_raw = get_all_core_tb()

    with st.sidebar:
        if st.button("Back to Menu", icon=":material/arrow_back:", use_container_width=True):
            st.session_state.active_program = None
            st.rerun()
            
        st.markdown("<hr style='margin: 15px 0; border: none; border-bottom: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #0f172a; margin: 0 0 15px 0;'><i class='fa-solid fa-folder-open' style='color: #475569;'></i> TB Controls</h4>", unsafe_allow_html=True)
        
        # --- NEW: Specific Year Selector ---
        available_years = list(range(2026, 2014, -1))
        selected_year = st.selectbox("Select Year", options=available_years, index=0)

        # Municipality Filter
        if not df_all_raw.empty and "Muncity" in df_all_raw.columns:
            muni_options = ["All Municipalities"] + sorted(df_all_raw["Muncity"].dropna().unique().tolist())
            muncity_input = st.selectbox("Filter Municipality", options=muni_options, index=0)
        else:
            muncity_input = "All Municipalities"
            
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("Refresh Data", icon=":material/refresh:", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # 2. Apply Filters globally for Trends
    if muncity_input != "All Municipalities":
        df_all_filtered = df_all_raw[df_all_raw["Muncity"] == muncity_input]
    else:
        df_all_filtered = df_all_raw

    # Extract Data for the specifically selected year (and the previous year for YOY math)
    df_combined = df_all_filtered[df_all_filtered['Year'] == selected_year]
    df_prev_year = df_all_filtered[df_all_filtered['Year'] == (selected_year - 1)]
    
    # Load auxiliary data based on year
    df_tpt = get_aux_tb_data('TPT', selected_year)
    df_hiv = get_aux_tb_data('HIV', selected_year)

    # --- DOWNLOAD BUTTON IN SIDEBAR ---
    with st.sidebar:
        if not df_combined.empty:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            csv_data = df_combined.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"Download {selected_year} Data",
                data=csv_data,
                file_name=f"Abra_TB_Data_{selected_year}_{muncity_input.replace(' ', '_')}.csv",
                mime="text/csv",
                icon=":material/download:",
                use_container_width=True
            )

    st.title("Abra PESU: Tuberculosis Control Program")
    st.markdown("---")

    if df_combined.empty:
        st.warning(f"No case data found for {selected_year} in the selected area.")
    
    # 3. YOY Metrics (Year Over Year)
    curr_cases = len(df_combined)
    prev_cases = len(df_prev_year)
    case_delta = curr_cases - prev_cases

    def get_success_count(df):
        if "Outcome/Status" in df.columns:
            return len(df[df["Outcome/Status"].str.upper().isin(["CURED", "TREATMENT COMPLETED"])])
        return 0

    curr_success = get_success_count(df_combined)
    prev_success = get_success_count(df_prev_year)
    success_delta = curr_success - prev_success

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
        # STRICT FILTER: Only count valid Abra municipalities (fixes the 28/27 bug)
        if 'Muncity' in df_combined.columns:
            valid_curr = df_combined[df_combined['Muncity'].isin(ALL_ABRA_MUNICIPALITIES)]
            curr_geo = valid_curr['Muncity'].nunique()
        else:
            curr_geo = 0
            
        if 'Muncity' in df_prev_year.columns:
            valid_prev = df_prev_year[df_prev_year['Muncity'].isin(ALL_ABRA_MUNICIPALITIES)]
            prev_geo = valid_prev['Muncity'].nunique()
        else:
            prev_geo = 0
            
        geo_delta = curr_geo - prev_geo
        geo_val = f"{curr_geo} / 27"
    else:
        geo_kpi_title = "Affected Barangays"
        curr_geo = df_combined['Brgy'].nunique() if 'Brgy' in df_combined.columns else 0
        prev_geo = df_prev_year['Brgy'].nunique() if 'Brgy' in df_prev_year.columns else 0
        geo_delta = curr_geo - prev_geo
        total_brgy = ABRA_BRGY_COUNTS.get(muncity_input, "?")
        geo_val = f"{curr_geo} / {total_brgy}"

    # --- UPGRADED PREMIUM HTML CARDS WITH YOY DELTAS ---
    def create_yoy_card(title, value, border_color, delta_val, inverse_color=False):
        # Determine arrow and colors based on whether high/low is good/bad
        if delta_val > 0:
            arrow = "↑"
            text_color = "#dc2626" if inverse_color else "#16a34a" # Red if inverse (bad), Green if normal (good)
            bg_color = "#fee2e2" if inverse_color else "#dcfce3"
        elif delta_val < 0:
            arrow = "↓"
            text_color = "#16a34a" if inverse_color else "#dc2626" # Green if inverse (good), Red if normal (bad)
            bg_color = "#dcfce3" if inverse_color else "#fee2e2"
        else:
            arrow = "→"
            text_color = "#64748b"
            bg_color = "#f1f5f9"
            
        return f"""
        <div style="background-color: #ffffff; padding: 22px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-left: 8px solid {border_color}; text-align: center;">
            <p style="margin: 0; font-size: 1rem; color: #64748b; font-weight: 600; text-transform: uppercase;">{title}</p>
            <h2 style="margin: 10px 0 10px 0; font-size: 2.6rem; color: #0f172a; font-weight: 800;">{value}</h2>
            <span style="color: {text_color}; font-size: 0.85rem; font-weight: 700; background-color: {bg_color}; padding: 4px 10px; border-radius: 20px;">
                {arrow} {abs(delta_val)} vs prev year
            </span>
        </div>
        """

    col1, col2, col3 = st.columns(3)
    with col1: 
        # Inverse: Fewer cases = Good (Green)
        st.markdown(create_yoy_card(f"Total Cases ({selected_year})", f"{curr_cases:,}", "#2563eb", case_delta, inverse_color=True), unsafe_allow_html=True)
    with col2: 
        # Normal: More successes = Good (Green)
        st.markdown(create_yoy_card(f"Successful Outcomes", f"{curr_success:,}", "#10b981", success_delta, inverse_color=False), unsafe_allow_html=True)
    with col3: 
        # Inverse: Fewer affected areas = Good (Green)
        st.markdown(create_yoy_card(geo_kpi_title, geo_val, "#f59e0b", geo_delta, inverse_color=True), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Epidemiological Trends", "Demographics", "Clinical & Outcomes", 
        "Preventive Treatment (TPT)", "TB-HIV Collaboration", "Choropleth Map", "Raw Line List"
    ])

    with tab1:
        # --- MULTI-YEAR TREND CHART ---
        st.subheader("Multi-Year Trend Analysis")
        yearly_trend = df_all_filtered.groupby("Year").size().reset_index(name="Total Cases")
        if not yearly_trend.empty:
            fig_yoy = px.line(yearly_trend, x="Year", y="Total Cases", markers=True, title=f"Historical Case Trend (2015-{selected_year})")
            fig_yoy.update_traces(line_color='#2563eb', marker=dict(size=10))
            
            # Highlight the currently selected year
            fig_yoy.add_vline(x=selected_year, line_width=2, line_dash="dash", line_color="red", annotation_text=f"{selected_year} Selected")
            
            fig_yoy.update_layout(height=400, xaxis=dict(dtick=1))
            st.plotly_chart(fig_yoy, use_container_width=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # --- MONTHLY TREND CHART (Selected Year) ---
        st.subheader(f"Monthly Case Detection ({selected_year})")
        if "Date of Diagnosis" in df_combined.columns and not df_combined.empty:
            df_combined['Diag_Date'] = pd.to_datetime(df_combined['Date of Diagnosis'], errors='coerce')
            df_combined['Month'] = df_combined['Diag_Date'].dt.month
            
            # Map numbers to month names
            month_map = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
            
            monthly_trend = df_combined.dropna(subset=['Month']).groupby('Month').size().reset_index(name='Cases')
            monthly_trend['Month Name'] = monthly_trend['Month'].map(month_map)
            
            if not monthly_trend.empty:
                fig_trend = px.bar(monthly_trend, x='Month Name', y='Cases', text_auto=True, title=f"Cases by Month in {selected_year}")
                fig_trend.update_traces(marker_color='#d97706')
                fig_trend.update_layout(height=400, xaxis_title="Month", yaxis_title="Number of Cases")
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info(f"Insufficient date data for monthly trend analysis in {selected_year}.")

    with tab2:
        st.subheader(f"Demographic Distribution ({selected_year})")
        if "Muncity" in df_combined.columns and muncity_input == "All Municipalities":
            muncity_counts = df_combined["Muncity"].value_counts().reset_index()
            muncity_counts.columns = ["Municipality", "Count"]
            fig_bar = px.bar(muncity_counts, x="Municipality", y="Count", title="Total TB Cases per Municipality", text_auto=True)
            fig_bar.update_traces(marker_color="#0284c7") 
            fig_bar.update_layout(xaxis={'categoryorder':'total descending'}, height=500)
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

        c_source, c_site = st.columns(2)
        with c_source:
            if "Source of Patient" in df_combined.columns:
                src_counts = df_combined["Source of Patient"].fillna("Unknown").value_counts().reset_index()
                src_counts.columns = ["Source", "Count"]
                fig_src = px.bar(src_counts, x="Count", y="Source", orientation='h', title="Referral Source")
                fig_src.update_traces(marker_color='#f59e0b')
                fig_src.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_src, use_container_width=True)

        with c_site:
            if "Anatomical Site" in df_combined.columns:
                site_counts = df_combined["Anatomical Site"].fillna("Unknown").value_counts().reset_index()
                site_counts.columns = ["Site", "Count"]
                fig_site = px.pie(site_counts, names="Site", values="Count", hole=0.45, title="Anatomical Site (P vs. EP)")
                fig_site.update_traces(marker_colors=['#0ea5e9', '#8b5cf6'])
                st.plotly_chart(fig_site, use_container_width=True)

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
            st.info(f"No TPT data available for {selected_year}.")

    with tab5:
        st.subheader(f"TB-HIV Collaborative Activities ({selected_year})")
        if not df_hiv.empty:
            try:
                col_total_tb = "All Reg Group 15 above TB Cases"
                col_tested = "All Reg Group 15 above TB Cases Tested or with Known HIV Status"
                col_positive = "All Reg Group 15 above Confirmed HIV+TB Patients"
                col_art = "All Reg Group 15 above Confirmed HIV+TB Patients Started on ART"
                
                total_tb_15 = df_hiv[col_total_tb].sum()
                total_tested = df_hiv[col_tested].sum()
                total_pos = df_hiv[col_positive].sum()
                total_art = df_hiv[col_art].sum()
                
                testing_rate = (total_tested / total_tb_15 * 100) if total_tb_15 > 0 else 0
                
                c5, c6, c7 = st.columns(3)
                c5.metric("Eligible TB Patients (15+ yrs)", f"{total_tb_15:,}")
                c6.metric("Tested for HIV", f"{total_tested:,}", f"{testing_rate:.1f}% Coverage")
                c7.metric("Co-infected & on ART", f"{total_art:,} / {total_pos:,}")
                
                if "Facility" in df_hiv.columns:
                    facility_summary = df_hiv.groupby("Facility")[[col_total_tb, col_tested]].sum().reset_index()
                    fig_fac = px.bar(facility_summary, x="Facility", y=[col_total_tb, col_tested], 
                                     title="HIV Testing Compliance by Facility",
                                     labels={"value": "Patient Count", "variable": "Metric"},
                                     barmode="group")
                    st.plotly_chart(fig_fac, use_container_width=True)
            except Exception as e:
                st.error("HIV Data columns do not match the expected ITIS export format.")
        else:
            st.info(f"No HIV data available for {selected_year}.")

    with tab6:
        map_style_choice = st.radio("Select Map Theme:", ["Light", "Street", "Satellite", "Dark"], horizontal=True, key="tb_map_theme")
        style_map = {"Light": "carto-positron", "Street": "open-street-map", "Dark": "carto-darkmatter", "Satellite": "white-bg"}
        label_color = 'white' if map_style_choice in ["Dark", "Satellite"] else 'black'

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
                        lons.append(lon); lats.append(lat)
                        texts.append(f"{display_name.title()}<br>{int(cases)}")
                
                cam_lat = np.mean(lats) if lats else 17.58
                cam_lon = np.mean(lons) if lons else 120.83
                
                fig_map = px.choropleth_mapbox(
                    map_data, geojson=brgy_geojson, locations='Join_Key', featureidkey='properties.Standard_Name', 
                    color='Total Cases', hover_name='Barangay_Display', color_continuous_scale="Blues",
                    mapbox_style=style_map[map_style_choice], zoom=11.5, center={"lat": cam_lat, "lon": cam_lon}, opacity=0.85
                )
                
                if map_style_choice == "Satellite":
                    fig_map.update_layout(mapbox_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}])
                
                fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=12, color=label_color), hoverinfo='skip', showlegend=False))
                fig_map.update_layout(margin={"r":0,"t":20,"l":0,"b":0}, height=700)
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.error(err if err else "Barangay column (Brgy) missing in data.")
                
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
                        lons.append(lon); lats.append(lat)
                        texts.append(f"{std_name.title()}<br>{int(cases)}")
                        
                fig_map = px.choropleth_mapbox(
                    map_data, geojson=abra_geojson, locations='Muncity', featureidkey='properties.Standard_Name', 
                    color='Total Cases', hover_name='Muncity', color_continuous_scale="Blues",
                    mapbox_style=style_map[map_style_choice], zoom=8.8, center={"lat": 17.58, "lon": 120.83}, opacity=0.85
                )
                
                if map_style_choice == "Satellite":
                    fig_map.update_layout(mapbox_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}])

                fig_map.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode='text', text=texts, textfont=dict(size=12, color=label_color), hoverinfo='skip', showlegend=False))
                fig_map.update_layout(margin={"r":0,"t":20,"l":0,"b":0}, height=700)
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.error("Could not fetch the Abra geographic boundaries.")

    with tab7:
        st.subheader(f"Filtered TB Registry ({selected_year})")
        st.caption("Showing key programmatic columns. Use the Download button in the sidebar for the full dataset.")
        
        clean_cols = [
            "TB/TPT Case No.", "First Name", "Last Name", "Age", "Sex", 
            "Brgy", "Muncity", "Bacteriologic Status", "Outcome/Status", "Date Started Tx"
        ]
        available_cols = [col for col in clean_cols if col in df_combined.columns]
        
        if available_cols:
            st.dataframe(df_combined[available_cols], use_container_width=True, hide_index=True, height=600)
        else:
            st.dataframe(df_combined, use_container_width=True, hide_index=True, height=600)

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