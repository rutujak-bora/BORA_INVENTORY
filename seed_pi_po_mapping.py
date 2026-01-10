"""
Seed script for PI to PO Mapping feature
Creates sample PIs and POs with linked relationships for testing
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import uuid

# MongoDB connection
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "bora_inventory_mongo"

async def seed_data():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("🌱 Starting seed process for PI-PO Mapping...")
    
    # Get existing companies, products, warehouses
    companies = await db.companies.find({"is_active": True}, {"_id": 0}).to_list(length=None)
    products = await db.products.find({"is_active": True}, {"_id": 0}).to_list(length=None)
    
    if not companies or not products:
        print("❌ No companies or products found. Please create master data first.")
        return
    
    company1 = companies[0]
    print(f"✅ Using Company: {company1['name']}")
    
    # Use first 3 products
    product_list = products[:3]
    print(f"✅ Using {len(product_list)} products")
    
    # Create 3 sample PIs
    pis_created = []
    
    for i in range(1, 4):
        pi_id = str(uuid.uuid4())
        pi_number = f"TEST-PI-MAPPING-{i:03d}"
        
        # Create line items with varying quantities
        line_items = []
        total_amount = 0
        
        for idx, product in enumerate(product_list):
            quantity = 100 + (i * 20) + (idx * 10)  # Varying quantities
            rate = 10 + (i * 2) + (idx * 1.5)  # Varying rates
            amount = quantity * rate
            
            line_items.append({
                "product_id": product["id"],
                "product_name": product.get("sku_name", f"Product-{product['id'][:8]}"),
                "sku": product.get("sku_name", f"SKU-{product['id'][:8]}"),
                "category": product.get("category", "Electronics"),
                "brand": product.get("brand", "Generic"),
                "hsn_sac": product.get("hsn_sac", "12345678"),
                "quantity": quantity,
                "rate": rate,
                "amount": amount
            })
            total_amount += amount
        
        pi_doc = {
            "id": pi_id,
            "voucher_no": pi_number,
            "date": datetime(2025, 11, i, 10, 0, 0).isoformat(),
            "company_id": company1["id"],
            "company_name": company1["name"],
            "buyer": f"Test Buyer {i}",
            "consignee": f"Test Consignee Company {i}",
            "supplier": f"Test Supplier {i}",
            "line_items": line_items,
            "total_amount": total_amount,
            "status": "Active",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.performa_invoices.insert_one(pi_doc)
        pis_created.append(pi_doc)
        print(f"✅ Created PI: {pi_number} with {len(line_items)} items, Total: ₹{total_amount:.2f}")
    
    # Create 2 POs for each PI (6 total POs)
    pos_created = 0
    
    for pi_idx, pi in enumerate(pis_created):
        # Create 2 POs per PI with partial quantities
        for po_num in range(1, 3):
            po_id = str(uuid.uuid4())
            po_number = f"TEST-PO-MAPPING-{pi_idx+1:03d}-{po_num}"
            
            # Create line items with partial quantities from PI
            line_items = []
            total_amount = 0
            
            for pi_item in pi["line_items"]:
                # PO gets 40% of PI quantity for PO1, 30% for PO2
                po_quantity = int(pi_item["quantity"] * (0.4 if po_num == 1 else 0.3))
                # PO rate slightly higher than PI rate
                po_rate = pi_item["rate"] * 1.1
                amount = po_quantity * po_rate
                
                line_items.append({
                    "product_id": pi_item["product_id"],
                    "product_name": pi_item["product_name"],
                    "sku": pi_item["sku"],
                    "category": pi_item["category"],
                    "brand": pi_item["brand"],
                    "hsn_sac": pi_item["hsn_sac"],
                    "quantity": po_quantity,
                    "rate": po_rate,
                    "amount": amount,
                    "gst_percentage": 18,
                    "tds_percentage": 2,
                    "gst_value": amount * 0.18,
                    "tds_value": amount * 0.02
                })
                total_amount += amount
            
            po_doc = {
                "id": po_id,
                "voucher_no": po_number,
                "date": datetime(2025, 11, pi_idx + 1 + po_num, 10, 0, 0).isoformat(),
                "company_id": company1["id"],
                "company_name": company1["name"],
                "supplier": pi["supplier"],
                "consignee": pi["consignee"],
                "reference_pi_id": pi["id"],  # Link to PI
                "reference_pi_ids": [pi["id"]],  # Array for multi-PI support
                "line_items": line_items,
                "total_amount": total_amount,
                "status": "Pending",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.purchase_orders.insert_one(po_doc)
            pos_created += 1
            print(f"  ✅ Created PO: {po_number} linked to {pi['voucher_no']}, Total: ₹{total_amount:.2f}")
    
    print(f"\n🎉 Seed completed successfully!")
    print(f"📊 Summary:")
    print(f"  - Created {len(pis_created)} PIs")
    print(f"  - Created {pos_created} POs")
    print(f"  - Each PI has 2 linked POs")
    print(f"  - Remaining quantity per SKU: ~30% of PI quantity")
    print(f"\n🔍 You can now test the PI → PO Mapping feature in the Customer Management module!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
