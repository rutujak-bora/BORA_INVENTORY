import motor.motor_asyncio
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def run():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME', 'bora_tech')]
    
    # Check PI 304
    pi = await db.proforma_invoices.find_one({'voucher_no': 'BMLP/25/PI/304'})
    if pi:
        print(f"PI 304 ID: {pi['id']}")
        for item in pi.get('line_items', []):
            print(f"PI Item: {item.get('product_name')}, PID: {item.get('product_id')}, SKU: {item.get('sku')}, Qty: {item.get('quantity')}")
            
        outwards = await db.outward_stock.find({'pi_ids': pi['id'], 'is_active': True}).to_list(100)
        print(f"Found {len(outwards)} active outwards for PI 304")
        for o in outwards:
            print(f"Outward {o['id']} ({o.get('dispatch_type')}):")
            for item in o.get('line_items', []):
                print(f"  Item: {item.get('product_name')}, PID: {item.get('product_id')}, SKU: {item.get('sku')}, Qty: {item.get('dispatch_quantity') or item.get('quantity')}")

if __name__ == "__main__":
    asyncio.run(run())
