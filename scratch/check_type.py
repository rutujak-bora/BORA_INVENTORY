import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def check_type():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    inward = await db.inward_stock.find_one({"po_id": "bd2d21e3-f0fb-4089-b84d-fc0713ab1595"})
    if inward:
        wh_id = inward.get("warehouse_id")
        print(f"Warehouse ID: [{wh_id}] | Type: {type(wh_id)}")
    else:
        print("Inward not found")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_type())
