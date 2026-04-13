import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    warehouse = await db.warehouses.find_one({})
    if warehouse:
        print(f"Warehouse ID: {warehouse.get('id')} | Name: {warehouse.get('name')}")
    else:
        print("No warehouses found")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
