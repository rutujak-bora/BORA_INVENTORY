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
    
    # Find a PO with multiple PIs
    print("Searching for POs with multiple reference PIs...")
    async for po in db.purchase_orders.find({"is_active": True, "$where": "this.reference_pi_ids ? this.reference_pi_ids.length > 1 : false"}):
        print(f"\n--- PO Voucher: {po.get('voucher_no')} ---")
        print(f"Linked PIs: {po.get('reference_pi_ids')}")
        for item in po.get('line_items', []):
             print(f"- SKU: {item.get('sku')} | Qty: {item.get('quantity')} | From PI: {item.get('pi_voucher_no')}")
             
if __name__ == "__main__":
    asyncio.run(check_data())
