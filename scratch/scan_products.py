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
    
    count = await db.products.count_documents({})
    print(f"Products count in {db_name}: {count}")
    
    # Try find all unique product names in purchase_orders to reconstruct products if needed
    print("=== Scanning POs for unique products ===")
    pipeline = [
        {"$unwind": "$line_items"},
        {"$group": {
            "_id": "$line_items.sku",
            "name": {"$first": "$line_items.product_name"},
            "category": {"$first": "$line_items.category"},
            "brand": {"$first": "$line_items.brand"},
            "hsn_sac": {"$first": "$line_items.hsn_sac"}
        }}
    ]
    cursor = db.purchase_orders.aggregate(pipeline)
    count_unique = 0
    async for doc in cursor:
        count_unique += 1
        if count_unique < 5:
            print(f"Found product: {doc}")
            
    print(f"Total unique products found in POs: {count_unique}")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
