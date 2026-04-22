import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv


async def check_db():
    load_dotenv("backend/.env")
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        print("MONGO_URL not found in .env")
        return

    print(
        f"Connecting to: {mongo_url.split('@')[1] if '@' in mongo_url else 'unknown'}"
    )
    client = AsyncIOMotorClient(mongo_url)
    db = client.bora_inventory_mongo

    print("--- PI EXAMPLE ---")
    pi = await db.proforma_invoices.find_one({"is_active": True})
    if pi:
        for k, v in pi.items():
            if k != "line_items":
                print(f"{k}: {type(v).__name__} = {v}")
            else:
                print(
                    f"{k}: {len(v)} items, first item keys: {v[0].keys() if v else 'None'}"
                )
    else:
        print("No active PI found")

    print("\n--- PO EXAMPLE ---")
    po = await db.purchase_orders.find_one({"is_active": True})
    if po:
        for k, v in po.items():
            if k != "line_items":
                print(f"{k}: {type(v).__name__} = {v}")
            else:
                print(
                    f"{k}: {len(v)} items, first item keys: {v[0].keys() if v else 'None'}"
                )
    else:
        print("No active PO found")


if __name__ == "__main__":
    asyncio.run(check_db())
