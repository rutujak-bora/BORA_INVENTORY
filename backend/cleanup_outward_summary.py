import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def cleanup_orphaned_outward():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"Cleaning up orphaned outward quantities...")
    
    # 1. Get all stock tracking entries with outward qty > 0
    cursor = db.stock_tracking.find({"quantity_outward": {"$gt": 0}})
    tracking_entries = await cursor.to_list(None)
    
    if not tracking_entries:
        print("No orphaned quantities found.")
        return

    # 2. Check if we have NO active outward entries (as per user request)
    active_outward_count = await db.outward_stock.count_documents({"is_active": True})
    
    if active_outward_count == 0:
        print(f"Verified: 0 active outward entries in database. Resetting ALL tracking outward quantities.")
        
        for e in tracking_entries:
            inward_qty = float(e.get("quantity_inward", 0))
            await db.stock_tracking.update_one(
                {"id": e.get("id")},
                {"$set": {
                    "quantity_outward": 0.0,
                    "remaining_stock": inward_qty,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "last_outward_date": None
                }}
            )
            print(f"  ✅ Reset {e.get('product_name')} (ID: {e.get('id')}): Outward 0, Remaining {inward_qty}")
    else:
        print(f"⚠️ Found {active_outward_count} active outward entries. Manual check required to avoid resetting legitimate data.")
        # In this case we would need to cross-ref, but the user says there are NONE.

if __name__ == "__main__":
    asyncio.run(cleanup_orphaned_outward())
