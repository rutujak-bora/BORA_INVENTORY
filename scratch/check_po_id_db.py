import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def check_po_id_db():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    inward = await db.inward_stock.find_one({"inward_invoice_no": "INW-1776949097321"})
    if inward:
        po_id = inward.get("po_id")
        print(f"PO ID in Inward: [{po_id}] | Repr: {repr(po_id)}")
    else:
        print("Inward not found")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_po_id_db())
