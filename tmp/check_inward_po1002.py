import asyncio
import os
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
    
    po_ids = ["cfff630f-bba8-4ce2-9a70-5b6cceb0b0bb", "7fc26b9c-d38e-4ec7-9ea7-4c681c7fea5e"]
    
    print("--- Searching for existing inward entries for PO1002 IDs ---")
    for pid in po_ids:
        print(f"Checking PO ID: {pid}")
        async for inward in db.inward_stock.find({"po_id": pid, "is_active": True}):
            print(f"  Found Inward: {inward.get('id')} ({inward.get('inward_invoice_no')})")
            for item in inward.get("line_items", []):
                print(f"    Item SKU: {item.get('sku')} Qty: {item.get('quantity')}")
                
    print("\n--- Searching for existing pickups for PO1002 IDs ---")
    for pid in po_ids:
        print(f"Checking PO ID: {pid}")
        async for pickup in db.pickup_in_transit.find({"po_id": pid, "is_active": True, "is_inwarded": {"$ne": True}}):
            print(f"  Found Pickup: {pickup.get('id')}")
            for item in pickup.get("line_items", []):
                print(f"    Item SKU: {item.get('sku')} Qty: {item.get('quantity')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(run())
