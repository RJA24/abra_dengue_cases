# utils/cleaning.py
import re
import unicodedata
from utils.constants import ALL_ABRA_MUNICIPALITIES

def clean_muni_name(raw_name):
    if not isinstance(raw_name, str): 
        return ""
    raw = str(raw_name).upper()
    
    # Intercept Excel encoding glitches
    raw = raw.replace("Ã‘", "N").replace("Ñ", "N")
    raw = unicodedata.normalize('NFKD', raw).encode('ASCII', 'ignore').decode('utf-8')
    raw = raw.replace("(CAPITAL)", "").replace("CAPITAL", "").strip()
    
    raw_alpha = re.sub(r'[^A-Z]', '', raw)
    
    for muni in ALL_ABRA_MUNICIPALITIES:
        if raw_alpha == re.sub(r'[^A-Z]', '', muni.replace("Ñ", "N")):
            return muni
            
    if raw_alpha in ["LICUANBAAY", "LICUAN", "BAAY"]: return "LICUAN-BAAY"
    if raw_alpha in ["PENARRUBIA", "PENARUBIA", "PEAARRUBIA", "PENAR", "RUBIA", "PEÃ‘ARRUBIA"]: return "PEÑARRUBIA"
    if raw_alpha in ["LAPAZ", "PAZ"]: return "LA PAZ"
    if raw_alpha in ["SANJUAN", "JUAN"]: return "SAN JUAN"
    if raw_alpha in ["SANISIDRO", "ISIDRO"]: return "SAN ISIDRO"
    if raw_alpha in ["SANQUINTIN", "QUINTIN"]: return "SAN QUINTIN"
    
    return raw_name

def clean_brgy_name(raw_name):
    if not isinstance(raw_name, str): 
        return ""
    raw = str(raw_name).upper()
    raw = unicodedata.normalize('NFKD', raw).encode('ASCII', 'ignore').decode('utf-8')
    raw = re.sub(r'\(.*?\)', '', raw) 
    raw = raw.replace("BARANGAY", "").replace("BRGY", "").replace("POBLACION", "POB").replace("POB.", "POB")
    return re.sub(r'[^A-Z0-9]', '', raw)
