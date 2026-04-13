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
    
    out_file = Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/tmp/po1002_all_details.txt")
    with open(out_file, "w") as f:
        keyword = "PO1002"
        f.write(f"--- Detailed check for {keyword} ---\n")
        async for po in db.purchase_orders.find({"$or": [{"voucher_no": keyword}, {"po_no": keyword}, {"po_number": keyword}]}):
            f.write(f"PO ID: {po.get('id')}\n")
            f.write(f"  VoucherNo: {po.get('voucher_no')}\n")
            f.write(f"  PoNo: {po.get('po_no')}\n")
            f.write(f"  IsActive: {po.get('is_active')}\n")
            f.write(f"  LineItems:\n")
            for item in po.get("line_items", []):
                f.write(f"    - SKU: {item.get('sku')} | Qty: {item.get('quantity')} | ProdID: {item.get('product_id')} | ID: {item.get('id')}\n")
            f.write("\n")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
