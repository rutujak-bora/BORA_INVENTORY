from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from models import UserRole

# Auth Schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.REGULAR

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    username: str
    email: str
    role: UserRole
    section: str
    is_active: bool
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Company Schemas
class CompanyCreate(BaseModel):
    name: str
    gstn: Optional[str] = None
    apob: Optional[str] = None
    address: Optional[str] = None
    contact_details: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    gstn: Optional[str] = None
    apob: Optional[str] = None
    address: Optional[str] = None
    contact_details: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None

class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    gstn: Optional[str] = None
    apob: Optional[str] = None
    address: Optional[str] = None
    contact_details: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    is_active: bool
    created_at: datetime

# Product Schemas
class ProductCreate(BaseModel):
    sku_name: str
    category: Optional[str] = None
    brand: Optional[str] = None
    hsn_sac: Optional[str] = None
    country_of_origin: Optional[str] = None
    color: Optional[str] = None
    specification: Optional[str] = None  # Changed to string to accept both text and numbers
    feature: Optional[str] = None  # New field

class ProductUpdate(BaseModel):
    sku_name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    hsn_sac: Optional[str] = None
    country_of_origin: Optional[str] = None
    color: Optional[str] = None
    specification: Optional[str] = None  # Changed to string to accept both text and numbers
    feature: Optional[str] = None  # New field

class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    sku_name: str
    category: Optional[str] = None
    brand: Optional[str] = None
    hsn_sac: Optional[str] = None
    country_of_origin: Optional[str] = None
    color: Optional[str] = None
    specification: Optional[str] = None  # Changed to string to accept both text and numbers
    feature: Optional[str] = None  # New field
    is_active: bool
    created_at: datetime

# Warehouse Schemas
class WarehouseCreate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    contact_details: Optional[str] = None

class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    contact_details: Optional[str] = None

class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    contact_details: Optional[str] = None
    is_active: bool
    created_at: datetime


# Bank Schemas
class BankCreate(BaseModel):
    bank_name: str
    ifsc_code: Optional[str] = None
    ad_code: Optional[str] = None
    address: Optional[str] = None
    account_number: Optional[str] = None

class BankUpdate(BaseModel):
    bank_name: Optional[str] = None
    ifsc_code: Optional[str] = None
    ad_code: Optional[str] = None
    address: Optional[str] = None
    account_number: Optional[str] = None

class BankResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    bank_name: str
    ifsc_code: Optional[str] = None
    ad_code: Optional[str] = None
    address: Optional[str] = None
    account_number: Optional[str] = None
    is_active: bool
    created_at: datetime

# PI Line Item Schema
class PILineItemCreate(BaseModel):
    product_id: str
    product_name: str
    sku: str
    category: Optional[str] = None
    brand: Optional[str] = None
    hsn_sac: Optional[str] = None
    made_in: Optional[str] = None
    quantity: float
    rate: float
    amount: float

class PILineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    product_id: str
    product_name: str
    sku: str
    category: Optional[str] = None
    brand: Optional[str] = None
    hsn_sac: Optional[str] = None
    made_in: Optional[str] = None
    quantity: float
    rate: float
    amount: float

# PI Schemas
class PICreate(BaseModel):
    company_id: str
    voucher_no: str
    date: datetime
    consignee: Optional[str] = None
    buyer: Optional[str] = None
    line_items: List[PILineItemCreate]

class PIUpdate(BaseModel):
    company_id: Optional[str] = None
    voucher_no: Optional[str] = None
    date: Optional[datetime] = None
    consignee: Optional[str] = None
    buyer: Optional[str] = None
    status: Optional[str] = None

class PIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    company_id: str
    voucher_no: str
    date: datetime
    consignee: Optional[str] = None
    buyer: Optional[str] = None
    status: str
    is_active: bool
    created_at: datetime

class PIDetailResponse(PIResponse):
    line_items: List[PILineItemResponse] = []

# PO Line Item Schema
class POLineItemCreate(BaseModel):
    product_id: str
    product_name: str
    sku: str
    category: Optional[str] = None
    brand: Optional[str] = None
    hsn_sac: Optional[str] = None
    quantity: float
    rate: float
    amount: float
    input_igst: Optional[float] = 0
    tds: Optional[float] = 0

class POLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    product_id: str
    product_name: str
    sku: str
    category: Optional[str] = None
    brand: Optional[str] = None
    hsn_sac: Optional[str] = None
    quantity: float
    rate: float
    amount: float
    input_igst: float
    tds: float

# PO Schemas
class POCreate(BaseModel):
    company_id: str
    voucher_no: str
    date: datetime
    consignee: Optional[str] = None
    supplier: Optional[str] = None
    reference_pi_id: Optional[str] = None  # For backward compatibility
    reference_pi_ids: Optional[List[str]] = None  # New field for multiple PIs
    reference_no_date: Optional[str] = None
    dispatched_through: Optional[str] = None
    destination: Optional[str] = None
    line_items: List[POLineItemCreate]

class POUpdate(BaseModel):
    company_id: Optional[str] = None
    voucher_no: Optional[str] = None
    date: Optional[datetime] = None
    consignee: Optional[str] = None
    supplier: Optional[str] = None
    reference_pi_id: Optional[str] = None  # For backward compatibility
    reference_pi_ids: Optional[List[str]] = None  # New field for multiple PIs
    reference_no_date: Optional[str] = None
    dispatched_through: Optional[str] = None
    destination: Optional[str] = None
    status: Optional[str] = None

class POResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    company_id: str
    voucher_no: str
    date: datetime
    consignee: Optional[str] = None
    supplier: Optional[str] = None
    reference_pi_id: Optional[str] = None  # For backward compatibility
    reference_pi_ids: Optional[List[str]] = None  # New field for multiple PIs
    reference_no_date: Optional[str] = None
    dispatched_through: Optional[str] = None
    destination: Optional[str] = None
    status: str
    is_active: bool
    created_at: datetime

class PODetailResponse(POResponse):
    line_items: List[POLineItemResponse] = []

# Payment Schemas
class PaymentCreate(BaseModel):
    pi_id: str
    voucher_no: Optional[str] = None
    date: datetime
    advance_payment: Optional[float] = 0
    received_amount: Optional[float] = 0
    remaining_amount: Optional[float] = 0
    bank_name: Optional[str] = None
    bank_details: Optional[str] = None
    dispatch_qty: Optional[float] = 0
    pending_qty: Optional[float] = 0
    dispatch_date: Optional[datetime] = None
    export_invoice_no: Optional[str] = None
    dispatch_goods_value: Optional[float] = 0
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    pi_id: str
    voucher_no: Optional[str] = None
    date: datetime
    advance_payment: float
    received_amount: float
    remaining_amount: float
    bank_name: Optional[str] = None
    dispatch_qty: float
    pending_qty: float
    dispatch_date: Optional[datetime] = None
    export_invoice_no: Optional[str] = None
    dispatch_goods_value: float
    notes: Optional[str] = None
    created_at: datetime

# Inward Stock Line Item Schemas
class InwardLineItemCreate(BaseModel):
    product_id: str
    product_name: str
    sku: str
    quantity: float
    rate: float
    amount: float

class InwardLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    product_id: str
    product_name: str
    sku: str
    quantity: float
    rate: float
    amount: float

# Inward Stock Schemas (Enhanced for multi-product support)
class InwardStockCreate(BaseModel):
    inward_invoice_no: str
    date: datetime
    po_id: Optional[str] = None
    pi_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    inward_type: str  # warehouse, direct
    source_type: Optional[str] = None  # pickup_inward, direct_inward
    status: Optional[str] = "Received"
    line_items: List[InwardLineItemCreate]

class InwardStockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    inward_invoice_no: str
    date: datetime
    po_id: Optional[str] = None
    pi_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    inward_type: str
    source_type: Optional[str] = None
    status: str
    total_amount: float
    line_items_count: int
    created_at: datetime

class InwardStockDetailResponse(InwardStockResponse):
    line_items: List[InwardLineItemResponse] = []

# Stock Summary Schemas
class StockSummaryResponse(BaseModel):
    product_id: str
    product_name: str
    sku: str
    category: Optional[str] = None
    warehouse_id: Optional[str] = None
    warehouse_name: Optional[str] = None
    quantity_inward: float
    quantity_outward: float
    remaining_stock: float
    
# Central Stock Tracking Schema
class StockTrackingResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    sku: str
    warehouse_id: Optional[str] = None
    warehouse_name: Optional[str] = None
    current_stock: float
    last_updated: datetime

# Outward Stock Schemas
class OutwardLineItemCreate(BaseModel):
    product_id: str
    product_name: str
    sku: str
    quantity: float
    rate: float
    amount: float
    dimensions: Optional[str] = None
    weight: Optional[float] = None

class OutwardLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    product_id: str
    product_name: str
    sku: str
    quantity: float
    rate: float
    amount: float
    dimensions: Optional[str] = None
    weight: Optional[float] = None

class OutwardStockCreate(BaseModel):
    export_invoice_no: Optional[str] = None  # For dispatch plans, this might be generated later
    date: datetime
    company_id: str
    pi_id: Optional[str] = None
    warehouse_id: str
    mode: Optional[str] = None  # Sea, Air
    dispatch_type: str  # dispatch_plan, export_invoice, direct_export
    status: Optional[str] = "Pending Dispatch"  # Pending Dispatch, Dispatched, Delivered
    line_items: List[OutwardLineItemCreate]

class OutwardStockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    export_invoice_no: Optional[str] = None
    date: datetime
    company_id: str
    pi_id: Optional[str] = None
    warehouse_id: str
    mode: Optional[str] = None
    dispatch_type: str
    status: str
    total_amount: float
    line_items_count: int
    created_at: datetime

class OutwardStockDetailResponse(OutwardStockResponse):
    line_items: List[OutwardLineItemResponse] = []

# Expense Schemas
class ExpenseCreate(BaseModel):
    export_invoice_nos: str  # Comma-separated
    freight: Optional[float] = 0
    cha_charges: Optional[float] = 0
    other_charges: Optional[float] = 0
    notes: Optional[str] = None

class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    export_invoice_nos: str
    freight: float
    cha_charges: float
    other_charges: float
    total: float
    date: datetime
    notes: Optional[str] = None
    created_at: datetime

# Dashboard Stats
class DashboardStats(BaseModel):
    total_companies: int
    total_warehouses: int
    total_pis: int
    total_pos: int
    total_stock_inward: float
    total_stock_outward: float
    pending_pis: int
    pending_pos: int
