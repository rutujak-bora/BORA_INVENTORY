"""
Test script to verify outward stock updates in stock summary
Run this script to check if the stock tracking is working correctly
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# You'll need to get a valid token first by logging in
# Replace this with your actual token
TOKEN = "your_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_stock_flow():
    print("=" * 80)
    print("STOCK FLOW TEST")
    print("=" * 80)
    
    # Step 1: Get stock summary before creating outward entry
    print("\n1️⃣ Getting stock summary BEFORE outward entry...")
    response = requests.get(f"{BASE_URL}/stock-summary", headers=headers)
    if response.status_code == 200:
        stock_before = response.json()
        print(f"   ✅ Found {len(stock_before)} stock entries")
        if stock_before:
            sample = stock_before[0]
            print(f"   📦 Sample entry: {sample.get('product_name')}")
            print(f"      - Inward: {sample.get('quantity_inward', 0)}")
            print(f"      - Outward: {sample.get('quantity_outward', 0)}")
            print(f"      - Remaining: {sample.get('remaining_stock', 0)}")
    else:
        print(f"   ❌ Error: {response.status_code}")
        return
    
    # Step 2: Get a product and warehouse for testing
    print("\n2️⃣ Getting test data...")
    
    # Get warehouses
    response = requests.get(f"{BASE_URL}/warehouses", headers=headers)
    warehouses = response.json() if response.status_code == 200 else []
    if not warehouses:
        print("   ❌ No warehouses found")
        return
    warehouse = warehouses[0]
    print(f"   ✅ Using warehouse: {warehouse.get('name')} ({warehouse.get('id')})")
    
    # Get companies
    response = requests.get(f"{BASE_URL}/companies", headers=headers)
    companies = response.json() if response.status_code == 200 else []
    if not companies:
        print("   ❌ No companies found")
        return
    company = companies[0]
    print(f"   ✅ Using company: {company.get('name')} ({company.get('id')})")
    
    # Get PIs
    response = requests.get(f"{BASE_URL}/pi", headers=headers)
    pis = response.json() if response.status_code == 200 else []
    if not pis:
        print("   ❌ No PIs found")
        return
    pi = pis[0]
    print(f"   ✅ Using PI: {pi.get('voucher_no')} ({pi.get('id')})")
    
    # Get PI details with warehouse context
    response = requests.get(f"{BASE_URL}/pi/{pi.get('id')}?warehouse_id={warehouse.get('id')}", headers=headers)
    if response.status_code != 200:
        print(f"   ❌ Error getting PI details: {response.status_code}")
        return
    pi_details = response.json()
    
    if not pi_details.get('line_items'):
        print("   ❌ PI has no line items")
        return
    
    line_item = pi_details['line_items'][0]
    print(f"   ✅ Using product: {line_item.get('product_name')}")
    print(f"      - Product ID: {line_item.get('product_id')}")
    print(f"      - Available Qty: {line_item.get('available_quantity', 0)}")
    print(f"      - Dispatched Qty: {line_item.get('dispatched_quantity', 0)}")
    
    # Step 3: Create a dispatch plan
    print("\n3️⃣ Creating dispatch plan...")
    
    dispatch_data = {
        "dispatch_type": "dispatch_plan",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "company_id": company.get('id'),
        "warehouse_id": warehouse.get('id'),
        "mode": "Sea",
        "pi_ids": [pi.get('id')],
        "line_items": [{
            "product_id": line_item.get('product_id'),
            "product_name": line_item.get('product_name'),
            "sku": line_item.get('sku'),
            "rate": line_item.get('rate', 0),
            "dispatch_quantity": 10,  # Test with 10 units
            "pi_total_quantity": line_item.get('pi_quantity', 0),
            "dimensions": "",
            "weight": 0
        }]
    }
    
    response = requests.post(f"{BASE_URL}/outward-stock", headers=headers, json=dispatch_data)
    if response.status_code == 200:
        dispatch_plan = response.json()
        print(f"   ✅ Dispatch plan created: {dispatch_plan.get('export_invoice_no')}")
    else:
        print(f"   ❌ Error creating dispatch plan: {response.status_code}")
        print(f"      {response.text}")
        return
    
    # Step 4: Get stock summary AFTER creating outward entry
    print("\n4️⃣ Getting stock summary AFTER outward entry...")
    response = requests.get(f"{BASE_URL}/stock-summary", headers=headers)
    if response.status_code == 200:
        stock_after = response.json()
        
        # Find the product we just dispatched
        product_stock = next((s for s in stock_after if s.get('product_id') == line_item.get('product_id')), None)
        
        if product_stock:
            print(f"   ✅ Found product in stock summary: {product_stock.get('product_name')}")
            print(f"      - Inward: {product_stock.get('quantity_inward', 0)}")
            print(f"      - Outward: {product_stock.get('quantity_outward', 0)} ⬅️ Should be 10")
            print(f"      - Remaining: {product_stock.get('remaining_stock', 0)}")
            
            if product_stock.get('quantity_outward', 0) >= 10:
                print("\n   ✅ ✅ ✅ SUCCESS! Stock summary updated correctly!")
            else:
                print("\n   ❌ ❌ ❌ ISSUE! Outward quantity not updated!")
                print("      Let's check the stock_tracking collection directly...")
                
                # Use debug endpoint
                response = requests.get(
                    f"{BASE_URL}/stock-summary/debug/{line_item.get('product_id')}?warehouse_id={warehouse.get('id')}", 
                    headers=headers
                )
                if response.status_code == 200:
                    debug_data = response.json()
                    print(f"\n   📊 Debug data:")
                    print(f"      - Stock tracking entries: {debug_data.get('total_tracking_entries')}")
                    print(f"      - Outward entries: {debug_data.get('total_outward_entries')}")
                    print(json.dumps(debug_data, indent=2))
        else:
            print(f"   ❌ Product not found in stock summary!")
    else:
        print(f"   ❌ Error: {response.status_code}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: You need to update the TOKEN variable in this script first!")
    print("   1. Log in to the application")
    print("   2. Open browser DevTools (F12)")
    print("   3. Go to Application/Storage → Local Storage")
    print("   4. Copy the 'token' value")
    print("   5. Paste it in this script where it says 'your_token_here'")
    print("\n   Then run: python test_outward_stock.py\n")
    
    # Uncomment this line after adding your token
    # test_stock_flow()
