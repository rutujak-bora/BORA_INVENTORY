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
    
    # List all databases
    dbs = await client.list_database_names()
    print(f"Databases: {dbs}")
    
    for db_name in dbs:
        if db_name in ['admin', 'local', 'config']: continue
        db = client[db_name]
        colls = await db.list_collection_names()
        print(f"\nDatabase: {db_name}")
        for coll_name in colls:
            count = await db[coll_name].count_documents({})
            print(f"  {coll_name:20}: {count} docs")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
