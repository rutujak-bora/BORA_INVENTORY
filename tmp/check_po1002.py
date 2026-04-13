import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/backend")
    load_dotenv(backend_dir / ".env")
    
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    # 1. Check PO1002
    po_no = "PO1002"
    po = await db.purchase_orders.find_one({"voucher_no": po_no, "is_active": True})
    if not po:
        po = await db.purchase_orders.find_one({"po_no": po_no, "is_active": True})
        
    if not po:
        print(f"PO {po_no} not found!")
        return
        
    print(f"Found PO: {po.get('voucher_no')} (ID: {po.get('id')})")
    
    # 2. Check line items
    for item in po.get("line_items", []):
        print(f" SKU: {item.get('sku')} | ProductID: {item.get('product_id')} | Qty: {item.get('quantity')}")
        
    # 3. Check existing inward entries
    inward_entries = await db.inward_stock.find({"po_id": po.get('id'), "is_active": True}).to_list(None)
    print(f"Total already inwarded entries for this PO ID: {len(inward_entries)}")
    for i, entry in enumerate(inward_entries):
        for item in entry.get("line_items", []):
             print(f"  Entry {i} item: SKU={item.get('sku')} Qty={item.get('quantity')}")
             
    # 4. Check pickups
    pickups = await db.pickup_in_transit.find({"po_id": po.get('id'), "is_active": True, "is_inwarded": {"$ne": True}}).to_list(None)
    print(f"Total pickups (in transit) for this PO ID: {len(pickups)}")
    for i, p in enumerate(pickups):
         for item in p.get("line_items", []):
             print(f"  Pickup {i} item: SKU={item.get('sku')} Qty={item.get('quantity')}")
             
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
