
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
    
    print("Searching for PI with voucher containing 408...")
    pi = await db.proforma_invoices.find_one({'voucher_no': {'$regex': '408'}, 'is_active': True})
    if pi:
        print(f"PI Found: ID={pi.get('id')}, Voucher={pi.get('voucher_no')}, CompanyID={pi.get('company_id')}")
        # Search for POs referencing this PI
        pi_id = pi.get('id')
        po_query = {
            "$or": [
                {"reference_pi_id": pi_id},
                {"reference_pi_ids": pi_id}
            ],
            "is_active": True
        }
        pos = await db.purchase_orders.find(po_query).to_list(length=10)
        print(f"Found {len(pos)} POs referencing this PI")
        for po in pos:
            print(f"PO Voucher: {po.get('voucher_no')}")
    else:
        print("PI not found")

if __name__ == "__main__":
    asyncio.run(check())
