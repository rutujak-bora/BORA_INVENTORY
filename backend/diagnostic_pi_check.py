import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def check_db():
    load_dotenv('backend/.env')
    mongo_url = os.getenv("MONGO_URL")
    client = AsyncIOMotorClient(mongo_url)
    db = client.bora_inventory_mongo
    
    print("--- PI EXAMPLE ---")
    pi = await db.proforma_invoices.find_one({"is_active": True})
    if pi:
        for k, v in pi.items():
            print(f"{k}: {type(v).__name__} = {v}")
    else:
        print("No active PI found")

if __name__ == "__main__":
    asyncio.run(check_db())
