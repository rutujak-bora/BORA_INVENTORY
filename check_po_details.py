#!/usr/bin/env python3
"""
Check PO Details
"""

import requests
import json

# Configuration
BASE_URL = "https://stockbulkactions.preview.emergentagent.com/api"

# Test credentials
TEST_USERS = {
    "all_companies": {
        "username": "rutuja@bora.tech",
        "password": "rutuja@123"
    }
}

def authenticate():
    """Authenticate and get token"""
    session = requests.Session()
    user_creds = TEST_USERS["all_companies"]
    response = session.post(
        f"{BASE_URL}/auth/login",
        json=user_creds,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        auth_token = data.get("access_token")
        session.headers.update({
            "Authorization": f"Bearer {auth_token}"
        })
        return session
    else:
        return None

def check_po_details():
    """Check PO details"""
    session = authenticate()
    if not session:
        return
    
    # Get specific PO
    po_id = "fc629606-1f4e-4dbf-a827-79c341398d13"
    response = session.get(f"{BASE_URL}/po/{po_id}")
    
    if response.status_code == 200:
        po = response.json()
        print("PO Details:")
        print(f"  ID: {po.get('id')}")
        print(f"  voucher_no: {po.get('voucher_no')}")
        print(f"  reference_pi_id: {po.get('reference_pi_id')}")
        print(f"  reference_pi_ids: {po.get('reference_pi_ids')}")
        print(f"  All fields: {list(po.keys())}")
    else:
        print(f"Failed to get PO: {response.status_code}")

if __name__ == "__main__":
    check_po_details()