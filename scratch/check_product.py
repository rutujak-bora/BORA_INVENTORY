import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def check_product():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    p_dot = await db.products.find_one({"sku": "C91W6AT."})
    p_no_dot = await db.products.find_one({"sku": "C91W6AT"})
    
    print(f"Product with dot: {'Found' if p_dot else 'Not Found'}")
    if p_dot: print(f"  ID: {p_dot.get('id')}")
    
    print(f"Product without dot: {'Found' if p_no_dot else 'Not Found'}")
    if p_no_dot: print(f"  ID: {p_no_dot.get('id')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_product())
