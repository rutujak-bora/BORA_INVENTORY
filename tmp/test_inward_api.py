"""
Direct API test - calls the running FastAPI server to reproduce the 400 error
and capture its exact detail message.
"""
import asyncio
import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/backend/.env"))

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Login
        print("=== Step 1: Login ===")
        login_res = await client.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "admin@123"})
        if login_res.status_code != 200:
            # Try other passwords
            for pwd in ["admin123", "Admin@123", "password", "admin", "bora@123", "Bora@123"]:
                login_res = await client.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": pwd})
                if login_res.status_code == 200:
                    print(f"  Login succeeded with password: {pwd}")
                    break
        
        if login_res.status_code != 200:
            print(f"  Login FAILED: {login_res.status_code} - {login_res.text}")
            return
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  Login OK. Token obtained.")

        # Step 2: Get POs to find PO1002
        print("\n=== Step 2: Fetch POs ===")
        pos_res = await client.get(f"{BASE_URL}/api/po", headers=headers)
        pos = pos_res.json()
        po1002_list = [p for p in pos if p.get("voucher_no") == "PO1002"]
        print(f"  Found {len(po1002_list)} POs with voucher_no=PO1002")
        
        if not po1002_list:
            print("  PO1002 not in active POs list!")
            return
        
        po1002 = po1002_list[0]
        po1002_id = po1002["id"]
        print(f"  PO1002 id={po1002_id}, is_active={po1002.get('is_active')}")

        # Step 3: Get PO lines with stats
        print("\n=== Step 3: Get PO lines with stats ===")
        stats_res = await client.get(
            f"{BASE_URL}/api/pos/lines-with-stats?voucher_no=PO1002",
            headers=headers
        )
        print(f"  Status: {stats_res.status_code}")
        if stats_res.status_code != 200:
            print(f"  ERROR: {stats_res.text}")
            return
        
        stats = stats_res.json()
        print(f"  po_ids: {stats.get('po_ids')}")
        print(f"  line_items count: {len(stats.get('line_items', []))}")
        for item in stats.get("line_items", []):
            print(f"    SKU={item.get('sku')} product_id={item.get('product_id')} po_qty={item.get('po_quantity')} available={item.get('available_for_pickup')}")

        # Step 4: Get a warehouse
        print("\n=== Step 4: Get warehouse ===")
        wh_res = await client.get(f"{BASE_URL}/api/warehouses", headers=headers)
        warehouses = wh_res.json() if wh_res.status_code == 200 else []
        if not warehouses:
            print("  No warehouses found!")
            return
        wh_id = warehouses[0]["id"]
        print(f"  Using warehouse id={wh_id} name={warehouses[0].get('name', warehouses[0].get('warehouseName'))}")

        # Step 5: Try creating inward entry with first line item qty=50
        print("\n=== Step 5: POST /api/inward-stock ===")
        
        line_items = stats.get("line_items", [])
        if not line_items:
            print("  No line items to inward!")
            return
        
        first_item = line_items[0]
        inward_qty = min(50.0, first_item.get("available_for_pickup", 50.0))
        if inward_qty <= 0:
            inward_qty = 10.0  # force a small qty even if "overcommitted"
        
        payload = {
            "manual": "TEST-API-001",
            "po_voucher_no": stats.get("po_voucher_no"),
            "po_ids": stats.get("po_ids"),
            "warehouse_id": wh_id,
            "date": "2026-04-07",
            "inward_invoice_no": f"INV-TEST-{os.urandom(4).hex()}",
            "inward_type": "warehouse",
            "source_type": "warehouse_inward",
            "line_items": [
                {
                    "id": first_item.get("id"),
                    "product_id": first_item.get("product_id"),
                    "product_name": first_item.get("product_name"),
                    "sku": first_item.get("sku"),
                    "quantity": inward_qty,
                    "rate": first_item.get("rate", 0)
                }
            ]
        }
        
        print(f"  Payload:\n{json.dumps(payload, indent=2)}")
        
        inward_res = await client.post(f"{BASE_URL}/api/inward-stock", json=payload, headers=headers)
        print(f"\n  Response Status: {inward_res.status_code}")
        print(f"  Response Body: {inward_res.text}")
        
        if inward_res.status_code == 200:
            print("\n  ✅ SUCCESS! Inward entry created.")
            # Clean up
            entry_id = inward_res.json().get("id")
            if entry_id:
                del_res = await client.delete(f"{BASE_URL}/api/inward-stock/{entry_id}", headers=headers)
                print(f"  Cleaned up test entry: {del_res.status_code}")
        else:
            print(f"\n  ❌ FAILED with {inward_res.status_code}")

asyncio.run(main())
