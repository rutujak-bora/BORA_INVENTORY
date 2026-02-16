import asyncio
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from auth import get_password_hash
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def populate_users():
    # Connect to MongoDB
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'bora_inventory_mongo')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Drop existing users
    await db.users.delete_many({})
    print("✓ Cleared existing users")
    
    # Define users
    all_companies_users = [
        {"email": "rutuja@bora.tech", "password": "rutuja@123", "role": "admin"},
        {"email": "sunil@bora.tech", "password": "sunil@123", "role": "regular"},
        {"email": "atharva@bora.tech", "password": "atharva@123", "role": "regular"},
        {"email": "kritika@bora.tech", "password": "kritika@123", "role": "regular"},
        {"email": "himanshu@bora.tech", "password": "himanshu@123", "role": "regular"},
        {"email": "sayam@bora.tech", "password": "sayam@123", "role": "regular"},
        {"email": "bharat@bora.tech", "password": "bharat@123", "role": "regular"},
        {"email": "akansha@bora.tech", "password": "akansha@123", "role": "regular"},
    ]
    
    dns_users = [
        {"email": "rkn@bora.tech", "password": "rkn@123", "role": "regular"},
        {"email": "dyaneshwar@bora.tech", "password": "dyan@123", "role": "regular"},
        {"email": "shravni@bora.tech", "password": "shravni@123", "role": "regular"},
        {"email": "shreyash@bora.tech", "password": "shreyash@123", "role": "regular"},
        {"email": "rutuja@bora.tech", "password": "rutuja@123", "role": "admin"},  # Rutuja in both sections
    ]
    
    # Create All Companies Documentary users
    for user_data in all_companies_users:
        user_doc = {
            "id": str(uuid.uuid4()),
            "username": user_data["email"],
            "email": user_data["email"],
            "hashed_password": get_password_hash(user_data["password"]),
            "role": user_data["role"],
            "section": "all_companies",
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z"
        }
        await db.users.insert_one(user_doc)
        print(f"✓ Created user: {user_data['email']} (All Companies - {user_data['role']})")
    
    # Create DNS Documentary users
    for user_data in dns_users:
        # Check if user already exists in all_companies
        is_duplicate = any(u["email"] == user_data["email"] for u in all_companies_users)
        
        username = user_data["email"]
        email = user_data["email"]
        
        if is_duplicate:
            username = f"{user_data['email']}_dns"
            email = f"{user_data['email']}.dns"
            
        user_doc = {
            "id": str(uuid.uuid4()),
            "username": username,
            "email": email,
            "hashed_password": get_password_hash(user_data["password"]),
            "role": user_data["role"],
            "section": "dns",
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z"
        }
        await db.users.insert_one(user_doc)
        print(f"✓ Created user: {username} (DNS - {user_data['role']})")
    
    print("\n✅ All users created successfully!")
    print("\n📝 Login Credentials:")
    print("\n--- All Companies Documentary ---")
    for user_data in all_companies_users:
        print(f"  {user_data['email']} / {user_data['password']} ({user_data['role']})")
    print("\n--- DNS Documentary ---")
    for user_data in dns_users:
        print(f"  {user_data['email']} / {user_data['password']} ({user_data['role']})")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(populate_users())
