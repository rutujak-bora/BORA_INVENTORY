import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def check_atharv():
    load_dotenv('backend/.env')
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Check for anything starting with 'ath'
    cursor = db.users.find({
        "username": {"$regex": "^ath", "$options": "i"}
    }, {"_id": 0, "hashed_password": 0})
    
    users = await cursor.to_list(length=None)
    
    if not users:
        print("No users found starting with 'ath'.")
    else:
        for u in users:
            print(u)

if __name__ == "__main__":
    asyncio.run(check_atharv())
