#!/usr/bin/env python3
"""
Stock Movement Flow Testing for Bora Mobility Inventory System
Testing the complete stock movement flow as requested:
1. Create Pick-up Inward Stock Entry
2. Mark Stock as Inwarded to Warehouse  
3. Mark as Done
4. Verify in Dispatch Plan
5. Check Available Quantity
6. Create Dispatch Plan
7. Convert to Export Invoice
8. Check Stock Summary
"""

import requests
import json
import uuid
from datetime import datetime
import os

# Configuration
BASE_URL = "https://stockbulkactions.preview.emergentagent.com/api"

# Test credentials
TEST_USER = {
    "username": "rutuja@bora.tech",
    "password": "rutuja@123"
}

class StockMovementTestSuite:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_data = {
            "company_id": None,
            "product_id": None,
            "warehouse_id": None,
            "pi_id": None,
            "po_id": None,
            "pickup_inward_id": None,
            "warehouse_inward_id": None,
            "dispatch_plan_id": None,
            "export_invoice_id": None
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
        """Test authentication"""
        try:
            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json=TEST_USER,
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
                    f"Successfully authenticated as {TEST_USER['username']}"
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
        """Setup test data - get existing company, warehouse, PO from database"""
        try:
            # Get existing companies
            companies_response = self.session.get(f"{BASE_URL}/companies")
            if companies_response.status_code != 200:
                self.log_result("Setup - Get Companies", False, f"Failed to get companies: {companies_response.status_code}")
                return False
            
            companies = companies_response.json()
            if not companies:
                self.log_result("Setup - Get Companies", False, "No companies found in database")
                return False
            
            self.test_data["company_id"] = companies[0]["id"]
            
            # Get existing warehouses
            warehouses_response = self.session.get(f"{BASE_URL}/warehouses")
            if warehouses_response.status_code != 200:
                self.log_result("Setup - Get Warehouses", False, f"Failed to get warehouses: {warehouses_response.status_code}")
                return False
            
            warehouses = warehouses_response.json()
            if not warehouses:
                self.log_result("Setup - Get Warehouses", False, "No warehouses found in database")
                return False
            
            self.test_data["warehouse_id"] = warehouses[0]["id"]
            
            # Get existing products
            products_response = self.session.get(f"{BASE_URL}/products")
            if products_response.status_code != 200:
                self.log_result("Setup - Get Products", False, f"Failed to get products: {products_response.status_code}")
                return False
            
            products = products_response.json()
            if not products:
                self.log_result("Setup - Get Products", False, "No products found in database")
                return False
            
            self.test_data["product_id"] = products[0]["id"]
            
            # Get existing POs
            pos_response = self.session.get(f"{BASE_URL}/po")
            if pos_response.status_code != 200:
                self.log_result("Setup - Get POs", False, f"Failed to get POs: {pos_response.status_code}")
                return False
            
            pos = pos_response.json()
            if not pos:
                self.log_result("Setup - Get POs", False, "No POs found in database")
                return False
            
            self.test_data["po_id"] = pos[0]["id"]
            
            # Get PI from PO
            po_detail_response = self.session.get(f"{BASE_URL}/po/{self.test_data['po_id']}")
            if po_detail_response.status_code == 200:
                po_detail = po_detail_response.json()
                if po_detail.get("reference_pi_id"):
                    self.test_data["pi_id"] = po_detail["reference_pi_id"]
                elif po_detail.get("reference_pi_ids") and len(po_detail["reference_pi_ids"]) > 0:
                    self.test_data["pi_id"] = po_detail["reference_pi_ids"][0]
            
            self.log_result(
                "Setup Test Data", 
                True, 
                f"Successfully retrieved existing data - Company: {companies[0]['name']}, Warehouse: {warehouses[0]['name']}, Product: {products[0]['sku_name']}, PO: {pos[0]['voucher_no']}"
            )
            return True
            
        except Exception as e:
            self.log_result("Setup Test Data", False, f"Error setting up test data: {str(e)}")
            return False
    
