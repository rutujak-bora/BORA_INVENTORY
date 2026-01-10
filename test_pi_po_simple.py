"""
Simple integration tests for PI to PO Mapping using requests library
"""
import requests
import json

# Test configuration
BASE_URL = "https://stockbulkactions.preview.emergentagent.com/api"
AUTH_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2YWFkZmFiYi0xZDgzLTQ5NGYtODcyMi1hNGIwM2U2OTE4YzkiLCJleHAiOjE3NjQxNzYwNTJ9.eVJo7ZY8OiYEjzAoUkB9_QOYGEdhj5_-NHzZEQ2f3JI"

headers = {
    "Authorization": AUTH_TOKEN,
    "Content-Type": "application/json"
}

def test_list_mappings():
    """Test 1: List PI-PO mappings"""
    print("\\n🧪 Test 1: List PI-PO Mappings")
    response = requests.get(f"{BASE_URL}/pi-po-mapping?page=1&page_size=50", headers=headers)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    assert "data" in data, "Response missing 'data' field"
    assert "pagination" in data, "Response missing 'pagination' field"
    assert isinstance(data["data"], list), "data should be a list"
    
    print(f"   ✅ PASSED: Found {len(data['data'])} mappings")
    print(f"   📊 Total records: {data['pagination']['total_count']}")
    return data

def test_filter_by_consignee():
    """Test 2: Filter by consignee"""
    print("\\n🧪 Test 2: Filter by Consignee")
    response = requests.get(f"{BASE_URL}/pi-po-mapping?consignee=Test Consignee", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    for item in data["data"]:
        assert "test consignee" in item["consignee"].lower()
    
    print(f"   ✅ PASSED: Found {len(data['data'])} filtered results")
    return data

def test_get_detail():
    """Test 3: Get mapping detail"""
    print("\\n🧪 Test 3: Get Mapping Detail")
    
    # First get a list to find a valid ID
    list_response = requests.get(f"{BASE_URL}/pi-po-mapping?page=1&page_size=1", headers=headers)
    list_data = list_response.json()
    
    if len(list_data["data"]) == 0:
        print("   ⚠️ SKIPPED: No data available")
        return None
    
    mapping_id = list_data["data"][0]["id"]
    pi_number = list_data["data"][0]["pi_number"]
    
    # Get detail
    response = requests.get(f"{BASE_URL}/pi-po-mapping/{mapping_id}", headers=headers)
    
    assert response.status_code == 200
    detail = response.json()
    
    # Verify structure
    required_fields = ["id", "pi_number", "consignee", "pi_total_quantity", 
                       "total_po_quantity", "total_remaining_quantity", "pi_items", "linked_pos"]
    
    for field in required_fields:
        assert field in detail, f"Missing required field: {field}"
    
    print(f"   ✅ PASSED: Retrieved detail for {pi_number}")
    print(f"   📊 PI Qty: {detail['pi_total_quantity']}, PO Qty: {detail['total_po_quantity']}, Remaining: {detail['total_remaining_quantity']}")
    return detail

def test_remaining_calculation():
    """Test 4: Remaining quantity calculation"""
    print("\\n🧪 Test 4: Remaining Quantity Calculation")
    
    # Get a mapping with linked POs
    response = requests.get(f"{BASE_URL}/pi-po-mapping?page=1&page_size=10", headers=headers)
    data = response.json()["data"]
    
    # Find mapping with POs
    mapping_with_pos = next((item for item in data if item.get("linked_po_count", 0) > 0), None)
    
    if not mapping_with_pos:
        print("   ⚠️ SKIPPED: No mappings with linked POs")
        return
    
    # Get detail
    detail_response = requests.get(f"{BASE_URL}/pi-po-mapping/{mapping_with_pos['id']}", headers=headers)
    detail = detail_response.json()
    
    # Verify total calculation
    expected_remaining = detail["pi_total_quantity"] - detail["total_po_quantity"]
    assert detail["total_remaining_quantity"] == expected_remaining, \
        f"Remaining calculation error: Expected {expected_remaining}, got {detail['total_remaining_quantity']}"
    
    # Verify per-SKU calculations
    for pi_item in detail["pi_items"]:
        expected_remaining_sku = pi_item["pi_quantity"] - pi_item["total_po_quantity"]
        actual_remaining = pi_item["remaining_quantity"]
        
        assert actual_remaining == expected_remaining_sku, \
            f"SKU {pi_item['sku']}: Expected {expected_remaining_sku}, got {actual_remaining}"
        
        assert actual_remaining >= 0, f"Remaining quantity should not be negative for {pi_item['sku']}"
    
    print(f"   ✅ PASSED: All calculations correct")
    print(f"   📊 Verified {len(detail['pi_items'])} SKU calculations")

def test_search():
    """Test 5: Search functionality"""
    print("\\n🧪 Test 5: Search Functionality")
    
    response = requests.get(f"{BASE_URL}/pi-po-mapping?search=TEST", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    for item in data["data"]:
        found = "test" in item.get("pi_number", "").lower() or \
                "test" in item.get("consignee", "").lower()
        assert found, f"Search term not found in: {item.get('pi_number')}"
    
    print(f"   ✅ PASSED: Found {len(data['data'])} search results")

def test_pagination():
    """Test 6: Pagination"""
    print("\\n🧪 Test 6: Pagination")
    
    for page_size in [10, 25, 50]:
        response = requests.get(f"{BASE_URL}/pi-po-mapping?page=1&page_size={page_size}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) <= page_size
        assert data["pagination"]["page_size"] == page_size
    
    print(f"   ✅ PASSED: Pagination working correctly")

def test_update_metadata():
    """Test 7: Update mapping metadata"""
    print("\\n🧪 Test 7: Update Mapping Metadata")
    
    # Get a valid ID
    list_response = requests.get(f"{BASE_URL}/pi-po-mapping?page=1&page_size=1", headers=headers)
    list_data = list_response.json()
    
    if len(list_data["data"]) == 0:
        print("   ⚠️ SKIPPED: No data available")
        return
    
    mapping_id = list_data["data"][0]["id"]
    
    # Update metadata
    response = requests.put(
        f"{BASE_URL}/pi-po-mapping/{mapping_id}?notes=Test+note&status=In+Progress",
        headers=headers
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert "message" in result
    assert result["id"] == mapping_id
    
    print(f"   ✅ PASSED: Metadata updated successfully")

def test_invalid_id():
    """Test 8: Invalid mapping ID"""
    print("\\n🧪 Test 8: Invalid Mapping ID")
    
    response = requests.get(f"{BASE_URL}/pi-po-mapping/invalid-id-12345", headers=headers)
    
    assert response.status_code == 404
    
    print(f"   ✅ PASSED: Returns 404 for invalid ID")

def run_all_tests():
    """Run all tests"""
    print("\\n" + "="*70)
    print("PI → PO MAPPING - INTEGRATION TESTS")
    print("="*70)
    
    tests = [
        test_list_mappings,
        test_filter_by_consignee,
        test_get_detail,
        test_remaining_calculation,
        test_search,
        test_pagination,
        test_update_metadata,
        test_invalid_id,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"   ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"   ⚠️ ERROR: {e}")
            failed += 1
    
    print("\\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*70 + "\\n")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
