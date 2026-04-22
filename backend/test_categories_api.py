import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client.get_database()


async def test_categories():
    print("Testing categories logic...")
    categories = await db.products.distinct("category")
    categories_upper = await db.products.distinct("Category")
    po_categories = await db.purchase_orders.distinct("line_items.category")

    print(f"Products 'category': {categories}")
    print(f"Products 'Category': {categories_upper}")
    print(f"PO 'line_items.category': {po_categories}")

    all_cats = list(
        {
            c
            for c in categories + categories_upper + po_categories
            if c and isinstance(c, str) and c.strip() and c != "Unknown"
        }
    )
    all_cats.sort()

    results = [{"id": c, "name": c} for c in all_cats]
    print(f"Final results count: {len(results)}")
    print(f"First few results: {results[:5]}")


if __name__ == "__main__":
    asyncio.run(test_categories())
