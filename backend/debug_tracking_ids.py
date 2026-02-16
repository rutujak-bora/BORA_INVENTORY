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
        print(f"PI 304 ID: {pi['id']}")
        for item in pi.get('line_items', []):
            print(f"PI Item: {item.get('product_name')}, ID: {item.get('product_id')}, Qty: {item.get('quantity')}")
            
        outwards = await db.outward_stock.find({'pi_ids': pi['id']}).to_list(100)
        for o in outwards:
            print(f"Outward ID: {o['id']}, Type: {o.get('dispatch_type')}")
            for item in o.get('line_items', []):
                print(f"  Outward Item: {item.get('product_name')}, ID: {item.get('product_id')}, Qty: {item.get('dispatch_quantity') or item.get('quantity')}")

if __name__ == "__main__":
    asyncio.run(run())
