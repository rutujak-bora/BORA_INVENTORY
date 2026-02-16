from database import mongo_db
import asyncio
import sys

async def debug_pi_stock():
    with open("stock_debug_results.txt", "w", encoding="utf-8") as f:
        voucher_no = "BMLP/25/PI/320"
        pi = await mongo_db.proforma_invoices.find_one({"voucher_no": voucher_no})
        if not pi:
            f.write(f"PI {voucher_no} not found\n")
            pi = await mongo_db.proforma_invoices.find_one({"voucher_no": {"$regex": voucher_no, "$options": "i"}})
            if not pi:
                f.write("PI not found even with regex\n")
                return
        
        f.write(f"PI Found: {pi['voucher_no']} (ID: {pi['id']})\n")
        pi_id = pi['id']
        
        f.write("\nProducts in PI:\n")
        for item in pi.get("line_items", []):
            f.write(f" - {item.get('product_name')} | SKU: {item.get('sku')} | ID: {item.get('product_id')} | Qty: {item.get('quantity')}\n")
        
        f.write(f"\nInward Entries for PI {pi_id}:\n")
        async for inward in mongo_db.inward_stock.find({"$or": [{"pi_id": pi_id}, {"pi_ids": pi_id}]}):
            f.write(f" - ID: {inward.get('id')} | Date: {inward.get('date')} | Type: {inward.get('inward_type')}\n")
            for item in inward.get("line_items", []):
                f.write(f"   * {item.get('product_name')} | SKU: {item.get('sku')} | ID: {item.get('product_id')} | Qty: {item.get('quantity')}\n")

        f.write("\nInward Entries for 'Canon Pixma MG2577S' (Global Search):\n")
        async for inward in mongo_db.inward_stock.find({"line_items.product_name": {"$regex": "Canon Pixma MG2577S", "$options": "i"}}):
            f.write(f" - ID: {inward.get('id')} | PI: {inward.get('pi_id')} | PIs: {inward.get('pi_ids')} | PO: {inward.get('po_id')}\n")
            for item in inward.get("line_items", []):
                if "Canon" in item.get('product_name', ''):
                    f.write(f"   * Name: {item.get('product_name')} | Qty: {item.get('quantity')} | SKU: {item.get('sku')} | ID: {item.get('product_id')}\n")

        f.write(f"\nOutward Entries for PI {pi_id}:\n")
        async for outward in mongo_db.outward_stock.find({"$or": [{"pi_id": pi_id}, {"pi_ids": pi_id}]}):
            f.write(f" - ID: {outward.get('id')} | Type: {outward.get('dispatch_type')} | Status: {outward.get('status')}\n")
            for item in outward.get("line_items", []):
                f.write(f"   * {item.get('product_name')} | Qty: {item.get('dispatch_quantity', item.get('quantity'))}\n")

if __name__ == "__main__":
    asyncio.run(debug_pi_stock())
