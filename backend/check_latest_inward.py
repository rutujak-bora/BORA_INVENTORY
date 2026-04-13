import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import json

async def run():
    load_dotenv()
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    
    print("--- LATEST INWARD ENTRIES ---")
    async for entry in db.inward_stock.find().sort("created_at", -1).limit(10):
        entry.pop("_id", None)
        print(f"ID: {entry.get('id')} | Date: {entry.get('date')} | Created: {entry.get('created_at')} | Type: {entry.get('inward_type')}")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
