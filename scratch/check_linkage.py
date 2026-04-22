import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

async def check_data():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get a PI that has some POs
    print("--- Searching for linked data ---")
    po = await db.purchase_orders.find_one({"is_active": True, "reference_pi_ids": {"$not": {"$size": 0}}})
    
    if not po:
        print("No linked POs found. Checking direct reference...")
        po = await db.purchase_orders.find_one({"is_active": True, "reference_pi_id": {"$exists": True}})
        
    if po:
        print(f"PO Voucher: {po.get('voucher_no')}")
        print(f"Linked PIs: {po.get('reference_pi_ids') or po.get('reference_pi_id')}")
        print("\nPO Line Items Structure:")
        for item in po.get('line_items', []):
            print(f"- Product: {item.get('product_name')} | SKU: {item.get('sku')} | Qty: {item.get('quantity')} | Source PI: {item.get('pi_voucher_no')}")
            
        # Now find one of those PIs
        pi_id = (po.get('reference_pi_ids') or [po.get('reference_pi_id')])[0]
        pi = await db.proforma_invoices.find_one({"id": pi_id})
        if pi:
            print(f"\nTarget PI Voucher: {pi.get('voucher_no')}")
            print(f"Target PI ID: {pi.get('id')}")
    else:
        print("No data found to show an example.")

if __name__ == "__main__":
    asyncio.run(check_data())
