import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def search_product():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    p = await db.products.find_one({"name": {"$regex": "HP 250R G10 CORE-3", "$options": "i"}})
    if p:
        print(f"Found Product: {p.get('name')}")
        print(f"  SKU: [{p.get('sku')}]")
        print(f"  ID: {p.get('id')}")
    else:
        print("Product not found by name regex")

    client.close()

if __name__ == "__main__":
    asyncio.run(search_product())
