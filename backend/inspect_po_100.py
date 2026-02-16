
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
    
    print("Inspecting PO-100...")
    po = await db.purchase_orders.find_one({'voucher_no': 'PO-100'})
    if po:
        print(f"PO ID: {po.get('id')}")
        print(f"reference_pi_id: {po.get('reference_pi_id')}")
        print(f"reference_pi_ids: {po.get('reference_pi_ids')}")
    else:
        print("PO-100 not found")

if __name__ == "__main__":
    asyncio.run(check())
