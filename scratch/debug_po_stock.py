import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def check_po_stock():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # 1. Find the PO
    po = await db.purchase_orders.find_one({"voucher_no": "PO-L02"})
    if not po:
        print("PO-L02 not found")
        return
    
    po_id = po["id"]
    print(f"PO-L02 ID: {po_id}")
    
    # 2. Find inward stock for this PO
    inwards = await db.inward_stock.find({"po_id": po_id, "is_active": True}).to_list(None)
    print(f"Found {len(inwards)} inward entries for this PO")
    
    for inward in inwards:
        print(f"  - Inward {inward.get('inward_invoice_no')} | Warehouse: {inward.get('warehouse_id')}")
        for item in inward.get("line_items", []):
            print(f"    * Product ID: {item.get('product_id')} | SKU: {item.get('sku')} | Product: {item.get('product_name')} | Qty: {item.get('quantity')}")

    # 3. Find outward stock for this PO
    outwards = await db.outward_stock.find({
        "$or": [{"po_id": po_id}, {"po_ids": po_id}],
        "is_active": True,
        "status": {"$ne": "Cancelled"}
    }).to_list(None)
    print(f"Found {len(outwards)} outward entries for this PO")
    
    for outward in outwards:
        print(f"  - Outward {outward.get('export_invoice_no')} | Type: {outward.get('dispatch_type')}")
        for item in outward.get("line_items", []):
            print(f"    * Product ID: {item.get('product_id')} | SKU: {item.get('sku')} | Qty: {item.get('dispatch_quantity') or item.get('quantity')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_po_stock())
