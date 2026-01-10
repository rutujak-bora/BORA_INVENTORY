"""
Unit tests for PI to PO Mapping API endpoints
"""
import asyncio
import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from server import app

client = TestClient(app)

# MongoDB connection for test data
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "bora_inventory_mongo"

# Mock auth token (replace with actual test user token)
AUTH_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2YWFkZmFiYi0xZDgzLTQ5NGYtODcyMi1hNGIwM2U2OTE4YzkiLCJleHAiOjE3NjQxNzYwNTJ9.eVJo7ZY8OiYEjzAoUkB9_QOYGEdhj5_-NHzZEQ2f3JI"

def get_headers():
    """Get auth headers for API requests"""
    return {"Authorization": AUTH_TOKEN}

class TestPIPOMapping:
    """Test suite for PI to PO Mapping functionality"""
    
    def test_list_pi_po_mappings(self):
        """Test GET /api/pi-po-mapping - List all mappings"""
        response = client.get(
            "/api/pi-po-mapping?page=1&page_size=50",
            headers=get_headers()
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        
        # Verify pagination structure
        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_count" in pagination
        assert "total_pages" in pagination
        
        print(f"✅ List test passed: Found {len(data['data'])} mappings")
    
    def test_list_with_filters(self):
        """Test filtering by consignee"""
        response = client.get(
            "/api/pi-po-mapping?consignee=Test Consignee",
            headers=get_headers()
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify filtered results contain the search term
        for item in data["data"]:
            assert "consignee" in item
            # Case-insensitive search
            assert "test consignee" in item["consignee"].lower()
        
        print(f"✅ Filter test passed: Found {len(data['data'])} filtered results")
    
    def test_get_pi_po_detail(self):
        """Test GET /api/pi-po-mapping/{mapping_id} - Get single mapping detail"""
        # First, get a list to find a valid ID
        list_response = client.get(
            "/api/pi-po-mapping?page=1&page_size=1",
            headers=get_headers()
        )
        
        assert list_response.status_code == 200
        list_data = list_response.json()
        
        if len(list_data["data"]) == 0:
            print("⚠️ No data to test detail endpoint")
            return
        
        # Get the first mapping ID
        mapping_id = list_data["data"][0]["id"]
        
        # Test detail endpoint
        detail_response = client.get(
            f"/api/pi-po-mapping/{mapping_id}",
            headers=get_headers()
        )
        
        assert detail_response.status_code == 200
        detail = detail_response.json()
        
        # Verify detail structure
        assert "id" in detail
        assert "pi_number" in detail
        assert "consignee" in detail
        assert "pi_total_quantity" in detail
        assert "total_po_quantity" in detail
        assert "total_remaining_quantity" in detail
        assert "pi_items" in detail
        assert "linked_pos" in detail
        
        # Verify PI items structure
        if len(detail["pi_items"]) > 0:
            pi_item = detail["pi_items"][0]
            assert "sku" in pi_item
            assert "product_name" in pi_item
            assert "pi_quantity" in pi_item
            assert "pi_rate" in pi_item
            assert "total_po_quantity" in pi_item
            assert "remaining_quantity" in pi_item
        
        print(f"✅ Detail test passed for mapping: {detail['pi_number']}")
    
    def test_update_pi_po_metadata(self):
        """Test PUT /api/pi-po-mapping/{mapping_id} - Update metadata"""
        # Get a valid mapping ID
        list_response = client.get(
            "/api/pi-po-mapping?page=1&page_size=1",
            headers=get_headers()
        )
        
        if len(list_response.json()["data"]) == 0:
            print("⚠️ No data to test update endpoint")
            return
        
        mapping_id = list_response.json()["data"][0]["id"]
        
        # Update metadata
        update_response = client.put(
            f"/api/pi-po-mapping/{mapping_id}",
            params={"notes": "Test note", "status": "In Progress"},
            headers=get_headers()
        )
        
        assert update_response.status_code == 200
        result = update_response.json()
        assert "message" in result
        assert result["id"] == mapping_id
        
        print(f"✅ Update test passed for mapping: {mapping_id}")
    
    def test_remaining_quantity_calculation(self):
        """Test remaining quantity calculation logic"""
        # Get detail for a mapping with linked POs
        list_response = client.get(
            "/api/pi-po-mapping?page=1&page_size=10",
            headers=get_headers()
        )
        
        data = list_response.json()["data"]
        
        # Find a mapping with linked POs
        mapping_with_pos = None
        for item in data:
            if item.get("linked_po_count", 0) > 0:
                mapping_with_pos = item
                break
        
        if not mapping_with_pos:
            print("⚠️ No mappings with linked POs found")
            return
        
        # Get detail
        detail_response = client.get(
            f"/api/pi-po-mapping/{mapping_with_pos['id']}",
            headers=get_headers()
        )
        
        detail = detail_response.json()
        
        # Verify calculation: PI Total - Total PO = Remaining
        expected_remaining = detail["pi_total_quantity"] - detail["total_po_quantity"]
        assert detail["total_remaining_quantity"] == expected_remaining
        
        # Verify per-SKU calculations
        for pi_item in detail["pi_items"]:
            expected_remaining_sku = pi_item["pi_quantity"] - pi_item["total_po_quantity"]
            assert pi_item["remaining_quantity"] == expected_remaining_sku
            # Remaining should not be negative
            assert pi_item["remaining_quantity"] >= 0
        
        print(f"✅ Remaining quantity calculation test passed")
    
    def test_pagination(self):
        """Test pagination functionality"""
        # Test different page sizes
        for page_size in [10, 25, 50]:
            response = client.get(
                f"/api/pi-po-mapping?page=1&page_size={page_size}",
                headers=get_headers()
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify page size is respected
            assert len(data["data"]) <= page_size
            assert data["pagination"]["page_size"] == page_size
        
        print(f"✅ Pagination test passed")
    
    def test_search_functionality(self):
        """Test global search across multiple fields"""
        response = client.get(
            "/api/pi-po-mapping?search=TEST",
            headers=get_headers()
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All results should contain "TEST" in some field
        for item in data["data"]:
            found = (
                "test" in item.get("pi_number", "").lower() or
                "test" in item.get("consignee", "").lower()
            )
            assert found, f"Search term not found in result: {item}"
        
        print(f"✅ Search test passed: Found {len(data['data'])} results")
    
    def test_date_range_filter(self):
        """Test date range filtering"""
        response = client.get(
            "/api/pi-po-mapping?from_date=2025-11-01&to_date=2025-11-30",
            headers=get_headers()
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify dates are within range
        from datetime import datetime
        for item in data["data"]:
            if item.get("pi_date"):
                pi_date = datetime.fromisoformat(item["pi_date"].replace("Z", "+00:00"))
                assert datetime(2025, 11, 1) <= pi_date <= datetime(2025, 11, 30)
        
        print(f"✅ Date range filter test passed")
    
    def test_invalid_mapping_id(self):
        """Test getting detail for non-existent mapping"""
        response = client.get(
            "/api/pi-po-mapping/invalid-id-12345",
            headers=get_headers()
        )
        
        assert response.status_code == 404
        assert "detail" in response.json()
        
        print(f"✅ Invalid ID test passed: Returns 404")

def run_tests():
    """Run all tests"""
    print("\\n" + "="*60)
    print("Running PI → PO Mapping Unit Tests")
    print("="*60 + "\\n")
    
    test_suite = TestPIPOMapping()
    
    tests = [
        ("List PI-PO Mappings", test_suite.test_list_pi_po_mappings),
        ("Filter by Consignee", test_suite.test_list_with_filters),
        ("Get Mapping Detail", test_suite.test_get_pi_po_detail),
        ("Update Metadata", test_suite.test_update_pi_po_metadata),
        ("Remaining Qty Calculation", test_suite.test_remaining_quantity_calculation),
        ("Pagination", test_suite.test_pagination),
        ("Search Functionality", test_suite.test_search_functionality),
        ("Date Range Filter", test_suite.test_date_range_filter),
        ("Invalid Mapping ID", test_suite.test_invalid_mapping_id),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\\n🧪 Running: {test_name}")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {test_name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️ ERROR: {test_name}")
            print(f"   Error: {e}")
            failed += 1
    
    print("\\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60 + "\\n")
    
    return passed, failed

if __name__ == "__main__":
    passed, failed = run_tests()
    sys.exit(0 if failed == 0 else 1)
