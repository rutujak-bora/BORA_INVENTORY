
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def check():
    load_dotenv(Path('backend/.env'))
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("Searching for PI 408...")
    pi = await db.proforma_invoices.find_one({'voucher_no': {'$regex': '408'}, 'is_active': True})
    if pi:
        print(f"PI Found: {pi.get('voucher_no')}")
        for item in pi.get('line_items', []):
            print(f"  Item: {item.get('product_name')}, SKU: {item.get('sku')}, ProductID: {item.get('product_id')}")
        
        pi_id = pi.get('id')
        po_query = {
            "$or": [
                {"reference_pi_id": pi_id},
                {"reference_pi_ids": pi_id}
            ],
            "is_active": True
        }
        pos = await db.purchase_orders.find(po_query).to_list(length=10)
        print(f"Found {len(pos)} POs")
        for po in pos:
            print(f"PO Voucher: {po.get('voucher_no')}")
            for item in po.get('line_items', []):
                print(f"    Item: {item.get('product_name')}, SKU: {item.get('sku')}, ProductID: {item.get('product_id')}")
    else:
        print("PI not found")

if __name__ == "__main__":
    asyncio.run(check())
