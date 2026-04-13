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
    
    print("--- Listing all active POs ---")
    async for po in db.purchase_orders.find({"is_active": True}, {"voucher_no": 1, "po_no": 1, "id": 1}):
        print(f"PO: {po.get('voucher_no') or po.get('po_no')} (ID: {po.get('id')})")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
