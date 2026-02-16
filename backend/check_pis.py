
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

async def check_pis():
    ROOT_DIR = Path(__file__).parent
    load_dotenv(ROOT_DIR / '.env')
    
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    pis = await db.proforma_invoices.find({"is_active": True}).to_list(length=100)
    print(f"Found {len(pis)} active PIs")
    for pi in pis:
        print(f"ID: {pi.get('id')}, Voucher: {pi.get('voucher_no')}, Company: {pi.get('company_id')}")

if __name__ == "__main__":
    asyncio.run(check_pis())
