import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def check_outward():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Checking outward_stock for BMLEXRP26-41...")
    cursor = db.outward_stock.find({"export_invoice_no": "BMLEXRP26-41"})
    entries = await cursor.to_list(None)
    
    print(f"Found {len(entries)} entries.")
    for e in entries:
        print(f"ID: {e.get('id')}, Created: {e.get('created_at')}")
        for item in e.get('line_items', []):
            print(f"  - {item.get('product_name')}: Qty {item.get('quantity')}")

if __name__ == "__main__":
    asyncio.run(check_outward())
