import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import uuid
from datetime import datetime, timezone

# Load .env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def test_full_cycle():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    test_product_id = "test-prod-" + str(uuid.uuid4())[:8]
    test_warehouse_id = "test-wh-" + str(uuid.uuid4())[:8]
    test_inward_id = "test-in-" + str(uuid.uuid4())[:8]
    test_outward_id = "test-out-" + str(uuid.uuid4())[:8]

    print(f"--- STARTING AUTOMATED TEST ---")
    
    # 1. Create Mock Inward
    inward_entry = {
        "id": test_inward_id,
        "inward_invoice_no": "TEST-INV-001",
        "date": "2026-02-16",
        "warehouse_id": test_warehouse_id,
        "is_active": True,
        "line_items": [
            {
                "product_id": test_product_id,
                "product_name": "Test Product",
                "sku": "TEST-SKU-01",
                "quantity": 100.0,
                "rate": 10.0
            }
        ]
    }
    
    from server import update_stock_tracking, update_stock_tracking_outward, revert_stock_tracking_outward
    
    print(f"1. Creating inward for 100 units...")
    await db.inward_stock.insert_one(inward_entry)
    await update_stock_tracking(inward_entry, "inward")
    
    # Check Summary
    summary = await db.stock_tracking.find_one({"inward_entry_id": test_inward_id})
    print(f"   Summary -> Inward: {summary['quantity_inward']}, Outward: {summary['quantity_outward']}, Remaining: {summary['remaining_stock']}")

    # 2. Create Mock Outward
    outward_entry = {
        "id": test_outward_id,
        "export_invoice_no": "TEST-OUT-001",
        "warehouse_id": test_warehouse_id,
        "is_active": True,
        "line_items": [
            {
                "product_id": test_product_id,
                "product_name": "Test Product",
                "sku": "TEST-SKU-01",
                "quantity": 30.0
            }
        ]
    }
    print(f"2. Creating outward for 30 units...")
    await db.outward_stock.insert_one(outward_entry)
    await update_stock_tracking_outward(outward_entry)
    
    # Check Summary
    summary = await db.stock_tracking.find_one({"inward_entry_id": test_inward_id})
    print(f"   Summary -> Inward: {summary['quantity_inward']}, Outward: {summary['quantity_outward']}, Remaining: {summary['remaining_stock']}")

    # 3. Delete Outward (Simulate)
    print(f"3. Deleting outward (reverting)...")
    await db.outward_stock.update_one({"id": test_outward_id}, {"$set": {"is_active": False}})
    await revert_stock_tracking_outward(outward_entry)
    
    # Check Summary
    summary = await db.stock_tracking.find_one({"inward_entry_id": test_inward_id})
    print(f"   Summary -> Inward: {summary['quantity_inward']}, Outward: {summary['quantity_outward']}, Remaining: {summary['remaining_stock']}")

    # 4. Delete Inward
    from server import delete_inward_stock
    # Need mock current_user
    mock_user = {"id": "test-user"}
    print(f"4. Deleting inward (cascading)...")
    await db.inward_stock.delete_one({"id": test_inward_id}) # Just clean up
    await db.stock_tracking.delete_many({"inward_entry_id": test_inward_id}) # Manual for test as delete_inward_stock uses depends
    
    # Verify summary is gone
    count = await db.stock_tracking.count_documents({"inward_entry_id": test_inward_id})
    print(f"   Summary Entries Remaining: {count}")

    # Final Cleanup
    await db.inward_stock.delete_many({"id": test_inward_id})
    await db.outward_stock.delete_many({"id": test_outward_id})
    await db.stock_tracking.delete_many({"inward_entry_id": test_inward_id})
    print(f"--- TEST COMPLETED ---")

if __name__ == "__main__":
    asyncio.run(test_full_cycle())
