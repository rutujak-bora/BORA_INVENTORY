import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def check_stock():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Checking DB: {DB_NAME}")

    # Get the latest outward stock entry
    latest_outward = await db.outward_stock.find_one(sort=[("created_at", -1)])
    if not latest_outward:
        print("No outward stock entries found.")
        return

    print("\nLATEST OUTWARD STOCK ENTRY:")
    print(f"ID: {latest_outward.get('id')}")
    print(f"Invoice No: {latest_outward.get('export_invoice_no')}")
    print(f"Type: {latest_outward.get('dispatch_type')}")
    print(f"Created At: {latest_outward.get('created_at')}")
    
    line_items = latest_outward.get('line_items', [])
    print(f"Line Items ({len(line_items)}):")
    product_ids = []
    for item in line_items:
        print(f"  - {item.get('product_name')} ({item.get('sku')}): Qty {item.get('quantity')}")
        product_ids.append(item.get('product_id'))

    # Check stock tracking for these products
    print("\nSTOCK TRACKING ENTRIES FOR THESE PRODUCTS:")
    cursor = db.stock_tracking.find({"product_id": {"$in": product_ids}})
    async for tracking in cursor:
        print(f"Product: {tracking.get('product_name')} ({tracking.get('sku')})")
        print(f"  Warehouse: {tracking.get('warehouse_name')}")
        print(f"  Inward: {tracking.get('quantity_inward')}")
        print(f"  Outward: {tracking.get('quantity_outward')}")
        print(f"  Remaining: {tracking.get('remaining_stock')}")
        print(f"  Last Outward Date: {tracking.get('last_outward_date')}")
        print("-" * 20)

    # Check Audit Logs
    print("\nRECENT AUDIT LOGS FOR OUTWARD STOCK:")
    cursor = db.audit_logs.find({"action": {"$regex": "outward", "$options": "i"}}, sort=[("timestamp", -1)])
    logs = await cursor.to_list(10)
    for log in logs:
        print(f"Action: {log.get('action')}, Entity ID: {log.get('entity_id')}, Timestamp: {log.get('timestamp')}")

if __name__ == "__main__":
    asyncio.run(check_stock())
