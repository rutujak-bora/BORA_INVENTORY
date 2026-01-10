#!/usr/bin/env python3
"""
PO Multiple PIs Backend Support Testing
Comprehensive testing for the newly implemented PO Multiple PIs Backend Support feature
"""

import requests
import json
import uuid
from datetime import datetime
import os

# Configuration
BASE_URL = "https://stockbulkactions.preview.emergentagent.com/api"

# Test credentials
TEST_USERS = {
    "all_companies": {
        "username": "rutuja@bora.tech",
        "password": "rutuja@123"
    }
}

class POMultiplePIsTestSuite:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_data = {
            "company_id": None,
            "product_id": None,
            "product_id_2": None,
            "warehouse_id": None,
            "pi_id_1": None,
            "pi_id_2": None,
            "pi_id_3": None,
            "po_single_pi_id": None,
            "po_multiple_pis_id": None,
            "inward_id": None
        }
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def authenticate(self, user_type="all_companies"):
        """Test authentication"""
        try:
            user_creds = TEST_USERS[user_type]
            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json=user_creds,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                self.log_result(
                    f"Authentication ({user_type})", 
                    True, 
                    f"Successfully authenticated as {user_creds['username']}"
                )
                return True
            else:
                self.log_result(
                    f"Authentication ({user_type})", 
                    False, 
                    f"Failed to authenticate: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                f"Authentication ({user_type})", 
                False, 
                f"Authentication error: {str(e)}"
            )
            return False
    
    def setup_test_data(self):
        """Create test companies, products, warehouses, and PIs for testing"""
        success = True
        
        # Create test company
        try:
            company_data = {
                "name": "Test Company for PO Multiple PIs",
                "gstn": "27TESTMULTI9603R1ZV",
                "address": "123 Multiple PI Street, Mumbai",
                "contact_details": "+91-9876543210",
                "country": "India",
                "city": "Mumbai"
            }
            
            response = self.session.post(
                f"{BASE_URL}/companies",
                json=company_data
            )
            
            if response.status_code == 200:
                company = response.json()
                self.test_data["company_id"] = company["id"]
                self.log_result(
                    "Setup Test Company", 
                    True, 
                    f"Created test company: {company['name']}"
                )
            else:
                self.log_result(
                    "Setup Test Company", 
                    False, 
                    f"Failed to create company: {response.status_code}",
                    {"response": response.text}
                )
                success = False
                
        except Exception as e:
            self.log_result(
                "Setup Test Company", 
                False, 
                f"Error creating company: {str(e)}"
            )
            success = False
        
        # Create test products
        try:
            product_data_1 = {
                "sku_name": "TEST-MULTI-PI-SKU-001",
                "category": "Test Electronics",
                "brand": "TestBrand",
                "hsn_sac": "8517",
                "country_of_origin": "India",
                "unit_of_measure": "pcs",
                "default_rate": 2500.00
            }
            
            response = self.session.post(
                f"{BASE_URL}/products",
                json=product_data_1
            )
            
            if response.status_code == 200:
                product = response.json()
                self.test_data["product_id"] = product["id"]
                self.log_result(
                    "Setup Test Product 1", 
                    True, 
                    f"Created test product: {product['sku_name']}"
                )
            else:
                self.log_result(
                    "Setup Test Product 1", 
                    False, 
                    f"Failed to create product: {response.status_code}",
                    {"response": response.text}
                )
                success = False
            
            # Create second product
            product_data_2 = {
                "sku_name": "TEST-MULTI-PI-SKU-002",
                "category": "Test Accessories",
                "brand": "TestBrand2",
                "hsn_sac": "8543",
                "country_of_origin": "India",
                "unit_of_measure": "box",
                "default_rate": 1800.00
            }
            
            response = self.session.post(
                f"{BASE_URL}/products",
                json=product_data_2
            )
            
            if response.status_code == 200:
                product = response.json()
                self.test_data["product_id_2"] = product["id"]
                self.log_result(
                    "Setup Test Product 2", 
                    True, 
                    f"Created test product: {product['sku_name']}"
                )
            else:
                self.log_result(
                    "Setup Test Product 2", 
                    False, 
                    f"Failed to create product 2: {response.status_code}",
                    {"response": response.text}
                )
                success = False
                
        except Exception as e:
            self.log_result(
                "Setup Test Products", 
                False, 
                f"Error creating products: {str(e)}"
            )
            success = False
        
        # Create test warehouse
        try:
            warehouse_data = {
                "name": "Test Warehouse for Multiple PIs",
                "address": "123 Warehouse Street, Mumbai",
                "city": "Mumbai",
                "country": "India",
                "contact_details": "+91-9876543211"
            }
            
            response = self.session.post(
                f"{BASE_URL}/warehouses",
                json=warehouse_data
            )
            
            if response.status_code == 200:
                warehouse = response.json()
                self.test_data["warehouse_id"] = warehouse["id"]
                self.log_result(
                    "Setup Test Warehouse", 
                    True, 
                    f"Created test warehouse: {warehouse['name']}"
                )
            else:
                self.log_result(
                    "Setup Test Warehouse", 
                    False, 
                    f"Failed to create warehouse: {response.status_code}",
                    {"response": response.text}
                )
                success = False
                
        except Exception as e:
            self.log_result(
                "Setup Test Warehouse", 
                False, 
                f"Error creating warehouse: {str(e)}"
            )
            success = False
        
        # Create multiple test PIs
        try:
            # PI 1
            pi_data_1 = {
                "company_id": self.test_data["company_id"],
                "voucher_no": f"TEST-MULTI-PI-1-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "consignee": "Test Consignee 1",
                "buyer": "Test Buyer 1",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Test Product 1 for Multiple PIs",
                        "sku": "TEST-MULTI-PI-SKU-001",
                        "category": "Test Electronics",
                        "brand": "TestBrand",
                        "hsn_sac": "8517",
                        "made_in": "India",
                        "quantity": 50,
                        "rate": 2500.00
                    }
                ]
            }
            
            response = self.session.post(
                f"{BASE_URL}/pi",
                json=pi_data_1
            )
            
            if response.status_code == 200:
                pi = response.json()
                self.test_data["pi_id_1"] = pi["id"]
                self.log_result(
                    "Setup Test PI 1", 
                    True, 
                    f"Created test PI 1: {pi['voucher_no']}"
                )
            else:
                self.log_result(
                    "Setup Test PI 1", 
                    False, 
                    f"Failed to create PI 1: {response.status_code}",
                    {"response": response.text}
                )
                success = False
            
            # PI 2
            pi_data_2 = {
                "company_id": self.test_data["company_id"],
                "voucher_no": f"TEST-MULTI-PI-2-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "consignee": "Test Consignee 2",
                "buyer": "Test Buyer 2",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id_2"],
                        "product_name": "Test Product 2 for Multiple PIs",
                        "sku": "TEST-MULTI-PI-SKU-002",
                        "category": "Test Accessories",
                        "brand": "TestBrand2",
                        "hsn_sac": "8543",
                        "made_in": "India",
                        "quantity": 30,
                        "rate": 1800.00
                    }
                ]
            }
            
            response = self.session.post(
                f"{BASE_URL}/pi",
                json=pi_data_2
            )
            
            if response.status_code == 200:
                pi = response.json()
                self.test_data["pi_id_2"] = pi["id"]
                self.log_result(
                    "Setup Test PI 2", 
                    True, 
                    f"Created test PI 2: {pi['voucher_no']}"
                )
            else:
                self.log_result(
                    "Setup Test PI 2", 
                    False, 
                    f"Failed to create PI 2: {response.status_code}",
                    {"response": response.text}
                )
                success = False
            
            # PI 3
            pi_data_3 = {
                "company_id": self.test_data["company_id"],
                "voucher_no": f"TEST-MULTI-PI-3-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "consignee": "Test Consignee 3",
                "buyer": "Test Buyer 3",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Test Product 3 for Multiple PIs",
                        "sku": "TEST-MULTI-PI-SKU-001",
                        "category": "Test Electronics",
                        "brand": "TestBrand",
                        "hsn_sac": "8517",
                        "made_in": "India",
                        "quantity": 25,
                        "rate": 2500.00
                    }
                ]
            }
            
            response = self.session.post(
                f"{BASE_URL}/pi",
                json=pi_data_3
            )
            
            if response.status_code == 200:
                pi = response.json()
                self.test_data["pi_id_3"] = pi["id"]
                self.log_result(
                    "Setup Test PI 3", 
                    True, 
                    f"Created test PI 3: {pi['voucher_no']}"
                )
            else:
                self.log_result(
                    "Setup Test PI 3", 
                    False, 
                    f"Failed to create PI 3: {response.status_code}",
                    {"response": response.text}
                )
                success = False
                
        except Exception as e:
            self.log_result(
                "Setup Test PIs", 
                False, 
                f"Error creating PIs: {str(e)}"
            )
            success = False
        
        return success
    
    # ==================== PO CREATION TESTS ====================
    
    def test_po_creation_single_pi_backward_compatibility(self):
        """Test 1: PO Creation with Single PI (Backward Compatibility)"""
        try:
            po_data = {
                "company_id": self.test_data["company_id"],
                "voucher_no": f"TEST-PO-SINGLE-PI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "consignee": "Test Consignee Single PI",
                "supplier": "Test Supplier Single PI",
                "reference_pi_id": self.test_data["pi_id_1"],  # Old format - single PI
                "reference_no_date": f"PI-REF-SINGLE | {datetime.now().strftime('%Y-%m-%d')}",
                "dispatched_through": "Test Logistics",
                "destination": "Mumbai Port",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Test Product Single PI",
                        "sku": "TEST-MULTI-PI-SKU-001",
                        "category": "Test Electronics",
                        "brand": "TestBrand",
                        "hsn_sac": "8517",
                        "quantity": 20,
                        "rate": 2500.00,
                        "input_igst": 450.00,
                        "tds": 25.00
                    }
                ]
            }
            
            response = self.session.post(
                f"{BASE_URL}/po",
                json=po_data
            )
            
            if response.status_code == 200:
                po = response.json()
                self.test_data["po_single_pi_id"] = po["id"]
                
                # Verify backward compatibility fields
                if po.get("reference_pi_id") != self.test_data["pi_id_1"]:
                    self.log_result(
                        "PO Creation Single PI (Backward Compatibility)", 
                        False, 
                        f"reference_pi_id not set correctly: {po.get('reference_pi_id')} != {self.test_data['pi_id_1']}"
                    )
                    return False
                
                # Verify new field is populated
                if not po.get("reference_pi_ids") or len(po.get("reference_pi_ids", [])) != 1:
                    self.log_result(
                        "PO Creation Single PI (Backward Compatibility)", 
                        False, 
                        f"reference_pi_ids not populated correctly: {po.get('reference_pi_ids')}"
                    )
                    return False
                
                if po.get("reference_pi_ids")[0] != self.test_data["pi_id_1"]:
                    self.log_result(
                        "PO Creation Single PI (Backward Compatibility)", 
                        False, 
                        f"reference_pi_ids[0] not matching reference_pi_id: {po.get('reference_pi_ids')[0]} != {self.test_data['pi_id_1']}"
                    )
                    return False
                
                self.log_result(
                    "PO Creation Single PI (Backward Compatibility)", 
                    True, 
                    f"Successfully created PO with single PI - reference_pi_id: {po.get('reference_pi_id')}, reference_pi_ids: {po.get('reference_pi_ids')}"
                )
                return True
            else:
                self.log_result(
                    "PO Creation Single PI (Backward Compatibility)", 
                    False, 
                    f"Failed to create PO with single PI: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "PO Creation Single PI (Backward Compatibility)", 
                False, 
                f"Error creating PO with single PI: {str(e)}"
            )
            return False
    
    def test_po_creation_multiple_pis(self):
        """Test 2: PO Creation with Multiple PIs (New Feature)"""
        try:
            po_data = {
                "company_id": self.test_data["company_id"],
                "voucher_no": f"TEST-PO-MULTI-PI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "consignee": "Test Consignee Multiple PIs",
                "supplier": "Test Supplier Multiple PIs",
                "reference_pi_ids": [  # New format - multiple PIs
                    self.test_data["pi_id_1"],
                    self.test_data["pi_id_2"],
                    self.test_data["pi_id_3"]
                ],
                "reference_no_date": f"PI-REF-MULTI | {datetime.now().strftime('%Y-%m-%d')}",
                "dispatched_through": "Test Logistics Multi",
                "destination": "Mumbai Port",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Test Product Multi PI 1",
                        "sku": "TEST-MULTI-PI-SKU-001",
                        "category": "Test Electronics",
                        "brand": "TestBrand",
                        "hsn_sac": "8517",
                        "quantity": 15,
                        "rate": 2500.00,
                        "input_igst": 337.50,
                        "tds": 18.75
                    },
                    {
                        "product_id": self.test_data["product_id_2"],
                        "product_name": "Test Product Multi PI 2",
                        "sku": "TEST-MULTI-PI-SKU-002",
                        "category": "Test Accessories",
                        "brand": "TestBrand2",
                        "hsn_sac": "8543",
                        "quantity": 10,
                        "rate": 1800.00,
                        "input_igst": 324.00,
                        "tds": 18.00
                    }
                ]
            }
            
            response = self.session.post(
                f"{BASE_URL}/po",
                json=po_data
            )
            
            if response.status_code == 200:
                po = response.json()
                self.test_data["po_multiple_pis_id"] = po["id"]
                
                # Verify multiple PI IDs are stored
                if not po.get("reference_pi_ids") or len(po.get("reference_pi_ids", [])) != 3:
                    self.log_result(
                        "PO Creation Multiple PIs", 
                        False, 
                        f"reference_pi_ids not populated correctly: {po.get('reference_pi_ids')}"
                    )
                    return False
                
                expected_pi_ids = [self.test_data["pi_id_1"], self.test_data["pi_id_2"], self.test_data["pi_id_3"]]
                if set(po.get("reference_pi_ids")) != set(expected_pi_ids):
                    self.log_result(
                        "PO Creation Multiple PIs", 
                        False, 
                        f"reference_pi_ids mismatch: {po.get('reference_pi_ids')} != {expected_pi_ids}"
                    )
                    return False
                
                # Verify backward compatibility - reference_pi_id should be first PI
                if po.get("reference_pi_id") != self.test_data["pi_id_1"]:
                    self.log_result(
                        "PO Creation Multiple PIs", 
                        False, 
                        f"reference_pi_id not set to first PI: {po.get('reference_pi_id')} != {self.test_data['pi_id_1']}"
                    )
                    return False
                
                self.log_result(
                    "PO Creation Multiple PIs", 
                    True, 
                    f"Successfully created PO with multiple PIs - reference_pi_id: {po.get('reference_pi_id')}, reference_pi_ids: {po.get('reference_pi_ids')}"
                )
                return True
            else:
                self.log_result(
                    "PO Creation Multiple PIs", 
                    False, 
                    f"Failed to create PO with multiple PIs: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "PO Creation Multiple PIs", 
                False, 
                f"Error creating PO with multiple PIs: {str(e)}"
            )
            return False
    
    def test_po_creation_pi_validation(self):
        """Test 3: PO Creation PI Validation"""
        try:
            # Test with invalid PI ID
            po_data = {
                "company_id": self.test_data["company_id"],
                "voucher_no": f"TEST-PO-INVALID-PI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "consignee": "Test Consignee Invalid PI",
                "supplier": "Test Supplier Invalid PI",
                "reference_pi_ids": [
                    self.test_data["pi_id_1"],
                    "invalid-pi-id-12345",  # Invalid PI ID
                    self.test_data["pi_id_2"]
                ],
                "status": "Pending",
                "line_items": [
                    {
                        "product_name": "Test Product Invalid PI",
                        "sku": "TEST-INVALID-PI-SKU",
                        "quantity": 5,
                        "rate": 1000.00
                    }
                ]
            }
            
            response = self.session.post(
                f"{BASE_URL}/po",
                json=po_data
            )
            
            # Should fail with 404 for invalid PI
            if response.status_code == 404:
                response_data = response.json()
                if "not found" in response_data.get("detail", "").lower():
                    self.log_result(
                        "PO Creation PI Validation", 
                        True, 
                        f"Correctly rejected PO with invalid PI ID - {response.status_code}: {response_data.get('detail')}"
                    )
                    return True
                else:
                    self.log_result(
                        "PO Creation PI Validation", 
                        False, 
                        f"Wrong error message for invalid PI: {response_data.get('detail')}"
                    )
                    return False
            else:
                self.log_result(
                    "PO Creation PI Validation", 
                    False, 
                    f"Should have failed with 404 for invalid PI, got: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "PO Creation PI Validation", 
                False, 
                f"Error testing PI validation: {str(e)}"
            )
            return False
    
    # ==================== PO DETAIL RETRIEVAL TESTS ====================
    
    def test_po_detail_single_pi(self):
        """Test 4: PO Detail Retrieval for Single PI"""
        try:
            if not self.test_data.get("po_single_pi_id"):
                self.log_result(
                    "PO Detail Single PI", 
                    False, 
                    "No single PI PO available for testing"
                )
                return False
            
            response = self.session.get(f"{BASE_URL}/po/{self.test_data['po_single_pi_id']}")
            
            if response.status_code == 200:
                po = response.json()
                
                # Verify reference_pi field (backward compatibility)
                if "reference_pi" not in po:
                    self.log_result(
                        "PO Detail Single PI", 
                        False, 
                        "reference_pi field missing for backward compatibility"
                    )
                    return False
                
                # Verify reference_pis array
                if "reference_pis" not in po or len(po.get("reference_pis", [])) != 1:
                    self.log_result(
                        "PO Detail Single PI", 
                        False, 
                        f"reference_pis array incorrect: {po.get('reference_pis')}"
                    )
                    return False
                
                # Verify PI details are populated
                reference_pi = po.get("reference_pi")
                if not reference_pi or reference_pi.get("id") != self.test_data["pi_id_1"]:
                    self.log_result(
                        "PO Detail Single PI", 
                        False, 
                        f"reference_pi details incorrect: {reference_pi}"
                    )
                    return False
                
                reference_pis = po.get("reference_pis")
                if not reference_pis or reference_pis[0].get("id") != self.test_data["pi_id_1"]:
                    self.log_result(
                        "PO Detail Single PI", 
                        False, 
                        f"reference_pis[0] details incorrect: {reference_pis}"
                    )
                    return False
                
                self.log_result(
                    "PO Detail Single PI", 
                    True, 
                    f"Successfully retrieved PO with single PI details - PI ID: {reference_pi.get('id')}, PI Voucher: {reference_pi.get('voucher_no')}"
                )
                return True
            else:
                self.log_result(
                    "PO Detail Single PI", 
                    False, 
                    f"Failed to get PO details: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "PO Detail Single PI", 
                False, 
                f"Error getting PO details for single PI: {str(e)}"
            )
            return False
    
    def test_po_detail_multiple_pis(self):
        """Test 5: PO Detail Retrieval for Multiple PIs"""
        try:
            if not self.test_data.get("po_multiple_pis_id"):
                self.log_result(
                    "PO Detail Multiple PIs", 
                    False, 
                    "No multiple PIs PO available for testing"
                )
                return False
            
            response = self.session.get(f"{BASE_URL}/po/{self.test_data['po_multiple_pis_id']}")
            
            if response.status_code == 200:
                po = response.json()
                
                # Verify reference_pi field (backward compatibility - should be first PI)
                if "reference_pi" not in po:
                    self.log_result(
                        "PO Detail Multiple PIs", 
                        False, 
                        "reference_pi field missing for backward compatibility"
                    )
                    return False
                
                # Verify reference_pis array contains all PIs
                if "reference_pis" not in po or len(po.get("reference_pis", [])) != 3:
                    self.log_result(
                        "PO Detail Multiple PIs", 
                        False, 
                        f"reference_pis array should contain 3 PIs: {po.get('reference_pis')}"
                    )
                    return False
                
                # Verify first PI is in reference_pi for backward compatibility
                reference_pi = po.get("reference_pi")
                if not reference_pi or reference_pi.get("id") != self.test_data["pi_id_1"]:
                    self.log_result(
                        "PO Detail Multiple PIs", 
                        False, 
                        f"reference_pi should be first PI: {reference_pi}"
                    )
                    return False
                
                # Verify all PIs are in reference_pis array
                reference_pis = po.get("reference_pis")
                expected_pi_ids = [self.test_data["pi_id_1"], self.test_data["pi_id_2"], self.test_data["pi_id_3"]]
                actual_pi_ids = [pi.get("id") for pi in reference_pis]
                
                if set(actual_pi_ids) != set(expected_pi_ids):
                    self.log_result(
                        "PO Detail Multiple PIs", 
                        False, 
                        f"reference_pis PI IDs mismatch: {actual_pi_ids} != {expected_pi_ids}"
                    )
                    return False
                
                # Verify PI details are complete
                for pi in reference_pis:
                    if not pi.get("voucher_no") or not pi.get("line_items"):
                        self.log_result(
                            "PO Detail Multiple PIs", 
                            False, 
                            f"PI details incomplete: {pi}"
                        )
                        return False
                
                pi_vouchers = [pi.get("voucher_no") for pi in reference_pis]
                self.log_result(
                    "PO Detail Multiple PIs", 
                    True, 
                    f"Successfully retrieved PO with multiple PI details - PI Count: {len(reference_pis)}, PI Vouchers: {pi_vouchers}"
                )
                return True
            else:
                self.log_result(
                    "PO Detail Multiple PIs", 
                    False, 
                    f"Failed to get PO details: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "PO Detail Multiple PIs", 
                False, 
                f"Error getting PO details for multiple PIs: {str(e)}"
            )
            return False
    
    # ==================== PO UPDATE TESTS ====================
    
    def test_po_update_add_more_pis(self):
        """Test 6: PO Update - Add More PIs"""
        try:
            if not self.test_data.get("po_single_pi_id"):
                self.log_result(
                    "PO Update Add More PIs", 
                    False, 
                    "No single PI PO available for updating"
                )
                return False
            
            # Update single PI PO to have multiple PIs
            update_data = {
                "reference_pi_ids": [
                    self.test_data["pi_id_1"],  # Original PI
                    self.test_data["pi_id_2"],  # Add second PI
                    self.test_data["pi_id_3"]   # Add third PI
                ]
            }
            
            response = self.session.put(
                f"{BASE_URL}/po/{self.test_data['po_single_pi_id']}",
                json=update_data
            )
            
            if response.status_code == 200:
                po = response.json()
                
                # Verify updated PI IDs
                if not po.get("reference_pi_ids") or len(po.get("reference_pi_ids", [])) != 3:
                    self.log_result(
                        "PO Update Add More PIs", 
                        False, 
                        f"reference_pi_ids not updated correctly: {po.get('reference_pi_ids')}"
                    )
                    return False
                
                expected_pi_ids = [self.test_data["pi_id_1"], self.test_data["pi_id_2"], self.test_data["pi_id_3"]]
                if set(po.get("reference_pi_ids")) != set(expected_pi_ids):
                    self.log_result(
                        "PO Update Add More PIs", 
                        False, 
                        f"Updated PI IDs mismatch: {po.get('reference_pi_ids')} != {expected_pi_ids}"
                    )
                    return False
                
                # Verify backward compatibility field is still first PI
                if po.get("reference_pi_id") != self.test_data["pi_id_1"]:
                    self.log_result(
                        "PO Update Add More PIs", 
                        False, 
                        f"reference_pi_id should remain first PI: {po.get('reference_pi_id')} != {self.test_data['pi_id_1']}"
                    )
                    return False
                
                self.log_result(
                    "PO Update Add More PIs", 
                    True, 
                    f"Successfully updated PO to add more PIs - New PI count: {len(po.get('reference_pi_ids'))}"
                )
                return True
            else:
                self.log_result(
                    "PO Update Add More PIs", 
                    False, 
                    f"Failed to update PO: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "PO Update Add More PIs", 
                False, 
                f"Error updating PO to add more PIs: {str(e)}"
            )
            return False
    
    def test_po_update_change_pi_references(self):
        """Test 7: PO Update - Change PI References"""
        try:
            if not self.test_data.get("po_multiple_pis_id"):
                self.log_result(
                    "PO Update Change PI References", 
                    False, 
                    "No multiple PIs PO available for updating"
                )
                return False
            
            # Change PI references - remove one, keep others
            update_data = {
                "reference_pi_ids": [
                    self.test_data["pi_id_2"],  # Keep second PI
                    self.test_data["pi_id_3"]   # Keep third PI, remove first
                ]
            }
            
            response = self.session.put(
                f"{BASE_URL}/po/{self.test_data['po_multiple_pis_id']}",
                json=update_data
            )
            
            if response.status_code == 200:
                po = response.json()
                
                # Verify updated PI IDs
                if not po.get("reference_pi_ids") or len(po.get("reference_pi_ids", [])) != 2:
                    self.log_result(
                        "PO Update Change PI References", 
                        False, 
                        f"reference_pi_ids not updated correctly: {po.get('reference_pi_ids')}"
                    )
                    return False
                
                expected_pi_ids = [self.test_data["pi_id_2"], self.test_data["pi_id_3"]]
                if set(po.get("reference_pi_ids")) != set(expected_pi_ids):
                    self.log_result(
                        "PO Update Change PI References", 
                        False, 
                        f"Updated PI IDs mismatch: {po.get('reference_pi_ids')} != {expected_pi_ids}"
                    )
                    return False
                
                # Verify backward compatibility field is now first PI in new list
                if po.get("reference_pi_id") != self.test_data["pi_id_2"]:
                    self.log_result(
                        "PO Update Change PI References", 
                        False, 
                        f"reference_pi_id should be new first PI: {po.get('reference_pi_id')} != {self.test_data['pi_id_2']}"
                    )
                    return False
                
                self.log_result(
                    "PO Update Change PI References", 
                    True, 
                    f"Successfully updated PO PI references - New PI IDs: {po.get('reference_pi_ids')}, New first PI: {po.get('reference_pi_id')}"
                )
                return True
            else:
                self.log_result(
                    "PO Update Change PI References", 
                    False, 
                    f"Failed to update PO PI references: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "PO Update Change PI References", 
                False, 
                f"Error updating PO PI references: {str(e)}"
            )
            return False
    
    # ==================== INWARD STOCK INTEGRATION TESTS ====================
    
    def test_inward_stock_with_multiple_pis_po(self):
        """Test 8: Inward Stock Integration with PO having Multiple PIs"""
        try:
            if not self.test_data.get("po_multiple_pis_id"):
                self.log_result(
                    "Inward Stock Multiple PIs Integration", 
                    False, 
                    "No multiple PIs PO available for inward stock testing"
                )
                return False
            
            inward_data = {
                "inward_invoice_no": f"TEST-INWARD-MULTI-PI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "po_id": self.test_data["po_multiple_pis_id"],  # PO with multiple PIs
                "warehouse_id": self.test_data["warehouse_id"],
                "inward_type": "warehouse",
                "source_type": "direct_inward",
                "status": "Received",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Test Product Inward Multi PI",
                        "sku": "TEST-MULTI-PI-SKU-001",
                        "quantity": 10,
                        "rate": 2500.00
                    }
                ]
            }
            
            response = self.session.post(
                f"{BASE_URL}/inward-stock",
                json=inward_data
            )
            
            if response.status_code == 200:
                inward = response.json()
                self.test_data["inward_id"] = inward["id"]
                
                # Verify pi_ids array is populated from PO's reference_pi_ids
                if not inward.get("pi_ids") or len(inward.get("pi_ids", [])) == 0:
                    self.log_result(
                        "Inward Stock Multiple PIs Integration", 
                        False, 
                        f"pi_ids array not populated from PO: {inward.get('pi_ids')}"
                    )
                    return False
                
                # Verify pi_id is set to first PI for backward compatibility
                if not inward.get("pi_id"):
                    self.log_result(
                        "Inward Stock Multiple PIs Integration", 
                        False, 
                        f"pi_id not set for backward compatibility: {inward.get('pi_id')}"
                    )
                    return False
                
                # Verify pi_id is first element of pi_ids
                if inward.get("pi_id") != inward.get("pi_ids", [])[0]:
                    self.log_result(
                        "Inward Stock Multiple PIs Integration", 
                        False, 
                        f"pi_id should be first element of pi_ids: {inward.get('pi_id')} != {inward.get('pi_ids', [])[0] if inward.get('pi_ids') else 'None'}"
                    )
                    return False
                
                self.log_result(
                    "Inward Stock Multiple PIs Integration", 
                    True, 
                    f"Successfully created inward stock with multiple PIs - pi_id: {inward.get('pi_id')}, pi_ids: {inward.get('pi_ids')}"
                )
                return True
            else:
                self.log_result(
                    "Inward Stock Multiple PIs Integration", 
                    False, 
                    f"Failed to create inward stock: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Inward Stock Multiple PIs Integration", 
                False, 
                f"Error creating inward stock with multiple PIs: {str(e)}"
            )
            return False
    
    # ==================== CUSTOMER MANAGEMENT INTEGRATION TESTS ====================
    
    def test_customer_management_pi_po_mapping_multiple_pis(self):
        """Test 9: Customer Management PI-PO Mapping with Multiple PIs"""
        try:
            response = self.session.get(f"{BASE_URL}/customer-management/pi-po-mapping")
            
            if response.status_code == 200:
                mappings = response.json()
                
                # Find our test PIs in the mappings (PIs we created)
                test_pi_mappings = []
                test_pi_ids = [self.test_data.get("pi_id_1"), self.test_data.get("pi_id_2"), self.test_data.get("pi_id_3")]
                
                for mapping in mappings:
                    if mapping.get("pi_id") in test_pi_ids:
                        test_pi_mappings.append(mapping)
                
                if len(test_pi_mappings) == 0:
                    self.log_result(
                        "Customer Management PI-PO Mapping Multiple PIs", 
                        False, 
                        "Test PIs not found in PI-PO mappings"
                    )
                    return False
                
                # Verify mappings include linked POs (check that PIs have linked POs)
                pis_with_linked_pos = 0
                total_linked_pos = 0
                
                for mapping in test_pi_mappings:
                    linked_pos = mapping.get("linked_pos", [])
                    if len(linked_pos) > 0:
                        pis_with_linked_pos += 1
                        total_linked_pos += len(linked_pos)
                        
                        # Verify PO structure (po_id should be present)
                        for po in linked_pos:
                            if not po.get("po_id"):
                                self.log_result(
                                    "Customer Management PI-PO Mapping Multiple PIs", 
                                    False, 
                                    f"PO ID missing in mapping: {po}"
                                )
                                return False
                
                if pis_with_linked_pos == 0:
                    self.log_result(
                        "Customer Management PI-PO Mapping Multiple PIs", 
                        False, 
                        "No test PIs have linked POs in mappings"
                    )
                    return False
                
                self.log_result(
                    "Customer Management PI-PO Mapping Multiple PIs", 
                    True, 
                    f"Successfully found test PIs in PI-PO mappings - PI mappings: {len(test_pi_mappings)}, PIs with linked POs: {pis_with_linked_pos}, Total linked POs: {total_linked_pos}"
                )
                return True
            else:
                self.log_result(
                    "Customer Management PI-PO Mapping Multiple PIs", 
                    False, 
                    f"Failed to get PI-PO mappings: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Customer Management PI-PO Mapping Multiple PIs", 
                False, 
                f"Error testing PI-PO mapping: {str(e)}"
            )
            return False
    
    def test_customer_management_inward_quantity_multiple_pis(self):
        """Test 10: Customer Management Inward Quantity with Multiple PIs"""
        try:
            response = self.session.get(f"{BASE_URL}/customer-management/inward-quantity")
            
            if response.status_code == 200:
                inward_quantities = response.json()
                
                # Find our test inward entry in the results
                test_inward_found = False
                for entry in inward_quantities:
                    if entry.get("po_id") == self.test_data.get("po_multiple_pis_id"):
                        test_inward_found = True
                        
                        # Verify entry has required fields
                        required_fields = ["consignee_name", "pi_number", "pi_id", "po_number", "po_id", 
                                         "pi_total_quantity", "inward_total_quantity", "remaining_quantity", 
                                         "sku_details", "status"]
                        
                        missing_fields = [field for field in required_fields if field not in entry]
                        if missing_fields:
                            self.log_result(
                                "Customer Management Inward Quantity Multiple PIs", 
                                False, 
                                f"Missing required fields in inward quantity entry: {missing_fields}"
                            )
                            return False
                        
                        # Verify calculations are correct
                        if entry.get("remaining_quantity") != (entry.get("pi_total_quantity", 0) - entry.get("inward_total_quantity", 0)):
                            self.log_result(
                                "Customer Management Inward Quantity Multiple PIs", 
                                False, 
                                f"Remaining quantity calculation incorrect: {entry.get('remaining_quantity')} != {entry.get('pi_total_quantity', 0) - entry.get('inward_total_quantity', 0)}"
                            )
                            return False
                        
                        break
                
                if not test_inward_found:
                    self.log_result(
                        "Customer Management Inward Quantity Multiple PIs", 
                        False, 
                        "Test inward entry with multiple PIs PO not found in inward quantities"
                    )
                    return False
                
                self.log_result(
                    "Customer Management Inward Quantity Multiple PIs", 
                    True, 
                    f"Successfully found test inward entry in inward quantities - Total entries: {len(inward_quantities)}"
                )
                return True
            else:
                self.log_result(
                    "Customer Management Inward Quantity Multiple PIs", 
                    False, 
                    f"Failed to get inward quantities: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Customer Management Inward Quantity Multiple PIs", 
                False, 
                f"Error testing inward quantity: {str(e)}"
            )
            return False
    
    # ==================== MAIN TEST RUNNER ====================
    
    def run_all_tests(self):
        """Run all PO Multiple PIs tests"""
        print("🚀 STARTING PO MULTIPLE PIs BACKEND SUPPORT TESTING")
        print("=" * 80)
        
        # Authentication
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        # Setup test data
        if not self.setup_test_data():
            print("❌ Test data setup failed. Cannot proceed with tests.")
            return False
        
        print("\n📋 RUNNING PO MULTIPLE PIs TESTS:")
        print("-" * 50)
        
        # Run all tests
        tests = [
            self.test_po_creation_single_pi_backward_compatibility,
            self.test_po_creation_multiple_pis,
            self.test_po_creation_pi_validation,
            self.test_po_detail_single_pi,
            self.test_po_detail_multiple_pis,
            self.test_po_update_add_more_pis,
            self.test_po_update_change_pi_references,
            self.test_inward_stock_with_multiple_pis_po,
            self.test_customer_management_pi_po_mapping_multiple_pis,
            self.test_customer_management_inward_quantity_multiple_pis
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ EXCEPTION in {test.__name__}: {str(e)}")
                failed += 1
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 PO MULTIPLE PIs TESTING SUMMARY")
        print("=" * 80)
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"📈 SUCCESS RATE: {(passed / (passed + failed) * 100):.1f}%")
        
        if failed == 0:
            print("\n🎉 ALL PO MULTIPLE PIs TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  {failed} TEST(S) FAILED - SEE DETAILS ABOVE")
            return False

def main():
    """Main function to run PO Multiple PIs tests"""
    test_suite = POMultiplePIsTestSuite()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n✅ PO Multiple PIs Backend Support is working correctly!")
        exit(0)
    else:
        print("\n❌ PO Multiple PIs Backend Support has issues that need to be addressed!")
        exit(1)

if __name__ == "__main__":
    main()