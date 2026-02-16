import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def get_summary():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Fetching Stock Summary...")
    
    # Simulate get_stock_summary logic
    query = {}
    pending_in_transit = {}
    async for pickup in db.pickup_in_transit.find({"is_active": True, "is_inwarded": {"$ne": True}}):
        for item in pickup.get("line_items", []):
            sku = item.get("sku")
            if sku:
                pending_in_transit[sku] = pending_in_transit.get(sku, 0) + float(item.get("quantity", 0))

    stock_entries = []
    async for stock in db.stock_tracking.find(query):
        # Only show today's or relevant entries to keep output small
        if stock.get("quantity_outward", 0) > 0:
            print(f"Product: {stock.get('product_name')}")
            print(f"  SKU: {stock.get('sku')}")
            print(f"  Inward: {stock.get('quantity_inward')}")
            print(f"  Outward: {stock.get('quantity_outward')}")
            print(f"  Remaining: {stock.get('remaining_stock')}")
            print(f"  Last Updated: {stock.get('last_updated')}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(get_summary())
