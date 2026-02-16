import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def check_all():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Checking ALL outward entries for BMLEXRP26-41 (including inactive)...")
    cursor = db.outward_stock.find({"export_invoice_no": "BMLEXRP26-41"})
    entries = await cursor.to_list(None)
    
    for e in entries:
        print(f"ID: {e.get('id')}, Active: {e.get('is_active')}, Created: {e.get('created_at')}")

if __name__ == "__main__":
    asyncio.run(check_all())
