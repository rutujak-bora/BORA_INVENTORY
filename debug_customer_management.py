#!/usr/bin/env python3
"""
Debug Customer Management PI-PO Mapping Issue
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
        print(f"✅ Authenticated as {user_creds['username']}")
        return session
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        return None

def debug_customer_management():
    """Debug customer management PI-PO mapping"""
    session = authenticate()
    if not session:
        return
    
    print("\n🔍 DEBUGGING CUSTOMER MANAGEMENT PI-PO MAPPING")
    print("=" * 60)
    
    # Get all PIs
    print("\n1. Getting all PIs...")
    pi_response = session.get(f"{BASE_URL}/pi")
    if pi_response.status_code == 200:
        pis = pi_response.json()
        print(f"   Found {len(pis)} PIs")
        
        # Show recent PIs
        recent_pis = [pi for pi in pis if "TEST-MULTI-PI" in pi.get("voucher_no", "")][-3:]
        for pi in recent_pis:
            print(f"   - PI: {pi.get('voucher_no')} (ID: {pi.get('id')})")
    else:
        print(f"   ❌ Failed to get PIs: {pi_response.status_code}")
        return
    
    # Get all POs
    print("\n2. Getting all POs...")
    po_response = session.get(f"{BASE_URL}/po")
    if po_response.status_code == 200:
        pos = po_response.json()
        print(f"   Found {len(pos)} POs")
        
        # Show recent POs with PI references
        recent_pos = [po for po in pos if po.get("voucher_no") and "TEST-PO" in po.get("voucher_no", "")][-5:]
        for po in recent_pos:
            print(f"   - PO: {po.get('voucher_no')} (ID: {po.get('id')})")
            print(f"     reference_pi_id: {po.get('reference_pi_id')}")
            print(f"     reference_pi_ids: {po.get('reference_pi_ids')}")
    else:
        print(f"   ❌ Failed to get POs: {po_response.status_code}")
        return
    
    # Get PI-PO mappings
    print("\n3. Getting PI-PO mappings...")
    mapping_response = session.get(f"{BASE_URL}/customer-management/pi-po-mapping")
    if mapping_response.status_code == 200:
        mappings = mapping_response.json()
        print(f"   Found {len(mappings)} PI-PO mappings")
        
        # Show test mappings
        test_mappings = [m for m in mappings if "TEST-MULTI-PI" in m.get("pi_number", "")]
        print(f"   Test mappings found: {len(test_mappings)}")
        
        for mapping in test_mappings:
            print(f"   - PI: {mapping.get('pi_number')} (ID: {mapping.get('pi_id')})")
            print(f"     Linked POs: {len(mapping.get('linked_pos', []))}")
            for po in mapping.get('linked_pos', []):
                print(f"       - PO: {po.get('po_number')} (ID: {po.get('po_id')})")
    else:
        print(f"   ❌ Failed to get PI-PO mappings: {mapping_response.status_code}")
        print(f"   Response: {mapping_response.text}")
        return
    
    # Check specific PI mapping
    if recent_pis:
        test_pi_id = recent_pis[0].get('id')
        print(f"\n4. Checking specific PI mapping for PI ID: {test_pi_id}")
        
        # Find POs that should link to this PI
        matching_pos = []
        for po in pos:
            if (po.get('reference_pi_id') == test_pi_id or 
                test_pi_id in po.get('reference_pi_ids', [])):
                matching_pos.append(po)
        
        print(f"   POs that should link to this PI: {len(matching_pos)}")
        for po in matching_pos:
            print(f"   - PO: {po.get('voucher_no')} (reference_pi_ids: {po.get('reference_pi_ids')})")
        
        # Check if this PI appears in mappings
        pi_in_mappings = False
        for mapping in mappings:
            if mapping.get('pi_id') == test_pi_id:
                pi_in_mappings = True
                print(f"   ✅ PI found in mappings with {len(mapping.get('linked_pos', []))} linked POs")
                break
        
        if not pi_in_mappings:
            print(f"   ❌ PI NOT found in mappings - this indicates the query issue")

if __name__ == "__main__":
    debug_customer_management()