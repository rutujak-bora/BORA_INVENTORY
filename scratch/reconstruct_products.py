import asyncio
import os
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone

async def run():
    backend_dir = Path("backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    print("=== RECONSTRUCTING PRODUCTS COLLECTION (V2) ===\n")
    
    product_map = {} # sku -> product_data
    
    collections = ['purchase_orders', 'inward_stock', 'outward_stock', 'proforma_invoices']
    
    for coll_name in collections:
        print(f"Scanning {coll_name}...")
        cursor = db[coll_name].find({"line_items": {"$exists": True}})
        async for doc in cursor:
            for item in doc.get("line_items", []):
                sku = str(item.get("sku", "")).strip()
                if not sku or sku.lower() in ("nan", "none"):
                    continue
                
                if sku not in product_map:
                    product_map[sku] = {
                        "id": str(uuid.uuid4()),
                        "sku": sku,         # Added for the existing index
                        "sku_name": sku,    # Used in models and some code
                        "product_name": item.get("product_name", sku),
                        "category": item.get("category", "Uncategorized"),
                        "brand": item.get("brand", "Unknown"),
                        "hsn_sac": item.get("hsn_sac", ""),
                        "is_active": True,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    # Merge info if current map has missing fields
                    p = product_map[sku]
                    if p["category"] == "Uncategorized" and item.get("category"):
                        p["category"] = item.get("category")
                    if p["brand"] == "Unknown" and item.get("brand"):
                        p["brand"] = item.get("brand")
                    if not p["hsn_sac"] and item.get("hsn_sac"):
                        p["hsn_sac"] = item.get("hsn_sac")

    new_products = list(product_map.values())
    print(f"\nFound {len(new_products)} unique products to insert.")
    
    if new_products:
        # Clear existing empty collection
        await db.products.delete_many({})
        # Insert all
        result = await db.products.insert_many(new_products)
        print(f"Successfully inserted {len(result.inserted_ids)} products.")
        
        # Now fix the line_items in all collections to point to these new IDs
        print("\n=== Updating transaction collections with new Product IDs ===")
        for coll_name in collections:
            fixed_count = 0
            cursor = db[coll_name].find({"line_items": {"$exists": True}})
            async for doc in cursor:
                line_items = doc.get("line_items", [])
                needs_update = False
                for item in line_items:
                    sku = str(item.get("sku", "")).strip()
                    if sku in product_map:
                        new_id = product_map[sku]["id"]
                        if item.get("product_id") != new_id:
                            item["product_id"] = new_id
                            needs_update = True
                            fixed_count += 1
                
                if needs_update:
                    await db[coll_name].update_one({"_id": doc["_id"]}, {"$set": {"line_items": line_items}})
            print(f"Updated {coll_name}: {fixed_count} line items fixed.")

    client.close()
    print("\n=== RECONSTRUCTION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(run())
