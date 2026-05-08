import requests
import json

# Try to hit the local server if it's running
# Actually, I don't know the port. server.py said 3000 in comments but it's FastAPI (usually 8000)

# Let's try to simulate the logic instead of hitting the API
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

async def test_ledger_logic():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Simulate get_pi_po_stock_ledger for one PI
    pi = await db.proforma_invoices.find_one({"is_active": True})
    if not pi:
        print("No PI found")
        return

    print(f"Testing ledger for PI: {pi.get('voucher_no')}")
    
    pi_id = pi['id']
    po_query = {
        "is_active": True,
        "$or": [
            {"reference_pi_id": pi_id},
            {"reference_pi_ids": pi_id}
        ]
    }
    pos = await db.purchase_orders.find(po_query).to_list(None)
    print(f"Found {len(pos)} linked POs")
    
    for pi_item in pi.get('line_items', []):
        sku = pi_item.get('sku')
        print(f"  Item: {sku} | PI Qty: {pi_item.get('quantity')}")
        
        linked_po_qty = 0
        for po in pos:
            for po_item in po.get('line_items', []):
                if po_item.get('sku') == sku:
                    linked_po_qty += po_item.get('quantity', 0)
        
        print(f"    Linked PO Qty: {linked_po_qty}")

    client.close()

if __name__ == "__main__":
    asyncio.run(test_ledger_logic())
