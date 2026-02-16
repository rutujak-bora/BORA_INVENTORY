import motor.motor_asyncio
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def check_pnl_data():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME', 'bora_tech')]
    
    print("-" * 60)
    print("P&L DATA CHECK")
    print("-" * 60)
    
    # Check Export Invoices
    export_count = await db.outward_stock.count_documents({
        "dispatch_type": {"$in": ["export_invoice", "direct_export"]},
        "is_active": True
    })
    print(f"Export Invoices (Revenue Source): {export_count}")
    
    # Check Expenses
    expense_count = await db.expenses.count_documents({"is_active": True})
    print(f"Expense Records (Cost Source): {expense_count}")
    
    # Check Purchase Orders
    po_count = await db.purchase_orders.count_documents({"is_active": True})
    print(f"Purchase Orders (COGS Source): {po_count}")
    
    print("-" * 60)
    if export_count > 0:
        print("✅ Data exists for P&L calculation.")
    else:
        print("⚠️ No Export Invoices found. P&L Report will be empty.")

if __name__ == "__main__":
    asyncio.run(check_pnl_data())
