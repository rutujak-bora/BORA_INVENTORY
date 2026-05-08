import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def list_pos():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    pos = await db.purchase_orders.find({}, {"voucher_no": 1, "id": 1}).to_list(None)
    print(f"Found {len(pos)} POs total")
    for po in pos:
        print(f"PO: [{po.get('voucher_no')}] | ID: {po.get('id')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(list_pos())
