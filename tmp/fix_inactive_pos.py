import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(url)
    db = client[db_name]

    print("=== FULL DIAGNOSIS ===\n")

    # 1. Show all inactive POs
    print("--- INACTIVE POs ---")
    async for po in db.purchase_orders.find({"is_active": False}, {"_id": 0, "voucher_no": 1, "id": 1, "status": 1}):
        print(f"  PO: {po.get('voucher_no')} | ID: {po.get('id')} | Status: {po.get('status')}")

    # 2. Check the test entry we just created and remove it
    print("\n--- CHECKING TEST INWARD ENTRY (ec6df742-...) ---")
    test_entry = await db.inward_stock.find_one({"id": "ec6df742-f219-4" + ""}, {"_id": 0})
    # Find reproduction entries
    async for e in db.inward_stock.find({"manual": "REF-REPRO-001"}, {"_id": 0, "id": 1, "manual": 1}):
        print(f"  Found test entry: {e.get('id')}")
        # Delete it
        await db.inward_stock.delete_one({"id": e.get("id")})
        # Also delete from stock_tracking
        await db.stock_tracking.delete_many({"inward_entry_id": e.get("id")})
        print(f"  Cleaned up test entry: {e.get('id')}")

    # 3. Fix all inactive POs - set is_active to True
    print("\n--- FIXING INACTIVE POs (setting is_active=True) ---")
    result = await db.purchase_orders.update_many(
        {"is_active": False},
        {"$set": {"is_active": True}}
    )
    print(f"  Updated {result.modified_count} POs to is_active=True")

    # 4. Verify
    count_active = await db.purchase_orders.count_documents({"is_active": True})
    count_inactive = await db.purchase_orders.count_documents({"is_active": False})
    print(f"\n  Active POs after fix: {count_active}")
    print(f"  Inactive POs after fix: {count_inactive}")

    # 5. Confirm PO1002 is now active
    po1002 = await db.purchase_orders.find_one({"voucher_no": "PO1002"}, {"_id": 0, "voucher_no": 1, "id": 1, "is_active": 1})
    if po1002:
        print(f"\n  PO1002 is_active: {po1002.get('is_active')}")
    else:
        print("\n  PO1002 not found")

    client.close()
    print("\n=== DONE ===")

if __name__ == "__main__":
    asyncio.run(run())
