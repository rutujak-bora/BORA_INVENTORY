import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "bora_inventory_mongo")

async def check_audit():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("Recent product deletions in audit logs:")
    async for log in db.audit_logs.find({"collection": "products", "action": {"$regex": "delete", "$options": "i"}}).sort("timestamp", -1).limit(10):
        print(f"Timestamp: {log.get('timestamp')} | Action: {log.get('action')} | User: {log.get('user_email')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_audit())
