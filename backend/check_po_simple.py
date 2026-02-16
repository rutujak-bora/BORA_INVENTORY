import motor.motor_asyncio
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def count_pos():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME', 'bora_tech')]
    count = await db.purchase_orders.count_documents({})
    print(f"PO Count: {count}")

if __name__ == "__main__":
    asyncio.run(count_pos())
