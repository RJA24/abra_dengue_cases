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
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- Clean, Professional CSS tailored to your TOML ---
st.markdown("""
    <style>
    /* Adjust top padding to pull title higher */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    
    /* Hide default header/footer for a clean app feel */
    header { background: transparent !important; }
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    
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
        justify-content: flex-start !important; /* Left-align the text */
        color: #334155 !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #f1f5f9 !important; /* Subtle hover effect */
        color: #0f172a !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button p {
        font-size: 16px !important;
    }
    /* ---------------------------------------------------- */

    /* Giant Program Buttons styling */
    div.element-container:has(.big-btn-marker) + div.element-container button {
        height: 140px !important;
        border-radius: 12px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        transition: all 0.2s ease-in-out !important;
        justify-content: center !important; /* Ensure main menu buttons stay centered */
    }
    div.element-container:has(.big-btn-marker) + div.element-container button p {
        font-size: 24px !important;
        font-weight: 600 !important;
        color: #0f172a !important;
    }
    div.element-container:has(.big-btn-marker) + div.element-container button:hover {
        border-color: #2563eb !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15) !important;
    }
    div.element-container:has(.big-btn-marker) + div.element-container button:hover p {
        color: #2563eb !important;
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
    raw = unicodedata.normalize('NFKD', raw).encode('ASCII', 'ignore').decode('utf-8')
    raw_alpha = re.sub(r'[^A-Z]', '', raw)
    if "LICUAN" in raw_alpha or "BAAY" in raw_alpha: return "LICUAN-BAAY"
    if "PENAR" in raw_alpha or "RUBIA" in raw_alpha: return "PEÑARRUBIA"
    if "PAZ" in raw_alpha: return "LA PAZ"
    if "JUAN" in raw_alpha: return "SAN JUAN"
    if "ISIDRO" in raw_alpha: return "SAN ISIDRO"
    if "QUINTIN" in raw_alpha: return "SAN QUINTIN"
    for muni in ALL_ABRA_MUNICIPALITIES:
        if re.sub(r'[^A-Z]', '', muni.replace("Ñ", "N")) in raw_alpha: return muni
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
    for k in keys:
        if k in upper_props:
            std = clean_muni_name(upper_props[k])
            if std in ALL_ABRA_MUNICIPALITIES: return std
    for val in props.values():
        std = clean_muni_name(str(val))
        if std in ALL_ABRA_MUNICIPALITIES: return std
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
    st.markdown("<h2 style='text-align: center;'>Provincial Epidemiology and Surveillance Unit</h2>", unsafe_allow_html=True)
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
    st.title("Admin Control Panel")
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
    st.title("Account Settings")
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
    # --- BACKGROUND IMAGE INJECTION ---
    bg_css = """
    <style>
    .stApp {
        background: linear-gradient(
            rgba(240, 242, 246, 0.8), 
            rgba(240, 242, 246, 0.8)
        ), 
        url("https://github.com/RJA24/abra_sia_2026/blob/main/Abra%20(2).png?raw=true") !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }
    header[data-testid="stHeader"] { background: rgba(0,0,0,0) !important; }
    </style>
    """
    st.markdown(bg_css, unsafe_allow_html=True)
    # ----------------------------------

    st.markdown("<h1 style='text-align: center; font-size: 3rem; margin-bottom: 50px;'>Provincial Epidemiology and Surveillance Unit</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3, gap="large")
    
    with col1:
        st.markdown('<span class="big-btn-marker"></span>', unsafe_allow_html=True)
        if st.button("Dengue", use_container_width=True):
            st.session_state.active_program = 'dengue'
            st.rerun()
            
    with col2:
        st.markdown('<span class="big-btn-marker"></span>', unsafe_allow_html=True)
        if st.button("Place Holder 1", use_container_width=True):
            pass
            
    with col3:
        st.markdown('<span class="big-btn-marker"></span>', unsafe_allow_html=True)
        if st.button("Place Holder 2", use_container_width=True):
            pass

def render_dengue():
    with st.sidebar:
        if st.button("⬅️ Back to Menu", use_container_width=True):
            st.session_state.active_program = None
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 📊 Surveillance Filters")
        
        df = load_data()
        
        with st.expander("Filter Options", expanded=True):
            muni_options = ["All Municipalities"] + sorted(df["Muncity"].dropna().unique().tolist())
            muncity_input = st.selectbox("Select Municipality:", options=muni_options, index=0)
            sex_input = st.multiselect("Select Sex:", options=df["Sex"].dropna().unique(), default=[])
            clin_input = st.multiselect("Clinical Classification:", options=df["ClinClass"].dropna().unique(), default=[])
            
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    muncity_filter = df["Muncity"].dropna().unique() if muncity_input == "All Municipalities" else [muncity_input]
    sex_filter = sex_input if sex_input else df["Sex"].dropna().unique()
    clin_filter = clin_input if clin_input else df["ClinClass"].dropna().unique()
    filtered_df = df.query("Muncity in @muncity_filter & Sex in @sex_filter & ClinClass in @clin_filter")

    st.title("Abra PESU: Dengue Surveillance Dashboard")
    st.markdown("---")

    total_cases = len(filtered_df)
    total_deaths = len(filtered_df[filtered_df["Outcome"] == "D"]) if "Outcome" in filtered_df.columns else 0
    avg_age = round(filtered_df["AgeYears"].mean(), 1) if not filtered_df.empty and "AgeYears" in filtered_df.columns else 0
    affected_muni = filtered_df["Muncity"].nunique()

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
    with col4: st.markdown(create_kpi_card("Affected Municipalities", f"{affected_muni} / 27", "#f59e0b"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Epidemiological Trends", "Demographics & Geography", "Clinical & Laboratory", "Choropleth Map", "Raw Line List"
    ])

    with tab1:
        if "MorbidityWeek" in filtered_df.columns:
            cases_by_week = filtered_df.groupby("MorbidityWeek").size().reset_index(name="Case Count")
            fig_line = px.line(cases_by_week, x="MorbidityWeek", y="Case Count", markers=True, title="Dengue Epidemic Curve by Morbidity Week")
            fig_line.update_traces(line_color='#2563eb', marker=dict(size=10))
            fig_line.update_layout(height=500)
            st.plotly_chart(fig_line, use_container_width=True)

        if "MorbidityMonth" in filtered_df.columns:
            month_counts = filtered_df.groupby("MorbidityMonth").size().reset_index(name="Cases")
            fig_month = px.bar(month_counts, x="MorbidityMonth", y="Cases", text_auto=True, title="Dengue Cases by Morbidity Month")
            fig_month.update_traces(marker_color='#1d4ed8')
            fig_month.update_layout(height=450)
            st.plotly_chart(fig_month, use_container_width=True)
        
    with tab2:
        if "Muncity" in filtered_df.columns:
            muncity_counts = filtered_df["Muncity"].value_counts().reset_index()
            muncity_counts.columns = ["Municipality", "Count"]
            fig_bar = px.bar(muncity_counts, x="Municipality", y="Count", title="Total Cases per Municipality", text_auto=True)
            fig_bar.update_traces(marker_color='#2563eb')
            fig_bar.update_layout(xaxis={'categoryorder':'total descending'}, height=500)
            st.plotly_chart(fig_bar, use_container_width=True)

        if "AgeYears" in filtered_df.columns and "Sex" in filtered_df.columns:
            fig_hist = px.histogram(filtered_df, x="AgeYears", nbins=25, title="Age and Sex Distribution of Cases", color="Sex", barmode="group", color_discrete_sequence=["#2563eb", "#ec4899"])
            fig_hist.update_layout(height=500)
            st.plotly_chart(fig_hist, use_container_width=True)
        
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

def main():
    if not st.session_state.logged_in:
        if st.session_state.current_page == 'register':
            render_register()
        else:
            render_login()
    else:
        # --- Clean, professional sidebar matching the Upwork/Coinbase styling ---
        with st.sidebar:
            
            # Centered profile block 
            st.markdown(f"""
            <div style="text-align: center; padding-bottom: 20px; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px;">
                <div style="font-size: 60px; line-height: 1;">👤</div>
                <h3 style="margin: 10px 0 0 0; color: #0f172a;">{st.session_state.username}</h3>
                <p style="margin: 0; color: #64748b; font-size: 14px;">{st.session_state.role.title()}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Borderless list items with icons
            if st.session_state.role == 'admin':
                if st.button("🛡️ Admin Panel", use_container_width=True): navigate('admin')
            if st.button("⚙️ Profile & Settings", use_container_width=True): navigate('settings')
            
            # Add some spacing before the logout button
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("🚪 Sign out", use_container_width=True): logout()

        # --- Routing Logic ---
        if st.session_state.current_page == 'admin' and st.session_state.role == 'admin':
            if st.button("⬅️ Back to Menu"): navigate('main_menu')
            render_admin_panel()
        elif st.session_state.current_page == 'settings':
            if st.button("⬅️ Back to Menu"): navigate('main_menu')
            render_settings()
        else:
            if st.session_state.active_program == 'dengue':
                render_dengue()
            else:
                render_main_menu()

if __name__ == "__main__":
    main()