import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def list_users():
    load_dotenv('backend/.env')
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print(f"Connecting to DB: {db_name}")
    users = await db.users.find({}, {"_id": 0, "hashed_password": 0}).to_list(length=None)
    
    print("\nList of Users:")
    print("-" * 50)
    for user in users:
        print(f"Username: {user.get('username')}")
        print(f"Email: {user.get('email')}")
        print(f"Role: {user.get('role')}")
        print(f"Section: {user.get('section')}")
        print(f"Active: {user.get('is_active', True)}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(list_users())
