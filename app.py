# app.py
import streamlit as st
import pandas as pd
import hashlib
from streamlit_gsheets import GSheetsConnection
from utils.validation import validate_dataset

# Import our newly modularized dashboards and constants
from utils.constants import SHEET_URL
from dengue.dashboard import render_dengue
from tb.dashboard import render_tb
from utils.audit import log_action
from utils.data import load_data, get_all_core_tb

# --- Page Configuration ---
st.set_page_config(
    page_title="Abra PESU Portal", 
    page_icon="https://github.com/RJA24/abra_sia_2026/blob/main/PHO%20logo.png?raw=true", 
    layout="wide", 
    initial_sidebar_state="auto"
)

# Inject FontAwesome Library
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

# --- Clean, Professional CSS ---
st.markdown("""
    <style>
    .stDeployButton, [data-testid="stAppDeployButton"] { display: none !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    #MainMenu, footer { visibility: hidden; } 
    .js-plotly-plot { margin-bottom: 2rem; }
    div.row-widget.stRadio > div { flex-direction: row; align-items: center; justify-content: center; background: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; }
    .stButton > button, .stPopover > button { color: #1e293b !important; border-color: #cbd5e1 !important; background-color: white !important; }
    .stButton > button:hover, .stPopover > button:hover, .stButton > button:focus, .stPopover > button:focus, .stButton > button:active, .stPopover > button:active { border-color: #1e293b !important; color: #1e293b !important; background-color: #f1f5f9 !important; box-shadow: none !important; }
    section[data-testid="stSidebar"] .stButton > button { background-color: transparent !important; border: none !important; box-shadow: none !important; padding: 8px 12px !important; border-radius: 8px !important; width: 100% !important; transition: all 0.2s ease !important; }
    section[data-testid="stSidebar"] .stButton > button div[data-testid="stMarkdownContainer"] { display: flex !important; width: 100% !important; justify-content: flex-start !important; }
    section[data-testid="stSidebar"] .stButton > button p { font-size: 15px !important; font-weight: 500 !important; color: #334155 !important; margin: 0 !important; text-align: left !important; }
    section[data-testid="stSidebar"] .stButton > button:hover { background-color: #f1f5f9 !important; }
    section[data-testid="stSidebar"] .stButton > button:hover p { color: #0f172a !important; }
    div.element-container:has(.big-btn-marker) + div.element-container button { height: 110px !important; border-radius: 55px !important; border: 2px solid rgba(255, 255, 255, 0.5) !important; background: rgba(255, 255, 255, 0.35) !important; backdrop-filter: blur(12px) !important; -webkit-backdrop-filter: blur(12px) !important; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1) !important; transition: all 0.3s ease-in-out !important; justify-content: center !important; }
    div.element-container:has(.big-btn-marker) + div.element-container button div[data-testid="stMarkdownContainer"] { justify-content: center !important; text-align: center !important; }
    div.element-container:has(.big-btn-marker) + div.element-container button p { font-size: 22px !important; font-weight: 900 !important; color: #000000 !important; text-transform: uppercase !important; letter-spacing: 1.5px !important; text-align: center !important; }
    div.element-container:has(.big-btn-marker) + div.element-container button:hover { border-color: rgba(255, 255, 255, 0.9) !important; background: rgba(255, 255, 255, 0.6) !important; box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.2) !important; transform: translateY(-3px) !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# GOOGLE SHEETS DATABASE & AUTH FUNCTIONS
# ==========================================

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
    if username.strip() in df['username'].values: return False
    new_row = pd.DataFrame({'username': [username.strip()], 'password': [hash_password(password)], 'role': ['user'], 'status': ['pending']})
    updated_df = pd.concat([df, new_row], ignore_index=True)
    save_users_df(updated_df)
    return True

def authenticate(username, password):
    # Secure Master Admin Check
    master_user = st.secrets["MASTER_ADMIN_USER"]
    master_pass = st.secrets["MASTER_ADMIN_PASS"]
    
    if username.strip() == master_user and password == master_pass:
        return 'admin', 'approved'
        
    # Standard User Check
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
    if clean_new_user != old_username and clean_new_user in df['username'].values: return False
    if new_password: df.loc[df['username'] == old_username, ['username', 'password']] = [clean_new_user, hash_password(new_password)]
    else: df.loc[df['username'] == old_username, 'username'] = clean_new_user
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
# UI COMPONENTS & MENUS
# ==========================================

def render_login():
    st.markdown("<h2 style='text-align: center;'>Abra Provincial Epidemiology and Surveillance Unit</h2><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        st.markdown("### Secure Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log In", use_container_width=True):
                role, status = authenticate(username, password)
                if role:
                    if status == 'approved':
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = role
                        navigate('main_menu')
                    else: st.error("Your account is pending admin approval.")
                else: st.error("Invalid username or password.")
        if st.button("Create new account", use_container_width=True): navigate('register')

def render_register():
    st.markdown("<h2 style='text-align: center;'>Create an Account</h2>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("register_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Request Access", use_container_width=True):
                if new_password != confirm_password: st.error("Passwords do not match.")
                elif len(new_username) < 3 or len(new_password) < 6: st.error("Username (min 3) and Password (min 6) must be longer.")
                else:
                    if create_user(new_username, new_password): st.success("Account created! Please wait for admin approval.")
                    else: st.error("Username already exists.")
        if st.button("Back to Login", use_container_width=True): navigate('login')

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
                                    log_action(st.session_state.username, "Changed Role", f"Updated {row['username']} to {selected_role}")
                                    st.rerun()
                        with col_actions:
                            c1, c2 = st.columns(2)
                            with c1:
                                if row['status'] == 'pending' and st.button("Approve", key=f"app_{row['username']}", use_container_width=True):
                                    update_user_status(row['username'], 'approved')
                                    update_user_role(row['username'], selected_role)
                                    log_action(st.session_state.username, "Approved User", f"Granted access to {row['username']}")
                                    st.rerun()
                            with c2:
                                if st.button("Delete User", key=f"del_{row['username']}", use_container_width=True):
                                    delete_user(row['username'])
                                    log_action(st.session_state.username, "Deleted User", f"Removed account: {row['username']}")
                                    st.rerun()
                        st.markdown("---")
            else: st.info("No other users found in the database.")
        except Exception: st.error("Could not load users. Check Google Service Account configuration.")

    with tab_db:
        st.caption("Upload cumulative 2026 export files to overwrite and update the master Google Sheets.")
        st.info("💡 **Backup Tip:** Google Sheets automatically saves 'Version History'. If you overwrite data by mistake, you can restore it directly in Google Drive.")
        
        report_mapping = {"Dengue Cases": "Dengue Cases", "2026 MN": "2026 MN", "DSTB": "2026 DSTB", "DRTB": "2026 DRTB", "TPT": "2026 TPT", "HIV": "2026 HIV", "2026 Report 5": "2026 Report 5"}
        selected_report = st.selectbox("1. Select Report to Update", options=list(report_mapping.keys()))
        target_worksheet = report_mapping[selected_report]
        
        uploaded_file = st.file_uploader("2. Upload Cumulative Export File (.csv or .xlsx)", type=['csv', 'xlsx'])
        if uploaded_file is not None:
            try:
                preview_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                
                # --- RUN DATA QUALITY VALIDATION ---
                st.markdown("### Data Quality Report")
                report = validate_dataset(preview_df, selected_report)
                
                score_color = "normal" if report["score"] >= 95 else ("off" if report["score"] >= 80 else "inverse")
                c1, c2 = st.columns([1, 3])
                c1.metric("Quality Score", f"{report['score']}%", delta=None, delta_color=score_color)
                
                with c2:
                    if report["score"] == 100.0:
                        st.success("✅ Perfect Dataset! No missing critical data or duplicates detected.")
                    else:
                        st.warning("⚠️ Anomalies Detected in Upload:")
                        for warning in report["warnings"]:
                            st.write(f"- {warning}")
                
                with st.expander(f"View Data Preview ({len(preview_df):,} rows)"): 
                    st.dataframe(preview_df.head(10), use_container_width=True)
                
                st.markdown("<hr>", unsafe_allow_html=True)
                
                if report['score'] < 95.0:
                    st.error("This dataset has a low quality score. Are you sure you want to push this to the live database?")
                
                # --- SAFETY CATCH ---
                confirm_overwrite = st.checkbox("I verify this data is correct and authorize overwriting the master Google Sheet.")
                
                if confirm_overwrite:
                    if st.button("Overwrite Master Database with this File", type="primary", use_container_width=True):
                        with st.spinner(f"Updating '{target_worksheet}' in Google Sheets..."):
                            try:
                                conn = st.connection("gsheets", type=GSheetsConnection)
                                try: conn.clear(spreadsheet=SHEET_URL, worksheet=target_worksheet)
                                except: pass
                                conn.update(spreadsheet=SHEET_URL, worksheet=target_worksheet, data=preview_df)
                                st.cache_data.clear()
                                
                                # Log the massive database update!
                                log_action(st.session_state.username, "Updated Database", f"Uploaded {len(preview_df)} records to {target_worksheet}. QA Score: {report['score']}%")
                                
                                st.success(f"✅ Successfully replaced data in '{target_worksheet}' with {len(preview_df):,} records!")
                            except Exception as e: st.error(f"Error updating Google Sheet: {e}")
            except Exception as e: st.error(f"Could not read the uploaded file: {e}")

def render_settings():
    st.markdown("### <i class='fa-solid fa-gear' style='color: #475569;'></i> Account Settings", unsafe_allow_html=True)
    with st.columns([1, 1])[0]:
        with st.form("settings_form"):
            st.subheader("Update Credentials")
            new_username = st.text_input("New Username", value=st.session_state.username)
            new_password = st.text_input("New Password (leave blank to keep current)", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Update Account"):
                if new_password and new_password != confirm_password: st.error("New passwords do not match.")
                elif st.session_state.username == 'admin' and new_username != 'admin': st.error("You cannot change the master admin username.")
                else:
                    if update_credentials(st.session_state.username, new_username, new_password):
                        st.success("Credentials updated! Please log in again.")
                        logout()
                    else: st.error("Username already taken.")

def render_main_menu():
    st.markdown("""
    <style>
    .stApp { background: url("https://github.com/RJA24/abra_sia_2026/blob/main/Abra%20(2).png?raw=true") !important; background-size: cover !important; background-position: center !important; background-attachment: fixed !important; }
    .main-title { text-align: center; font-size: 3.2rem; font-weight: 900; color: #0f172a; margin-top: 10px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 0px 2px 4px rgba(255,255,255,0.9), 0px 4px 15px rgba(255,255,255,0.7); }
    .kpi-container { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(10px); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.5); box-shadow: 0 8px 32px 0 rgba(0,0,0,0.1); text-align: center; margin-bottom: 30px; }
    .kpi-value { font-size: 2.5rem; font-weight: 800; color: #0f172a; margin: 0; }
    .kpi-label { font-size: 1rem; font-weight: 600; color: #475569; text-transform: uppercase; margin: 0; }
    </style>
    <div style='text-align: center; margin-bottom: 10px;'><img src="https://upload.wikimedia.org/wikipedia/commons/1/1a/Abra_provincial_seal.png?utm_source=commons.wikimedia.org&utm_campaign=index&utm_content=thumbnail_unscaled&_=20170706162937?raw=true" width="100" style="filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.3));"></div>
    <h1 class='main-title'>Abra Provincial Epidemiology<br>and Surveillance Unit</h1>
    """, unsafe_allow_html=True)
    
    # --- EXECUTIVE SUMMARY DATA FETCH ---
    with st.spinner("Compiling Provincial Health Summary..."):
        try:
            df_dengue = load_data()
            total_dengue = len(df_dengue)
            dengue_deaths = len(df_dengue[df_dengue["Outcome"] == "D"]) if "Outcome" in df_dengue.columns else 0
            
            df_tb = get_all_core_tb()
            total_tb_2026 = len(df_tb[df_tb['Year'] == 2026])
        except Exception:
            total_dengue, dengue_deaths, total_tb_2026 = 0, 0, 0
            
        active_users = len(get_users_df()[get_users_df()['status'] == 'approved']) + 1 # +1 for admin
    
    # --- KPI CARDS ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='kpi-container'><p class='kpi-label' style='color:#2563eb;'>Dengue Cases</p><p class='kpi-value'>{total_dengue:,}</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='kpi-container'><p class='kpi-label' style='color:#ef4444;'>Dengue Fatalities</p><p class='kpi-value'>{dengue_deaths:,}</p></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='kpi-container'><p class='kpi-label' style='color:#10b981;'>TB Cases (2026)</p><p class='kpi-value'>{total_tb_2026:,}</p></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='kpi-container'><p class='kpi-label' style='color:#8b5cf6;'>Active Personnel</p><p class='kpi-value'>{active_users}</p></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- NAVIGATION BUTTONS ---
    _, col1, col2, col3, _ = st.columns([1, 4, 4, 4, 1], gap="medium")
    with col1:
        st.markdown('<span class="big-btn-marker"></span>', unsafe_allow_html=True)
        if st.button("DENGUE SURVEILLANCE", use_container_width=True): st.session_state.active_program = 'dengue'; st.rerun()
    with col2:
        st.markdown('<span class="big-btn-marker"></span>', unsafe_allow_html=True)
        if st.button("TB CONTROL PROGRAM", use_container_width=True): st.session_state.active_program = 'tb'; st.rerun()
    with col3:
        st.markdown('<span class="big-btn-marker"></span>', unsafe_allow_html=True)
        st.button("HIV / NEXT PROGRAM", use_container_width=True)

# ==========================================
# MAIN ROUTING LOGIC
# ==========================================

def main():
    if not st.session_state.logged_in:
        render_register() if st.session_state.current_page == 'register' else render_login()
    else:
        profile_img_url = "https://github.com/RJA24/abra_dengue_cases/blob/main/dengue.png?raw=true" if st.session_state.active_program == 'dengue' else "https://github.com/RJA24/abra_sia_2026/blob/main/PHO%20logo.png?raw=true"

        with st.sidebar:
            st.markdown(f"""
            <div style="text-align: center; padding-bottom: 20px; border-bottom: 1px solid #e2e8f0; margin-bottom: 15px;">
                <img src="{profile_img_url}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: contain; margin-bottom: 10px; background-color: #f8fafc; padding: 5px; border: 1px solid #e2e8f0;">
                <h3 style="margin: 0; color: #0f172a; font-size: 1.2rem;">{st.session_state.username}</h3>
                <p style="margin: 0; color: #64748b; font-size: 0.9rem;">{st.session_state.role.title()}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.role == 'admin' and st.button("Admin Panel", icon=":material/build:", use_container_width=True): navigate('admin')
            if st.button("Profile & Settings", icon=":material/settings:", use_container_width=True): navigate('settings')
            if st.button("Sign out", icon=":material/logout:", use_container_width=True): logout()

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