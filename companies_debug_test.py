#!/usr/bin/env python3
"""
Additional Companies API Debug Test - Test without authentication to check CORS and access issues
"""

import requests
import json

BASE_URL = "https://stockbulkactions.preview.emergentagent.com/api"

def test_companies_without_auth():
    """Test companies API without authentication to check if that's the issue"""
    print("Testing companies API without authentication...")
    
    try:
        response = requests.get(f"{BASE_URL}/companies")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 401:
            print("✅ EXPECTED: API correctly requires authentication (401 Unauthorized)")
            return True
        elif response.status_code == 200:
            print("⚠️  WARNING: API allows access without authentication")
            companies = response.json()
            print(f"Retrieved {len(companies)} companies without auth")
            return True
        else:
            print(f"❌ UNEXPECTED: API returned {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def test_cors_preflight():
    """Test CORS preflight request"""
    print("\nTesting CORS preflight request...")
    
    try:
        # Simulate browser preflight request
        response = requests.options(
            f"{BASE_URL}/companies",
            headers={
                'Origin': 'https://stockbulkactions.preview.emergentagent.com',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'authorization,content-type'
            }
        )
        
        print(f"Preflight Status Code: {response.status_code}")
        print(f"CORS Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ CORS preflight successful")
            return True
        else:
            print(f"❌ CORS preflight failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ CORS ERROR: {str(e)}")
        return False

def test_with_invalid_auth():
    """Test with invalid authentication token"""
    print("\nTesting with invalid authentication token...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/companies",
            headers={'Authorization': 'Bearer invalid_token_12345'}
        )
        
        print(f"Invalid Auth Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ EXPECTED: API correctly rejects invalid token (401 Unauthorized)")
            return True
        else:
            print(f"❌ UNEXPECTED: API returned {response.status_code} for invalid token")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("COMPANIES API DEBUG - Authentication & CORS Testing")
    print("=" * 60)
    
    test_companies_without_auth()
    test_cors_preflight()
    test_with_invalid_auth()
    
    print("\n" + "=" * 60)
    print("If all tests show expected behavior, the issue is likely in the frontend")
    print("=" * 60)