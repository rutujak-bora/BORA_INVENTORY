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
        pi_products = {item.get('product_id'): item.get('product_name') for item in pi.get('line_items', [])}
        print(f"PI 304 Products: {pi_products}")
            
        outwards = await db.outward_stock.find({'pi_ids': pi['id']}).to_list(100)
        for o in outwards:
            print(f"Outward {o['id']} ({o.get('dispatch_type')}):")
            for item in o.get('line_items', []):
                pid = item.get('product_id')
                sku = item.get('sku')
                name = item.get('product_name')
                print(f"  Item: {name}, PID: {pid}, SKU: {sku}")

if __name__ == "__main__":
    asyncio.run(run())
