import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { SearchableSelect } from '../components/SearchableSelect';
import { Plus, Trash2, Download, Upload, X, Eye, Search, Filter } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Card, CardContent } from '../components/ui/card';

const PerformaInvoice = () => {
  const [pis, setPis] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [editingPI, setEditingPI] = useState(null);
  const [viewingPI, setViewingPI] = useState(null);
  const [selectedPIs, setSelectedPIs] = useState([]);

  // Search and Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    status: 'all',
    company: 'all'
  });
  const [filteredPIs, setFilteredPIs] = useState([]);

  const [formData, setFormData] = useState({
    company_id: '',
    voucher_no: '',
    date: new Date().toISOString().split('T')[0],
    consignee: '',
    buyer: '',
    status: 'Pending',
    line_items: [
      {
        product_id: '',
        product_name: '',
        sku: '',
        category: '',
        brand: '',
        hsn_sac: '',
        made_in: '',
        quantity: 0,
        rate: 0,
        amount: 0
      }
    ]
  });

  const { toast } = useToast();

  // Use custom hook to suppress ResizeObserver errors
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchData();
  }, []);

  // Apply search and filters
  useEffect(() => {
    let filtered = [...pis];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(pi =>
        pi.voucher_no?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        pi.consignee?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        pi.buyer?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        pi.line_items?.some(item =>
          item.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.sku?.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }

    // Date range filter
    if (filters.dateFrom) {
      filtered = filtered.filter(pi => new Date(pi.date) >= new Date(filters.dateFrom));
    }
    if (filters.dateTo) {
      filtered = filtered.filter(pi => new Date(pi.date) <= new Date(filters.dateTo));
    }

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(pi => pi.status?.toLowerCase() === filters.status.toLowerCase());
    }

    // Company filter
    if (filters.company !== 'all') {
      filtered = filtered.filter(pi => pi.company_id === filters.company);
    }

    setFilteredPIs(filtered);
  }, [pis, searchTerm, filters]);

  const fetchData = async () => {
    try {
      const [pisRes, companiesRes, productsRes] = await Promise.all([
        api.get('/pi'),
        api.get('/companies'),
        api.get('/products')
      ]);
      setPis(pisRes.data);
      setCompanies(companiesRes.data);
      setProducts(productsRes.data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch data',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  // Calculate totals for filtered data
  const calculateTotals = () => {
    const totalQuantity = filteredPIs.reduce((sum, pi) => {
      const piTotal = pi.line_items?.reduce((itemSum, item) => itemSum + (parseFloat(item.quantity) || 0), 0) || 0;
      return sum + piTotal;
    }, 0);

    const totalAmount = filteredPIs.reduce((sum, pi) => {
      const piTotal = pi.line_items?.reduce((itemSum, item) => itemSum + (parseFloat(item.amount) || 0), 0) || 0;
      return sum + piTotal;
    }, 0);

    return { totalQuantity, totalAmount: totalAmount.toFixed(2) };
  };

  const resetFilters = () => {
    setSearchTerm('');
    setFilters({
      dateFrom: '',
      dateTo: '',
      status: 'all',
      company: 'all'
    });
  };

  const handleSKUSelect = (index, productId) => {
    const product = products.find(p => p.id === productId);
    if (product) {
      const newLineItems = [...formData.line_items];
      // Only auto-fill Category, Brand, HSN/SAC, Made In - NOT Product Name, Quantity, Rate
      newLineItems[index] = {
        ...newLineItems[index],
        product_id: product.id,
        sku: product.sku_name,
        category: product.category || '',
        brand: product.brand || '',
        hsn_sac: product.hsn_sac || '',
        made_in: product.country_of_origin || '',
        // Keep existing quantity and rate values
        amount: newLineItems[index].quantity * newLineItems[index].rate
      };
      setFormData({ ...formData, line_items: newLineItems });
    }
  };

  const handleLineItemChange = (index, field, value) => {
    const newLineItems = [...formData.line_items];
    newLineItems[index][field] = value;

    // Auto-calculate amount
    if (field === 'quantity' || field === 'rate') {
      newLineItems[index].amount = newLineItems[index].quantity * newLineItems[index].rate;
    }

    setFormData({ ...formData, line_items: newLineItems });
  };

  const addLineItem = () => {
    setFormData({
      ...formData,
      line_items: [
        ...formData.line_items,
        {
          product_id: '',
          product_name: '',
          sku: '',
          category: '',
          brand: '',
          hsn_sac: '',
          made_in: '',
          quantity: 0,
          rate: 0,
          amount: 0
        }
      ]
    });
  };

  const removeLineItem = (index) => {
    if (formData.line_items.length > 1) {
      const newLineItems = formData.line_items.filter((_, i) => i !== index);
      setFormData({ ...formData, line_items: newLineItems });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingPI) {
        await api.put(`/pi/${editingPI.id}`, formData);
        toast({ title: 'Success', description: 'PI updated successfully' });
      } else {
        await api.post('/pi', formData);
        toast({ title: 'Success', description: 'PI created successfully' });
      }
      fetchData();
      setDialogOpen(false);
      resetForm();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Operation failed',
        variant: 'destructive',
      });
    }
  };

  const handleView = async (pi) => {
    try {
      const fullPI = await api.get(`/pi/${pi.id}`);
      setViewingPI(fullPI.data);
      setViewDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch PI details', variant: 'destructive' });
    }
  };

  const handleEdit = async (pi) => {
    const fullPI = await api.get(`/pi/${pi.id}`);
    setEditingPI(fullPI.data);
    setFormData({
      company_id: fullPI.data.company_id,
      voucher_no: fullPI.data.voucher_no,
      date: fullPI.data.date.split('T')[0],
      consignee: fullPI.data.consignee || '',
      buyer: fullPI.data.buyer || '',
      status: fullPI.data.status,
      line_items: fullPI.data.line_items || []
    });
    setDialogOpen(true);
  };

  const handleDelete = async (pi) => {
    if (window.confirm('Are you sure you want to delete this PI?')) {
      try {
        await api.delete(`/pi/${pi.id}`);
        toast({ title: 'Success', description: 'PI deleted successfully' });
        fetchData();
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Failed to delete PI',
          variant: 'destructive',
        });
      }
    }
  };

  const handleBulkUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/pi/bulk', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast({ title: 'Success', description: response.data.message });
      fetchData();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Bulk upload failed',
        variant: 'destructive',
      });
    }
    e.target.value = '';
  };

  const handleExport = async () => {
    if (selectedPIs.length === 0) {
      toast({ title: 'Warning', description: 'Please select PIs to export', variant: 'destructive' });
      return;
    }

    try {
      const response = await api.post('/pi/export', selectedPIs, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'PI_Export.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to export PIs', variant: 'destructive' });
    }
  };

  const togglePISelection = (piId) => {
    setSelectedPIs(prev =>
      prev.includes(piId) ? prev.filter(id => id !== piId) : [...prev, piId]
    );
  };

  const resetForm = () => {
    setFormData({
      company_id: '',
      voucher_no: '',
      date: new Date().toISOString().split('T')[0],
      consignee: '',
      buyer: '',
      status: 'Pending',
      line_items: [{
        product_id: '',
        product_name: '',
        sku: '',
        category: '',
        brand: '',
        hsn_sac: '',
        made_in: '',
        quantity: 0,
        rate: 0,
        amount: 0
      }]
    });
    setEditingPI(null);
  };

  const getTotalAmount = () => {
    return formData.line_items.reduce((sum, item) => sum + (item.amount || 0), 0).toFixed(2);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="pi-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Performa Invoice (PI)</h1>
          <p className="text-slate-600 mt-1">Manage performa invoices with multi-line items</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => window.open(`${window.location.origin}/api/templates/pi`, '_blank')}
            data-testid="download-pi-template-btn"
            className="border-emerald-600 text-emerald-600 hover:bg-emerald-50"
          >
            Download Template
          </Button>
          <input
            type="file"
            id="pi-bulk-upload"
            accept=".xlsx,.xls,.csv"
            onChange={handleBulkUpload}
            className="hidden"
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById('pi-bulk-upload').click()}
            data-testid="pi-bulk-upload-btn"
          >
            <Upload size={20} className="mr-2" />
            Bulk Upload
          </Button>
          {selectedPIs.length > 0 && (
            <Button
              variant="outline"
              onClick={handleExport}
              className="border-blue-600 text-blue-600"
            >
              <Download size={20} className="mr-2" />
              Export ({selectedPIs.length})
            </Button>
          )}
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button
                className="bg-blue-600 hover:bg-blue-700 text-white"
                onClick={resetForm}
                data-testid="add-pi-btn"
              >
                <Plus size={20} className="mr-2" />
                Create PI
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{editingPI ? 'Edit PI' : 'Create New PI'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* PI Header */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label>Company *</Label>
                    <Select
                      value={formData.company_id}
                      onValueChange={(value) => {
                        // Add a small delay to prevent rapid state updates that can cause ResizeObserver errors
                        setTimeout(() => {
                          setFormData({ ...formData, company_id: value });
                        }, 0);
                      }}
                      required
                    >
                      <SelectTrigger data-testid="pi-company-select">
                        <SelectValue placeholder="Select company" />
                      </SelectTrigger>
                      <SelectContent className="max-h-60 overflow-y-auto">
                        {companies.map(company => (
                          <SelectItem key={company.id} value={company.id}>
                            {company.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Voucher No *</Label>
                    <Input
                      value={formData.voucher_no}
                      onChange={(e) => setFormData({ ...formData, voucher_no: e.target.value })}
                      required
                      data-testid="pi-voucher-input"
                    />
                  </div>
                  <div>
                    <Label>Date *</Label>
                    <Input
                      type="date"
                      value={formData.date}
                      onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                      required
                      data-testid="pi-date-input"
                    />
                  </div>
                  <div>
                    <Label>Consignee (Ship To)</Label>
                    <Input
                      value={formData.consignee}
                      onChange={(e) => setFormData({ ...formData, consignee: e.target.value })}
                      data-testid="pi-consignee-input"
                    />
                  </div>
                  <div>
                    <Label>Buyer (Bill To)</Label>
                    <Input
                      value={formData.buyer}
                      onChange={(e) => setFormData({ ...formData, buyer: e.target.value })}
                      data-testid="pi-buyer-input"
                    />
                  </div>
                  <div>
                    <Label>Status</Label>
                    <Select
                      value={formData.status}
                      onValueChange={(value) => {
                        // Add a small delay to prevent rapid state updates that can cause ResizeObserver errors
                        setTimeout(() => {
                          setFormData({ ...formData, status: value });
                        }, 0);
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="max-h-60 overflow-y-auto">
                        <SelectItem value="Pending">Pending</SelectItem>
                        <SelectItem value="In Progress">In Progress</SelectItem>
                        <SelectItem value="Completed">Completed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Line Items */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <Label className="text-lg font-semibold">Line Items</Label>
                    <Button type="button" variant="outline" size="sm" onClick={addLineItem}>
                      <Plus size={16} className="mr-1" />
                      Add Item
                    </Button>
                  </div>

                  <div className="space-y-4">
                    {formData.line_items.map((item, index) => (
                      <div key={index} className="border rounded-lg p-4 bg-slate-50">
                        <div className="flex items-center justify-between mb-3">
                          <span className="font-medium text-slate-700">Item {index + 1}</span>
                          {formData.line_items.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => removeLineItem(index)}
                            >
                              <X size={16} className="text-red-600" />
                            </Button>
                          )}
                        </div>

                        <div className="grid grid-cols-4 gap-3">
                          <div className="col-span-2">
                            <Label>Product Name *</Label>
                            <Input
                              value={item.product_name}
                              onChange={(e) => handleLineItemChange(index, 'product_name', e.target.value)}
                              placeholder="Enter product name"
                              required
                            />
                          </div>
                          <div className="col-span-2">
                            <Label>SKU</Label>
                            {/* <SearchableSelect
                              value={item.product_id}
                              onValueChange={(value) => handleSKUSelect(index, value)}
                              options={products.map(p => ({ value: p.id, label: p.sku_name }))}
                              placeholder="Search and select SKU"
                              searchPlaceholder="Type to search SKU..."
                            /> */}

                            <Input
                              value={item.sku}
                              onChange={(e) => handleLineItemChange(index, 'sku', e.target.value)}
                              placeholder="Enter sku value"
                              required
                            />
                          </div>
                          <div>
                            <Label>Category </Label>
                            <Input value={item.category}
                              onChange={(e) => handleLineItemChange(index, 'category', e.target.value)}
                              className="bg-gray-100" />
                          </div>
                          <div>
                            <Label>Brand</Label>
                            <Input value={item.brand}
                              onChange={(e) => handleLineItemChange(index, 'brand', e.target.value)}
                              className="bg-gray-100" />
                          </div>
                          <div>
                            <Label>HSN/SAC</Label>
                            <Input value={item.hsn_sac}
                              onChange={(e) => handleLineItemChange(index, 'hsn_sac', e.target.value)}
                              className="bg-gray-100" />
                          </div>
                          <div>
                            <Label>Made In </Label>
                            <Input value={item.made_in}
                              onChange={(e) => handleLineItemChange(index, 'made_in', e.target.value)}
                              className="bg-gray-100" />
                          </div>
                          <div>
                            <Label>Quantity *</Label>
                            <Input
                              type="number"
                              step="0.01"
                              value={item.quantity || ''}
                              onChange={(e) => handleLineItemChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                              placeholder="Enter quantity"
                              required
                            />
                          </div>
                          <div>
                            <Label>Rate *</Label>
                            <Input
                              type="number"
                              step="0.01"
                              value={item.rate || ''}
                              onChange={(e) => handleLineItemChange(index, 'rate', parseFloat(e.target.value) || 0)}
                              placeholder="Enter rate"
                              required
                            />
                          </div>
                          <div>
                            <Label>Amount (Auto-calculated)</Label>
                            <Input
                              value={`₹${item.amount.toFixed(2)}`}
                              disabled
                              className="bg-blue-50 font-semibold"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 flex justify-end">
                    <div className="bg-blue-100 px-6 py-3 rounded-lg">
                      <span className="text-sm text-slate-700">Total Amount: </span>
                      <span className="text-xl font-bold text-blue-900">₹{getTotalAmount()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" className="bg-blue-600 hover:bg-blue-700" data-testid="save-pi-btn">
                    {editingPI ? 'Update PI' : 'Create PI'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* View PI Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>View Performa Invoice Details</DialogTitle>
          </DialogHeader>

          {viewingPI && (
            <div className="space-y-6">
              {/* PI Header Information */}
              <div className="bg-slate-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">PI Information</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Company</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingPI.company ? viewingPI.company.name : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Voucher No</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-semibold">
                      {viewingPI.voucher_no}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Date</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {new Date(viewingPI.date).toLocaleDateString()}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Status</Label>
                    <div className="mt-1">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${viewingPI.status === 'Completed' ? 'bg-green-100 text-green-800' :
                          viewingPI.status === 'In Progress' ? 'bg-blue-100 text-blue-800' :
                            'bg-yellow-100 text-yellow-800'
                        }`}>
                        {viewingPI.status}
                      </span>
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Buyer</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingPI.buyer || 'Not specified'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Consignee</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingPI.consignee || 'Not specified'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Line Items */}
              <div>
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Line Items</h3>
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-slate-100">
                      <tr>
                        <th className="text-left p-3 font-medium text-slate-700">Product Name</th>
                        <th className="text-left p-3 font-medium text-slate-700">SKU</th>
                        <th className="text-left p-3 font-medium text-slate-700">Category</th>
                        <th className="text-left p-3 font-medium text-slate-700">Brand</th>
                        <th className="text-left p-3 font-medium text-slate-700">Made In</th>
                        <th className="text-right p-3 font-medium text-slate-700">Quantity</th>
                        <th className="text-right p-3 font-medium text-slate-700">Rate</th>
                        <th className="text-right p-3 font-medium text-slate-700">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {viewingPI.line_items?.map((item, index) => (
                        <tr key={index} className="border-t">
                          <td className="p-3">{item.product_name}</td>
                          <td className="p-3 font-mono text-sm">{item.sku}</td>
                          <td className="p-3">{item.category || '-'}</td>
                          <td className="p-3">{item.brand || '-'}</td>
                          <td className="p-3">{item.made_in || '-'}</td>
                          <td className="p-3 text-right">{item.quantity}</td>
                          <td className="p-3 text-right">₹{item.rate?.toFixed(2)}</td>
                          <td className="p-3 text-right font-semibold">₹{item.amount?.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Total Amount */}
                <div className="mt-4 flex justify-end">
                  <div className="bg-blue-100 px-6 py-3 rounded-lg">
                    <span className="text-sm text-slate-700">Total Amount: </span>
                    <span className="text-xl font-bold text-blue-900">
                      ₹{viewingPI.line_items?.reduce((sum, item) => sum + (item.amount || 0), 0).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Dialog Actions */}
              <div className="flex justify-end gap-2 border-t pt-4">
                <Button variant="outline" onClick={() => setViewDialogOpen(false)}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Filter size={18} className="text-slate-600" />
            <h3 className="font-semibold text-slate-900">Search & Filters</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Search Bar */}
            <div>
              <Label className="text-xs">Search</Label>
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                <Input
                  placeholder="Search by voucher, customer, product..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>

            {/* Date From */}
            <div>
              <Label className="text-xs">From Date</Label>
              <Input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
              />
            </div>

            {/* Date To */}
            <div>
              <Label className="text-xs">To Date</Label>
              <Input
                type="date"
                value={filters.dateTo}
                onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
              />
            </div>

            {/* Status Filter */}
            <div>
              <Label className="text-xs">Status</Label>
              <select
                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            {/* Company Filter */}
            <div>
              <Label className="text-xs">Company</Label>
              <select
                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
                value={filters.company}
                onChange={(e) => setFilters({ ...filters, company: e.target.value })}
              >
                <option value="all">All Companies</option>
                {companies.map(company => (
                  <option key={company.id} value={company.id}>{company.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Reset and Results Count */}
          <div className="flex items-center justify-between mt-3 pt-3 border-t">
            <p className="text-sm text-slate-600">
              Showing <span className="font-semibold text-blue-600">{filteredPIs.length}</span> of <span className="font-semibold">{pis.length}</span> records
            </p>
            <Button variant="outline" size="sm" onClick={resetFilters}>
              Reset Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* PI Table */}
      <div className="border rounded-lg overflow-hidden bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedPIs(filteredPIs.map(pi => pi.id));
                    } else {
                      setSelectedPIs([]);
                    }
                  }}
                />
              </TableHead>
              <TableHead>Voucher No</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Consignee</TableHead>
              <TableHead>Buyer</TableHead>
              <TableHead>Products</TableHead>
              <TableHead>Total Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredPIs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-slate-500 py-8">
                  {searchTerm || filters.dateFrom || filters.dateTo || filters.status !== 'all' || filters.company !== 'all'
                    ? 'No PIs match your search/filter criteria.'
                    : 'No PIs found. Create your first PI to get started.'}
                </TableCell>
              </TableRow>
            ) : (
              filteredPIs.map((pi) => (
                <TableRow key={pi.id}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedPIs.includes(pi.id)}
                      onChange={() => togglePISelection(pi.id)}
                    />
                  </TableCell>
                  <TableCell className="font-medium">{pi.voucher_no}</TableCell>
                  <TableCell>{new Date(pi.date).toLocaleDateString()}</TableCell>
                  <TableCell>{pi.consignee || '-'}</TableCell>
                  <TableCell>{pi.buyer || '-'}</TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {pi.line_items_count} items
                      {pi.line_items && pi.line_items.length > 0 && (
                        <div className="text-xs text-slate-500">
                          {pi.line_items[0].product_name}
                          {pi.line_items.length > 1 && ` +${pi.line_items.length - 1} more`}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-semibold">₹{pi.total_amount?.toFixed(2)}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs ${pi.status === 'Completed' ? 'bg-green-100 text-green-800' :
                        pi.status === 'In Progress' ? 'bg-blue-100 text-blue-800' :
                          'bg-yellow-100 text-yellow-800'
                      }`}>
                      {pi.status}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleView(pi)}>
                        <Eye size={16} className="text-blue-600" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(pi)}>
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(pi)}>
                        <Trash2 size={16} className="text-red-600" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
            {filteredPIs.length > 0 && (
              <TableRow className="bg-blue-50 border-t-2 border-blue-400 font-bold">
                <TableCell></TableCell>
                <TableCell colSpan={4} className="text-right text-blue-900">TOTALS:</TableCell>
                <TableCell className="text-blue-900">
                  <div className="text-xs">Total Qty: {calculateTotals().totalQuantity}</div>
                  <div className="text-xs">{filteredPIs.length} PIs</div>
                </TableCell>
                <TableCell className="text-right text-blue-900">₹{calculateTotals().totalAmount}</TableCell>
                <TableCell></TableCell>
                <TableCell></TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default PerformaInvoice;
