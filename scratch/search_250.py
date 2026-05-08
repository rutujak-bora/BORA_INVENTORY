import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def search_250_products():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("Searching for '250' products...")
    async for p in db.products.find({"name": {"$regex": "250", "$options": "i"}}).limit(20):
        print(f"Name: {p.get('name')} | SKU: {p.get('sku')} | ID: {p.get('id')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(search_250_products())
