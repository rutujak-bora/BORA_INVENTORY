import sys
import os
import uuid
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient
from dotenv import load_dotenv

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

env_path = os.path.join(backend_dir, ".env")
load_dotenv(env_path)

from server import app
from auth import get_current_active_user

mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
db_name = os.environ.get("DB_NAME", "bora_inventory_mongo")


def test_local_outward_stock_creation():
    """
    Integration test: POST /api/outward-stock with dispatch_mode='Local'
    Verifies:
      1. HTTP 200 response
      2. Correct dispatch_mode / po_ids saved to MongoDB
      3. FIFO stock deduction (remaining_stock: 10 - 3 = 7)
    """
    test_user = {
        "id": "test-user-id-outward",
        "username": "test_user_outward",
        "role": "admin",
        "is_active": True,
    }
    app.dependency_overrides[get_current_active_user] = lambda: test_user

    try:
        with TestClient(app) as client:
            asyncio.run(run_test_logic(client))
    finally:
        app.dependency_overrides.clear()


async def run_test_logic(client):
    print("\n[START] Local Outward Stock Integration Test")

    db_client = AsyncIOMotorClient(mongo_url)
    mongo_db = db_client[db_name]

    test_id = str(uuid.uuid4())[:8]
    company_id = f"test-company-{test_id}"
    warehouse_id = f"test-warehouse-{test_id}"
    product_id = f"test-product-{test_id}"
    sku = f"TEST-SKU-{test_id}"
    po_id = f"test-po-{test_id}"
    stock_tracking_id = f"stock-tracking-{test_id}"
    created_outward_id = None

    try:
        # ------------------------------------------------------------------ #
        # Seed test data
        # ------------------------------------------------------------------ #
        await mongo_db.companies.insert_one(
            {"id": company_id, "name": f"Test Co {test_id}", "is_active": True}
        )
        await mongo_db.warehouses.insert_one(
            {"id": warehouse_id, "name": f"Test WH {test_id}", "is_active": True}
        )
        await mongo_db.products.insert_one(
            {
                "id": product_id,
                "name": f"Test Product {test_id}",
                "sku": sku,
                "is_active": True,
            }
        )
        await mongo_db.purchase_orders.insert_one(
            {
                "id": po_id,
                "voucher_no": f"PO-{test_id}",
                "po_number": f"PO-{test_id}",
                "company_id": company_id,
                "date": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                "line_items": [
                    {
                        "id": f"po-item-{test_id}",
                        "product_id": product_id,
                        "product_name": f"Test Product {test_id}",
                        "sku": sku,
                        "quantity": 10.0,
                        "rate": 100.0,
                        "amount": 1000.0,
                    }
                ],
            }
        )
        # Simulate inward stock tracking entry (10 units in warehouse)
        await mongo_db.stock_tracking.insert_one(
            {
                "id": stock_tracking_id,
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "sku": sku,
                "quantity_inward": 10.0,
                "quantity_outward": 0.0,
                "remaining_stock": 10.0,
                "rate": 100.0,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        print("[OK] Seed data inserted.")

        # ------------------------------------------------------------------ #
        # POST Local outward stock entry (dispatch 3 units)
        # ------------------------------------------------------------------ #
        payload = {
            "company_id": company_id,
            "warehouse_id": warehouse_id,
            "dispatch_mode": "Local",
            "dispatch_type": "dispatch_plan",
            "po_ids": [po_id],
            "date": datetime.now(timezone.utc).date().isoformat(),
            "mode": "Road",
            "line_items": [
                {
                    "product_id": product_id,
                    "product_name": f"Test Product {test_id}",
                    "sku": sku,
                    "dispatch_quantity": 3.0,
                    "rate": 120.0,
                    "amount": 360.0,
                }
            ],
        }

        response = client.post("/api/outward-stock", json=payload)

        assert response.status_code == 200, (
            f"Expected HTTP 200, got {response.status_code}. Body: {response.text}"
        )
        res_data = response.json()
        created_outward_id = res_data.get("id")
        print(f"[OK] POST /api/outward-stock returned 200. ID={created_outward_id}")

        # Verify response fields
        assert res_data["dispatch_mode"] == "Local", "dispatch_mode mismatch in response"
        assert res_data["po_ids"] == [po_id], "po_ids mismatch in response"
        assert len(res_data["line_items"]) == 1, "Expected 1 line item in response"
        assert res_data["line_items"][0]["quantity"] == 3.0, "Quantity mismatch in response"
        print("[OK] Response payload fields verified.")

        # ------------------------------------------------------------------ #
        # Verify MongoDB record
        # ------------------------------------------------------------------ #
        db_entry = await mongo_db.outward_stock.find_one({"id": created_outward_id})
        assert db_entry is not None, "Outward entry not found in MongoDB"
        assert db_entry["dispatch_mode"] == "Local", "dispatch_mode not persisted"
        assert db_entry["po_ids"] == [po_id], "po_ids not persisted"
        print("[OK] MongoDB outward_stock entry verified.")

        # ------------------------------------------------------------------ #
        # Verify FIFO stock deduction: 10 - 3 = 7
        # ------------------------------------------------------------------ #
        tracking = await mongo_db.stock_tracking.find_one({"id": stock_tracking_id})
        assert tracking is not None, "Stock tracking entry not found"
        remaining = float(tracking["remaining_stock"])
        assert remaining == 7.0, (
            f"Expected remaining_stock=7.0 after FIFO deduction, got {remaining}"
        )
        print(f"[OK] FIFO stock deduction verified: remaining_stock={remaining}")

        print("\n[PASS] All assertions passed.")

    finally:
        # ------------------------------------------------------------------ #
        # Cleanup
        # ------------------------------------------------------------------ #
        print("[CLEANUP] Removing test documents...")
        await mongo_db.companies.delete_many({"id": company_id})
        await mongo_db.warehouses.delete_many({"id": warehouse_id})
        await mongo_db.products.delete_many({"id": product_id})
        await mongo_db.purchase_orders.delete_many({"id": po_id})
        await mongo_db.stock_tracking.delete_many({"id": stock_tracking_id})
        if created_outward_id:
            await mongo_db.outward_stock.delete_many({"id": created_outward_id})
            await mongo_db.audit_logs.delete_many({"entity_id": created_outward_id})
        db_client.close()
        print("[CLEANUP] Done.")
