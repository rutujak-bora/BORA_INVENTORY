import asyncio
from database import mongo_db

async def check_data():
    extra_payments = await mongo_db.pi_extra_payments.find({}).to_list(length=100)
    print(f"Found {len(extra_payments)} extra payments")
    for ep in extra_payments:
        print(ep)

if __name__ == "__main__":
    asyncio.run(check_data())
