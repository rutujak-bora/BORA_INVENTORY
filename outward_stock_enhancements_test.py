#!/usr/bin/env python3
"""
Comprehensive Testing of Outward Stock Enhancements Feature
Testing all new outward stock functionality as per review request
"""

import requests
import json
import uuid
from datetime import datetime
import os

# Configuration
BASE_URL = "https://stockbulkactions.preview.emergentagent.com/api"

# Test credentials
TEST_CREDENTIALS = {
    "username": "rutuja@bora.tech",
    "password": "rutuja@123"
}

class OutwardStockEnhancementsTestSuite:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_data = {
            "company_id": None,
            "product_id": None,
            "product_id_2": None,
            "warehouse_id": None,
            "pi_id": None,
            "pi_id_2": None,
            "po_id": None,
            "inward_id": None,
            "dispatch_plan_id": None,
            "dispatch_plan_id_2": None,
            "export_invoice_id": None,
            "export_invoice_standalone_id": None
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
    
    def authenticate(self):
        """Test authentication with rutuja@bora.tech / rutuja@123"""
        try:
            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json=TEST_CREDENTIALS,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                self.log_result(
                    "Authentication", 
                    True, 
                    f"Successfully authenticated as {TEST_CREDENTIALS['username']}"
                )
                return True
            else:
                self.log_result(
                    "Authentication", 
                    False, 
                    f"Failed to authenticate: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Authentication", 
                False, 
                f"Authentication error: {str(e)}"
            )
            return False
    
    def setup_test_data(self):
        """Setup - Login and Create Test Data (POs, PIs, Warehouses, Inward Stock)"""
        try:
            # Get existing companies
            companies_response = self.session.get(f"{BASE_URL}/companies")
            if companies_response.status_code != 200:
                self.log_result("Setup - Get Companies", False, f"Failed to get companies: {companies_response.status_code}")
                return False
            
            companies = companies_response.json()
            if not companies:
                self.log_result("Setup - Get Companies", False, "No companies found")
                return False
            
            self.test_data["company_id"] = companies[0]["id"]
            
            # Get existing warehouses
            warehouses_response = self.session.get(f"{BASE_URL}/warehouses")
            if warehouses_response.status_code != 200:
                self.log_result("Setup - Get Warehouses", False, f"Failed to get warehouses: {warehouses_response.status_code}")
                return False
            
            warehouses = warehouses_response.json()
            if not warehouses:
                self.log_result("Setup - Get Warehouses", False, "No warehouses found")
                return False
            
            self.test_data["warehouse_id"] = warehouses[0]["id"]
            
            # Get existing products with inward stock
            products_response = self.session.get(f"{BASE_URL}/products")
            if products_response.status_code != 200:
                self.log_result("Setup - Get Products", False, f"Failed to get products: {products_response.status_code}")
                return False
            
            products = products_response.json()
            if len(products) < 2:
                self.log_result("Setup - Get Products", False, "Need at least 2 products for testing")
                return False
            
            self.test_data["product_id"] = products[0]["id"]
            self.test_data["product_id_2"] = products[1]["id"]
            
