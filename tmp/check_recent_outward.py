import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('backend/.env')
db_url = os.getenv('MONGO_URL')
db_name = os.getenv('DB_NAME')

async def main():
    client = AsyncIOMotorClient(db_url)
    db = client[db_name]
    
    print("Most recent outward stock entries:")
    cursor = db.outward_stock.find({}).sort("created_at", -1).limit(10)
    async for doc in cursor:
        print(f"ID: {doc.get('id')}")
        print(f"  Voucher/Invoice No: {doc.get('voucher_no')} / {doc.get('export_invoice_no')}")
        print(f"  Dispatch Type: {doc.get('dispatch_type')}")
        print(f"  Is Active: {doc.get('is_active', 'NOT_SET')}")
        print(f"  Date: {doc.get('date')}")
        print(f"  Created At: {doc.get('created_at')}")
        print("-")

if __name__ == "__main__":
    asyncio.run(main())
