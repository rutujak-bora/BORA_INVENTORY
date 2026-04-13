import asyncio
import os
import json
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
    
    search_val = "PO1002"
    cursor = db.purchase_orders.find({
        "$or": [
            {"voucher_no": search_val},
            {"po_no": search_val},
            {"po_number": search_val}
        ]
    })
    
    async for doc in cursor:
        print(f"Found PO1002: ID={doc.get('id')} IsActive={doc.get('is_active')} Status={doc.get('status')} CompanyID={doc.get('company_id')}")
        # Print line items
        for item in doc.get("line_items", []):
            print(f"  Item: SKU={item.get('sku')} Qty={item.get('quantity')} ID={item.get('id')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
