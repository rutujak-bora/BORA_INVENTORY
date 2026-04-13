import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from chatbot_utils import (
    tool_get_document_details,
    tool_search_documents_by_company,
    tool_get_stock_summary_by_category,
    tool_get_recent_transactions,
    tool_get_pending_documents,
    tool_get_sku_stock_stats
)
from database import mongo_db

async def test_tools():
    print("--- Testing Bora AI Tools ---")
    
    # 1. Search docs by company
    print("\n[1] Testing search_documents_by_company...")
    # Find a company name from DB first
    company = await mongo_db.companies.find_one({}, {"_id": 0, "name": 1})
    if company:
        name = company["name"]
        print(f"Searching for docs for: {name}")
        res = await tool_search_documents_by_company(name, "PI")
        print(f"PI Result: {res}")
        res = await tool_search_documents_by_company(name, "PO")
        print(f"PO Result: {res}")
    else:
        print("No companies found in DB to test search.")

    # 2. Category summary
    print("\n[2] Testing get_stock_summary_by_category...")
    product = await mongo_db.products.find_one({"category": {"$exists": True}, "is_active": True})
    if product:
        category = product["category"]
        print(f"Checking stock for category: {category}")
        res = await tool_get_stock_summary_by_category(category)
        print(f"Stock Summary: {res}")
    else:
        print("No products with categories found.")

    # 3. Recent transactions
    print("\n[3] Testing get_recent_transactions...")
    res = await tool_get_recent_transactions(limit=3)
    print(f"Recent Transactions: {res}")

    # 4. Pending documents
    print("\n[4] Testing get_pending_documents...")
    res = await tool_get_pending_documents("PI")
    print(f"Pending PIs: {res}")

    # 5. SKU stock stats
    print("\n[5] Testing get_sku_stock_stats...")
    sku_prod = await mongo_db.products.find_one({"sku_name": {"$exists": True}, "is_active": True})
    if sku_prod:
        sku = sku_prod["sku_name"]
        print(f"Checking stock for SKU: {sku}")
        res = await tool_get_sku_stock_stats(sku)
        print(f"SKU Stats: {res}")

if __name__ == "__main__":
    asyncio.run(test_tools())
