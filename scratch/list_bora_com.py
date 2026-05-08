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
    
    db = client['bora_com']
    colls = await db.list_collection_names()
    print(f"Database: bora_com")
    for coll_name in colls:
        count = await db[coll_name].count_documents({})
        print(f"  {coll_name:20}: {count} docs")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
