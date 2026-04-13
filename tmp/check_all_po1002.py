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
    
    keyword = "PO1002"
    print(f"--- Detailed check for {keyword} ---")
    async for po in db.purchase_orders.find({"$or": [{"voucher_no": keyword}, {"po_no": keyword}, {"po_number": keyword}]}):
        print(f"PO ID: {po.get('id')}")
        print(f"  VoucherNo: {po.get('voucher_no')}")
        print(f"  IsActive: {po.get('is_active')}")
        print(f"  Items:")
        for item in po.get("line_items", []):
            print(f"    SKU: {item.get('sku')} | Qty: {item.get('quantity')} | ProdID: {item.get('product_id')}")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
