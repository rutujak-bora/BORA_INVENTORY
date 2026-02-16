
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def check():
    load_dotenv(Path('backend/.env'))
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("Listing 4XX PIs...")
    pis = await db.proforma_invoices.find({'voucher_no': {'$regex': '4[0-9]{2}'}, 'is_active': True}).to_list(length=100)
    for pi in pis:
        print(f"Voucher: {pi.get('voucher_no')}, ID: {pi.get('id')}")

if __name__ == "__main__":
    asyncio.run(check())
