from database import mongo_db
import asyncio

async def check_po_links():
    pi_id = "ea3b9d65-489c-4064-b3bb-eaf37c2ff1f2"
    with open("po_links_debug.txt", "w", encoding="utf-8") as f:
        # PIs often have POs linked via the purchase_orders collection
        async for po in mongo_db.purchase_orders.find({"$or": [{"reference_pi_id": pi_id}, {"reference_pi_ids": pi_id}]}):
            f.write(f"PO linked to PI: {po['id']} ({po['voucher_no']})\n")

if __name__ == "__main__":
    asyncio.run(check_po_links())
