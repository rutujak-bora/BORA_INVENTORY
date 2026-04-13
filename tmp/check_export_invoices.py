import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('backend/.env')
db_url = os.getenv('MONGO_URL')
db_name = os.getenv('DB_NAME')

async def main():
    client = AsyncIOMotorClient(db_url)
    db = client[db_name]
    
    print("All dispatch types:", await db.outward_stock.distinct('dispatch_type'))
    print("Active dispatch types:", await db.outward_stock.distinct('dispatch_type', {'is_active': True}))
    
if __name__ == "__main__":
    asyncio.run(main())
