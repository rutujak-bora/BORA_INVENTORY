import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def check_all_counts():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    cols = await db.list_collection_names()
    print(f"Counts in {DB_NAME}:")
    for col in cols:
        count = await db[col].count_documents({})
        print(f"  - {col}: {count}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_all_counts())
