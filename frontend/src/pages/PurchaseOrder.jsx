import React, { useEffect, useState } from 'react';
import api, { API_BASE } from '../utils/api';
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

const PurchaseOrder = () => {
  const [pos, setPOs] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [products, setProducts] = useState([]);
  const [pis, setPIs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [editingPO, setEditingPO] = useState(null);
  const [viewingPO, setViewingPO] = useState(null);
  const [selectedPOs, setSelectedPOs] = useState([]);

  // Search and Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    status: 'all',
    company: 'all'
  });
  const [filteredPOs, setFilteredPOs] = useState([]);


  const [formData, setFormData] = useState({
    company_id: '',
    voucher_no: '',
    date: new Date().toISOString().split('T')[0],
    consignee: '',
    supplier: '',
    reference_pi_ids: [],  // Changed to array for multiple PIs
    reference_no_date: '',
    dispatched_through: '',
    destination: '',
    gst_percentage: 0,  // GST % to be entered manually
    tds_percentage: 0,  // TDS % to be entered manually
    status: 'Pending',
    line_items: [{
      product_id: '',
      product_name: '',
      sku: '',
      category: '',
      brand: '',
      hsn_sac: '',
      quantity: 0,
      rate: 0,
      amount: 0,
      gst_value: 0,  // Will be auto-calculated
      tds_value: 0   // Will be auto-calculated
    }]
  });

  const { toast } = useToast();

  // Use custom hook to suppress ResizeObserver errors
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchData();
  }, []);

  // Apply search and filters
  useEffect(() => {
    let filtered = [...pos];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(po =>
        po.po_no?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        po.supplier?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        po.consignee?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        po.line_items?.some(item =>
          item.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.sku?.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }

    // Date range filter
    if (filters.dateFrom) {
      filtered = filtered.filter(po => new Date(po.date) >= new Date(filters.dateFrom));
    }
    if (filters.dateTo) {
      filtered = filtered.filter(po => new Date(po.date) <= new Date(filters.dateTo));
    }

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(po => po.status?.toLowerCase() === filters.status.toLowerCase());
    }

    // Company filter
    if (filters.company !== 'all') {
      filtered = filtered.filter(po => po.company_id === filters.company);
    }

    setFilteredPOs(filtered);
  }, [pos, searchTerm, filters]);

  const fetchData = async () => {
    try {
      const [posRes, companiesRes, productsRes, pisRes] = await Promise.all([
        api.get('/po'),
        api.get('/companies'),
        api.get('/products'),
        api.get('/pi')
      ]);
      setPOs(posRes.data);
      setCompanies(companiesRes.data);
      setProducts(productsRes.data);
      setPIs(pisRes.data);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch data', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  // Calculate totals for filtered data
  const calculateTotals = () => {
    const totalQuantity = filteredPOs.reduce((sum, po) => {
      const poTotal = po.line_items?.reduce((itemSum, item) => itemSum + (parseFloat(item.quantity) || 0), 0) || 0;
      return sum + poTotal;
    }, 0);

    const totalAmount = filteredPOs.reduce((sum, po) => {
      const poTotal = po.line_items?.reduce((itemSum, item) => itemSum + (parseFloat(item.amount) || 0), 0) || 0;
      return sum + poTotal;
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
      newLineItems[index] = {
        ...newLineItems[index],
        product_id: product.id,
        sku: product.sku_name,
        category: product.category || '',
        brand: product.brand || '',
        hsn_sac: product.hsn_sac || '',
        amount: newLineItems[index].quantity * newLineItems[index].rate
      };
      setFormData({ ...formData, line_items: newLineItems });
    }
  };

  const handlePISelect = async (piIds) => {
    // piIds is now an array of selected PI IDs
    if (!piIds || piIds.length === 0) {
      setFormData({
        ...formData,
        reference_pi_ids: [],
        reference_no_date: '',
        line_items: [{
          product_id: '',
          product_name: '',
          sku: '',
          category: '',
          brand: '',
          hsn_sac: '',
          quantity: 0,
          rate: 0,
          amount: 0,
          input_igst: 0,
          tds: 0
        }]
      });
      return;
    }

    try {
      // Fetch all selected PIs
      const selectedPIs = await Promise.all(
        piIds.map(piId => api.get(`/pI/${piId}`))
      );

      // Build reference_no_date string from all PIs
      const piReferences = selectedPIs.map(res => {
        const pi = res.data;
        return `${pi.voucher_no} (${new Date(pi.date).toLocaleDateString()})`;
      }).join(', ');

      // Collect all unique products from all selected PIs with PI quantities
      const allLineItems = [];
      const seenProducts = new Set();
      const piQuantitiesMap = new Map(); // Store PI quantities per product

      selectedPIs.forEach(res => {
        const pi = res.data;
        pi.line_items?.forEach(item => {
          const productKey = item.sku || item.product_id;

          // Aggregate PI quantities for same product
          if (piQuantitiesMap.has(productKey)) {
            piQuantitiesMap.set(productKey, piQuantitiesMap.get(productKey) + (item.quantity || 0));
          } else {
            piQuantitiesMap.set(productKey, item.quantity || 0);
          }

          if (!seenProducts.has(productKey)) {
            seenProducts.add(productKey);
            allLineItems.push({
              product_id: item.product_id,
              product_name: item.product_name,
              sku: item.sku,
              category: item.category || '',
              brand: item.brand || '',
              hsn_sac: item.hsn_sac || '',
              pi_quantity: piQuantitiesMap.get(productKey), // Add PI quantity
              quantity: 0,  // Manual entry (PO Quantity)
              rate: 0,      // Manual entry
              amount: 0,
              input_igst: 0,
              tds: 0
            });
          }
        });
      });

      // Update all items with their PI quantities
      allLineItems.forEach(item => {
        const productKey = item.sku || item.product_id;
        item.pi_quantity = piQuantitiesMap.get(productKey) || 0;
      });

      setFormData({
        ...formData,
        reference_pi_ids: piIds,
        reference_no_date: piReferences,
        line_items: allLineItems.length > 0 ? allLineItems : [{
          product_id: '',
          product_name: '',
          sku: '',
          category: '',
          brand: '',
          hsn_sac: '',
          quantity: 0,
          rate: 0,
          amount: 0,
          input_igst: 0,
          tds: 0
        }]
      });

      toast({
        title: 'Success',
        description: `Products auto-fetched from ${piIds.length} PI(s). Please enter Quantity and Amount manually.`
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch PI details',
        variant: 'destructive'
      });
    }
  };

  const handleLineItemChange = (index, field, value) => {
    const newLineItems = [...formData.line_items];
    newLineItems[index][field] = value;

    // Auto-calculate amount, GST value, and TDS value
    if (field === 'quantity' || field === 'rate') {
      const amount = newLineItems[index].quantity * newLineItems[index].rate;
      newLineItems[index].amount = amount;

      // Calculate GST Value: Amount × (GST % / 100)
      newLineItems[index].gst_value = amount * (formData.gst_percentage / 100);

      // Calculate TDS Value: Amount × (TDS % / 100)
      newLineItems[index].tds_value = amount * (formData.tds_percentage / 100);
    }

    setFormData({ ...formData, line_items: newLineItems });
  };

  // Recalculate all line items when GST% or TDS% changes
  const handlePercentageChange = (field, value) => {
    const percentage = parseFloat(value) || 0;
    const newFormData = { ...formData, [field]: percentage };

    // Recalculate GST and TDS for all line items
    newFormData.line_items = formData.line_items.map(item => {
      const gst_value = item.amount * (field === 'gst_percentage' ? percentage : formData.gst_percentage) / 100;
      const tds_value = item.amount * (field === 'tds_percentage' ? percentage : formData.tds_percentage) / 100;
      return { ...item, gst_value, tds_value };
    });

    setFormData(newFormData);
  };

  const addLineItem = () => {
    setFormData({
      ...formData,
      line_items: [...formData.line_items, {
        product_id: '',
        product_name: '',
        sku: '',
        category: '',
        brand: '',
        hsn_sac: '',
        quantity: 0,
        rate: 0,
        amount: 0,
        input_igst: 0,
        tds: 0
      }]
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
      if (editingPO) {
        await api.put(`/po/${editingPO.id}`, formData);
        toast({ title: 'Success', description: 'PO updated successfully' });
      } else {
        await api.post('/po', formData);
        toast({ title: 'Success', description: 'PO created successfully' });
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

  const handleView = async (po) => {
    try {
      const fullPO = await api.get(`/po/${po.id}`);
      setViewingPO(fullPO.data);
      setViewDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch PO details', variant: 'destructive' });
    }
  };

  const handleEdit = async (po) => {
    const fullPO = await api.get(`/po/${po.id}`);
    setEditingPO(fullPO.data);

    // Support both old single PI and new multiple PIs format
    let reference_pi_ids = fullPO.data.reference_pi_ids || [];
    if (!reference_pi_ids.length && fullPO.data.reference_pi_id) {
      reference_pi_ids = [fullPO.data.reference_pi_id];
    }

    setFormData({
      company_id: fullPO.data.company_id,
      voucher_no: fullPO.data.voucher_no,
      date: fullPO.data.date.split('T')[0],
      consignee: fullPO.data.consignee || '',
      supplier: fullPO.data.supplier || '',
      reference_pi_ids: reference_pi_ids,
      reference_no_date: fullPO.data.reference_no_date || '',
      dispatched_through: fullPO.data.dispatched_through || '',
      destination: fullPO.data.destination || '',
      status: fullPO.data.status,
      line_items: fullPO.data.line_items || []
    });
    setDialogOpen(true);
  };

  const handleDelete = async (po) => {
    if (window.confirm('Are you sure you want to delete this PO?')) {
      try {
        await api.delete(`/po/${po.id}`);
        toast({ title: 'Success', description: 'PO deleted successfully' });
        fetchData();
      } catch (error) {
        toast({ title: 'Error', description: 'Failed to delete PO', variant: 'destructive' });
      }
    }
  };

  const handleBulkUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/po/bulk', formData, {
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
    if (selectedPOs.length === 0) {
      toast({ title: 'Warning', description: 'Please select POs to export', variant: 'destructive' });
      return;
    }

    try {
      const response = await api.post('/po/export', selectedPOs, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'PO_Export.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to export POs', variant: 'destructive' });
    }
  };

  const togglePOSelection = (poId) => {
    setSelectedPOs(prev =>
      prev.includes(poId) ? prev.filter(id => id !== poId) : [...prev, poId]
    );
  };

  const resetForm = () => {
    setFormData({
      company_id: '',
      voucher_no: '',
      date: new Date().toISOString().split('T')[0],
      consignee: '',
      supplier: '',
      reference_pi_ids: [],  // Changed to array
      reference_no_date: '',
      dispatched_through: '',
      destination: '',
      status: 'Pending',
      line_items: [{
        product_id: '',
        product_name: '',
        sku: '',
        category: '',
        brand: '',
        hsn_sac: '',
        quantity: 0,
        rate: 0,
        amount: 0,
        input_igst: 0,
        tds: 0
      }]
    });
    setEditingPO(null);
  };

  const getTotalBasicAmount = () => {
    return formData.line_items.reduce((sum, item) => sum + (item.amount || 0), 0);
  };

  const getTotalGST = () => {
    return formData.line_items.reduce((sum, item) => sum + (item.gst_value || 0), 0);
  };

  const getTotalTDS = () => {
    return formData.line_items.reduce((sum, item) => sum + (item.tds_value || 0), 0);
  };

  const getTotalAmount = () => {
    const basic = getTotalBasicAmount();
    const gst = getTotalGST();
    const tds = getTotalTDS();
    return (basic + gst - tds).toFixed(2);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="po-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Purchase Order (PO)</h1>
          <p className="text-slate-600 mt-1">Manage purchase orders linked to performa invoices</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => window.open(`${API_BASE}/templates/po`, '_blank')}
            data-testid="download-po-template-btn"
            className="border-emerald-600 text-emerald-600 hover:bg-emerald-50"
          >
            Download Template
          </Button>
          <input
            type="file"
            id="po-bulk-upload"
            accept=".xlsx,.xls,.csv"
            onChange={handleBulkUpload}
            className="hidden"
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById('po-bulk-upload').click()}
            data-testid="po-bulk-upload-btn"
          >
            <Upload size={20} className="mr-2" />
            Bulk Upload
          </Button>
          {selectedPOs.length > 0 && (
            <Button
              variant="outline"
              onClick={handleExport}
              className="border-blue-600 text-blue-600"
            >
              <Download size={20} className="mr-2" />
              Export ({selectedPOs.length})
            </Button>
          )}
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button
                className="bg-blue-600 hover:bg-blue-700 text-white"
                onClick={resetForm}
                data-testid="add-po-btn"
              >
                <Plus size={20} className="mr-2" />
                Create PO
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{editingPO ? 'Edit PO' : 'Create New PO'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* PO Header */}
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
                      <SelectTrigger data-testid="po-company-select">
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
                      data-testid="po-voucher-input"
                    />
                  </div>
                  <div>
                    <Label>Date *</Label>
                    <Input
                      type="date"
                      value={formData.date}
                      onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                      required
                      data-testid="po-date-input"
                    />
                  </div>
                  <div>
                    <Label>Consignee (Ship To)</Label>
                    <Input
                      value={formData.consignee}
                      onChange={(e) => setFormData({ ...formData, consignee: e.target.value })}
                      data-testid="po-consignee-input"
                    />
                  </div>
                  <div>
                    <Label>Supplier (Bill From)</Label>
                    <Input
                      value={formData.supplier}
                      onChange={(e) => setFormData({ ...formData, supplier: e.target.value })}
                      data-testid="po-supplier-input"
                    />
                  </div>
                  <div>
                    <Label>Reference PIs (Link to Multiple PIs)</Label>
                    <div className="space-y-2">
                      {/* Multi-select dropdown for PIs */}
                      <Select
                        value="_select_pi_"
                        onValueChange={(piId) => {
                          if (piId && piId !== "_select_pi_" && !formData.reference_pi_ids.includes(piId)) {
                            handlePISelect([...formData.reference_pi_ids, piId]);
                          }
                        }}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select PI to add..." />
                        </SelectTrigger>
                        <SelectContent className="max-h-60 overflow-y-auto">
                          {pis
                            .filter(pi => !formData.reference_pi_ids.includes(pi.id))
                            .map(pi => (
                              <SelectItem key={pi.id} value={pi.id}>
                                {pi.voucher_no} | {new Date(pi.date).toLocaleDateString()}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>

                      {/* Display selected PIs */}
                      {formData.reference_pi_ids.length > 0 && (
                        <div className="flex flex-wrap gap-2 p-2 bg-blue-50 rounded border border-blue-200">
                          {formData.reference_pi_ids.map(piId => {
                            const pi = pis.find(p => p.id === piId);
                            return pi ? (
                              <div key={piId} className="flex items-center gap-1 bg-blue-600 text-white px-2 py-1 rounded text-sm">
                                <span>{pi.voucher_no}</span>
                                <button
                                  type="button"
                                  onClick={() => {
                                    const newPiIds = formData.reference_pi_ids.filter(id => id !== piId);
                                    handlePISelect(newPiIds);
                                  }}
                                  className="hover:bg-blue-700 rounded-full p-0.5"
                                >
                                  <X size={14} />
                                </button>
                              </div>
                            ) : null;
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                  <div>
                    <Label>Dispatched Through</Label>
                    <Input
                      value={formData.dispatched_through}
                      onChange={(e) => setFormData({ ...formData, dispatched_through: e.target.value })}
                      placeholder="e.g., DHL Express"
                    />
                  </div>
                  <div>
                    <Label>Destination</Label>
                    <Input
                      value={formData.destination}
                      onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
                      placeholder="e.g., Mumbai Port"
                    />
                  </div>
                  <div>
                    <Label>GST % <span className="text-red-500">*</span></Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.gst_percentage}
                      onChange={(e) => handlePercentageChange('gst_percentage', e.target.value)}
                      placeholder="e.g., 18"
                      className="font-semibold"
                    />
                    <p className="text-xs text-gray-500 mt-1">Enter GST percentage for auto-calculation</p>
                  </div>
                  <div>
                    <Label>TDS % <span className="text-red-500">*</span></Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.tds_percentage}
                      onChange={(e) => handlePercentageChange('tds_percentage', e.target.value)}
                      placeholder="e.g., 0.1"
                      className="font-semibold"
                    />
                    <p className="text-xs text-gray-500 mt-1">Enter TDS percentage for auto-calculation</p>
                  </div>
                  <div>
                    <Label>Status</Label>
                    <Select
                      value={formData.status}
                      onValueChange={(value) => setFormData({ ...formData, status: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Pending">Pending</SelectItem>
                        <SelectItem value="Approved">Approved</SelectItem>
                        {/* In Transit status removed - feature deprecated */}
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
                            <Button type="button" variant="ghost" size="sm" onClick={() => removeLineItem(index)}>
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
                          {/* <div className="col-span-2">
                            <Label>SKU * (Searchable)</Label>
                            <SearchableSelect
                              value={item.product_id}
                              onValueChange={(value) => handleSKUSelect(index, value)}
                              options={products.map(p => ({ value: p.id, label: p.sku_name }))}
                              placeholder="Search and select SKU"
                              searchPlaceholder="Type to search SKU..."
                            />
                          </div> */}

                          <div className="col-span-2">
                            <Label>SKU *</Label>
                            <Input
                              value={item.sku}
                              onChange={(e) => handleLineItemChange(index, 'sku', e.target.value)}
                              placeholder="Enter SKU"
                              required
                            />
                          </div>

                          <div>
                            <Label>Category</Label>
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
                            <Label>PI Total Qty</Label>
                            <Input
                              value={item.pi_quantity}
                              onChange={(e) => handleLineItemChange(index, 'pi_quantity', e.target.value)}
                              className="bg-blue-50 font-semibold text-blue-700"
                              title="Total quantity from linked PI(s)"
                            />
                          </div>
                          <div>
                            <Label>PO Quantity *</Label>
                            <Input
                              type="number"
                              step="0.01"
                              value={item.quantity || ''}
                              onChange={(e) => handleLineItemChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                              placeholder="Enter PO quantity"
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
                            <Label>Amount (Auto-calc)</Label>
                            <Input
                              value={`₹${item.amount.toFixed(2)}`}
                              disabled
                              className="bg-blue-50 font-semibold"
                            />
                          </div>
                          <div>
                            <Label>GST Value (Auto-calc)</Label>
                            <Input
                              value={`₹${(item.gst_value || 0).toFixed(2)}`}
                              disabled
                              className="bg-green-50 font-semibold text-green-700"
                              title={`Amount × (${formData.gst_percentage}% / 100)`}
                            />
                          </div>
                          <div>
                            <Label>TDS Value (Auto-calc)</Label>
                            <Input
                              value={`₹${(item.tds_value || 0).toFixed(2)}`}
                              disabled
                              className="bg-orange-50 font-semibold text-orange-700"
                              title={`Amount × (${formData.tds_percentage}% / 100)`}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 flex justify-end">
                    <div className="bg-gradient-to-r from-blue-50 to-blue-100 px-6 py-4 rounded-lg border border-blue-200">
                      <div className="space-y-1">
                        <div className="flex justify-between gap-8">
                          <span className="text-sm text-slate-700">Basic Amount:</span>
                          <span className="text-sm font-semibold">₹{getTotalBasicAmount().toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between gap-8">
                          <span className="text-sm text-green-700">+ GST ({formData.gst_percentage}%):</span>
                          <span className="text-sm font-semibold text-green-700">₹{getTotalGST().toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between gap-8">
                          <span className="text-sm text-orange-700">- TDS ({formData.tds_percentage}%):</span>
                          <span className="text-sm font-semibold text-orange-700">₹{getTotalTDS().toFixed(2)}</span>
                        </div>
                        <div className="border-t border-blue-300 pt-2 mt-2">
                          <div className="flex justify-between gap-8">
                            <span className="text-base font-medium text-slate-900">Total Amount:</span>
                            <span className="text-xl font-bold text-blue-900">₹{getTotalAmount()}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" className="bg-blue-600 hover:bg-blue-700" data-testid="save-po-btn">
                    {editingPO ? 'Update PO' : 'Create PO'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* View PO Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>View Purchase Order Details</DialogTitle>
          </DialogHeader>

          {viewingPO && (
            <div className="space-y-6">
              {/* PO Header Information */}
              <div className="bg-slate-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">PO Information</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Company</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingPO.company ? viewingPO.company.name : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Voucher No</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-semibold">
                      {viewingPO.voucher_no}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Date</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {new Date(viewingPO.date).toLocaleDateString()}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Status</Label>
                    <div className="mt-1">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${viewingPO.status === 'Completed' ? 'bg-green-100 text-green-800' :
                        /* In Transit removed */ false ? '' :
                          viewingPO.status === 'Approved' ? 'bg-purple-100 text-purple-800' :
                            'bg-yellow-100 text-yellow-800'
                        }`}>
                        {viewingPO.status}
                      </span>
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Supplier</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingPO.supplier || 'Not specified'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Consignee</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingPO.consignee || 'Not specified'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Reference PIs Information - Support Multiple PIs */}
              {viewingPO.reference_pis && viewingPO.reference_pis.length > 0 && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4 text-blue-800">
                    Linked Performa Invoice{viewingPO.reference_pis.length > 1 ? 's' : ''}
                    ({viewingPO.reference_pis.length})
                  </h3>
                  <div className="space-y-3">
                    {viewingPO.reference_pis.map((pi, index) => (
                      <div key={pi.id || index} className="grid grid-cols-2 gap-4 bg-white p-3 rounded border border-blue-200">
                        <div>
                          <Label className="text-sm font-medium text-blue-600">PI Voucher No</Label>
                          <div className="mt-1 font-semibold">
                            {pi.voucher_no}
                          </div>
                        </div>
                        <div>
                          <Label className="text-sm font-medium text-blue-600">PI Date</Label>
                          <div className="mt-1">
                            {new Date(pi.date).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Additional Information */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium text-slate-600">Dispatched Through</Label>
                  <div className="mt-1 p-2 bg-white rounded border">
                    {viewingPO.dispatched_through || 'Not specified'}
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-600">Destination</Label>
                  <div className="mt-1 p-2 bg-white rounded border">
                    {viewingPO.destination || 'Not specified'}
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
                        <th className="text-right p-3 font-medium text-slate-700">Quantity</th>
                        <th className="text-right p-3 font-medium text-slate-700">Rate</th>
                        <th className="text-right p-3 font-medium text-slate-700">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {viewingPO.line_items?.map((item, index) => (
                        <tr key={index} className="border-t">
                          <td className="p-3">{item.product_name}</td>
                          <td className="p-3 font-mono text-sm">{item.sku}</td>
                          <td className="p-3">{item.category || '-'}</td>
                          <td className="p-3">{item.brand || '-'}</td>
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
                      ₹{viewingPO.line_items?.reduce((sum, item) => sum + (item.amount || 0), 0).toFixed(2)}
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
            <div>
              <Label className="text-xs">Search</Label>
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                <Input
                  placeholder="Search PO, supplier, product..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <div>
              <Label className="text-xs">From Date</Label>
              <Input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
              />
            </div>
            <div>
              <Label className="text-xs">To Date</Label>
              <Input
                type="date"
                value={filters.dateTo}
                onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
              />
            </div>
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
          <div className="flex items-center justify-between mt-3 pt-3 border-t">
            <p className="text-sm text-slate-600">
              Showing <span className="font-semibold text-blue-600">{filteredPOs.length}</span> of <span className="font-semibold">{pos.length}</span> records
            </p>
            <Button variant="outline" size="sm" onClick={resetFilters}>
              Reset Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* PO Table */}
      <div className="border rounded-lg overflow-hidden bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedPOs(pos.map(po => po.id));
                    } else {
                      setSelectedPOs([]);
                    }
                  }}
                />
              </TableHead>
              <TableHead>Voucher No</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Supplier</TableHead>
              <TableHead>Reference PI</TableHead>
              <TableHead>Items</TableHead>
              <TableHead>Total Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredPOs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-slate-500 py-8">
                  {searchTerm || filters.dateFrom || filters.dateTo || filters.status !== 'all' || filters.company !== 'all'
                    ? 'No POs match your search/filter criteria.'
                    : 'No POs found. Create your first PO to get started.'}
                </TableCell>
              </TableRow>
            ) : (
              filteredPOs.map((po) => (
                <TableRow key={po.id}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedPOs.includes(po.id)}
                      onChange={() => togglePOSelection(po.id)}
                    />
                  </TableCell>
                  <TableCell className="font-medium">{po.voucher_no}</TableCell>
                  <TableCell>{new Date(po.date).toLocaleDateString()}</TableCell>
                  <TableCell>{po.supplier || '-'}</TableCell>
                  <TableCell className="text-sm">{po.reference_no_date || '-'}</TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {po.line_items_count} items
                      {po.line_items && po.line_items.length > 0 && (
                        <div className="text-xs text-slate-500">
                          {po.line_items[0].product_name}
                          {po.line_items.length > 1 && ` +${po.line_items.length - 1} more`}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-semibold">₹{po.total_amount?.toFixed(2)}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs ${po.status === 'Completed' ? 'bg-green-100 text-green-800' :
                      /* In Transit removed */ false ? '' :
                        po.status === 'Approved' ? 'bg-purple-100 text-purple-800' :
                          'bg-yellow-100 text-yellow-800'
                      }`}>
                      {po.status}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleView(po)}>
                        <Eye size={16} className="text-blue-600" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(po)}>
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(po)}>
                        <Trash2 size={16} className="text-red-600" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
            {filteredPOs.length > 0 && (
              <TableRow className="bg-blue-50 border-t-2 border-blue-400 font-bold">
                <TableCell></TableCell>
                <TableCell colSpan={4} className="text-right text-blue-900">TOTALS:</TableCell>
                <TableCell className="text-blue-900">
                  <div className="text-xs">Total Qty: {calculateTotals().totalQuantity}</div>
                  <div className="text-xs">{filteredPOs.length} POs</div>
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

export default PurchaseOrder;
