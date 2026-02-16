import motor.motor_asyncio
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def run():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME', 'bora_tech')]
    
    pi = await db.proforma_invoices.find_one({'voucher_no': 'BMLP/25/PI/304'})
    if pi:
        print("PI 304 First Item:", pi.get('line_items', [])[0] if pi.get('line_items') else "None")
            
    outwards = await db.outward_stock.find({'pi_ids': pi['id']}).to_list(1)
    if outwards:
        print("Outward First Item:", outwards[0].get('line_items', [])[0] if outwards[0].get('line_items') else "None")

if __name__ == "__main__":
    asyncio.run(run())
