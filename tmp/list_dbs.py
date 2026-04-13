import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(url)
    dbs = await client.list_database_names()
    print("Databases:", dbs)
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
