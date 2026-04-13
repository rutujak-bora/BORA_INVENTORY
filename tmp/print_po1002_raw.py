import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/backend")
    load_dotenv(backend_dir / ".env")
    
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    po = await db.purchase_orders.find_one({"voucher_no": "PO1002"})
    if po:
        # Convert ObjectId and other non-serializable to string
        po['_id'] = str(po['_id'])
        print(json.dumps(po, indent=2))
    else:
        print("PO1002 not found")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
