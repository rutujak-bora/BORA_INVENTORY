import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import json

async def check_dropdown_data():
    ROOT_DIR = Path(__file__).parent
    load_dotenv(ROOT_DIR / '.env')
    
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    print(f"Connecting to: {DB_NAME}")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Check Collections
    collections = await db.list_collection_names()
    print(f"Collections: {collections}")
    
    # 1. Companies
    companies_count = await db.companies.count_documents({"is_active": True})
    print(f"Active Companies: {companies_count}")
    if companies_count > 0:
        sample = await db.companies.find_one({"is_active": True})
        print(f"Sample Company: {json.dumps(sample, default=str)}")
        
    # 2. Warehouses
    warehouses_count = await db.warehouses.count_documents({})
    print(f"Warehouses: {warehouses_count}")
    if warehouses_count > 0:
        sample = await db.warehouses.find_one({})
        print(f"Sample Warehouse: {json.dumps(sample, default=str)}")
        
    # 3. Products (for categories)
    p_cats = await db.products.distinct("category")
    p_cats_alt = await db.products.distinct("Category")
    print(f"Product Categories: {p_cats}")
    print(f"Product Categories (Alt): {p_cats_alt}")
    
    # 4. Stock Tracking (for categories)
    st_cats = await db.stock_tracking.distinct("category")
    print(f"Stock Tracking Categories: {st_cats}")

if __name__ == "__main__":
    asyncio.run(check_dropdown_data())
