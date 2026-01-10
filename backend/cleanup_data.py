"""
Data Cleanup Script
Removes all transactional data while preserving master data
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def cleanup_data():
    # Connect to MongoDB
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client.bora_inventory
    
    print("🧹 Starting data cleanup...")
    print("=" * 60)
    
    # Collections to clear (transactional data)
    collections_to_clear = [
        "performa_invoices",
        "purchase_orders",
        "inward_stock",
        "outward_stock",
        "stock_tracking",
        "payment_tracking"
    ]
    
    for collection_name in collections_to_clear:
        try:
            result = await db[collection_name].delete_many({})
            print(f"✅ Cleared {collection_name}: {result.deleted_count} documents deleted")
        except Exception as e:
            print(f"❌ Error clearing {collection_name}: {str(e)}")
    
    print("=" * 60)
    print("✅ Data cleanup completed!")
    print("\n📊 Master Data Preserved:")
    print("  - Companies")
    print("  - Products")
    print("  - Warehouses")
    print("  - Banks")
    print("  - Users")
    print("\n🔄 You can now start with fresh transactional data!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup_data())
