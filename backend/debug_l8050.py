import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def debug_tracking():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Checking stock_tracking for Epson L8050...")
    cursor = db.stock_tracking.find({"sku": {"$regex": "^Epson L8050", "$options": "i"}})
    entries = await cursor.to_list(None)
    
    for e in entries:
        print(f"ID: {e.get('id')}, Invoice: {e.get('inward_invoice_no')}, Inward: {e.get('quantity_inward')}, Outward: {e.get('quantity_outward')}, Remaining: {e.get('remaining_stock')}")

if __name__ == "__main__":
    asyncio.run(debug_tracking())
