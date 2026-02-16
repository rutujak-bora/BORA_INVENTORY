import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def check_all_outward():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Checking all outward_stock entries for today...")
    cursor = db.outward_stock.find({"created_at": {"$regex": "^2026-02-16"}}, sort=[("created_at", 1)])
    entries = await cursor.to_list(None)
    
    print(f"Found {len(entries)} entries.")
    for e in entries:
        print(f"ID: {e.get('id')}, Invoice: {e.get('export_invoice_no')}, Created: {e.get('created_at')}, Total Qty: {sum(item.get('quantity', 0) for item in e.get('line_items', []))}")

if __name__ == "__main__":
    asyncio.run(check_all_outward())
