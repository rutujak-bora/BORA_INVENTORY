import motor.motor_asyncio
import asyncio
import os
from dotenv import load_dotenv

async def check_products():
    load_dotenv('backend/.env')
    mongo_url = os.getenv('MONGO_URL')
    db_name = os.getenv('DB_NAME')
    
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Check PI items
    pi_items = await db.proforma_invoices.distinct("line_items.sku")
    pi_cats = await db.proforma_invoices.distinct("line_items.category")
    
    # Check PO items
    po_items = await db.purchase_orders.distinct("line_items.sku")
    po_cats = await db.purchase_orders.distinct("line_items.category")
    
    print(f"PI SKUs found: {len(pi_items)}")
    print(f"PI Categories found: {len(pi_cats)}")
    print(f"PO SKUs found: {len(po_items)}")
    print(f"PO Categories found: {len(po_cats)}")
    
    # Check if we can see one example
    po = await db.purchase_orders.find_one()
    if po:
        print("PO Example Line Item:", po.get('line_items', [])[0] if po.get('line_items') else "No line items")

if __name__ == "__main__":
    asyncio.run(check_products())
