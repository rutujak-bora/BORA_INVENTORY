import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = "c:/Users/Admin/Downloads/project/DMS/Bora_DMS-main1/backend"
sys.path.append(backend_path)

# Import the function (and satisfy its imports)
from server import create_inward_stock

async def reproduce():
    # Mock user
    current_user = {"id": "reproduction_test_user"}
    
    # Mock inward data (like the user's selected PO1002)
    # The user enters 300 Qty in the screenshot
    inward_data = {
        "manual": "REF-REPRO-001",
        "inward_invoice_no": "INV-REPRO-001",
        "date": "2026-04-07",
        "po_ids": ["cfff630f-bba8-4ce2-9a70-5b6cceb0b0bb"],
        "warehouse_id": "62898362-34fa-4578-8291-4c413247ac98",
        "inward_type": "warehouse",
        "source_type": "warehouse_inward",
        "line_items": [
            {
                "id": "item_id_not_used_yet", # Frontend usually sends something here
                "product_id": "nan", # This is what's in the DB!
                "product_name": "INSPIRON 5440",
                "sku": "INDINSP5440C3U-S1",
                "quantity": 300.0,
                "rate": 29500.0
            }
        ]
    }
    
    print("--- Starting reproduction attempt ---")
    try:
        result = await create_inward_stock(inward_data, current_user)
        print("Success! Created inward entry:", result)
    except Exception as e:
        print(f"FAILED with error: {str(e)}")
        if hasattr(e, "detail"):
            print(f"Error detail: {e.detail}")

if __name__ == "__main__":
    asyncio.run(reproduce())
