import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import json

async def check_user_structure():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    user = await db.users.find_one({})
    if user:
        if '_id' in user: del user['_id']
        # Don't print the actual hash if it's sensitive, but check the key name
        print(f"User keys: {list(user.keys())}")
        print(f"Username: {user.get('username')}")
    else:
        print("No users found")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_user_structure())
