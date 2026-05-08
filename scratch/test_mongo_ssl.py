import motor.motor_asyncio
import certifi
import os
import asyncio
from dotenv import load_dotenv

async def test():
    load_dotenv("backend/.env")
    url = os.environ.get("MONGO_URL")
    print(f"Testing connection with certifi: {certifi.where()}")
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(url, tlsCAFile=certifi.where())
        await client.admin.command('ping')
        print("Success with certifi!")
    except Exception as e:
        print(f"Failed with certifi: {e}")
        try:
            print("Trying with tlsAllowInvalidCertificates=True...")
            client = motor.motor_asyncio.AsyncIOMotorClient(url, tlsAllowInvalidCertificates=True)
            await client.admin.command('ping')
            print("Success with tlsAllowInvalidCertificates=True!")
        except Exception as e2:
            print(f"Failed again: {e2}")

if __name__ == "__main__":
    asyncio.run(test())
