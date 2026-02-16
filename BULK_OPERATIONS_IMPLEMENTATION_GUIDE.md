# Bulk Operations Implementation Guide

## Overview
This guide provides the complete pattern for implementing Edit, Delete, Bulk Select, Bulk Delete, and Export functionality across all modules.

---

## ✅ Completed Components

### Reusable Frontend Components
1. **`/app/frontend/src/components/BulkActionToolbar.jsx`**
   - Displays when items are selected
   - Provides: Clear Selection, Export CSV, Export Excel, Delete Selected buttons
   
2. **`/app/frontend/src/components/DeleteConfirmDialog.jsx`**
   - Reusable delete confirmation modal
   - Shows warning icon and customizable message
   
3. **`/app/frontend/src/utils/exportUtils.js`**
   - `exportToCSV(data, filename)` - Export to CSV
   - `exportToExcel(data, filename, sheetName)` - Export to Excel
   - `formatDataForExport(data, fieldMapping)` - Format data for export

### Backend Pattern (Implemented for Companies)
1. **Enhanced DELETE endpoint** - Referential integrity checks
2. **POST /bulk-delete endpoint** - Bulk deletion with error handling
3. **GET /export endpoint** - Data export with format support

---

## 📋 Implementation Pattern

### Backend Implementation (for each module)

#### Step 1: Enhanced DELETE Endpoint
```python
@api_router.delete("/{module}/{id}")
async def delete_record(id: str, current_user: dict = Depends(get_current_active_user)):
    # 1. Check referential integrity
    # Example: Check if used in other modules
    dependent_count = await mongo_db.dependent_collection.count_documents({
        "reference_id": id, 
        "is_active": True
    })
    
    if dependent_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete. Record is referenced in {dependent_count} dependent record(s)."
        )
    
    # 2. Delete record
    result = await mongo_db.collection.delete_one({"id": id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # 3. Audit log
    await mongo_db.audit_logs.insert_one({
        "action": "module_deleted",
        "user_id": current_user["id"],
        "entity_id": id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Record deleted successfully"}
```

#### Step 2: Bulk Delete Endpoint
```python
@api_router.post("/{module}/bulk-delete")
async def bulk_delete_records(
    payload: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Bulk delete with error handling"""
    ids = payload.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    deleted = []
    failed = []
    
    for record_id in ids:
        try:
            # Check referential integrity
            dependent_count = await mongo_db.dependent.count_documents({
                "reference_id": record_id,
                "is_active": True
            })
            
            if dependent_count > 0:
                failed.append({
                    "id": record_id,
                    "reason": f"Referenced in {dependent_count} record(s)"
                })
                continue
            
            # Delete
            result = await mongo_db.collection.delete_one({"id": record_id})
            if result.deleted_count > 0:
                deleted.append(record_id)
                # Audit log
                await mongo_db.audit_logs.insert_one({
                    "action": "module_bulk_deleted",
                    "user_id": current_user["id"],
                    "entity_id": record_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                failed.append({"id": record_id, "reason": "Not found"})
                
        except Exception as e:
            failed.append({"id": record_id, "reason": str(e)})
    
    return {
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "failed_count": len(failed),
        "failed": failed
    }
```

#### Step 3: Export Endpoint
```python
@api_router.get("/{module}/export")
async def export_records(
    format: str = "json",
    # Add filter parameters as needed
    current_user: dict = Depends(get_current_active_user)
):
    """Export data with optional filters"""
    query = {}  # Add filter logic here
    
    records = []
    async for record in mongo_db.collection.find(query, {"_id": 0}):
        records.append(record)
    
    if format == "csv":
        return {"data": records, "format": "csv"}
    
    return records
```

---

### Frontend Implementation (for each module)

#### Step 1: Add State Variables
```javascript
const [selectedIds, setSelectedIds] = useState([]);
const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
const [recordToDelete, setRecordToDelete] = useState(null);
const [editDialogOpen, setEditDialogOpen] = useState(false);
const [recordToEdit, setRecordToEdit] = useState(null);
```

#### Step 2: Add Checkbox Handlers
```javascript
// Master checkbox handler
const handleSelectAll = (checked) => {
  if (checked) {
    setSelectedIds(filteredData.map(item => item.id));
  } else {
    setSelectedIds([]);
  }
};

// Individual checkbox handler
const handleSelectRow = (id, checked) => {
  if (checked) {
    setSelectedIds([...selectedIds, id]);
  } else {
    setSelectedIds(selectedIds.filter(selectedId => selectedId !== id));
  }
};
```

