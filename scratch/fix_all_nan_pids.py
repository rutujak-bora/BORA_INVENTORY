import asyncio
import os
import re
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def fix_collection(db, coll_name):
    print(f"--- Fixing {coll_name} ---")
    fixed_count = 0
    total_items = 0
    
    cursor = db[coll_name].find({"line_items": {"$exists": True}})
    async for doc in cursor:
        line_items = doc.get("line_items", [])
        needs_update = False
        
        for item in line_items:
            product_id = item.get("product_id")
            sku = item.get("sku", "")
            
            if str(product_id).lower() in ("nan", "none", "null", "") or product_id is None:
                if sku and str(sku).lower() not in ("nan", "none", ""):
                    # Try to find product by SKU (exact match first)
                    # Field name in MongoDB products collection is 'sku_name'
                    product = await db.products.find_one({"sku_name": sku}, {"_id": 0, "id": 1})
                    
                    if not product:
                        # Try case-insensitive search using escaped regex
                        escaped_sku = re.escape(str(sku))
                        product = await db.products.find_one({"sku_name": {"$regex": f"^{escaped_sku}$", "$options": "i"}}, {"_id": 0, "id": 1})
                    
                    # Try 'sku' field just in case
                    if not product:
                        product = await db.products.find_one({"sku": sku}, {"_id": 0, "id": 1})
                        
                    if product:
                        item["product_id"] = product["id"]
                        needs_update = True
                        fixed_count += 1
            total_items += 1
            
        if needs_update:
            await db[coll_name].update_one(
                {"_id": doc["_id"]},
                {"$set": {"line_items": line_items}}
            )
            
    print(f"Finished {coll_name}: Fixed {fixed_count} items out of {total_items} total items.")
    return fixed_count

async def run():
    backend_dir = Path("backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    collections = ['purchase_orders', 'inward_stock', 'outward_stock', 'proforma_invoices']
    
    total_fixed = 0
    for coll in collections:
        total_fixed += await fix_collection(db, coll)
        
    print(f"\n=== TOTAL ITEMS FIXED: {total_fixed} ===")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
