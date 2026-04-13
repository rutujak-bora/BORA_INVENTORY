import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def run():
    backend_dir = Path("c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/backend")
    load_dotenv(backend_dir / ".env")
    
    url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    client = AsyncIOMotorClient(url)
    db = client[db_name]
    
    search_val = "PO1002"
    colls = await db.list_collection_names()
    
    print(f"Searching for '{search_val}' across all collections...")
    for coll_name in colls:
        coll = db[coll_name]
        # Search in common fields
        count = await coll.count_documents({
            "$or": [
                {"id": search_val},
                {"voucher_no": search_val},
                {"po_no": search_val},
                {"po_number": search_val},
                {"reference_no": search_val}
            ]
        })
        if count > 0:
            print(f"Found in collection '{coll_name}': {count} documents")
            doc = await coll.find_one({"$or": [{"voucher_no": search_val}, {"po_no": search_val}, {"po_number": search_val}]})
            if doc:
                print(f"  Sample ID: {doc.get('id')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
