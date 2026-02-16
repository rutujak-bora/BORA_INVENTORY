import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def check_mongo_info():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print(f"--- Company Collection Info ---")
    indexes = await db.companies.index_information()
    for name, details in indexes.items():
        print(f"Index: {name}, Details: {details}")
    
    count = await db.companies.count_documents({})
    print(f"Total entries: {count}")
    
    # Get one doc to see current fields
    sample = await db.companies.find_one({})
    if sample:
        sample.pop("_id", None)
        print(f"Sample Document Fields: {list(sample.keys())}")
        print(f"Sample Data: {json.dumps(sample, indent=2)}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_mongo_info())
