import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def check_entry():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    target_id = "38d77474-9c78-4b53-b797-8e7352c2e8a2"
    print(f"Checking outward entry {target_id}...")
    e = await db.outward_stock.find_one({"id": target_id})
    if e:
        print(f"Found! Invoice: {e.get('export_invoice_no')}, Active: {e.get('is_active')}, Created: {e.get('created_at')}")
    else:
        print("Not found in outward_stock.")

if __name__ == "__main__":
    asyncio.run(check_entry())
