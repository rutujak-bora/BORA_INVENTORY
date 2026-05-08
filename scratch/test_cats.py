import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
mongo_db = client["bora_inventory_mongo"]

async def main():
    combined = []

    async def get_distinct_safe(collection, field):
        try:
            return await collection.distinct(field)
        except Exception as e:
            return []

    sources = [
        (mongo_db.products, "category"),
        (mongo_db.products, "Category"),
        (mongo_db.purchase_orders, "line_items.category"),
        (mongo_db.stock_tracking, "category"),
        (mongo_db.inward_stock, "line_items.category"),
    ]

    for coll, field in sources:
        results = await get_distinct_safe(coll, field)
        combined.extend(results)

    unique_cats = {
        c.strip().upper()
        for c in combined
        if c
        and isinstance(c, str)
        and c.strip()
        and c.lower() not in ["unknown", "nan", "none", "null", "undefined"]
    }

    sorted_cats = sorted(list(unique_cats))
    print([{"id": c, "name": c} for c in sorted_cats])

asyncio.run(main())
