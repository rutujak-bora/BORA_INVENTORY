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
    
    # Reactivate the 9 export invoices
    res = await db.outward_stock.update_many(
        {'dispatch_type': 'export_invoice'},
        {'$set': {'is_active': True}}
    )
    
    print(f"Reactivated {res.modified_count} export invoices.")

if __name__ == "__main__":
    asyncio.run(main())
