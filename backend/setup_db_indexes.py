
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def setup_indexes():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "bora_dms")
    
    print(f"Connecting to MongoDB at {mongo_url}...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("Setting up indexes...")
    
    collections = {
        "stock_tracking": ["is_active", "sku", "warehouse_id", "product_id"],
        "proforma_invoices": ["is_active", "id", "voucher_no", "customer_id"],
        "purchase_orders": ["is_active", "id", "voucher_no", "reference_pi_ids", "reference_pi_id"],
        "inward_stock": ["is_active", "po_id", "inward_invoice_no"],
        "outward_stock": ["is_active", "pi_id", "pi_ids", "dispatch_type", "dispatch_plan_id"],
        "pickup_in_transit": ["is_active", "po_id", "is_inwarded"],
        "companies": ["id", "name"]
    }

    for coll_name, fields in collections.items():
        for field in fields:
            try:
                await db[coll_name].create_index([(field, 1)])
                print(f"Created index for {coll_name}.{field}")
            except Exception as e:
                print(f"Skipping {coll_name}.{field}: {e}")
    
    print("All possible indexes created!")
    client.close()

if __name__ == "__main__":
    asyncio.run(setup_indexes())
