from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File
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

from database import mongo_db
from schemas import (
    UserLogin, CompanyCreate, CompanyUpdate,
    ProductCreate, ProductUpdate,
    WarehouseCreate, WarehouseUpdate,
    BankCreate, BankUpdate,
    DashboardStats,
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

api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    company_dict = {
        "id": str(uuid.uuid4()),
        **company_data.model_dump(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await mongo_db.companies.insert_one(company_dict)
    
    await mongo_db.audit_logs.insert_one({
        "action": "company_created",
        "user_id": current_user["id"],
        "entity_id": company_dict["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    company_dict.pop("_id", None)
    return company_dict



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
    pi_count = await mongo_db.performa_invoices.count_documents({"company_id": company_id, "is_active": True})
    
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
            pi_count = await mongo_db.performa_invoices.count_documents({"company_id": company_id, "is_active": True})
            
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

@api_router.post("/products/bulk")
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
    pi_count = await mongo_db.performa_invoices.count_documents({
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
            pi_count = await mongo_db.performa_invoices.count_documents({
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

# ==================== WAREHOUSE ROUTES ====================
@api_router.post("/warehouses")
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    current_user: dict = Depends(get_current_active_user)
):
    try:
        warehouse_dict = {
            "id": str(uuid.uuid4()),

            # Map to DB fields that have unique indexes
            "warehouseName": warehouse_data.name,
            "contactDetails": warehouse_data.contact_details,

            **warehouse_data.model_dump(),

            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        await mongo_db.warehouses.insert_one(warehouse_dict)
        warehouse_dict.pop("_id", None)

        return warehouse_dict

    except Exception as e:
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
    bank_dict = {
        "id": str(uuid.uuid4()),
        **bank_data.model_dump(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await mongo_db.banks.insert_one(bank_dict)
    bank_dict.pop("_id", None)
    return bank_dict

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

# ==================== PERFORMA INVOICE (PI) ROUTES ====================
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
    
    await mongo_db.performa_invoices.insert_one(pi_dict)
    
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
                await mongo_db.performa_invoices.insert_one(pi_dict)
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
    async for pi in mongo_db.performa_invoices.find({"is_active": True}, {"_id": 0}):
        # Calculate total amount
        total_amount = sum(item.get("amount", 0) for item in pi.get("line_items", []))
        pi["total_amount"] = total_amount
        pi["line_items_count"] = len(pi.get("line_items", []))
        # Keep line_items for display but only show minimal info in list
        pis.append(pi)
    return pis

@api_router.get("/pI/{pi_id}")
async def get_pi(pi_id: str, current_user: dict = Depends(get_current_active_user)):
    pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    # Get company details
    if pi.get("company_id"):
        company = await mongo_db.companies.find_one({"id": pi["company_id"]}, {"_id": 0})
        pi["company"] = company
    
    return pi

# async def get_dispatched_qty_for_pi(
#     pi_id: str,
#     line_item_id: str,  # Match by line item ID
#     warehouse_id: str
# ):
#     dispatched = 0.0

#     async for outward in mongo_db.outward_stock.find(
#         {
#             "pi_ids": pi_id,
#             "warehouse_id": warehouse_id,
#             "is_active": True
#         },
#         {"_id": 0}
#     ):
#         for item in outward.get("line_items", []):
#             if item.get("id") == line_item_id:  # Match by line item ID
#                 dispatched += float(item.get("quantity", 0))

#     return dispatched

# async def get_inward_qty_for_pi(
#     pi_id: str,
#     line_item_id: str,  # Match by line item ID
#     warehouse_id: str
# ):
#     inward = 0.0

#     async for inward_doc in mongo_db.inward_stock.find(
#         {
#             "pi_id": pi_id,
#             "warehouse_id": warehouse_id,
#             "is_active": True
#         },
#         {"_id": 0}
#     ):
#         for item in inward_doc.get("line_items", []):
#             if item.get("id") == line_item_id:  # Match by line item ID
#                 inward += float(item.get("quantity", 0))

#     return inward


# #i need to see this code carefully
# @api_router.get("/pi/{pi_id}")
# async def get_pi(
#     pi_id: str,
#     warehouse_id: str,  #REQUIRED
#     current_user: dict = Depends(get_current_active_user)
# ):
#     # Fetch the PI
#     pi = await mongo_db.performa_invoices.find_one(
#         {"id": pi_id},
#         {"_id": 0}
#     )
#     if not pi:
#         raise HTTPException(status_code=404, detail="PI not found")

#     # Company
#     if pi.get("company_id"):
#         company = await mongo_db.companies.find_one(
#             {"id": pi["company_id"]},
#             {"_id": 0}
#         )
#         pi["company"] = company

#     # Inward stock (optional, reference only)
#     inward_stocks = []
#     async for stock in mongo_db.inward_stock.find(
#         {"pi_id": pi_id, "warehouse_id": warehouse_id},
#         {"_id": 0}
#     ):
#         inward_stocks.append(stock)
#     pi["inward_stock"] = inward_stocks

#     # ✅ CORRECT CALCULATION
#     for item in pi.get("line_items", []):

#         line_item_id = item.get("id")

#         inward_qty = await get_inward_qty_for_pi(
#             pi_id=pi_id,
#             line_item_id=line_item_id,   #using item id the unique one
#             warehouse_id=warehouse_id
#         )

#         dispatched_qty = await get_dispatched_qty_for_pi(
#             pi_id=pi_id,
#              line_item_id=line_item_id,
#             warehouse_id=warehouse_id
#         )

#         item["pi_quantity"] = float(item.get("quantity", 0))
#         item["inward_quantity"] = inward_qty
#         item["dispatched_quantity"] = dispatched_qty
#         item["available_quantity"] = max(inward_qty - dispatched_qty, 0)

#     return pi


async def get_dispatched_qty_for_pi(
    pi_id: str,
    product_sku: str,  # ✅ Changed to SKU
    warehouse_id: str
):
    dispatched = 0.0

    async for outward in mongo_db.outward_stock.find(
        {
            "pi_ids": pi_id,
            "warehouse_id": warehouse_id,
            "is_active": True
        },
        {"_id": 0}
    ):
        for item in outward.get("line_items", []):
            if item.get("sku") == product_sku:  # ✅ Match by SKU
                dispatched += float(item.get("quantity", 0))

    return dispatched

async def get_inward_qty_for_pi(
    pi_id: str,
    product_sku: str,  # ✅ Changed to SKU
    warehouse_id: str
):
    inward = 0.0

    async for inward_doc in mongo_db.inward_stock.find(
        {
            "pi_id": pi_id,
            "warehouse_id": warehouse_id,
            "is_active": True
        },
        {"_id": 0}
    ):
        for item in inward_doc.get("line_items", []):
            if item.get("sku") == product_sku:  # ✅ Match by SKU
                inward += float(item.get("quantity", 0))

    return inward


# ✅ Update the endpoint
@api_router.get("/pi/{pi_id}")
async def get_pi(
    pi_id: str,
    warehouse_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    pi = await mongo_db.performa_invoices.find_one(
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

    inward_stocks = []
    async for stock in mongo_db.inward_stock.find(
        {"pi_id": pi_id, "warehouse_id": warehouse_id},
        {"_id": 0}
    ):
        inward_stocks.append(stock)
    pi["inward_stock"] = inward_stocks

    # ✅ Calculate quantities using SKU
    for item in pi.get("line_items", []):

        product_sku = item.get("sku")  # ✅ Get SKU

        inward_qty = await get_inward_qty_for_pi(
            pi_id=pi_id,
            product_sku=product_sku,  # ✅ Pass SKU
            warehouse_id=warehouse_id
        )

        dispatched_qty = await get_dispatched_qty_for_pi(
            pi_id=pi_id,
            product_sku=product_sku,  # ✅ Pass SKU
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
    pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
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
    
    await mongo_db.performa_invoices.update_one({"id": pi_id}, {"$set": update_data})
    
    updated_pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
    return updated_pi

@api_router.delete("/pi/{pi_id}")
async def delete_pi(pi_id: str, current_user: dict = Depends(get_current_active_user)):
    pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    await mongo_db.performa_invoices.update_one({"id": pi_id}, {"$set": {"is_active": False}})
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
        pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
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
            pi = await mongo_db.performa_invoices.find_one({"id": pi_id, "is_active": True}, {"_id": 0})
            if not pi:
                raise HTTPException(status_code=404, detail=f"Performa Invoice {pi_id} not found")
    
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
    return po_dict

@api_router.post("/po/bulk")
async def bulk_upload_pos(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    try:
        print("\n====== PO BULK UPLOAD STARTED ======")

        contents = await file.read()
        filename = file.filename.lower()

        print(f"File received: {filename}")
        print(f"File size: {len(contents)} bytes")

        # --- Read file correctly (CSV / XLS / XLSX) ---
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

        # Drop fully blank rows
        df = df.dropna(how="all")
        print("After dropping empty:", len(df))

        # Normalize column names
        df.columns = [str(c).strip().lower() for c in df.columns]
        print("Normalized columns:", df.columns.tolist())

        # 👇 Map template fields to backend field names
        if "input_igst" in df.columns and "gst_percentage" not in df.columns:
            df["gst_percentage"] = df["input_igst"]

        if "tds" in df.columns and "tds_percentage" not in df.columns:
            df["tds_percentage"] = df["tds"]


        if "voucher_no" not in df.columns:
            raise HTTPException(
                status_code=400,
                detail="Missing required column: voucher_no"
            )

        pos_created = 0
        print("Voucher numbers:", df["voucher_no"].unique())

        # --- Group by voucher_no ---
        for voucher_no in df["voucher_no"].unique():
            print(f"\n---- Processing PO voucher: {voucher_no} ----")

            po_rows = df[df["voucher_no"] == voucher_no]
            first_row = po_rows.iloc[0]

            # Handle multiple PI references
            reference_pi_ids = []
            if pd.notna(first_row.get("reference_pi_ids")):
                pi_ids_str = str(first_row.get("reference_pi_ids", "")).strip()
                if pi_ids_str:
                    reference_pi_ids = [pi_id.strip() for pi_id in pi_ids_str.split(",")]
            elif pd.notna(first_row.get("reference_pi_id")):
                reference_pi_ids = [str(first_row.get("reference_pi_id", "")).strip()]

            po_dict = {
                "id": str(uuid.uuid4()),
                "company_id": str(first_row.get("company_id", "")),
                "voucher_no": str(voucher_no),
                "date": str(first_row.get("date", datetime.now(timezone.utc).isoformat())),
                "consignee": str(first_row.get("consignee", "")),
                "supplier": str(first_row.get("supplier", "")),
                "reference_pi_id": reference_pi_ids[0] if reference_pi_ids else None,
                "reference_pi_ids": reference_pi_ids,
                "reference_no_date": (
                    str(first_row.get("reference_no_date"))
                    if pd.notna(first_row.get("reference_no_date"))
                    else None
                ),
                "dispatched_through": str(first_row.get("dispatched_through", "")),
                "destination": str(first_row.get("destination", "")),
                "gst_percentage": float(first_row.get("gst_percentage", 0) or 0),
                "tds_percentage": float(first_row.get("tds_percentage", 0) or 0),
                "status": "Pending",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user["id"],
                "line_items": []
            }

            print("PO Header:")
            print(po_dict)

            gst_percentage = po_dict["gst_percentage"]
            tds_percentage = po_dict["tds_percentage"]

            total_basic_amount = 0
            total_gst_value = 0
            total_tds_value = 0

            # --- Line items ---
            for _, row in po_rows.iterrows():
                quantity = float(row.get("quantity", 0) or 0)
                rate = float(row.get("rate", 0) or 0)
                amount = quantity * rate

                gst_value = amount * (gst_percentage / 100) if gst_percentage else 0
                tds_value = amount * (tds_percentage / 100) if tds_percentage else 0

                line_item = {
                    "id": str(uuid.uuid4()),
                    "product_id": str(row.get("product_id", "")),
                    "product_name": str(row.get("product_name", "")),
                    "sku": str(row.get("sku", "")),
                    "category": str(row.get("category", "")),
                    "brand": str(row.get("brand", "")),
                    "hsn_sac": str(row.get("hsn_sac", "")),
                    "quantity": quantity,
                    "rate": rate,
                    "amount": amount,
                    "gst_value": round(gst_value, 2),
                    "tds_value": round(tds_value, 2)
                }

                print(" ➜ Adding line:", line_item)

                po_dict["line_items"].append(line_item)

                total_basic_amount += amount
                total_gst_value += gst_value
                total_tds_value += tds_value

            # Totals
            po_dict["total_basic_amount"] = round(total_basic_amount, 2)
            po_dict["total_gst_value"] = round(total_gst_value, 2)
            po_dict["total_tds_value"] = round(total_tds_value, 2)
            po_dict["total_amount"] = round(total_basic_amount + total_gst_value - total_tds_value, 2)

            print("PO Total Summary:")
            print({
                "basic": po_dict["total_basic_amount"],
                "gst": po_dict["total_gst_value"],
                "tds": po_dict["total_tds_value"],
                "total": po_dict["total_amount"]
            })

            # Insert
            try:
                print(f"📥 Inserting PO voucher {voucher_no}")
                await mongo_db.purchase_orders.insert_one(po_dict)
                pos_created += 1
                print(f"✅ Inserted PO #{pos_created}")
            except Exception as e:
                print(f"🔥 Error inserting PO {voucher_no}: {e}")
                continue

        print("\n====== PO BULK UPLOAD FINISHED ======")
        print("Total created:", pos_created)

        return {
            "message": f"Successfully uploaded {pos_created} POs",
            "count": pos_created
        }

    except Exception as e:
        print("🔥 FATAL ERROR:", e)
        raise HTTPException(
            status_code=400,
            detail=f"Error processing file: {str(e)}"
        )

@api_router.get("/po")
@api_router.get("/purchase-orders")  # Alias for frontend compatibility
async def get_pos(current_user: dict = Depends(get_current_active_user)):
    """Get all active Purchase Orders (accessible via /po or /purchase-orders)"""
    logger.info(f"Fetching POs for user: {current_user.get('username')}")
    pos = []
    try:
        async for po in mongo_db.purchase_orders.find({"is_active": True}, {"_id": 0}):
            # Calculate total amount
            total_amount = sum(item.get("amount", 0) for item in po.get("line_items", []))
            po["total_amount"] = total_amount
            po["line_items_count"] = len(po.get("line_items", []))
            pos.append(po)
        logger.info(f"Returning {len(pos)} purchase orders")
        return pos
    except Exception as e:
        logger.error(f"Error fetching POs: {str(e)}")
        # Return empty array instead of raising error
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
            pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
            if pi:
                pi_details.append(pi)
        
        po["reference_pis"] = pi_details  # Multiple PIs
        if pi_details:
            po["reference_pi"] = pi_details[0]  # For backward compatibility
    
    return po

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
            pi = await mongo_db.performa_invoices.find_one({"id": pi_id, "is_active": True}, {"_id": 0})
            if not pi:
                raise HTTPException(status_code=404, detail=f"Performa Invoice {pi_id} not found")
    
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
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    # Update line items
    if "line_items" in po_data:
        line_items = []
        for item in po_data["line_items"]:
            line_item = {
                "id": item.get("id", str(uuid.uuid4())),
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "sku": item.get("sku"),
                "category": item.get("category"),
                "brand": item.get("brand"),
                "hsn_sac": item.get("hsn_sac"),
                "quantity": float(item.get("quantity", 0)),
                "rate": float(item.get("rate", 0)),
                "amount": float(item.get("quantity", 0)) * float(item.get("rate", 0)),
                "input_igst": float(item.get("input_igst", 0)),
                "tds": float(item.get("tds", 0))
            }
            line_items.append(line_item)
        update_data["line_items"] = line_items
    
    await mongo_db.purchase_orders.update_one({"id": po_id}, {"$set": update_data})
    
    updated_po = await mongo_db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
    return updated_po

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
            po_line_item_id = inward_item.get("id")
            product_id = inward_item.get("product_id")
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
                            if existing_item.get("id") == po_line_item_id:
                                already_inwarded += float(existing_item.get("quantity", 0))

                total_inward_after_this = already_inwarded + inward_qty

                if total_inward_after_this > total_po_qty:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot inward {product_id}: total inward ({total_inward_after_this}) exceeds PO qty ({total_po_qty}). Already inwarded: {already_inwarded}"
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
        # Get company details if PO is linked
        if entry.get("po_id"):
            po = await mongo_db.purchase_orders.find_one({"id": entry["po_id"]}, {"_id": 0})
            if po and po.get("company_id"):
                company = await mongo_db.companies.find_one({"id": po["company_id"]}, {"_id": 0})
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
                    pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
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
                pi = await mongo_db.performa_invoices.find_one({"id": pid}, {"_id": 0, "voucher_no": 1})
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
    Returns: Product | SKU | Color | PI & PO Number | Category | Warehouse | Company | Inward | Outward | Remaining | Status | Age | Actions
    entry_type: 'regular' for Stock Entries (Warehouse Inward + Export Invoice)
                'direct' for Direct Stock Entries (Direct Inward + Direct Outward)
    """
    query = {}
    
    # Apply filters
    if warehouse_id:
        query["warehouse_id"] = warehouse_id
    if company_id:
        query["company_id"] = company_id
    if pi_number:
        query["pi_number"] = {"$regex": pi_number, "$options": "i"}
    if po_number:
        query["po_number"] = {"$regex": po_number, "$options": "i"}
    if sku:
        query["sku"] = {"$regex": sku, "$options": "i"}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}
    if entry_type:
        query["entry_type"] = entry_type  # NEW: Filter by entry type
    
    stock_entries = []
    async for stock in mongo_db.stock_tracking.find(query, {"_id": 0}):
        # Calculate stock age (days since last update)
        last_updated_str = stock.get("last_updated", stock.get("created_at"))
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
            stock_age_days = (datetime.now(timezone.utc) - last_updated).days
        except:
            stock_age_days = 0
        
        # Determine stock status based on remaining_stock
        remaining = stock.get("remaining_stock", 0)
        if remaining < 10:
            stock_status = "Low Stock"
        else:
            stock_status = "Normal"
        
        # Format PI & PO Number combined
        pi_po_combined = f"{stock.get('pi_number', 'N/A')} / {stock.get('po_number', 'N/A')}"
        
        # Calculate In-Transit quantity for this SKU from pickup_in_transit collection
        in_transit_qty = 0
        async for pickup in mongo_db.pickup_in_transit.find({"is_active": True}, {"_id": 0}):
            for pickup_item in pickup.get("line_items", []):
                if pickup_item.get("sku") == stock.get("sku"):
                    in_transit_qty += float(pickup_item.get("quantity", 0))
        
        stock_summary = {
            "id": stock.get("id"),  # For actions
            "product_id": stock.get("product_id"),
            "product_name": stock.get("product_name"),
            "sku": stock.get("sku"),
            "color": stock.get("color", "N/A"),  # NEW: Add color
            "pi_po_number": pi_po_combined,  # Combined column
            "pi_number": stock.get("pi_number", "N/A"),  # Individual for filtering
            "po_number": stock.get("po_number", "N/A"),  # Individual for filtering
            "category": stock.get("category", "Unknown"),
            "warehouse_id": stock.get("warehouse_id"),
            "warehouse_name": stock.get("warehouse_name", "Unknown"),
            "company_id": stock.get("company_id"),
            "company_name": stock.get("company_name", "Unknown"),
            "in_transit": in_transit_qty,  # NEW: In-transit quantity
            "quantity_inward": stock.get("quantity_inward", 0),
            "quantity_outward": stock.get("quantity_outward", 0),
            "remaining_stock": remaining,
            "status": stock_status,
            "age_days": stock_age_days,
            "last_updated": last_updated_str
        }
        
        stock_entries.append(stock_summary)
    
    # Sort by remaining stock (lowest first - for low stock visibility)
    stock_entries.sort(key=lambda x: x["remaining_stock"])
    
    return stock_entries

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
    
    # Get Export Invoice transactions (dispatch_type = "export_invoice")
    async for outward in mongo_db.outward_stock.find(
        {**warehouse_query, "dispatch_type": "export_invoice", "is_active": True},
        {"_id": 0}
    ).sort("date", -1):
        for item in outward.get("line_items", []):
            if item.get("product_id") == product_id:
                transactions.append({
                    "type": "outward",
                    "transaction_id": outward["id"],
                    "date": outward["date"],
                    "reference_no": outward.get("export_invoice_no", "N/A"),
                    "dispatch_type": "Export Invoice",
                    "quantity": item.get("dispatch_quantity") or item.get("quantity", 0),
                    "rate": item.get("rate", 0),
                    "amount": item.get("amount", 0),
                    "product_name": item.get("product_name"),
                    "sku": item.get("sku"),
                    "created_at": outward.get("created_at")
                })
    
    # Get Direct Export transactions (dispatch_type = "direct_export")
    async for outward in mongo_db.outward_stock.find(
        {**warehouse_query, "dispatch_type": "direct_export", "is_active": True},
        {"_id": 0}
    ).sort("date", -1):
        for item in outward.get("line_items", []):
            if item.get("product_id") == product_id:
                transactions.append({
                    "type": "outward",
                    "transaction_id": outward["id"],
                    "date": outward["date"],
                    "reference_no": outward.get("export_invoice_no", "N/A"),
                    "dispatch_type": "Direct Export",
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
    
    # Log incoming data for debugging
    print(f"\n{'='*80}")
    print(f"📥 CREATE OUTWARD STOCK REQUEST")
    print(f"{'='*80}")
    print(f"Dispatch Type: {outward_data.get('dispatch_type')}")
    print(f"Company ID: {outward_data.get('company_id')}")
    print(f"Warehouse ID: {outward_data.get('warehouse_id')}")
    print(f"Line Items Count: {len(outward_data.get('line_items', []))}")
    print(f"{'='*80}\n")
    
    # Validate company
    company = await mongo_db.companies.find_one({"id": outward_data["company_id"]}, {"_id": 0})
    if not company:
        print(f"❌ ERROR: Company not found - {outward_data['company_id']}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Validate PI(s) if provided - support both single pi_id and multiple pi_ids
    pi_data = None
    pi_ids_list = []
    
    # Check for multiple PIs (new format)
    if outward_data.get("pi_ids") and isinstance(outward_data["pi_ids"], list):
        pi_ids_list = outward_data["pi_ids"]
        # Validate all PIs exist
        for pi_id in pi_ids_list:
            pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
            if not pi:
                raise HTTPException(status_code=404, detail=f"PI {pi_id} not found")
        # Get first PI for backward compatibility
        if pi_ids_list:
            pi_data = await mongo_db.performa_invoices.find_one({"id": pi_ids_list[0]}, {"_id": 0})
    # Fallback to single pi_id (old format)
    elif outward_data.get("pi_id"):
        pi_ids_list = [outward_data["pi_id"]]
        pi_data = await mongo_db.performa_invoices.find_one({"id": outward_data["pi_id"]}, {"_id": 0})
        if not pi_data:
            raise HTTPException(status_code=404, detail="PI not found")
    
    # Validate warehouse
    warehouse = await mongo_db.warehouses.find_one({"id": outward_data["warehouse_id"]}, {"_id": 0})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Create outward entry
    outward_dict = {
        "id": str(uuid.uuid4()),
        "export_invoice_no": outward_data.get("export_invoice_no") or f"EXP-{str(uuid.uuid4())[:8].upper()}",
        "export_invoice_number": outward_data.get("export_invoice_number", ""),  # NEW: Manually typed export invoice number
        "date": outward_data.get("date"),
        "company_id": outward_data["company_id"],
        "pi_id": pi_ids_list[0] if pi_ids_list else None,  # Store first PI for backward compatibility
        "pi_ids": pi_ids_list,  # Store all PIs
        "warehouse_id": outward_data["warehouse_id"],
        "mode": outward_data.get("mode"),  # Sea, Air
        "containers_pallets": outward_data.get("containers_pallets"),  # Number of containers (Sea) or pallets (Air)
        "dispatch_type": outward_data.get("dispatch_type"),  # dispatch_plan, export_invoice, direct_export
        "dispatch_plan_id": outward_data.get("dispatch_plan_id"),  # Link to Dispatch Plan if Export Invoice
        "status": outward_data.get("status", "Pending Dispatch"),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
        "line_items": []
    }
    
    # Process line items and validate stock availability
    total_amount = 0
    for item in outward_data.get("line_items", []):
        # Support both quantity and dispatch_quantity fields
        qty = item.get("dispatch_quantity") or item.get("quantity", 0)
        
        # Check available stock for Dispatch Plans and Export Invoices (not from Dispatch Plan)
        # Export Invoices created FROM Dispatch Plans don't need stock validation (already validated)
        # Direct Exports also don't need stock validation (they're from Direct Inward)
        should_validate_stock = (
            outward_data.get("dispatch_type") == "dispatch_plan" or
            (outward_data.get("dispatch_type") == "export_invoice" and not outward_data.get("dispatch_plan_id"))
        )
        
        if should_validate_stock:
            print(f"  📦 Validating stock for {item['product_name']} - Qty: {qty}")
            
            # Calculate available stock using inward-outward calculation (same as available-quantity endpoint)
            total_inward = 0.0
            inward_query = {"is_active": True, "warehouse_id": outward_data["warehouse_id"]}
            async for inward in mongo_db.inward_stock.find(inward_query, {"_id": 0}):
                for inward_item in inward.get("line_items", []):
                    if inward_item.get("product_id") == item["product_id"]:
                        total_inward += float(inward_item.get("quantity", 0))
            
            total_outward = 0.0
            outward_query = {"is_active": True, "warehouse_id": outward_data["warehouse_id"]}
            async for outward in mongo_db.outward_stock.find(outward_query, {"_id": 0}):
                for outward_item in outward.get("line_items", []):
                    if outward_item.get("product_id") == item["product_id"]:
                        total_outward += float(outward_item.get("quantity", 0))
            
            available_stock = total_inward - total_outward
            print(f"  📊 Stock check: Inward={total_inward}, Outward={total_outward}, Available={available_stock}")
            
            # BLOCK if quantity exceeds available stock
            if qty > available_stock:
                print(f"  ❌ Insufficient stock!")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot dispatch {item['product_name']}: Requested quantity ({qty}) exceeds available stock ({available_stock})"
                )
            print(f"  ✅ Stock validation passed")
        else:
            print(f"  ⏭️  Skipping stock validation for {outward_data.get('dispatch_type')}")
        
        line_item = {
            "id": str(uuid.uuid4()),
            "product_id": item.get("product_id"),
            "product_name": item.get("product_name"),
            "sku": item.get("sku"),
            "pi_total_quantity": float(item.get("pi_total_quantity", 0)),  # Add this field
            "quantity": float(qty),  # Store as quantity in DB
            "dispatch_quantity": float(qty),  # Also store as dispatch_quantity
            "rate": float(item.get("rate", 0)),
            "amount": float(qty) * float(item.get("rate", 0)),
            "dimensions": item.get("dimensions"),
            "weight": float(item.get("weight", 0)) if item.get("weight") else None
        }
        total_amount += line_item["amount"]
        outward_dict["line_items"].append(line_item)
    
    outward_dict["total_amount"] = total_amount
    outward_dict["line_items_count"] = len(outward_dict["line_items"])
    
    # Insert outward entry
    await mongo_db.outward_stock.insert_one(outward_dict)
    
    # Update central stock tracking for Export Invoice AND Direct Export
    # Dispatch Plans are NOT included (they're planning only)
    if outward_data.get("dispatch_type") in ["export_invoice", "direct_export"]:
        await update_stock_tracking_outward(outward_dict)
        dispatch_type_label = "Direct Export" if outward_data.get("dispatch_type") == "direct_export" else "Export Invoice"
        print(f"  ✅ Stock Summary updated ({dispatch_type_label}): Reduced {sum(item.get('quantity', 0) for item in outward_dict.get('line_items', []))} units")
    else:
        print(f"  ℹ️  Dispatch Plan created - Stock Summary NOT updated (planning only)")
    
    await mongo_db.audit_logs.insert_one({
        "action": "outward_stock_created",
        "user_id": current_user["id"],
        "entity_id": outward_dict["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    outward_dict.pop("_id", None)
    return outward_dict

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
            
        # Get PI details if linked
        if entry.get("pi_id"):
            pi = await mongo_db.performa_invoices.find_one({"id": entry["pi_id"]}, {"_id": 0})
            entry["pi"] = pi
            
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
                    pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
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
    
    # Calculate total inward quantity
    total_inward = 0.0
    inward_query = {"is_active": True}
    if warehouse_id:
        inward_query["warehouse_id"] = warehouse_id
    
    async for inward in mongo_db.inward_stock.find(inward_query, {"_id": 0}):
        for item in inward.get("line_items", []):
            if item.get("product_id") == product_id:
                total_inward += float(item.get("quantity", 0))
    
    # Calculate total outward quantity
    total_outward = 0.0
    outward_query = {"is_active": True}
    if warehouse_id:
        outward_query["warehouse_id"] = warehouse_id
    
    async for outward in mongo_db.outward_stock.find(outward_query, {"_id": 0}):
        for item in outward.get("line_items", []):
            if item.get("product_id") == product_id:
                total_outward += float(item.get("quantity", 0))
    
    # Available = Inward - Outward
    available_quantity = total_inward - total_outward
    
    return {
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "total_inward": total_inward,
        "total_outward": total_outward,
        "available_quantity": max(0, available_quantity)  # Ensure non-negative
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
        
    if entry.get("pi_id"):
        pi = await mongo_db.performa_invoices.find_one({"id": entry["pi_id"]}, {"_id": 0})
        entry["pi"] = pi
    
    return entry

@api_router.put("/outward-stock/{outward_id}")
async def update_outward_stock(
    outward_id: str,
    outward_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Update outward stock entry"""
    entry = await mongo_db.outward_stock.find_one({"id": outward_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Outward entry not found")
    
    update_data = {
        "export_invoice_no": outward_data.get("export_invoice_no"),
        "export_invoice_number": outward_data.get("export_invoice_number", entry.get("export_invoice_number", "")),
        "date": outward_data.get("date"),
        "company_id": outward_data.get("company_id"),
        "warehouse_id": outward_data.get("warehouse_id"),
        "mode": outward_data.get("mode"),
        "status": outward_data.get("status", entry.get("status")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    # Update line items if provided
    if "line_items" in outward_data:
        line_items = []
        total_amount = 0
        for item in outward_data["line_items"]:
            line_item = {
                "id": item.get("id", str(uuid.uuid4())),
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "sku": item.get("sku"),
                "quantity": float(item.get("quantity", 0)),
                "rate": float(item.get("rate", 0)),
                "amount": float(item.get("quantity", 0)) * float(item.get("rate", 0)),
                "dimensions": item.get("dimensions"),
                "weight": float(item.get("weight", 0)) if item.get("weight") else None
            }
            total_amount += line_item["amount"]
            line_items.append(line_item)
        
        update_data["line_items"] = line_items
        update_data["total_amount"] = total_amount
        update_data["line_items_count"] = len(line_items)
    
    await mongo_db.outward_stock.update_one({"id": outward_id}, {"$set": update_data})
    
    updated_entry = await mongo_db.outward_stock.find_one({"id": outward_id}, {"_id": 0})
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
    
    await mongo_db.outward_stock.update_one({"id": outward_id}, {"$set": {"is_active": False}})
    return {"message": "Outward entry deleted successfully"}


# Helper functions for outward operations
async def get_available_stock(product_id: str, warehouse_id: str) -> float:
    """Get available stock for a product in a specific warehouse"""
    stock_entry = await mongo_db.stock_tracking.find_one({
        "product_id": product_id,
        "warehouse_id": warehouse_id
    }, {"_id": 0})
    
    return stock_entry["current_stock"] if stock_entry else 0.0

async def update_stock_tracking_outward(outward_entry: dict):
    """
    STOCK SUMMARY - Transaction-Based Outward Tracking
    Links outward to specific inward entries using FIFO (First In First Out)
    Reduces quantity from oldest inward entries first
    """
    try:
        print(f"  🔄 Updating stock tracking for outward: {outward_entry.get('export_invoice_no')}")
        
        for item in outward_entry.get("line_items", []):
            try:
                # Support both quantity and dispatch_quantity fields
                qty_to_dispatch = item.get("dispatch_quantity") or item.get("quantity", 0)
                
                print(f"     - Processing: {item.get('product_name')} (Dispatch Qty: {qty_to_dispatch})")
                
                # Find all stock_tracking entries for this product in this warehouse with remaining stock
                # Sort by created_at (FIFO - oldest first)
                stock_entries = []
                async for stock in mongo_db.stock_tracking.find({
                    "product_id": item["product_id"],
                    "warehouse_id": outward_entry.get("warehouse_id"),
                    "remaining_stock": {"$gt": 0}  # Only entries with stock remaining
                }, {"_id": 0}).sort("created_at", 1):  # FIFO: oldest first
                    stock_entries.append(stock)
                
                if not stock_entries:
                    print(f"       ⚠️  No stock available for {item.get('product_name')} in warehouse {outward_entry.get('warehouse_id')}")
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
                    
                    print(f"       ✅ Updated entry (Invoice: {stock.get('inward_invoice_no')}): Outward {old_outward} → {new_outward}, Remaining: {new_remaining}")
                    
                    remaining_to_dispatch -= qty_from_this_entry
                
                if remaining_to_dispatch > 0:
                    print(f"       ⚠️  Insufficient stock! Could not dispatch {remaining_to_dispatch} units of {item.get('product_name')}")
                    
            except Exception as item_error:
                print(f"       ❌ Error processing item {item.get('product_name')}: {str(item_error)}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"  ✅ Outward stock tracking update completed (FIFO)")
    except Exception as e:
        print(f"  ❌ CRITICAL ERROR in update_stock_tracking_outward: {str(e)}")
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
            pi = await mongo_db.performa_invoices.find_one({"id": payment["pi_id"]}, {"_id": 0})
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
        pi = await mongo_db.performa_invoices.find_one({"id": payment["pi_id"]}, {"_id": 0})
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
    pi = await mongo_db.performa_invoices.find_one({"id": payment_data["pi_id"]}, {"_id": 0})
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
    pi = await mongo_db.performa_invoices.find_one({"id": pi_id}, {"_id": 0})
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
    pi_number: str,
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
    pi_number: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new extra payment for a PI"""
    # Validate required fields
    if not payment_data.get("date"):
        raise HTTPException(status_code=400, detail="Date is required")
    if not payment_data.get("bank_id"):
        raise HTTPException(status_code=400, detail="Bank is required")
    if not payment_data.get("amount") or payment_data.get("amount") <= 0:
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
        "amount": float(payment_data["amount"]),
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await mongo_db.pi_extra_payments.insert_one(extra_payment)
    
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


@api_router.put("/extra-payments/{extra_payment_id}")
async def update_extra_payment(
    extra_payment_id: str,
    payment_data: dict,
    pi_number: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Update an existing extra payment"""
    # Validate required fields
    if "date" in payment_data and not payment_data["date"]:
        raise HTTPException(status_code=400, detail="Date is required")
    if "bank_id" in payment_data and not payment_data["bank_id"]:
        raise HTTPException(status_code=400, detail="Bank is required")
    if "amount" in payment_data and (not payment_data["amount"] or payment_data["amount"] <= 0):
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    # Check if extra payment exists
    existing = await mongo_db.pi_extra_payments.find_one({
        "id": extra_payment_id,
        "pi_number": pi_number,
        "is_active": True
    })
    
    if not existing:
        raise HTTPException(status_code=404, detail="Extra payment not found")
    
    # Verify bank if being updated
    if payment_data.get("bank_id"):
        bank = await mongo_db.banks.find_one({"id": payment_data["bank_id"], "is_active": True})
        if not bank:
            raise HTTPException(status_code=404, detail="Bank not found")
        payment_data["bank_name"] = bank.get("bank_name", "")
    
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
        update_data["bank_name"] = payment_data["bank_name"]
    if "amount" in payment_data:
        update_data["amount"] = float(payment_data["amount"])
    
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


@api_router.delete("/extra-payments/{extra_payment_id}")
async def delete_extra_payment(
    extra_payment_id: str,
    pi_number: str,
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
    # Find payment record for this PI
    payment = await mongo_db.payments.find_one({
        "pi_voucher_no": pi_number,
        "is_active": True
    })
    
    if not payment:
        return
    
    # Calculate total extra payments
    total_extra = 0
    async for extra_payment in mongo_db.pi_extra_payments.find({
        "pi_number": pi_number,
        "is_active": True
    }):
        total_extra += extra_payment.get("amount", 0)
    
    # Calculate received amount from payment entries
    payment_entries_total = sum(e.get("received_amount", 0) for e in payment.get("payment_entries", []))
    
    # Update payment record
    advance_payment = payment.get("advance_payment", 0)
    total_amount = payment.get("total_amount", 0)
    
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
    """Calculate P&L for selected export invoices with detailed breakdown"""
    export_invoice_ids = request_data.get("export_invoice_ids", [])
    from_date = request_data.get("from_date")
    to_date = request_data.get("to_date")
    company_id = request_data.get("company_id")
    sku_filter = request_data.get("sku")
    
    if not export_invoice_ids:
        raise HTTPException(status_code=400, detail="No export invoices selected")
    
    # Initialize totals
    total_export_value = 0
    total_purchase_cost = 0
    total_expenses = 0
    item_breakdown = []
    export_invoice_details = []
    
    # Process each export invoice
    for inv_id in export_invoice_ids:
        outward = await mongo_db.outward_stock.find_one({"id": inv_id, "is_active": True}, {"_id": 0})
        if not outward:
            continue
        
        # Apply filters
        if from_date and outward.get("date") < from_date:
            continue
        if to_date and outward.get("date") > to_date:
            continue
        if company_id and outward.get("company_id") != company_id:
            continue
        
        invoice_export_value = 0
        invoice_purchase_cost = 0
        invoice_items = []
        
        # Process line items
        for item in outward.get("line_items", []):
            # Apply SKU filter
            if sku_filter and sku_filter.lower() not in item.get("sku", "").lower():
                continue
            
            # Calculate export value
            export_qty = item.get("quantity", 0)
            export_rate = item.get("rate", 0)
            export_value = export_qty * export_rate
            
            # Find purchase cost via PI reference (Option A)
            purchase_cost = 0
            pi_ids = outward.get("pi_ids", []) or ([outward.get("pi_id")] if outward.get("pi_id") else [])
            
            for pi_id in pi_ids:
                # Get PO linked to this PI
                po = await mongo_db.purchase_orders.find_one({"reference_pi_id": pi_id, "is_active": True}, {"_id": 0})
                if po:
                    # Find matching SKU in PO line items
                    for po_item in po.get("line_items", []):
                        if po_item.get("sku") == item.get("sku"):
                            purchase_cost += po_item.get("quantity", 0) * po_item.get("rate", 0)
            
            # If no PI reference, try direct SKU matching in all POs (Option B)
            if purchase_cost == 0:
                async for po in mongo_db.purchase_orders.find({"is_active": True}, {"_id": 0}):
                    for po_item in po.get("line_items", []):
                        if po_item.get("sku") == item.get("sku"):
                            purchase_cost += po_item.get("quantity", 0) * po_item.get("rate", 0)
                            break
            
            invoice_export_value += export_value
            invoice_purchase_cost += purchase_cost
            
            # Store item breakdown
            item_data = {
                "sku": item.get("sku"),
                "product_name": item.get("product_name"),
                "export_qty": export_qty,
                "export_rate": export_rate,
                "export_value": export_value,
                "purchase_cost": purchase_cost,
                "item_gross": export_value - purchase_cost
            }
            invoice_items.append(item_data)
            item_breakdown.append({
                **item_data,
                "export_invoice_no": outward.get("export_invoice_no")
            })
        
        total_export_value += invoice_export_value
        total_purchase_cost += invoice_purchase_cost
        
        export_invoice_details.append({
            "id": inv_id,
            "export_invoice_no": outward.get("export_invoice_no"),
            "date": outward.get("date"),
            "export_value": invoice_export_value,
            "purchase_cost": invoice_purchase_cost,
            "items": invoice_items
        })
    
    # Get expenses for these export invoices
    async for expense in mongo_db.expenses.find({"is_active": True}, {"_id": 0}):
        # Check if any of our export invoices are in this expense
        expense_invoice_ids = expense.get("export_invoice_ids", [])
        if any(inv_id in expense_invoice_ids for inv_id in export_invoice_ids):
            total_expenses += expense.get("total_expense", 0)
    
    # Calculate P&L
    gross_total = total_export_value - total_purchase_cost - total_expenses
    gst_amount = gross_total * 0.18
    net_profit = gross_total - gst_amount
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
    Returns aggregated data showing PIs with linked POs and SKU-level details.
    """
    # Validate page size
    if page_size > 200:
        page_size = 200
    if page_size < 1:
        page_size = 50
    
    skip = (page - 1) * page_size
    
    # Build PI query
    pi_query = {"is_active": True}
    
    # Apply filters
    if pi_number:
        pi_query["voucher_no"] = {"$regex": pi_number, "$options": "i"}
    
    if consignee:
        pi_query["consignee"] = {"$regex": consignee, "$options": "i"}
    
    if from_date:
        pi_query["date"] = {"$gte": from_date}
    
    if to_date:
        if "date" in pi_query:
            pi_query["date"]["$lte"] = to_date
        else:
            pi_query["date"] = {"$lte": to_date}
    
    # Search across multiple fields
    if search:
        pi_query["$or"] = [
            {"voucher_no": {"$regex": search, "$options": "i"}},
            {"consignee": {"$regex": search, "$options": "i"}},
            {"line_items.sku": {"$regex": search, "$options": "i"}},
            {"line_items.product_name": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count for pagination
    total_count = await mongo_db.performa_invoices.count_documents(pi_query)
    
    # Fetch PIs with pagination
    mappings = []
    cursor = mongo_db.performa_invoices.find(pi_query, {"_id": 0}).sort("date", -1).skip(skip).limit(page_size)
    
    async for pi in cursor:
        pi_id = pi.get("id")
        pi_number_val = pi.get("voucher_no")
        consignee_val = pi.get("consignee", "")
        
        # Calculate PI total quantity
        pi_total_quantity = sum(item.get("quantity", 0) for item in pi.get("line_items", []))
        
        # Build PI items list
        pi_items = []
        for item in pi.get("line_items", []):
            pi_items.append({
                "sku": item.get("sku", ""),
                "product_name": item.get("product_name", ""),
                "pi_quantity": item.get("quantity", 0),
                "pi_rate": item.get("rate", 0)
            })
        
        # Find linked POs
        po_query = {
            "$or": [
                {"reference_pi_id": pi_id},
                {"reference_pi_ids": pi_id}
            ],
            "is_active": True
        }
        
        # Apply PO number filter if provided
        if po_number:
            po_query["voucher_no"] = {"$regex": po_number, "$options": "i"}
        
        linked_pos = []
        po_cursor = mongo_db.purchase_orders.find(po_query, {"_id": 0}).sort("date", 1)
        
        async for po in po_cursor:
            po_items = []
            
            for po_item in po.get("line_items", []):
                po_sku = po_item.get("sku", "")
                
                # Find matching PI item for this SKU
                pi_item = next((item for item in pi_items if item["sku"] == po_sku), None)
                
                if pi_item:
                    po_quantity = po_item.get("quantity", 0)
                    pi_quantity = pi_item["pi_quantity"]
                    
                    # Calculate remaining for this PO item (other POs might also have quantities)
                    # For now, simple calculation per PO
                    remaining = pi_quantity - po_quantity
                    
                    po_items.append({
                        "sku": po_sku,
                        "product_name": po_item.get("product_name", ""),
                        "po_quantity": po_quantity,
                        "po_rate": po_item.get("rate", 0),
                        "pi_quantity": pi_quantity,
                        "pi_rate": pi_item["pi_rate"],
                        "remaining_quantity": remaining
                    })
            
            if po_items:  # Only include POs that have matching items
                linked_pos.append({
                    "po_number": po.get("voucher_no"),
                    "po_date": po.get("date"),
                    "po_id": po.get("id"),
                    "items": po_items
                })
        
        # Apply SKU filter if provided (filter at mapping level)
        if sku:
            # Check if any PI item or linked PO item matches the SKU
            has_sku = any(item["sku"].lower().find(sku.lower()) >= 0 for item in pi_items)
            if not has_sku and linked_pos:
                has_sku = any(
                    any(item["sku"].lower().find(sku.lower()) >= 0 for item in po["items"])
                    for po in linked_pos
                )
            if not has_sku:
                continue
        
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
    pi = await mongo_db.performa_invoices.find_one({"id": mapping_id, "is_active": True}, {"_id": 0})
    
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
    notes: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update PI to PO mapping metadata (notes, status).
    This endpoint allows updating mapping-related metadata without modifying core PI/PO data.
    """
    # Verify PI exists
    pi = await mongo_db.performa_invoices.find_one({"id": mapping_id, "is_active": True})
    
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    # Update metadata (can be stored in a separate mapping_metadata collection if needed)
    # For now, we'll add fields to the PI document
    update_data = {}
    
    if notes is not None:
        update_data["mapping_notes"] = notes
    
    if status is not None:
        update_data["mapping_status"] = status
    
    if update_data:
        await mongo_db.performa_invoices.update_one(
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
    pi = await mongo_db.performa_invoices.find_one({"id": mapping_id, "is_active": True})
    
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    # Soft delete by setting is_active to False
    await mongo_db.performa_invoices.update_one(
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
    
    async for pi in mongo_db.performa_invoices.find(pi_query, {"_id": 0}):
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
    ONLY counts Export Invoice (dispatch_type="export_invoice")
    Does NOT count Dispatch Plans
    """
    outward_data = []
    
    # Build PI query
    pi_query = {"is_active": True}
    if pi_number:
        pi_query["voucher_no"] = {"$regex": pi_number, "$options": "i"}
    if consignee:
        pi_query["consignee"] = {"$regex": consignee, "$options": "i"}
    
    async for pi in mongo_db.performa_invoices.find(pi_query, {"_id": 0}):
        # Get outward entries linked to this PI - ONLY Export Invoice
        # Use $or to avoid duplicate counting
        outward_query = {
            "$or": [
                {"pi_id": pi["id"]},
                {"pi_ids": pi["id"]}
            ],
            "dispatch_type": "export_invoice",  # ONLY export_invoice
            "is_active": True
        }
        
        # Calculate quantities per SKU
        pi_sku_quantities = {}
        for item in pi.get("line_items", []):
            sku_key = item.get("sku")
            if not sku or sku.lower() in sku_key.lower():
                pi_sku_quantities[sku_key] = {
                    "product_name": item.get("product_name"),
                    "pi_quantity": item.get("quantity", 0),
                    "outward_quantity": 0,
                    "remaining_quantity": item.get("quantity", 0)
                }
        
        # Calculate outwarded quantities - SINGLE query (no duplication)
        async for outward in mongo_db.outward_stock.find(outward_query, {"_id": 0}):
            for item in outward.get("line_items", []):
                sku_key = item.get("sku")
                if sku_key in pi_sku_quantities:
                    # Use dispatch_quantity (the actual outwarded quantity)
                    qty = item.get("dispatch_quantity") or item.get("quantity", 0)
                    pi_sku_quantities[sku_key]["outward_quantity"] += qty
                    pi_sku_quantities[sku_key]["remaining_quantity"] = (
                        pi_sku_quantities[sku_key]["pi_quantity"] - 
                        pi_sku_quantities[sku_key]["outward_quantity"]
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
                    "sku": sku,
                    "product_name": data["product_name"],
                    "pi_quantity": data["pi_quantity"],
                    "outward_quantity": data["outward_quantity"],
                    "remaining_quantity": data["remaining_quantity"]
                }
                for sku, data in pi_sku_quantities.items()
            ],
            "status": calc_status
        })
    
    return outward_data

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_active_user)):
    total_companies = await mongo_db.companies.count_documents({"is_active": True})
    total_warehouses = await mongo_db.warehouses.count_documents({"is_active": True})
    total_products = await mongo_db.products.count_documents({"is_active": True})
    
    return {
        "total_companies": total_companies,
        "total_warehouses": total_warehouses,
        "total_pis": 0,
        "total_pos": 0,
        "total_stock_inward": 0,
        "total_stock_outward": 0,
        "pending_pis": 0,
        "pending_pos": 0
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
    
    async for pi in mongo_db.performa_invoices.find(pi_query, {"_id": 0}).sort("date", -1):
        # Get customer/company details
        customer = await mongo_db.companies.find_one({"id": pi.get("customer_id")}, {"_id": 0})
        customer_name_str = customer.get("name") if customer else "Unknown"
        
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
            
            # Find POs linked to this PI
            linked_pos = []
            async for po in mongo_db.purchase_orders.find({
                "reference_pi_ids": pi["id"],
                "is_active": True
            }, {"_id": 0}):
                linked_pos.append(po)
            
            # Find inward entries linked to these POs
            for po in linked_pos:
                async for inward in mongo_db.inward_stock.find({
                    "po_id": po["id"],
                    "inward_type": "warehouse",
                    "is_active": True
                }, {"_id": 0}):
                    for inward_item in inward.get("line_items", []):
                        if inward_item.get("product_id") == product_id:
                            qty = float(inward_item.get("quantity", 0))
                            inwarded_quantity += qty
                            inward_details.append({
                                "po_number": po.get("po_no"),
                                "inward_invoice_no": inward.get("inward_invoice_no"),
                                "date": inward.get("date"),
                                "quantity": qty
                            })
            
            # Calculate Dispatched Quantity (from Export Invoices linked to this PI)
            dispatched_quantity = 0.0
            dispatch_details = []
            
            async for outward in mongo_db.outward_stock.find({
                "pi_ids": pi["id"],
                "dispatch_type": {"$in": ["dispatch_plan", "export_invoice"]},
                "is_active": True
            }, {"_id": 0}):
                for outward_item in outward.get("line_items", []):
                    if outward_item.get("product_id") == product_id:
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
                "linked_po_numbers": [po.get("po_no") for po in linked_pos],
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
    Filter by Company and PI, then display all linked POs with quantities
    """
    try:
        # Parse filters
        company_id_list = company_ids.split(",") if company_ids else []
        pi_number_list = pi_numbers.split(",") if pi_numbers else []
        
        if not company_id_list or not pi_number_list:
            return {"message": "Please select Company and PI Number filters", "data": []}
        
        # Build PI query
        pi_query = {
            "company_id": {"$in": company_id_list},
            "voucher_no": {"$in": pi_number_list},
            "is_active": True
        }
        
        # Fetch all matching PIs
        pis = []
        async for pi in mongo_db.performa_invoices.find(pi_query, {"_id": 0}):
            pis.append(pi)
        
        if not pis:
            return {"message": "No PIs found for selected filters", "data": []}
        
        # Get all PI IDs
        pi_ids = [pi.get("id") for pi in pis]
        
        # Fetch all POs linked to these PIs
        po_query = {
            "$or": [
                {"reference_pi_id": {"$in": pi_ids}},
                {"reference_pi_ids": {"$elemMatch": {"$in": pi_ids}}}
            ],
            "is_active": True
        }
        
        pos = []
        async for po in mongo_db.purchase_orders.find(po_query, {"_id": 0}):
            pos.append(po)
        
        # Build analysis data
        analysis_data = []
        
        for po in pos:
            po_number = po.get("voucher_no")
            po_id = po.get("id")
            
            # Get reference PI IDs from PO
            reference_pi_ids = po.get("reference_pi_ids", [])
            if not reference_pi_ids and po.get("reference_pi_id"):
                reference_pi_ids = [po.get("reference_pi_id")]
            
            # For each product in PO
            for po_item in po.get("line_items", []):
                product_id = po_item.get("product_id")
                product_name = po_item.get("product_name")
                sku = po_item.get("sku")
                po_quantity = float(po_item.get("quantity", 0))
                
                # Find matching PI and get PI quantity
                pi_quantity = 0
                buyer = "N/A"
                pi_number = "N/A"
                
                for pi in pis:
                    if pi.get("id") in reference_pi_ids:
                        buyer = pi.get("buyer", "N/A")
                        pi_number = pi.get("voucher_no", "N/A")
                        
                        # Find matching product in PI
                        for pi_item in pi.get("line_items", []):
                            if pi_item.get("product_id") == product_id:
                                pi_quantity = float(pi_item.get("quantity", 0))
                                break
                        break
                
                # Calculate Inward Quantity (from inward_stock where inward_type="warehouse")
                inward_quantity = 0
                async for inward in mongo_db.inward_stock.find({
                    "po_id": po_id,
                    "inward_type": "warehouse",
                    "is_active": True
                }, {"_id": 0}):
                    for inward_item in inward.get("line_items", []):
                        if inward_item.get("product_id") == product_id:
                            inward_quantity += float(inward_item.get("quantity", 0))
                
                # Calculate In-Transit Quantity (from pickup_in_transit collection)
                intransit_quantity = 0
                async for pickup in mongo_db.pickup_in_transit.find({
                    "po_id": po_id,
                    "is_active": True
                }, {"_id": 0}):
                    for pickup_item in pickup.get("line_items", []):
                        if pickup_item.get("product_id") == product_id:
                            intransit_quantity += float(pickup_item.get("quantity", 0))
                
                # Calculate Remaining (PO Qty - Inward - In-Transit)
                remaining_quantity = po_quantity - inward_quantity - intransit_quantity
                
                # Add to analysis data
                analysis_data.append({
                    "buyer": buyer,
                    "product_name": product_name,
                    "sku": sku,
                    "pi_number": pi_number,
                    "pi_quantity": pi_quantity,
                    "po_number": po_number,
                    "po_quantity": po_quantity,
                    "inward_quantity": inward_quantity,
                    "intransit_quantity": intransit_quantity,
                    "remaining_quantity": remaining_quantity
                })
        
        return {"data": analysis_data, "count": len(analysis_data)}
        
    except Exception as e:
        print(f"Error in purchase analysis: {str(e)}")
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
#             async for pi in mongo_db.performa_invoices.find({"id": {"$in": reference_pi_ids}, "is_active": True}, {"_id": 0}):
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
    
    Query param: voucher_no (PO voucher number)
    """
    try:
        # Find PO by voucher number
        po = await mongo_db.purchase_orders.find_one({"voucher_no": voucher_no, "is_active": True}, {"_id": 0})
        if not po:
            raise HTTPException(status_code=404, detail=f"PO not found with voucher number: {voucher_no}")
        
        po_id = po.get("id")
        
        # Get reference PI IDs from PO
        reference_pi_ids = po.get("reference_pi_ids", [])
        if not reference_pi_ids and po.get("reference_pi_id"):
            reference_pi_ids = [po.get("reference_pi_id")]
        
        # Fetch all referenced PIs
        pis = []
        if reference_pi_ids:
            async for pi in mongo_db.performa_invoices.find({"id": {"$in": reference_pi_ids}, "is_active": True}, {"_id": 0}):
                pis.append(pi)
        
        # Build line items with stats
        line_stats = []
        for po_item in po.get("line_items", []):
            po_item_id = po_item.get("id")  # ✅ This is the key to match across collections
            product_id = po_item.get("product_id")
            product_name = po_item.get("product_name")
            sku = po_item.get("sku")
            po_quantity = float(po_item.get("quantity", 0))
            rate = float(po_item.get("rate", 0))
            
            # Find matching PI quantity
            pi_quantity = 0
            for pi in pis:
                for pi_item in pi.get("line_items", []):
                    if pi_item.get("product_id") == product_id:
                        pi_quantity += float(pi_item.get("quantity", 0))
            
            # Calculate Already Inwarded (from inward_stock)
            already_inwarded = 0
            async for inward in mongo_db.inward_stock.find({
                "po_id": po_id,
                "is_active": True
            }, {"_id": 0}):
                for inward_item in inward.get("line_items", []):
                    if inward_item.get("id") == po_item_id:  # ✅ Match by line item ID
                        already_inwarded += float(inward_item.get("quantity", 0))
            
            # Calculate In-Transit (from pickup_in_transit collection)
            in_transit = 0
            async for pickup in mongo_db.pickup_in_transit.find({
                "po_id": po_id,
                "is_active": True
            }, {"_id": 0}):
                for pickup_item in pickup.get("line_items", []):
                    if pickup_item.get("id") == po_item_id:  # ✅ Match by line item ID
                        in_transit += float(pickup_item.get("quantity", 0))
            
            # Calculate available quantity for pickup
            available_for_pickup = po_quantity - already_inwarded - in_transit
            
            line_stats.append({
                "id": po_item_id,  # ✅ PO line item ID - required for pickup creation
                "product_id": product_id,
                "product_name": product_name,
                "sku": sku,
                "pi_quantity": pi_quantity,
                "po_quantity": po_quantity,
                "already_inwarded": already_inwarded,
                "in_transit": in_transit,
                "available_for_pickup": available_for_pickup,
                "rate": rate
            })
        
        return {
            "po_voucher_no": voucher_no,
            "po_id": po_id,
            "po_date": po.get("date"),
            "supplier": po.get("supplier"),
            "line_items": line_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching PO line stats: {str(e)}")
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


@api_router.post("/pickups")
async def create_pickup(
    pickup_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Create a new Pickup (In-Transit) entry
    """
    try:
        # -----------------------------
        # 1️⃣ BASIC VALIDATION
        # -----------------------------
        po_id = pickup_data.get("po_id")
        if not po_id:
            raise HTTPException(status_code=400, detail="po_id is required")

        po = await mongo_db.purchase_orders.find_one(
            {"id": po_id, "is_active": True},
            {"_id": 0}
        )
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")

        line_items = pickup_data.get("line_items", [])
        if not line_items:
            raise HTTPException(
                status_code=400,
                detail="At least one line item is required"
            )

        # -----------------------------
        # 2️⃣ VALIDATE QUANTITIES
        # -----------------------------
        for item in line_items:
            po_line_id = item.get("id")   # ✅ PO line item id
            new_quantity = float(item.get("quantity", 0))

            if not po_line_id:
                raise HTTPException(
                    status_code=400,
                    detail="PO line item id is required"
                )

            if new_quantity <= 0:
                continue  # skip zero qty

            # 🔹 Find PO quantity for this line
            po_quantity = 0
            for po_item in po.get("line_items", []):
                if po_item.get("id") == po_line_id:
                    po_quantity = float(po_item.get("quantity", 0))
                    break

            if po_quantity == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid PO line item id"
                )

            # 🔹 Calculate already inwarded
            already_inwarded = 0
            async for inward in mongo_db.inward_stock.find(
                {"po_id": po_id, "is_active": True},
                {"_id": 0}
            ):
                for inward_item in inward.get("line_items", []):
                    if inward_item.get("id") == po_line_id:
                        already_inwarded += float(
                            inward_item.get("quantity", 0)
                        )

            # 🔹 Calculate existing in-transit
            existing_in_transit = 0
            async for pickup in mongo_db.pickup_in_transit.find(
                {"po_id": po_id, "is_active": True},
                {"_id": 0}
            ):
                for pickup_item in pickup.get("line_items", []):
                    if pickup_item.get("id") == po_line_id:
                        existing_in_transit += float(
                            pickup_item.get("quantity", 0)
                        )

            # 🔹 Final validation
            total_quantity = (
                new_quantity
                + already_inwarded
                + existing_in_transit
            )

            if total_quantity > po_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Pickup quantity exceeds PO quantity. "
                        f"PO: {po_quantity}, "
                        f"Inwarded: {already_inwarded}, "
                        f"In Transit: {existing_in_transit}"
                    )
                )

        # -----------------------------
        # 3️⃣ CREATE PICKUP ENTRY
        # -----------------------------
        pickup_dict = {
            "id": str(uuid.uuid4()),  # ✅ pickup id
            "pickup_date": pickup_data.get("pickup_date"),
            "po_id": po_id,
            "po_voucher_no": po.get("voucher_no"),
            "manual": pickup_data.get("manual", ""),
            "notes": pickup_data.get("notes", ""),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user["id"],
            "line_items": []
        }

        # -----------------------------
        # 4️⃣ ADD PICKUP LINE ITEMS
        # -----------------------------
        for item in line_items:
            quantity = float(item.get("quantity", 0))
            if quantity > 0:
                pickup_dict["line_items"].append({
                    "id": item.get("id"),   # ✅ PO line item id
                    "product_name": item.get("product_name"),
                    "sku": item.get("sku"),
                    "quantity": quantity,
                    "rate": float(item.get("rate", 0))
                })

        if not pickup_dict["line_items"]:
            raise HTTPException(
                status_code=400,
                detail="No valid line items with quantity > 0"
            )

        # -----------------------------
        # 5️⃣ SAVE TO DB
        # -----------------------------
        await mongo_db.pickup_in_transit.insert_one(pickup_dict)

        # Audit log
        await mongo_db.audit_logs.insert_one({
            "action": "pickup_created",
            "user_id": current_user["id"],
            "entity_id": pickup_dict["id"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        pickup_dict.pop("_id", None)

        return pickup_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pickup: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@api_router.get("/pickups")
async def get_pickups(
    po_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all pickup entries with optional PO filter"""
    try:
        query = {"is_active": True}
        if po_id:
            query["po_id"] = po_id
        
        pickups = []
        async for pickup in mongo_db.pickup_in_transit.find(query, {"_id": 0}).sort("created_at", -1):
            pickups.append(pickup)
        
        return pickups
    except Exception as e:
        logger.error(f"Error fetching pickups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/{pickup_id}/inward")
async def inward_from_pickup(pickup_id: str):

    pickup = await mongo_db.pickup_in_transit.find_one({"id": pickup_id})
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found")

    if pickup.get("is_inwarded"):
        raise HTTPException(status_code=400, detail="Pickup already inwarded")

    inward = await mongo_db.inward_stock.find_one({"po_id": pickup["po_id"]})
    if not inward:
        raise HTTPException(status_code=400, detail="Inward stock not found for this PO")

    for pickup_item in pickup["line_items"]:

        inward_item = next(
            (
                item for item in inward["line_items"]
                if item["product_name"] == pickup_item["product_name"]
                and item["sku"] == pickup_item["sku"]
            ),
            None
        )

        if not inward_item:
            raise HTTPException(
                status_code=400,
                detail=f"Product {pickup_item['product_name']} not found in inward stock"
            )

        if pickup_item["quantity"] > inward_item["remaining"]:
            raise HTTPException(
                status_code=400,
                detail=f"Pickup quantity exceeds remaining PO quantity for {pickup_item['product_name']}"
            )

        # 🔹 MOVE quantity from pickup → inward
        pickup_qty = pickup_item["quantity"]

        # save old inward quantity
        inward_item["previous_quantity"] = inward_item.get("quantity", 0)

        # update inward quantity
        inward_item["quantity"] = inward_item["previous_quantity"] + pickup_qty
        inward_item["already_inwarded"] += pickup_qty
        inward_item["remaining"] = inward_item["total_po_qty"] - inward_item["quantity"]

        # reset pickup quantity
        pickup_item["already_inwarded"] = pickup_qty
        pickup_item["quantity"] = 0

    await mongo_db.pickup_in_transit.update_one(
        {"id": pickup["id"]},
        {
            "$set": {
                "line_items": pickup["line_items"],
                "is_inwarded": True
            }
        }
    )

    await mongo_db.inward_stock.update_one(
        {"_id": inward["_id"]},
        {
            "$set": {
                "line_items": inward["line_items"],
                "status": "Received"
            }
        }
    )

    return {
        "message": "Inward completed successfully",
        "pickup_id": pickup["id"],
        "inward_stock_id": str(inward["_id"]),
        "po_id": pickup["po_id"]
    }

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
    """Get a specific pickup entry"""
    pickup = await mongo_db.pickup_in_transit.find_one({"id": pickup_id, "is_active": True}, {"_id": 0})
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found")
    return pickup


@api_router.delete("/pickups/{pickup_id}")
async def delete_pickup(
    pickup_id: str,
    current_user: dict = Depends(get_current_active_user)
):
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
            
            # Check if there's related outward stock
            outward_count = await mongo_db.outward_stock.count_documents({
                "po_id": inward.get("po_id"),
                "is_active": True
            })
            
            if outward_count > 0:
                failed.append({
                    "id": inward_id,
                    "reason": f"Has related {outward_count} outward record(s)"
                })
                continue
            
            # Soft delete
            await mongo_db.inward_stock.update_one(
                {"id": inward_id},
                {"$set": {"is_active": False}}
            )
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

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")
