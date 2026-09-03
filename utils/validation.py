# utils/validation.py
import pandas as pd
from utils.constants import ALL_ABRA_MUNICIPALITIES

def validate_dataset(df, report_type):
    report = {
        "total_records": len(df),
        "missing_muncity": 0,
        "invalid_muncity": 0,
        "missing_dates": 0,
        "duplicates": 0,
        "score": 100.0,
        "warnings": []
    }
    
    if df.empty:
        report["score"] = 0.0
        report["warnings"].append("Dataset is completely empty.")
        return report
        
    # 1. Check Municipalities
    muni_col = 'Muncity' if 'Muncity' in df.columns else ('City/Municipality' if 'City/Municipality' in df.columns else None)
    if muni_col:
        # Count genuinely missing cells
        missing_muni = df[muni_col].isna() | (df[muni_col].astype(str).str.strip() == '')
        report["missing_muncity"] = int(missing_muni.sum())
        
        # Check for typos or out-of-province data
        valid_munis = [m.upper() for m in ALL_ABRA_MUNICIPALITIES]
        invalid_muni = df[~missing_muni][muni_col].astype(str).str.upper().apply(
            lambda x: not any(m in x.replace("Ñ", "N") for m in valid_munis)
        )
        report["invalid_muncity"] = int(invalid_muni.sum())
    else:
        report["warnings"].append("Could not find a Municipality column to validate.")

    # 2. Check Dates & Duplicates based on Program
    if report_type == "Dengue Cases":
        if 'DOnset' in df.columns:
            report["missing_dates"] = int(df['DOnset'].isna().sum())
        if 'PatientNumber' in df.columns:
            report["duplicates"] = int(df.duplicated(subset=['PatientNumber']).sum())
            
    elif report_type in ["DSTB", "DRTB", "2026 MN", "TPT", "HIV"]:
        if 'Date of Diagnosis' in df.columns:
            report["missing_dates"] = int(df['Date of Diagnosis'].isna().sum())
        if 'TB/TPT Case No.' in df.columns:
            report["duplicates"] = int(df.duplicated(subset=['TB/TPT Case No.']).sum())
            
    # 3. Calculate Overall Score
    total_errors = report["missing_muncity"] + report["invalid_muncity"] + report["missing_dates"] + report["duplicates"]
    if report["total_records"] > 0:
        penalty = (total_errors / report["total_records"]) * 100
        report["score"] = max(0.0, round(100.0 - penalty, 1))
        
    # 4. Generate Readable Warnings
    if report["missing_muncity"] > 0: 
        report["warnings"].append(f"Missing Municipality: {report['missing_muncity']} records")
    if report["invalid_muncity"] > 0: 
        report["warnings"].append(f"Unrecognized/Outside Municipality: {report['invalid_muncity']} records")
    if report["missing_dates"] > 0: 
        report["warnings"].append(f"Missing Key Dates (Onset/Diagnosis): {report['missing_dates']} records")
    if report["duplicates"] > 0: 
        report["warnings"].append(f"Duplicate Patient/Case IDs: {report['duplicates']} records")
    
    return report