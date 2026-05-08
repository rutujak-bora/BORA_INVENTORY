import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import json

async def check_po():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    po = await db.purchase_orders.find_one({"is_active": True})
    if po:
        if '_id' in po: del po['_id']
        print(json.dumps(po, indent=2))
    else:
        print("No POs found")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_po())
