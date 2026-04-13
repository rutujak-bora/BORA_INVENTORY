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
    
    user = await db.users.find_one({"username": "admin"})
    if user:
        print(f"User: {user.get('username')} | IsActive: {user.get('is_active')}")
    else:
        print("User admin not found")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
