import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

async def fix_nan_skus():
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
    
    # 2. Update records
    for coll_name in collections:
        coll = db[coll_name]
        cursor = coll.find({"line_items.sku": "nan"})
        updated_count = 0
        
        async for doc in cursor:
            line_items = doc.get('line_items', [])
            modified = False
            for item in line_items:
                if item.get('sku') == 'nan':
                    name = item.get('product_name')
                    if name in name_to_sku:
                        item['sku'] = name_to_sku[name]
                        # Also fix product_id if it's 'nan'
                        if item.get('product_id') == 'nan':
                            item['product_id'] = "" # Or leave as is, but SKU is more important
                        modified = True
            
            if modified:
                await coll.update_one({"_id": doc["_id"]}, {"$set": {"line_items": line_items}})
                updated_count += 1
                
        print(f" - {coll_name}: Updated {updated_count} documents.")

    client.close()

if __name__ == "__main__":
    asyncio.run(fix_nan_skus())
