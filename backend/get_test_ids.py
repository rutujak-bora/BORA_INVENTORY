import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def get_ids():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    company = await db.companies.find_one({"is_active": True})
    warehouse = await db.warehouses.find_one({"is_active": True})
    product = await db.products.find_one({"is_active": True})
    
    print(f"COMPANY_ID: {company.get('id')}")
    print(f"WAREHOUSE_ID: {warehouse.get('id')}")
    print(f"PRODUCT_ID: {product.get('id')}")
    print(f"PRODUCT_SKU: {product.get('sku_name')}")

if __name__ == "__main__":
    asyncio.run(get_ids())
