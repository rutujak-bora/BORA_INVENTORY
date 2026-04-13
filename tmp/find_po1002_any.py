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
    
    print("--- Searching for ANY PO with PO1002 ---")
    async for po in db.purchase_orders.find({"voucher_no": {"$regex": "PO1002"}}):
        print(f"ID: {po.get('id')} | Voucher: {po.get('voucher_no')} | IsActive: {po.get('is_active')} | Status: {po.get('status')}")
        for item in po.get("line_items", []):
            print(f"  Item: SKU={item.get('sku')} Qty={item.get('quantity')}")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
