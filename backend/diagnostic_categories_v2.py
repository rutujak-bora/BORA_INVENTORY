import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path


async def diagnose_categories():
    ROOT_DIR = Path(__file__).parent
    load_dotenv(ROOT_DIR / ".env")

    MONGO_URL = os.environ.get("MONGO_URL")
    DB_NAME = os.environ.get("DB_NAME")

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Database: {DB_NAME}")

    print("\nChecking products.distinct('category')...")
    p_cats = await db.products.distinct("category")
    print(f"Found: {p_cats}")

    print("\nChecking products.distinct('Category')...")
    p_cats_alt = await db.products.distinct("Category")
    print(f"Found: {p_cats_alt}")

    print("\nChecking purchase_orders.distinct('line_items.category')...")
    po_cats = await db.purchase_orders.distinct("line_items.category")
    print(f"Found: {po_cats if len(po_cats) < 10 else f'{len(po_cats)} items'}")
    if po_cats:
        print(f"Sample: {po_cats[:5]}")

    print("\nChecking stock_tracking.distinct('category')...")
    st_cats = await db.stock_tracking.distinct("category")
    print(f"Found: {st_cats if len(st_cats) < 10 else f'{len(st_cats)} items'}")
    if st_cats:
        print(f"Sample: {st_cats[:5]}")

    combined = p_cats + p_cats_alt + po_cats + st_cats
    print(f"\nTotal combined raw categories: {len(combined)}")

    unique_cats = {
        c.strip()
        for c in combined
        if c
        and isinstance(c, str)
        and c.strip()
        and c.lower() not in ["unknown", "nan", "none", "null"]
    }
    print(f"Unique cleaned categories: {len(unique_cats)}")
    print(f"Categories list: {sorted(list(unique_cats))}")


if __name__ == "__main__":
    asyncio.run(diagnose_categories())
