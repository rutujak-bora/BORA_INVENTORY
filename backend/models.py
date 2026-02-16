from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime, timezone
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    REGULAR = "regular"
    DNS_LIMITED = "dns_limited"
    AUDITOR = "auditor"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.REGULAR)
    section = Column(String, nullable=False)  # 'all_companies' or 'dns'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    gstn = Column(String, unique=True)
    apob = Column(String)
    address = Column(Text)
    contact_details = Column(String)
    country = Column(String)
    city = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True)
    sku_name = Column(String, nullable=False, unique=True, index=True)
    category = Column(String)
    brand = Column(String)
    hsn_sac = Column(String)
    country_of_origin = Column(String)
    unit_of_measure = Column(String)
    default_rate = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Warehouse(Base):
    __tablename__ = "warehouses"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)
    address = Column(Text)
    city = Column(String)
    country = Column(String)
    contact_details = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class proformaInvoice(Base):
    __tablename__ = "proforma_invoices"
    
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'))
    voucher_no = Column(String, nullable=False, unique=True, index=True)
    date = Column(DateTime, nullable=False)
    consignee = Column(String)
    buyer = Column(String)
    status = Column(String, default="Pending")  # Pending, In Progress, Completed
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    company = relationship("Company")

class PILineItem(Base):
    __tablename__ = "pi_line_items"
    
    id = Column(String, primary_key=True)
    pi_id = Column(String, ForeignKey('proforma_invoices.id'))
    product_id = Column(String, ForeignKey('products.id'))
    product_name = Column(String)
    sku = Column(String)
    category = Column(String)
    brand = Column(String)
    hsn_sac = Column(String)
    made_in = Column(String)
    quantity = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    
    pi = relationship("proformaInvoice")
    product = relationship("Product")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'))
    voucher_no = Column(String, nullable=False, unique=True, index=True)
    date = Column(DateTime, nullable=False)
    consignee = Column(String)
    supplier = Column(String)
    reference_pi_id = Column(String, ForeignKey('proforma_invoices.id'), nullable=True)
    reference_no_date = Column(String)
    dispatched_through = Column(String)
    destination = Column(String)
    status = Column(String, default="Pending")  # Pending, Approved, In Transit, Completed
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    company = relationship("Company")
    reference_pi = relationship("proformaInvoice")

class POLineItem(Base):
    __tablename__ = "po_line_items"
    
    id = Column(String, primary_key=True)
    po_id = Column(String, ForeignKey('purchase_orders.id'))
    product_id = Column(String, ForeignKey('products.id'))
    product_name = Column(String)
    sku = Column(String)
    category = Column(String)
    brand = Column(String)
    hsn_sac = Column(String)
    quantity = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    input_igst = Column(Float, default=0)
    tds = Column(Float, default=0)
    
    po = relationship("PurchaseOrder")
    product = relationship("Product")

class InwardStock(Base):
    __tablename__ = "inward_stock"
    
    id = Column(String, primary_key=True)
    inward_invoice_no = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    po_id = Column(String, ForeignKey('purchase_orders.id'), nullable=True)
    pi_id = Column(String, ForeignKey('proforma_invoices.id'), nullable=True)
    product_id = Column(String, ForeignKey('products.id'))
    warehouse_id = Column(String, ForeignKey('warehouses.id'), nullable=True)
    product_name = Column(String)
    sku = Column(String)
    quantity = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    inward_type = Column(String)  # in_transit, warehouse, direct
    status = Column(String, default="Received")  # In Transit, Received
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    po = relationship("PurchaseOrder")
    pi = relationship("proformaInvoice")
    product = relationship("Product")
    warehouse = relationship("Warehouse")

class OutwardStock(Base):
    __tablename__ = "outward_stock"
    
    id = Column(String, primary_key=True)
    export_invoice_no = Column(String, nullable=False, unique=True)
    date = Column(DateTime, nullable=False)
    company_id = Column(String, ForeignKey('companies.id'))
    pi_id = Column(String, ForeignKey('proforma_invoices.id'), nullable=True)
    warehouse_id = Column(String, ForeignKey('warehouses.id'))
    mode = Column(String)  # Sea, Air
    dispatch_type = Column(String)  # dispatch_plan, export_invoice, direct_export
    status = Column(String, default="Pending Dispatch")  # Pending Dispatch, Dispatched, Delivered
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company")
    pi = relationship("proformaInvoice")
    warehouse = relationship("Warehouse")

class OutwardLineItem(Base):
    __tablename__ = "outward_line_items"
    
    id = Column(String, primary_key=True)
    outward_id = Column(String, ForeignKey('outward_stock.id'))
    product_id = Column(String, ForeignKey('products.id'))
    product_name = Column(String)
    sku = Column(String)
    quantity = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    dimensions = Column(String)
    weight = Column(Float)
    
    outward = relationship("OutwardStock")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(String, primary_key=True)
    pi_id = Column(String, ForeignKey('proforma_invoices.id'))
    voucher_no = Column(String)
    date = Column(DateTime, nullable=False)
    advance_payment = Column(Float, default=0)
    received_amount = Column(Float, default=0)
    remaining_amount = Column(Float, default=0)
    bank_name = Column(String)
    bank_details = Column(Text)
    dispatch_qty = Column(Float, default=0)
    pending_qty = Column(Float, default=0)
    dispatch_date = Column(DateTime, nullable=True)
    export_invoice_no = Column(String)
    dispatch_goods_value = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    pi = relationship("proformaInvoice")

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(String, primary_key=True)
    export_invoice_nos = Column(Text)  # Comma-separated export invoice numbers
    freight = Column(Float, default=0)
    cha_charges = Column(Float, default=0)
    other_charges = Column(Float, default=0)
    total = Column(Float, default=0)
    date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
