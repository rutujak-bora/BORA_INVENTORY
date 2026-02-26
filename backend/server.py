from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.encoders import jsonable_encoder
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import uuid
from datetime import datetime, timezone
import pandas as pd
import io
import math
from bson import ObjectId

from database import mongo_db
from schemas import (
    UserLogin, CompanyCreate, CompanyUpdate,
    ProductCreate, ProductUpdate,
    WarehouseCreate, WarehouseUpdate,
    BankCreate, BankUpdate,
    DashboardStats, MappingUpdate,
    InwardStockCreate, InwardStockResponse, InwardStockDetailResponse,
    StockSummaryResponse, StockTrackingResponse,
    OutwardStockCreate, OutwardStockResponse, OutwardStockDetailResponse
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="Bora Mobility Inventory System")

# Configure CORS BEFORE defining routes
# This ensures preflight OPTIONS requests are handled correctly
cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
cors_origins = [origin.strip() for origin in cors_origins]  # Remove whitespace

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)

@app.get("/")
async def root():
    return {"message": "Bora Mobility Inventory System API is running"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"❌ HTTP Error {exc.status_code} at {request.url.path}: {exc.detail}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add file handler for persistent logs
file_handler = logging.FileHandler("backend_debug.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# ==================== AUTH ROUTES ====================
@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user_doc = await mongo_db.users.find_one({"username": user_data.username}, {"_id": 0})
    
    if not user_doc or not verify_password(user_data.password, user_doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(data={"sub": user_doc["id"]})
    
    await mongo_db.audit_logs.insert_one({
        "action": "user_login",
        "user_id": user_doc["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_doc
    }

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_active_user)):
    return current_user

# ==================== COMPANY ROUTES ====================
@api_router.post("/companies")
async def create_company(
    company_data: CompanyCreate,
    current_user: dict = Depends(get_current_active_user)
):
    try:
        data = company_data.model_dump()
        
        # 🔹 map gstn -> GSTNumber for DB consistency
        # If gstn is empty string or None, we don't want to store it as a duplicate null/empty
        gst_value = data.pop("gstn", None)
        if not gst_value: # Handle "" or None
            gst_value = None
        
        company_dict = {
            "id": str(uuid.uuid4()),
            **data,
            "GSTNumber": gst_value,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # If GSTNumber is None, remove it from dict to avoid Unique index conflict (if using sparse)
        if company_dict["GSTNumber"] is None:
            company_dict.pop("GSTNumber")
            
        await mongo_db.companies.insert_one(company_dict)
        
        await mongo_db.audit_logs.insert_one({
            "action": "company_created",
            "user_id": current_user["id"],
            "entity_id": company_dict["id"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        company_dict.pop("_id", None)
        # Convert back for response if needed
        company_dict["gstn"] = company_dict.get("GSTNumber")
            
        return company_dict
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        if "E11000 duplicate key error" in str(e):
            raise HTTPException(status_code=400, detail="Company with this Name or GSTN already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create company: {str(e)}")



@api_router.post("/companies/bulk")
async def bulk_upload_companies(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    try:
        print("====== BULK UPLOAD STARTED ======")

        contents = await file.read()
        filename = file.filename.lower()

        print(f"File received: {filename}")
        print(f"File size: {len(contents)} bytes")

        # --- Read CSV or Excel properly ---
        if filename.endswith(".csv"):
            try:
                df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
            except UnicodeDecodeError:
                df = pd.read_csv(io.StringIO(contents.decode('ISO-8859-1')))
        elif filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contents), engine="xlrd")
        else:
            df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")

        print("Original dataframe rows:", len(df))

        # --- Drop completely empty rows ---
        df = df.dropna(how='all')
        print("After dropping empty rows:", len(df))

        # --- Normalize columns ---
        df.columns = [str(col).strip().lower() for col in df.columns]
        print("Columns detected:", df.columns.tolist())

        inserted_count = 0
        skipped_rows = []

        for idx, row in df.iterrows():
            print("\n---- Processing row:", idx + 2, "----")
            print("Row data:", row.to_dict())

            try:
                name = str(row.get('name', '')).strip()
                if not name:
                    print("❌ Skipping row — missing name")
                    skipped_rows.append({"row": idx + 2, "reason": "Missing name"})
                    continue

                gst_raw = row.get('gstn', None)
                gst_value = None
                if pd.notna(gst_raw):
                    gst_value = str(gst_raw).strip()
                    if not gst_value:
                        gst_value = None

                company_dict = {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    **({"GSTNumber": gst_value} if gst_value else {}),
                    "apob": str(row.get('apob', '')).strip() if pd.notna(row.get('apob', '')) else None,
                    "address": str(row.get('address', '')).strip() if pd.notna(row.get('address', '')) else None,
                    "contact_details": str(row.get('contact_details', '')).strip() if pd.notna(row.get('contact_details', '')) else None,
                    "country": str(row.get('country', '')).strip() if pd.notna(row.get('country', '')) else None,
                    "city": str(row.get('city', '')).strip() if pd.notna(row.get('city', '')) else None,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

                print("📥 Inserting company:", company_dict)

                await mongo_db.companies.insert_one(company_dict)
                inserted_count += 1

                print("✅ Inserted — total now:", inserted_count)

            except Exception as e:
                print("🔥 Error inserting row:", e)

                if "E11000 duplicate key error" in str(e):
                    skipped_rows.append({"row": idx + 2, "reason": "Duplicate entry"})
                else:
                    skipped_rows.append({"row": idx + 2, "reason": f"Error: {str(e)}"})
                continue

        print("\n====== BULK UPLOAD FINISHED ======")
        print("Inserted:", inserted_count)
        print("Skipped:", skipped_rows)

        return {
            "message": f"Upload finished: {inserted_count} inserted, {len(skipped_rows)} skipped",
            "inserted_count": inserted_count,
            "skipped_rows": skipped_rows
        }

    except Exception as e:
        print("🔥 FATAL ERROR:", e)

        raise HTTPException(
            status_code=400,
            detail=f"Error processing file: {str(e)}"
        )



@api_router.get("/companies")
async def get_companies(current_user: dict = Depends(get_current_active_user)):
    companies = []
    async for company in mongo_db.companies.find({"is_active": True}, {"_id": 0}):
        
        # Convert GSTNumber -> gstn for frontend
        if "GSTNumber" in company:
            company["gstn"] = company.pop("GSTNumber")

        companies.append(company)

    return companies


@api_router.get("/companies/{company_id}")
async def get_company(company_id: str, current_user: dict = Depends(get_current_active_user)):
    company = await mongo_db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@api_router.put("/companies/{company_id}")
async def update_company(
    company_id: str,
    company_data: CompanyUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    company = await mongo_db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    update_data = company_data.model_dump(exclude_unset=True)

    # 🔹 map gstn -> GSTNumber for DB
    if "gstn" in update_data:
        gst_value = update_data.pop("gstn")
        if gst_value:           # only set if not empty
            update_data["GSTNumber"] = gst_value
        else:                   # if cleared, remove GSTNumber
            update_data["GSTNumber"] = None

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await mongo_db.companies.update_one(
        {"id": company_id},
        {"$set": update_data}
    )

    updated_company = await mongo_db.companies.find_one({"id": company_id}, {"_id": 0})
    return updated_company


@api_router.delete("/companies/{company_id}")
async def delete_company(company_id: str, current_user: dict = Depends(get_current_active_user)):
    # Check if company is referenced in other modules
    po_count = await mongo_db.purchase_orders.count_documents({"company_id": company_id, "is_active": True})
    pi_count = await mongo_db.proforma_invoices.count_documents({"company_id": company_id, "is_active": True})
    
    if po_count > 0 or pi_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete company. It is referenced in {po_count} PO(s) and {pi_count} PI(s). Delete those records first."
        )
    
    result = await mongo_db.companies.delete_one({"id": company_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Audit log
    await mongo_db.audit_logs.insert_one({
        "action": "company_deleted",
        "user_id": current_user["id"],
        "entity_id": company_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Company deleted successfully"}

@api_router.post("/companies/bulk-delete")
async def bulk_delete_companies(
    company_ids: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Bulk delete companies
    Payload: {"ids": ["id1", "id2", ...]}
    """
    ids = company_ids.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    deleted = []
    failed = []
    
    for company_id in ids:
        try:
            # Check references
            po_count = await mongo_db.purchase_orders.count_documents({"company_id": company_id, "is_active": True})
            pi_count = await mongo_db.proforma_invoices.count_documents({"company_id": company_id, "is_active": True})
            
            if po_count > 0 or pi_count > 0:
                failed.append({
                    "id": company_id,
                    "reason": f"Referenced in {po_count} PO(s) and {pi_count} PI(s)"
                })
                continue
            
            result = await mongo_db.companies.delete_one({"id": company_id})
            if result.deleted_count > 0:
                deleted.append(company_id)
                # Audit log
                await mongo_db.audit_logs.insert_one({
                    "action": "company_bulk_deleted",
                    "user_id": current_user["id"],
                    "entity_id": company_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                failed.append({"id": company_id, "reason": "Not found"})
        except Exception as e:
            failed.append({"id": company_id, "reason": str(e)})
    
    return {
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "failed_count": len(failed),
        "failed": failed
    }

@api_router.get("/companies/export")
async def export_companies(
    format: str = "json",
    current_user: dict = Depends(get_current_active_user)
):
    """
    Export companies data
    Format: json (default), csv
    """
    companies = []
    async for company in mongo_db.companies.find({}, {"_id": 0}):
        companies.append(company)
    
    if format == "csv":
        # Return data formatted for CSV
        return {
            "data": companies,
            "format": "csv"
        }
    
    return companies

# ==================== PRODUCT ROUTES ====================
@api_router.post("/products")
async def create_product(
    product_data: ProductCreate,
    current_user: dict = Depends(get_current_active_user)
):
    try:
        product_dict = {
            "id": str(uuid.uuid4()),
            **product_data.model_dump(),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await mongo_db.products.insert_one(product_dict)
        product_dict.pop("_id", None)
        return product_dict
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        if "E11000 duplicate key error" in str(e):
            raise HTTPException(status_code=400, detail="Product with this SKU already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")

@api_router.post("/products/bulk-upload")
@api_router.post("/products/bulk")  # Support both for compatibility
async def bulk_upload_products(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        products = []
        for _, row in df.iterrows():
            # Handle specification - can be text or number
            spec_value = row.get('specification', row.get('Specification', row.get('default_rate', row.get('Rate', ''))))
            if pd.notna(spec_value):
                specification = str(spec_value)  # Keep as string to support both text and numbers
            else:
                specification = None
            
            product_dict = {
                "id": str(uuid.uuid4()),
                "sku_name": str(row.get('sku_name', row.get('SKU', row.get('Name', '')))),
                "category": str(row.get('category', row.get('Category', ''))) if pd.notna(row.get('category', row.get('Category', ''))) else None,
                "brand": str(row.get('brand', row.get('Brand', ''))) if pd.notna(row.get('brand', row.get('Brand', ''))) else None,
                "hsn_sac": str(row.get('hsn_sac', row.get('HSN', ''))) if pd.notna(row.get('hsn_sac', row.get('HSN', ''))) else None,
                "country_of_origin": str(row.get('country_of_origin', row.get('Country', ''))) if pd.notna(row.get('country_of_origin', row.get('Country', ''))) else None,
                "color": str(row.get('color', row.get('Color', ''))) if pd.notna(row.get('color', row.get('Color', ''))) else None,
                "specification": specification,  # Can be text or number
                "feature": str(row.get('feature', row.get('Feature', ''))) if pd.notna(row.get('feature', row.get('Feature', ''))) else None,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            products.append(product_dict)
        
        if products:
            await mongo_db.products.insert_many(products)
        
        return {"message": f"Successfully uploaded {len(products)} products", "count": len(products)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@api_router.get("/products")
async def get_products(current_user: dict = Depends(get_current_active_user)):
    products = []
    async for product in mongo_db.products.find({"is_active": True}, {"_id": 0}):
        products.append(product)
    return products

@api_router.get("/products/export")
async def export_products(
    format: str = "json",
    current_user: dict = Depends(get_current_active_user)
):
    """Export products data"""
    products = []
    async for product in mongo_db.products.find({"is_active": True}, {"_id": 0}):
        products.append(product)
    
    if format == "csv":
        return {"data": products, "format": "csv"}
    
    return products

@api_router.get("/products/{product_id}")
async def get_product(product_id: str, current_user: dict = Depends(get_current_active_user)):
    product = await mongo_db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@api_router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    product = await mongo_db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await mongo_db.products.update_one({"id": product_id}, {"$set": update_data})
    
    updated_product = await mongo_db.products.find_one({"id": product_id}, {"_id": 0})
    return updated_product

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_active_user)):
    product = await mongo_db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check referential integrity
    pi_count = await mongo_db.proforma_invoices.count_documents({
        "line_items.product_id": product_id,
        "is_active": True
    })
    po_count = await mongo_db.purchase_orders.count_documents({
        "line_items.product_id": product_id,
        "is_active": True
    })
    inward_count = await mongo_db.inward_stock.count_documents({
        "line_items.product_id": product_id,
        "is_active": True
    })
    outward_count = await mongo_db.outward_stock.count_documents({
        "line_items.product_id": product_id,
        "is_active": True
    })
    
    total_references = pi_count + po_count + inward_count + outward_count
    if total_references > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete product. It is referenced in {pi_count} PI(s), {po_count} PO(s), {inward_count} Inward(s), and {outward_count} Outward(s). Delete those records first."
        )
    
    await mongo_db.products.update_one({"id": product_id}, {"$set": {"is_active": False}})
    
    # Audit log
    await mongo_db.audit_logs.insert_one({
        "action": "product_deleted",
        "user_id": current_user["id"],
        "entity_id": product_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Product deleted successfully"}

@api_router.post("/products/bulk-delete")
async def bulk_delete_products(
    payload: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Bulk delete products with referential integrity checks"""
    ids = payload.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    deleted = []
    failed = []
    
    for product_id in ids:
        try:
            product = await mongo_db.products.find_one({"id": product_id}, {"_id": 0})
            if not product:
                failed.append({"id": product_id, "reason": "Product not found"})
                continue
            
            # Check referential integrity
            pi_count = await mongo_db.proforma_invoices.count_documents({
                "line_items.product_id": product_id,
                "is_active": True
            })
            po_count = await mongo_db.purchase_orders.count_documents({
                "line_items.product_id": product_id,
                "is_active": True
            })
            inward_count = await mongo_db.inward_stock.count_documents({
                "line_items.product_id": product_id,
                "is_active": True
            })
            outward_count = await mongo_db.outward_stock.count_documents({
                "line_items.product_id": product_id,
                "is_active": True
            })
            
            total_references = pi_count + po_count + inward_count + outward_count
            if total_references > 0:
                failed.append({
                    "id": product_id,
                    "reason": f"Referenced in {pi_count} PI(s), {po_count} PO(s), {inward_count} Inward(s), {outward_count} Outward(s)"
                })
                continue
            
            # Soft delete
            await mongo_db.products.update_one(
                {"id": product_id},
                {"$set": {"is_active": False}}
            )
            deleted.append(product_id)
            
            # Audit log
            await mongo_db.audit_logs.insert_one({
                "action": "product_bulk_deleted",
                "user_id": current_user["id"],
                "entity_id": product_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            failed.append({"id": product_id, "reason": str(e)})
    
    return {
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "failed_count": len(failed),
        "failed": failed
    }

@api_router.post("/warehouses")
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    current_user: dict = Depends(get_current_active_user)
):
    try:
        warehouse_dict = {
            "id": str(uuid.uuid4()),
            **warehouse_data.model_dump(),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Map to legacy DB fields that have unique indexes
        # We only set them if they are not None to avoid collisions with sparse indexes
        warehouse_dict["warehouseName"] = warehouse_data.name
        if warehouse_data.contact_details:
            warehouse_dict["contactDetails"] = warehouse_data.contact_details

        await mongo_db.warehouses.insert_one(warehouse_dict)
        warehouse_dict.pop("_id", None)

        return warehouse_dict

    except Exception as e:
        print(f"Error creating warehouse: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@api_router.post("/warehouses/bulk")
async def bulk_upload_warehouses(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        warehouses = []
        for _, row in df.iterrows():
            warehouse_dict = {
                "id": str(uuid.uuid4()),
                "name": str(row.get('name', row.get('Name', ''))),
                "address": str(row.get('address', row.get('Address', ''))) if pd.notna(row.get('address', row.get('Address', ''))) else None,
                "city": str(row.get('city', row.get('City', ''))) if pd.notna(row.get('city', row.get('City', ''))) else None,
                "country": str(row.get('country', row.get('Country', ''))) if pd.notna(row.get('country', row.get('Country', ''))) else None,
                "contact_details": str(row.get('contact_details', row.get('Contact', ''))) if pd.notna(row.get('contact_details', row.get('Contact', ''))) else None,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            warehouses.append(warehouse_dict)
        
        if warehouses:
            await mongo_db.warehouses.insert_many(warehouses)
        
        return {"message": f"Successfully uploaded {len(warehouses)} warehouses", "count": len(warehouses)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@api_router.get("/warehouses/export")
async def export_warehouses(
    format: str = "json",
    current_user: dict = Depends(get_current_active_user)
):
    """Export warehouses data"""
    warehouses = []
    async for warehouse in mongo_db.warehouses.find({"is_active": True}, {"_id": 0}):
        warehouses.append(warehouse)
    
    if format == "csv":
        return {"data": warehouses, "format": "csv"}
    
    return warehouses

@api_router.get("/warehouses")
async def get_warehouses(current_user: dict = Depends(get_current_active_user)):
    warehouses = await mongo_db.warehouses.find({}, {"_id": 0}).to_list(length=None)
    return warehouses



@api_router.get("/warehouses/{warehouse_id}")
async def get_warehouse(warehouse_id: str, current_user: dict = Depends(get_current_active_user)):
    warehouse = await mongo_db.warehouses.find_one({"id": warehouse_id}, {"_id": 0})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse

@api_router.put("/warehouses/{warehouse_id}")
async def update_warehouse(
    warehouse_id: str,
    warehouse_data: WarehouseUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    warehouse = await mongo_db.warehouses.find_one({"id": warehouse_id}, {"_id": 0})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    update_data = warehouse_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await mongo_db.warehouses.update_one({"id": warehouse_id}, {"$set": update_data})
    
    updated_warehouse = await mongo_db.warehouses.find_one({"id": warehouse_id}, {"_id": 0})
    return updated_warehouse

@api_router.delete("/warehouses/{warehouse_id}")
async def delete_warehouse(warehouse_id: str, current_user: dict = Depends(get_current_active_user)):
    warehouse = await mongo_db.warehouses.find_one({"id": warehouse_id}, {"_id": 0})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Check referential integrity
    inward_count = await mongo_db.inward_stock.count_documents({
        "warehouse_id": warehouse_id,
        "is_active": True
    })
    outward_count = await mongo_db.outward_stock.count_documents({
        "warehouse_id": warehouse_id,
        "is_active": True
    })
    
    total_references = inward_count + outward_count
    if total_references > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete warehouse. It is referenced in {inward_count} Inward(s) and {outward_count} Outward(s). Delete those records first."
        )
    
    await mongo_db.warehouses.update_one({"id": warehouse_id}, {"$set": {"is_active": False}})
    
    # Audit log
    await mongo_db.audit_logs.insert_one({
        "action": "warehouse_deleted",
        "user_id": current_user["id"],
        "entity_id": warehouse_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Warehouse deleted successfully"}

@api_router.post("/warehouses/bulk-delete")
async def bulk_delete_warehouses(
    payload: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Bulk delete warehouses with referential integrity checks"""
    ids = payload.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    deleted = []
    failed = []
    
    for warehouse_id in ids:
        try:
            warehouse = await mongo_db.warehouses.find_one({"id": warehouse_id}, {"_id": 0})
            if not warehouse:
                failed.append({"id": warehouse_id, "reason": "Warehouse not found"})
                continue
            
            # Check referential integrity
            inward_count = await mongo_db.inward_stock.count_documents({
                "warehouse_id": warehouse_id,
                "is_active": True
            })
            outward_count = await mongo_db.outward_stock.count_documents({
                "warehouse_id": warehouse_id,
                "is_active": True
            })
            
            total_references = inward_count + outward_count
            if total_references > 0:
                failed.append({
                    "id": warehouse_id,
                    "reason": f"Referenced in {inward_count} Inward(s) and {outward_count} Outward(s)"
                })
                continue
            
            # Soft delete
            await mongo_db.warehouses.update_one(
                {"id": warehouse_id},
                {"$set": {"is_active": False}}
            )
            deleted.append(warehouse_id)
            
            # Audit log
            await mongo_db.audit_logs.insert_one({
                "action": "warehouse_bulk_deleted",
                "user_id": current_user["id"],
                "entity_id": warehouse_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            failed.append({"id": warehouse_id, "reason": str(e)})
    
    return {
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "failed_count": len(failed),
        "failed": failed
    }

# ==================== BANK ROUTES ====================
@api_router.post("/banks")
async def create_bank(
    bank_data: BankCreate,
    current_user: dict = Depends(get_current_active_user)
):
    try:
        bank_dict = {
            "id": str(uuid.uuid4()),
            **bank_data.model_dump(),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Map to legacy DB fields that have unique indexes
        # We only set them if they are not None to avoid collisions with sparse indexes
        if bank_data.ifsc_code:
            bank_dict["IFSC_code"] = bank_data.ifsc_code
        if bank_data.ad_code:
            bank_dict["AD_code"] = bank_data.ad_code
        if bank_data.account_number:
            bank_dict["Account_Number"] = bank_data.account_number

        await mongo_db.banks.insert_one(bank_dict)
        bank_dict.pop("_id", None)
        return bank_dict
    except Exception as e:
        print(f"Error creating bank: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/banks")
async def get_banks(current_user: dict = Depends(get_current_active_user)):
    banks = []
    async for bank in mongo_db.banks.find({"is_active": True}, {"_id": 0}):
        banks.append(bank)
    return banks

@api_router.get("/banks/{bank_id}")
async def get_bank(bank_id: str, current_user: dict = Depends(get_current_active_user)):
    bank = await mongo_db.banks.find_one({"id": bank_id}, {"_id": 0})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    return bank

@api_router.put("/banks/{bank_id}")
async def update_bank(
    bank_id: str,
    bank_data: BankUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    bank = await mongo_db.banks.find_one({"id": bank_id}, {"_id": 0})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    update_data = bank_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await mongo_db.banks.update_one({"id": bank_id}, {"$set": update_data})
    
    updated_bank = await mongo_db.banks.find_one({"id": bank_id}, {"_id": 0})
    return updated_bank

@api_router.delete("/banks/{bank_id}")
async def delete_bank(bank_id: str, current_user: dict = Depends(get_current_active_user)):
    bank = await mongo_db.banks.find_one({"id": bank_id}, {"_id": 0})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    await mongo_db.banks.update_one({"id": bank_id}, {"$set": {"is_active": False}})
    return {"message": "Bank deleted successfully"}

# ==================== TEMPLATE DOWNLOAD ROUTES ====================
@api_router.get("/templates/companies")
async def download_companies_template():
    from fastapi.responses import StreamingResponse
    import pandas as pd
    from io import BytesIO
    
    data = {
        'name': ['Acme Corporation', 'TechVision Industries'],
        'gstn': ['27AABCU9603R1ZV', '29AAGCC7409Q1Z6'],
        'apob': ['Mumbai Port', 'Bangalore Airport'],
        'address': ['123 MG Road, Andheri', '456 Tech Park, Whitefield'],
        'contact_details': ['+91-9876543210', '+91-8765432109'],
        'country': ['India', 'India'],
        'city': ['Mumbai', 'Bangalore']
    }
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Companies')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Companies_Template.xlsx"}
    )

@api_router.get("/templates/products")
async def download_products_template():
    from fastapi.responses import StreamingResponse
    import pandas as pd
    from io import BytesIO
    
    data = {
        'sku_name': ['WIDGET-001', 'GADGET-002', 'CABLE-003'],
        'category': ['Electronics', 'Accessories', 'Cables'],
        'brand': ['TechBrand', 'SmartGear', 'ConnectPro'],
        'hsn_sac': ['8517', '8543', '8544'],
        'country_of_origin': ['India', 'China', 'Taiwan'],
        'color': ['Red', 'Blue', 'Black'],
        'specification': ['1500.00', 'Premium Quality', '2m length'],  # Can be text or number
        'feature': ['Waterproof, Fast Charge', 'Wireless, Compact', 'Durable, USB-C']
    }
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Products')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Products_Template.xlsx"}
    )

@api_router.get("/templates/warehouses")
async def download_warehouses_template():
    from fastapi.responses import StreamingResponse
    import pandas as pd
    from io import BytesIO
    
    data = {
        'name': ['Main Warehouse Mumbai', 'Secondary Storage Delhi'],
        'address': ['Plot 101, MIDC Area, Andheri East', 'Sector 18, Industrial Area, Noida'],
        'city': ['Mumbai', 'Delhi'],
        'country': ['India', 'India'],
        'contact_details': ['+91-9999888877', '+91-8888777766']
    }
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Warehouses')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Warehouses_Template.xlsx"}
    )

# ==================== proforma INVOICE (PI) ROUTES ====================
@api_router.post("/pi")
async def create_pi(
    pi_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    # Create PI
    pi_dict = {
        "id": str(uuid.uuid4()),
        "company_id": pi_data.get("company_id"),
        "voucher_no": pi_data.get("voucher_no"),
        "date": pi_data.get("date"),
        "consignee": pi_data.get("consignee"),
        "buyer": pi_data.get("buyer"),
        "status": pi_data.get("status", "Pending"),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
        "line_items": []
    }
    
    # Add line items
    for item in pi_data.get("line_items", []):
        line_item = {
            "id": str(uuid.uuid4()),
            "product_id": item.get("product_id"),
            "product_name": item.get("product_name"),
            "sku": item.get("sku"),
            "category": item.get("category"),
            "brand": item.get("brand"),
            "hsn_sac": item.get("hsn_sac"),
            "made_in": item.get("made_in"),
            "quantity": float(item.get("quantity", 0)),
            "rate": float(item.get("rate", 0)),
            "amount": float(item.get("quantity", 0)) * float(item.get("rate", 0))
        }
        pi_dict["line_items"].append(line_item)
    
    await mongo_db.proforma_invoices.insert_one(pi_dict)
    
    await mongo_db.audit_logs.insert_one({
        "action": "pi_created",
        "user_id": current_user["id"],
        "entity_id": pi_dict["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    pi_dict.pop("_id", None)
    return pi_dict

@api_router.post("/pi/bulk")
async def bulk_upload_pis(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    try:
        print("\n====== PI BULK UPLOAD STARTED ======")

        contents = await file.read()
        print(f"File received: {file.filename}")
        print(f"File size: {len(contents)} bytes")

        filename = file.filename.lower()
        print(f"File received: {filename}")

        # Read based on extension
        if filename.endswith(".csv"):
            try:
                df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
            except UnicodeDecodeError:
                df = pd.read_csv(io.StringIO(contents.decode("ISO-8859-1")))
        elif filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contents), engine="xlrd")
        else:  # .xlsx
            df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")

        print("Original rows:", len(df))
        print("Columns:", df.columns.tolist())

        # Drop empty rows
        df = df.dropna(how="all")
        print("After dropping empty:", len(df))

        # Validate required column
        if "voucher_no" not in df.columns:
            raise HTTPException(
                status_code=400,
                detail="Missing required column: voucher_no"
            )

        pis_created = 0

        print("Unique voucher numbers:", df["voucher_no"].unique())

        for voucher_no in df["voucher_no"].unique():
            print(f"\n---- Processing voucher: {voucher_no} ----")

            pi_rows = df[df["voucher_no"] == voucher_no]
            first_row = pi_rows.iloc[0]

            pi_dict = {
                "id": str(uuid.uuid4()),
                "company_id": str(first_row.get("company_id", "")),
                "voucher_no": str(voucher_no),
                "date": str(first_row.get("date", datetime.now(timezone.utc).isoformat())),
                "consignee": str(first_row.get("consignee", "")),
                "buyer": str(first_row.get("buyer", "")),
                "status": "Pending",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["id"],
                "line_items": []
            }

            print(f"Header for voucher {voucher_no}:", pi_dict)

            # Build line items
            for _, row in pi_rows.iterrows():
                line_item = {
                    "id": str(uuid.uuid4()),
                    "product_id": str(row.get("product_id", "")),
                    "product_name": str(row.get("product_name", "")),
                    "sku": str(row.get("sku", "")),
                    "category": str(row.get("category", "")),
                    "brand": str(row.get("brand", "")),
                    "hsn_sac": str(row.get("hsn_sac", "")),
                    "made_in": str(row.get("made_in", "")),
                    "quantity": float(row.get("quantity", 0) or 0),
                    "rate": float(row.get("rate", 0) or 0),
                    "amount": float(row.get("quantity", 0) or 0) * float(row.get("rate", 0) or 0)
                }

                print(" ➜ Adding line:", line_item)

                pi_dict["line_items"].append(line_item)

            try:
                print(f"📥 Inserting PI for voucher {voucher_no}")
                await mongo_db.proforma_invoices.insert_one(pi_dict)
                pis_created += 1
                print(f"✅ Inserted PI #{pis_created}")
            except Exception as e:
                print(f"🔥 Error inserting PI for {voucher_no}: {e}")
                continue

        print("\n====== PI BULK UPLOAD FINISHED ======")
        print("Total created:", pis_created)

        return {
            "message": f"Successfully uploaded {pis_created} PIs",
            "count": pis_created
        }

    except Exception as e:
        print("🔥 FATAL ERROR:", e)
        raise HTTPException(
            status_code=400,
            detail=f"Error processing file: {str(e)}"
        )

@api_router.get("/pi")
async def get_pis(current_user: dict = Depends(get_current_active_user)):
    pis = []
    async for pi in mongo_db.proforma_invoices.find({"is_active": True}, {"_id": 0}):
        # Calculate total amount
        total_amount = sum(item.get("amount", 0) for item in pi.get("line_items", []))
        pi["total_amount"] = total_amount
        pi["line_items_count"] = len(pi.get("line_items", []))
        # Keep line_items for display but only show minimal info in list
        pis.append(pi)
    return pis

# Helper functions for PI stock calculations
async def get_inward_qty_for_pi(pi_id: str, product_sku: str, warehouse_id: str, product_id: str = None) -> float:
    """Calculate total inward quantity for a specific PI, product SKU, and warehouse"""
    total_inward = 0.0
    
    # 1. Get all PO IDs linked to this PI
    linked_po_ids = []
    async for po in mongo_db.purchase_orders.find({
        "$or": [{"reference_pi_id": pi_id}, {"reference_pi_ids": pi_id}],
        "is_active": True
    }, {"id": 1}):
        linked_po_ids.append(po["id"])

    # 2. Build query for inward entries
    # Match by PI ID OR by linked PO IDs
    query = {
        "is_active": True,
        "warehouse_id": warehouse_id,
        "$or": [
            {"pi_id": pi_id},
            {"pi_ids": pi_id}
        ]
    }
    
    if linked_po_ids:
        query["$or"].append({"po_id": {"$in": linked_po_ids}})
        query["$or"].append({"po_ids": {"$in": linked_po_ids}})

    async for inward in mongo_db.inward_stock.find(query, {"_id": 0}):
        for item in inward.get("line_items", []):
            matched = False
            if product_id and item.get("product_id") == product_id:
                matched = True
            elif product_sku and item.get("sku") == product_sku:
                matched = True
                
            if matched:
                total_inward += float(item.get("quantity", 0))
    
    return total_inward

async def get_dispatched_qty_for_pi(pi_id: str, product_sku: str, warehouse_id: str, product_id: str = None) -> float:
    """Calculate total dispatched quantity for a specific PI, product SKU, and warehouse"""
    total_dispatched = 0.0
    
    # 1. Get all PO IDs linked to this PI
    linked_po_ids = []
    async for po in mongo_db.purchase_orders.find({
        "$or": [{"reference_pi_id": pi_id}, {"reference_pi_ids": pi_id}],
        "is_active": True
    }, {"id": 1}):
        linked_po_ids.append(po["id"])

    # 2. Build query - Include dispatch_plan, export_invoice, and direct_export
    query = {
        "warehouse_id": warehouse_id,
        "is_active": True,
        "status": {"$ne": "Cancelled"},
        "dispatch_type": {"$in": ["dispatch_plan", "export_invoice", "direct_export"]},
        "$or": [
            {"pi_id": pi_id},
            {"pi_ids": pi_id}
        ]
    }
    
    if linked_po_ids:
        query["$or"].append({"po_id": {"$in": linked_po_ids}})
        query["$or"].append({"po_ids": {"$in": linked_po_ids}})

    # 3. Fetch all outward entries and identify linked plans to avoid double-counting
    all_outwards = []
    async for outward in mongo_db.outward_stock.find(query, {"_id": 0}):
        all_outwards.append(outward)
    
    # Get IDs of dispatch plans that have been converted to export invoices
    linked_plan_ids = {o.get("dispatch_plan_id") for o in all_outwards if o.get("dispatch_plan_id")}
    
    # 4. Calculate dispatched quantity, skipping converted dispatch plans
    for outward in all_outwards:
        # Skip dispatch plans that have been converted to export invoices (to avoid double-counting)
        if outward.get("dispatch_type") == "dispatch_plan" and outward.get("id") in linked_plan_ids:
            continue
            
        for item in outward.get("line_items", []):
            matched = False
            if product_id and item.get("product_id") == product_id:
                matched = True
            elif product_sku and item.get("sku") == product_sku:
                matched = True
                
            if matched:
                # Support both 'quantity' and 'dispatch_quantity' fields
                qty = item.get("dispatch_quantity") or item.get("quantity", 0)
                total_dispatched += float(qty)
    
    return total_dispatched


@api_router.get("/pi/{pi_id}")
async def get_pi(
    pi_id: str,
    warehouse_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    pi = await mongo_db.proforma_invoices.find_one(
        {"id": pi_id},
        {"_id": 0}
    )
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")

    if pi.get("company_id"):
        company = await mongo_db.companies.find_one(
            {"id": pi["company_id"]},
            {"_id": 0}
        )
        pi["company"] = company

    # Only calculate detailed stock info if a warehouse is specified (contextual detailed view)
    if warehouse_id:
        inward_stocks = []
        async for stock in mongo_db.inward_stock.find(
            {"pi_id": pi_id, "warehouse_id": warehouse_id},
            {"_id": 0}
        ):
            inward_stocks.append(stock)
        pi["inward_stock"] = inward_stocks

        # Calculate quantities using Product ID and SKU
        for item in pi.get("line_items", []):
            product_sku = item.get("sku")
            product_id = item.get("product_id")
            
            # CRITICAL FIX: If product_id is missing, look it up from products collection
            if not product_id and product_sku:
                product = await mongo_db.products.find_one({"sku": product_sku}, {"id": 1})
                if product:
                    product_id = product["id"]
                    item["product_id"] = product_id

            inward_qty = await get_inward_qty_for_pi(
                pi_id=pi_id,
                product_sku=product_sku,
                product_id=product_id,
                warehouse_id=warehouse_id
            )

            dispatched_qty = await get_dispatched_qty_for_pi(
                pi_id=pi_id,
                product_sku=product_sku,
                product_id=product_id,
                warehouse_id=warehouse_id
            )

            item["pi_quantity"] = float(item.get("quantity", 0))
            item["inward_quantity"] = inward_qty
            item["dispatched_quantity"] = dispatched_qty
            item["available_quantity"] = max(inward_qty - dispatched_qty, 0)
    
    return pi


@api_router.put("/pi/{pi_id}")
async def update_pi(
    pi_id: str,
    pi_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    update_data = {
        "company_id": pi_data.get("company_id"),
        "voucher_no": pi_data.get("voucher_no"),
        "date": pi_data.get("date"),
        "consignee": pi_data.get("consignee"),
        "buyer": pi_data.get("buyer"),
        "status": pi_data.get("status", pi.get("status")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    # Update line items
    if "line_items" in pi_data:
        line_items = []
        for item in pi_data["line_items"]:
            line_item = {
                "id": item.get("id", str(uuid.uuid4())),
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "sku": item.get("sku"),
                "category": item.get("category"),
                "brand": item.get("brand"),
                "hsn_sac": item.get("hsn_sac"),
                "made_in": item.get("made_in"),
                "quantity": float(item.get("quantity", 0)),
                "rate": float(item.get("rate", 0)),
                "amount": float(item.get("quantity", 0)) * float(item.get("rate", 0))
            }
            line_items.append(line_item)
        update_data["line_items"] = line_items
    
    await mongo_db.proforma_invoices.update_one({"id": pi_id}, {"$set": update_data})
    
    updated_pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
    return updated_pi

@api_router.delete("/pi/{pi_id}")
async def delete_pi(pi_id: str, current_user: dict = Depends(get_current_active_user)):
    pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    await mongo_db.proforma_invoices.update_one({"id": pi_id}, {"$set": {"is_active": False}})
    return {"message": "PI deleted successfully"}

@api_router.get("/templates/pi")
async def download_pi_template():
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    
    data = {
        'company_id': ['company-id-here', 'company-id-here'],
        'voucher_no': ['PI-2025-001', 'PI-2025-001'],
        'date': ['2025-01-15', '2025-01-15'],
        'consignee': ['ABC Traders', 'ABC Traders'],
        'buyer': ['XYZ Corporation', 'XYZ Corporation'],
        'product_id': ['product-id-here', 'product-id-here'],
        'product_name': ['Widget A (Enter manually)', 'Gadget B (Enter manually)'],
        'sku': ['SKU-001 (from Product Master)', 'SKU-002 (from Product Master)'],
        'category': ['Auto-filled from SKU', 'Auto-filled from SKU'],
        'brand': ['Auto-filled from SKU', 'Auto-filled from SKU'],
        'hsn_sac': ['Auto-filled from SKU', 'Auto-filled from SKU'],
        'made_in': ['Auto-filled from SKU', 'Auto-filled from SKU'],
        'quantity': [100, 50],
        'rate': [1500.00, 2500.00]
    }
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='PI')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=PI_Template.xlsx"}
    )

@api_router.post("/pi/export")
async def export_pis(
    pi_ids: list[str],
    current_user: dict = Depends(get_current_active_user)
):
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    
    all_rows = []
    for pi_id in pi_ids:
        pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
        if pi:
            company = await mongo_db.companies.find_one({"id": pi.get("company_id")}, {"_id": 0})
            company_name = company.get("name") if company else ""
            
            for item in pi.get("line_items", []):
                row = {
                    "Voucher No": pi.get("voucher_no"),
                    "Date": pi.get("date"),
                    "Company Name": company_name,
                    "Consignee": pi.get("consignee"),
                    "Buyer": pi.get("buyer"),
                    "Product Name": item.get("product_name"),
                    "SKU": item.get("sku"),
                    "Category": item.get("category"),
                    "Brand": item.get("brand"),
                    "HSN/SAC": item.get("hsn_sac"),
                    "Made In": item.get("made_in"),
                    "Quantity": item.get("quantity"),
                    "Rate": item.get("rate"),
                    "Amount": item.get("amount"),
                    "Status": pi.get("status")
                }
                all_rows.append(row)
    
    df = pd.DataFrame(all_rows)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='PIs')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=PI_Export.xlsx"}
    )

# ==================== PURCHASE ORDER (PO) ROUTES ====================
@api_router.post("/po")
async def create_po(
    po_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    # Handle multiple PI references (backward compatible with single PI)
    reference_pi_ids = po_data.get("reference_pi_ids", [])
    if not reference_pi_ids and po_data.get("reference_pi_id"):
        # Backward compatibility: convert single PI to array
        reference_pi_ids = [po_data.get("reference_pi_id")]
    
    # Validate all PI IDs exist
    if reference_pi_ids:
        for pi_id in reference_pi_ids:
            pi = await mongo_db.proforma_invoices.find_one({"id": pi_id, "is_active": True}, {"_id": 0})
            if not pi:
                raise HTTPException(status_code=404, detail=f"proforma Invoice {pi_id} not found")
    
    # Create PO
    po_dict = {
        "id": str(uuid.uuid4()),
        "company_id": po_data.get("company_id"),
        "voucher_no": po_data.get("voucher_no"),
        "date": po_data.get("date"),
        "consignee": po_data.get("consignee"),
        "supplier": po_data.get("supplier"),
        "reference_pi_id": reference_pi_ids[0] if reference_pi_ids else None,  # For backward compatibility
        "reference_pi_ids": reference_pi_ids,  # New field for multiple PIs
        "reference_no_date": po_data.get("reference_no_date"),
        "dispatched_through": po_data.get("dispatched_through"),
        "destination": po_data.get("destination"),
        "gst_percentage": float(po_data.get("gst_percentage", 0)),  # GST % entered manually
        "tds_percentage": float(po_data.get("tds_percentage", 0)),  # TDS % entered manually
        "status": po_data.get("status", "Pending"),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
        "line_items": []
    }
    
    # Get GST and TDS percentages from PO level
    gst_percentage = float(po_data.get("gst_percentage", 0))
    tds_percentage = float(po_data.get("tds_percentage", 0))
    
    # Add line items with auto-calculated GST and TDS
    total_basic_amount = 0
    total_gst_value = 0
    total_tds_value = 0
    
    for item in po_data.get("line_items", []):
        quantity = float(item.get("quantity", 0))
        rate = float(item.get("rate", 0))
        amount = quantity * rate
        
        # Calculate GST Value: Amount × (GST % / 100)
        gst_value = amount * (gst_percentage / 100) if gst_percentage > 0 else 0
        
        # Calculate TDS Value: Amount × (TDS % / 100)
        tds_value = amount * (tds_percentage / 100) if tds_percentage > 0 else 0
        
        line_item = {
            "id": str(uuid.uuid4()),
            "product_id": item.get("product_id"),
            "product_name": item.get("product_name"),
            "sku": item.get("sku"),
            "category": item.get("category"),
            "brand": item.get("brand"),
            "hsn_sac": item.get("hsn_sac"),
            "pi_voucher_no": item.get("pi_voucher_no"),
            "quantity": quantity,
            "rate": rate,
            "amount": amount,
            "gst_value": round(gst_value, 2),  # Calculated GST value
            "tds_value": round(tds_value, 2)   # Calculated TDS value
        }
        po_dict["line_items"].append(line_item)
        
        total_basic_amount += amount
        total_gst_value += gst_value
        total_tds_value += tds_value
    
    # Add totals to PO
    po_dict["total_basic_amount"] = round(total_basic_amount, 2)
    po_dict["total_gst_value"] = round(total_gst_value, 2)
    po_dict["total_tds_value"] = round(total_tds_value, 2)
    po_dict["total_amount"] = round(total_basic_amount + total_gst_value - total_tds_value, 2)  # Basic + GST - TDS
    
    await mongo_db.purchase_orders.insert_one(po_dict)
    
    await mongo_db.audit_logs.insert_one({
        "action": "po_created",
        "user_id": current_user["id"],
        "entity_id": po_dict["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    po_dict.pop("_id", None)
    return jsonable_encoder(prepare_po_response(po_dict))

def sanitize_mongo_obj(obj):
    """Recursively convert ObjectId and other non-JSON types to str"""
    if isinstance(obj, list):
        return [sanitize_mongo_obj(v) for v in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_mongo_obj(v) for k, v in obj.items()}
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, datetime):
        return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
    return str(obj)

def sanitize_floats(obj):
    """Recursively convert NaN and Inf to 0.0 in a dictionary or list"""
    if isinstance(obj, list):
        return [sanitize_floats(v) for v in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_floats(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    return obj

def sanitize_po(po_dict):
    return sanitize_floats(po_dict)

def prepare_po_response(po):
    # Safer calculation of total amount
    total_amount = 0
    for item in po.get("line_items", []):
        amt = item.get("amount")
        if amt is not None:
            try:
                f_amt = float(amt)
                if not math.isnan(f_amt) and not math.isinf(f_amt):
                    total_amount += f_amt
            except (ValueError, TypeError):
                pass
    
    po["total_amount"] = round(total_amount, 2)
    po["line_items_count"] = len(po.get("line_items", []))
    return sanitize_po(po)

@api_router.post("/po/bulk")
async def bulk_upload_pos(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    try:
        print("\n" + "="*50)
        print("🚀 PO BULK UPLOAD START")
        print("="*50)

        contents = await file.read()
        filename = file.filename.lower()
        print(f"📄 Filename: {filename}")
        print(f"📊 Size: {len(contents)} bytes")

        # --- Read file correctly ---
        if filename.endswith(".csv"):
            try:
                df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
            except UnicodeDecodeError:
                df = pd.read_csv(io.StringIO(contents.decode("ISO-8859-1")))
        elif filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contents), engine="xlrd")
        else:  # .xlsx
            df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")

        if df.empty:
            print("❌ Error: Dataframe is empty")
            raise HTTPException(status_code=400, detail="The uploaded file is empty")

        # Normalize column names
        raw_cols = df.columns.tolist()
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        print(f"📝 Raw columns: {raw_cols}")
        print(f"⚙️ Normalized columns: {df.columns.tolist()}")

        # mapping
        mapping = {
            "invoice_no": "voucher_no",
            "po_no": "voucher_no",
            "po_number": "voucher_no",
            "gst_val": "gst_percentage",
            "input_igst": "gst_percentage",
            "gst_%": "gst_percentage",
            "tds_val": "tds_percentage",
            "tds_%": "tds_percentage"
        }
        for old_col, new_col in mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                print(f"🔄 Mapping column: {old_col} ➜ {new_col}")
                df[new_col] = df[old_col]

        if "voucher_no" not in df.columns:
            msg = f"Missing 'voucher_no'. Available: {', '.join(df.columns)}"
            print(f"❌ Error: {msg}")
            raise HTTPException(status_code=400, detail=msg)

        def clean_str(val):
            if pd.isna(val) or val is None: return ""
            val = str(val).strip()
            if val.endswith('.0'): val = val[:-2]
            return val

        def clean_float(val, default=0.0):
            try:
                if pd.isna(val) or val is None: return default
                s = str(val).strip().replace(',', '').replace('$', '').replace('₹', '')
                if s == "": return default
                return float(s)
            except:
                return default

        df["voucher_no"] = df["voucher_no"].apply(clean_str)
        df = df[df["voucher_no"] != ""]
        
        if df.empty:
            print("❌ Error: No valid voucher numbers found after filtering")
            raise HTTPException(status_code=400, detail="No valid voucher numbers found in file")

        pos_created = 0
        unique_vouchers = df["voucher_no"].unique()
        print(f"🎯 Unique POs detected: {len(unique_vouchers)}")

        for voucher_no in unique_vouchers:
            print(f"📦 Processing PO: {voucher_no}")
            po_rows = df[df["voucher_no"] == voucher_no]
            first_row = po_rows.iloc[0]

            reference_pi_ids = []
            pi_ids_val = first_row.get("reference_pi_ids")
            if pd.isna(pi_ids_val): pi_ids_val = first_row.get("reference_pi_id")
            
            if pd.notna(pi_ids_val) and str(pi_ids_val).strip():
                pi_ids_str = str(pi_ids_val).strip()
                reference_pi_ids = [pid.strip() for pid in pi_ids_str.split(",") if pid.strip()]

            date_val = first_row.get("date")
            po_date = str(date_val) if pd.notna(date_val) else datetime.now(timezone.utc).isoformat()

            gst_pct = clean_float(first_row.get("gst_percentage"))
            tds_pct = clean_float(first_row.get("tds_percentage"))

            po_dict = {
                "id": str(uuid.uuid4()),
                "company_id": clean_str(first_row.get("company_id")),
                "voucher_no": voucher_no,
                "date": po_date,
                "consignee": clean_str(first_row.get("consignee")),
                "supplier": clean_str(first_row.get("supplier")),
                "reference_pi_id": reference_pi_ids[0] if reference_pi_ids else None,
                "reference_pi_ids": reference_pi_ids,
                "reference_no_date": clean_str(first_row.get("reference_no_date")),
                "dispatched_through": clean_str(first_row.get("dispatched_through")),
                "destination": clean_str(first_row.get("destination")),
                "gst_percentage": gst_pct,
                "tds_percentage": tds_pct,
                "status": "Pending",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["id"],
                "line_items": []
            }

            total_basic = 0
            total_gst = 0
            total_tds = 0

            for _, row in po_rows.iterrows():
                qty = clean_float(row.get("quantity"))
                rate = clean_float(row.get("rate"))
                amount = qty * rate
                gst_v = amount * (gst_pct / 100)
                tds_v = amount * (tds_pct / 100)

                po_dict["line_items"].append({
                    "id": str(uuid.uuid4()),
                    "product_id": clean_str(row.get("product_id")),
                    "product_name": clean_str(row.get("product_name")),
                    "sku": clean_str(row.get("sku")),
                    "category": clean_str(row.get("category")),
                    "brand": clean_str(row.get("brand")),
                    "hsn_sac": clean_str(row.get("hsn_sac")),
                    "pi_voucher_no": clean_str(row.get("pi_voucher_no", row.get("pi_no", row.get("pi_number", "")))),
                    "quantity": qty,
                    "rate": rate,
                    "amount": round(amount, 2),
                    "gst_value": round(gst_v, 2),
                    "tds_value": round(tds_v, 2)
                })
                total_basic += amount
                total_gst += gst_v
                total_tds += tds_v

            po_dict["total_basic_amount"] = round(total_basic, 2)
            po_dict["total_gst_value"] = round(total_gst, 2)
            po_dict["total_tds_value"] = round(total_tds, 2)
            po_dict["total_amount"] = round(total_basic + total_gst - total_tds, 2)

            po_dict = prepare_po_response(po_dict)
            await mongo_db.purchase_orders.insert_one(po_dict)
            pos_created += 1

        print(f"🏁 Successfully created {pos_created} POs")
        return {"message": f"Successfully uploaded {pos_created} Purchase Orders", "count": pos_created}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/po")
@api_router.get("/purchase-orders")
async def get_pos(current_user: dict = Depends(get_current_active_user)):
    """Get all active Purchase Orders"""
    pos = []
    try:
        async for po in mongo_db.purchase_orders.find({"is_active": True}, {"_id": 0}):
            try:
                prepared_po = prepare_po_response(po)
                pos.append(prepared_po)
            except Exception as inner_e:
                logger.error(f"Error processing individual PO {po.get('voucher_no')}: {str(inner_e)}")
                continue

        return jsonable_encoder(pos)
    except Exception as e:
        logger.error(f"Error fetching POs: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

@api_router.get("/po/{po_id}")
async def get_po(po_id: str, current_user: dict = Depends(get_current_active_user)):
    po = await mongo_db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Get company details
    if po.get("company_id"):
        company = await mongo_db.companies.find_one({"id": po["company_id"]}, {"_id": 0})
        po["company"] = company
    
    # Get PI details if linked (support both single and multiple PIs)
    reference_pi_ids = po.get("reference_pi_ids", [])
    if not reference_pi_ids and po.get("reference_pi_id"):
        # Backward compatibility
        reference_pi_ids = [po.get("reference_pi_id")]
    
    if reference_pi_ids:
        pi_details = []
        for pi_id in reference_pi_ids:
            pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
            if pi:
                pi_details.append(pi)
        
        po["reference_pis"] = pi_details  # Multiple PIs
        if pi_details:
            po["reference_pi"] = pi_details[0]  # For backward compatibility
    
    return jsonable_encoder(prepare_po_response(po))

@api_router.put("/po/{po_id}")
async def update_po(
    po_id: str,
    po_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    po = await mongo_db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Handle multiple PI references (backward compatible with single PI)
    reference_pi_ids = po_data.get("reference_pi_ids", [])
    if not reference_pi_ids and po_data.get("reference_pi_id"):
        # Backward compatibility: convert single PI to array
        reference_pi_ids = [po_data.get("reference_pi_id")]
    
    # Validate all PI IDs exist if provided
    if reference_pi_ids:
        for pi_id in reference_pi_ids:
            pi = await mongo_db.proforma_invoices.find_one({"id": pi_id, "is_active": True}, {"_id": 0})
            if not pi:
                raise HTTPException(status_code=404, detail=f"proforma Invoice {pi_id} not found")
    
    # Get GST and TDS percentages
    gst_percentage = float(po_data.get("gst_percentage", 0))
    tds_percentage = float(po_data.get("tds_percentage", 0))

    update_data = {
        "company_id": po_data.get("company_id"),
        "voucher_no": po_data.get("voucher_no"),
        "date": po_data.get("date"),
        "consignee": po_data.get("consignee"),
        "supplier": po_data.get("supplier"),
        "reference_pi_id": reference_pi_ids[0] if reference_pi_ids else None,  # For backward compatibility
        "reference_pi_ids": reference_pi_ids,  # New field for multiple PIs
        "reference_no_date": po_data.get("reference_no_date"),
        "dispatched_through": po_data.get("dispatched_through"),
        "destination": po_data.get("destination"),
        "status": po_data.get("status", po.get("status")),
        "gst_percentage": gst_percentage,
        "tds_percentage": tds_percentage,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    # Update line items and recalculate totals
    if "line_items" in po_data:
        line_items = []
        total_basic_amount = 0
        total_gst_value = 0
        total_tds_value = 0

        for item in po_data["line_items"]:
            quantity = float(item.get("quantity", 0))
            rate = float(item.get("rate", 0))
            amount = quantity * rate
            
            # Recalculate or use provided values if matched
            # We enforce consistency with PO-level percentages
            gst_value = amount * (gst_percentage / 100) if gst_percentage > 0 else 0
            tds_value = amount * (tds_percentage / 100) if tds_percentage > 0 else 0

            line_item = {
                "id": item.get("id", str(uuid.uuid4())),
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "sku": item.get("sku"),
                "category": item.get("category"),
                "brand": item.get("brand"),
                "hsn_sac": item.get("hsn_sac"),
                "pi_voucher_no": item.get("pi_voucher_no"),
                "quantity": quantity,
                "rate": rate,
                "amount": amount,
                "gst_value": round(gst_value, 2),
                "tds_value": round(tds_value, 2)
            }
            line_items.append(line_item)
            
            total_basic_amount += amount
            total_gst_value += gst_value
            total_tds_value += tds_value
        
        update_data["line_items"] = line_items
        update_data["total_basic_amount"] = round(total_basic_amount, 2)
        update_data["total_gst_value"] = round(total_gst_value, 2)
        update_data["total_tds_value"] = round(total_tds_value, 2)
        update_data["total_amount"] = round(total_basic_amount + total_gst_value - total_tds_value, 2)
    
    await mongo_db.purchase_orders.update_one({"id": po_id}, {"$set": update_data})
    
    updated_po = await mongo_db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
    return jsonable_encoder(prepare_po_response(updated_po))

@api_router.delete("/po/{po_id}")
async def delete_po(po_id: str, current_user: dict = Depends(get_current_active_user)):
    po = await mongo_db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    await mongo_db.purchase_orders.update_one({"id": po_id}, {"$set": {"is_active": False}})
    return {"message": "PO deleted successfully"}

@api_router.get("/templates/po")
async def download_po_template():
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    
    data = {
        'company_id': ['company-id-here', 'company-id-here'],
        'voucher_no': ['PO-2025-001', 'PO-2025-001'],
        'date': ['2025-01-15', '2025-01-15'],
        'consignee': ['ABC Traders', 'ABC Traders'],
        'supplier': ['XYZ Suppliers', 'XYZ Suppliers'],
        'reference_pi_ids': ['pi-id-1,pi-id-2', 'pi-id-3'],  # Multiple PIs comma-separated
        'reference_no_date': ['PI-2025-001 | 2025-01-10', 'PI-2025-001 | 2025-01-10'],
        'dispatched_through': ['DHL Express', 'DHL Express'],
        'destination': ['Mumbai Port', 'Mumbai Port'],
        'product_id': ['product-id-here', 'product-id-here'],
        'product_name': ['Widget A (Enter manually)', 'Gadget B (Enter manually)'],
        'sku': ['SKU-001 (from Product Master)', 'SKU-002 (from Product Master)'],
        'category': ['Auto-filled from SKU', 'Auto-filled from SKU'],
        'brand': ['Auto-filled from SKU', 'Auto-filled from SKU'],
        'hsn_sac': ['Auto-filled from SKU', 'Auto-filled from SKU'],
        'quantity': [100, 50],
        'rate': [1500.00, 2500.00],
        'input_igst': [270.00, 450.00],
        'tds': [15.00, 25.00]
    }
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='PO')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=PO_Template.xlsx"}
    )

@api_router.post("/po/export")
async def export_pos(
    po_ids: list[str],
    current_user: dict = Depends(get_current_active_user)
):
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    
    all_rows = []
    for po_id in po_ids:
        po = await mongo_db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
        if po:
            company = await mongo_db.companies.find_one({"id": po.get("company_id")}, {"_id": 0})
            company_name = company.get("name") if company else ""
            
            for item in po.get("line_items", []):
                row = {
                    "Voucher No": po.get("voucher_no"),
                    "Date": po.get("date"),
                    "Company Name": company_name,
                    "Consignee": po.get("consignee"),
                    "Supplier": po.get("supplier"),
                    "Reference PI": po.get("reference_no_date"),
                    "Dispatched Through": po.get("dispatched_through"),
                    "Destination": po.get("destination"),
                    "Product Name": item.get("product_name"),
                    "SKU": item.get("sku"),
                    "Category": item.get("category"),
                    "Brand": item.get("brand"),
                    "HSN/SAC": item.get("hsn_sac"),
                    "Quantity": item.get("quantity"),
                    "Rate": item.get("rate"),
                    "Amount": item.get("amount"),
                    "Input IGST": item.get("input_igst"),
                    "TDS": item.get("tds"),
                    "Status": po.get("status")
                }
                all_rows.append(row)
    
    df = pd.DataFrame(all_rows)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='POs')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=PO_Export.xlsx"}
    )

# ==================== STOCK MANAGEMENT ROUTES ====================

# ==================== INWARD OPERATIONS ====================
@api_router.post("/inward-stock")
async def create_inward_stock(
    inward_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Create inward stock entry (Inward to Warehouse or Direct Inward)
    MULTIPLE PO SUPPORT: Accepts po_ids array for multiple PO selection
    """

    po_ids = inward_data.get("po_ids", [])
    if not po_ids and inward_data.get("po_id"):
        po_ids = [inward_data["po_id"]]

    all_pi_ids = []
    company_id_from_po = None
    aggregated_po_quantities = {}

    # ------------------- VALIDATE ALL POs -------------------
    if po_ids:
        for po_id in po_ids:
            po = await mongo_db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
            if not po:
                raise HTTPException(status_code=404, detail=f"PO not found: {po_id}")

            reference_pi_ids = po.get("reference_pi_ids", [])
            if not reference_pi_ids and po.get("reference_pi_id"):
                reference_pi_ids = [po.get("reference_pi_id")]
            all_pi_ids.extend(reference_pi_ids)

            if not company_id_from_po and po.get("company_id"):
                company_id_from_po = po["company_id"]

            for po_item in po.get("line_items", []):
                product_id = po_item.get("product_id")
                po_item_id = po_item.get("id")
                if product_id not in aggregated_po_quantities:
                    aggregated_po_quantities[product_id] = 0
                aggregated_po_quantities[product_id] += float(po_item.get("quantity", 0))

        # ---- QUANTITY VALIDATION ----
        for inward_item in inward_data.get("line_items", []):
            product_id = inward_item.get("product_id")
            sku = inward_item.get("sku")
            po_line_item_id = inward_item.get("id")
            inward_qty = float(inward_item.get("quantity", 0))

            if product_id in aggregated_po_quantities:
                total_po_qty = aggregated_po_quantities[product_id]

                already_inwarded = 0
                for po_id in po_ids:
                    async for existing_inward in mongo_db.inward_stock.find(
                        {"po_id": po_id, "is_active": True},
                        {"_id": 0}
                    ):
                        for existing_item in existing_inward.get("line_items", []):
                            matched = False
                            if po_line_item_id and existing_item.get("id") == po_line_item_id:
                                matched = True
                            elif sku and existing_item.get("sku") == sku:
                                matched = True
                            elif product_id and existing_item.get("product_id") == product_id:
                                matched = True
                            
                            if matched:
                                already_inwarded += float(existing_item.get("quantity", 0))

                # Also deduct In-Transit quantities
                in_transit = 0
                for po_id in po_ids:
                    async for pickup in mongo_db.pickup_in_transit.find(
                        {"po_id": po_id, "is_active": True, "is_inwarded": {"$ne": True}},
                        {"_id": 0}
                    ):
                        for p_item in pickup.get("line_items", []):
                             matched = False
                             if po_line_item_id and p_item.get("id") == po_line_item_id:
                                 matched = True
                             elif sku and p_item.get("sku") == sku:
                                 matched = True
                             elif product_id and p_item.get("product_id") == product_id:
                                 matched = True
                             
                             if matched:
                                 in_transit += float(p_item.get("quantity", 0))

                total_unavailable = already_inwarded + in_transit
                if (already_inwarded + in_transit + inward_qty) > total_po_qty:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot inward {product_id}: total (inwarded+transit+new={already_inwarded + in_transit + inward_qty}) exceeds PO qty ({total_po_qty}). Already Inwarded: {already_inwarded}, In Transit: {in_transit}"
                    )

        all_pi_ids = list(set(all_pi_ids))

        if all_pi_ids:
            inward_data["pi_id"] = all_pi_ids[0]
            inward_data["pi_ids"] = all_pi_ids

        if company_id_from_po and not inward_data.get("company_id"):
            inward_data["company_id"] = company_id_from_po

    # ------------------- CREATE INWARD ENTRY -------------------
    inward_dict = {
        "id": str(uuid.uuid4()),
        "manual":inward_data.get("manual"),
        "inward_invoice_no": inward_data.get("inward_invoice_no"),
        "date": inward_data.get("date"),
        "po_id": po_ids[0] if po_ids else None,
        "po_ids": po_ids,
        "pi_id": inward_data.get("pi_id"),
        "pi_ids": inward_data.get("pi_ids", [inward_data.get("pi_id")] if inward_data.get("pi_id") else []),
        "company_id": inward_data.get("company_id"),
        "warehouse_id": inward_data.get("warehouse_id"),
        "inward_type": inward_data.get("inward_type"),
        "source_type": inward_data.get("source_type"),
        "status": inward_data.get("status", "Received"),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
        "line_items": []
    }

    # ------------------- PROCESS LINE ITEMS -------------------
    total_amount = 0

    for item in inward_data.get("line_items", []):
        po_line_item_id = item.get("id")
        product_id = item.get("product_id")
        inward_qty = float(item.get("quantity", 0))
        rate = float(item.get("rate", 0))

        total_po_qty = aggregated_po_quantities.get(product_id, 0)

        already_inwarded = 0
        for po_id in po_ids:
            async for existing_inward in mongo_db.inward_stock.find(
                {"po_id": po_id, "is_active": True},
                {"_id": 0}
            ):
                for existing_item in existing_inward.get("line_items", []):

                    if existing_item.get("id") == po_line_item_id:
                        already_inwarded += float(existing_item.get("quantity", 0))

        remaining = total_po_qty - (already_inwarded + inward_qty)

        line_item = {
            "id": po_line_item_id,
            "product_id": product_id,
            "product_name": item.get("product_name"),
            "sku": item.get("sku"),
            "quantity": inward_qty,
            "rate": rate,
            "amount": inward_qty * rate,

            # informational only
            "total_po_qty": total_po_qty,
            "already_inwarded": already_inwarded,
            "remaining": remaining
        }

        total_amount += line_item["amount"]
        inward_dict["line_items"].append(line_item)

    inward_dict["total_amount"] = total_amount
    inward_dict["line_items_count"] = len(inward_dict["line_items"])

    # ------------------- SAVE INWARD -------------------
    await mongo_db.inward_stock.insert_one(inward_dict)

    await update_stock_tracking(inward_dict, "inward")

    await mongo_db.audit_logs.insert_one({
        "action": "inward_stock_created",
        "user_id": current_user["id"],
        "entity_id": inward_dict["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    inward_dict.pop("_id", None)
    return inward_dict



# ==================== PICKUP (IN-TRANSIT) ROUTES ====================

@api_router.post("/pickups")
async def create_pickup(
    pickup_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Create a pickup (in-transit) entry.
    Validates that the quantity does not exceed PO quantity - (Already Inwarded + In Transit).
    Optimized: Bulk fetching for validation.
    """
    po_ids = pickup_data.get("po_ids", [])
    if not po_ids and pickup_data.get("po_id"):
        po_ids = [pickup_data["po_id"]]

    logger.info(f"🚚 Creating pickup. POs: {po_ids}, Warehouse: {pickup_data.get('warehouse_id')}")
    
    if not po_ids:
        raise HTTPException(status_code=400, detail="PO ID(s) is required")

    # 1. Fetch all POs and build quantity map
    aggregated_po_quantities = {}
    po_list = []
    company_id = None

    for po_id in po_ids:
        po = await mongo_db.purchase_orders.find_one({"id": po_id, "is_active": True}, {"_id": 0})
        if not po:
            raise HTTPException(status_code=404, detail=f"PO {po_id} not found")
        po_list.append(po)
        if not company_id:
            company_id = po.get("company_id")
        
        for item in po.get("line_items", []):
            product_id = item.get("product_id")
            sku = item.get("sku")
            key = product_id if product_id else sku
            if key:
                aggregated_po_quantities[key] = aggregated_po_quantities.get(key, 0) + float(item.get("quantity", 0))

    # 2. Bulk fetch Inward and In-Transit data for all validation
    all_inwards = await mongo_db.inward_stock.find({
        "$or": [{"po_id": {"$in": po_ids}}, {"po_ids": {"$in": po_ids}}],
        "is_active": True
    }, {"_id": 0}).to_list(length=None)

    all_pickups = await mongo_db.pickup_in_transit.find({
        "$or": [{"po_id": {"$in": po_ids}}, {"po_ids": {"$in": po_ids}}],
        "is_active": True,
        "is_inwarded": False
    }, {"_id": 0}).to_list(length=None)

    # 3. Process and Validate Line Items
    processed_line_items = []
    for item in pickup_data.get("line_items", []):
        product_id = item.get("product_id")
        sku = item.get("sku")
        quantity = float(item.get("quantity", 0))
        key = product_id if product_id else sku
        
        if quantity <= 0:
            continue
            
        if not key:
             raise HTTPException(status_code=400, detail=f"Line item missing both product_id and sku for {item.get('product_name')}")

        total_po_qty = aggregated_po_quantities.get(key, 0)
        
        # Calculate used quantity from bulk data
        used_qty = 0
        for inward in all_inwards:
            for line in inward.get("line_items", []):
                if (product_id and line.get("product_id") == product_id) or (sku and line.get("sku") == sku):
                    used_qty += float(line.get("quantity", 0))

        for existing_pickup in all_pickups:
            for line in existing_pickup.get("line_items", []):
                if (product_id and line.get("product_id") == product_id) or (sku and line.get("sku") == sku):
                    used_qty += float(line.get("quantity", 0))
        
        if (used_qty + quantity) > (total_po_qty + 0.001):
            error_msg = f"Cannot pickup {item.get('product_name')}. Total ({used_qty} used + {quantity} new) exceeds PO Qty ({total_po_qty})."
            raise HTTPException(status_code=400, detail=error_msg)
            
        processed_line_items.append({
            "id": str(uuid.uuid4()),
            "po_line_item_id": item.get("id"),
            "product_id": product_id,
            "product_name": item.get("product_name"),
            "sku": item.get("sku"),
            "quantity": quantity,
            "rate": float(item.get("rate", 0)),
            "amount": quantity * float(item.get("rate", 0))
        })

    if not processed_line_items:
         raise HTTPException(status_code=400, detail="No valid line items to pickup")

    pickup_entry = {
        "id": str(uuid.uuid4()),
        "po_ids": po_ids,
        "po_id": po_ids[0], 
        "po_voucher_no": po_list[0].get("voucher_no"),
        "pickup_date": pickup_data.get("pickup_date"),
        "manual": pickup_data.get("manual"),
        "notes": pickup_data.get("notes"),
        "warehouse_id": pickup_data.get("warehouse_id"),
        "line_items": processed_line_items,
        "is_inwarded": False,
        "is_active": True,
        "company_id": company_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await mongo_db.pickup_in_transit.insert_one(pickup_entry)
    
    # Audit log
    await mongo_db.audit_logs.insert_one({
        "action": "pickup_created",
        "user_id": current_user["id"],
        "entity_id": pickup_entry["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    pickup_entry.pop("_id", None)
    return pickup_entry


@api_router.get("/pickups")
async def list_pickups(
    po_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all active pickup entries with optional PO filter"""
    try:
        query = {"is_active": True, "is_inwarded": {"$ne": True}}
        if po_id:
            query["po_id"] = po_id
        
        pickups = []
        async for pickup in mongo_db.pickup_in_transit.find(query, {"_id": 0}).sort("created_at", -1):
            pickups.append(pickup)
        
        return pickups
    except Exception as e:
        logger.error(f"Error fetching pickups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/pickups/export")
async def export_pickups(
    format: str = "json",
    po_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Export pickup entries"""
    query = {"is_active": True}
    if po_id:
        query["po_id"] = po_id
    
    pickups = []
    async for pickup in mongo_db.pickup_in_transit.find(query, {"_id": 0}).sort("created_at", -1):
        pickups.append(pickup)
    
    if format == "csv":
        return {"data": pickups, "format": "csv"}
    
    return pickups

@api_router.get("/pickups/{pickup_id}")
async def get_pickup(
    pickup_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get a single pickup entry"""
    pickup = await mongo_db.pickup_in_transit.find_one({"id": pickup_id, "is_active": True}, {"_id": 0})
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup entry not found")
    return pickup

@api_router.post("/{pickup_id}/inward")
async def inward_from_pickup(
    pickup_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Move quantities from pickup (in-transit) to a NEW Inward Stock entry.
    """
    logger.info(f"🚀 EXECUTING inward_from_pickup for ID: {pickup_id}")
    pickup = await mongo_db.pickup_in_transit.find_one({"id": pickup_id, "is_active": True})
    if not pickup:
        logger.error(f"❌ Inward Failed: Pickup {pickup_id} not found")
        raise HTTPException(status_code=404, detail="Pickup entry not found")

    if pickup.get("is_inwarded"):
        logger.error(f"❌ Inward Failed: Pickup {pickup_id} already marked inwarded")
        raise HTTPException(status_code=400, detail="Pickup already inwarded")

    # Support multiple POs if present
    po_ids = pickup.get("po_ids", [pickup.get("po_id")] if pickup.get("po_id") else [])
    
    # Calculate aggregated PO quantities and collect linked PI IDs
    aggregated_po_quantities = {}
    all_pi_ids = []
    if po_ids:
        for p_id in po_ids:
            po = await mongo_db.purchase_orders.find_one({"id": p_id}, {"_id": 0})
            if po:
                # Collect PIs
                ref_pi_ids = po.get("reference_pi_ids", [])
                if not ref_pi_ids and po.get("reference_pi_id"):
                    ref_pi_ids = [po.get("reference_pi_id")]
                all_pi_ids.extend(ref_pi_ids)

                for po_item in po.get("line_items", []):
                    prod_id = po_item.get("product_id")
                    sku = po_item.get("sku")
                    key = prod_id if prod_id else sku
                    if key:
                        aggregated_po_quantities[key] = aggregated_po_quantities.get(key, 0) + float(po_item.get("quantity", 0))

    all_pi_ids = list(set(all_pi_ids)) # Deduplicate

    # 1. Create the NEW Inward Entry
    inward_dict = {
        "id": str(uuid.uuid4()),
        "manual": pickup.get("manual", ""),
        "inward_invoice_no": pickup.get("manual", ""),
        "date": datetime.now(timezone.utc).isoformat().split('T')[0],
        "po_id": po_ids[0] if po_ids else None,
        "po_ids": po_ids,
        "pi_id": all_pi_ids[0] if all_pi_ids else None,
        "pi_ids": all_pi_ids,
        "warehouse_id": pickup.get("warehouse_id"),
        "inward_type": "warehouse",
        "source_type": "pickup_inward",
        "source_id": pickup_id,
        "status": "Received",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
        "line_items": []
    }

    total_amount = 0
    for pickup_item in pickup.get("line_items", []):
        p_id = pickup_item.get("product_id")
        sku = pickup_item.get("sku")
        key = p_id if p_id else sku
        qty = float(pickup_item.get("quantity", 0))
        rate = float(pickup_item.get("rate", 0))
        
        total_p_qty = aggregated_po_quantities.get(key, 0)
        
        inward_item = {
            "id": pickup_item.get("po_line_item_id") or str(uuid.uuid4()),
            "product_id": p_id,
            "product_name": pickup_item.get("product_name"),
            "sku": sku,
            "quantity": qty,
            "rate": rate,
            "amount": qty * rate,
            "total_po_qty": total_p_qty
        }
        total_amount += inward_item["amount"]
        inward_dict["line_items"].append(inward_item)

    inward_dict["total_amount"] = total_amount
    inward_dict["line_items_count"] = len(inward_dict["line_items"])

    # 2. Insert Inward entry
    await mongo_db.inward_stock.insert_one(inward_dict)
    
    # 3. Update stock tracking levels
    await update_stock_tracking(inward_dict, "inward")

    # 4. Mark pickup as inwarded
    await mongo_db.pickup_in_transit.update_one(
        {"id": pickup_id},
        {"$set": {"is_inwarded": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    # 5. Audit log
    await mongo_db.audit_logs.insert_one({
        "action": "inward_from_pickup",
        "user_id": current_user["id"],
        "entity_id": inward_dict["id"],
        "source_pickup_id": pickup_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Inward completed successfully", "inward_id": inward_dict["id"]}

@api_router.put("/pickups/{pickup_id}")
async def update_pickup(
    pickup_id: str,
    pickup_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Update a pickup entry"""
    pickup = await mongo_db.pickup_in_transit.find_one({"id": pickup_id}, {"_id": 0})
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup entry not found")
        
    update_data = {
        "pickup_date": pickup_data.get("pickup_date"),
        "manual": pickup_data.get("manual"),
        "notes": pickup_data.get("notes"),
        "warehouse_id": pickup_data.get("warehouse_id"),
        "line_items": pickup_data.get("line_items", []),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    await mongo_db.pickup_in_transit.update_one({"id": pickup_id}, {"$set": update_data})
    
    updated_pickup = await mongo_db.pickup_in_transit.find_one({"id": pickup_id}, {"_id": 0})
    return updated_pickup

@api_router.delete("/pickups/{pickup_id}")
async def delete_pickup(
    pickup_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete (soft) a pickup entry"""
    pickup = await mongo_db.pickup_in_transit.find_one({"id": pickup_id})
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup entry not found")
        
    await mongo_db.pickup_in_transit.update_one({"id": pickup_id}, {"$set": {"is_active": False}})
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "pickup_deleted",
        "user_id": current_user["id"],
        "entity_id": pickup_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Pickup entry deleted successfully"}

# ==================== INWARD STOCK ROUTES ====================

@api_router.get("/inward-stock")

async def get_inward_stock(
    inward_type: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all inward stock entries with optional filtering"""
    query = {"is_active": True}
    if inward_type:
        query["inward_type"] = inward_type
    
    inward_entries = []
    async for entry in mongo_db.inward_stock.find(query, {"_id": 0}):
        # Get company details
        company_id = entry.get("company_id")
        
        # Always fetch PO details if po_id exists to get voucher_no
        po_id = entry.get("po_id")
        if po_id:
            po = await mongo_db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
            if po:
                entry["po_voucher_no"] = po.get("voucher_no")
                if not company_id:
                    company_id = po.get("company_id")
        
        if company_id:
            company = await mongo_db.companies.find_one({"id": company_id}, {"_id": 0})
            entry["company"] = company
                
        # Get warehouse details
        if entry.get("warehouse_id"):
            warehouse = await mongo_db.warehouses.find_one({"id": entry["warehouse_id"]}, {"_id": 0})
            entry["warehouse"] = warehouse
            
        inward_entries.append(entry)
    
    return inward_entries

# ==================== INWARD STOCK ENHANCEMENTS ====================
@api_router.get("/inward-stock/direct-entries")
async def get_direct_inward_entries(
    warehouse_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get Direct Inward entries for linking to Direct Export"""
    query = {
        "source_type": "direct_inward",
        "is_active": True
    }
    if warehouse_id:
        query["warehouse_id"] = warehouse_id
    
    direct_entries = []
    async for entry in mongo_db.inward_stock.find(query, {"_id": 0}).sort("date", -1):
        # Get warehouse details
        if entry.get("warehouse_id"):
            warehouse = await mongo_db.warehouses.find_one({"id": entry["warehouse_id"]}, {"_id": 0})
            entry["warehouse"] = warehouse
        
        # Calculate remaining quantity (not yet dispatched)
        for item in entry.get("line_items", []):
            # Check how much has been dispatched via direct export
            dispatched_qty = 0.0
            async for outward in mongo_db.outward_stock.find({
                "dispatch_type": "direct_export",
                "inward_invoice_ids": entry["id"],
                "is_active": True
            }, {"_id": 0}):
                for out_item in outward.get("line_items", []):
                    if out_item.get("product_id") == item.get("product_id"):
                        dispatched_qty += float(out_item.get("dispatch_quantity", 0) or out_item.get("quantity", 0))
            
            item["remaining_quantity"] = float(item.get("quantity", 0)) - dispatched_qty
        
        direct_entries.append(entry)
    
    return direct_entries

# Pickup-pending endpoint removed - in-transit feature deprecated

# Transfer-to-warehouse endpoint removed - in-transit feature deprecated

@api_router.get("/inward-stock/export")
async def export_inward_stock(
    format: str = "json",
    inward_type: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Export inward stock entries"""
    query = {"is_active": True}
    if inward_type:
        query["inward_type"] = inward_type
    
    inward_entries = []
    async for entry in mongo_db.inward_stock.find(query, {"_id": 0}).sort("created_at", -1):
        inward_entries.append(entry)
    
    if format == "csv":
        return {"data": inward_entries, "format": "csv"}
    
    return inward_entries


@api_router.get("/inward-stock/{inward_id}")
async def get_inward_stock_detail(
    inward_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed inward stock entry"""
    entry = await mongo_db.inward_stock.find_one({"id": inward_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Inward entry not found")
    
    # Get related data
    if entry.get("po_id"):
        po = await mongo_db.purchase_orders.find_one({"id": entry["po_id"]}, {"_id": 0})
        entry["po"] = po
        
        # Get PI details if linked (support both single and multiple PIs)
        if po:
            reference_pi_ids = po.get("reference_pi_ids", [])
            if not reference_pi_ids and po.get("reference_pi_id"):
                # Backward compatibility
                reference_pi_ids = [po.get("reference_pi_id")]
            
            if reference_pi_ids:
                pi_details = []
                for pi_id in reference_pi_ids:
                    pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
                    if pi:
                        pi_details.append(pi)
                
                entry["pis"] = pi_details  # Multiple PIs
                if pi_details:
                    entry["pi"] = pi_details[0]  # For backward compatibility
    
    if entry.get("warehouse_id"):
        warehouse = await mongo_db.warehouses.find_one({"id": entry["warehouse_id"]}, {"_id": 0})
        entry["warehouse"] = warehouse
    
    return entry

@api_router.put("/inward-stock/{inward_id}")
async def update_inward_stock(
    inward_id: str,
    inward_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Update inward stock entry"""
    entry = await mongo_db.inward_stock.find_one({"id": inward_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Inward entry not found")
    
    update_data = {
        "inward_invoice_no": inward_data.get("inward_invoice_no"),
        "date": inward_data.get("date"),
        "warehouse_id": inward_data.get("warehouse_id"),
        "status": inward_data.get("status", entry.get("status")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    # Update line items if provided
    if "line_items" in inward_data:
        line_items = []
        total_amount = 0
        for item in inward_data["line_items"]:
            line_item = {
                "id": item.get("id", str(uuid.uuid4())),
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "sku": item.get("sku"),
                "quantity": float(item.get("quantity", 0)),
                "rate": float(item.get("rate", 0)),
                "amount": float(item.get("quantity", 0)) * float(item.get("rate", 0))
            }
            total_amount += line_item["amount"]
            line_items.append(line_item)
        
        update_data["line_items"] = line_items
        update_data["total_amount"] = total_amount
        update_data["line_items_count"] = len(line_items)
    
    await mongo_db.inward_stock.update_one({"id": inward_id}, {"$set": update_data})
    
    updated_entry = await mongo_db.inward_stock.find_one({"id": inward_id}, {"_id": 0})
    return updated_entry

@api_router.delete("/inward-stock/{inward_id}")
async def delete_inward_stock(
    inward_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Soft delete inward stock entry"""
    entry = await mongo_db.inward_stock.find_one({"id": inward_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Inward entry not found")
    
    # Check if any quantity from this inward batch has already been dispatched
    # We check the stock_tracking entries for this inward_id
    has_dispatched = await mongo_db.stock_tracking.count_documents({
        "inward_entry_id": inward_id,
        "quantity_outward": {"$gt": 0}
    })
    
    if has_dispatched > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete: Part of this inward stock has already been dispatched/outwarded."
        )
    
    # Delete linked stock tracking entries
    # Regardless of type, if it has tracking entries, they must be removed
    delete_result = await mongo_db.stock_tracking.delete_many({"inward_entry_id": inward_id})
    if delete_result.deleted_count > 0:
        print(f"       ✅ Removed {delete_result.deleted_count} summary entries for inward: {inward_id}")
        
        # Log this specific sub-action
        await mongo_db.audit_logs.insert_one({
            "action": "stock_tracking_deleted_cascade",
            "parent_id": inward_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    await mongo_db.inward_stock.update_one({"id": inward_id}, {"$set": {"is_active": False}})
    return {"message": "Inward entry deleted successfully"}


# Helper function to update central stock tracking
async def update_stock_tracking(inward_entry: dict, operation: str):
    """
    STOCK SUMMARY - Transaction-Based Tracking
    Creates ONE stock_tracking entry per inward transaction (not aggregated)
    Each row shows: Inward qty from that entry, Outward qty dispatched from it, Remaining
    """
    try:
        # Skip if no warehouse_id (invalid entry)
        if not inward_entry.get("warehouse_id"):
            print(f"  ⚠️  Skipping stock tracking - no warehouse_id")
            return
        
        print(f"  🔄 Creating stock tracking entries for inward: {inward_entry.get('inward_invoice_no')}")
        
        # Fetch warehouse details
        warehouse = await mongo_db.warehouses.find_one(
            {"id": inward_entry.get("warehouse_id")}, 
            {"_id": 0, "name": 1}
        )
        warehouse_name = warehouse.get("name") if warehouse else "Unknown"
        
        # Fetch company details
        company_id = inward_entry.get("company_id")
        company_name = "Unknown"
        if company_id:
            company = await mongo_db.companies.find_one(
                {"id": company_id}, 
                {"_id": 0, "name": 1}
            )
            company_name = company.get("name") if company else "Unknown"
        
        # Get PI and PO information
        pi_id = inward_entry.get("pi_id")
        pi_ids = inward_entry.get("pi_ids", [])
        if pi_id and pi_id not in pi_ids:
            pi_ids.append(pi_id)
        
        # Fetch PI voucher numbers
        pi_numbers = []
        for pid in pi_ids:
            if pid:
                pi = await mongo_db.proforma_invoices.find_one({"id": pid}, {"_id": 0, "voucher_no": 1})
                if pi and pi.get("voucher_no"):
                    pi_numbers.append(pi["voucher_no"])
        pi_number_str = ", ".join(pi_numbers) if pi_numbers else "N/A"
        
        # Get PO number
        po_number = "N/A"
        if inward_entry.get("po_id"):
            po = await mongo_db.purchase_orders.find_one(
                {"id": inward_entry.get("po_id")}, 
                {"_id": 0, "voucher_no": 1}
            )
            po_number = po.get("voucher_no") if po else "N/A"
        
        # Determine entry type
        entry_type = "direct" if inward_entry.get("source_type") == "direct_inward" else "regular"
        
        # Create SEPARATE stock_tracking entry for EACH product in this inward entry
        for item in inward_entry.get("line_items", []):
            try:
                # Get product category and color
                product = await mongo_db.products.find_one(
                    {"id": item["product_id"]}, 
                    {"_id": 0, "category": 1, "color": 1}
                )
                category = product.get("category") if product else "Unknown"
                color = product.get("color") if product else "N/A"
                
                print(f"     - Creating entry for: {item.get('product_name')} (Qty: {item.get('quantity')})")
                
                # Create NEW stock entry for this transaction (NO aggregation)
                stock_entry = {
                    "id": str(uuid.uuid4()),
                    "inward_entry_id": inward_entry.get("id"),  # Link to source inward entry
                    "inward_invoice_no": inward_entry.get("inward_invoice_no"),  # For reference
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "sku": item["sku"],
                    "color": color,
                    "category": category,
                    "warehouse_id": inward_entry.get("warehouse_id"),
                    "warehouse_name": warehouse_name,
                    "company_id": company_id,
                    "company_name": company_name,
                    "pi_number": pi_number_str,
                    "po_number": po_number,
                    "entry_type": entry_type,
                    "status": "Inward",  # Status for warehouse inward
                    "quantity_inward": item["quantity"],  # Exact quantity from THIS entry only
                    "quantity_outward": 0,  # Will be updated when dispatched
                    "remaining_stock": item["quantity"],  # Initially same as inward
                    "inward_date": inward_entry.get("date"),
                    "last_inward_date": datetime.now(timezone.utc).isoformat(),
                    "last_outward_date": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
                await mongo_db.stock_tracking.insert_one(stock_entry)
                print(f"       ✅ Created transaction entry: Inward {item['quantity']}, Remaining: {item['quantity']}")
            except Exception as item_error:
                print(f"       ❌ Error processing item {item.get('product_name')}: {str(item_error)}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"  ✅ Stock tracking entries created (transaction-based)")
    except Exception as e:
        print(f"  ❌ CRITICAL ERROR in update_stock_tracking: {str(e)}")
        import traceback
        traceback.print_exc()

# In-Transit tracking functions removed - feature deprecated

@api_router.get("/stock-summary")
async def get_stock_summary(
    warehouse_id: Optional[str] = None,
    company_id: Optional[str] = None,
    pi_number: Optional[str] = None,
    po_number: Optional[str] = None,
    sku: Optional[str] = None,
    category: Optional[str] = None,
    entry_type: Optional[str] = None,  # NEW: Filter by entry_type (regular/direct)
    current_user: dict = Depends(get_current_active_user)
):
    """
    STOCK SUMMARY REBUILD - Get stock summary from stock_tracking collection
    Optimized: Uses aggregation for in-transit calculation to avoid N+1 issues.
    """
    query = {}
    if warehouse_id: query["warehouse_id"] = warehouse_id
    if company_id: query["company_id"] = company_id
    if pi_number: query["pi_number"] = {"$regex": pi_number, "$options": "i"}
    if po_number: query["po_number"] = {"$regex": po_number, "$options": "i"}
    if sku: query["sku"] = {"$regex": sku, "$options": "i"}
    if category: query["category"] = {"$regex": category, "$options": "i"}
    if entry_type: query["entry_type"] = entry_type
    
    # 1. Optimize: Aggregate all pending in-transit quantities by SKU
    it_pipeline = [
        {"$match": {"is_active": True, "is_inwarded": {"$ne": True}}},
        {"$unwind": "$line_items"},
        {"$group": {"_id": "$line_items.sku", "total": {"$sum": "$line_items.quantity"}}}
    ]
    it_results = await mongo_db.pickup_in_transit.aggregate(it_pipeline).to_list(length=None)
    pending_in_transit = {r["_id"]: r["total"] for r in it_results if r["_id"]}

    # 2. Fetch stock entries
    stock_entries = []
    async for stock in mongo_db.stock_tracking.find(query, {"_id": 0}):
        last_updated_str = stock.get("last_updated", stock.get("created_at"))
        try:
            last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
            stock_age_days = (datetime.now(timezone.utc) - last_updated).days
        except:
            stock_age_days = "N/A"
        
        remaining = stock.get("remaining_stock", 0)
        stock_status = "Low Stock" if remaining < 10 else "Normal"
        if remaining <= 0: stock_status = "Out of Stock"
        
        in_transit_qty = pending_in_transit.get(stock.get("sku"), 0)
        
        stock_entries.append({
            "id": stock.get("id"),
            "product_id": stock.get("product_id"),
            "product_name": stock.get("product_name"),
            "sku": stock.get("sku"),
            "color": stock.get("color", "N/A"),
            "pi_po_number": f"{stock.get('pi_number', 'N/A')} / {stock.get('po_number', 'N/A')}",
            "pi_number": stock.get("pi_number", "N/A"),
            "po_number": stock.get("po_number", "N/A"),
            "category": stock.get("category", "Unknown"),
            "warehouse_id": stock.get("warehouse_id"),
            "warehouse_name": stock.get("warehouse_name", "Unknown"),
            "company_id": stock.get("company_id"),
            "company_name": stock.get("company_name", "Unknown"),
            "in_transit": in_transit_qty,
            "quantity_inward": stock.get("quantity_inward", 0),
            "quantity_outward": stock.get("quantity_outward", 0),
            "remaining_stock": remaining,
            "status": stock_status,
            "age_days": stock_age_days,
            "last_updated": last_updated_str
        })
    
    stock_entries.sort(key=lambda x: x["remaining_stock"])
    return stock_entries


@api_router.get("/stock-summary/debug/{product_id}")
async def debug_stock_tracking(
    product_id: str,
    warehouse_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Debug endpoint to check stock_tracking data for a specific product"""
    query = {"product_id": product_id}
    if warehouse_id:
        query["warehouse_id"] = warehouse_id
    
    tracking_entries = []
    async for entry in mongo_db.stock_tracking.find(query, {"_id": 0}):
        tracking_entries.append(entry)
    
    # Also get outward entries for this product
    outward_entries = []
    outward_query = {}
    if warehouse_id:
        outward_query["warehouse_id"] = warehouse_id
    
    async for outward in mongo_db.outward_stock.find(outward_query, {"_id": 0}):
        for item in outward.get("line_items", []):
            if item.get("product_id") == product_id:
                outward_entries.append({
                    "outward_id": outward.get("id"),
                    "export_invoice_no": outward.get("export_invoice_no"),
                    "dispatch_type": outward.get("dispatch_type"),
                    "date": outward.get("date"),
                    "quantity": item.get("dispatch_quantity") or item.get("quantity", 0),
                    "product_name": item.get("product_name")
                })
    
    return {
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "stock_tracking_entries": tracking_entries,
        "outward_entries": outward_entries,
        "total_tracking_entries": len(tracking_entries),
        "total_outward_entries": len(outward_entries)
    }

@api_router.delete("/stock-summary/{stock_id}")
async def delete_stock_summary(
    stock_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    STOCK SUMMARY REBUILD - Delete stock entry by ID
    Note: Does not affect inward/outward records, only removes from stock tracking
    """
    # Check if stock entry exists
    stock = await mongo_db.stock_tracking.find_one({"id": stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock entry not found")
    
    # Delete the stock entry
    await mongo_db.stock_tracking.delete_one({"id": stock_id})
    
    # Log the action
    await mongo_db.audit_logs.insert_one({
        "action": "stock_summary_deleted",
        "user_id": current_user["id"],
        "entity_id": stock_id,
        "product_id": stock.get("product_id"),
        "warehouse_id": stock.get("warehouse_id"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Stock entry deleted successfully", "deleted_id": stock_id}

@api_router.get("/low-stock-alerts")
async def get_low_stock_alerts(
    threshold: Optional[float] = 10.0,
    current_user: dict = Depends(get_current_active_user)
):
    """Get low stock alerts for dashboard"""
    alerts = []
    async for stock in mongo_db.stock_tracking.find({}, {"_id": 0}):
        if stock["current_stock"] <= threshold:
            # Get warehouse name
            warehouse_name = None
            if stock.get("warehouse_id"):
                warehouse = await mongo_db.warehouses.find_one({"id": stock["warehouse_id"]}, {"_id": 0})
                warehouse_name = warehouse.get("name") if warehouse else None
            
            alert = {
                "product_id": stock["product_id"],
                "product_name": stock["product_name"],
                "sku": stock["sku"],
                "warehouse_id": stock.get("warehouse_id"),
                "warehouse_name": warehouse_name,
                "current_stock": stock["current_stock"],
                "alert_level": "critical" if stock["current_stock"] == 0 else "warning",
                "message": f"{stock['product_name']} is {'out of stock' if stock['current_stock'] == 0 else 'running low'} in {warehouse_name or 'Unknown Warehouse'}"
            }
            alerts.append(alert)
    
    # Sort by stock level (lowest first)
    alerts.sort(key=lambda x: x["current_stock"])
    
    return alerts

# ==================== STOCK TRANSACTION HISTORY ====================
@api_router.get("/stock-transactions/{product_id}/{warehouse_id}")
async def get_stock_transactions(
    product_id: str,
    warehouse_id: str = "",
    current_user: dict = Depends(get_current_active_user)
):
    """
    STOCK SUMMARY REBUILD - Get transaction history for View action
    Returns: Warehouse Inward + Direct Inward + Export Invoice + Direct Export transactions
    """
    transactions = []
    
    # Build query for warehouse (handle empty warehouse_id)
    warehouse_query = {"warehouse_id": warehouse_id} if warehouse_id else {}
    
    # Get Warehouse Inward transactions (inward_type = "warehouse")
    async for inward in mongo_db.inward_stock.find(
        {**warehouse_query, "inward_type": "warehouse", "is_active": True},
        {"_id": 0}
    ).sort("date", -1):
        for item in inward.get("line_items", []):
            if item.get("product_id") == product_id:
                transactions.append({
                    "type": "inward",
                    "transaction_id": inward["id"],
                    "date": inward["date"],
                    "reference_no": inward.get("inward_invoice_no", "N/A"),
                    "inward_type": "Warehouse Inward",
                    "quantity": item["quantity"],
                    "rate": item.get("rate", 0),
                    "amount": item.get("amount", 0),
                    "product_name": item.get("product_name"),
                    "sku": item.get("sku"),
                    "created_at": inward.get("created_at")
                })
    
    # Get Direct Inward transactions (source_type = "direct_inward")
    async for inward in mongo_db.inward_stock.find(
        {**warehouse_query, "source_type": "direct_inward", "is_active": True},
        {"_id": 0}
    ).sort("date", -1):
        for item in inward.get("line_items", []):
            if item.get("product_id") == product_id:
                transactions.append({
                    "type": "inward",
                    "transaction_id": inward["id"],
                    "date": inward["date"],
                    "reference_no": inward.get("inward_invoice_no", "N/A"),
                    "inward_type": "Direct Inward",
                    "quantity": item["quantity"],
                    "rate": item.get("rate", 0),
                    "amount": item.get("amount", 0),
                    "product_name": item.get("product_name"),
                    "sku": item.get("sku"),
                    "created_at": inward.get("created_at")
                })
    
    # Get all Outward transactions and filter for regular/direct
    outward_query = {**warehouse_query, "is_active": True}
    all_outwards = []
    async for outward in mongo_db.outward_stock.find(outward_query, {"_id": 0}):
        all_outwards.append(outward)
    
    linked_plan_ids = {o.get("dispatch_plan_id") for o in all_outwards if o.get("dispatch_plan_id")}
    
    for outward in all_outwards:
        # SKIP dispatch plans that have already been converted
        if outward.get("dispatch_type") == "dispatch_plan" and outward.get("id") in linked_plan_ids:
            continue
            
        # Match type for this view
        d_type = outward.get("dispatch_type")
        type_label = "Export Invoice"
        if d_type == "dispatch_plan": type_label = "Dispatch Plan"
        elif d_type == "direct_export": type_label = "Direct Export"
        
        for item in outward.get("line_items", []):
            if item.get("product_id") == product_id:
                transactions.append({
                    "type": "outward",
                    "transaction_id": outward["id"],
                    "date": outward["date"],
                    "reference_no": outward.get("export_invoice_no", "N/A"),
                    "dispatch_type": type_label,
                    "quantity": item.get("dispatch_quantity") or item.get("quantity", 0),
                    "rate": item.get("rate", 0),
                    "amount": item.get("amount", 0),
                    "product_name": item.get("product_name"),
                    "sku": item.get("sku"),
                    "created_at": outward.get("created_at")
                })
    
    # Sort by date (most recent first)
    transactions.sort(key=lambda x: x["date"], reverse=True)
    
    return {
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "total_transactions": len(transactions),
        "transactions": transactions
    }

# ==================== OUTWARD OPERATIONS ====================
@api_router.post("/outward-stock")
async def create_outward_stock(
    outward_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Create outward stock entry (Dispatch Plan, Export Invoice, or Direct Export)"""
    
    # Log incoming data for debugging - BOTH to console AND file
    import sys
    log_msg = f"\n{'='*80}\n"
    log_msg += f"🚀 CREATE OUTWARD STOCK REQUEST RECEIVED\n"
    log_msg += f"{'='*80}\n"
    log_msg += f"📥 Dispatch Type: {outward_data.get('dispatch_type')}\n"
    log_msg += f"📥 Company ID: {outward_data.get('company_id')}\n"
    log_msg += f"📥 Warehouse ID: {outward_data.get('warehouse_id')}\n"
    log_msg += f"📥 Line Items Count: {len(outward_data.get('line_items', []))}\n"
    log_msg += f"📥 User: {current_user.get('username', 'Unknown')}\n"
    for idx, item in enumerate(outward_data.get('line_items', []), 1):
        qty = item.get('dispatch_quantity') or item.get('quantity', 0)
        log_msg += f"   Item {idx}: {item.get('product_name')} - Qty: {qty} (Product ID: {item.get('product_id')})\n"
    log_msg += f"{'='*80}\n"
    
    print(log_msg, flush=True)
    sys.stdout.flush()
    
    # Also write to file
    try:
        with open("outward_stock_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now(timezone.utc).isoformat()}]\n")
            f.write(log_msg)
            f.flush()
    except Exception as e:
        print(f"Error writing to log file: {e}")
    
    # Log to both console and file
    def log_this(msg):
        print(msg, flush=True)
        try:
            with open("outward_stock_debug.log", "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except: pass

    try:
        # Validate company
        company = await mongo_db.companies.find_one({"id": outward_data.get("company_id")}, {"_id": 0})
        if not company:
            log_this(f"  ❌ ERROR: Company not found - {outward_data.get('company_id')}")
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Validate warehouse
        warehouse_id = outward_data.get("warehouse_id")
        warehouse = await mongo_db.warehouses.find_one({"id": warehouse_id}, {"_id": 0})
        if not warehouse:
            log_this(f"  ❌ ERROR: Warehouse not found - {warehouse_id}")
            raise HTTPException(status_code=404, detail="Warehouse not found")

        # Validate PI(s) if provided
        pi_ids_list = outward_data.get("pi_ids", [])
        if not pi_ids_list and outward_data.get("pi_id"):
            pi_ids_list = [outward_data.get("pi_id")]

        # Create outward record base
        outward_dict = {
            "id": str(uuid.uuid4()),
            "export_invoice_no": outward_data.get("export_invoice_no") or f"EXP-{str(uuid.uuid4())[:8].upper()}",
            "export_invoice_number": outward_data.get("export_invoice_number", ""),
            "date": outward_data.get("date"),
            "company_id": outward_data["company_id"],
            "pi_id": pi_ids_list[0] if pi_ids_list else None,
            "pi_ids": pi_ids_list,
            "warehouse_id": warehouse_id,
            "mode": outward_data.get("mode"),
            "containers_pallets": outward_data.get("containers_pallets"),
            "dispatch_type": outward_data.get("dispatch_type"),
            "dispatch_plan_id": outward_data.get("dispatch_plan_id"),
            "status": outward_data.get("status", "Pending Dispatch"),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user["id"],
            "line_items": []
        }
        
        log_this(f"  📝 Processing {len(outward_data.get('line_items', []))} line items...")
        
        total_amount = 0
        for item in outward_data.get("line_items", []):
            qty = float(item.get("dispatch_quantity") or item.get("quantity", 0))
            product_id = item.get("product_id")
            product_sku = item.get("sku")
            product_name = item.get("product_name", "Unknown Product")
            
            # Recovery logic
            if not product_id and product_sku:
                product = await mongo_db.products.find_one({"sku": product_sku}, {"id": 1})
                if product:
                    product_id = product["id"]
                    item["product_id"] = product_id
                    log_this(f"     ✅ Recovered ID for {product_sku}: {product_id}")

            # Stock Validation
            should_validate = (
                outward_data.get("dispatch_type") == "dispatch_plan" or
                (outward_data.get("dispatch_type") == "export_invoice" and not outward_data.get("dispatch_plan_id"))
            )
            
            if should_validate:
                log_this(f"     🔍 Validating stock: {product_name} ({qty} units)")
                avail = await get_available_stock(product_id, warehouse_id, product_sku)
                log_this(f"     📊 Available: {avail}, Requested: {qty}")
                
                if qty > (avail + 0.001):
                    log_this(f"     ❌ INSUFFICIENT STOCK!")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Insufficient stock for {product_name}. Available: {avail}, Requested: {qty}"
                    )
            
            line_item = {
                "id": str(uuid.uuid4()),
                "product_id": product_id,
                "product_name": product_name,
                "sku": product_sku,
                "pi_total_quantity": float(item.get("pi_total_quantity", 0)),
                "quantity": qty,
                "dispatch_quantity": qty,
                "rate": float(item.get("rate", 0)),
                "amount": qty * float(item.get("rate", 0)),
                "dimensions": item.get("dimensions"),
                "weight": float(item.get("weight", 0)) if item.get("weight") else None
            }
            total_amount += line_item["amount"]
            outward_dict["line_items"].append(line_item)
        
        outward_dict["total_amount"] = total_amount
        outward_dict["line_items_count"] = len(outward_dict["line_items"])
        
        # Save to DB
        await mongo_db.outward_stock.insert_one(outward_dict)
        log_this(f"  💾 Saved outward entry: {outward_dict['export_invoice_no']}")
        
        # Stock Summary update logic
        should_update = False
        tp = outward_data.get("dispatch_type")
        if tp in ["dispatch_plan", "direct_export"]:
            should_update = True
        elif tp == "export_invoice" and not outward_data.get("dispatch_plan_id"):
            should_update = True
        
        if should_update:
            log_this(f"  🔄 Updating stock tracking...")
            await update_stock_tracking_outward(outward_dict)
        elif tp == "export_invoice" and outward_data.get("dispatch_plan_id"):
            log_this(f"  ℹ️  Linked to plan, updating plan status...")
            await mongo_db.outward_stock.update_one(
                {"id": outward_data.get("dispatch_plan_id")},
                {"$set": {"status": "Invoiced", "updated_at": datetime.now(timezone.utc).isoformat()}}
            )

        await mongo_db.audit_logs.insert_one({
            "action": "outward_stock_created",
            "user_id": current_user["id"],
            "entity_id": outward_dict["id"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        outward_dict.pop("_id", None)
        log_this(f"  ✨ SUCCESS!")
        return outward_dict

    except HTTPException:
        raise
    except Exception as e:
        log_this(f"  💥 CRITICAL ERROR in create_outward_stock: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@api_router.get("/outward-stock")
async def get_outward_stock(
    dispatch_type: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all outward stock entries with optional filtering"""
    query = {"is_active": True}
    if dispatch_type:
        query["dispatch_type"] = dispatch_type
    
    outward_entries = []
    async for entry in mongo_db.outward_stock.find(query, {"_id": 0}):
        # Get company details
        if entry.get("company_id"):
            company = await mongo_db.companies.find_one({"id": entry["company_id"]}, {"_id": 0})
            entry["company"] = company
            
        # Get warehouse details
        if entry.get("warehouse_id"):
            warehouse = await mongo_db.warehouses.find_one({"id": entry["warehouse_id"]}, {"_id": 0})
            entry["warehouse"] = warehouse
            
        # Get PI details (support multiple PIs)
        pi_ids = entry.get("pi_ids", [])
        if not pi_ids and entry.get("pi_id"):
            pi_ids = [entry["pi_id"]]
        
        if pi_ids:
            pi_details = []
            for pi_id in pi_ids:
                pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
                if pi:
                    pi_details.append(pi)
            entry["pis"] = pi_details
            # Keep legacy pi_id for compatibility
            if pi_details:
                entry["pi"] = pi_details[0]

        outward_entries.append(entry)
    
    return outward_entries

# ==================== OUTWARD STOCK ENHANCEMENTS ====================
@api_router.get("/outward-stock/dispatch-plans-pending")
async def get_pending_dispatch_plans(
    current_user: dict = Depends(get_current_active_user)
):
    """Get Dispatch Plans that haven't been linked to Export Invoice yet"""
    pending_dispatch_plans = []
    
    # Find all dispatch plans
    async for dispatch in mongo_db.outward_stock.find({
        "dispatch_type": "dispatch_plan",
        "is_active": True
    }, {"_id": 0}):
        # Check if this dispatch plan is already linked to an export invoice
        linked_export = await mongo_db.outward_stock.find_one({
            "dispatch_type": "export_invoice",
            "dispatch_plan_id": dispatch["id"],
            "is_active": True
        }, {"_id": 0})
        
        if not linked_export:
            # Get company details
            if dispatch.get("company_id"):
                company = await mongo_db.companies.find_one({"id": dispatch["company_id"]}, {"_id": 0})
                dispatch["company"] = company
            
            # Get PI details (support multiple PIs)
            pi_ids = dispatch.get("pi_ids", [])
            if not pi_ids and dispatch.get("pi_id"):
                pi_ids = [dispatch["pi_id"]]
            
            if pi_ids:
                pi_details = []
                for pi_id in pi_ids:
                    pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
                    if pi:
                        pi_details.append(pi)
                dispatch["pis"] = pi_details
            
            pending_dispatch_plans.append(dispatch)
    
    return pending_dispatch_plans

@api_router.get("/outward-stock/available-quantity/{product_id}")
async def get_available_inward_quantity(
    product_id: str,
    warehouse_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get available inward quantity for a specific SKU/product"""
    if not warehouse_id:
        raise HTTPException(status_code=400, detail="warehouse_id is required")
        
    available_quantity = await get_available_stock(product_id, warehouse_id)
    
    return {
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "available_quantity": max(0, available_quantity)
    }

@api_router.get("/outward-stock/export")
async def export_outward_stock(
    format: str = "json",
    current_user: dict = Depends(get_current_active_user)
):
    """Export outward stock entries"""
    outward_entries = []
    async for entry in mongo_db.outward_stock.find({"is_active": True}, {"_id": 0}).sort("created_at", -1):
        outward_entries.append(entry)
    
    if format == "csv":
        return {"data": outward_entries, "format": "csv"}
    
    return outward_entries


@api_router.get("/outward-stock/{outward_id}")
async def get_outward_stock_detail(
    outward_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed outward stock entry"""
    entry = await mongo_db.outward_stock.find_one({"id": outward_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Outward entry not found")
    
    # Get related data
    if entry.get("company_id"):
        company = await mongo_db.companies.find_one({"id": entry["company_id"]}, {"_id": 0})
        entry["company"] = company
        
    if entry.get("warehouse_id"):
        warehouse = await mongo_db.warehouses.find_one({"id": entry["warehouse_id"]}, {"_id": 0})
        entry["warehouse"] = warehouse
        
    # Resolve PIs
    pi_ids = entry.get("pi_ids", [])
    if not pi_ids and entry.get("pi_id"):
        pi_ids = [entry["pi_id"]]
        
    if pi_ids:
        pi_details = []
        for pi_id in pi_ids:
            pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
            if pi:
                pi_details.append(pi)
        entry["pis"] = pi_details
        if pi_details:
            entry["pi"] = pi_details[0]
    
    return entry

@api_router.put("/outward-stock/{outward_id}")
async def update_outward_stock(
    outward_id: str,
    outward_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Update outward stock entry with stock tracking recalibration"""
    old_entry = await mongo_db.outward_stock.find_one({"id": outward_id}, {"_id": 0})
    if not old_entry:
        raise HTTPException(status_code=404, detail="Outward entry not found")
    
    # Check if this is an Export Invoice linked to a Dispatch Plan
    # Editing these should be handled carefully as stock was reduced by the plan
    if old_entry.get("dispatch_type") == "export_invoice" and old_entry.get("dispatch_plan_id"):
        # Allow editing non-stock fields only, or warn
        pass

    # 1. Determine if we need to revert and update stock tracking
    # We update tracking for Dispatch Plans, Direct Exports, and Standalone Export Invoices
    tracking_enabled = (
        old_entry.get("dispatch_type") == "dispatch_plan" or
        old_entry.get("dispatch_type") == "direct_export" or
        (old_entry.get("dispatch_type") == "export_invoice" and not old_entry.get("dispatch_plan_id"))
    )

    if tracking_enabled:
        print(f"  🔄 Edit detected: Reverting old stock tracking for {outward_id}")
        await revert_stock_tracking_outward(old_entry)
    
    # 2. Prepare update data
    update_data = {
        "export_invoice_no": outward_data.get("export_invoice_no", old_entry.get("export_invoice_no")),
        "export_invoice_number": outward_data.get("export_invoice_number", old_entry.get("export_invoice_number", "")),
        "date": outward_data.get("date", old_entry.get("date")),
        "company_id": outward_data.get("company_id", old_entry.get("company_id")),
        "warehouse_id": outward_data.get("warehouse_id", old_entry.get("warehouse_id")),
        "mode": outward_data.get("mode", old_entry.get("mode")),
        "status": outward_data.get("status", old_entry.get("status")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    # Update line items if provided
    current_line_items = []
    if "line_items" in outward_data:
        total_amount = 0
        for item in outward_data["line_items"]:
            # Support both quantity and dispatch_quantity for editing
            qty = item.get("dispatch_quantity") or item.get("quantity", 0)
            
            line_item = {
                "id": item.get("id", str(uuid.uuid4())),
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "sku": item.get("sku"),
                "quantity": float(qty),
                "dispatch_quantity": float(qty),
                "rate": float(item.get("rate", 0)),
                "amount": float(qty) * float(item.get("rate", 0)),
                "dimensions": item.get("dimensions"),
                "weight": float(item.get("weight", 0)) if item.get("weight") else None
            }
            total_amount += line_item["amount"]
            current_line_items.append(line_item)
        
        update_data["line_items"] = current_line_items
        update_data["total_amount"] = total_amount
        update_data["line_items_count"] = len(current_line_items)
    
    # 3. Save updated entry
    await mongo_db.outward_stock.update_one({"id": outward_id}, {"$set": update_data})
    
    # 4. Fetch updated entry and apply new stock tracking
    updated_entry = await mongo_db.outward_stock.find_one({"id": outward_id}, {"_id": 0})
    
    if tracking_enabled:
        print(f"  🔄 Applying new stock tracking for edited entry {outward_id}")
        await update_stock_tracking_outward(updated_entry)
        print(f"  ✅ Edited Stock Summary updated successfully")

    return updated_entry

@api_router.delete("/outward-stock/{outward_id}")
async def delete_outward_stock(
    outward_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Soft delete outward stock entry"""
    entry = await mongo_db.outward_stock.find_one({"id": outward_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Outward entry not found")
    
    # Revert stock tracking (add back the stock)
    await revert_stock_tracking_outward(entry)

    await mongo_db.outward_stock.update_one({"id": outward_id}, {"$set": {"is_active": False}})
    return {"message": "Outward entry deleted successfully"}

async def revert_stock_tracking_outward(outward_entry: dict):
    """
    STOCK SUMMARY - Revert Outward Tracking (On Delete)
    Adds back the quantity to stock tracking entries.
    Strategy: LIFO (Last In First Out) restoration.
    Since outward uses FIFO (Oldest first), we restore to Youngest first to "slide back" the allocation
    or undo the most recent bucket usage.
    """
    try:
        print(f"  🔄 Reverting stock tracking for outward: {outward_entry.get('export_invoice_no')}")
        
        for item in outward_entry.get("line_items", []):
            try:
                # Support both quantity and dispatch_quantity fields
                qty_to_restore = item.get("dispatch_quantity") or item.get("quantity", 0)
                product_id = item.get("product_id")
                product_name = item.get("product_name")
                sku = item.get("sku")
                
                print(f"     - Restoring: {product_name} (Qty: {qty_to_restore})")
                
                # Find all stock_tracking entries for this product in this warehouse with outward stock
                # Sort by created_at DESC (Youngest first)
                tracking_query = {
                    "warehouse_id": outward_entry.get("warehouse_id"),
                    "quantity_outward": {"$gt": 0}  # Only entries that have been used
                }
                
                if product_id:
                    tracking_query["product_id"] = product_id
                elif sku:
                    sku_val = sku.strip()
                    import re
                    sku_esc = re.escape(sku_val)
                    print(f"       ℹ️ No product_id, falling back to flexible SKU for restoration: {sku_val}")
                    tracking_query["sku"] = {"$regex": f"^{sku_esc}", "$options": "i"}
                else:
                    print(f"       ❌ ERROR: Both product_id and SKU are missing for {product_name} in restoration")
                    continue

                stock_entries = []
                async for stock in mongo_db.stock_tracking.find(tracking_query, {"_id": 0}).sort("created_at", -1):  # LIFO: Youngest first
                    stock_entries.append(stock)
                
                remaining_to_restore = qty_to_restore
                
                for stock in stock_entries:
                    if remaining_to_restore <= 0:
                        break
                    
                    # How much can we restore to this entry?
                    # We can deduct from outward up to the amount it has
                    available_to_restore = stock.get("quantity_outward", 0)
                    qty_to_restore_here = min(available_to_restore, remaining_to_restore)
                    
                    # Update this stock entry
                    old_outward = stock.get("quantity_outward", 0)
                    new_outward = old_outward - qty_to_restore_here
                    
                    old_remaining = stock.get("remaining_stock", 0)
                    new_remaining = old_remaining + qty_to_restore_here
                    
                    await mongo_db.stock_tracking.update_one(
                        {"id": stock.get("id")},
                        {"$set": {
                            "quantity_outward": new_outward,
                            "remaining_stock": new_remaining,
                            "last_updated": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    
                    print(f"       ✅ Restored to entry (Invoice: {stock.get('inward_invoice_no')}): Outward {old_outward} → {new_outward}, Remaining {old_remaining} → {new_remaining}")
                    
                    remaining_to_restore -= qty_to_restore_here
                
                if remaining_to_restore > 0:
                    print(f"       ⚠️  Could not fully restore {remaining_to_restore} units of {product_name} (Stock mismatch?)")
                    
            except Exception as item_error:
                print(f"       ❌ Error restoring item {item.get('product_name')}: {str(item_error)}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"  ✅ Outward stock restoration completed")
    except Exception as e:
        print(f"  ❌ CRITICAL ERROR in revert_stock_tracking_outward: {str(e)}")
        import traceback
        traceback.print_exc()


# Helper functions for outward operations
async def get_available_stock(product_id: str, warehouse_id: str, sku: Optional[str] = None) -> float:
    """Get available stock for a product in a specific warehouse (Summed across all inward entries)"""
    total_available = 0.0
    
    query = {
        "warehouse_id": warehouse_id,
        "remaining_stock": {"$gt": 0}
    }
    
    if product_id:
        query["product_id"] = product_id
    elif sku:
        # Flexible SKU matching: allow the provided SKU to be a prefix or match exactly
        sku_clean = sku.strip()
        # Escaping regex special characters if any
        import re
        sku_esc = re.escape(sku_clean)
        query["sku"] = {"$regex": f"^{sku_esc}", "$options": "i"}
    else:
        return 0.0

    async def local_log(msg):
        print(msg)
        try:
            with open("outward_stock_debug.log", "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except: pass

    await local_log(f"     [DEBUG] Stock Query: {query}")
    async for entry in mongo_db.stock_tracking.find(query):
        val = float(entry.get("remaining_stock", 0))
        total_available += val
        await local_log(f"     [DEBUG] Found Item: {entry.get('sku')} | Qty: {val}")
    
    await local_log(f"     [DEBUG] Total Found: {total_available}")
    return total_available

async def update_stock_tracking_outward(outward_entry: dict):
    """
    STOCK SUMMARY - Transaction-Based Outward Tracking
    Links outward to specific inward entries using FIFO (First In First Out)
    Reduces quantity from oldest inward entries first
    """
    import sys
    
    def log_to_file(msg):
        """Helper to log to both console and file"""
        print(msg, flush=True)
        try:
            with open("outward_stock_debug.log", "a", encoding="utf-8") as f:
                f.write(msg + "\n")
                f.flush()
        except:
            pass
    
    try:
        log_to_file(f"  🔄 Updating stock tracking for outward: {outward_entry.get('export_invoice_no')}")
        log_to_file(f"     Warehouse ID: {outward_entry.get('warehouse_id')}")
        log_to_file(f"     Number of line items: {len(outward_entry.get('line_items', []))}")
        
        for item in outward_entry.get("line_items", []):
            try:
                # Support both quantity and dispatch_quantity fields
                qty_to_dispatch = item.get("dispatch_quantity") or item.get("quantity", 0)
                product_id = item.get("product_id")
                product_name = item.get("product_name")
                
                log_to_file(f"     - Processing: {product_name} (Product ID: {product_id}, Dispatch Qty: {qty_to_dispatch})")
                
                # Find all stock_tracking entries for this product in this warehouse with remaining stock
                # Sort by created_at (FIFO - oldest first)
                stock_entries = []
                
                # Use query that prefers product_id but falls back to SKU if product_id is missing
                tracking_query = {
                    "warehouse_id": outward_entry.get("warehouse_id"),
                    "remaining_stock": {"$gt": 0}
                }
                
                if product_id:
                    tracking_query["product_id"] = product_id
                elif item.get("sku"):
                    sku_val = item.get("sku").strip()
                    import re
                    sku_esc = re.escape(sku_val)
                    log_to_file(f"       ℹ️ No product_id, falling back to flexible SKU: {sku_val}")
                    tracking_query["sku"] = {"$regex": f"^{sku_esc}", "$options": "i"}
                else:
                    log_to_file(f"       ❌ ERROR: Both product_id and SKU are missing for {product_name}")
                    continue

                async for stock in mongo_db.stock_tracking.find(tracking_query, {"_id": 0}).sort("created_at", 1):  # FIFO: oldest first
                    stock_entries.append(stock)
                
                log_to_file(f"       📦 Found {len(stock_entries)} stock entries with available stock")
                
                if not stock_entries:
                    log_to_file(f"       ⚠️  No stock available for {product_name} (ID: {product_id}) in warehouse {outward_entry.get('warehouse_id')}")
                    # Check if there are ANY stock entries for this product (even with 0 remaining)
                    total_entries = await mongo_db.stock_tracking.count_documents({
                        "product_id": product_id,
                        "warehouse_id": outward_entry.get("warehouse_id")
                    })
                    log_to_file(f"       📊 Total stock entries for this product: {total_entries}")
                    continue
                
                remaining_to_dispatch = qty_to_dispatch
                
                # Dispatch from oldest entries first (FIFO)
                for stock in stock_entries:
                    if remaining_to_dispatch <= 0:
                        break
                    
                    available_qty = stock.get("remaining_stock", 0)
                    qty_from_this_entry = min(available_qty, remaining_to_dispatch)
                    
                    # Update this stock entry
                    old_outward = stock.get("quantity_outward", 0)
                    new_outward = old_outward + qty_from_this_entry
                    new_remaining = stock.get("quantity_inward", 0) - new_outward
                    
                    await mongo_db.stock_tracking.update_one(
                        {"id": stock.get("id")},
                        {"$set": {
                            "quantity_outward": new_outward,
                            "remaining_stock": max(0, new_remaining),
                            "last_outward_date": datetime.now(timezone.utc).isoformat(),
                            "last_updated": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    
                    log_to_file(f"       ✅ Updated entry (Invoice: {stock.get('inward_invoice_no')}): Outward {old_outward} → {new_outward}, Remaining: {new_remaining}")
                    
                    remaining_to_dispatch -= qty_from_this_entry
                
                if remaining_to_dispatch > 0:
                    log_to_file(f"       ⚠️  Insufficient stock! Could not dispatch {remaining_to_dispatch} units of {product_name}")
                    
            except Exception as item_error:
                log_to_file(f"       ❌ Error processing item {item.get('product_name')}: {str(item_error)}")
                import traceback
                traceback.print_exc()
                continue
        
        log_to_file(f"  ✅ Outward stock tracking update completed (FIFO)")
    except Exception as e:
        log_to_file(f"  ❌ CRITICAL ERROR in update_stock_tracking_outward: {str(e)}")
        import traceback
        traceback.print_exc()

@api_router.get("/available-stock")
async def get_available_stock_summary(
    warehouse_id: Optional[str] = None,
    product_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get available stock summary for outward operations"""
    query = {}
    if warehouse_id:
        query["warehouse_id"] = warehouse_id
    if product_id:
        query["product_id"] = product_id
    
    stock_entries = []
    async for stock in mongo_db.stock_tracking.find(query, {"_id": 0}):
        if stock["current_stock"] > 0:  # Only show items with available stock
            # Get warehouse name
            warehouse_name = None
            if stock.get("warehouse_id"):
                warehouse = await mongo_db.warehouses.find_one({"id": stock["warehouse_id"]}, {"_id": 0})
                warehouse_name = warehouse.get("name") if warehouse else None
            
            stock_summary = {
                "product_id": stock["product_id"],
                "product_name": stock["product_name"],
                "sku": stock["sku"],
                "warehouse_id": stock.get("warehouse_id"),
                "warehouse_name": warehouse_name,
                "available_stock": stock["current_stock"]
            }
            stock_entries.append(stock_summary)
    
    return stock_entries

# ==================== PAYMENT TRACKING ====================
@api_router.get("/payments")
async def get_payments(
    pi_number: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all payment records with filters"""
    query = {"is_active": True}
    if pi_number:
        query["pi_voucher_no"] = {"$regex": pi_number, "$options": "i"}
    
    payments = []
    async for payment in mongo_db.payments.find(query, {"_id": 0}).sort("date", -1):
        # Enrich with PI and company details
        if payment.get("pi_id"):
            pi = await mongo_db.proforma_invoices.find_one({"id": payment["pi_id"]}, {"_id": 0})
            if pi:
                payment["pi_details"] = pi
        
        if payment.get("company_id"):
            company = await mongo_db.companies.find_one({"id": payment["company_id"]}, {"_id": 0})
            if company:
                payment["company_name"] = company.get("name")
        
        payments.append(payment)
    
    return payments

@api_router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get specific payment record with full details"""
    payment = await mongo_db.payments.find_one({"id": payment_id, "is_active": True}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
    
    # Enrich with related data
    if payment.get("pi_id"):
        pi = await mongo_db.proforma_invoices.find_one({"id": payment["pi_id"]}, {"_id": 0})
        if pi:
            payment["pi_details"] = pi
            
            # Calculate dispatch quantities from outward stock
            dispatch_qty = 0
            async for outward in mongo_db.outward_stock.find({
                "pi_id": payment["pi_id"],
                "dispatch_type": {"$in": ["export_invoice", "dispatch_plan"]},
                "is_active": True
            }, {"_id": 0}):
                for item in outward.get("line_items", []):
                    dispatch_qty += item.get("quantity", 0)
            
            payment["calculated_dispatch_qty"] = dispatch_qty
            payment["calculated_pending_qty"] = payment.get("total_quantity", 0) - dispatch_qty
    
    if payment.get("company_id"):
        company = await mongo_db.companies.find_one({"id": payment["company_id"]}, {"_id": 0})
        if company:
            payment["company_details"] = company
    
    return payment

@api_router.post("/payments")
async def create_payment(
    payment_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Create new payment record for a PI"""
    # Validate PI exists
    pi = await mongo_db.proforma_invoices.find_one({"id": payment_data["pi_id"]}, {"_id": 0})
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    # Check if payment record already exists for this PI
    existing = await mongo_db.payments.find_one({"pi_id": payment_data["pi_id"], "is_active": True}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Payment record already exists for this PI. Please use edit to update.")
    
    # Calculate dispatch quantities from outward stock
    dispatch_qty = 0
    dispatch_value = 0
    async for outward in mongo_db.outward_stock.find({
        "pi_id": payment_data["pi_id"],
        "dispatch_type": {"$in": ["export_invoice", "dispatch_plan"]},
        "is_active": True
    }, {"_id": 0}):
        for item in outward.get("line_items", []):
            dispatch_qty += item.get("quantity", 0)
            dispatch_value += item.get("amount", 0)
    
    # Calculate total PI amount and quantity
    total_amount = sum(item.get("amount", 0) for item in pi.get("line_items", []))
    total_quantity = sum(item.get("quantity", 0) for item in pi.get("line_items", []))
    
    # Auto-calculate remaining payment
    advance_payment = payment_data.get("advance_payment", 0)
    received_amount = payment_data.get("received_amount", 0)
    remaining_payment = total_amount - advance_payment - received_amount
    
    # Create payment record
    payment_dict = {
        "id": str(uuid.uuid4()),
        "pi_id": payment_data["pi_id"],
        "manual_entry": payment_data.get("manual_entry", ""),
        "pi_voucher_no": pi.get("voucher_no"),
        "company_id": pi.get("company_id"),
        "date": payment_data.get("date", datetime.now(timezone.utc).date().isoformat()),
        "total_amount": total_amount,
        "total_quantity": total_quantity,
        "advance_payment": advance_payment,
        "received_amount": received_amount,
        "remaining_payment": remaining_payment,
        "payment_entries": [],  # New: Array to store multiple payment entries
        "total_received": advance_payment + received_amount,
        "is_fully_paid": (remaining_payment <= 0),
        "bank_name": payment_data.get("bank_name", ""),
        "bank_details": payment_data.get("bank_details", ""),
        "dispatch_qty": payment_data.get("dispatch_qty", dispatch_qty),
        "pending_qty": payment_data.get("pending_qty", total_quantity - dispatch_qty),
        "dispatch_date": payment_data.get("dispatch_date"),
        "export_invoice_no": payment_data.get("export_invoice_no", ""),
        "dispatch_goods_value": payment_data.get("dispatch_goods_value", dispatch_value),
        "notes": payment_data.get("notes", ""),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await mongo_db.payments.insert_one(payment_dict)
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "payment_created",
        "user_id": current_user["id"],
        "entity_id": payment_dict["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    payment_dict.pop("_id", None)
    return payment_dict

@api_router.put("/payments/{payment_id}")
async def update_payment(
    payment_id: str,
    payment_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Update existing payment record"""
    existing = await mongo_db.payments.find_one({"id": payment_id, "is_active": True}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Payment record not found")
    
    # Recalculate remaining payment if payment amounts changed
    advance_payment = payment_data.get("advance_payment", existing.get("advance_payment", 0))
    received_amount = payment_data.get("received_amount", existing.get("received_amount", 0))
    total_amount = existing.get("total_amount", 0)
    remaining_payment = total_amount - advance_payment - received_amount
    
    # Update fields
    update_data = {
        "advance_payment": advance_payment,
        "received_amount": received_amount,
        "remaining_payment": remaining_payment,
        "bank_name": payment_data.get("bank_name", existing.get("bank_name")),
        "bank_details": payment_data.get("bank_details", existing.get("bank_details")),
        "dispatch_qty": payment_data.get("dispatch_qty", existing.get("dispatch_qty")),
        "pending_qty": payment_data.get("pending_qty", existing.get("pending_qty")),
        "dispatch_date": payment_data.get("dispatch_date", existing.get("dispatch_date")),
        "export_invoice_no": payment_data.get("export_invoice_no", existing.get("export_invoice_no")),
        "dispatch_goods_value": payment_data.get("dispatch_goods_value", existing.get("dispatch_goods_value")),
        "notes": payment_data.get("notes", existing.get("notes")),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await mongo_db.payments.update_one(
        {"id": payment_id},
        {"$set": update_data}
    )
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "payment_updated",
        "user_id": current_user["id"],
        "entity_id": payment_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    updated = await mongo_db.payments.find_one({"id": payment_id}, {"_id": 0})
    return updated

@api_router.delete("/payments/{payment_id}")
async def delete_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete payment record"""
    result = await mongo_db.payments.update_one(
        {"id": payment_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    


# ==================== PAYMENT ENTRIES (Multiple payments per PI) ====================
@api_router.post("/payments/{payment_id}/entries")
async def add_payment_entry(
    payment_id: str,
    entry_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Add a new payment entry to existing payment record"""
    payment = await mongo_db.payments.find_one({"id": payment_id, "is_active": True}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
    
    # Validate bank if provided
    if entry_data.get("bank_id"):
        bank = await mongo_db.banks.find_one({"id": entry_data["bank_id"]}, {"_id": 0})
        if not bank:
            raise HTTPException(status_code=404, detail="Bank not found")
    
    # Create payment entry
    entry = {
        "id": str(uuid.uuid4()),
        "date": entry_data.get("date", datetime.now(timezone.utc).date().isoformat()),
        "received_amount": entry_data.get("received_amount", 0),
        "receipt_number": entry_data.get("receipt_number", ""),
        "bank_id": entry_data.get("bank_id"),
        "notes": entry_data.get("notes", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    # Add entry to payment_entries array
    await mongo_db.payments.update_one(
        {"id": payment_id},
        {
            "$push": {"payment_entries": entry},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Recalculate remaining payment
    updated_payment = await mongo_db.payments.find_one({"id": payment_id}, {"_id": 0})
    
    # Calculate received from payment entries only (not including advance)
    payment_entries_total = sum(e.get("received_amount", 0) for e in updated_payment.get("payment_entries", []))
    
    # Calculate total received including advance and extra payments
    advance = updated_payment.get("advance_payment", 0)
    extra_payments = updated_payment.get("extra_payments_total", 0)
    total_received = advance + payment_entries_total + extra_payments
    
    remaining = updated_payment.get("total_amount", 0) - total_received
    
    # Check if fully paid
    is_fully_paid = remaining <= 0
    
    await mongo_db.payments.update_one(
        {"id": payment_id},
        {
            "$set": {
                "received_amount": payment_entries_total,
                "total_received": total_received,
                "remaining_payment": remaining,
                "is_fully_paid": is_fully_paid,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "payment_entry_added",
        "user_id": current_user["id"],
        "payment_id": payment_id,
        "entry_id": entry["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return await mongo_db.payments.find_one({"id": payment_id}, {"_id": 0})

@api_router.delete("/payments/{payment_id}/entries/{entry_id}")
async def delete_payment_entry(
    payment_id: str,
    entry_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a payment entry from a payment record"""
    payment = await mongo_db.payments.find_one({"id": payment_id, "is_active": True}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
    
    # Remove entry from payment_entries array
    await mongo_db.payments.update_one(
        {"id": payment_id},
        {
            "$pull": {"payment_entries": {"id": entry_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Recalculate remaining payment
    updated_payment = await mongo_db.payments.find_one({"id": payment_id}, {"_id": 0})
    
    # Calculate received from payment entries only (not including advance)
    payment_entries_total = sum(e.get("received_amount", 0) for e in updated_payment.get("payment_entries", []))
    
    # Calculate total received including advance and extra payments
    advance = updated_payment.get("advance_payment", 0)
    extra_payments = updated_payment.get("extra_payments_total", 0)
    total_received = advance + payment_entries_total + extra_payments
    
    remaining = updated_payment.get("total_amount", 0) - total_received
    
    # Check if fully paid
    is_fully_paid = remaining <= 0
    
    await mongo_db.payments.update_one(
        {"id": payment_id},
        {
            "$set": {
                "received_amount": payment_entries_total,
                "total_received": total_received,
                "remaining_payment": remaining,
                "is_fully_paid": is_fully_paid,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "payment_entry_deleted",
        "user_id": current_user["id"],
        "entity_id": payment_id,
        "entry_id": entry_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Payment entry deleted successfully"}

@api_router.get("/payments/{payment_id}/export-details")
async def get_export_details(
    payment_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get export details (export invoice wise) for a payment/PI"""
    payment = await mongo_db.payments.find_one({"id": payment_id, "is_active": True}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
    
    pi_id = payment.get("pi_id")
    if not pi_id:
        return []
    
    # Get PI details
    pi = await mongo_db.proforma_invoices.find_one({"id": pi_id}, {"_id": 0})
    if not pi:
        return []
    
    # Calculate PI total quantity
    pi_total_qty = sum(item.get("quantity", 0) for item in pi.get("line_items", []))
    
    # Get all export invoices for this PI
    export_details = []
    async for outward in mongo_db.outward_stock.find({
        "$or": [
            {"pi_id": pi_id},
            {"pi_ids": pi_id}
        ],
        "dispatch_type": "export_invoice",
        "is_active": True
    }, {"_id": 0}):
        # Calculate exported quantity for this invoice
        exported_qty = sum(item.get("dispatch_quantity", item.get("quantity", 0)) 
                          for item in outward.get("line_items", []))
        
        export_details.append({
            "export_invoice_no": outward.get("export_invoice_no"),
            "date": outward.get("date"),
            "pi_total_quantity": pi_total_qty,
            "exported_quantity": exported_qty,
            "remaining_for_export": pi_total_qty - exported_qty if len(export_details) == 0 else 0,
            "mode": outward.get("mode"),
            "status": outward.get("status")
        })
    
    # Calculate total exported and remaining
    total_exported = sum(e["exported_quantity"] for e in export_details)
    
    if export_details:
        export_details[-1]["remaining_for_export"] = pi_total_qty - total_exported
    
    return {
        "pi_total_quantity": pi_total_qty,
        "total_exported": total_exported,
        "remaining_for_export": pi_total_qty - total_exported,
        "export_invoices": export_details
    }


# ==================== SHORT PAYMENT ====================
@api_router.post("/payments/{payment_id}/short-payment")
async def mark_short_payment(
    payment_id: str,
    short_payment_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Mark a payment as short payment (closed for further payments)"""
    # Validate note is provided
    if not short_payment_data.get("note"):
        raise HTTPException(status_code=400, detail="Note is required for short payment")
    
    # Find payment
    payment = await mongo_db.payments.find_one({"id": payment_id, "is_active": True})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Update payment with short payment status
    await mongo_db.payments.update_one(
        {"id": payment_id},
        {
            "$set": {
                "short_payment_status": True,
                "short_payment_note": short_payment_data["note"],
                "short_payment_date": datetime.now(timezone.utc).isoformat(),
                "short_payment_by": current_user["id"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "short_payment_marked",
        "user_id": current_user["id"],
        "entity_id": payment_id,
        "note": short_payment_data["note"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Payment marked as short payment successfully",
        "payment_id": payment_id,
        "short_payment_status": True
    }


@api_router.post("/payments/{payment_id}/reopen-short-payment")
async def reopen_short_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Reopen a short payment to allow further payments"""
    # Find payment
    payment = await mongo_db.payments.find_one({"id": payment_id, "is_active": True})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if not payment.get("short_payment_status"):
        raise HTTPException(status_code=400, detail="Payment is not marked as short payment")
    
    # Reopen payment
    await mongo_db.payments.update_one(
        {"id": payment_id},
        {
            "$set": {
                "short_payment_status": False,
                "short_payment_reopened_at": datetime.now(timezone.utc).isoformat(),
                "short_payment_reopened_by": current_user["id"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "short_payment_reopened",
        "user_id": current_user["id"],
        "entity_id": payment_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Short payment reopened successfully",
        "payment_id": payment_id,
        "short_payment_status": False
    }


# ==================== EXTRA PAYMENTS ====================
@api_router.get("/extra-payments")
async def get_extra_payments(
    pi_number: str = Query(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Get all extra payments for a specific PI number"""
    extra_payments = []
    async for payment in mongo_db.pi_extra_payments.find(
        {"pi_number": pi_number, "is_active": True},
        {"_id": 0}
    ).sort("date", -1):
        extra_payments.append(payment)
    
    return extra_payments


@api_router.post("/extra-payments")
async def create_extra_payment(
    payment_data: dict,
    pi_number: str = Query(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new extra payment for a PI"""
    try:
        # Validate required fields
        if not payment_data.get("date"):
            raise HTTPException(status_code=400, detail="Date is required")
        if not payment_data.get("bank_id"):
            raise HTTPException(status_code=400, detail="Bank is required")
        
        amount = float(payment_data.get("amount") or 0)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        # Verify bank exists
        bank = await mongo_db.banks.find_one({"id": payment_data["bank_id"], "is_active": True})
        if not bank:
            raise HTTPException(status_code=404, detail="Bank not found")
        
        # Create extra payment record
        extra_payment = {
            "id": str(uuid.uuid4()),
            "pi_number": pi_number,
            "date": payment_data["date"],
            "receipt": payment_data.get("receipt", ""),
            "bank_id": payment_data["bank_id"],
            "bank_name": bank.get("bank_name", ""),
            "amount": amount,
            "note": payment_data.get("note", ""),
            "is_active": True,
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = await mongo_db.pi_extra_payments.insert_one(extra_payment)
        
        # Update payment record total if exists
        await update_payment_with_extra_payments(pi_number)
        
        # Log action
        await mongo_db.audit_logs.insert_one({
            "action": "extra_payment_created",
            "user_id": current_user["id"],
            "entity_id": extra_payment["id"],
            "pi_number": pi_number,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        extra_payment.pop("_id", None)
        return extra_payment
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in create_extra_payment: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@api_router.put("/extra-payments/{extra_payment_id}")
async def update_extra_payment(
    extra_payment_id: str,
    payment_data: dict,
    pi_number: str = Query(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Update an existing extra payment"""
    try:
        print(f"DEBUG: Updating extra payment {extra_payment_id} for PI: {pi_number}")
        
        # Validate required fields
        if "date" in payment_data and not payment_data["date"]:
            raise HTTPException(status_code=400, detail="Date is required")
        if "bank_id" in payment_data and not payment_data["bank_id"]:
            raise HTTPException(status_code=400, detail="Bank is required")
        
        # Check if extra payment exists
        existing = await mongo_db.pi_extra_payments.find_one({
            "id": extra_payment_id,
            "pi_number": pi_number,
            "is_active": True
        })
        
        if not existing:
            raise HTTPException(status_code=404, detail="Extra payment not found")
        
        # Verify bank if being updated
        bank_name = existing.get("bank_name", "")
        if payment_data.get("bank_id"):
            bank = await mongo_db.banks.find_one({"id": payment_data["bank_id"], "is_active": True})
            if not bank:
                raise HTTPException(status_code=404, detail="Bank not found")
            bank_name = bank.get("bank_name", "")
        
        # Update fields
        update_data = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if "date" in payment_data:
            update_data["date"] = payment_data["date"]
        if "receipt" in payment_data:
            update_data["receipt"] = payment_data["receipt"]
        if "bank_id" in payment_data:
            update_data["bank_id"] = payment_data["bank_id"]
            update_data["bank_name"] = bank_name
        if "amount" in payment_data:
            amount = float(payment_data.get("amount") or 0)
            if amount <= 0:
                raise HTTPException(status_code=400, detail="Amount must be greater than 0")
            update_data["amount"] = amount
        if "note" in payment_data:
            update_data["note"] = payment_data["note"]
        
        await mongo_db.pi_extra_payments.update_one(
            {"id": extra_payment_id},
            {"$set": update_data}
        )
        
        # Update payment record total if exists
        await update_payment_with_extra_payments(pi_number)
        
        # Log action
        await mongo_db.audit_logs.insert_one({
            "action": "extra_payment_updated",
            "user_id": current_user["id"],
            "entity_id": extra_payment_id,
            "pi_number": pi_number,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        updated = await mongo_db.pi_extra_payments.find_one({"id": extra_payment_id}, {"_id": 0})
        return updated
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in update_extra_payment: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/extra-payments/{extra_payment_id}")
async def delete_extra_payment(
    extra_payment_id: str,
    pi_number: str = Query(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Soft delete an extra payment"""
    result = await mongo_db.pi_extra_payments.update_one(
        {"id": extra_payment_id, "pi_number": pi_number},
        {
            "$set": {
                "is_active": False,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_by": current_user["id"]
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Extra payment not found")
    
    # Update payment record total if exists
    await update_payment_with_extra_payments(pi_number)
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "extra_payment_deleted",
        "user_id": current_user["id"],
        "entity_id": extra_payment_id,
        "pi_number": pi_number,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Extra payment deleted successfully"}


async def update_payment_with_extra_payments(pi_number: str):
    """Helper function to update payment record with extra payments total"""
    try:
        # Find payment record for this PI
        payment = await mongo_db.payments.find_one({
            "pi_voucher_no": pi_number,
            "is_active": True
        })
        
        if not payment:
            print(f"DEBUG: No payment record found for PI: {pi_number}")
            return
        
        # Calculate total extra payments
        total_extra = 0
        async for extra_payment in mongo_db.pi_extra_payments.find({
            "pi_number": pi_number,
            "is_active": True
        }):
            total_extra += float(extra_payment.get("amount") or 0)
        
        # Calculate received amount from payment entries
        payment_entries_total = sum(float(e.get("received_amount") or 0) for e in payment.get("payment_entries") or [])
        
        # Update payment record
        advance_payment = float(payment.get("advance_payment") or 0)
        total_amount = float(payment.get("total_amount") or 0)
        
        # Total received = Advance + Payment Entries + Extra Payments
        total_received = advance_payment + payment_entries_total + total_extra
        remaining_payment = total_amount - total_received
        
        await mongo_db.payments.update_one(
            {"id": payment["id"]},
            {
                "$set": {
                    "received_amount": payment_entries_total,
                    "extra_payments_total": total_extra,
                    "total_received": total_received,
                    "remaining_payment": remaining_payment,
                    "is_fully_paid": remaining_payment <= 0,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"ERROR in update_payment_with_extra_payments: {str(e)}")


# ==================== EXPENSE CALCULATION ====================
@api_router.get("/expenses")
async def get_expenses(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all expense records with filters"""
    query = {"is_active": True}
    
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    
    expenses = []
    async for expense in mongo_db.expenses.find(query, {"_id": 0}).sort("date", -1):
        # Enrich with export invoice details
        export_invoice_details = []
        if expense.get("export_invoice_ids"):
            for inv_id in expense["export_invoice_ids"]:
                outward = await mongo_db.outward_stock.find_one({"id": inv_id, "is_active": True}, {"_id": 0})
                if outward:
                    export_invoice_details.append({
                        "id": outward["id"],
                        "export_invoice_no": outward.get("export_invoice_no"),
                        "date": outward.get("date"),
                        "line_items": outward.get("line_items", [])
                    })
        
        expense["export_invoice_details"] = export_invoice_details
        expenses.append(expense)
    
    return expenses

@api_router.get("/expenses/{expense_id}")
async def get_expense(
    expense_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get specific expense record with full details"""
    expense = await mongo_db.expenses.find_one({"id": expense_id, "is_active": True}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense record not found")
    
    # Enrich with export invoice details and stock items
    export_invoice_details = []
    total_stock_value = 0
    
    if expense.get("export_invoice_ids"):
        for inv_id in expense["export_invoice_ids"]:
            outward = await mongo_db.outward_stock.find_one({"id": inv_id, "is_active": True}, {"_id": 0})
            if outward:
                # Calculate total value of line items
                items_value = sum(item.get("amount", 0) for item in outward.get("line_items", []))
                total_stock_value += items_value
                
                # Get warehouse and company details
                warehouse = None
                if outward.get("warehouse_id"):
                    warehouse = await mongo_db.warehouses.find_one({"id": outward["warehouse_id"]}, {"_id": 0})
                
                export_invoice_details.append({
                    "id": outward["id"],
                    "export_invoice_no": outward.get("export_invoice_no"),
                    "date": outward.get("date"),
                    "dispatch_type": outward.get("dispatch_type"),
                    "mode": outward.get("mode"),
                    "status": outward.get("status"),
                    "warehouse": warehouse,
                    "line_items": outward.get("line_items", []),
                    "items_total_value": items_value
                })
    
    expense["export_invoice_details"] = export_invoice_details
    expense["total_stock_value"] = total_stock_value
    
    return expense

@api_router.post("/expenses")
async def create_expense(
    expense_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Create new expense record"""
    # Validate export invoices if provided
    if expense_data.get("export_invoice_ids"):
        for inv_id in expense_data["export_invoice_ids"]:
            outward = await mongo_db.outward_stock.find_one({"id": inv_id}, {"_id": 0})
            if not outward:
                raise HTTPException(status_code=404, detail=f"Export Invoice {inv_id} not found")
    
    # Calculate total expense
    freight_charges = expense_data.get("freight_charges", 0)
    cha_charges = expense_data.get("cha_charges", 0)
    other_charges = expense_data.get("other_charges", 0)
    total_expense = freight_charges + cha_charges + other_charges
    
    # Create expense record
    expense_dict = {
        "id": str(uuid.uuid4()),
        "expense_reference_no": expense_data.get("expense_reference_no") or f"EXP-{str(uuid.uuid4())[:8].upper()}",
        "date": expense_data.get("date", datetime.now(timezone.utc).date().isoformat()),
        "export_invoice_ids": expense_data.get("export_invoice_ids", []),
        "export_invoice_nos_manual": expense_data.get("export_invoice_nos_manual", ""),
        "freight_charges": freight_charges,
        "freight_vendor": expense_data.get("freight_vendor", ""),
        "cha_charges": cha_charges,
        "cha_vendor": expense_data.get("cha_vendor", ""),
        "other_charges": other_charges,
        "other_charges_description": expense_data.get("other_charges_description", ""),
        "total_expense": total_expense,
        "payment_status": expense_data.get("payment_status", "Pending"),
        "notes": expense_data.get("notes", ""),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await mongo_db.expenses.insert_one(expense_dict)
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "expense_created",
        "user_id": current_user["id"],
        "entity_id": expense_dict["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    expense_dict.pop("_id", None)
    return expense_dict

@api_router.put("/expenses/{expense_id}")
async def update_expense(
    expense_id: str,
    expense_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Update existing expense record"""
    existing = await mongo_db.expenses.find_one({"id": expense_id, "is_active": True}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Expense record not found")
    
    # Recalculate total expense
    freight_charges = expense_data.get("freight_charges", existing.get("freight_charges", 0))
    cha_charges = expense_data.get("cha_charges", existing.get("cha_charges", 0))
    other_charges = expense_data.get("other_charges", existing.get("other_charges", 0))
    total_expense = freight_charges + cha_charges + other_charges
    
    # Update fields
    update_data = {
        "date": expense_data.get("date", existing.get("date")),
        "export_invoice_ids": expense_data.get("export_invoice_ids", existing.get("export_invoice_ids")),
        "export_invoice_nos_manual": expense_data.get("export_invoice_nos_manual", existing.get("export_invoice_nos_manual")),
        "freight_charges": freight_charges,
        "freight_vendor": expense_data.get("freight_vendor", existing.get("freight_vendor")),
        "cha_charges": cha_charges,
        "cha_vendor": expense_data.get("cha_vendor", existing.get("cha_vendor")),
        "other_charges": other_charges,
        "other_charges_description": expense_data.get("other_charges_description", existing.get("other_charges_description")),
        "total_expense": total_expense,
        "payment_status": expense_data.get("payment_status", existing.get("payment_status")),
        "notes": expense_data.get("notes", existing.get("notes")),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await mongo_db.expenses.update_one(
        {"id": expense_id},
        {"$set": update_data}
    )
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "expense_updated",
        "user_id": current_user["id"],
        "entity_id": expense_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    updated = await mongo_db.expenses.find_one({"id": expense_id}, {"_id": 0})
    return updated

@api_router.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete expense record"""
    result = await mongo_db.expenses.update_one(
        {"id": expense_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Expense record not found")
    
    # Log action
    await mongo_db.audit_logs.insert_one({
        "action": "expense_deleted",
        "user_id": current_user["id"],
        "entity_id": expense_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Expense record deleted successfully"}

# ==================== P&L REPORTING ====================
@api_router.post("/pl-report/calculate")
async def calculate_pl_report(
    request_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Calculate P&L for selected export invoices with detailed breakdown.
    Optimized: Bulk fetches POs and Expenses to avoid N+1 queries.
    """
    export_invoice_ids = request_data.get("export_invoice_ids", [])
    from_date = request_data.get("from_date")
    to_date = request_data.get("to_date")
    company_id = request_data.get("company_id")
    sku_filter = request_data.get("sku")
    
    if not export_invoice_ids:
        raise HTTPException(status_code=400, detail="No export invoices selected")
    
    # 1. Bulk Fetch Invoices
    outwards = await mongo_db.outward_stock.find({"id": {"$in": export_invoice_ids}, "is_active": True}, {"_id": 0}).to_list(length=None)
    if not outwards:
        return {"summary": {}, "message": "No invoices found"}

    # 2. Collect PI IDs and SKUs for rate lookup
    pi_ids = []
    skus = []
    for o in outwards:
        pi_ids.extend(o.get("pi_ids", []) or ([o.get("pi_id")] if o.get("pi_id") else []))
        for item in o.get("line_items", []):
            if item.get("sku"):
                skus.append(item.get("sku"))
    
    # 3. Bulk fetch POs for rate mapping
    # Strategy: Build a map of SKU -> Rate from linked POs or most recent POs
    po_rate_map = {} # key: pi_id:sku, value: rate
    global_rate_map = {} # key: sku, value: rate (fallback)
    
    po_query = {
        "is_active": True,
        "$or": [
            {"reference_pi_id": {"$in": pi_ids}},
            {"reference_pi_ids": {"$in": pi_ids}},
            {"line_items.sku": {"$in": skus}} # In case line items have sku at top level or we search by sku
        ]
    }
    # More robust: just fetch POs that might be relevant
    relevant_pos = await mongo_db.purchase_orders.find(po_query, {"_id": 0}).to_list(length=None)
    
    for po in relevant_pos:
        # Link to PIs
        p_ids = po.get("reference_pi_ids", []) or ([po.get("reference_pi_id")] if po.get("reference_pi_id") else [])
        for item in po.get("line_items", []):
            item_sku = item.get("sku")
            item_rate = float(item.get("rate", 0))
            if item_sku:
                for pid in p_ids:
                    po_rate_map[f"{pid}:{item_sku}"] = item_rate
                global_rate_map[item_sku] = item_rate

    # 4. Bulk fetch Expenses
    total_expenses = 0
    expense_query = {
        "is_active": True,
        "export_invoice_ids": {"$in": export_invoice_ids}
    }
    expenses_list = await mongo_db.expenses.find(expense_query, {"_id": 0}).to_list(length=None)
    for exp in expenses_list:
        total_expenses += exp.get("total_expense", 0)

    # 5. Process Invoices
    total_export_value = 0
    total_purchase_cost = 0
    item_breakdown = []
    export_invoice_details = []
    
    for outward in outwards:
        # Filters (Double check in memory)
        if from_date and outward.get("date") < from_date: continue
        if to_date and outward.get("date") > to_date: continue
        if company_id and outward.get("company_id") != company_id: continue
        
        inv_export_value = 0
        inv_purchase_cost = 0
        invoice_items = []
        
        inv_pi_ids = outward.get("pi_ids", []) or ([outward.get("pi_id")] if outward.get("pi_id") else [])
        
        for item in outward.get("line_items", []):
            if sku_filter and sku_filter.lower() not in item.get("sku", "").lower():
                continue
            
            qty = float(item.get("quantity", 0))
            export_rate = float(item.get("rate", 0))
            export_val = qty * export_rate
            
            # Lookup purchase rate
            p_rate = 0
            # Try PI specific PO rate first
            for pid in inv_pi_ids:
                if f"{pid}:{item.get('sku')}" in po_rate_map:
                    p_rate = po_rate_map[f"{pid}:{item.get('sku')}"]
                    break
            
            # Fallback to global rate for this SKU
            if p_rate == 0:
                p_rate = global_rate_map.get(item.get("sku"), 0)
                
            purchase_cost = qty * p_rate
            inv_export_value += export_val
            inv_purchase_cost += purchase_cost
            
            item_data = {
                "sku": item.get("sku"),
                "product_name": item.get("product_name"),
                "export_qty": qty,
                "export_rate": export_rate,
                "export_value": export_val,
                "purchase_cost": purchase_cost,
                "item_gross": export_val - purchase_cost
            }
            invoice_items.append(item_data)
            item_breakdown.append({**item_data, "export_invoice_no": outward.get("export_invoice_no")})
            
        total_export_value += inv_export_value
        total_purchase_cost += inv_purchase_cost
        
        export_invoice_details.append({
            "id": outward["id"],
            "export_invoice_no": outward.get("export_invoice_no"),
            "date": outward.get("date"),
            "export_value": inv_export_value,
            "purchase_cost": inv_purchase_cost,
            "items": invoice_items
        })
    
    # Final P&L Calculation
    gross_total = total_export_value - total_purchase_cost - total_expenses
    net_profit = gross_total / 1.18
    gst_amount = gross_total - net_profit
    net_profit_percentage = (net_profit / total_export_value * 100) if total_export_value > 0 else 0
    
    return {
        "summary": {
            "total_export_value": total_export_value,
            "total_purchase_cost": total_purchase_cost,
            "total_expenses": total_expenses,
            "gross_total": gross_total,
            "gst_amount": gst_amount,
            "net_profit": net_profit,
            "net_profit_percentage": net_profit_percentage
        },
        "export_invoices": export_invoice_details,
        "item_breakdown": item_breakdown,
        "filters_applied": {
            "from_date": from_date,
            "to_date": to_date,
            "company_id": company_id,
            "sku": sku_filter,
            "invoice_count": len(export_invoice_details)
        }
    }

@api_router.get("/pl-report/export-invoices")
async def get_export_invoices_for_pl(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get export invoices available for P&L calculation"""
    query = {
        "dispatch_type": {"$in": ["export_invoice", "direct_export"]},
        "is_active": True
    }
    
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    
    invoices = []
    async for outward in mongo_db.outward_stock.find(query, {"_id": 0}).sort("date", -1):
        # Calculate total value
        total_value = sum(item.get("amount", 0) for item in outward.get("line_items", []))
        
        invoices.append({
            "id": outward["id"],
            "export_invoice_no": outward.get("export_invoice_no"),
            "date": outward.get("date"),
            "dispatch_type": outward.get("dispatch_type"),
            "status": outward.get("status"),
            "total_value": total_value,
            "line_items_count": len(outward.get("line_items", []))
        })
    
    return invoices

# ==================== DASHBOARD ROUTES ====================
# ==================== CUSTOMER MANAGEMENT ====================

# ==================== PI TO PO MAPPING (NEW IMPLEMENTATION) ====================
@api_router.get("/pi-po-mapping")
async def get_pi_po_mapping_list(
    page: int = 1,
    page_size: int = 50,
    consignee: Optional[str] = None,
    pi_number: Optional[str] = None,
    po_number: Optional[str] = None,
    sku: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """
    List PI to PO mappings with pagination and filtering.
    Optimized: Bulk fetches all linked POs for the set of PIs on the current page.
    """
    if page_size > 200: page_size = 200
    if page_size < 1: page_size = 50
    skip = (page - 1) * page_size
    
    pi_query = {"is_active": True}
    if pi_number: pi_query["voucher_no"] = {"$regex": pi_number, "$options": "i"}
    if consignee: pi_query["consignee"] = {"$regex": consignee, "$options": "i"}
    if from_date: pi_query["date"] = {"$gte": from_date}
    if to_date:
        if "date" in pi_query: pi_query["date"]["$lte"] = to_date
        else: pi_query["date"] = {"$lte": to_date}
    if search:
        pi_query["$or"] = [
            {"voucher_no": {"$regex": search, "$options": "i"}},
            {"consignee": {"$regex": search, "$options": "i"}},
            {"line_items.sku": {"$regex": search, "$options": "i"}},
            {"line_items.product_name": {"$regex": search, "$options": "i"}}
        ]
    
    total_count = await mongo_db.proforma_invoices.count_documents(pi_query)
    pis = await mongo_db.proforma_invoices.find(pi_query, {"_id": 0}).sort("date", -1).skip(skip).limit(page_size).to_list(length=None)
    
    if not pis:
        return {"data": [], "total_count": 0, "page": page, "page_size": page_size}

    pi_ids = [pi["id"] for pi in pis]
    
    # Bulk fetch all linked POs
    po_query = {
        "is_active": True,
        "$or": [
            {"reference_pi_id": {"$in": pi_ids}},
            {"reference_pi_ids": {"$in": pi_ids}}
        ]
    }
    if po_number:
        po_query["voucher_no"] = {"$regex": po_number, "$options": "i"}
        
    all_linked_pos = await mongo_db.purchase_orders.find(po_query, {"_id": 0}).to_list(length=None)
    
    # Map PIs to their POs
    pi_to_pos = {pi_id: [] for pi_id in pi_ids}
    for po in all_linked_pos:
        ref_ids = po.get("reference_pi_ids", []) or ([po.get("reference_pi_id")] if po.get("reference_pi_id") else [])
        for rid in ref_ids:
            if rid in pi_to_pos:
                pi_to_pos[rid].append(po)

    mappings = []
    for pi in pis:
        pi_id = pi.get("id")
        pi_items = []
        for item in pi.get("line_items", []):
            pi_items.append({
                "sku": item.get("sku", ""),
                "product_name": item.get("product_name", ""),
                "pi_quantity": item.get("quantity", 0),
                "pi_rate": item.get("rate", 0)
            })
            
        linked_pos = []
        pi_linked_pos = pi_to_pos.get(pi_id, [])
        for po in pi_linked_pos:
            po_items = []
            for po_item in po.get("line_items", []):
                po_sku = po_item.get("sku", "")
                pi_item = next((item for item in pi_items if item["sku"] == po_sku), None)
                if pi_item:
                    po_items.append({
                        "sku": po_sku,
                        "product_name": po_item.get("product_name", ""),
                        "po_quantity": po_item.get("quantity", 0),
                        "po_rate": po_item.get("rate", 0),
                        "pi_quantity": pi_item["pi_quantity"],
                        "pi_rate": pi_item["pi_rate"],
                        "remaining_quantity": pi_item["pi_quantity"] - po_item.get("quantity", 0)
                    })
            if po_items:
                linked_pos.append({
                    "po_number": po.get("voucher_no") or po.get("po_no"),
                    "po_date": po.get("date"),
                    "po_id": po.get("id"),
                    "items": po_items
                })
        
        # Skill filter check
        if sku:
            has_sku = any(sku.lower() in item["sku"].lower() for item in pi_items)
            if not has_sku:
                has_sku = any(any(sku.lower() in item["sku"].lower() for item in po["items"]) for po in linked_pos)
            if not has_sku: continue

        consignee_val = pi.get("consignee") or pi.get("buyer") or "N/A"
        pi_number_val = pi.get("voucher_no", "N/A")
        pi_total_quantity = sum(item.get("pi_quantity", 0) for item in pi_items)

        mappings.append({
            "id": pi_id,
            "consignee": consignee_val,
            "pi_number": pi_number_val,
            "pi_date": pi.get("date"),
            "pi_total_quantity": pi_total_quantity,
            "pi_items": pi_items,
            "linked_pos": linked_pos,
            "linked_po_count": len(linked_pos)
        })
    
    return {
        "data": mappings,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    }


@api_router.get("/pi-po-mapping/{mapping_id}")
async def get_pi_po_mapping_detail(
    mapping_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get detailed PI to PO mapping for a specific PI.
    Returns full hierarchical structure with all linked POs and SKU details.
    """
    # Find the PI
    pi = await mongo_db.proforma_invoices.find_one({"id": mapping_id, "is_active": True}, {"_id": 0})
    
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    pi_id = pi.get("id")
    pi_number = pi.get("voucher_no")
    consignee = pi.get("consignee", "")
    
    # Calculate PI total quantity
    pi_total_quantity = sum(item.get("quantity", 0) for item in pi.get("line_items", []))
    
    # Build PI items with aggregated PO quantities
    pi_items_map = {}
    for item in pi.get("line_items", []):
        sku = item.get("sku", "")
        pi_items_map[sku] = {
            "sku": sku,
            "product_name": item.get("product_name", ""),
            "pi_quantity": item.get("quantity", 0),
            "pi_rate": item.get("rate", 0),
            "total_po_quantity": 0,  # Will be calculated
            "remaining_quantity": item.get("quantity", 0)  # Will be updated
        }
    
    # Find all linked POs
    po_query = {
        "$or": [
            {"reference_pi_id": pi_id},
            {"reference_pi_ids": pi_id}
        ],
        "is_active": True
    }
    
    linked_pos = []
    po_cursor = mongo_db.purchase_orders.find(po_query, {"_id": 0}).sort("date", 1)
    
    async for po in po_cursor:
        po_items = []
        
        for po_item in po.get("line_items", []):
            po_sku = po_item.get("sku", "")
            
            if po_sku in pi_items_map:
                po_quantity = po_item.get("quantity", 0)
                pi_item = pi_items_map[po_sku]
                
                # Update total PO quantity for this SKU
                pi_item["total_po_quantity"] += po_quantity
                
                po_items.append({
                    "sku": po_sku,
                    "product_name": po_item.get("product_name", ""),
                    "po_quantity": po_quantity,
                    "po_rate": po_item.get("rate", 0),
                    "pi_quantity": pi_item["pi_quantity"],
                    "pi_rate": pi_item["pi_rate"],
                    "remaining_quantity": pi_item["pi_quantity"] - pi_item["total_po_quantity"]
                })
        
        if po_items:
            linked_pos.append({
                "po_number": po.get("voucher_no"),
                "po_date": po.get("date"),
                "po_id": po.get("id"),
                "items": po_items
            })
    
    # Update remaining quantities in pi_items_map
    for sku, item in pi_items_map.items():
        item["remaining_quantity"] = item["pi_quantity"] - item["total_po_quantity"]
    
    # Calculate totals
    total_po_quantity = sum(item["total_po_quantity"] for item in pi_items_map.values())
    total_remaining = sum(item["remaining_quantity"] for item in pi_items_map.values())
    
    return {
        "id": pi_id,
        "consignee": consignee,
        "pi_number": pi_number,
        "pi_date": pi.get("date"),
        "pi_total_quantity": pi_total_quantity,
        "total_po_quantity": total_po_quantity,
        "total_remaining_quantity": total_remaining,
        "pi_items": list(pi_items_map.values()),
        "linked_pos": linked_pos,
        "linked_po_count": len(linked_pos)
    }


@api_router.put("/pi-po-mapping/{mapping_id}")
async def update_pi_po_mapping(
    mapping_id: str,
    update_data_body: MappingUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update PI to PO mapping metadata (notes, status).
    This endpoint allows updating mapping-related metadata without modifying core PI/PO data.
    """
    # Verify PI exists
    pi = await mongo_db.proforma_invoices.find_one({"id": mapping_id, "is_active": True})
    
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    # Update metadata (can be stored in a separate mapping_metadata collection if needed)
    # For now, we'll add fields to the PI document
    update_data = {}
    
    if update_data_body.notes is not None:
        update_data["mapping_notes"] = update_data_body.notes
    
    if update_data_body.status is not None:
        update_data["mapping_status"] = update_data_body.status
    
    if update_data:
        await mongo_db.proforma_invoices.update_one(
            {"id": mapping_id},
            {"$set": update_data}
        )
    
    return {"message": "Mapping updated successfully", "id": mapping_id}


@api_router.delete("/pi-po-mapping/{mapping_id}")
async def delete_pi_po_mapping(
    mapping_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Soft delete PI to PO mapping.
    This marks the PI as archived/deleted without removing the actual data.
    """
    # Verify PI exists
    pi = await mongo_db.proforma_invoices.find_one({"id": mapping_id, "is_active": True})
    
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    # Soft delete by setting is_active to False
    await mongo_db.proforma_invoices.update_one(
        {"id": mapping_id},
        {
            "$set": {
                "is_active": False,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Mapping archived successfully", "id": mapping_id}


@api_router.get("/customer-management/inward-quantity")
async def get_inward_quantity(
    consignee: Optional[str] = None,
    pi_number: Optional[str] = None,
    po_number: Optional[str] = None,
    sku: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get inward quantity tracking (only Inward to Warehouse type)"""
    inward_data = []
    
    # Build PI query
    pi_query = {"is_active": True}
    if pi_number:
        pi_query["voucher_no"] = {"$regex": pi_number, "$options": "i"}
    if consignee:
        pi_query["consignee"] = {"$regex": consignee, "$options": "i"}
    
    async for pi in mongo_db.proforma_invoices.find(pi_query, {"_id": 0}):
        # Get linked POs (search in both reference_pi_id and reference_pi_ids array)
        po_query = {
            "$or": [
                {"reference_pi_id": pi["id"]},
                {"reference_pi_ids": pi["id"]}
            ],
            "is_active": True
        }
        if po_number:
            po_query["voucher_no"] = {"$regex": po_number, "$options": "i"}
        
        async for po in mongo_db.purchase_orders.find(po_query, {"_id": 0}):
            # Get inward entries linked to this PO (only warehouse type)
            inward_entries = []
            async for inward in mongo_db.inward_stock.find({
                "po_id": po["id"],
                "inward_type": "warehouse",  # Only Inward to Warehouse
                "is_active": True
            }, {"_id": 0}):
                inward_entries.append(inward)
            
            # Calculate quantities per SKU
            pi_sku_quantities = {}
            for item in pi.get("line_items", []):
                sku_key = item.get("sku")
                if not sku or sku.lower() in sku_key.lower():
                    pi_sku_quantities[sku_key] = {
                        "product_name": item.get("product_name"),
                        "pi_quantity": item.get("quantity", 0),
                        "inward_quantity": 0,
                        "remaining_quantity": item.get("quantity", 0)
                    }
            
            # Calculate inwarded quantities
            for inward in inward_entries:
                for item in inward.get("line_items", []):
                    sku_key = item.get("sku")
                    if sku_key in pi_sku_quantities:
                        pi_sku_quantities[sku_key]["inward_quantity"] += item.get("quantity", 0)
                        pi_sku_quantities[sku_key]["remaining_quantity"] = (
                            pi_sku_quantities[sku_key]["pi_quantity"] - 
                            pi_sku_quantities[sku_key]["inward_quantity"]
                        )
            
            if sku and not pi_sku_quantities:
                continue
            
            # Calculate status
            total_pi_qty = sum(d["pi_quantity"] for d in pi_sku_quantities.values())
            total_inward_qty = sum(d["inward_quantity"] for d in pi_sku_quantities.values())
            
            if total_inward_qty == 0:
                status = "Not Started"
            elif total_inward_qty >= total_pi_qty:
                status = "Completed"
            else:
                status = "Partially Inwarded"
            
            inward_data.append({
                "consignee_name": pi.get("consignee"),
                "pi_number": pi.get("voucher_no"),
                "pi_id": pi.get("id"),
                "po_number": po.get("voucher_no"),
                "po_id": po.get("id"),
                "pi_total_quantity": total_pi_qty,
                "inward_total_quantity": total_inward_qty,
                "remaining_quantity": total_pi_qty - total_inward_qty,
                "sku_details": [
                    {
                        "sku": sku,
                        "product_name": data["product_name"],
                        "pi_quantity": data["pi_quantity"],
                        "inward_quantity": data["inward_quantity"],
                        "remaining_quantity": data["remaining_quantity"]
                    }
                    for sku, data in pi_sku_quantities.items()
                ],
                "status": status
            })
    
    return inward_data

@api_router.get("/customer-management/outward-quantity")
async def get_outward_quantity(
    consignee: Optional[str] = None,
    pi_number: Optional[str] = None,
    sku: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """
    STOCK SUMMARY REBUILD - Get outward quantity tracking
    Counts both Export Invoice AND Dispatch Plans
    Deduplicates Dispatch Plans that are already linked to Export Invoices
    """
    outward_data = []
    
    # Build PI query
    pi_query = {"is_active": True}
    if pi_number:
        pi_query["voucher_no"] = {"$regex": pi_number, "$options": "i"}
    if consignee:
        pi_query["consignee"] = {"$regex": consignee, "$options": "i"}
    
    async for pi in mongo_db.proforma_invoices.find(pi_query, {"_id": 0}):
        # Get outward entries linked to this PI - ONLY Export Invoice
        # Use $or to avoid duplicate counting
        outward_query = {
            "$or": [
                {"pi_id": pi["id"]},
                {"pi_ids": pi["id"]}
            ],
            "dispatch_type": {"$in": ["dispatch_plan", "export_invoice"]},
            "is_active": True
        }
        
        # Calculate quantities per SKU
        pi_sku_quantities = {}
        for item in pi.get("line_items", []):
            item_sku = item.get("sku") or ""
            item_pid = item.get("product_id") or ""
            # If search filter 'sku' matches
            if not sku or (item_sku and sku.lower() in item_sku.lower()):
                # Create a robust key combining PID and SKU to handle empty fields
                unique_key = f"{item_pid}_{item_sku}"
                pi_sku_quantities[unique_key] = {
                    "product_id": item_pid,
                    "sku": item_sku,
                    "product_name": item.get("product_name"),
                    "pi_quantity": float(item.get("quantity", 0)),
                    "outward_quantity": 0,
                    "remaining_quantity": float(item.get("quantity", 0))
                }
        
        # Calculate outwarded quantities - Fetch all associated records
        all_outwards = await mongo_db.outward_stock.find(outward_query, {"_id": 0}).to_list(None)
        
        # Deduplication: Track dispatch plans that are already converted to invoices
        invoiced_plan_ids = {o.get("dispatch_plan_id") for o in all_outwards if o.get("dispatch_type") == "export_invoice" and o.get("dispatch_plan_id")}
        
        for outward in all_outwards:
            # Skip if this is a dispatch plan that has already been fulfilled by an export invoice
            if outward.get("dispatch_type") == "dispatch_plan" and outward.get("id") in invoiced_plan_ids:
                continue
                
            for item in outward.get("line_items", []):
                o_sku = item.get("sku") or ""
                o_pid = item.get("product_id") or ""
                
                # Match by PID + SKU or Name if needed, but here we use our prepared map
                match_key = f"{o_pid}_{o_sku}"
                
                # If exact key doesn't match, try matching by PID or SKU independently
                if match_key not in pi_sku_quantities:
                    found_key = None
                    for k, d in pi_sku_quantities.items():
                        if (o_pid and d["product_id"] == o_pid) or (o_sku and d["sku"] == o_sku):
                            found_key = k
                            break
                    match_key = found_key

                if match_key and match_key in pi_sku_quantities:
                    qty = float(item.get("dispatch_quantity") or item.get("quantity", 0))
                    pi_sku_quantities[match_key]["outward_quantity"] += qty
                    pi_sku_quantities[match_key]["remaining_quantity"] = (
                        pi_sku_quantities[match_key]["pi_quantity"] - 
                        pi_sku_quantities[match_key]["outward_quantity"]
                    )
        
        if sku and not pi_sku_quantities:
            continue
        
        # Calculate status
        total_pi_qty = sum(d["pi_quantity"] for d in pi_sku_quantities.values())
        total_outward_qty = sum(d["outward_quantity"] for d in pi_sku_quantities.values())
        
        if total_outward_qty == 0:
            calc_status = "Not Started"
        elif total_outward_qty >= total_pi_qty:
            calc_status = "Completed"
        else:
            calc_status = "Partially Outwarded"
        
        # Filter by status if provided
        if status and calc_status != status:
            continue
        
        outward_data.append({
            "consignee_name": pi.get("consignee"),
            "pi_number": pi.get("voucher_no"),
            "pi_id": pi.get("id"),
            "pi_date": pi.get("date"),
            "pi_total_quantity": total_pi_qty,
            "outward_total_quantity": total_outward_qty,
            "remaining_quantity": total_pi_qty - total_outward_qty,
            "sku_details": [
                {
                    "sku": d["sku"],
                    "product_name": d["product_name"],
                    "pi_quantity": d["pi_quantity"],
                    "outward_quantity": d["outward_quantity"],
                    "remaining_quantity": d["remaining_quantity"]
                }
                for d in pi_sku_quantities.values()
            ],
            "status": calc_status
        })
    
    return outward_data

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_active_user)):
    """
    Get dashboard statistics with optimized aggregation.
    """
    total_companies = await mongo_db.companies.count_documents({"is_active": True})
    total_warehouses = await mongo_db.warehouses.count_documents({"is_active": True})
    total_products = await mongo_db.products.count_documents({"is_active": True})
    total_pis = await mongo_db.proforma_invoices.count_documents({"is_active": True})
    total_pos = await mongo_db.purchase_orders.count_documents({"is_active": True})
    
    # Calculate Total Stock Inward (Optimized)
    inward_pipeline = [
        {"$match": {"is_active": True}},
        {"$unwind": "$line_items"},
        {"$group": {"_id": None, "total_qty": {"$sum": "$line_items.quantity"}}}
    ]
    inward_result = await mongo_db.inward_stock.aggregate(inward_pipeline).to_list(1)
    total_stock_inward = inward_result[0]["total_qty"] if inward_result else 0
    
    # Calculate Total Stock Outward (Optimized with Deduplication)
    # Strategy: Aggregation with $lookup to find if a dispatch_plan is already invoiced
    outward_pipeline = [
        {"$match": {"is_active": True}},
        # Identify dispatch plans and check if they have a corresponding export invoice
        {"$project": {
            "id": 1,
            "dispatch_type": 1,
            "dispatch_plan_id": 1,
            "line_items": 1
        }},
        # Group to find all plan IDs that are invoiced
        {"$facet": {
            "invoiced_plans": [
                {"$match": {"dispatch_type": "export_invoice", "dispatch_plan_id": {"$exists": True, "$ne": None}}},
                {"$group": {"_id": None, "ids": {"$addToSet": "$dispatch_plan_id"}}}
            ],
            "all_entries": [
                {"$match": {}}
            ]
        }},
        {"$unwind": "$all_entries"},
        {"$project": {
            "entry": "$all_entries",
            "invoiced_plan_ids": {"$ifNull": [{"$arrayElemAt": ["$invoiced_plans.ids", 0]}, []]}
        }},
        # Filter: Skip if dispatch_plan AND in invoiced_plan_ids
        {"$match": {
            "$expr": {
                "$not": {
                    "$and": [
                        {"$eq": ["$entry.dispatch_type", "dispatch_plan"]},
                        {"$in": ["$entry.id", "$invoiced_plan_ids"]}
                    ]
                }
            }
        }},
        {"$unwind": "$entry.line_items"},
        {"$group": {
            "_id": None,
            "total_qty": {"$sum": {"$ifNull": ["$entry.line_items.quantity", "$entry.line_items.dispatch_quantity"]}}
        }}
    ]
    
    outward_result = await mongo_db.outward_stock.aggregate(outward_pipeline).to_list(1)
    total_stock_outward = outward_result[0]["total_qty"] if outward_result else 0
    
    pending_pis = await mongo_db.proforma_invoices.count_documents({
        "is_active": True,
        "status": {"$in": ["Pending", "Draft"]}
    })
    
    pending_pos = await mongo_db.purchase_orders.count_documents({
        "is_active": True,
        "status": {"$in": ["Pending", "Draft"]}
    })
    
    return {
        "total_companies": total_companies,
        "total_warehouses": total_warehouses,
        "total_pis": total_pis,
        "total_pos": total_pos,
        "total_products": total_products,
        "total_stock_inward": total_stock_inward,
        "total_stock_outward": total_stock_outward,
        "pending_pis": pending_pis,
        "pending_pos": pending_pos
    }


# Include router in app
# ==================== CUSTOMER TRACKING ====================
@api_router.get("/customer-tracking")
async def get_customer_tracking(
    customer_name: Optional[str] = None,
    pi_number: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get customer tracking data with PI, Inward, and Outward quantity mapping
    Auto-calculates remaining quantities for inward and dispatch
    """
    
    tracking_data = []
    
    # Get all PIs (base data)
    pi_query = {"is_active": True}
    if pi_number:
        pi_query["voucher_no"] = {"$regex": pi_number, "$options": "i"}
    
    async for pi in mongo_db.proforma_invoices.find(pi_query, {"_id": 0}).sort("date", -1):
        # Get customer/company details - try company_id first, fallback to buyer/consignee
        customer = None
        if pi.get("company_id"):
            customer = await mongo_db.companies.find_one({"id": pi.get("company_id")}, {"_id": 0})
        if not customer and pi.get("customer_id"):
            customer = await mongo_db.companies.find_one({"id": pi.get("customer_id")}, {"_id": 0})
        # Fallback: use buyer or consignee field directly from PI
        if customer:
            customer_name_str = customer.get("name", "Unknown")
        else:
            customer_name_str = pi.get("buyer") or pi.get("consignee") or pi.get("company_name") or "Unknown"
        
        # Filter by customer name if provided
        if customer_name and customer_name.lower() not in customer_name_str.lower():
            continue
        
        # Process each line item in PI
        for pi_item in pi.get("line_items", []):
            product_id = pi_item.get("product_id")
            pi_quantity = float(pi_item.get("quantity", 0))
            
            # Calculate Inwarded Quantity (from Inward Stock entries linked to this PI)
            inwarded_quantity = 0.0
            inward_details = []
            
            # Find POs linked to this PI - check all possible reference fields
            linked_pos = []
            async for po in mongo_db.purchase_orders.find({
                "$or": [
                    {"reference_pi_ids": pi["id"]},
                    {"reference_pi_id": pi["id"]},
                    {"pi_id": pi["id"]}
                ],
                "is_active": True
            }, {"_id": 0}):
                linked_pos.append(po)
            
            # Find inward entries linked to these POs
            for po in linked_pos:
                async for inward in mongo_db.inward_stock.find({
                    "po_id": po["id"],
                    "is_active": True
                }, {"_id": 0}):
                    for inward_item in inward.get("line_items", []):
                        # Match by product_id or SKU
                        if (inward_item.get("product_id") == product_id or
                            (pi_item.get("sku") and inward_item.get("sku") == pi_item.get("sku"))):
                            qty = float(inward_item.get("quantity", 0))
                            inwarded_quantity += qty
                            inward_details.append({
                                "po_number": po.get("voucher_no") or po.get("po_no"),
                                "inward_invoice_no": inward.get("inward_invoice_no"),
                                "date": inward.get("date"),
                                "quantity": qty
                            })
            
            # Calculate Dispatched Quantity (from Dispatch Plans and Export Invoices)
            dispatched_quantity = 0.0
            dispatch_details = []
            
            outward_query = {
                "$or": [
                    {"pi_id": pi["id"]},
                    {"pi_ids": pi["id"]}
                ],
                "dispatch_type": {"$in": ["dispatch_plan", "export_invoice"]},
                "is_active": True
            }
            
            all_outwards = await mongo_db.outward_stock.find(outward_query, {"_id": 0}).to_list(None)
            invoiced_plan_ids = {o.get("dispatch_plan_id") for o in all_outwards if o.get("dispatch_type") == "export_invoice" and o.get("dispatch_plan_id")}
            
            for outward in all_outwards:
                if outward.get("dispatch_type") == "dispatch_plan" and outward.get("id") in invoiced_plan_ids:
                    continue
                    
                for outward_item in outward.get("line_items", []):
                    # Match by product_id or SKU or Name
                    o_pid = outward_item.get("product_id")
                    o_sku = outward_item.get("sku")
                    o_name = outward_item.get("product_name")
                    
                    matches = False
                    if product_id and o_pid == product_id:
                        matches = True
                    elif pi_item.get("sku") and o_sku == pi_item.get("sku"):
                        matches = True
                    elif pi_item.get("product_name") == o_name:
                        matches = True
                        
                    if matches:
                        qty = float(outward_item.get("dispatch_quantity", 0) or outward_item.get("quantity", 0))
                        dispatched_quantity += qty
                        dispatch_details.append({
                            "export_invoice_no": outward.get("export_invoice_no"),
                            "date": outward.get("date"),
                            "quantity": qty,
                            "dispatch_type": outward.get("dispatch_type")
                        })
            
            # Calculate remaining quantities
            remaining_inward = pi_quantity - inwarded_quantity
            remaining_dispatch = pi_quantity - dispatched_quantity
            
            tracking_data.append({
                "customer_name": customer_name_str,
                "pi_number": pi.get("voucher_no"),
                "pi_date": pi.get("date"),
                "product_name": pi_item.get("product_name"),
                "sku": pi_item.get("sku"),
                "pi_quantity": pi_quantity,
                "inwarded_quantity": inwarded_quantity,
                "remaining_quantity_inward": remaining_inward,
                "dispatched_quantity": dispatched_quantity,
                "remaining_quantity_dispatch": remaining_dispatch,
                "inward_details": inward_details,
                "dispatch_details": dispatch_details,
                "linked_po_numbers": [po.get("voucher_no") or po.get("po_no") for po in linked_pos],
                "status": "Completed" if remaining_dispatch == 0 else "Pending"
            })
    
    return tracking_data

@api_router.get("/purchase-analysis")
async def get_purchase_analysis(
    company_ids: Optional[str] = None,  # Comma-separated company IDs
    pi_numbers: Optional[str] = None,   # Comma-separated PI numbers
    current_user: dict = Depends(get_current_active_user)
):
    """
    Purchase Analysis Module
    Optimized: Bulk fetches all inward and in-transit records for performance.
    """
    try:
        company_id_list = company_ids.split(",") if company_ids else []
        pi_number_list = pi_numbers.split(",") if pi_numbers else []
        
        if not company_id_list or not pi_number_list:
            return {"message": "Please select Company and PI Number filters", "data": []}
        
        # 1. Fetch Company Names for mapping (PIs might use names)
        expanded_company_ids = list(company_id_list)
        async for company in mongo_db.companies.find({"id": {"$in": company_id_list}}):
            if company.get("name"):
                expanded_company_ids.append(company["name"])
        
        # 2. Fetch PIs
        pi_query = {
            "company_id": {"$in": expanded_company_ids},
            "voucher_no": {"$in": pi_number_list},
            "is_active": True
        }
        pis = await mongo_db.proforma_invoices.find(pi_query, {"_id": 0}).to_list(None)
        if not pis:
            return {"message": "No PIs found for selected filters", "data": []}
        
        pi_ids = [pi.get("id") for pi in pis]
        
        # 3. Fetch POs linked to these PIs
        po_query = {
            "$or": [
                {"reference_pi_id": {"$in": pi_ids}},
                {"reference_pi_ids": {"$in": pi_ids}},
                {"pi_id": {"$in": pi_ids}}
            ],
            "is_active": True
        }
        pos = await mongo_db.purchase_orders.find(po_query, {"_id": 0}).to_list(None)
        po_ids = [po["id"] for po in pos]

        # 4. Bulk fetch Inward and In-Transit records for all POs
        inwards = await mongo_db.inward_stock.find({
            "po_id": {"$in": po_ids},
            "inward_type": "warehouse",
            "is_active": True
        }, {"_id": 0}).to_list(None)

        pickups = await mongo_db.pickup_in_transit.find({
            "po_id": {"$in": po_ids},
            "is_active": True,
            "is_inwarded": {"$ne": True}
        }, {"_id": 0}).to_list(None)

        # 5. Process everything in memory
        analysis_data = []
        for po in pos:
            po_number = po.get("voucher_no") or po.get("po_no")
            po_id = po.get("id")
            ref_pi_ids = po.get("reference_pi_ids", [])
            if not ref_pi_ids and po.get("reference_pi_id"):
                ref_pi_ids = [po.get("reference_pi_id")]
            
            for po_item in po.get("line_items", []):
                product_id = po_item.get("product_id")
                sku = po_item.get("sku")
                po_quantity = float(po_item.get("quantity", 0))
                
                # Find matching PI and quantity
                pi_quantity = 0
                buyer = "N/A"
                pi_no = "N/A"
                for pi in pis:
                    if pi.get("id") in ref_pi_ids:
                        buyer = pi.get("buyer", "N/A")
                        pi_no = pi.get("voucher_no", "N/A")
                        for pi_item in pi.get("line_items", []):
                            if (product_id and pi_item.get("product_id") == product_id) or (sku and pi_item.get("sku") == sku):
                                pi_quantity = float(pi_item.get("quantity", 0))
                                break
                        break
                
                # Calculate Inward Qty from bulk data
                inward_quantity = 0
                for inward in inwards:
                    if inward.get("po_id") == po_id:
                        for item in inward.get("line_items", []):
                            if (product_id and item.get("product_id") == product_id) or (sku and item.get("sku") == sku) or (item.get("id") == po_item.get("id") and po_item.get("id")):
                                inward_quantity += float(item.get("quantity", 0))
                
                # Calculate In-Transit Qty from bulk data
                intransit_quantity = 0
                for pickup in pickups:
                    if pickup.get("po_id") == po_id:
                        for item in pickup.get("line_items", []):
                            if (product_id and item.get("product_id") == product_id) or (sku and item.get("sku") == sku) or (item.get("id") == po_item.get("id") and po_item.get("id")):
                                intransit_quantity += float(item.get("quantity", 0))
                
                analysis_data.append({
                    "buyer": buyer,
                    "product_name": po_item.get("product_name"),
                    "sku": sku,
                    "pi_number": pi_no,
                    "pi_quantity": pi_quantity,
                    "po_number": po_number,
                    "po_quantity": po_quantity,
                    "inward_quantity": inward_quantity,
                    "intransit_quantity": intransit_quantity,
                    "remaining_quantity": po_quantity - inward_quantity - intransit_quantity
                })
        
        return {"data": analysis_data, "count": len(analysis_data)}
        
    except Exception as e:
        logger.error(f"Error in purchase analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PICKUP (IN-TRANSIT) ROUTES ====================
# @api_router.get("/pos/lines-with-stats")
# async def get_po_lines_with_stats(
#     voucher_no: str,
#     current_user: dict = Depends(get_current_active_user)
# ):
#     """
#     Get PO line items with detailed statistics:
#     - PI Qty (from PI reference)
#     - PO Qty (from PO)
#     - Already Inwarded (from inward_stock)
#     - In-Transit (from pickup_in_transit collection)
    
#     Query param: voucher_no (PO voucher number)
#     """
#     try:
#         # Find PO by voucher number
#         po = await mongo_db.purchase_orders.find_one({"voucher_no": voucher_no, "is_active": True}, {"_id": 0})
#         if not po:
#             raise HTTPException(status_code=404, detail=f"PO not found with voucher number: {voucher_no}")
        
#         po_id = po.get("id")
        
#         # Get reference PI IDs from PO
#         reference_pi_ids = po.get("reference_pi_ids", [])
#         if not reference_pi_ids and po.get("reference_pi_id"):
#             reference_pi_ids = [po.get("reference_pi_id")]
        
#         # Fetch all referenced PIs
#         pis = []
#         if reference_pi_ids:
#             async for pi in mongo_db.proforma_invoices.find({"id": {"$in": reference_pi_ids}, "is_active": True}, {"_id": 0}):
#                 pis.append(pi)
        
#         # Build line items with stats
#         line_stats = []
#         for po_item in po.get("line_items", []):
#             product_id = po_item.get("product_id")
#             product_name = po_item.get("product_name")
#             sku = po_item.get("sku")
#             po_quantity = float(po_item.get("quantity", 0))
#             rate = float(po_item.get("rate", 0))
            
#             # Find matching PI quantity
#             pi_quantity = 0
#             for pi in pis:
#                 for pi_item in pi.get("line_items", []):
#                     if pi_item.get("product_id") == product_id:
#                         pi_quantity += float(pi_item.get("quantity", 0))
            
#             # Calculate Already Inwarded (from inward_stock)
#             already_inwarded = 0
#             async for inward in mongo_db.inward_stock.find({
#                 "po_id": po_id,
#                 "is_active": True
#             }, {"_id": 0}):
#                 for inward_item in inward.get("line_items", []):
#                     if inward_item.get("product_id") == product_id:
#                         already_inwarded += float(inward_item.get("quantity", 0))
            
#             # Calculate In-Transit (from pickup_in_transit collection)
#             in_transit = 0
#             async for pickup in mongo_db.pickup_in_transit.find({
#                 "po_id": po_id,
#                 "is_active": True
#             }, {"_id": 0}):
#                 for pickup_item in pickup.get("line_items", []):
#                     if pickup_item.get("product_id") == product_id:
#                         in_transit += float(pickup_item.get("quantity", 0))
            
#             # Calculate available quantity for pickup
#             available_for_pickup = po_quantity - already_inwarded - in_transit
            
#             line_stats.append({
#                 "id": po_item.get("id"),  # ✅ PO line item ID - required for pickup creation
#                 "product_id": product_id,
#                 "product_name": product_name,
#                 "sku": sku,
#                 "pi_quantity": pi_quantity,
#                 "po_quantity": po_quantity,
#                 "already_inwarded": already_inwarded,
#                 "in_transit": in_transit,
#                 "available_for_pickup": available_for_pickup,
#                 "rate": rate
#             })
        
#         return {
#             "po_voucher_no": voucher_no,
#             "po_id": po_id,
#             "po_date": po.get("date"),
#             "supplier": po.get("supplier"),
#             "line_items": line_stats
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error fetching PO line stats: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/pos/lines-with-stats")
async def get_po_lines_with_stats(
    voucher_no: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get PO line items with detailed statistics:
    - PI Qty (from PI reference)
    - PO Qty (from PO)
    - Already Inwarded (from inward_stock)
    - In-Transit (from pickup_in_transit collection)
    
    Query param: voucher_no (can be a single voucher or comma-separated list of vouchers)
    Optimized: Bulk fetches all inward and in-transit records.
    """
    try:
        voucher_nos = [v.strip() for v in voucher_no.split(",") if v.strip()]
        if not voucher_nos:
             raise HTTPException(status_code=400, detail="At least one voucher number is required")

        # 1. Find all POs by voucher numbers
        pos = await mongo_db.purchase_orders.find({"voucher_no": {"$in": voucher_nos}, "is_active": True}, {"_id": 0}).to_list(length=100)
        if not pos:
            raise HTTPException(status_code=404, detail=f"No active POs found for vouchers: {voucher_no}")
        
        po_ids = [po.get("id") for po in pos]
        
        # 2. Collect and aggregate all referenced PIs
        all_pi_ids = []
        for po in pos:
            ref_ids = po.get("reference_pi_ids", [])
            if not ref_ids and po.get("reference_pi_id"):
                ref_ids = [po.get("reference_pi_id")]
            all_pi_ids.extend(ref_ids)
        
        pis = []
        if all_pi_ids:
            pis = await mongo_db.proforma_invoices.find({"id": {"$in": list(set(all_pi_ids))}, "is_active": True}, {"_id": 0}).to_list(None)
        
        # 3. Bulk fetch ALL inward stock for these POs
        inwards = await mongo_db.inward_stock.find({"po_id": {"$in": po_ids}, "is_active": True}, {"_id": 0}).to_list(None)
        
        # 4. Bulk fetch ALL in-transit (pickups) for these POs
        pickups = await mongo_db.pickup_in_transit.find({
            "po_id": {"$in": po_ids}, 
            "is_active": True, 
            "is_inwarded": {"$ne": True}
        }, {"_id": 0}).to_list(None)
        
        # 5. Build lookup maps for fast access
        aggregated_stats = {} # key: product_key (sku or product_id)

        for po in pos:
            po_id = po.get("id")
            for po_item in po.get("line_items", []):
                po_item_id = po_item.get("id")
                product_id = po_item.get("product_id")
                sku = po_item.get("sku")
                product_key = sku if sku else product_id
                
                if product_key not in aggregated_stats:
                    aggregated_stats[product_key] = {
                        "ids": [], 
                        "product_id": product_id,
                        "product_name": po_item.get("product_name"),
                        "sku": sku,
                        "pi_quantity": 0,
                        "po_quantity": 0,
                        "already_inwarded": 0,
                        "in_transit": 0,
                        "rate": float(po_item.get("rate", 0))
                    }
                
                stats = aggregated_stats[product_key]
                stats["ids"].append(po_item_id)
                stats["po_quantity"] += float(po_item.get("quantity", 0))
                
                # Fetch PI quantity for this product from relevant PIs
                for pi in pis:
                    for pi_item in pi.get("line_items", []):
                        if (sku and pi_item.get("sku") == sku) or (not sku and pi_item.get("product_id") == product_id):
                             stats["pi_quantity"] += float(pi_item.get("quantity", 0))

                # Calculate already inwarded from bulk data
                for inward in inwards:
                    if inward.get("po_id") == po_id:
                        for inward_item in inward.get("line_items", []):
                            if inward_item.get("id") == po_item_id or (not inward_item.get("id") and sku and inward_item.get("sku") == sku):
                                stats["already_inwarded"] += float(inward_item.get("quantity", 0))
                
                # Calculate in-transit from bulk data
                for pickup in pickups:
                    if pickup.get("po_id") == po_id:
                        for pickup_item in pickup.get("line_items", []):
                            if pickup_item.get("id") == po_item_id or (not pickup_item.get("id") and sku and pickup_item.get("sku") == sku):
                                stats["in_transit"] += float(pickup_item.get("quantity", 0))

        # 6. Prepare final response
        line_stats = []
        for key, stats in aggregated_stats.items():
            stats["available_for_pickup"] = stats["po_quantity"] - stats["already_inwarded"] - stats["in_transit"]
            # ID is first line item ID or product key
            stats["id"] = stats["ids"][0] if stats["ids"] else key
            line_stats.append(stats)
            
        return {
            "po_voucher_no": ", ".join(voucher_nos),
            "po_ids": po_ids,
            "po_date": pos[0].get("date") if pos else None,
            "supplier": pos[0].get("supplier") if pos else None,
            "line_items": line_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching PO line stats: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# @api_router.post("/pickups")
# async def create_pickup(
#     pickup_data: dict,
#     current_user: dict = Depends(get_current_active_user)
# ):
#     """
#     Create a new Pickup (In-Transit) entry
#     """
#     try:
#         po_id = pickup_data.get("po_id")
#         if not po_id:
#             raise HTTPException(status_code=400, detail="po_id is required")
        
#         # Verify PO exists
#         po = await mongo_db.purchase_orders.find_one({"id": po_id, "is_active": True}, {"_id": 0})
#         if not po:
#             raise HTTPException(status_code=404, detail="PO not found")
        
#         # Validate line items
#         line_items = pickup_data.get("line_items", [])
#         if not line_items:
#             raise HTTPException(status_code=400, detail="At least one line item is required")
        
#         # Validation: Check if new pickup quantities are valid
#         for item in line_items:
#             po_line_id = item.get("id")   # ← PO line item id
#             new_quantity = float(item.get("quantity", 0))

#             if not po_line_id:
#                 raise HTTPException(
#                     status_code=400,
#                     detail="PO line item id is required"
#                 )

            
#             if new_quantity <= 0:
#                 continue  # Skip zero quantities
            
#             # Find PO quantity for this product
#             po_quantity = 0
#             for po_item in po.get("line_items", []):
#                 if po_item.get("id") == po_line_id:
#                     po_quantity = float(po_item.get("quantity", 0))
#                     break

            
#             # Calculate already inwarded
#             already_inwarded = 0
#             async for inward in mongo_db.inward_stock.find({
#                 "po_id": po_id,
#                 "is_active": True
#             }, {"_id": 0}):
#                 for inward_item in inward.get("line_items", []):
#                     if pickup_item.get("id") == po_line_id:
#                         existing_in_transit += float(pickup_item.get("quantity", 0))

            
#             # Calculate existing in-transit
#             existing_in_transit = 0
#             async for pickup in mongo_db.pickup_in_transit.find({
#                 "po_id": po_id,
#                 "is_active": True
#             }, {"_id": 0}):
#                 for pickup_item in pickup.get("line_items", []):
#                     if pickup_item.get("product_id") == po_line_id:
#                         existing_in_transit += float(pickup_item.get("quantity", 0))
            
#             # Validate: new + inwarded + existing in-transit should not exceed PO qty
#             total_quantity = new_quantity + already_inwarded + existing_in_transit
#             if total_quantity > po_quantity:
#                 product_name = item.get("product_name", "Unknown Product")
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Cannot create pickup for {product_name}: Total quantity ({total_quantity}) exceeds PO quantity ({po_quantity}). Already inwarded: {already_inwarded}, Existing in-transit: {existing_in_transit}"
#                 )
        
#         # Create pickup entry
#         pickup_dict = {
#             "id": item.get("id"),
#             "pickup_date": pickup_data.get("pickup_date"),
#             "po_id": po_id,
#             "po_voucher_no": po.get("voucher_no"),
#             "manual": pickup_data.get("manual", ""),
#             "notes": pickup_data.get("notes", ""),
#             "is_active": True,
#             "created_at": datetime.now(timezone.utc).isoformat(),
#             "updated_at": datetime.now(timezone.utc).isoformat(),
#             "created_by": current_user["id"],
#             "line_items": []
#         }
        
#         # Process line items - only add items with quantity > 0
#         for item in line_items:
#             quantity = float(item.get("quantity", 0))
#             if quantity > 0:
#                 line_item = {
#                     "id": str(uuid.uuid4()),
#                     "product_id": item.get("product_id"),
#                     "product_name": item.get("product_name"),
#                     "sku": item.get("sku"),
#                     "quantity": quantity,
#                     "rate": float(item.get("rate", 0))
#                 }
#                 pickup_dict["line_items"].append(line_item)
        
#         if not pickup_dict["line_items"]:
#             raise HTTPException(status_code=400, detail="No valid line items with quantity > 0")
        
#         # Insert pickup entry
#         await mongo_db.pickup_in_transit.insert_one(pickup_dict)
        
#         # Audit log
#         await mongo_db.audit_logs.insert_one({
#             "action": "pickup_created",
#             "user_id": current_user["id"],
#             "entity_id": pickup_dict["id"],
#             "timestamp": datetime.now(timezone.utc).isoformat()
#         })
        
#         pickup_dict.pop("_id", None)
#         return pickup_dict
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error creating pickup: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# --- DELETED DUPLICATE PICKUP ROUTES ---
    """Delete (soft delete) a pickup entry"""
    pickup = await mongo_db.pickup_in_transit.find_one({"id": pickup_id, "is_active": True}, {"_id": 0})
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found")
    
    await mongo_db.pickup_in_transit.update_one({"id": pickup_id}, {"$set": {"is_active": False}})
    
    await mongo_db.audit_logs.insert_one({
        "action": "pickup_deleted",
        "user_id": current_user["id"],
        "entity_id": pickup_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Pickup deleted successfully"}

@api_router.post("/pickups/bulk-delete")
async def bulk_delete_pickups(
    payload: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Bulk delete pickup entries"""
    ids = payload.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    deleted = []
    failed = []
    
    for pickup_id in ids:
        try:
            pickup = await mongo_db.pickup_in_transit.find_one({"id": pickup_id, "is_active": True}, {"_id": 0})
            if not pickup:
                failed.append({"id": pickup_id, "reason": "Pickup not found"})
                continue
            
            # Soft delete
            await mongo_db.pickup_in_transit.update_one(
                {"id": pickup_id},
                {"$set": {"is_active": False}}
            )
            deleted.append(pickup_id)
            
            # Audit log
            await mongo_db.audit_logs.insert_one({
                "action": "pickup_bulk_deleted",
                "user_id": current_user["id"],
                "entity_id": pickup_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            failed.append({"id": pickup_id, "reason": str(e)})
    
    return {
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "failed_count": len(failed),
        "failed": failed
    }

# ==================== INWARD STOCK BULK OPERATIONS ====================
@api_router.post("/inward-stock/bulk-delete")
async def bulk_delete_inward_stock(
    payload: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Bulk delete inward stock entries"""
    ids = payload.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    deleted = []
    failed = []
    
    for inward_id in ids:
        try:
            inward = await mongo_db.inward_stock.find_one({"id": inward_id, "is_active": True}, {"_id": 0})
            if not inward:
                failed.append({"id": inward_id, "reason": "Inward entry not found"})
                continue
            
            # Check if there's related outward stock that actually deducted from THIS inward entry
            # In transaction-based tracking, we check if any outward has been recorded against this batch
            has_dispatched = await mongo_db.stock_tracking.count_documents({
                "inward_entry_id": inward_id,
                "quantity_outward": {"$gt": 0}
            })
            
            if has_dispatched > 0:
                failed.append({
                    "id": inward_id,
                    "reason": f"Cannot delete: {has_dispatched} units already dispatched from this batch"
                })
                continue
            
            # Soft delete
            await mongo_db.inward_stock.update_one(
                {"id": inward_id},
                {"$set": {"is_active": False}}
            )
            
            # Remove from stock summary
            await mongo_db.stock_tracking.delete_many({"inward_entry_id": inward_id})
            
            deleted.append(inward_id)
            
            # Audit log
            await mongo_db.audit_logs.insert_one({
                "action": "inward_bulk_deleted",
                "user_id": current_user["id"],
                "entity_id": inward_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            failed.append({"id": inward_id, "reason": str(e)})
    
    return {
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "failed_count": len(failed),
        "failed": failed
    }

# ==================== OUTWARD STOCK BULK OPERATIONS ====================
@api_router.post("/outward-stock/bulk-delete")
async def bulk_delete_outward_stock(
    payload: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Bulk delete outward stock entries"""
    ids = payload.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    deleted = []
    failed = []
    
    for outward_id in ids:
        try:
            outward = await mongo_db.outward_stock.find_one({"id": outward_id, "is_active": True}, {"_id": 0})
            if not outward:
                failed.append({"id": outward_id, "reason": "Outward entry not found"})
                continue
            
            # Soft delete
            await mongo_db.outward_stock.update_one(
                {"id": outward_id},
                {"$set": {"is_active": False}}
            )
            
            # Revert stock tracking (add back the stock to summary)
            await revert_stock_tracking_outward(outward)
            
            deleted.append(outward_id)
            
            # Audit log
            await mongo_db.audit_logs.insert_one({
                "action": "outward_bulk_deleted",
                "user_id": current_user["id"],
                "entity_id": outward_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            failed.append({"id": outward_id, "reason": str(e)})
    
    return {
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "failed_count": len(failed),
        "failed": failed
    }

app.include_router(api_router)

# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Bora Mobility Inventory API"}

@app.on_event("startup")
async def startup_event():
    logger.info("Application started - using MongoDB")
    
    # Initialize indexes
    try:
        # Companies: Name is unique, GSTNumber is unique but optional (sparse)
        await mongo_db.companies.create_index("name", unique=True)
        await mongo_db.companies.create_index("GSTNumber", unique=True, sparse=True)
        
        # Products: SKU is unique
        await mongo_db.products.create_index("sku", unique=True)
        
        # Warehouses: Name is unique
        await mongo_db.warehouses.create_index("name", unique=True)
        
        logger.info("MongoDB indexes initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing MongoDB indexes: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")
