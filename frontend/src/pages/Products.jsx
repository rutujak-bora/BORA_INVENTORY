import React, { useEffect, useState } from 'react';
import api, { API_BASE } from '../utils/api';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Plus, Edit, Trash2, Search } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import BulkActionToolbar from '../components/BulkActionToolbar';
import DeleteConfirmDialog from '../components/DeleteConfirmDialog';
import { exportToCSV, exportToExcel, formatDataForExport } from '../utils/exportUtils';

const Products = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [productToDelete, setProductToDelete] = useState(null);
  
  const [formData, setFormData] = useState({
    sku_name: '',
    category: '',
    brand: '',
    hsn_sac: '',
    country_of_origin: '',
    color: '',
    specification: '',
    feature: ''
  });
  
  const { toast } = useToast();
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch products', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const filteredData = products.filter((product) =>
    Object.values(product).some((value) =>
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
      'sku_name': 'SKU Name',
      'category': 'Category',
      'brand': 'Brand',
      'hsn_sac': 'HSN/SAC',
      'country_of_origin': 'Country of Origin',
      'color': 'Color',
      'specification': 'Specification',
      'feature': 'Feature',
      'is_active': 'Status'
    };
    
    exportToCSV(formatDataForExport(dataToExport, fieldMapping), 'products');
    toast({ title: 'Success', description: 'Products exported to CSV' });
  };

  const handleExportExcel = () => {
    const dataToExport = selectedIds.length > 0
      ? filteredData.filter(item => selectedIds.includes(item.id))
      : filteredData;
    
    const fieldMapping = {
      'sku_name': 'SKU Name',
      'category': 'Category',
      'brand': 'Brand',
      'hsn_sac': 'HSN/SAC',
      'country_of_origin': 'Country of Origin',
      'color': 'Color',
      'specification': 'Specification',
      'feature': 'Feature',
      'is_active': 'Status'
    };
    
    exportToExcel(formatDataForExport(dataToExport, fieldMapping), 'products', 'Products');
    toast({ title: 'Success', description: 'Products exported to Excel' });
  };

  const handleBulkDelete = async () => {
    if (!window.confirm(`Delete ${selectedIds.length} selected products? This action cannot be undone.`)) {
      return;
    }
    
    try {
      const response = await api.post('/products/bulk-delete', { ids: selectedIds });
      
      if (response.data.deleted_count > 0) {
        toast({
          title: 'Success',
          description: `${response.data.deleted_count} product(s) deleted successfully`,
        });
      }
      
      if (response.data.failed_count > 0) {
        const failedReasons = response.data.failed.map(f => `${f.id}: ${f.reason}`).join('\n');
        toast({
          title: 'Partial Success',
          description: `${response.data.failed_count} product(s) could not be deleted`,
          variant: 'destructive'
        });
        console.log('Failed deletions:', failedReasons);
      }
      
      setSelectedIds([]);
      fetchProducts();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete products',
        variant: 'destructive'
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        specification: formData.specification || null,
      };
      if (editingProduct) {
        await api.put(`/products/${editingProduct.id}`, payload);
        toast({ title: 'Success', description: 'Product updated successfully' });
      } else {
        await api.post('/products', payload);
        toast({ title: 'Success', description: 'Product created successfully' });
      }
      fetchProducts();
      setDialogOpen(false);
      resetForm();
    } catch (error) {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Operation failed', variant: 'destructive' });
    }
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      sku_name: product.sku_name,
      category: product.category || '',
      brand: product.brand || '',
      hsn_sac: product.hsn_sac || '',
      country_of_origin: product.country_of_origin || '',
      color: product.color || '',
      specification: product.specification || '',
      feature: product.feature || '',
    });
    setDialogOpen(true);
  };

  const handleDeleteClick = (product) => {
    setProductToDelete(product);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    try {
      await api.delete(`/products/${productToDelete.id}`);
      toast({ title: 'Success', description: 'Product deleted successfully' });
      setDeleteDialogOpen(false);
      setProductToDelete(null);
      fetchProducts();
    } catch (error) {
      toast({ 
        title: 'Error', 
        description: error.response?.data?.detail || 'Failed to delete product', 
        variant: 'destructive' 
      });
    }
  };

  const handleBulkUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formDataUpload = new FormData();
    formDataUpload.append('file', file);

    try {
      await api.post('/products/bulk-upload', formDataUpload, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast({ title: 'Success', description: 'Products uploaded successfully' });
      fetchProducts();
    } catch (error) {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Bulk upload failed', variant: 'destructive' });
    }
  };

  const resetForm = () => {
    setFormData({
      sku_name: '',
      category: '',
      brand: '',
      hsn_sac: '',
      country_of_origin: '',
      color: '',
      specification: '',
      feature: ''
    });
    setEditingProduct(null);
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
          <h1 className="text-3xl font-bold text-slate-900">Products / SKU</h1>
          <p className="text-slate-600 mt-1">Manage your product master data</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => window.open(`${API_BASE}/templates/products`, '_blank')}
            className="border-emerald-600 text-emerald-600 hover:bg-emerald-50"
          >
            Download Template
          </Button>
          <input
            type="file"
            id="product-bulk-upload"
            accept=".xlsx,.xls,.csv"
            onChange={handleBulkUpload}
            className="hidden"
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById('product-bulk-upload').click()}
          >
            <Plus size={20} className="mr-2" />
            Bulk Upload (Excel)
          </Button>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={resetForm}>
                <Plus size={20} className="mr-2" />
                Add Product
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{editingProduct ? 'Edit Product' : 'Add New Product'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="sku_name">SKU Name *</Label>
                    <Input
                      id="sku_name"
                      value={formData.sku_name}
                      onChange={(e) => setFormData({ ...formData, sku_name: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="category">Category</Label>
                    <Input
                      id="category"
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="brand">Brand</Label>
                    <Input
                      id="brand"
                      value={formData.brand}
                      onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="hsn_sac">HSN/SAC</Label>
                    <Input
                      id="hsn_sac"
                      value={formData.hsn_sac}
                      onChange={(e) => setFormData({ ...formData, hsn_sac: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="country_of_origin">Country of Origin</Label>
                    <Input
                      id="country_of_origin"
                      value={formData.country_of_origin}
                      onChange={(e) => setFormData({ ...formData, country_of_origin: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="color">Color</Label>
                    <Input
                      id="color"
                      value={formData.color}
                      onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="specification">Specification</Label>
                    <Input
                      id="specification"
                      value={formData.specification}
                      onChange={(e) => setFormData({ ...formData, specification: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="feature">Feature</Label>
                    <Input
                      id="feature"
                      value={formData.feature}
                      onChange={(e) => setFormData({ ...formData, feature: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                    {editingProduct ? 'Update' : 'Create'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <Input
            placeholder="Search products..."
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

      {/* Products Table */}
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
              <TableHead>SKU Name</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Brand</TableHead>
              <TableHead>HSN/SAC</TableHead>
              <TableHead>Country</TableHead>
              <TableHead>Color</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-slate-500 py-8">
                  No products available
                </TableCell>
              </TableRow>
            ) : (
              filteredData.map((product) => (
                <TableRow key={product.id}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(product.id)}
                      onChange={(e) => handleSelectRow(product.id, e.target.checked)}
                      className="rounded border-gray-300"
                    />
                  </TableCell>
                  <TableCell className="font-medium">{product.sku_name}</TableCell>
                  <TableCell>{product.category || '-'}</TableCell>
                  <TableCell>{product.brand || '-'}</TableCell>
                  <TableCell>{product.hsn_sac || '-'}</TableCell>
                  <TableCell>{product.country_of_origin || '-'}</TableCell>
                  <TableCell>{product.color || '-'}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs ${product.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {product.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleEdit(product)}
                        className="text-blue-600 hover:text-blue-800 p-1"
                        title="Edit product"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteClick(product)}
                        className="text-red-600 hover:text-red-800 p-1"
                        title="Delete product"
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
          setProductToDelete(null);
        }}
        onConfirm={handleDeleteConfirm}
        itemName={productToDelete?.sku_name}
        message="Are you sure you want to delete this product? This action cannot be undone. The product will only be deleted if it's not referenced in any PI, PO, Inward, or Outward records."
      />
    </div>
  );
};

export default Products;
