import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    collections = ['purchase_orders', 'inward_stock', 'outward_stock', 'proforma_invoices', 'products']
    
    print("=== Checking for 'nan' or empty SKUs/ProductIDs ===\n")
    
    for coll_name in collections:
        coll = db[coll_name]
        
        # Check for string "nan" or null or empty in various fields
        if coll_name == 'products':
            nan_sku = await coll.count_documents({"sku": {"$in": ["nan", "None", "", None]}})
            print(f"Collection {coll_name:20}: {nan_sku} documents with bad SKU")
        else:
            # Check line items
            cursor = coll.find({"line_items": {"$exists": True}})
            total_bad_sku = 0
            total_bad_pid = 0
            async for doc in cursor:
                for item in doc.get("line_items", []):
                    sku = str(item.get("sku", "")).lower()
                    pid = str(item.get("product_id", "")).lower()
                    if sku in ["nan", "none", ""]:
                        total_bad_sku += 1
                    if pid in ["nan", "none", ""]:
                        total_bad_pid += 1
            print(f"Collection {coll_name:20}: {total_bad_sku} items with bad SKU, {total_bad_pid} items with bad ProductID")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
