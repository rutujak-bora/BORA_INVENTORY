import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

async def find_sku_matches():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    collections = ['purchase_orders', 'inward_stock', 'outward_stock', 'proforma_invoices']
    
    # 1. Build a map of product_name -> sku from non-nan records
    name_to_sku = {}
    
    for coll_name in collections:
        async for doc in db[coll_name].find({"line_items.sku": {"$ne": "nan"}}):
            for item in doc.get('line_items', []):
                name = item.get('product_name')
                sku = item.get('sku')
                if name and sku and sku != 'nan':
                    name_to_sku[name] = sku
                    
    print(f"Built name-to-sku map with {len(name_to_sku)} products.")
    
    # 2. Check how many 'nan' records can be fixed
    for coll_name in collections:
        coll = db[coll_name]
        cursor = coll.find({"line_items.sku": "nan"})
        fixable = 0
        total_nan = 0
        async for doc in cursor:
            for item in doc.get('line_items', []):
                if item.get('sku') == 'nan':
                    total_nan += 1
                    if item.get('product_name') in name_to_sku:
                        fixable += 1
        print(f" - {coll_name}: {fixable} out of {total_nan} 'nan' line items are fixable using name matching.")

    client.close()

if __name__ == "__main__":
    asyncio.run(find_sku_matches())
