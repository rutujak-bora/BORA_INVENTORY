import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

async def cleanup_all_nan_strings():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    collections = ['purchase_orders', 'inward_stock', 'outward_stock', 'proforma_invoices', 'products', 'stock_tracking']
    
    print(f"Cleaning up 'nan' strings in {DB_NAME}...")
    for coll_name in collections:
        coll = db[coll_name]
        
        # Search for any document containing "nan" in line_items or other fields
        # This is a bit broad, but we'll focus on line_items first
        cursor = coll.find({"$or": [
            {"line_items.sku": "nan"},
            {"line_items.product_id": "nan"},
            {"line_items.category": "nan"},
            {"sku": "nan"},
            {"product_id": "nan"}
        ]})
        
        updated_count = 0
        async for doc in cursor:
            modified = False
            
            # Fix line_items
            if 'line_items' in doc:
                for item in doc['line_items']:
                    for key in ['sku', 'product_id', 'category', 'brand']:
                        if item.get(key) == 'nan':
                            item[key] = ""
                            modified = True
            
            # Fix top-level fields
            for key in ['sku', 'product_id', 'category', 'brand']:
                if doc.get(key) == 'nan':
                    doc[key] = ""
                    modified = True
            
            if modified:
                await coll.replace_one({"_id": doc["_id"]}, doc)
                updated_count += 1
                
        print(f" - {coll_name}: Cleaned up {updated_count} documents.")

    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup_all_nan_strings())
