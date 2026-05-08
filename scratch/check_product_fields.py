import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import json

async def check_product_fields():
    load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    p = await db.products.find_one({})
    if p:
        if '_id' in p: del p['_id']
        print(json.dumps(p, indent=2))
    else:
        print("No products found")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_product_fields())
