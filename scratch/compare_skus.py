import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def compare_skus():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    po = await db.purchase_orders.find_one({"voucher_no": "PO-L02"})
    inward = await db.inward_stock.find_one({"po_id": po["id"]})
    
    po_sku = po['line_items'][0]['sku']
    inward_sku = inward['line_items'][0]['sku']
    
    print(f"PO SKU:     [{po_sku}] | Len: {len(po_sku)} | Repr: {repr(po_sku)}")
    print(f"Inward SKU: [{inward_sku}] | Len: {len(inward_sku)} | Repr: {repr(inward_sku)}")
    
    print(f"Match: {po_sku == inward_sku}")

    client.close()

if __name__ == "__main__":
    asyncio.run(compare_skus())
