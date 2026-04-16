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
    Search for a specific document (Proforma Invoice or Purchase Order) by its voucher number.
    Returns the document details, status, and line items.
    """
    return f"Searching for document {voucher_no}..."

def search_documents_by_company(company_name: str, doc_type: str = "PI"):
    """
    Search for Proforma Invoices (PI) or Purchase Orders (PO) by company name.
    company_name: Part of the buyer or supplier name.
    doc_type: 'PI' for Proforma Invoice or 'PO' for Purchase Order.
    """
    return f"Searching for {doc_type}s for company {company_name}..."

def get_stock_summary_by_category(category: str):
    """
    Get the total stock summary for all SKUs within a specific category.
    Returns the total quantity available in that category.
    """
    return f"Calculating total stock for category {category}..."

def get_recent_transactions(limit: int = 5):
    """
    Get the most recent inward and outward stock transactions.
    """
    return f"Fetching the last {limit} transactions..."

def get_pending_documents(doc_type: str = "PI"):
    """
    List all pending Proforma Invoices (PI) or Purchase Orders (PO).
    """
    return f"Listing pending {doc_type}s..."

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

async def tool_search_documents_by_company(company_name: str, doc_type: str = "PI"):
    """Search documents by company name (buyer/supplier)"""
    query = {"is_active": True}
    collection = "proforma_invoices" if doc_type.upper() == "PI" else "purchase_orders"
    search_field = "buyer" if doc_type.upper() == "PI" else "supplier"
    
    query[search_field] = {"$regex": company_name, "$options": "i"}
    
    cursor = mongo_db[collection].find(query, {"_id": 0}).sort("date", -1).limit(5)
    docs = await cursor.to_list(length=5)
    
    if not docs:
        return {"message": f"No {doc_type}s found for company matching '{company_name}'"}
    
    return {
        "count": len(docs),
        "results": [{
            "voucher_no": d.get("voucher_no"),
            "date": d.get("date"),
            "company": d.get(search_field),
            "status": d.get("status")
        } for d in docs]
    }

async def tool_get_stock_summary_by_category(category: str):
    """Aggregate stock levels for all products in a category"""
    # 1. Find all SKUs in this category
    products = await mongo_db.products.find({"category": {"$regex": category, "$options": "i"}, "is_active": True}).to_list(None)
    if not products:
        return {"error": f"No products found in category '{category}'"}
    
    skus = [p["sku_name"] for p in products]
    
    # 2. Sum inward and outward for these SKUs
    inward_pipeline = [
        {"$match": {"line_items.sku": {"$in": skus}, "is_active": True}},
        {"$unwind": "$line_items"},
        {"$match": {"line_items.sku": {"$in": skus}}},
        {"$group": {"_id": None, "total_qty": {"$sum": "$line_items.quantity"}}}
    ]
    inward_res = await mongo_db.inward_stock.aggregate(inward_pipeline).to_list(1)
    total_inward = inward_res[0]["total_qty"] if inward_res else 0

    outward_pipeline = [
        {"$match": {"line_items.sku": {"$in": skus}, "is_active": True}},
        {"$unwind": "$line_items"},
        {"$match": {"line_items.sku": {"$in": skus}}},
        {"$group": {"_id": None, "total_qty": {"$sum": "$line_items.quantity"}}}
    ]
    outward_res = await mongo_db.outward_stock.aggregate(outward_pipeline).to_list(1)
    total_outward = outward_res[0]["total_qty"] if outward_res else 0

    return {
        "category": category,
        "product_count": len(products),
        "total_inward": total_inward,
        "total_outward": total_outward,
        "current_stock": total_inward - total_outward
    }

async def tool_get_recent_transactions(limit: int = 5):
    """Latest inward and outward movements"""
    inwards = await mongo_db.inward_stock.find({"is_active": True}, {"_id": 0}).sort("date", -1).limit(limit).to_list(limit)
    outwards = await mongo_db.outward_stock.find({"is_active": True}, {"_id": 0}).sort("date", -1).limit(limit).to_list(limit)
    
    return {
        "inwards": [{
            "invoice": i.get("inward_invoice_no"),
            "date": i.get("date"),
            "items": len(i.get("line_items", []))
        } for i in inwards],
        "outwards": [{
            "invoice": o.get("export_invoice_no"),
            "date": o.get("date"),
            "items": len(o.get("line_items", []))
        } for o in outwards]
    }

async def tool_get_pending_documents(doc_type: str = "PI"):
    """Fetch documents with Pending status"""
    collection = "proforma_invoices" if doc_type.upper() == "PI" else "purchase_orders"
    cursor = mongo_db[collection].find({"status": "Pending", "is_active": True}, {"_id": 0}).sort("date", -1).limit(10)
    docs = await cursor.to_list(length=10)
    
    return {
        "type": doc_type,
        "count": len(docs),
        "pending_list": [{
            "voucher_no": d.get("voucher_no"),
            "date": d.get("date"),
            "company": d.get("buyer" if doc_type.upper() == "PI" else "supplier")
        } for d in docs]
    }

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
    tools = [
        get_document_details, 
        get_sku_stock_stats,
        search_documents_by_company,
        get_stock_summary_by_category,
        get_recent_transactions,
        get_pending_documents
    ]
    model_name = await get_available_model()
    
    model = genai.GenerativeModel(
        model_name=model_name,
        tools=tools,
        system_instruction="""You are the Bora Mobility Inventory Assistant. 
        You help users find details about Proforma Invoices (PI), Purchase Orders (PO), SKU stock levels, and transaction summaries.
        
        Guidelines:
        - Always be professional, concise, and helpful.
        - Use Markdown tables to present lists of documents or stock summaries for better readability.
        - If a user mentions a document number or SKU, use the appropriate tools.
        - If searching for a company, use search_documents_by_company.
        - If asked for "pending" items, use get_pending_documents.
        - If asked for recent activity, use get_recent_transactions.
        - Current Date context: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    chat = model.start_chat(history=history or [], enable_automatic_function_calling=False)
    
    try:
        response = chat.send_message(message)
        
        # Handle manual tool calling loop (Gemini might request multiple calls or we just handle one for now)
        if response.candidates[0].content.parts[0].function_call:
            call = response.candidates[0].content.parts[0].function_call
            tool_name = call.name
            args = call.args
            
            logger.info(f"Gemini calling tool: {tool_name} with args: {args}")

            if tool_name == "get_document_details":
                tool_result = await tool_get_document_details(args["voucher_no"])
            elif tool_name == "get_sku_stock_stats":
                tool_result = await tool_get_sku_stock_stats(args["sku_name"])
            elif tool_name == "search_documents_by_company":
                tool_result = await tool_search_documents_by_company(args.get("company_name"), args.get("doc_type", "PI"))
            elif tool_name == "get_stock_summary_by_category":
                tool_result = await tool_get_stock_summary_by_category(args.get("category"))
            elif tool_name == "get_recent_transactions":
                tool_result = await tool_get_recent_transactions(int(args.get("limit", 5)))
            elif tool_name == "get_pending_documents":
                tool_result = await tool_get_pending_documents(args.get("doc_type", "PI"))
            else:
                tool_result = {"error": f"Unknown tool: {tool_name}"}

            # Create FunctionResponse directly using protobuf classes
            function_response = genai.protos.FunctionResponse(
                name=tool_name,
                response=tool_result
            )
            part = genai.protos.Part(function_response=function_response)
            
            response = chat.send_message(
                genai.protos.Content(parts=[part])
            )

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
