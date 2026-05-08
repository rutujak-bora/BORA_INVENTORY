import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

async def count_nan_skus():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    collections = ['purchase_orders', 'inward_stock', 'outward_stock', 'proforma_invoices']
    
    print(f"Checking for 'nan' SKUs in {DB_NAME}...")
    for coll_name in collections:
        coll = db[coll_name]
        
        # Check for literal string "nan" or actually missing/null that might be rendered as nan
        # In Mongo, we usually care about the string "nan" if it came from pandas
        query = {"line_items.sku": "nan"}
        count = await coll.count_documents(query)
        
        total = await coll.count_documents({})
        print(f" - {coll_name}: {count} docs with 'nan' SKU (out of {total} total)")
        
        if count > 0:
            # Show one example
            doc = await coll.find_one(query)
            for item in doc.get('line_items', []):
                if item.get('sku') == 'nan':
                    print(f"   Example Product: {item.get('product_name')}")
                    break

    client.close()

if __name__ == "__main__":
    asyncio.run(count_nan_skus())
