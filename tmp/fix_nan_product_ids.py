import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(url)
    db = client[db_name]

    print("=== Fixing POs with product_id='nan' in line_items ===\n")

    fixed_count = 0
    async for po in db.purchase_orders.find({}):
        line_items = po.get("line_items", [])
        needs_update = False
        updated_items = []
        
        for item in line_items:
            product_id = item.get("product_id")
            sku = item.get("sku", "")
            
            # Fix nan values
            if str(product_id) in ("nan", "None", "null", "") or product_id is None:
                # Try to find product by SKU
                if sku and sku not in ("nan", "None", ""):
                    product = await db.products.find_one({"sku": sku}, {"_id": 0, "id": 1})
                    if product:
                        item["product_id"] = product["id"]
                        print(f"  Fixed PO {po.get('voucher_no')} item SKU={sku}: product_id set to {product['id']}")
                        needs_update = True
                    else:
                        print(f"  WARNING: Cannot fix PO {po.get('voucher_no')} item SKU={sku}: no product found in DB")
                else:
                    print(f"  WARNING: PO {po.get('voucher_no')} has nan product_id AND nan sku - skipping")
            
            updated_items.append(item)
        
        if needs_update:
            await db.purchase_orders.update_one(
                {"_id": po["_id"]},
                {"$set": {"line_items": updated_items}}
            )
            fixed_count += 1

    print(f"\n=== Fixed {fixed_count} POs with nan product_id ===")
    
    # Also verify PO1002 after fix
    po1002 = await db.purchase_orders.find_one({"voucher_no": "PO1002"})
    if po1002:
        print(f"\nPO1002 line items after fix:")
        for item in po1002.get("line_items", []):
            print(f"  SKU={item.get('sku')} product_id={item.get('product_id')} qty={item.get('quantity')}")

    client.close()
    print("\n=== DONE ===")

if __name__ == "__main__":
    asyncio.run(run())
