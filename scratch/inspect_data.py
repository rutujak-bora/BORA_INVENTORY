import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    print("=== INSPECTING BAD PO LINE ITEM ===")
    po = await db.purchase_orders.find_one({"line_items.product_id": {"$in": ["nan", "None", "", None]}})
    if po:
        print(f"PO Voucher No: {po.get('voucher_no')}")
        for item in po.get("line_items", []):
            pid = item.get("product_id")
            if str(pid).lower() in ("nan", "none", "") or pid is None:
                print(f"Bad Item: {item}")
                sku = item.get("sku")
                if sku:
                    print(f"Searching for SKU '{sku}' in products...")
                    p = await db.products.find_one({"sku_name": sku})
                    print(f"Result by 'sku_name': {p}")
                    p2 = await db.products.find_one({"sku": sku})
                    print(f"Result by 'sku': {p2}")
                    
                    # Try list all fields of one product
                    p_any = await db.products.find_one({})
                    print(f"Example product keys: {p_any.keys() if p_any else 'None'}")
                    if p_any:
                        print(f"Example product SKU value: {p_any.get('sku_name') or p_any.get('sku')}")
    else:
        print("No bad PO line items found with the query.")

    client.close()

if __name__ == "__main__":
    asyncio.run(run())
