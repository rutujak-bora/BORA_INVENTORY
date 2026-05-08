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
    
    print("=== CHECKING USER IDs ===")
    async for user in db.users.find({}):
        if 'id' not in user:
            print(f"User {user.get('username')} is MISSING 'id' field!")
        else:
            print(f"User {user.get('username')} has 'id': {user['id']}")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
