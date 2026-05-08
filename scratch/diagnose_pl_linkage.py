import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

async def diagnose_pl():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get recent export invoices
    print("--- Recent Export Invoices ---")
    async for inv in db.outward_stock.find({"is_active": True}).sort("date", -1).limit(5):
        print(f"No: {inv.get('export_invoice_no')} | Date: {inv.get('date')} | ID: {inv.get('id')}")
        pi_ids = inv.get("pi_ids", []) or ([inv.get("pi_id")] if inv.get("pi_id") else [])
        print(f"  Linked PI IDs: {pi_ids}")
        
        for item in inv.get("line_items", []):
            sku = item.get("sku")
            print(f"  Item: {sku} | Qty: {item.get('quantity')} | Rate: {item.get('rate')}")
            
            # Try to find a PO for this SKU and PI IDs
            po_query = {
                "is_active": True,
                "$or": [
                    {"reference_pi_id": {"$in": pi_ids}},
                    {"reference_pi_ids": {"$in": pi_ids}}
                ],
                "line_items.sku": sku
            }
            po = await db.purchase_orders.find_one(po_query)
            if po:
                # Find the rate in PO line items
                po_rate = 0
                for po_item in po.get("line_items", []):
                    if po_item.get("sku") == sku:
                        po_rate = po_item.get("rate")
                        break
                print(f"    [MATCH] Found in PO {po.get('voucher_no')} | Purchase Rate: {po_rate}")
            else:
                # Try global search for this SKU in any PO
                global_po = await db.purchase_orders.find_one({"is_active": True, "line_items.sku": sku})
                if global_po:
                    po_rate = 0
                    for po_item in global_po.get("line_items", []):
                        if po_item.get("sku") == sku:
                            po_rate = po_item.get("rate")
                            break
                    print(f"    [FALLBACK] Found in PO {global_po.get('voucher_no')} | Purchase Rate: {po_rate}")
                else:
                    print(f"    [MISSING] No PO found for SKU {sku}")
        print("-" * 30)

    client.close()

if __name__ == "__main__":
    asyncio.run(diagnose_pl())
