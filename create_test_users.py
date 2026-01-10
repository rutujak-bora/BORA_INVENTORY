#!/usr/bin/env python3
"""
Create test users for PO testing
"""

import asyncio
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import os

# MongoDB setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'bora_inventory_mongo')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_test_users():
    """Create test users for authentication testing"""
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Test users to create
    test_users = [
        {
            "id": str(uuid.uuid4()),
            "username": "rutuja@bora.tech",
            "email": "rutuja@bora.tech",
            "hashed_password": pwd_context.hash("boratech123"),
            "role": "admin",
            "section": "all_companies",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "username": "rkn@bora.tech",
            "email": "rkn@bora.tech", 
            "hashed_password": pwd_context.hash("boratech123"),
            "role": "admin",
            "section": "dns",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Check if users already exist and create if not
    for user_data in test_users:
        existing_user = await db.users.find_one({"username": user_data["username"]})
        
        if existing_user:
            print(f"User {user_data['username']} already exists")
            # Update password in case it changed
            await db.users.update_one(
                {"username": user_data["username"]},
                {"$set": {
                    "hashed_password": user_data["hashed_password"],
                    "updated_at": user_data["updated_at"]
                }}
            )
            print(f"Updated password for {user_data['username']}")
        else:
            await db.users.insert_one(user_data)
            print(f"Created user {user_data['username']}")
    
    # List all users
    print("\nAll users in database:")
    async for user in db.users.find({}, {"_id": 0, "hashed_password": 0}):
        print(f"- {user['username']} ({user['role']}, {user['section']})")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_test_users())