            # Create test PIs for multiple PI testing
            pi_data_1 = {
                "company_id": self.test_data["company_id"],
                "voucher_no": f"TEST-OUTWARD-PI-1-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "consignee": "Test Outward Consignee 1",
                "buyer": "Test Outward Buyer 1",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Samsung Galaxy Book 4 Pro",
                        "sku": "TEST-OUTWARD-SKU-001",
                        "category": "Electronics",
                        "brand": "Samsung",
                        "hsn_sac": "8517",
                        "made_in": "India",
                        "quantity": 50,
                        "rate": 1500.00
                    }
                ]
            }
            
            pi_response_1 = self.session.post(f"{BASE_URL}/pi", json=pi_data_1)
            if pi_response_1.status_code != 200:
                self.log_result("Setup - Create PI 1", False, f"Failed to create PI 1: {pi_response_1.status_code}")
                return False
            
            pi_1 = pi_response_1.json()
            self.test_data["pi_id"] = pi_1["id"]
            
            # Create second PI for multiple PI testing
            pi_data_2 = {
                "company_id": self.test_data["company_id"],
                "voucher_no": f"TEST-OUTWARD-PI-2-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "consignee": "Test Outward Consignee 2",
                "buyer": "Test Outward Buyer 2",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id_2"],
                        "product_name": "Apple MacBook Air M2",
                        "sku": "TEST-OUTWARD-SKU-002",
                        "category": "Electronics",
                        "brand": "Apple",
                        "hsn_sac": "8517",
                        "made_in": "India",
                        "quantity": 30,
                        "rate": 2000.00
                    }
                ]
            }
            
            pi_response_2 = self.session.post(f"{BASE_URL}/pi", json=pi_data_2)
            if pi_response_2.status_code != 200:
                self.log_result("Setup - Create PI 2", False, f"Failed to create PI 2: {pi_response_2.status_code}")
                return False
            
            pi_2 = pi_response_2.json()
            self.test_data["pi_id_2"] = pi_2["id"]
            
            # Create PO for inward stock
            po_data = {
                "company_id": self.test_data["company_id"],
                "voucher_no": f"TEST-OUTWARD-PO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "consignee": "Test Outward Consignee",
                "supplier": "Test Supplier Ltd",
                "reference_pi_ids": [self.test_data["pi_id"], self.test_data["pi_id_2"]],
                "reference_no_date": f"TEST-OUTWARD-REF | {datetime.now().strftime('%Y-%m-%d')}",
                "dispatched_through": "Test Logistics",
                "destination": "Mumbai Port",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Samsung Galaxy Book 4 Pro",
                        "sku": "TEST-OUTWARD-SKU-001",
                        "category": "Electronics",
                        "brand": "Samsung",
                        "hsn_sac": "8517",
                        "quantity": 100,
                        "rate": 1500.00,
                        "input_igst": 270.00,
                        "tds": 15.00
                    },
                    {
                        "product_id": self.test_data["product_id_2"],
                        "product_name": "Apple MacBook Air M2",
                        "sku": "TEST-OUTWARD-SKU-002",
                        "category": "Electronics",
                        "brand": "Apple",
                        "hsn_sac": "8517",
                        "quantity": 60,
                        "rate": 2000.00,
                        "input_igst": 360.00,
                        "tds": 20.00
                    }
                ]
            }
            
            po_response = self.session.post(f"{BASE_URL}/po", json=po_data)
            if po_response.status_code != 200:
                self.log_result("Setup - Create PO", False, f"Failed to create PO: {po_response.status_code}")
                return False
            
            po = po_response.json()
            self.test_data["po_id"] = po["id"]
            
            # Create inward stock to have available stock
            inward_data = {
                "inward_invoice_no": f"TEST-OUTWARD-INWARD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "po_id": self.test_data["po_id"],
                "warehouse_id": self.test_data["warehouse_id"],
                "inward_type": "warehouse",
                "source_type": "direct_inward",
                "status": "Received",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Samsung Galaxy Book 4 Pro",
                        "sku": "TEST-OUTWARD-SKU-001",
                        "quantity": 100,  # Available stock
                        "rate": 1500.00
                    },
                    {
                        "product_id": self.test_data["product_id_2"],
                        "product_name": "Apple MacBook Air M2",
                        "sku": "TEST-OUTWARD-SKU-002",
                        "quantity": 60,  # Available stock
                        "rate": 2000.00
                    }
                ]
            }
            
            inward_response = self.session.post(f"{BASE_URL}/inward-stock", json=inward_data)
            if inward_response.status_code != 200:
                self.log_result("Setup - Create Inward Stock", False, f"Failed to create inward stock: {inward_response.status_code}")
                return False
            
            inward = inward_response.json()
            self.test_data["inward_id"] = inward["id"]
            
            self.log_result(
                "Setup - Create Test Data", 
                True, 
                f"Successfully created test data - Company: {self.test_data['company_id'][:8]}..., Warehouse: {self.test_data['warehouse_id'][:8]}..., Products: 2, PIs: 2, PO: {self.test_data['po_id'][:8]}..., Inward Stock: {self.test_data['inward_id'][:8]}..."
            )
            return True
            
        except Exception as e:
            self.log_result("Setup - Create Test Data", False, f"Error setting up test data: {str(e)}")
            return False
    
    def test_1_setup_login_create_test_data(self):
        """Test 1: Setup - Login and Create Test Data"""
        if not self.authenticate():
            return False
        
        # Verify existing data
        pos_response = self.session.get(f"{BASE_URL}/po")
        pis_response = self.session.get(f"{BASE_URL}/pi")
        warehouses_response = self.session.get(f"{BASE_URL}/warehouses")
        inward_response = self.session.get(f"{BASE_URL}/inward-stock")
        
        if all(r.status_code == 200 for r in [pos_response, pis_response, warehouses_response, inward_response]):
            pos = pos_response.json()
            pis = pis_response.json()
            warehouses = warehouses_response.json()
            inward_entries = inward_response.json()
            
            self.log_result(
                "Verify Existing Data", 
                True, 
                f"Verified existing data - POs: {len(pos)}, PIs: {len(pis)}, Warehouses: {len(warehouses)}, Inward Stock: {len(inward_entries)}"
            )
        
        return self.setup_test_data()
    
    def test_2_create_dispatch_plans(self):
        """Test 2: Create 2-3 Dispatch Plans (dispatch_type: "dispatch_plan")"""
        try:
            # Create first dispatch plan
            dispatch_plan_1_data = {
                "export_invoice_no": f"DP-{datetime.now().strftime('%Y%m%d%H%M%S')}-1",
                "date": datetime.now().isoformat(),
                "company_id": self.test_data["company_id"],
                "pi_ids": [self.test_data["pi_id"]],
                "warehouse_id": self.test_data["warehouse_id"],
                "mode": "Sea",
                "containers_pallets": 2,
                "dispatch_type": "dispatch_plan",
                "status": "Pending Dispatch",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Samsung Galaxy Book 4 Pro",
                        "sku": "TEST-OUTWARD-SKU-001",
                        "quantity": 20,
                        "rate": 1500.00,
                        "dimensions": "30x20x5 cm",
                        "weight": 2.5
                    }
                ]
            }
            
            dp1_response = self.session.post(f"{BASE_URL}/outward-stock", json=dispatch_plan_1_data)
            if dp1_response.status_code != 200:
                self.log_result("Create Dispatch Plan 1", False, f"Failed to create dispatch plan 1: {dp1_response.status_code}", {"response": dp1_response.text})
                return False
            
            dp1 = dp1_response.json()
            self.test_data["dispatch_plan_id"] = dp1["id"]
            
            # Create second dispatch plan with multiple PIs
            dispatch_plan_2_data = {
                "export_invoice_no": f"DP-{datetime.now().strftime('%Y%m%d%H%M%S')}-2",
                "date": datetime.now().isoformat(),
                "company_id": self.test_data["company_id"],
                "pi_ids": [self.test_data["pi_id"], self.test_data["pi_id_2"]],  # Multiple PIs
                "warehouse_id": self.test_data["warehouse_id"],
                "mode": "Air",
                "containers_pallets": 5,
                "dispatch_type": "dispatch_plan",
                "status": "Pending Dispatch",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Samsung Galaxy Book 4 Pro",
                        "sku": "TEST-OUTWARD-SKU-001",
                        "quantity": 15,
                        "rate": 1500.00,
                        "dimensions": "30x20x5 cm",
                        "weight": 2.5
                    },
                    {
                        "product_id": self.test_data["product_id_2"],
                        "product_name": "Apple MacBook Air M2",
                        "sku": "TEST-OUTWARD-SKU-002",
                        "quantity": 10,
                        "rate": 2000.00,
                        "dimensions": "35x25x2 cm",
                        "weight": 1.8
                    }
                ]
            }
            
            dp2_response = self.session.post(f"{BASE_URL}/outward-stock", json=dispatch_plan_2_data)
            if dp2_response.status_code != 200:
                self.log_result("Create Dispatch Plan 2", False, f"Failed to create dispatch plan 2: {dp2_response.status_code}", {"response": dp2_response.text})
                return False
            
            dp2 = dp2_response.json()
            self.test_data["dispatch_plan_id_2"] = dp2["id"]
            
            # Create third dispatch plan
            dispatch_plan_3_data = {
                "export_invoice_no": f"DP-{datetime.now().strftime('%Y%m%d%H%M%S')}-3",
                "date": datetime.now().isoformat(),
                "company_id": self.test_data["company_id"],
                "pi_ids": [self.test_data["pi_id_2"]],
                "warehouse_id": self.test_data["warehouse_id"],
                "mode": "Sea",
                "containers_pallets": 1,
                "dispatch_type": "dispatch_plan",
                "status": "Pending Dispatch",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id_2"],
                        "product_name": "Apple MacBook Air M2",
                        "sku": "TEST-OUTWARD-SKU-002",
                        "quantity": 8,
                        "rate": 2000.00,
                        "dimensions": "35x25x2 cm",
                        "weight": 1.8
                    }
                ]
            }
            
            dp3_response = self.session.post(f"{BASE_URL}/outward-stock", json=dispatch_plan_3_data)
            if dp3_response.status_code != 200:
                self.log_result("Create Dispatch Plan 3", False, f"Failed to create dispatch plan 3: {dp3_response.status_code}", {"response": dp3_response.text})
                return False
            
            dp3 = dp3_response.json()
            
            self.log_result(
                "Create Dispatch Plans", 
                True, 
                f"Successfully created 3 dispatch plans - DP1: {dp1['id'][:8]}... (Single PI), DP2: {dp2['id'][:8]}... (Multiple PIs), DP3: {dp3['id'][:8]}... (Single PI)"
            )
            return True
            
        except Exception as e:
            self.log_result("Create Dispatch Plans", False, f"Error creating dispatch plans: {str(e)}")
            return False
    
    def test_3_get_dispatch_plans_pending(self):
        """Test 3: Test GET /api/outward-stock/dispatch-plans-pending"""
        try:
            response = self.session.get(f"{BASE_URL}/outward-stock/dispatch-plans-pending")
            
            if response.status_code == 200:
                pending_dispatch_plans = response.json()
                
                if not isinstance(pending_dispatch_plans, list):
                    self.log_result("GET Dispatch Plans Pending", False, "Response is not a list")
                    return False
                
                # Verify dispatch plans without linked export invoices appear
                found_our_dispatch_plans = 0
                for dp in pending_dispatch_plans:
                    if dp.get("id") in [self.test_data.get("dispatch_plan_id"), self.test_data.get("dispatch_plan_id_2")]:
                        found_our_dispatch_plans += 1
                        
                        # Verify company details are included
                        if not dp.get("company"):
                            self.log_result("GET Dispatch Plans Pending", False, "Company details not included")
                            return False
                        
                        # Verify PI details are included
                        if not dp.get("pis") or len(dp.get("pis", [])) == 0:
                            self.log_result("GET Dispatch Plans Pending", False, "PI details not included")
                            return False
                
                if found_our_dispatch_plans < 2:
                    self.log_result("GET Dispatch Plans Pending", False, f"Only found {found_our_dispatch_plans} of our dispatch plans in pending list")
                    return False
                
                self.log_result(
                    "GET Dispatch Plans Pending", 
                    True, 
                    f"Successfully retrieved {len(pending_dispatch_plans)} pending dispatch plans with company and PI details included"
                )
                return True
            else:
                self.log_result("GET Dispatch Plans Pending", False, f"Failed to get pending dispatch plans: {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_result("GET Dispatch Plans Pending", False, f"Error getting pending dispatch plans: {str(e)}")
            return False
    
    def test_4_get_available_quantity(self):
        """Test 4: Test GET /api/outward-stock/available-quantity/{product_id}"""
        try:
            # Test with warehouse_id
            response = self.session.get(f"{BASE_URL}/outward-stock/available-quantity/{self.test_data['product_id']}?warehouse_id={self.test_data['warehouse_id']}")
            
            if response.status_code == 200:
                availability = response.json()
                
                # Verify response structure
                required_fields = ["product_id", "warehouse_id", "total_inward", "total_outward", "available_quantity"]
                for field in required_fields:
                    if field not in availability:
                        self.log_result("GET Available Quantity", False, f"Missing field: {field}")
                        return False
                
                # Verify formula: available = inward - outward
                expected_available = availability["total_inward"] - availability["total_outward"]
                if availability["available_quantity"] != max(0, expected_available):
                    self.log_result("GET Available Quantity", False, f"Incorrect available quantity calculation: {availability['available_quantity']} != max(0, {expected_available})")
                    return False
                
                # Test with different product
                response2 = self.session.get(f"{BASE_URL}/outward-stock/available-quantity/{self.test_data['product_id_2']}?warehouse_id={self.test_data['warehouse_id']}")
                
                if response2.status_code == 200:
                    availability2 = response2.json()
                    
                    self.log_result(
                        "GET Available Quantity", 
                        True, 
                        f"Successfully retrieved available quantities - Product 1: Inward={availability['total_inward']}, Outward={availability['total_outward']}, Available={availability['available_quantity']} | Product 2: Available={availability2['available_quantity']}"
                    )
                    return True
                else:
                    self.log_result("GET Available Quantity", False, f"Failed to get availability for product 2: {response2.status_code}")
                    return False
            else:
                self.log_result("GET Available Quantity", False, f"Failed to get available quantity: {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_result("GET Available Quantity", False, f"Error getting available quantity: {str(e)}")
            return False
    
    def test_5_export_invoice_with_dispatch_plan_link(self):
        """Test 5: Test Export Invoice Creation with Dispatch Plan Link"""
        try:
            # Create Export Invoice linked to one of the pending Dispatch Plans
            export_invoice_data = {
                "export_invoice_no": f"EI-LINKED-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "company_id": self.test_data["company_id"],
                "pi_ids": [self.test_data["pi_id"]],
                "warehouse_id": self.test_data["warehouse_id"],
                "mode": "Sea",
                "containers_pallets": 2,
                "dispatch_type": "export_invoice",
                "dispatch_plan_id": self.test_data["dispatch_plan_id"],  # Link to Dispatch Plan
                "status": "Pending Dispatch",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Samsung Galaxy Book 4 Pro",
                        "sku": "TEST-OUTWARD-SKU-001",
                        "quantity": 20,
                        "rate": 1500.00,
                        "dimensions": "30x20x5 cm",
                        "weight": 2.5
                    }
                ]
            }
            
            response = self.session.post(f"{BASE_URL}/outward-stock", json=export_invoice_data)
            
            if response.status_code == 200:
                export_invoice = response.json()
                self.test_data["export_invoice_id"] = export_invoice["id"]
                
                # Verify dispatch_plan_id is stored correctly
                if export_invoice.get("dispatch_plan_id") != self.test_data["dispatch_plan_id"]:
                    self.log_result("Export Invoice with Dispatch Plan Link", False, f"dispatch_plan_id not stored correctly: {export_invoice.get('dispatch_plan_id')} != {self.test_data['dispatch_plan_id']}")
                    return False
                
                # Verify Export Invoice created successfully
                if export_invoice.get("dispatch_type") != "export_invoice":
                    self.log_result("Export Invoice with Dispatch Plan Link", False, f"Incorrect dispatch_type: {export_invoice.get('dispatch_type')}")
                    return False
                
                self.log_result(
                    "Export Invoice with Dispatch Plan Link", 
                    True, 
                    f"Successfully created Export Invoice linked to Dispatch Plan - EI: {export_invoice['id'][:8]}..., Linked DP: {export_invoice['dispatch_plan_id'][:8]}..."
                )
                return True
            else:
                self.log_result("Export Invoice with Dispatch Plan Link", False, f"Failed to create export invoice: {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_result("Export Invoice with Dispatch Plan Link", False, f"Error creating export invoice with dispatch plan link: {str(e)}")
            return False
    
    def test_6_verify_dispatch_plan_excluded(self):
        """Test 6: Verify Linked Dispatch Plan Excluded from Pending List"""
        try:
            # Fetch pending dispatch plans again
            response = self.session.get(f"{BASE_URL}/outward-stock/dispatch-plans-pending")
            
            if response.status_code == 200:
                pending_dispatch_plans = response.json()
                
                # Verify linked dispatch plan is excluded
                for dp in pending_dispatch_plans:
                    if dp.get("id") == self.test_data["dispatch_plan_id"]:
                        self.log_result("Verify Dispatch Plan Excluded", False, "Linked dispatch plan still appears in pending list")
                        return False
                
                # Verify unlinked dispatch plan still appears
                found_unlinked = False
                for dp in pending_dispatch_plans:
                    if dp.get("id") == self.test_data["dispatch_plan_id_2"]:
                        found_unlinked = True
                        break
                
                if not found_unlinked:
                    self.log_result("Verify Dispatch Plan Excluded", False, "Unlinked dispatch plan not found in pending list")
                    return False
                
                self.log_result(
                    "Verify Dispatch Plan Excluded", 
                    True, 
                    f"Successfully verified - Linked dispatch plan excluded, unlinked dispatch plans still appear ({len(pending_dispatch_plans)} pending)"
                )
                return True
            else:
                self.log_result("Verify Dispatch Plan Excluded", False, f"Failed to get pending dispatch plans: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Verify Dispatch Plan Excluded", False, f"Error verifying dispatch plan exclusion: {str(e)}")
            return False
    
    def test_7_export_invoice_without_dispatch_plan(self):
        """Test 7: Test Export Invoice Creation without Dispatch Plan"""
        try:
            # Create standalone Export Invoice without dispatch_plan_id
            standalone_export_data = {
                "export_invoice_no": f"EI-STANDALONE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "company_id": self.test_data["company_id"],
                "pi_ids": [self.test_data["pi_id_2"]],
                "warehouse_id": self.test_data["warehouse_id"],
                "mode": "Air",
                "containers_pallets": 3,
                "dispatch_type": "export_invoice",
                # No dispatch_plan_id - standalone
                "status": "Dispatched",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id_2"],
                        "product_name": "Apple MacBook Air M2",
                        "sku": "TEST-OUTWARD-SKU-002",
                        "quantity": 15,
                        "rate": 2000.00,
                        "dimensions": "35x25x2 cm",
                        "weight": 1.8
                    }
                ]
            }
            
            response = self.session.post(f"{BASE_URL}/outward-stock", json=standalone_export_data)
            
            if response.status_code == 200:
                standalone_export = response.json()
                self.test_data["export_invoice_standalone_id"] = standalone_export["id"]
                
                # Verify it works as standalone export invoice
                if standalone_export.get("dispatch_type") != "export_invoice":
                    self.log_result("Export Invoice without Dispatch Plan", False, f"Incorrect dispatch_type: {standalone_export.get('dispatch_type')}")
                    return False
                
                # Verify no dispatch_plan_id is set
                if standalone_export.get("dispatch_plan_id"):
                    self.log_result("Export Invoice without Dispatch Plan", False, f"dispatch_plan_id should be null but got: {standalone_export.get('dispatch_plan_id')}")
                    return False
                
                # Verify all existing validations still work
                if not standalone_export.get("line_items") or len(standalone_export.get("line_items", [])) == 0:
                    self.log_result("Export Invoice without Dispatch Plan", False, "Line items validation failed")
                    return False
                
                self.log_result(
                    "Export Invoice without Dispatch Plan", 
                    True, 
                    f"Successfully created standalone Export Invoice - EI: {standalone_export['id'][:8]}..., No dispatch_plan_id, Status: {standalone_export['status']}"
                )
                return True
            else:
                self.log_result("Export Invoice without Dispatch Plan", False, f"Failed to create standalone export invoice: {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_result("Export Invoice without Dispatch Plan", False, f"Error creating standalone export invoice: {str(e)}")
            return False
    
    def test_8_quantity_validation(self):
        """Test 8: Test Quantity Validation (Prevent Overselling)"""
        try:
            # Get current available quantity
            availability_response = self.session.get(f"{BASE_URL}/outward-stock/available-quantity/{self.test_data['product_id']}?warehouse_id={self.test_data['warehouse_id']}")
            
            if availability_response.status_code != 200:
                self.log_result("Quantity Validation - Get Availability", False, f"Failed to get availability: {availability_response.status_code}")
                return False
            
            availability = availability_response.json()
            available_qty = availability["available_quantity"]
            
            # Try to create Export Invoice with quantity exceeding available inward
            oversell_data = {
                "export_invoice_no": f"EI-OVERSELL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "company_id": self.test_data["company_id"],
                "pi_ids": [self.test_data["pi_id"]],
                "warehouse_id": self.test_data["warehouse_id"],
                "mode": "Sea",
                "containers_pallets": 1,
                "dispatch_type": "export_invoice",
                "status": "Pending Dispatch",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Samsung Galaxy Book 4 Pro",
                        "sku": "TEST-OUTWARD-SKU-001",
                        "quantity": available_qty + 50,  # Exceed available quantity
                        "rate": 1500.00,
                        "dimensions": "30x20x5 cm",
                        "weight": 2.5
                    }
                ]
            }
            
            response = self.session.post(f"{BASE_URL}/outward-stock", json=oversell_data)
            
            # Backend should reject with appropriate error message
            if response.status_code == 400 or response.status_code == 422:
                error_response = response.text
                if "stock" in error_response.lower() or "quantity" in error_response.lower() or "available" in error_response.lower():
                    self.log_result(
                        "Quantity Validation", 
                        True, 
                        f"Successfully rejected overselling - Available: {available_qty}, Attempted: {available_qty + 50}, Error: {response.status_code}"
                    )
                    return True
                else:
                    self.log_result("Quantity Validation", False, f"Rejected but with unexpected error message: {error_response}")
                    return False
            elif response.status_code == 200:
                self.log_result("Quantity Validation", False, f"Backend incorrectly allowed overselling - Available: {available_qty}, Attempted: {available_qty + 50}")
                return False
            else:
                self.log_result("Quantity Validation", False, f"Unexpected response code: {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_result("Quantity Validation", False, f"Error testing quantity validation: {str(e)}")
            return False
    
    def test_9_multiple_pis_export_invoice(self):
        """Test 9: Test Multiple PIs in Export Invoice"""
        try:
            # Create Export Invoice with multiple pi_ids
            multi_pi_export_data = {
                "export_invoice_no": f"EI-MULTI-PI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "company_id": self.test_data["company_id"],
                "pi_ids": [self.test_data["pi_id"], self.test_data["pi_id_2"]],  # Multiple PIs
                "warehouse_id": self.test_data["warehouse_id"],
                "mode": "Air",
                "containers_pallets": 4,
                "dispatch_type": "export_invoice",
                "dispatch_plan_id": self.test_data["dispatch_plan_id_2"],  # Link to Dispatch Plan with multiple PIs
                "status": "Pending Dispatch",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Samsung Galaxy Book 4 Pro",
                        "sku": "TEST-OUTWARD-SKU-001",
                        "quantity": 10,
                        "rate": 1500.00,
                        "dimensions": "30x20x5 cm",
                        "weight": 2.5
                    },
                    {
                        "product_id": self.test_data["product_id_2"],
                        "product_name": "Apple MacBook Air M2",
                        "sku": "TEST-OUTWARD-SKU-002",
                        "quantity": 8,
                        "rate": 2000.00,
                        "dimensions": "35x25x2 cm",
                        "weight": 1.8
                    }
                ]
            }
            
            response = self.session.post(f"{BASE_URL}/outward-stock", json=multi_pi_export_data)
            
            if response.status_code == 200:
                multi_pi_export = response.json()
                
                # Verify pi_ids array stored correctly
                if not multi_pi_export.get("pi_ids") or len(multi_pi_export.get("pi_ids", [])) != 2:
                    self.log_result("Multiple PIs Export Invoice", False, f"pi_ids array not stored correctly: {multi_pi_export.get('pi_ids')}")
                    return False
                
                # Verify PI reference mapping works
                expected_pi_ids = set([self.test_data["pi_id"], self.test_data["pi_id_2"]])
                actual_pi_ids = set(multi_pi_export.get("pi_ids", []))
                if expected_pi_ids != actual_pi_ids:
                    self.log_result("Multiple PIs Export Invoice", False, f"PI IDs don't match: {actual_pi_ids} != {expected_pi_ids}")
                    return False
                
                # Verify both entries linked via dispatch_plan_id
                if multi_pi_export.get("dispatch_plan_id") != self.test_data["dispatch_plan_id_2"]:
                    self.log_result("Multiple PIs Export Invoice", False, f"dispatch_plan_id not linked correctly: {multi_pi_export.get('dispatch_plan_id')}")
                    return False
                
                self.log_result(
                    "Multiple PIs Export Invoice", 
                    True, 
                    f"Successfully created Export Invoice with multiple PIs - EI: {multi_pi_export['id'][:8]}..., PIs: {len(multi_pi_export['pi_ids'])}, Linked DP: {multi_pi_export['dispatch_plan_id'][:8]}..."
                )
                return True
            else:
                self.log_result("Multiple PIs Export Invoice", False, f"Failed to create multi-PI export invoice: {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_result("Multiple PIs Export Invoice", False, f"Error creating multi-PI export invoice: {str(e)}")
            return False
    
    def test_10_get_outward_stock_with_dispatch_plan_id(self):
        """Test 10: Test GET /api/outward-stock with dispatch_plan_id field"""
        try:
            # Fetch all outward entries
            response = self.session.get(f"{BASE_URL}/outward-stock")
            
            if response.status_code == 200:
                outward_entries = response.json()
                
                if not isinstance(outward_entries, list):
                    self.log_result("GET Outward Stock", False, "Response is not a list")
                    return False
                
                # Verify Dispatch Plans and Export Invoices returned
                dispatch_plans_count = 0
                export_invoices_count = 0
                linked_export_invoices_count = 0
                standalone_export_invoices_count = 0
                
                for entry in outward_entries:
                    dispatch_type = entry.get("dispatch_type")
                    
                    if dispatch_type == "dispatch_plan":
                        dispatch_plans_count += 1
                    elif dispatch_type == "export_invoice":
                        export_invoices_count += 1
                        
                        # Verify dispatch_plan_id field populated for linked Export Invoices
                        if entry.get("dispatch_plan_id"):
                            linked_export_invoices_count += 1
                        else:
                            standalone_export_invoices_count += 1
                
                # Verify no dispatch_plan_id for standalone entries
                for entry in outward_entries:
                    if entry.get("dispatch_type") == "dispatch_plan" and entry.get("dispatch_plan_id"):
                        self.log_result("GET Outward Stock", False, "Dispatch Plan should not have dispatch_plan_id field")
                        return False
                
                self.log_result(
                    "GET Outward Stock", 
                    True, 
                    f"Successfully retrieved {len(outward_entries)} outward entries - Dispatch Plans: {dispatch_plans_count}, Export Invoices: {export_invoices_count} (Linked: {linked_export_invoices_count}, Standalone: {standalone_export_invoices_count})"
                )
                return True
            else:
                self.log_result("GET Outward Stock", False, f"Failed to get outward stock: {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_result("GET Outward Stock", False, f"Error getting outward stock: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all outward stock enhancement tests"""
        print("=" * 80)
        print("OUTWARD STOCK ENHANCEMENTS - COMPREHENSIVE TESTING")
        print("=" * 80)
        
        tests = [
            self.test_1_setup_login_create_test_data,
            self.test_2_create_dispatch_plans,
            self.test_3_get_dispatch_plans_pending,
            self.test_4_get_available_quantity,
            self.test_5_export_invoice_with_dispatch_plan_link,
            self.test_6_verify_dispatch_plan_excluded,
            self.test_7_export_invoice_without_dispatch_plan,
            self.test_8_quantity_validation,
            self.test_9_multiple_pis_export_invoice,
            self.test_10_get_outward_stock_with_dispatch_plan_id
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
                print(f"❌ FAIL: {test.__name__} - Unexpected error: {str(e)}")
                failed += 1
        
        print("\n" + "=" * 80)
        print("OUTWARD STOCK ENHANCEMENTS TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {passed + failed}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed / (passed + failed) * 100):.1f}%" if (passed + failed) > 0 else "0%")
        
        if failed == 0:
            print("\n🎉 ALL OUTWARD STOCK ENHANCEMENT TESTS PASSED!")
        else:
            print(f"\n⚠️  {failed} TEST(S) FAILED - CHECK DETAILS ABOVE")
        
        return failed == 0

if __name__ == "__main__":
    test_suite = OutwardStockEnhancementsTestSuite()
    success = test_suite.run_all_tests()
    exit(0 if success else 1)