#### Step 3: Add Bulk Action Handlers
```javascript
// Export CSV
const handleExportCSV = () => {
  const dataToExport = filteredData.filter(item => 
    selectedIds.length > 0 ? selectedIds.includes(item.id) : true
  );
  exportToCSV(formatDataForExport(dataToExport), 'module_name');
};

// Export Excel
const handleExportExcel = () => {
  const dataToExport = filteredData.filter(item => 
    selectedIds.length > 0 ? selectedIds.includes(item.id) : true
  );
  exportToExcel(formatDataForExport(dataToExport), 'module_name', 'Sheet1');
};

// Bulk Delete
const handleBulkDelete = async () => {
  if (!window.confirm(`Delete ${selectedIds.length} selected items?`)) return;
  
  try {
    const response = await api.post('/module/bulk-delete', { ids: selectedIds });
    
    if (response.data.deleted_count > 0) {
      toast({
        title: 'Success',
        description: `${response.data.deleted_count} items deleted successfully`,
      });
    }
    
    if (response.data.failed_count > 0) {
      toast({
        title: 'Partial Success',
        description: `${response.data.failed_count} items could not be deleted`,
        variant: 'destructive'
      });
    }
    
    setSelectedIds([]);
    fetchData(); // Refresh table
  } catch (error) {
    toast({
      title: 'Error',
      description: error.response?.data?.detail || 'Failed to delete items',
      variant: 'destructive'
    });
  }
};

// Single Delete
const handleDelete = async () => {
  try {
    await api.delete(`/module/${recordToDelete.id}`);
    toast({ title: 'Success', description: 'Record deleted successfully' });
    setDeleteDialogOpen(false);
    fetchData();
  } catch (error) {
    toast({
      title: 'Error',
      description: error.response?.data?.detail || 'Failed to delete record',
      variant: 'destructive'
    });
  }
};
```

#### Step 4: Update Table JSX
```jsx
import BulkActionToolbar from '../components/BulkActionToolbar';
import DeleteConfirmDialog from '../components/DeleteConfirmDialog';
import { exportToCSV, exportToExcel, formatDataForExport } from '../utils/exportUtils';
import { Edit, Trash2 } from 'lucide-react';

// Add Bulk Toolbar
<BulkActionToolbar
  selectedCount={selectedIds.length}
  onClearSelection={() => setSelectedIds([])}
  onBulkDelete={handleBulkDelete}
  onExportCSV={handleExportCSV}
  onExportExcel={handleExportExcel}
/>

// Update Table
<Table>
  <TableHeader>
    <TableRow>
      <TableHead className="w-12">
        <input
          type="checkbox"
          checked={selectedIds.length === filteredData.length && filteredData.length > 0}
          onChange={(e) => handleSelectAll(e.target.checked)}
          className="rounded border-gray-300"
        />
      </TableHead>
      {/* Other columns */}
      <TableHead className="text-right">Actions</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {filteredData.map((item) => (
      <TableRow key={item.id}>
        <TableCell>
          <input
            type="checkbox"
            checked={selectedIds.includes(item.id)}
            onChange={(e) => handleSelectRow(item.id, e.target.checked)}
            className="rounded border-gray-300"
          />
        </TableCell>
        {/* Other cells */}
        <TableCell className="text-right">
          <div className="flex items-center justify-end gap-2">
            <button
              onClick={() => {
                setRecordToEdit(item);
                setEditDialogOpen(true);
              }}
              className="text-blue-600 hover:text-blue-800"
            >
              <Edit className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                setRecordToDelete(item);
                setDeleteDialogOpen(true);
              }}
              className="text-red-600 hover:text-red-800"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>

// Add Delete Dialog
<DeleteConfirmDialog
  isOpen={deleteDialogOpen}
  onClose={() => setDeleteDialogOpen(false)}
  onConfirm={handleDelete}
  itemName={recordToDelete?.name}
/>
```

---

## 📊 Module-Specific Referential Integrity Rules

### 1. Companies
- **Cannot delete if:** Used in PI or PO
- **Check:** `purchase_orders.company_id`, `proforma_invoices.company_id`

### 2. Products
- **Cannot delete if:** Used in PI, PO, Inward, or Outward
- **Check:** `proforma_invoices.line_items.product_id`, `purchase_orders.line_items.product_id`, `inward_stock.line_items.product_id`, `outward_stock.line_items.product_id`

### 3. Warehouses
- **Cannot delete if:** Used in Inward or Outward stock
- **Check:** `inward_stock.warehouse_id`, `outward_stock.warehouse_id`

### 4. Banks
- **Cannot delete if:** Used in Payment Tracking
- **Check:** `payment_tracking.bank_id`

### 5. Proforma Invoice (PI)
- **Cannot delete if:** Referenced in PO or has related stock movements
- **Check:** `purchase_orders.reference_pi_id`, `inward_stock.pi_id`, `outward_stock.pi_id`

