import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

async def find_product():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    name = "HP 255R G10 R5-7535U (CW0W6AT) (8/512GB)"
    p = await db.products.find_one({"sku_name": {"$regex": name, "$options": "i"}})
    if not p:
        p = await db.products.find_one({"name": {"$regex": name, "$options": "i"}})
        
    if p:
        print(f"Found Product: SKU={p.get('sku_name')} | Name={p.get('name')} | ID={p.get('id')}")
    else:
        print("Product not found by name")

    client.close()

if __name__ == "__main__":
    asyncio.run(find_product())
