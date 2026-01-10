import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Plus, Edit, Trash2, Search } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import BulkActionToolbar from '../components/BulkActionToolbar';
import DeleteConfirmDialog from '../components/DeleteConfirmDialog';
import { exportToCSV, exportToExcel, formatDataForExport } from '../utils/exportUtils';

const Warehouses = () => {
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [warehouseToDelete, setWarehouseToDelete] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    address: '',
    city: '',
    country: '',
    contact_details: '',
  });
  
  const { toast } = useToast();
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchWarehouses();
  }, []);

  const fetchWarehouses = async () => {
    try {
      const response = await api.get('/warehouses');
      setWarehouses(response.data);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch warehouses', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const filteredData = warehouses.filter((warehouse) =>
    Object.values(warehouse).some((value) =>
      String(value).toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  // Bulk operation handlers
  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedIds(filteredData.map(item => item.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectRow = (id, checked) => {
    if (checked) {
      setSelectedIds([...selectedIds, id]);
    } else {
      setSelectedIds(selectedIds.filter(selectedId => selectedId !== id));
    }
  };

  const handleExportCSV = () => {
    const dataToExport = selectedIds.length > 0
      ? filteredData.filter(item => selectedIds.includes(item.id))
      : filteredData;
    
    const fieldMapping = {
      'name': 'Name',
      'address': 'Address',
      'city': 'City',
      'country': 'Country',
      'contact_details': 'Contact Details',
      'is_active': 'Status'
    };
    
    exportToCSV(formatDataForExport(dataToExport, fieldMapping), 'warehouses');
    toast({ title: 'Success', description: 'Warehouses exported to CSV' });
  };

  const handleExportExcel = () => {
    const dataToExport = selectedIds.length > 0
      ? filteredData.filter(item => selectedIds.includes(item.id))
      : filteredData;
    
    const fieldMapping = {
      'name': 'Name',
      'address': 'Address',
      'city': 'City',
      'country': 'Country',
      'contact_details': 'Contact Details',
      'is_active': 'Status'
    };
    
    exportToExcel(formatDataForExport(dataToExport, fieldMapping), 'warehouses', 'Warehouses');
    toast({ title: 'Success', description: 'Warehouses exported to Excel' });
  };

  const handleBulkDelete = async () => {
    if (!window.confirm(`Delete ${selectedIds.length} selected warehouses? This action cannot be undone.`)) {
      return;
    }
    
    try {
      const response = await api.post('/warehouses/bulk-delete', { ids: selectedIds });
      
      if (response.data.deleted_count > 0) {
        toast({
          title: 'Success',
          description: `${response.data.deleted_count} warehouse(s) deleted successfully`,
        });
      }
      
      if (response.data.failed_count > 0) {
        toast({
          title: 'Partial Success',
          description: `${response.data.failed_count} warehouse(s) could not be deleted`,
          variant: 'destructive'
        });
        console.log('Failed deletions:', response.data.failed);
      }
      
      setSelectedIds([]);
      fetchWarehouses();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete warehouses',
        variant: 'destructive'
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingWarehouse) {
        await api.put(`/warehouses/${editingWarehouse.id}`, formData);
        toast({ title: 'Success', description: 'Warehouse updated successfully' });
      } else {
        await api.post('/warehouses', formData);
        toast({ title: 'Success', description: 'Warehouse created successfully' });
      }
      fetchWarehouses();
      setDialogOpen(false);
      resetForm();
    } catch (error) {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Operation failed', variant: 'destructive' });
    }
  };

  const handleEdit = (warehouse) => {
    setEditingWarehouse(warehouse);
    setFormData({
      name: warehouse.name,
      address: warehouse.address || '',
      city: warehouse.city || '',
      country: warehouse.country || '',
      contact_details: warehouse.contact_details || '',
    });
    setDialogOpen(true);
  };

  const handleDeleteClick = (warehouse) => {
    setWarehouseToDelete(warehouse);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    try {
      await api.delete(`/warehouses/${warehouseToDelete.id}`);
      toast({ title: 'Success', description: 'Warehouse deleted successfully' });
      setDeleteDialogOpen(false);
      setWarehouseToDelete(null);
      fetchWarehouses();
    } catch (error) {
      toast({ 
        title: 'Error', 
        description: error.response?.data?.detail || 'Failed to delete warehouse', 
        variant: 'destructive' 
      });
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      address: '',
      city: '',
      country: '',
      contact_details: '',
    });
    setEditingWarehouse(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Warehouses</h1>
          <p className="text-slate-600 mt-1">Manage warehouse locations</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={resetForm}>
              <Plus size={20} className="mr-2" />
              Add Warehouse
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{editingWarehouse ? 'Edit Warehouse' : 'Add New Warehouse'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label htmlFor="name">Warehouse Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="col-span-2">
                  <Label htmlFor="address">Address</Label>
                  <Textarea
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    rows={3}
                  />
                </div>
                <div>
                  <Label htmlFor="city">City</Label>
                  <Input
                    id="city"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="country">Country</Label>
                  <Input
                    id="country"
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                  />
                </div>
                <div className="col-span-2">
                  <Label htmlFor="contact_details">Contact Details</Label>
                  <Input
                    id="contact_details"
                    value={formData.contact_details}
                    onChange={(e) => setFormData({ ...formData, contact_details: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                  {editingWarehouse ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <Input
            placeholder="Search warehouses..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Bulk Action Toolbar */}
      <BulkActionToolbar
        selectedCount={selectedIds.length}
        onClearSelection={() => setSelectedIds([])}
        onBulkDelete={handleBulkDelete}
        onExportCSV={handleExportCSV}
        onExportExcel={handleExportExcel}
      />

      {/* Warehouses Table */}
      <div className="border rounded-lg overflow-hidden">
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
              <TableHead>Name</TableHead>
              <TableHead>Address</TableHead>
              <TableHead>City</TableHead>
              <TableHead>Country</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-slate-500 py-8">
                  No warehouses available
                </TableCell>
              </TableRow>
            ) : (
              filteredData.map((warehouse) => (
                <TableRow key={warehouse.id}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(warehouse.id)}
                      onChange={(e) => handleSelectRow(warehouse.id, e.target.checked)}
                      className="rounded border-gray-300"
                    />
                  </TableCell>
                  <TableCell className="font-medium">{warehouse.name}</TableCell>
                  <TableCell>{warehouse.address || '-'}</TableCell>
                  <TableCell>{warehouse.city || '-'}</TableCell>
                  <TableCell>{warehouse.country || '-'}</TableCell>
                  <TableCell>{warehouse.contact_details || '-'}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs ${warehouse.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {warehouse.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleEdit(warehouse)}
                        className="text-blue-600 hover:text-blue-800 p-1"
                        title="Edit warehouse"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteClick(warehouse)}
                        className="text-red-600 hover:text-red-800 p-1"
                        title="Delete warehouse"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        isOpen={deleteDialogOpen}
        onClose={() => {
          setDeleteDialogOpen(false);
          setWarehouseToDelete(null);
        }}
        onConfirm={handleDeleteConfirm}
        itemName={warehouseToDelete?.name}
        message="Are you sure you want to delete this warehouse? This action cannot be undone. The warehouse will only be deleted if it's not referenced in any Inward or Outward records."
      />
    </div>
  );
};

export default Warehouses;
