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
    
    count_all = await db.purchase_orders.count_documents({})
    count_active = await db.purchase_orders.count_documents({"is_active": True})
    count_inactive = await db.purchase_orders.count_documents({"is_active": False})
    count_missing = await db.purchase_orders.count_documents({"is_active": {"$exists": False}})
    
    print(f"Total POs: {count_all}")
    print(f"Active POs: {count_active}")
    print(f"Inactive POs: {count_inactive}")
    print(f"Missing is_active field POs: {count_missing}")
    
    # List one missing if found
    if count_missing > 0:
        missing_po = await db.purchase_orders.find_one({"is_active": {"$exists": False}})
        print(f"Example PO with missing is_active field: Voucher={missing_po.get('voucher_no')}")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
