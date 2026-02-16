import asyncio
from database import mongo_db

async def check_banks():
    banks = await mongo_db.banks.find({}).to_list(length=100)
    print(f"Found {len(banks)} banks")
    for bank in banks:
        print(f"ID: {bank.get('id')}, Name: {bank.get('bank_name')}")

if __name__ == "__main__":
    asyncio.run(check_banks())
