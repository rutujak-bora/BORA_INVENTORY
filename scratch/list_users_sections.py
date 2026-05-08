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
    
    print("=== USERS AND SECTIONS ===")
    async for user in db.users.find({}, {"username": 1, "section": 1, "role": 1, "is_active": 1}):
        print(f"User: {user.get('username'):15} | Section: {user.get('section'):15} | Role: {user.get('role'):10} | Active: {user.get('is_active')}")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
