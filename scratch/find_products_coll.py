import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(url)
    
    dbs = await client.list_database_names()
    for db_name in dbs:
        db = client[db_name]
        colls = await db.list_collection_names()
        if 'products' in colls:
            count = await db['products'].count_documents({})
            print(f"Found 'products' in {db_name} with {count} docs")
            if count > 0:
                p = await db['products'].find_one({})
                print(f"Example product: {p}")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
