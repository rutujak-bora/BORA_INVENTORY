
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def check():
    load_dotenv(Path('backend/.env'))
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    results = []
    pis = await db.proforma_invoices.find({'voucher_no': {'$regex': '408'}, 'is_active': True}).to_list(length=10)
    for pi in pis:
        pi_info = {
            "voucher": pi.get("voucher_no"),
            "id": pi.get("id"),
            "company_id": pi.get("company_id"),
            "pos_referencing": []
        }
        pos = await db.purchase_orders.find({
            "$or": [
                {"reference_pi_id": pi.get("id")},
                {"reference_pi_ids": pi.get("id")}
            ],
            "is_active": True
        }).to_list(length=10)
        for po in pos:
            pi_info["pos_referencing"].append({
                "voucher": po.get("voucher_no"),
                "id": po.get("id"),
                "reference_pi_id": po.get("reference_pi_id"),
                "reference_pi_ids": po.get("reference_pi_ids")
            })
        results.append(pi_info)
    
    with open('pi_check_dump.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Dumped info to pi_check_dump.json")

if __name__ == "__main__":
    asyncio.run(check())
