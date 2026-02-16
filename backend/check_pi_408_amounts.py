
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
    
    print("Inspecting PI 408 line items...")
    pi = await db.proforma_invoices.find_one({'voucher_no': {'$regex': '408'}, 'is_active': True})
    if pi:
        print(f"PI Voucher: {pi.get('voucher_no')}")
        total = 0
        for item in pi.get('line_items', []):
            qty = item.get('quantity', 0)
            rate = item.get('rate', 0)
            amount = item.get('amount', 0)
            print(f"  Item: {item.get('product_name')}, Qty: {qty}, Rate: {rate}, Amount: {amount}")
            total += float(amount or 0)
        print(f"Total calculated: {total}")
    else:
        print("PI not found")

if __name__ == "__main__":
    asyncio.run(check())
