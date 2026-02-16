import motor.motor_asyncio
import asyncio
import os
from dotenv import load_dotenv

async def run():
    load_dotenv()
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME')]
    po = await db.purchase_orders.find_one({}, {"_id": 0})
    print(f"PO ID: {po.get('id')}")
    print(f"PO Voucher: {po.get('voucher_no')}")
    if po.get('line_items'):
        item = po['line_items'][0]
        print(f"Item Product ID: {item.get('product_id')}")
        print(f"Item SKU: {item.get('sku')}")

if __name__ == "__main__":
    asyncio.run(run())
