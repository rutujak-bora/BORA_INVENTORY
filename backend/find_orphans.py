import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def find_70_outward():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Searching for products with non-zero outward quantities in Stock Summary...")
    
    # Check stock_tracking
    cursor = db.stock_tracking.find({"quantity_outward": {"$gt": 0}})
    entries = await cursor.to_list(None)
    
    if not entries:
        print("No outward quantities found in stock_tracking.")
        return

    total_sum = 0
    for e in entries:
        qty = e.get("quantity_outward", 0)
        total_sum += qty
        print(f"Product: {e.get('product_name')} | SKU: {e.get('sku')}")
        print(f"  Inward Invoice: {e.get('inward_invoice_no')}")
        print(f"  Outward Qty: {qty}")
        print(f"  Tracking ID: {e.get('id')}")
        print("-" * 20)
    
    print(f"Total outward units in tracking: {total_sum}")

    # Check outward_stock for active entries
    print("\nChecking active outward_stock entries...")
    cursor = db.outward_stock.find({"is_active": True})
    outward_entries = await cursor.to_list(None)
    
    if not outward_entries:
        print("No active outward stock entries found.")
    else:
        for oo in outward_entries:
            print(f"Outward ID: {oo.get('id')} | Invoice: {oo.get('export_invoice_no')} | Created: {oo.get('created_at')}")
            total_qty = sum(item.get('quantity', 0) or item.get('dispatch_quantity', 0) for item in oo.get('line_items', []))
            print(f"  Total Qty in this record: {total_qty}")

if __name__ == "__main__":
    asyncio.run(find_70_outward())
