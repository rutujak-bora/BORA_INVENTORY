import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def check_po_ids():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    po = await db.purchase_orders.find_one({"voucher_no": "PO-L02"})
    if po:
        print("PO Line Items:")
        for item in po.get("line_items", []):
            print(f"  * Product ID: [{item.get('product_id')}] | SKU: [{item.get('sku')}]")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_po_ids())
