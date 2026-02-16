import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def check_today():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    today = "2026-02-16"
    print(f"Searching for outward entries on {today}...")

    cursor = db.outward_stock.find({"created_at": {"$regex": f"^{today}"}})
    entries = await cursor.to_list(None)
    
    print(f"Found {len(entries)} entries.")
    for e in entries:
        print(f"ID: {e.get('id')}, Invoice: {e.get('export_invoice_no')}, Type: {e.get('dispatch_type')}, Created: {e.get('created_at')}")
        for item in e.get('line_items', []):
            print(f"  - {item.get('product_name')}: Qty {item.get('quantity')}")
            
    # Check if there are any entries for the specific products in the image
    target_skus = ["Epson L130 (304)", "Epson L8050 (304)", "Epson EcoTank L1250"]
    print(f"\nChecking latest tracking for target SKUs...")
    for sku in target_skus:
        # Use regex to match SKU (flexible as per server.py logic)
        cursor = db.stock_tracking.find({"sku": {"$regex": f"^{sku}", "$options": "i"}})
        trackings = await cursor.to_list(None)
        print(f"\nSKU: {sku}")
        for t in trackings:
            print(f"  ID: {t.get('id')}, Warehouse: {t.get('warehouse_name')}")
            print(f"  Inward: {t.get('quantity_inward')}, Outward: {t.get('quantity_outward')}, Remaining: {t.get('remaining_stock')}")

if __name__ == "__main__":
    asyncio.run(check_today())
