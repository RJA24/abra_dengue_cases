# utils/geo.py
import json
import os
import requests
import numpy as np
import streamlit as st
from utils.constants import ALL_ABRA_MUNICIPALITIES
from utils.cleaning import clean_muni_name, clean_brgy_name

def get_muni_name_from_props(props):
    keys = ['ADM3_EN', 'MUN_NAME', 'NAME_3', 'MUNICIPALITY']
    upper_props = {str(k).upper(): str(v) for k, v in props.items()}
    
    for k in keys:
        if k in upper_props:
            std = clean_muni_name(upper_props[k])
            if std in ALL_ABRA_MUNICIPALITIES: 
                return std
            
    for val in props.values():
        std = clean_muni_name(str(val))
        if std in ALL_ABRA_MUNICIPALITIES: 
            return std
            
    return None

def extract_brgy_name(props):
    keys = ['ADM4_EN', 'BGY_NAME', 'BRGY_NAME', 'BARANGAY', 'NAME_4', 'NAME_3']
    upper_props = {str(k).upper(): v for k, v in props.items()}
    for k in keys:
        if k in upper_props: 
            return str(upper_props[k])
    for val in props.values():
        v_str = str(val).upper().strip()
        if v_str not in ["ABRA", "PHILIPPINES"] and clean_muni_name(v_str) not in ALL_ABRA_MUNICIPALITIES:
            if len(v_str) > 2: 
                return v_str
    return "UNKNOWN"

def get_polygon_centroid(geometry):
    try:
        coords = []
        if geometry['type'] == 'Polygon':
            for ring in geometry['coordinates']: 
                coords.extend(ring)
        elif geometry['type'] == 'MultiPolygon':
            for poly in geometry['coordinates']:
                for ring in poly: 
                    coords.extend(ring)
        if not coords: 
            return None, None
        coords = np.array(coords)
        return float(np.mean(coords[:, 0])), float(np.mean(coords[:, 1]))
    except: 
        return None, None

def apply_label_nudges(muni_name, lat, lon):
    name = str(muni_name).upper()
    if "BANGUED" in name: lat += 0.015
    elif "BUCAY" in name: lat -= 0.03; lon -= 0.015
    elif "LA PAZ" in name: lat -= 0.015
    elif "LAGANGILANG" in name: lat -= 0.015; lon += 0.02
    elif "LANGIDEN" in name: lat += 0.02; lon -= 0.02
    elif "MANABO" in name: lat -= 0.015; lon -= 0.015
    elif "PEÑARRUBIA" in name: lat -= 0.01; lon += 0.01
    elif "PILAR" in name: lat -= 0.015; lon -= 0.015
    elif "SALLAPADAN" in name: lat += 0.025; lon += 0.015
    elif "SAN ISIDRO" in name: lon -= 0.015
    elif "SAN JUAN" in name: lon += 0.015
    elif "TAYUM" in name: lat -= 0.015
    elif "TINEG" in name: lat -= 0.08; lon -= 0.030
    elif "TUBO" in name: lat += 0.08; lon += 0.015
    elif "VILLAVICIOSA" in name: lon += 0.015
    return float(lat), float(lon)

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
                if features: 
                    return {"type": "FeatureCollection", "features": features}
        except: 
            continue
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
            if features: 
                return {"type": "FeatureCollection", "features": features}, None
            return None, f"No barangays matched inside {target_muni}."
    except Exception as e: 
        return None, str(e)
