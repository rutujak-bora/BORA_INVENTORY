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
    
    print(f"Searching for 'sunil@bora.tech' in {db_name}.users...")
    user_by_username = await db.users.find_one({'username': 'sunil@bora.tech'})
    user_by_email = await db.users.find_one({'email': 'sunil@bora.tech'})
    
    print(f"By username: {user_by_username}")
    print(f"By email: {user_by_email}")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
