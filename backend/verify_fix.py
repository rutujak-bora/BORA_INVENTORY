import motor.motor_asyncio
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def verify_outward_quantities():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME', 'bora_tech')]
    
    pis_to_check = ['BMLP/25/PI/304', 'BMLP/25/PI/320']
    
    print("-" * 60)
    print("VERIFICATION REPORT")
    print("-" * 60)

    for pi_no in pis_to_check:
        pi = await db.proforma_invoices.find_one({'voucher_no': pi_no})
        if not pi:
            print(f"XXX PI {pi_no} NOT FOUND")
            continue
            
        print(f"\nScanning PI: {pi_no} (ID: {pi['id']})")
        
        # 1. Build PI Product Map
        pi_products = {} # key: pid_sku -> {name, pi_qty, out_qty}
        for item in pi.get('line_items', []):
            pid = item.get('product_id') or ""
            sku = item.get('sku') or ""
            key = f"{pid}_{sku}"
            pi_products[key] = {
                'name': item.get('product_name'),
                'pi_qty': float(item.get('quantity', 0)),
                'out_qty': 0.0
            }

        # 2. Find Linked Outwards (Dispatch Plans + Export Invoices)
        outward_query = {
            "$or": [{"pi_id": pi["id"]}, {"pi_ids": pi["id"]}],
            "dispatch_type": {"$in": ["dispatch_plan", "export_invoice"]},
            "is_active": True
        }
        
        all_outwards = await db.outward_stock.find(outward_query).to_list(None)
        
        # 3. Deduplicate: Identify Dispatch Plans that have been invoiced
        invoiced_plan_ids = set()
        for out in all_outwards:
            if out.get("dispatch_type") == "export_invoice" and out.get("dispatch_plan_id"):
                invoiced_plan_ids.add(out.get("dispatch_plan_id"))
        
        # 4. Calculate Quantities
        count_used = 0
        for out in all_outwards:
            # Skip if it's a Dispatch Plan already covered by an Invoice
            if out.get("dispatch_type") == "dispatch_plan" and out.get("id") in invoiced_plan_ids:
                print(f"  [Skipping] Dispatch Plan {out['id']} (converted to invoice)")
                continue
                
            count_used += 1
            type_lbl = "Invoice" if out.get("dispatch_type") == "export_invoice" else "Plan"
            print(f"  [Counting] {type_lbl}: {out.get('export_invoice_no') or out.get('id')}")

            for item in out.get('line_items', []):
                o_pid = item.get('product_id') or ""
                o_sku = item.get('sku') or ""
                
                # Match logic
                match_key = f"{o_pid}_{o_sku}"
                if match_key not in pi_products:
                    # Fuzzy match fallback
                    found = None
                    for k in pi_products:
                        k_pid, k_sku = k.split('_')
                        if (o_pid and o_pid == k_pid) or (o_sku and o_sku == k_sku):
                            found = k
                            break
                    match_key = found
                
                if match_key:
                    qty = float(item.get("dispatch_quantity") or item.get("quantity", 0))
                    pi_products[match_key]['out_qty'] += qty

        # 5. Print Results
        print(f"  -> Processed {count_used} outward records.")
        print(f"\n  {'PRODUCT NAME':<30} | {'PI QTY':<10} | {'DISPATCHED':<10} | {'REMAINING':<10}")
        print("  " + "-"*70)
        
        for p in pi_products.values():
            rem = p['pi_qty'] - p['out_qty']
            print(f"  {p['name'][:30]:<30} | {p['pi_qty']:<10.1f} | {p['out_qty']:<10.1f} | {rem:<10.1f}")

if __name__ == "__main__":
    asyncio.run(verify_outward_quantities())
