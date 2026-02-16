import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def dump_ids():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Dumping all outward_stock IDs...")
    cursor = db.outward_stock.find({}, {"id": 1, "export_invoice_no": 1, "is_active": 1})
    entries = await cursor.to_list(None)
    
    for e in entries:
        print(f"ID: {e.get('id')}, Invoice: {e.get('export_invoice_no')}, Active: {e.get('is_active')}")

if __name__ == "__main__":
    asyncio.run(dump_ids())
