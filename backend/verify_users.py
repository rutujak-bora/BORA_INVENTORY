import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def check_users():
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    count = await db.users.count_documents({})
    print(f"Total users in MongoDB: {count}")
    
    async for user in db.users.find({}, {"_id": 0, "username": 1, "section": 1, "role": 1}):
        print(f"User: {user['username']}, Section: {user['section']}, Role: {user['role']}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_users())
