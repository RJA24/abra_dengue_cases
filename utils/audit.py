# utils/audit.py
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from utils.constants import SHEET_URL
from datetime import datetime
import pytz

def log_action(username, action, details):
    """
    Silently writes an audit trail to the 'Audit_Log' Google Sheet.
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Get accurate Philippine time
        tz = pytz.timezone('Asia/Manila')
        timestamp = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        
        new_log = pd.DataFrame({
            "Timestamp": [timestamp],
            "User": [username],
            "Action": [action],
            "Details": [details]
        })
        
        # Fetch existing logs to append (ttl=0 ensures we don't grab a cached version)
        try:
            existing_logs = conn.read(spreadsheet=SHEET_URL, worksheet="Audit_Log", ttl=0)
            existing_logs = existing_logs.dropna(how='all') # Clean empty rows
            updated_logs = pd.concat([existing_logs, new_log], ignore_index=True)
        except Exception:
            # If the sheet is completely blank or errors out, just push the new log
            updated_logs = new_log
            
        conn.update(spreadsheet=SHEET_URL, worksheet="Audit_Log", data=updated_logs)
    except Exception as e:
        # We use a print statement here instead of st.error so that if the audit log fails, 
        # it doesn't crash the user's main workflow.
        print(f"Audit log push failed: {e}")