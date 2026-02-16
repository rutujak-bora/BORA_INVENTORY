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
        # Check outwards linked to this PI
        outwards = await db.outward_stock.find({'pi_ids': pi['id']}).to_list(100)
        print(f"Number of outwards linked to PI 304: {len(outwards)}")
        for o in outwards:
            print(f"Outward ID: {o['id']}, Type: {o.get('dispatch_type')}, Items: {len(o.get('line_items', []))}")
            for item in o.get('line_items', []):
                print(f"  Item: {item.get('product_name')}, Qty: {item.get('dispatch_quantity') or item.get('quantity')}")
    else:
        print("PI 304 not found")

    # Check PI 320
    pi_320 = await db.proforma_invoices.find_one({'voucher_no': 'BMLP/25/PI/320'})
    if pi_320:
        print(f"PI 320 ID: {pi_320['id']}")
        outwards_320 = await db.outward_stock.find({'pi_ids': pi_320['id']}).to_list(100)
        print(f"Number of outwards linked to PI 320: {len(outwards_320)}")
    else:
        print("PI 320 not found")

if __name__ == "__main__":
    asyncio.run(run())
