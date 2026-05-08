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
    
    print("=== CHECKING COMPANIES ===")
    async for company in db.companies.find({}):
        print(f"Company: {company.get('name')} | ID: {company.get('id')}")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