### 6. Purchase Order (PO)
- **Cannot delete if:** Has inward or pickup entries
- **Check:** `inward_stock.po_id`, `pickup_in_transit.po_id`

### 7. Inward Stock
- **Cannot delete if:** Related outward exists or consumed in dispatch
- **Check:** `outward_stock`, stock summary updates

### 8. Outward Stock
- **Can delete:** But must update stock summary and related calculations

---

## 🎯 Filter-Aware Export Pattern

```javascript
// Always use filteredData, not raw data
const getExportData = () => {
  // If items are selected, export only selected
  if (selectedIds.length > 0) {
    return filteredData.filter(item => selectedIds.includes(item.id));
  }
  // Otherwise export all filtered data
  return filteredData;
};

const handleExportCSV = () => {
  const dataToExport = getExportData();
  exportToCSV(formatDataForExport(dataToExport, fieldMapping), 'module_name');
};
```

---

## 🧪 Testing Checklist

For each module, verify:

- [ ] Edit button opens prefilled modal
- [ ] Edit saves and refreshes table
- [ ] Delete button shows confirmation
- [ ] Delete with dependencies blocked with clear error
- [ ] Delete without dependencies succeeds
- [ ] Master checkbox selects/deselects all
- [ ] Individual checkboxes work
- [ ] Bulk toolbar appears when items selected
- [ ] Bulk delete processes correctly
- [ ] Bulk delete shows failed items with reasons
- [ ] Export CSV downloads with correct data
- [ ] Export Excel downloads with correct data
- [ ] Export respects filters
- [ ] Export respects selection (if items selected)
- [ ] Audit logs created for all operations

---

## 📦 Modules Status

| Module | Backend | Frontend | Status |
|--------|---------|----------|--------|
| Companies | ✅ Complete | 🔄 Pending | Pattern Established |
| Products | 🔄 Pending | 🔄 Pending | Use Pattern |
| Warehouses | 🔄 Pending | 🔄 Pending | Use Pattern |
| Banks | 🔄 Pending | 🔄 Pending | Use Pattern |
| PI | 🔄 Pending | 🔄 Pending | Use Pattern |
| PO | 🔄 Pending | 🔄 Pending | Use Pattern |
| Inward Stock - Pickup | 🔄 Pending | 🔄 Pending | Use Pattern |
| Inward Stock - Warehouse | 🔄 Pending | 🔄 Pending | Use Pattern |
| Inward Stock - Direct | 🔄 Pending | 🔄 Pending | Use Pattern |
| Outward Stock - Dispatch | 🔄 Pending | 🔄 Pending | Use Pattern |
| Outward Stock - Export | 🔄 Pending | 🔄 Pending | Use Pattern |
| Outward Stock - Direct | 🔄 Pending | 🔄 Pending | Use Pattern |
| Stock Summary | 🔄 Pending | 🔄 Pending | Use Pattern |
| Customer Management | 🔄 Pending | 🔄 Pending | Use Pattern |
| Purchase Analysis | 🔄 Pending | 🔄 Pending | Use Pattern |
| Payment Tracking | 🔄 Pending | 🔄 Pending | Use Pattern |
| Expenses Calculation | 🔄 Pending | 🔄 Pending | Use Pattern |
| P&L Report | 🔄 Pending | 🔄 Pending | Use Pattern |

---

## 💡 Implementation Notes

1. **Start with simpler modules** (Companies, Products, Warehouses, Banks)
2. **Test thoroughly** before moving to complex modules
3. **Maintain consistency** in UI/UX across all modules
4. **Document special cases** for each module
5. **Use the pattern** - don't reinvent for each module
6. **Test edge cases** - empty data, all filtered out, large datasets

---

## 🚀 Next Steps

1. Complete backend for remaining modules using the pattern
2. Implement frontend for all modules using reusable components
3. Add comprehensive testing
4. Create screen recordings showing functionality
5. Generate export samples (CSV + Excel)
6. Deploy and verify in production

---

**Foundation Status:** ✅ Complete
- Reusable components created
- Backend pattern established
- Export utilities implemented
- Companies module fully implemented as reference

**Time Estimate for Remaining Modules:** 
- Backend: ~2-3 hours per module
- Frontend: ~1-2 hours per module  
- Testing: ~30 min per module
- **Total:** ~60-80 hours for all 18 modules

**Recommendation:** Implement in phases:
- **Phase 1:** Master data (Companies, Products, Warehouses, Banks) - 8 hours
- **Phase 2:** Transactions (PI, PO) - 6 hours
- **Phase 3:** Stock operations (Inward, Outward, Pickup) - 12 hours
- **Phase 4:** Reports (Stock Summary, Purchase Analysis, etc.) - 10 hours
