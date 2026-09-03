# tests/test_cleaning.py
import pytest
from utils.cleaning import clean_muni_name, clean_brgy_name

def test_clean_muni_name():
    # Test 1: Exact standard match
    assert clean_muni_name("BANGUED") == "BANGUED"
    
    # Test 2: Fixing Excel encoding glitches
    assert clean_muni_name("PEÃ‘ARRUBIA") == "PEÑARRUBIA"
    assert clean_muni_name("PENARRUBIA") == "PEÑARRUBIA"
    
    # Test 3: Handling strict aliases
    assert clean_muni_name("LAPAZ") == "LA PAZ"
    assert clean_muni_name("SANISIDRO") == "SAN ISIDRO"
    
    # Test 4: Stripping "(CAPITAL)" annotations
    assert clean_muni_name("BANGUED (CAPITAL)") == "BANGUED"

def test_clean_brgy_name():
    # Test 1: Removing "BRGY" and "BARANGAY"
    assert clean_brgy_name("BRGY. ZONE 1") == "ZONE1"
    assert clean_brgy_name("BARANGAY POBLACION") == "POB"
    
    # Test 2: Removing parentheses and special characters
    assert clean_brgy_name("LUSONG (POB.)") == "LUSONGPOB"