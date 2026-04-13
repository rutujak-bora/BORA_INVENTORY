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
    
    pos_file = Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/tmp/pos_all.txt")
    with open(pos_file, "w") as f:
        f.write("--- Listing all active POs ---\n")
        async for po in db.purchase_orders.find({"is_active": True}, {"voucher_no": 1, "po_no": 1, "id": 1, "status": 1}):
            vno = po.get('voucher_no') or po.get('po_no')
            f.write(f"PO: {vno} (ID: {po.get('id')}) Status: {po.get('status')}\n")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
