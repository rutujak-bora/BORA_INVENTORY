import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def check_db():
    load_dotenv('backend/.env')
    mongodb_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.bora_dms
    
    print("--- PI EXAMPLE ---")
    pi = await db.proforma_invoices.find_one({"is_active": True})
    if pi:
        for k, v in pi.items():
            if k != 'line_items':
                print(f"{k}: {v}")
            else:
                print(f"{k}: {len(v)} items, first item: {v[0] if v else 'None'}")
    
    print("\n--- PO EXAMPLE ---")
    po = await db.purchase_orders.find_one({"is_active": True})
    if po:
        for k, v in po.items():
            if k != 'line_items':
                print(f"{k}: {v}")
            else:
                print(f"{k}: {len(v)} items, first item: {v[0] if v else 'None'}")

if __name__ == "__main__":
    asyncio.run(check_db())
