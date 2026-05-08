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
    
    print("=== UPDATING stock_tracking Product IDs ===\n")
    
    # Map sku -> product_id from the newly filled products collection
    product_map = {}
    async for p in db.products.find({}, {"sku_name": 1, "id": 1}):
        product_map[p["sku_name"]] = p["id"]
        
    fixed_count = 0
    total_docs = 0
    async for doc in db.stock_tracking.find({}):
        total_docs += 1
        sku = str(doc.get("sku", "")).strip()
        if sku in product_map:
            new_id = product_map[sku]
            if doc.get("product_id") != new_id:
                await db.stock_tracking.update_one({"_id": doc["_id"]}, {"$set": {"product_id": new_id}})
                fixed_count += 1
                
    print(f"Finished stock_tracking: Updated {fixed_count} docs out of {total_docs}.")
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
