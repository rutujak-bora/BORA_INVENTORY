import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone

async def run():
    backend_dir = Path("backend")
    load_dotenv(backend_dir / ".env")
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    print("=== Checking Audit Logs for Errors ===\n")
    
    # Look for logs where action includes 'error' or 'failed'
    cursor = db.audit_logs.find({
        "$or": [
            {"action": {"$regex": "error", "$options": "i"}},
            {"action": {"$regex": "failed", "$options": "i"}},
            {"detail": {"$regex": "error", "$options": "i"}},
            {"message": {"$regex": "error", "$options": "i"}}
        ]
    }).sort("timestamp", -1).limit(20)
    
    count = 0
    async for log in cursor:
        print(f"Time: {log.get('timestamp')}")
        print(f"Action: {log.get('action')}")
        print(f"User ID: {log.get('user_id')}")
        print(f"Details: {log.get('detail') or log.get('message') or 'No details'}")
        print("-" * 30)
        count += 1
        
    if count == 0:
        print("No error logs found in audit_logs collection.")
    else:
        print(f"Found {count} recent error logs.")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
