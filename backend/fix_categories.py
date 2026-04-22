import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URL", "mongodb://localhost:27017")
print(f"Connecting to {MONGO_URI.split('@')[-1] if '@' in MONGO_URI else MONGO_URI}")
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_database() # Uses the DB from the connection string

async def fix_stock_tracking_categories():
    print("Fixing stock_tracking categories...")
    cursor = db.stock_tracking.find({"category": "Unknown"})
    count = 0
    updated = 0
    async for stock in cursor:
        count += 1
        product_id = stock.get("product_id")
        sku = stock.get("sku")
        
        category = "Unknown"
        
        # Try finding product by ID
        if product_id:
            product = await db.products.find_one({"id": product_id})
            if product:
                category = product.get("category") or product.get("Category") or "Unknown"
        
        # Try finding by SKU
        if category == "Unknown" and sku:
            product = await db.products.find_one({"sku": sku})
            if product:
                category = product.get("category") or product.get("Category") or "Unknown"
                
        # Try looking up from inward_stock
        if category == "Unknown" and stock.get("inward_entry_id"):
            inward = await db.inward_stock.find_one({"id": stock.get("inward_entry_id")})
            if inward:
                for item in inward.get("line_items", []):
                    if item.get("sku") == sku and item.get("category"):
                        category = item.get("category")
                        break
        
        # Try looking up from purchase_orders
        if category == "Unknown" and sku:
            po = await db.purchase_orders.find_one({"line_items.sku": sku})
            if po:
                for item in po.get("line_items", []):
                    if item.get("sku") == sku and item.get("category"):
                        category = item.get("category")
                        break
                        
        if category != "Unknown":
            await db.stock_tracking.update_one({"_id": stock["_id"]}, {"$set": {"category": category}})
            updated += 1
            print(f"Updated {sku} to {category}")
            
    print(f"Looked at {count} Unknown stocks, updated {updated} categories.")

if __name__ == "__main__":
    asyncio.run(fix_stock_tracking_categories())
