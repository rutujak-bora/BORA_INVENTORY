from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pathlib import Path
import os
import logging
import uuid
from datetime import datetime, timezone, timedelta

from database import Base, engine, get_db, get_mongo_db, mongo_db
from models import (
    User, UserRole, Company, Product, Warehouse, 
    proformaInvoice, PILineItem, PurchaseOrder, POLineItem,
    InwardStock, OutwardStock, OutwardLineItem, Payment, Expense
)
from schemas import (
    UserCreate, UserLogin, Token, UserResponse,
    CompanyCreate, CompanyUpdate, CompanyResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    WarehouseCreate, WarehouseUpdate, WarehouseResponse,
    PICreate, PIUpdate, PIResponse, PIDetailResponse, PILineItemResponse,
    POCreate, POUpdate, POResponse, PODetailResponse, POLineItemResponse,
    PaymentCreate, PaymentResponse,
    InwardStockCreate, InwardStockResponse,
    OutwardStockCreate, OutwardStockResponse, OutwardStockDetailResponse, OutwardLineItemResponse,
    ExpenseCreate, ExpenseResponse,
    DashboardStats
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user, require_role
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Create the main app
app = FastAPI(title="Bora Mobility Inventory System")

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== AUTH ROUTES ====================
# Registration disabled - users are predefined

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    # Find user in MongoDB
    user_doc = await mongo_db.users.find_one({"username": user_data.username}, {"_id": 0})
    
    if not user_doc or not verify_password(user_data.password, user_doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(data={"sub": user_doc["id"]})
    
    # Log to MongoDB
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

@api_router.get("/companies")
async def get_companies(
    current_user: dict = Depends(get_current_active_user)
):
    companies = []
    async for company in mongo_db.companies.find({"is_active": True}, {"_id": 0}):
        companies.append(company)
    return companies

@api_router.get("/companies/{company_id}")
async def get_company(
    company_id: str,
    current_user: dict = Depends(get_current_active_user)
):
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
async def delete_company(
    company_id: str,
    current_user: dict = Depends(get_current_active_user)
):
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

@api_router.get("/products")
async def get_products(
    current_user: dict = Depends(get_current_active_user)
):
    products = []
    async for product in mongo_db.products.find({"is_active": True}, {"_id": 0}):
        products.append(product)
    return products

@api_router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@api_router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product_data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    
    product.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(product)
    return product

@api_router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = False
    await db.commit()
    return {"message": "Product deleted successfully"}

# ==================== WAREHOUSE ROUTES ====================
@api_router.post("/warehouses", response_model=WarehouseResponse)
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    warehouse = Warehouse(id=str(uuid.uuid4()), **warehouse_data.model_dump())
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return warehouse

@api_router.get("/warehouses", response_model=list[WarehouseResponse])
async def get_warehouses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Warehouse).where(Warehouse.is_active == True))
    return result.scalars().all()

@api_router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    warehouse_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse

@api_router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: str,
    warehouse_data: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    for key, value in warehouse_data.model_dump(exclude_unset=True).items():
        setattr(warehouse, key, value)
    
    warehouse.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(warehouse)
    return warehouse

@api_router.delete("/warehouses/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    warehouse.is_active = False
    await db.commit()
    return {"message": "Warehouse deleted successfully"}

# ==================== PI ROUTES ====================
@api_router.post("/pi", response_model=PIDetailResponse)
async def create_pi(
    pi_data: PICreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Create PI
    pi = proformaInvoice(
        id=str(uuid.uuid4()),
        company_id=pi_data.company_id,
        voucher_no=pi_data.voucher_no,
        date=pi_data.date,
        consignee=pi_data.consignee,
        buyer=pi_data.buyer
    )
    db.add(pi)
    await db.flush()
    
    # Create line items
    line_items = []
    for item in pi_data.line_items:
        line_item = PILineItem(
            id=str(uuid.uuid4()),
            pi_id=pi.id,
            **item.model_dump()
        )
        db.add(line_item)
        line_items.append(line_item)
    
    await db.commit()
    await db.refresh(pi)
    
    response = PIDetailResponse.model_validate(pi)
    response.line_items = [PILineItemResponse.model_validate(item) for item in line_items]
    return response

@api_router.get("/pi", response_model=list[PIResponse])
async def get_pis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(proformaInvoice).where(proformaInvoice.is_active == True))
    return result.scalars().all()

@api_router.get("/pi/{pi_id}", response_model=PIDetailResponse)
async def get_pi(
    pi_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(proformaInvoice).where(proformaInvoice.id == pi_id))
    pi = result.scalar_one_or_none()
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    # Get line items
    line_items_result = await db.execute(select(PILineItem).where(PILineItem.pi_id == pi_id))
    line_items = line_items_result.scalars().all()
    
    response = PIDetailResponse.model_validate(pi)
    response.line_items = [PILineItemResponse.model_validate(item) for item in line_items]
    return response

@api_router.put("/pi/{pi_id}", response_model=PIResponse)
async def update_pi(
    pi_id: str,
    pi_data: PIUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(proformaInvoice).where(proformaInvoice.id == pi_id))
    pi = result.scalar_one_or_none()
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    for key, value in pi_data.model_dump(exclude_unset=True).items():
        setattr(pi, key, value)
    
    pi.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pi)
    return pi

