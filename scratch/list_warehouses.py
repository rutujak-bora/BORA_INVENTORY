import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def list_warehouses():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    async for w in db.warehouses.find({}):
        print(f"Warehouse: {w.get('name')} | ID: {w.get('id')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(list_warehouses())
