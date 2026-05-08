import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

async def list_collections():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    colls = await db.list_collection_names()
    print(f"Collections in {DB_NAME}:")
    for c in colls:
        count = await db[c].count_documents({})
        print(f" - {c}: {count} docs")

    client.close()

if __name__ == "__main__":
    asyncio.run(list_collections())