@api_router.delete("/pi/{pi_id}")
async def delete_pi(
    pi_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(proformaInvoice).where(proformaInvoice.id == pi_id))
    pi = result.scalar_one_or_none()
    if not pi:
        raise HTTPException(status_code=404, detail="PI not found")
    
    pi.is_active = False
    await db.commit()
    return {"message": "PI deleted successfully"}

# ==================== PO ROUTES ====================
@api_router.post("/po", response_model=PODetailResponse)
async def create_po(
    po_data: POCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Create PO
    po = PurchaseOrder(
        id=str(uuid.uuid4()),
        company_id=po_data.company_id,
        voucher_no=po_data.voucher_no,
        date=po_data.date,
        consignee=po_data.consignee,
        supplier=po_data.supplier,
        reference_pi_id=po_data.reference_pi_id,
        reference_no_date=po_data.reference_no_date,
        dispatched_through=po_data.dispatched_through,
        destination=po_data.destination
    )
    db.add(po)
    await db.flush()
    
    # Create line items
    line_items = []
    for item in po_data.line_items:
        line_item = POLineItem(
            id=str(uuid.uuid4()),
            po_id=po.id,
            **item.model_dump()
        )
        db.add(line_item)
        line_items.append(line_item)
    
    await db.commit()
    await db.refresh(po)
    
    response = PODetailResponse.model_validate(po)
    response.line_items = [POLineItemResponse.model_validate(item) for item in line_items]
    return response

@api_router.get("/po", response_model=list[POResponse])
async def get_pos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.is_active == True))
    return result.scalars().all()

