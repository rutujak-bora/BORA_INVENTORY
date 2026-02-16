
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def check():
    load_dotenv(Path('backend/.env'))
    MONGO_URL = os.environ.get('MONGO_URL')
    DB_NAME = os.environ.get('DB_NAME')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("Searching for company 'Bora Mobility LLP'...")
    company = await db.companies.find_one({'name': {'$regex': 'Bora Mobility', '$options': 'i'}})
    if company:
        print(f"Company Found: ID={company.get('id')}, Name='{company.get('name')}'")
    else:
        print("Company not found")

if __name__ == "__main__":
    asyncio.run(check())
