import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv


async def main():
    load_dotenv("backend/.env")
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client[os.getenv("DB_NAME")]
    collections = await db.list_collection_names()
    print(f"Collections: {collections}")


if __name__ == "__main__":
    asyncio.run(main())