@api_router.get("/po/{po_id}", response_model=PODetailResponse)
async def get_po(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Get line items
    line_items_result = await db.execute(select(POLineItem).where(POLineItem.po_id == po_id))
    line_items = line_items_result.scalars().all()
    
    response = PODetailResponse.model_validate(po)
    response.line_items = [POLineItemResponse.model_validate(item) for item in line_items]
    return response

@api_router.put("/po/{po_id}", response_model=POResponse)
async def update_po(
    po_id: str,
    po_data: POUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    for key, value in po_data.model_dump(exclude_unset=True).items():
        setattr(po, key, value)
    
    po.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(po)
    return po

@api_router.delete("/po/{po_id}")
async def delete_po(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    po.is_active = False
    await db.commit()
    return {"message": "PO deleted successfully"}

# ==================== PAYMENT ROUTES ====================
@api_router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    payment = Payment(id=str(uuid.uuid4()), **payment_data.model_dump())
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment

@api_router.get("/payments", response_model=list[PaymentResponse])
async def get_payments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Payment))
    return result.scalars().all()

@api_router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

# ==================== INWARD STOCK ROUTES ====================
@api_router.post("/inward", response_model=InwardStockResponse)
async def create_inward(
    inward_data: InwardStockCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    inward = InwardStock(id=str(uuid.uuid4()), **inward_data.model_dump())
    db.add(inward)
    await db.commit()
    await db.refresh(inward)
    return inward

@api_router.get("/inward", response_model=list[InwardStockResponse])
async def get_inwards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(InwardStock).where(InwardStock.is_active == True))
    return result.scalars().all()

# ==================== OUTWARD STOCK ROUTES ====================
@api_router.post("/outward", response_model=OutwardStockDetailResponse)
async def create_outward(
    outward_data: OutwardStockCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Create outward
    outward = OutwardStock(
        id=str(uuid.uuid4()),
        export_invoice_no=outward_data.export_invoice_no,
        date=outward_data.date,
        company_id=outward_data.company_id,
        pi_id=outward_data.pi_id,
        warehouse_id=outward_data.warehouse_id,
        mode=outward_data.mode,
        dispatch_type=outward_data.dispatch_type
    )
    db.add(outward)
    await db.flush()
    
    # Create line items
    line_items = []
    for item in outward_data.line_items:
        line_item = OutwardLineItem(
            id=str(uuid.uuid4()),
            outward_id=outward.id,
            **item.model_dump()
        )
        db.add(line_item)
        line_items.append(line_item)
    
    await db.commit()
    await db.refresh(outward)
    
    response = OutwardStockDetailResponse.model_validate(outward)
    response.line_items = [OutwardLineItemResponse.model_validate(item) for item in line_items]
    return response

@api_router.get("/outward", response_model=list[OutwardStockResponse])
async def get_outwards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(OutwardStock).where(OutwardStock.is_active == True))
    return result.scalars().all()

# ==================== EXPENSE ROUTES ====================
@api_router.post("/expenses", response_model=ExpenseResponse)
async def create_expense(
    expense_data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    total = expense_data.freight + expense_data.cha_charges + expense_data.other_charges
    expense = Expense(
        id=str(uuid.uuid4()),
        **expense_data.model_dump(),
        total=total
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense

@api_router.get("/expenses", response_model=list[ExpenseResponse])
async def get_expenses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Expense))
    return result.scalars().all()

# ==================== DASHBOARD ROUTES ====================
@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Get counts
    total_companies = await db.scalar(select(func.count()).select_from(Company).where(Company.is_active == True))
    total_warehouses = await db.scalar(select(func.count()).select_from(Warehouse).where(Warehouse.is_active == True))
    total_pis = await db.scalar(select(func.count()).select_from(proformaInvoice).where(proformaInvoice.is_active == True))
    total_pos = await db.scalar(select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.is_active == True))
    pending_pis = await db.scalar(select(func.count()).select_from(proformaInvoice).where(
        and_(proformaInvoice.is_active == True, proformaInvoice.status == "Pending")
    ))
    pending_pos = await db.scalar(select(func.count()).select_from(PurchaseOrder).where(
        and_(PurchaseOrder.is_active == True, PurchaseOrder.status == "Pending")
    ))
    
    # Get stock totals
    total_inward = await db.scalar(select(func.sum(InwardStock.quantity)).where(InwardStock.is_active == True))
    total_outward_result = await db.execute(
        select(func.sum(OutwardLineItem.quantity))
        .join(OutwardStock)
        .where(OutwardStock.is_active == True)
    )
    total_outward = total_outward_result.scalar()
    
    return DashboardStats(
        total_companies=total_companies or 0,
        total_warehouses=total_warehouses or 0,
        total_pis=total_pis or 0,
        total_pos=total_pos or 0,
        total_stock_inward=total_inward or 0,
        total_stock_outward=total_outward or 0,
        pending_pis=pending_pis or 0,
        pending_pos=pending_pos or 0
    )

# ==================== STOCK SUMMARY ROUTE ====================
@api_router.get("/stock/summary")
async def get_stock_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Get all products
    products_result = await db.execute(select(Product).where(Product.is_active == True))
    products = products_result.scalars().all()
    
    summary = []
    for product in products:
        # Get inward quantity
        inward_qty = await db.scalar(
            select(func.sum(InwardStock.quantity))
            .where(and_(InwardStock.product_id == product.id, InwardStock.is_active == True))
        )
        
        # Get outward quantity
        outward_result = await db.execute(
            select(func.sum(OutwardLineItem.quantity))
            .join(OutwardStock)
            .where(and_(OutwardLineItem.product_id == product.id, OutwardStock.is_active == True))
        )
        outward_qty = outward_result.scalar()
        
        summary.append({
            "product_id": product.id,
            "product_name": product.sku_name,
            "sku": product.sku_name,
            "category": product.category,
            "inward_quantity": inward_qty or 0,
            "outward_quantity": outward_qty or 0,
            "remaining_stock": (inward_qty or 0) - (outward_qty or 0)
        })
    
    return summary

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