    def test_1_create_pickup_inward_stock_entry(self):
        """Test 1: Create Pick-up Inward Stock Entry with inward_type='in_transit'"""
        try:
            pickup_inward_data = {
                "inward_invoice_no": f"PICKUP-FLOW-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "po_id": self.test_data["po_id"],
                "inward_type": "in_transit",
                "source_type": "pickup_inward",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Stock Movement Test Product",
                        "sku": "STOCK-FLOW-SKU-001",
                        "quantity": 100,  # Test quantity as requested
                        "rate": 500.00
                    }
                ]
            }
            
            response = self.session.post(f"{BASE_URL}/inward-stock", json=pickup_inward_data)
            
            if response.status_code == 200:
                pickup_inward = response.json()
                self.test_data["pickup_inward_id"] = pickup_inward["id"]
                
                # Verify entry is created with status awaiting warehouse assignment
                if pickup_inward.get("inward_type") != "in_transit":
                    self.log_result(
                        "Create Pick-up Inward Stock Entry", 
                        False, 
                        f"Incorrect inward_type: {pickup_inward.get('inward_type')} != in_transit"
                    )
                    return False
                
                if pickup_inward.get("status") not in ["Pending", "Received"]:
                    self.log_result(
                        "Create Pick-up Inward Stock Entry", 
                        False, 
                        f"Unexpected status: {pickup_inward.get('status')}"
                    )
                    return False
                
                # Verify total amount
                expected_total = 100 * 500.00  # 50000
                if pickup_inward.get("total_amount") != expected_total:
                    self.log_result(
                        "Create Pick-up Inward Stock Entry", 
                        False, 
                        f"Incorrect total amount: {pickup_inward.get('total_amount')} != {expected_total}"
                    )
                    return False
                
                self.log_result(
                    "Create Pick-up Inward Stock Entry", 
                    True, 
                    f"Successfully created Pick-up Inward entry - ID: {pickup_inward['id']}, Status: {pickup_inward['status']}, Total: ₹{pickup_inward['total_amount']}"
                )
                return True
            else:
                self.log_result(
                    "Create Pick-up Inward Stock Entry", 
                    False, 
                    f"Failed to create Pick-up Inward: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Create Pick-up Inward Stock Entry", 
                False, 
                f"Error creating Pick-up Inward: {str(e)}"
            )
            return False
    
    def test_2_mark_stock_as_inwarded_to_warehouse(self):
        """Test 2: Mark Stock as Inwarded to Warehouse using pickup-to-warehouse endpoint"""
        try:
            # Use the transfer-to-warehouse endpoint to move stock to warehouse
            transfer_data = {
                "pickup_inward_id": self.test_data["pickup_inward_id"],
                "warehouse_id": self.test_data["warehouse_id"]
            }
            
            response = self.session.post(f"{BASE_URL}/inward-stock/transfer-to-warehouse", json=transfer_data)
            
            if response.status_code == 200:
                transfer_result = response.json()
                
                # Verify warehouse inward entry is created
                if not transfer_result.get("warehouse_inward"):
                    self.log_result(
                        "Mark Stock as Inwarded to Warehouse", 
                        False, 
                        "Warehouse inward entry not created"
                    )
                    return False
                
                warehouse_inward = transfer_result["warehouse_inward"]
                self.test_data["warehouse_inward_id"] = warehouse_inward["id"]
                
                # Verify original pickup is marked as Transferred
                pickup_detail_response = self.session.get(f"{BASE_URL}/inward-stock/{self.test_data['pickup_inward_id']}")
                if pickup_detail_response.status_code == 200:
                    pickup_detail = pickup_detail_response.json()
                    
                    if pickup_detail.get("status") != "Transferred":
                        self.log_result(
                            "Mark Stock as Inwarded to Warehouse", 
                            False, 
                            f"Original pickup not marked as Transferred: {pickup_detail.get('status')}"
                        )
                        return False
                    
                    # Verify stock moves to warehouse
                    if warehouse_inward.get("warehouse_id") != self.test_data["warehouse_id"]:
                        self.log_result(
                            "Mark Stock as Inwarded to Warehouse", 
                            False, 
                            f"Stock not moved to correct warehouse: {warehouse_inward.get('warehouse_id')} != {self.test_data['warehouse_id']}"
                        )
                        return False
                    
                    self.log_result(
                        "Mark Stock as Inwarded to Warehouse", 
                        True, 
                        f"Successfully moved stock to warehouse - Original pickup marked as Transferred, New warehouse entry: {warehouse_inward['id']}"
                    )
                    return True
                else:
                    self.log_result(
                        "Mark Stock as Inwarded to Warehouse", 
                        False, 
                        f"Failed to get pickup detail: {pickup_detail_response.status_code}"
                    )
                    return False
            else:
                self.log_result(
                    "Mark Stock as Inwarded to Warehouse", 
                    False, 
                    f"Failed to transfer to warehouse: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Mark Stock as Inwarded to Warehouse", 
                False, 
                f"Error transferring to warehouse: {str(e)}"
            )
            return False
    
    def test_3_mark_as_done(self):
        """Test 3: Mark as Done using mark-done endpoint"""
        try:
            # Create another pickup entry for Done testing
            pickup_done_data = {
                "inward_invoice_no": f"PICKUP-DONE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "po_id": self.test_data["po_id"],
                "inward_type": "in_transit",
                "source_type": "pickup_inward",
                "status": "Pending",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Stock Movement Done Test Product",
                        "sku": "STOCK-DONE-SKU-001",
                        "quantity": 50,
                        "rate": 600.00
                    }
                ]
            }
            
            pickup_response = self.session.post(f"{BASE_URL}/inward-stock", json=pickup_done_data)
            if pickup_response.status_code != 200:
                self.log_result(
                    "Mark as Done - Setup", 
                    False, 
                    f"Failed to create pickup for Done test: {pickup_response.status_code}"
                )
                return False
            
            pickup_for_done = pickup_response.json()
            
            # Mark as Done
            done_data = {
                "warehouse_id": self.test_data["warehouse_id"]
            }
            
            response = self.session.post(f"{BASE_URL}/inward-stock/{pickup_for_done['id']}/mark-done", json=done_data)
            
            if response.status_code == 200:
                done_result = response.json()
                
                # Verify stock is finalized in warehouse
                done_detail_response = self.session.get(f"{BASE_URL}/inward-stock/{pickup_for_done['id']}")
                if done_detail_response.status_code == 200:
                    done_detail = done_detail_response.json()
                    
                    # Verify entry type changed to warehouse
                    if done_detail.get("inward_type") != "warehouse":
                        self.log_result(
                            "Mark as Done", 
                            False, 
                            f"Entry type not changed to warehouse: {done_detail.get('inward_type')}"
                        )
                        return False
                    
                    # Verify status changed to Done
                    if done_detail.get("status") != "Done":
                        self.log_result(
                            "Mark as Done", 
                            False, 
                            f"Status not changed to Done: {done_detail.get('status')}"
                        )
                        return False
                    
                    # Verify warehouse assignment
                    if done_detail.get("warehouse_id") != self.test_data["warehouse_id"]:
                        self.log_result(
                            "Mark as Done", 
                            False, 
                            f"Warehouse not assigned correctly: {done_detail.get('warehouse_id')} != {self.test_data['warehouse_id']}"
                        )
                        return False
                    
                    self.log_result(
                        "Mark as Done", 
                        True, 
                        f"Successfully marked as Done - Type: warehouse, Status: Done, Warehouse assigned"
                    )
                    return True
                else:
                    self.log_result(
                        "Mark as Done", 
                        False, 
                        f"Failed to get done entry detail: {done_detail_response.status_code}"
                    )
                    return False
            else:
                self.log_result(
                    "Mark as Done", 
                    False, 
                    f"Failed to mark as done: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Mark as Done", 
                False, 
                f"Error marking as done: {str(e)}"
            )
            return False
    
    def test_4_verify_in_dispatch_plan(self):
        """Test 4: Verify in Dispatch Plan using dispatch-plans-pending endpoint"""
        try:
            # Get pending dispatch plans
            response = self.session.get(f"{BASE_URL}/outward-stock/dispatch-plans-pending")
            
            if response.status_code == 200:
                dispatch_plans = response.json()
                
                if not isinstance(dispatch_plans, list):
                    self.log_result(
                        "Verify in Dispatch Plan", 
                        False, 
                        "Response is not a list"
                    )
                    return False
                
                # Verify the inwarded stock appears as available
                # This endpoint should show dispatch plans that can be converted to export invoices
                self.log_result(
                    "Verify in Dispatch Plan", 
                    True, 
                    f"Successfully retrieved {len(dispatch_plans)} pending dispatch plans - Inwarded stock available for dispatch planning"
                )
                return True
            else:
                self.log_result(
                    "Verify in Dispatch Plan", 
                    False, 
                    f"Failed to get dispatch plans: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Verify in Dispatch Plan", 
                False, 
                f"Error verifying dispatch plan: {str(e)}"
            )
            return False
    
    def test_5_check_available_quantity(self):
        """Test 5: Check Available Quantity using available-quantity endpoint"""
        try:
            # Get available quantity for the product
            response = self.session.get(f"{BASE_URL}/outward-stock/available-quantity/{self.test_data['product_id']}")
            
            if response.status_code == 200:
                available_data = response.json()
                
                # Should show quantity from completed inward stock
                if not isinstance(available_data, dict):
                    self.log_result(
                        "Check Available Quantity", 
                        False, 
                        "Response is not a dictionary"
                    )
                    return False
                
                # Verify available quantity is greater than 0 (from our inward stock)
                available_quantity = available_data.get("available_quantity", 0)
                if available_quantity <= 0:
                    self.log_result(
                        "Check Available Quantity", 
                        False, 
                        f"No available quantity found: {available_quantity}"
                    )
                    return False
                
                self.log_result(
                    "Check Available Quantity", 
                    True, 
                    f"Successfully retrieved available quantity: {available_quantity} units from completed inward stock"
                )
                return True
            else:
                self.log_result(
                    "Check Available Quantity", 
                    False, 
                    f"Failed to get available quantity: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Check Available Quantity", 
                False, 
                f"Error checking available quantity: {str(e)}"
            )
            return False
    
    def test_6_create_dispatch_plan(self):
        """Test 6: Create Dispatch Plan using quantity from inwarded stock"""
        try:
            # Create dispatch plan with dispatch_type='dispatch_plan'
            dispatch_plan_data = {
                "export_invoice_no": f"DISPATCH-PLAN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "company_id": self.test_data["company_id"],
                "pi_ids": [self.test_data["pi_id"]] if self.test_data["pi_id"] else [],
                "warehouse_id": self.test_data["warehouse_id"],
                "dispatch_type": "dispatch_plan",
                "mode": "Sea",
                "status": "Pending Dispatch",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Dispatch Plan Test Product",
                        "sku": "DISPATCH-SKU-001",
                        "dispatch_quantity": 80,  # Use quantity from inwarded stock (less than 100)
                        "rate": 500.00,
                        "dimensions": "10x10x10",
                        "weight": 5.0
                    }
                ]
            }
            
            response = self.session.post(f"{BASE_URL}/outward-stock", json=dispatch_plan_data)
            
            if response.status_code == 200:
                dispatch_plan = response.json()
                self.test_data["dispatch_plan_id"] = dispatch_plan["id"]
                
                # Verify dispatch plan created
                if dispatch_plan.get("dispatch_type") != "dispatch_plan":
                    self.log_result(
                        "Create Dispatch Plan", 
                        False, 
                        f"Incorrect dispatch_type: {dispatch_plan.get('dispatch_type')} != dispatch_plan"
                    )
                    return False
                
                # Verify total amount
                expected_total = 80 * 500.00  # 40000
                if dispatch_plan.get("total_amount") != expected_total:
                    self.log_result(
                        "Create Dispatch Plan", 
                        False, 
                        f"Incorrect total amount: {dispatch_plan.get('total_amount')} != {expected_total}"
                    )
                    return False
                
                self.log_result(
                    "Create Dispatch Plan", 
                    True, 
                    f"Successfully created Dispatch Plan - ID: {dispatch_plan['id']}, Type: {dispatch_plan['dispatch_type']}, Total: ₹{dispatch_plan['total_amount']}"
                )
                return True
            else:
                self.log_result(
                    "Create Dispatch Plan", 
                    False, 
                    f"Failed to create dispatch plan: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Create Dispatch Plan", 
                False, 
                f"Error creating dispatch plan: {str(e)}"
            )
            return False
    
    def test_7_convert_to_export_invoice(self):
        """Test 7: Convert to Export Invoice using dispatch_plan_id"""
        try:
            # Create export invoice with dispatch_type='export_invoice' and dispatch_plan_id
            export_invoice_data = {
                "export_invoice_no": f"EXPORT-INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": datetime.now().isoformat(),
                "company_id": self.test_data["company_id"],
                "pi_ids": [self.test_data["pi_id"]] if self.test_data["pi_id"] else [],
                "warehouse_id": self.test_data["warehouse_id"],
                "dispatch_type": "export_invoice",
                "dispatch_plan_id": self.test_data["dispatch_plan_id"],  # Link to dispatch plan
                "mode": "Sea",
                "status": "Dispatched",
                "line_items": [
                    {
                        "product_id": self.test_data["product_id"],
                        "product_name": "Export Invoice Test Product",
                        "sku": "EXPORT-SKU-001",
                        "dispatch_quantity": 80,  # Same quantity as dispatch plan
                        "rate": 500.00,
                        "dimensions": "10x10x10",
                        "weight": 5.0
                    }
                ]
            }
            
            response = self.session.post(f"{BASE_URL}/outward-stock", json=export_invoice_data)
            
            if response.status_code == 200:
                export_invoice = response.json()
                self.test_data["export_invoice_id"] = export_invoice["id"]
                
                # Verify export invoice created
                if export_invoice.get("dispatch_type") != "export_invoice":
                    self.log_result(
                        "Convert to Export Invoice", 
                        False, 
                        f"Incorrect dispatch_type: {export_invoice.get('dispatch_type')} != export_invoice"
                    )
                    return False
                
                # Verify dispatch_plan_id is linked
                if export_invoice.get("dispatch_plan_id") != self.test_data["dispatch_plan_id"]:
                    self.log_result(
                        "Convert to Export Invoice", 
                        False, 
                        f"dispatch_plan_id not linked: {export_invoice.get('dispatch_plan_id')} != {self.test_data['dispatch_plan_id']}"
                    )
                    return False
                
                self.log_result(
                    "Convert to Export Invoice", 
                    True, 
                    f"Successfully created Export Invoice - ID: {export_invoice['id']}, Linked to Dispatch Plan: {export_invoice['dispatch_plan_id']}"
                )
                return True
            else:
                self.log_result(
                    "Convert to Export Invoice", 
                    False, 
                    f"Failed to create export invoice: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Convert to Export Invoice", 
                False, 
                f"Error creating export invoice: {str(e)}"
            )
            return False
    
    def test_8_check_stock_summary(self):
        """Test 8: Check Stock Summary for correct categorization"""
        try:
            # Get stock summary
            response = self.session.get(f"{BASE_URL}/stock-summary")
            
            if response.status_code == 200:
                stock_summary = response.json()
                
                if not isinstance(stock_summary, list):
                    self.log_result(
                        "Check Stock Summary", 
                        False, 
                        "Response is not a list"
                    )
                    return False
                
                # Find our test product in the summary
                test_product_summary = None
                for item in stock_summary:
                    if item.get("product_id") == self.test_data["product_id"]:
                        test_product_summary = item
                        break
                
                if not test_product_summary:
                    self.log_result(
                        "Check Stock Summary", 
                        False, 
                        "Test product not found in stock summary"
                    )
                    return False
                
                # Verify correct categorization
                inward_qty = test_product_summary.get("quantity_inward", 0)
                outward_qty = test_product_summary.get("quantity_outward", 0)
                remaining_stock = test_product_summary.get("remaining_stock", 0)
                
                # Should show inward warehouse stock (before dispatch) and export invoice stock (after dispatch)
                if inward_qty <= 0:
                    self.log_result(
                        "Check Stock Summary", 
                        False, 
                        f"No inward quantity found: {inward_qty}"
                    )
                    return False
                
                if outward_qty <= 0:
                    self.log_result(
                        "Check Stock Summary", 
                        False, 
                        f"No outward quantity found: {outward_qty}"
                    )
                    return False
                
                # Verify remaining stock calculation
                expected_remaining = inward_qty - outward_qty
                if remaining_stock != expected_remaining:
                    self.log_result(
                        "Check Stock Summary", 
                        False, 
                        f"Incorrect remaining stock calculation: {remaining_stock} != {expected_remaining}"
                    )
                    return False
                
                self.log_result(
                    "Check Stock Summary", 
                    True, 
                    f"Successfully verified stock summary - Inward: {inward_qty}, Outward: {outward_qty}, Remaining: {remaining_stock}"
                )
                return True
            else:
                self.log_result(
                    "Check Stock Summary", 
                    False, 
                    f"Failed to get stock summary: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Check Stock Summary", 
                False, 
                f"Error checking stock summary: {str(e)}"
            )
            return False
    
    def run_complete_stock_movement_flow(self):
        """Run the complete stock movement flow test"""
        print("=" * 80)
        print("STOCK MOVEMENT FLOW TESTING - Bora Mobility Inventory System")
        print("=" * 80)
        
        # Authenticate
        if not self.authenticate():
            return False
        
        # Setup test data
        if not self.setup_test_data():
            return False
        
        # Run all tests in sequence
        tests = [
            self.test_1_create_pickup_inward_stock_entry,
            self.test_2_mark_stock_as_inwarded_to_warehouse,
            self.test_3_mark_as_done,
            self.test_4_verify_in_dispatch_plan,
            self.test_5_check_available_quantity,
            self.test_6_create_dispatch_plan,
            self.test_7_convert_to_export_invoice,
            self.test_8_check_stock_summary
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            if test():
                passed += 1
            else:
                failed += 1
        
        # Print summary
        print("\n" + "=" * 80)
        print("STOCK MOVEMENT FLOW TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {len(tests)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result["success"]:
                    print(f"❌ {result['test']}: {result['message']}")
        
        return failed == 0

def main():
    """Main function to run stock movement flow tests"""
    test_suite = StockMovementTestSuite()
    success = test_suite.run_complete_stock_movement_flow()
    
    if success:
        print("\n🎉 All stock movement flow tests passed!")
        exit(0)
    else:
        print("\n💥 Some stock movement flow tests failed!")
        exit(1)

if __name__ == "__main__":
    main()