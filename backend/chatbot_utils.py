import os
import google.generativeai as genai
from database import mongo_db
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def get_document_details(voucher_no: str):
    """
    Search for details of a specific Proforma Invoice (PI) or Purchase Order (PO) by its voucher number.
    Returns the items, total amount, buyer/supplier, and status.
    """
    return f"Searching for document {voucher_no}..."

def get_sku_stock_stats(sku_name: str):
    """
    Get the stock statistics for a specific SKU.
    Returns total inward quantity, total outward quantity, and remaining stock.
    """
    return f"Calculating stock for SKU {sku_name}..."

async def tool_get_document_details(voucher_no: str):
    """Async implementation of document search"""
    pi = await mongo_db.proforma_invoices.find_one({"voucher_no": voucher_no, "is_active": True}, {"_id": 0})
    if pi:
        items = pi.get("line_items", [])
        total = sum(item.get("amount", 0) for item in items)
        return {
            "type": "Proforma Invoice",
            "voucher_no": voucher_no,
            "date": pi.get("date"),
            "buyer": pi.get("buyer"),
            "status": pi.get("status"),
            "total_amount": total,
            "item_count": len(items),
            "items": [{"sku": i.get("sku"), "qty": i.get("quantity"), "rate": i.get("rate")} for i in items]
        }
    
    po = await mongo_db.purchase_orders.find_one({"voucher_no": voucher_no, "is_active": True}, {"_id": 0})
    if po:
        items = po.get("line_items", [])
        total = sum(item.get("amount", 0) for item in items)
        return {
            "type": "Purchase Order",
            "voucher_no": voucher_no,
            "date": po.get("date"),
            "supplier": po.get("supplier"),
            "status": po.get("status"),
            "total_amount": total,
            "item_count": len(items),
            "items": [{"sku": i.get("sku"), "qty": i.get("quantity"), "rate": i.get("rate")} for i in items]
        }
    
    return {"error": f"No active PI or PO found with number {voucher_no}"}

async def tool_get_sku_stock_stats(sku_name: str):
    """Async implementation of SKU statistics aggregation"""
    inward_pipeline = [
        {"$match": {"line_items.sku": sku_name, "is_active": True}},
        {"$unwind": "$line_items"},
        {"$match": {"line_items.sku": sku_name}},
        {"$group": {"_id": None, "total_qty": {"$sum": "$line_items.quantity"}}}
    ]
    inward_res = await mongo_db.inward_stock.aggregate(inward_pipeline).to_list(1)
    total_inward = inward_res[0]["total_qty"] if inward_res else 0

    outward_pipeline = [
        {"$match": {"line_items.sku": sku_name, "is_active": True}},
        {"$unwind": "$line_items"},
        {"$match": {"line_items.sku": sku_name}},
        {"$group": {"_id": None, "total_qty": {"$sum": "$line_items.quantity"}}}
    ]
    outward_res = await mongo_db.outward_stock.aggregate(outward_pipeline).to_list(1)
    total_outward = outward_res[0]["total_qty"] if outward_res else 0

    return {
        "sku": sku_name,
        "total_inward": total_inward,
        "total_outward": total_outward,
        "current_stock": total_inward - total_outward
    }

async def get_available_model():
    """Detect the best available model for the current API key"""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priority list
        preferred = ['models/gemini-1.5-flash', 'models/gemini-flash-latest', 'models/gemini-1.5-pro', 'models/gemini-pro']
        for p in preferred:
            if p in models:
                return p
        return models[0] if models else "gemini-1.5-flash"
    except:
        return "gemini-1.5-flash"

async def chat_with_bora_assistant(message: str, history: list = None):
    """
    Main entry point for the Gemini Chatbot.
    Handles the conversation flow and tool execution.
    """
    if not api_key:
        return {
            "text": "The Gemini API Key is missing. Please add 'GEMINI_API_KEY' to your environment variables.",
            "error": True
        }

    # Define tools for Gemini
    tools = [get_document_details, get_sku_stock_stats]
    model_name = await get_available_model()
    
    model = genai.GenerativeModel(
        model_name=model_name,
        tools=tools,
        system_instruction="""You are the Bora Mobility Inventory Assistant. 
        You help users find details about Proforma Invoices (PI), Purchase Orders (PO), and SKU stock levels.
        Always be professional, concise, and helpful. 
        If a user mentions a document number or SKU, use your tools to provide accurate data."""
    )

    chat = model.start_chat(history=history or [], enable_automatic_function_calling=False)
    
    try:
        response = chat.send_message(message)
        
        if response.candidates[0].content.parts[0].function_call:
            call = response.candidates[0].content.parts[0].function_call
            if call.name == "get_document_details":
                tool_result = await tool_get_document_details(call.args["voucher_no"])
            elif call.name == "get_sku_stock_stats":
                tool_result = await tool_get_sku_stock_stats(call.args["sku_name"])
            else:
                tool_result = {"error": "Unknown tool"}

            response = chat.send_message(
                genai.types.Content(
                parts=[genai.types.Part.from_function_response(
                    name=call.name,
                    response=tool_result
                )]
            ))

        return {
            "text": response.text,
            "history": [
                {"role": c.role, "parts": [{"text": p.text} for p in c.parts if p.text]}
                for c in chat.history
            ]
        }
    except Exception as e:
        logger.error(f"Chatbot Error: {str(e)}")
        return {"text": f"I encountered an error: {str(e)}", "error": True}
