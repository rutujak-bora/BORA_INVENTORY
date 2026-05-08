import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    print(f"=== Indexes for {db_name}.products ===")
    async for index in db.products.list_indexes():
        print(index)
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
