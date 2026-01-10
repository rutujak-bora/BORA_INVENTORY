from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File
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
    DashboardStats
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="Bora Mobility Inventory System")
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
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        companies = []
        for _, row in df.iterrows():
            company_dict = {
                "id": str(uuid.uuid4()),
                "name": str(row.get('name', row.get('Name', ''))),
                "gstn": str(row.get('gstn', row.get('GSTN', ''))) if pd.notna(row.get('gstn', row.get('GSTN', ''))) else None,
                "apob": str(row.get('apob', row.get('APOB', ''))) if pd.notna(row.get('apob', row.get('APOB', ''))) else None,
                "address": str(row.get('address', row.get('Address', ''))) if pd.notna(row.get('address', row.get('Address', ''))) else None,
                "contact_details": str(row.get('contact_details', row.get('Contact', ''))) if pd.notna(row.get('contact_details', row.get('Contact', ''))) else None,
                "country": str(row.get('country', row.get('Country', ''))) if pd.notna(row.get('country', row.get('Country', ''))) else None,
                "city": str(row.get('city', row.get('City', ''))) if pd.notna(row.get('city', row.get('City', ''))) else None,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            companies.append(company_dict)
        
        if companies:
            await mongo_db.companies.insert_many(companies)
        
        return {"message": f"Successfully uploaded {len(companies)} companies", "count": len(companies)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@api_router.get("/companies")
async def get_companies(current_user: dict = Depends(get_current_active_user)):
    companies = []
    async for company in mongo_db.companies.find({"is_active": True}, {"_id": 0}):
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
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await mongo_db.companies.update_one({"id": company_id}, {"$set": update_data})
    
    updated_company = await mongo_db.companies.find_one({"id": company_id}, {"_id": 0})
    return updated_company

@api_router.delete("/companies/{company_id}")
async def delete_company(company_id: str, current_user: dict = Depends(get_current_active_user)):
    company = await mongo_db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    await mongo_db.companies.update_one({"id": company_id}, {"$set": {"is_active": False}})
    return {"message": "Company deleted successfully"}

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
            product_dict = {
                "id": str(uuid.uuid4()),
                "sku_name": str(row.get('sku_name', row.get('SKU', row.get('Name', '')))),
                "category": str(row.get('category', row.get('Category', ''))) if pd.notna(row.get('category', row.get('Category', ''))) else None,
                "brand": str(row.get('brand', row.get('Brand', ''))) if pd.notna(row.get('brand', row.get('Brand', ''))) else None,
                "hsn_sac": str(row.get('hsn_sac', row.get('HSN', ''))) if pd.notna(row.get('hsn_sac', row.get('HSN', ''))) else None,
                "country_of_origin": str(row.get('country_of_origin', row.get('Country', ''))) if pd.notna(row.get('country_of_origin', row.get('Country', ''))) else None,
                "unit_of_measure": str(row.get('unit_of_measure', row.get('Unit', ''))) if pd.notna(row.get('unit_of_measure', row.get('Unit', ''))) else None,
                "default_rate": float(row.get('default_rate', row.get('Rate', 0))) if pd.notna(row.get('default_rate', row.get('Rate', 0))) else None,
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
    
    await mongo_db.products.update_one({"id": product_id}, {"$set": {"is_active": False}})
    return {"message": "Product deleted successfully"}

# ==================== WAREHOUSE ROUTES ====================
@api_router.post("/warehouses")
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    current_user: dict = Depends(get_current_active_user)
):
    warehouse_dict = {
        "id": str(uuid.uuid4()),
        **warehouse_data.model_dump(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await mongo_db.warehouses.insert_one(warehouse_dict)
    warehouse_dict.pop("_id", None)
    return warehouse_dict

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

@api_router.get("/warehouses")
async def get_warehouses(current_user: dict = Depends(get_current_active_user)):
    warehouses = []
    async for warehouse in mongo_db.warehouses.find({"is_active": True}, {"_id": 0}):
        warehouses.append(warehouse)
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
    
    await mongo_db.warehouses.update_one({"id": warehouse_id}, {"$set": {"is_active": False}})
    return {"message": "Warehouse deleted successfully"}

# ==================== DASHBOARD ROUTES ====================
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
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Application started - using MongoDB")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")
