import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def search_users(search_terms):
    load_dotenv('backend/.env')
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print(f"Searching for users: {', '.join(search_terms)}")
    
    results = []
    for term in search_terms:
        # Search case-insensitive
        cursor = db.users.find({
            "$or": [
                {"username": {"$regex": term, "$options": "i"}},
                {"email": {"$regex": term, "$options": "i"}}
            ]
        }, {"_id": 0, "hashed_password": 0})
        
        async for user in cursor:
            results.append(user)
    
    # De-duplicate
    unique_results = {u['id']: u for u in results}.values()
    
    if not unique_results:
        print("\nNo users found matching these terms.")
    else:
        print("\nMatching Users Found:")
        print("-" * 50)
        for user in unique_results:
            print(f"Username: {user.get('username')}")
            print(f"Email: {user.get('email')}")
            print(f"Role: {user.get('role')}")
            print(f"Section: {user.get('section')}")
            print(f"Active: {user.get('is_active', True)}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(search_users(['sunil', 'himanshu', 'athrav']))
