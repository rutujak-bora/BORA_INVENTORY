import React, { useEffect, useState, useMemo } from 'react';
import { Plus, Eye, Edit, Trash2, Download, Search, Filter, X } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Card, CardContent } from '../components/ui/card';
import { useToast } from '../hooks/use-toast';
import api from '../utils/api';
import useResizeObserverErrorFix from '../hooks/useResizeObserverErrorFix';

const OutwardStockNew = () => {
  // Apply resize observer fix
  useResizeObserverErrorFix();

  const { toast } = useToast();

  // State Management
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dispatch');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [currentType, setCurrentType] = useState('dispatch_plan');

  // Data States
  const [outwardEntries, setOutwardEntries] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [pis, setPIs] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [pendingDispatchPlans, setPendingDispatchPlans] = useState([]);
  const [availableQuantities, setAvailableQuantities] = useState({});
  const [directInwardEntries, setDirectInwardEntries] = useState([]);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState('');

  // Search and Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    mode: 'all',
    warehouse: 'all'
  });
  const [filteredDispatch, setFilteredDispatch] = useState([]);
  const [filteredExport, setFilteredExport] = useState([]);
  const [filteredDirect, setFilteredDirect] = useState([]);

  // Form State
  const [formData, setFormData] = useState({
    dispatch_type: 'dispatch_plan',
    date: new Date().toISOString().split('T')[0],
    company_id: '',
    warehouse_id: '',
    mode: '',
    pi_ids: [],
    dispatch_plan_id: '',
    export_invoice_no: '',
    // export_invoice_number: '', // NEW: Manually typed export invoice number
    inward_invoice_ids: [], // For Direct Export
    line_items: []
  });

  const [viewingEntry, setViewingEntry] = useState(null);
  const [editingEntry, setEditingEntry] = useState(null);

  // Fetch all required data
  useEffect(() => {
    fetchData();
  }, []);

  // Memoize filtered entries by type to prevent infinite re-renders
  const dispatchEntries = useMemo(() =>
    outwardEntries.filter(e => e.dispatch_type === 'dispatch_plan'),
    [outwardEntries]
  );

  const exportEntries = useMemo(() =>
    outwardEntries.filter(e => e.dispatch_type === 'export_invoice'),
    [outwardEntries]
  );

  const directEntries = useMemo(() =>
    outwardEntries.filter(e => e.dispatch_type === 'direct_export'),
    [outwardEntries]
  );

  // Apply search and filters with memoization
  useEffect(() => {
    const applyFilters = (entries) => {
      let filtered = [...entries];

      // Search filter
      if (searchTerm) {
        filtered = filtered.filter(entry =>
          entry.export_invoice_no?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          entry.line_items?.some(item =>
            item.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            item.sku?.toLowerCase().includes(searchTerm.toLowerCase())
          )
        );
      }

      // Date range filter
      if (filters.dateFrom) {
        filtered = filtered.filter(entry => new Date(entry.date) >= new Date(filters.dateFrom));
      }
      if (filters.dateTo) {
        filtered = filtered.filter(entry => new Date(entry.date) <= new Date(filters.dateTo));
      }

      // Mode filter
      if (filters.mode !== 'all') {
        filtered = filtered.filter(entry => entry.mode?.toLowerCase() === filters.mode.toLowerCase());
      }

      // Warehouse filter
      if (filters.warehouse !== 'all') {
        filtered = filtered.filter(entry => entry.warehouse_id === filters.warehouse);
      }

      return filtered;
    };

    setFilteredDispatch(applyFilters(dispatchEntries));
    setFilteredExport(applyFilters(exportEntries));
    setFilteredDirect(applyFilters(directEntries));
  }, [searchTerm, filters, dispatchEntries, exportEntries, directEntries]);

  const fetchData = async () => {
    try {
      const [outwardRes, companiesRes, pisRes, warehousesRes, dispatchPlansRes, directInwardRes] = await Promise.all([
        api.get('/outward-stock'),
        api.get('/companies'),
        api.get('/pi'),
        api.get('/warehouses'),
        api.get('/outward-stock/dispatch-plans-pending'),
        api.get('/inward-stock/direct-entries')
      ]);

      setOutwardEntries(outwardRes.data || []);
      setCompanies(companiesRes.data || []);
      setPIs(pisRes.data || []);
      setWarehouses(warehousesRes.data || []);
      setPendingDispatchPlans(dispatchPlansRes.data || []);
      setDirectInwardEntries(directInwardRes.data || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast({ title: 'Error', description: 'Failed to fetch data', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  // Calculate totals for filtered data
  const calculateTotals = (entries) => {
    const totalDispatchQty = entries.reduce((sum, entry) => {
      const entryTotal = entry.line_items?.reduce((s, item) =>
        s + (parseFloat(item.dispatch_quantity) || parseFloat(item.quantity) || 0), 0) || 0;
      return sum + entryTotal;
    }, 0);

    const totalAmount = entries.reduce((sum, entry) => {
      const entryTotal = entry.line_items?.reduce((s, item) => s + (parseFloat(item.amount) || 0), 0) || 0;
      return sum + entryTotal;
    }, 0);

    return { totalDispatchQty, totalAmount: totalAmount.toFixed(2) };
  };

  const resetFilters = () => {
    setSearchTerm('');
    setFilters({
      dateFrom: '',
      dateTo: '',
      mode: 'all',
      warehouse: 'all'
    });
  };

  // Fetch available quantity for a product
  const fetchAvailableQuantity = async (productId, warehouseId) => {
    if (!productId || !warehouseId) return 0;
    try {
      const res = await api.get(`/outward-stock/available-quantity/${productId}?warehouse_id=${warehouseId}`);
      return res.data.available_quantity || 0;
    } catch (error) {
      console.error('Failed to fetch available quantity:', error);
      return 0;
    }
  };

  // Handle PI Selection
  // const handlePISelect = async (piIds) => {
  //   if (!piIds || piIds.length === 0) {
  //     setFormData(prev => ({ ...prev, pi_ids: [], line_items: [] }));
  //     setAvailableQuantities({});
  //     return;
  //   }

  //   try {
  //     const selectedPIs = await Promise.all(
  //       piIds.map(piId => api.get(`/pi/${piId}?warehouse_id=${selectedWarehouseId}`))
  //     );

  //     const allLineItems = [];
  //     const seenProducts = new Set();
  //     const quantities = {}; // Build quantities here instead

  //     selectedPIs.forEach(res => {
  //       const pi = res.data;

  //       // Use inward_stock line_items if it exists, otherwise fallback to PI line_items
  //       const itemsToUse = pi.inward_stock?.[0]?.line_items || pi.line_items;

  //       pi.line_items.forEach(item => {
  //         const productKey = item.sku || item.product_id;
  //         if (!seenProducts.has(productKey)) {
  //           seenProducts.add(productKey);

  //           // Get the quantity from inward_stock if available
  //           const availableQty = item.available_quantity ?? 0; // This is from inward_stock line_items

  //           allLineItems.push({
  //             product_id: item.product_id,
  //             product_name: item.product_name,
  //             sku: item.sku,
  //             pi_total_quantity: item.total_po_qty || item.quantity, // use total_po_qty if available
  //             rate: item.rate,
  //             available_quantity: availableQty,
  //             dispatch_quantity: 0,
  //             remaining: item.remaining || item.quantity,
  //             already_inwarded: item.already_inwarded || 0,
  //             dimensions: '',
  //             weight: 0,
  //             amount: item.amount || 0
  //           });

  //           // Set the available quantity in the quantities object
  //           quantities[item.product_id] = availableQty;
  //         }
  //       });
  //     });

  //     setFormData(prev => ({
  //       ...prev,
  //       pi_ids: piIds,
  //       company_id: selectedPIs[0]?.data?.company_id || prev.company_id,
  //       line_items: allLineItems
  //     }));

  //     // Set available quantities from inward_stock
  //     setAvailableQuantities(quantities);

  //     toast({
  //       title: 'PI Selected',
  //       description: `Products loaded from ${piIds.length} PI(s). Enter dispatch quantities.`
  //     });

  //   } catch (error) {
  //     console.error('Error loading PI:', error);

  //     let errorMessage = 'Failed to load PI details. Please try again.';
  //     if (error.response?.status === 403) {
  //       errorMessage = 'Access denied. Your session may have expired. Please log in again.';
  //     } else if (error.response?.status === 404) {
  //       errorMessage = 'PI not found. It may have been deleted.';
  //     } else if (error.response?.data?.detail) {
  //       errorMessage = error.response.data.detail;
  //     }

  //     toast({
  //       title: 'Error',
  //       description: errorMessage,
  //       variant: 'destructive'
  //     });

  //     setFormData(prev => ({ ...prev, pi_ids: [], line_items: [] }));
  //   }
  // };

  const handlePISelect = async (piIds) => {
    if (!piIds || piIds.length === 0) {
      setFormData(prev => ({ ...prev, pi_ids: [], line_items: [] }));
      setAvailableQuantities({});
      return;
    }

    try {
      // 1️⃣ Call API WITH warehouse_id
      const selectedPIs = await Promise.all(
        piIds.map(piId =>
          api.get(`/pi/${piId}?warehouse_id=${selectedWarehouseId}`)
        )
      );

      const allLineItems = [];
      const seenProducts = new Set();
      const quantities = {};

      selectedPIs.forEach(res => {
        const pi = res.data;

        // 2️⃣ Use ONLY pi.line_items
        pi.line_items.forEach(item => {
          const key = item.product_id || item.sku;
          if (seenProducts.has(key)) return;
          seenProducts.add(key);

          const availableQty = item.available_quantity ?? 0;

          allLineItems.push({
            product_id: item.product_id,
            product_name: item.product_name,
            sku: item.sku,
            pi_total_quantity: item.pi_quantity,
            rate: item.rate,
            available_quantity: availableQty,
            dispatch_quantity: 0,
            dimensions: '',
            weight: 0,
            amount: 0
          });

          quantities[item.product_id] = availableQty;
        });
      });

      setFormData(prev => ({
        ...prev,
        pi_ids: piIds,
        company_id: selectedPIs[0]?.data?.company_id || prev.company_id,
        line_items: allLineItems
      }));

      setAvailableQuantities(quantities);

      toast({
        title: 'PI Selected',
        description: 'Available stock loaded (Inward − Outward)'
      });

    } catch (error) {
      console.error(error);
      toast({
        title: 'Error', 
        description: 'Failed to load PI details',
        variant: 'destructive'
      });
    }
  };


  // Handle Direct Inward Invoice Selection (for Direct Export)
  const handleDirectInwardSelect = (inwardInvoiceIds) => {
    if (!inwardInvoiceIds || inwardInvoiceIds.length === 0) {
      setFormData(prev => ({ ...prev, inward_invoice_ids: [], line_items: [] }));
      return;
    }

    try {
      const allLineItems = [];
      const seenProducts = new Set();

      inwardInvoiceIds.forEach(invoiceId => {
        const inwardEntry = directInwardEntries.find(entry => entry.id === invoiceId);
        if (!inwardEntry) return;

        inwardEntry.line_items?.forEach(item => {
          const productKey = item.sku || item.product_id;
          if (!seenProducts.has(productKey)) {
            seenProducts.add(productKey);
            allLineItems.push({
              product_id: item.product_id,
              product_name: item.product_name,
              sku: item.sku,
              inward_quantity: item.quantity, // Show inward quantity
              remaining_quantity: item.remaining_quantity || item.quantity, // Available for dispatch
              rate: item.rate,
              dispatch_quantity: 0,
              dimensions: item.dimensions || '',
              weight: item.weight || 0,
              amount: 0
            });
          }
        });
      });

      setFormData(prev => ({
        ...prev,
        inward_invoice_ids: inwardInvoiceIds,
        line_items: allLineItems
      }));

      toast({
        title: 'Direct Inward Invoice Selected',
        description: `Products loaded from ${inwardInvoiceIds.length} inward invoice(s). Enter dispatch quantities.`
      });
    } catch (error) {
      console.error('Error loading Direct Inward Invoice:', error);
      toast({
        title: 'Error',
        description: 'Failed to load inward invoice details.',
        variant: 'destructive'
      });
      setFormData(prev => ({ ...prev, inward_invoice_ids: [], line_items: [] }));
    }
  };

  // Handle Dispatch Plan Selection (for Export Invoice)
  const handleDispatchPlanSelect = async (dispatchPlanId) => {
    if (!dispatchPlanId || dispatchPlanId === 'none') {
      setFormData(prev => ({
        ...prev,
        dispatch_plan_id: 'none',
        pi_ids: [],
        line_items: []
      }));
      setAvailableQuantities({});
      return;
    }

    try {
      const dispatchPlan = pendingDispatchPlans.find(dp => dp.id === dispatchPlanId);
      if (dispatchPlan) {
        const lineItems = dispatchPlan.line_items?.map(item => ({
          ...item,
          dispatch_quantity: item.dispatch_quantity || item.quantity
        })) || [];

        setFormData(prev => ({
          ...prev,
          dispatch_plan_id: dispatchPlanId,
          company_id: dispatchPlan.company_id,
          warehouse_id: dispatchPlan.warehouse_id,
          pi_ids: dispatchPlan.pi_ids || [],
          mode: dispatchPlan.mode || '',
          line_items: lineItems
        }));

        // Fetch available quantities
        const quantities = {};
        for (const item of lineItems) {
          const availableQty = await fetchAvailableQuantity(item.product_id, dispatchPlan.warehouse_id);
          quantities[item.product_id] = availableQty;
        }
        setAvailableQuantities(quantities);

        toast({
          title: 'Dispatch Plan Selected',
          description: 'Products auto-populated. You can modify quantities.'
        });
      }
    } catch (error) {
      console.error('Error loading dispatch plan:', error);
      toast({ title: 'Error', description: 'Failed to load dispatch plan', variant: 'destructive' });
    }
  };

  // Handle line item changes
  const handleLineItemChange = (index, field, value) => {
    const newLineItems = [...formData.line_items];
    newLineItems[index][field] = value;

    // Auto-calculate amount
    if (field === 'dispatch_quantity' || field === 'rate') {
      const qty = field === 'dispatch_quantity' ? value : newLineItems[index].dispatch_quantity;
      const rate = field === 'rate' ? value : newLineItems[index].rate;
      newLineItems[index].amount = qty * rate;
    }

    setFormData({ ...formData, line_items: newLineItems });
  };

  // Add line item
  const handleAddLineItem = () => {
    setFormData({
      ...formData,
      line_items: [...formData.line_items, {
        product_id: '',
        product_name: '',
        sku: '',
        pi_total_quantity: 0,
        rate: 0,
        dispatch_quantity: 0,
        dimensions: '',
        weight: 0,
        amount: 0
      }]
    });
  };

  // Remove line item
  const handleRemoveLineItem = (index) => {
    const newLineItems = formData.line_items.filter((_, i) => i !== index);
    // Keep at least one empty item if all are removed
    if (newLineItems.length === 0) {
      setFormData({
        ...formData,
        line_items: [{
          product_id: '',
          product_name: '',
          sku: '',
          pi_total_quantity: 0,
          quantity: 0,
          dispatch_quantity: 0,
          rate: 0,
          amount: 0,
          dimensions: '',
          weight: 0
        }]
      });
    } else {
      setFormData({ ...formData, line_items: newLineItems });
    }
  };

  // Validate form
  const validateForm = () => {
    console.log('🔍 Starting validation...');

    if (!formData.company_id) {
      console.log('❌ Validation failed: No company selected');
      toast({ title: 'Error', description: 'Please select a company', variant: 'destructive' });
      return false;
    }
    console.log('✅ Company ID:', formData.company_id);

    if (!formData.warehouse_id) {
      console.log('❌ Validation failed: No warehouse selected');
      toast({ title: 'Error', description: 'Please select a warehouse', variant: 'destructive' });
      return false;
    }
    console.log('✅ Warehouse ID:', formData.warehouse_id);

    if (formData.dispatch_type !== 'direct_export' && formData.pi_ids.length === 0) {
      console.log('❌ Validation failed: No PI selected');
      toast({ title: 'Error', description: 'Please select at least one PI', variant: 'destructive' });
      return false;
    }
    console.log('✅ PI IDs:', formData.pi_ids);

    const validItems = formData.line_items.filter(item => item.product_name && item.product_name.trim() !== '');
    console.log('✅ Valid line items:', validItems.length);

    if (validItems.length === 0) {
      console.log('❌ Validation failed: No products');
      toast({ title: 'Error', description: 'Please add at least one product', variant: 'destructive' });
      return false;
    }

    // Validate quantities
    for (const item of validItems) {
      console.log(`📦 Checking item: ${item.product_name}, Dispatch: ${item.dispatch_quantity}, Available: ${availableQuantities[item.product_id]}`);

      if (!item.dispatch_quantity || item.dispatch_quantity <= 0) {
        console.log(`❌ Validation failed: Invalid quantity for ${item.product_name}`);
        toast({
          title: 'Error',
          description: `Please enter dispatch quantity for ${item.product_name}`,
          variant: 'destructive'
        });
        return false;
      }

      // Check available quantity ONLY for Dispatch Plan and Export Invoice (not for Direct Export)
      if (formData.dispatch_type !== 'direct_export') {
        const available = availableQuantities[item.product_id] || 0;
        if (item.dispatch_quantity > available) {
          console.log(`❌ Validation failed: ${item.product_name} - Dispatch (${item.dispatch_quantity}) > Available (${available})`);
          toast({
            title: 'Error',
            description: `Dispatch quantity for ${item.product_name} exceeds available stock (${available})`,
            variant: 'destructive'
          });
          return false;
        }
      } else {
        console.log(`✅ Skipping stock validation for Direct Export`);
      }
    }

    console.log('✅ All validation passed!');
    return true;
  };

  // Handle form submission
  const handleSubmit = async () => {
    console.log('🔵 CREATE BUTTON CLICKED');
    console.log('📋 Form Data:', formData);
    console.log('📦 Available Quantities:', availableQuantities);

    if (!validateForm()) {
      console.log('❌ Validation failed');
      return;
    }

    console.log('✅ Validation passed, submitting...');

    try {
      const submitData = {
        ...formData,
        line_items: formData.line_items.filter(item => item.product_name && item.product_name.trim() !== '')
      };

      console.log('📤 Submitting data:', JSON.stringify(submitData, null, 2));

      if (editingEntry) {
        const response = await api.put(`/outward-stock/${editingEntry.id}`, submitData);
        console.log('✅ Update response:', response.data);
        toast({ title: 'Success', description: 'Outward entry updated successfully' });
      } else {
        const response = await api.post('/outward-stock', submitData);
        console.log('✅ Create response:', response.data);
        toast({ title: 'Success', description: 'Outward entry created successfully' });
      }

      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      console.error('❌ Error submitting form:', error);
      console.error('❌ Error response:', error.response);
      console.error('❌ Error detail:', error.response?.data?.detail);
      console.error('❌ Error status:', error.response?.status);

      // Show detailed error message
      const errorMessage = error.response?.data?.detail || 'Failed to save outward entry';
      console.error('❌ Showing error message:', errorMessage);

      toast({
        title: 'Error Creating Entry',
        description: errorMessage,
        variant: 'destructive'
      });
    }
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      dispatch_type: currentType,
      date: new Date().toISOString().split('T')[0],
      company_id: '',
      warehouse_id: '',
      mode: '',
      pi_ids: [],
      dispatch_plan_id: '',
      export_invoice_no: '',
      export_invoice_number: '',
      inward_invoice_ids: [], // For Direct Export
      line_items: []
    });
    setAvailableQuantities({});
    setEditingEntry(null);
  };

  // Open create dialog
  const openCreateDialog = (type) => {
    setCurrentType(type);
    resetForm();
    setFormData(prev => ({ ...prev, dispatch_type: type }));
    setDialogOpen(true);
  };

  // Handle delete
  const handleDelete = async (entry) => {
    if (!window.confirm('Are you sure you want to delete this entry?')) return;

    try {
      await api.delete(`/outward-stock/${entry.id}`);
      toast({ title: 'Success', description: 'Entry deleted successfully' });
      fetchData();
    } catch (error) {
      console.error('Error deleting entry:', error);
      toast({ title: 'Error', description: 'Failed to delete entry', variant: 'destructive' });
    }
  };

  // Handle Create Export Invoice from Dispatch Plan
  const handleCreateExportInvoice = async (dispatchPlan) => {
    try {
      console.log('🔄 Converting Dispatch Plan to Export Invoice:', dispatchPlan);

      // Create export invoice with dispatch_plan_id reference
      const exportInvoiceData = {
        dispatch_type: 'export_invoice',
        dispatch_plan_id: dispatchPlan.id,
        date: dispatchPlan.date,
        company_id: dispatchPlan.company_id,
        warehouse_id: dispatchPlan.warehouse_id,
        mode: dispatchPlan.mode,
        export_invoice_no: dispatchPlan.export_invoice_no,
        pi_ids: dispatchPlan.pi_ids || [],
        line_items: dispatchPlan.line_items.map(item => ({
          product_id: item.product_id,
          product_name: item.product_name,
          sku: item.sku,
          rate: item.rate,
          dispatch_quantity: item.dispatch_quantity, // Keep dispatch_quantity
          quantity: item.dispatch_quantity, // Also add quantity for backward compatibility
          pi_total_quantity: item.pi_total_quantity,
          dimensions: item.dimensions,
          weight: item.weight,
          amount: item.amount
        }))
      };

      console.log('📤 Sending data:', JSON.stringify(exportInvoiceData, null, 2));

      const response = await api.post('/outward-stock', exportInvoiceData);
      console.log('✅ Export Invoice created:', response.data);

      // Delete the dispatch plan as it's now converted
      await api.delete(`/outward-stock/${dispatchPlan.id}`);
      console.log('✅ Dispatch Plan removed after conversion');

      toast({
        title: 'Success',
        description: 'Export Invoice created from Dispatch Plan successfully!'
      });

      fetchData();
    } catch (error) {
      console.error('❌ Error creating export invoice:', error);
      console.error('❌ Error response:', error.response?.data);
      console.error('❌ Error status:', error.response?.status);
      console.error('❌ Error detail:', error.response?.data?.detail);

      toast({
        title: 'Error Creating Export Invoice',
        description: error.response?.data?.detail || 'Failed to create export invoice. Check console for details.',
        variant: 'destructive'
      });
    }
  };

  // Handle Remove Dispatch Plan
  const handleRemoveDispatchPlan = async (dispatchPlan) => {
    if (!window.confirm(`Are you sure you want to remove Dispatch Plan "${dispatchPlan.export_invoice_no}"?`)) {
      return;
    }

    try {
      await api.delete(`/outward-stock/${dispatchPlan.id}`);
      toast({
        title: 'Success',
        description: 'Dispatch Plan removed successfully'
      });
      fetchData();
    } catch (error) {
      console.error('❌ Error removing dispatch plan:', error);
      toast({
        title: 'Error',
        description: 'Failed to remove dispatch plan',
        variant: 'destructive'
      });
    }
  };

  // Handle view
  const handleView = (entry) => {
    setViewingEntry(entry);
    setViewDialogOpen(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Outward Stock Management</h1>

      {/* Search and Filters - Common for all tabs */}
      <Card className="mb-6">
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
                  placeholder="Search invoice, product..."
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
              <Label className="text-xs">Mode</Label>
              <select
                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
                value={filters.mode}
                onChange={(e) => setFilters({ ...filters, mode: e.target.value })}
              >
                <option value="all">All Modes</option>
                <option value="sea">Sea</option>
                <option value="air">Air</option>
              </select>
            </div>
            <div>
              <Label className="text-xs">Warehouse</Label>
              <select
                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
                value={filters.warehouse}
                onChange={(e) => setFilters({ ...filters, warehouse: e.target.value })}
              >
                <option value="all">All Warehouses</option>
                {warehouses.map(wh => (
                  <option key={wh.id} value={wh.id}>{wh.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex items-center justify-between mt-3 pt-3 border-t">
            <div className="text-sm text-slate-600">
              <span className="font-semibold">Dispatch Plans:</span> {filteredDispatch.length} |
              <span className="font-semibold ml-2">Export Invoices:</span> {filteredExport.length} |
              <span className="font-semibold ml-2">Direct Exports:</span> {filteredDirect.length}
            </div>
            <Button variant="outline" size="sm" onClick={resetFilters}>
              Reset Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="dispatch">Dispatch Plan</TabsTrigger>
          <TabsTrigger value="export">Export Invoice</TabsTrigger>
          <TabsTrigger value="direct">Direct Export</TabsTrigger>
        </TabsList>

        {/* Dispatch Plan Tab */}

        <div className="flex items-center gap-3 mb-4">
          <Label className="text-sm font-medium">Warehouse</Label>

          <Select
            value={selectedWarehouseId}
            onValueChange={(value) => setSelectedWarehouseId(value)}
          >
            <SelectTrigger className="w-[260px]">
              <SelectValue placeholder="Select warehouse" />
            </SelectTrigger>

            <SelectContent>
              {warehouses.map(w => (
                <SelectItem key={w.id} value={w.id}>
                  {w.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <TabsContent value="dispatch">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Dispatch Plans</h2>
            <Button disabled={!selectedWarehouseId} onClick={() => openCreateDialog('dispatch_plan')} className="bg-blue-600 hover:bg-blue-700">
              <Plus size={16} className="mr-2" />
              Create Dispatch Plan
            </Button>
          </div>

          {/* Dispatch Plan Note */}
          <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-3 mb-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-blue-700 font-semibold">ℹ️ Note:</span>
              <span className="text-blue-800">Dispatch Plans are for planning only. Stock is NOT reduced until you create Export Invoice.</span>
            </div>
          </div>


          <div className="border rounded-lg overflow-hidden bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Invoice No</TableHead>
                  {/* <TableHead>Invoice Number</TableHead> */}
                  <TableHead>Mode</TableHead>
                  <TableHead>PI Reference</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Total Amount</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDispatch.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-slate-500 py-8">
                      {searchTerm || filters.dateFrom || filters.dateTo || filters.mode !== 'all' || filters.warehouse !== 'all'
                        ? 'No dispatch plans match your search/filter criteria.'
                        : 'No dispatch plans found. Create one to get started.'}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredDispatch.map(entry => (
                    <TableRow key={entry.id}>
                      <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                      <TableCell>{entry.export_invoice_no}</TableCell>
                      {/* <TableCell>{entry.export_invoice_number || '-'}</TableCell> */}
                      <TableCell>{entry.mode}</TableCell>
                      <TableCell>
                        {entry.pi_ids?.length > 0
                          ? `${entry.pi_ids.length} PI(s)`
                          : '-'}
                      </TableCell>
                      <TableCell>{entry.line_items_count || entry.line_items?.length || 0}</TableCell>
                      <TableCell>₹{entry.total_amount?.toFixed(2) || '0.00'}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" onClick={() => handleView(entry)}>
                          <Eye size={16} className="text-blue-600" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(entry)}>
                          <Trash2 size={16} className="text-red-600" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
                {filteredDispatch.length > 0 && (
                  <TableRow className="bg-blue-50 border-t-2 border-blue-400 font-bold">
                    <TableCell></TableCell>
                    <TableCell colSpan={4} className="text-right text-blue-900">TOTALS:</TableCell>
                    <TableCell className="text-blue-900">
                      <div className="text-xs">Dispatch Qty: {calculateTotals(filteredDispatch).totalDispatchQty.toFixed(0)}</div>
                      <div className="text-xs">{filteredDispatch.length} Plans</div>
                    </TableCell>
                    <TableCell className="text-right text-blue-900">₹{calculateTotals(filteredDispatch).totalAmount}</TableCell>
                    <TableCell></TableCell>
                    <TableCell></TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* Export Invoice Tab */}
        <TabsContent value="export">
          <h2 className="text-xl font-semibold mb-4">Export Invoices</h2>

          {/* Export Invoice Note */}
          <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-3 mb-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-red-700 font-semibold">📤 Important:</span>
              <span className="text-red-800">Export Invoices reduce stock from Stock Summary. Create this only when goods are actually dispatched.</span>
            </div>
          </div>


          {/* Pending Dispatch Plans Section */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold mb-3 text-orange-600">Pending Dispatch Plans (Awaiting Export Invoice)</h3>
            <div className="border rounded-lg overflow-hidden bg-white">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Invoice No</TableHead>
                    {/* <TableHead>Invoice Number</TableHead> */}
                    <TableHead>Mode</TableHead>
                    <TableHead>PI Reference</TableHead>
                    <TableHead>Items</TableHead>
                    <TableHead>Total Dispatch Qty</TableHead>
                    <TableHead>Total Amount</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDispatch.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-slate-500 py-8">
                        {searchTerm || filters.dateFrom || filters.dateTo || filters.mode !== 'all' || filters.warehouse !== 'all'
                          ? 'No pending dispatch plans match your search/filter criteria.'
                          : 'No pending dispatch plans. Create a dispatch plan first.'}
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredDispatch.map(entry => (
                      <TableRow key={entry.id} className="bg-orange-50">
                        <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                        <TableCell className="font-medium">{entry.export_invoice_no}</TableCell>
                        <TableCell>{entry.export_invoice_number || '-'}</TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded text-xs ${entry.mode === 'Air' ? 'bg-blue-100 text-blue-700' : 'bg-teal-100 text-teal-700'
                            }`}>
                            {entry.mode}
                          </span>
                        </TableCell>
                        <TableCell>
                          {entry.pi_ids?.length > 0
                            ? `${entry.pi_ids.length} PI(s)`
                            : '-'}
                        </TableCell>
                        <TableCell>{entry.line_items_count || entry.line_items?.length || 0}</TableCell>
                        <TableCell className="font-semibold">
                          {entry.line_items?.reduce((sum, item) => sum + (item.dispatch_quantity || 0), 0) || 0}
                        </TableCell>
                        <TableCell className="font-semibold">₹{entry.total_amount?.toFixed(2) || '0.00'}</TableCell>
                        <TableCell className="text-right space-x-2">
                          <Button
                            size="sm"
                            className="bg-green-600 hover:bg-green-700"
                            onClick={() => handleCreateExportInvoice(entry)}
                          >
                            <Plus size={14} className="mr-1" />
                            Create Export Invoice
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="border-red-300 text-red-600 hover:bg-red-50"
                            onClick={() => handleRemoveDispatchPlan(entry)}
                          >
                            <Trash2 size={14} className="mr-1" />
                            Remove
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>

          {/* Completed Export Invoices Section */}
          <div>
            <h3 className="text-lg font-semibold mb-3 text-green-600">Completed Export Invoices</h3>
            <div className="border rounded-lg overflow-hidden bg-white">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Invoice No</TableHead>
                    {/* <TableHead>Invoice Number</TableHead> */}
                    <TableHead>Mode</TableHead>
                    <TableHead>From Dispatch Plan</TableHead>
                    <TableHead>Items</TableHead>
                    <TableHead>Total Amount</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredExport.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-slate-500 py-8">
                        {searchTerm || filters.dateFrom || filters.dateTo || filters.mode !== 'all' || filters.warehouse !== 'all'
                          ? 'No export invoices match your search/filter criteria.'
                          : 'No export invoices created yet. Convert a dispatch plan above to create one.'}
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredExport.map(entry => (
                      <TableRow key={entry.id} className="bg-green-50">
                        <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                        <TableCell className="font-medium">{entry.export_invoice_no}</TableCell>
                        {/* <TableCell>{entry.export_invoice_number || '-'}</TableCell> */}
                        <TableCell>
                          <span className={`px-2 py-1 rounded text-xs ${entry.mode === 'Air' ? 'bg-blue-100 text-blue-700' : 'bg-teal-100 text-teal-700'
                            }`}>
                            {entry.mode}
                          </span>
                        </TableCell>
                        <TableCell>
                          {entry.dispatch_plan_id ? '✓ Yes' : 'Direct'}
                        </TableCell>
                        <TableCell>{entry.line_items_count || entry.line_items?.length || 0}</TableCell>
                        <TableCell className="font-semibold">₹{entry.total_amount?.toFixed(2) || '0.00'}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" onClick={() => handleView(entry)}>
                            <Eye size={16} className="text-blue-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(entry)}>
                            <Trash2 size={16} className="text-red-600" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                  {filteredExport.length > 0 && (
                    <TableRow className="bg-green-50 border-t-2 border-green-400 font-bold">
                      <TableCell></TableCell>
                      <TableCell colSpan={3} className="text-right text-green-900">TOTALS:</TableCell>
                      <TableCell className="text-green-900">
                        <div className="text-xs">Dispatch Qty: {calculateTotals(filteredExport).totalDispatchQty.toFixed(0)}</div>
                        <div className="text-xs">{filteredExport.length} Invoices</div>
                      </TableCell>
                      <TableCell className="text-right text-green-900">₹{calculateTotals(filteredExport).totalAmount}</TableCell>
                      <TableCell></TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </TabsContent>

        {/* Direct Export Tab */}
        <TabsContent value="direct">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Direct Export Invoices</h2>
            <Button onClick={() => openCreateDialog('direct_export')} className="bg-purple-600 hover:bg-purple-700">
              <Plus size={16} className="mr-2" />
              Create Direct Export
            </Button>
          </div>

          <div className="border rounded-lg overflow-hidden bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Invoice No</TableHead>
                  {/* <TableHead>Invoice Number</TableHead> */}
                  <TableHead>Mode</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Total Amount</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDirect.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-slate-500 py-8">
                      {searchTerm || filters.dateFrom || filters.dateTo || filters.mode !== 'all' || filters.warehouse !== 'all'
                        ? 'No direct export invoices match your search/filter criteria.'
                        : 'No direct export invoices found. Create one to get started.'}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredDirect.map(entry => (
                    <TableRow key={entry.id}>
                      <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                      <TableCell>{entry.export_invoice_no}</TableCell>
                      <TableCell>{entry.export_invoice_number || '-'}</TableCell>
                      <TableCell>{entry.mode}</TableCell>
                      <TableCell>{entry.line_items_count || entry.line_items?.length || 0}</TableCell>
                      <TableCell>₹{entry.total_amount?.toFixed(2) || '0.00'}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" onClick={() => handleView(entry)}>
                          <Eye size={16} className="text-blue-600" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(entry)}>
                          <Trash2 size={16} className="text-red-600" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
                {filteredDirect.length > 0 && (
                  <TableRow className="bg-purple-50 border-t-2 border-purple-400 font-bold">
                    <TableCell></TableCell>
                    <TableCell colSpan={3} className="text-right text-purple-900">TOTALS:</TableCell>
                    <TableCell className="text-purple-900">
                      <div className="text-xs">Export Qty: {calculateTotals(filteredDirect).totalDispatchQty.toFixed(0)}</div>
                      <div className="text-xs">{filteredDirect.length} Exports</div>
                    </TableCell>
                    <TableCell className="text-right text-purple-900">₹{calculateTotals(filteredDirect).totalAmount}</TableCell>
                    <TableCell></TableCell>
                    <TableCell></TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingEntry ? 'Edit' : 'Create'} {
                formData.dispatch_type === 'dispatch_plan' ? 'Dispatch Plan' :
                  formData.dispatch_type === 'export_invoice' ? 'Export Invoice' :
                    'Direct Export Invoice'
              }
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* Basic Fields */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Export Invoice No</Label>
                <Input
                  value={formData.export_invoice_no}
                  onChange={(e) => setFormData({ ...formData, export_invoice_no: e.target.value })}
                  placeholder="Auto-generated if empty"
                />
              </div>

              {/* <div>
                <Label>Export Invoice Number</Label>
                <Input
                  value={formData.export_invoice_number || ''}
                  onChange={(e) => setFormData({ ...formData, export_invoice_number: e.target.value })}
                  placeholder="Enter export invoice number"
                />
              </div> */}

              <div>
                <Label>Date *</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  required
                />
              </div>

              <div>
                <Label>Mode *</Label>
                <Select
                  value={formData.mode}
                  onValueChange={(value) => {
                    requestAnimationFrame(() => {
                      setTimeout(() => setFormData({ ...formData, mode: value }), 50);
                    });
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select mode" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Sea">Sea</SelectItem>
                    <SelectItem value="Air">Air</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Company *</Label>
                <Select
                  value={formData.company_id}
                  onValueChange={(value) => {
                    requestAnimationFrame(() => {
                      setTimeout(() => setFormData({ ...formData, company_id: value }), 50);
                    });
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select company" />
                  </SelectTrigger>
                  <SelectContent>
                    {(companies || []).map(company => (
                      <SelectItem key={company.id} value={company.id}>
                        {company.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Warehouse *</Label>
                <Select
                  value={formData.warehouse_id}
                  onValueChange={(value) => {
                    requestAnimationFrame(() => {
                      setTimeout(() => setFormData({ ...formData, warehouse_id: value }), 50);
                    });
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select warehouse" />
                  </SelectTrigger>
                  <SelectContent>
                    {(warehouses || []).map(warehouse => (
                      <SelectItem key={warehouse.id} value={warehouse.id}>
                        {warehouse.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Dispatch Plan Selection for Export Invoice */}
            {formData.dispatch_type === 'export_invoice' && (
              <div className="bg-blue-50 p-4 rounded border border-blue-200">
                <Label className="text-blue-800 font-semibold">Link to Dispatch Plan (Optional)</Label>
                <Select
                  value={formData.dispatch_plan_id}
                  onValueChange={(value) => {
                    requestAnimationFrame(() => {
                      setTimeout(() => handleDispatchPlanSelect(value), 50);
                    });
                  }}
                >
                  <SelectTrigger className="mt-2">
                    <SelectValue placeholder="Select Dispatch Plan or create new" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Create New (No Dispatch Plan)</SelectItem>
                    {(pendingDispatchPlans || []).map(dp => (
                      <SelectItem key={dp.id} value={dp.id}>
                        {dp.export_invoice_no} | {new Date(dp.date).toLocaleDateString()} | {dp.line_items?.length || 0} items
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {formData.dispatch_plan_id && formData.dispatch_plan_id !== 'none' && (
                  <p className="text-xs text-blue-600 mt-2">
                    ✓ Products auto-populated from Dispatch Plan
                  </p>
                )}
              </div>
            )}

            {/* PI Selection (for Dispatch Plan and Export Invoice without dispatch plan) */}
            {formData.dispatch_type !== 'direct_export' && (!formData.dispatch_plan_id || formData.dispatch_plan_id === 'none') && (
              <div>
                <Label>PI Reference * (Select one or multiple)</Label>
                <Select
                  value="_select_pi_"
                  onValueChange={(piId) => {
                    if (piId && piId !== "_select_pi_" && !formData.pi_ids.includes(piId)) {
                      console.log("this is the data which is being shown in the form ", piId);
                      requestAnimationFrame(() => {
                        setTimeout(() => {
                          handlePISelect([...formData.pi_ids, piId]);
                        }, 50);
                      });
                    }
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select PI to add..." />
                  </SelectTrigger>
                  <SelectContent>
                    {(pis || [])
                      .filter(pi => !formData.pi_ids.includes(pi.id))
                      .map(pi => (
                        <SelectItem key={pi.id} value={pi.id}>
                          {pi.voucher_no} | {new Date(pi.date).toLocaleDateString()}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>

                {formData.pi_ids.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2 p-2 bg-slate-50 rounded border">
                    {formData.pi_ids.map(piId => {
                      const pi = pis.find(p => p.id === piId);
                      return pi ? (
                        <div key={piId} className="flex items-center gap-1 bg-blue-600 text-white px-2 py-1 rounded text-sm">
                          <span>{pi.voucher_no}</span>
                          <button
                            type="button"
                            onClick={() => {
                              const newPiIds = formData.pi_ids.filter(id => id !== piId);
                              handlePISelect(newPiIds);
                            }}
                            className="hover:bg-blue-700 rounded-full p-0.5"
                          >
                            ×
                          </button>
                        </div>
                      ) : null;
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Direct Inward Invoice Selection (for Direct Export) */}
            {formData.dispatch_type === 'direct_export' && (
              <div className="bg-purple-50 p-4 rounded border border-purple-200">
                <Label className="text-purple-800 font-semibold">Select Inward Invoice No (Optional - Multiple selection enabled)</Label>
                <Select
                  value="_select_inward_"
                  onValueChange={(invoiceId) => {
                    if (invoiceId && invoiceId !== "_select_inward_" && !formData.inward_invoice_ids.includes(invoiceId)) {
                      requestAnimationFrame(() => {
                        setTimeout(() => {
                          handleDirectInwardSelect([...formData.inward_invoice_ids, invoiceId]);
                        }, 50);
                      });
                    }
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Direct Inward Invoice to add..." />
                  </SelectTrigger>
                  <SelectContent>
                    {(directInwardEntries || [])
                      .filter(entry => !(formData.inward_invoice_ids || []).includes(entry.id))
                      .map(entry => (
                        <SelectItem key={entry.id} value={entry.id}>
                          {entry.inward_invoice_no || entry.invoice_no} | {new Date(entry.date).toLocaleDateString()} | {entry.line_items?.length || 0} items
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>

                {(formData.inward_invoice_ids || []).length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2 p-2 bg-slate-50 rounded border">
                    {(formData.inward_invoice_ids || []).map(invoiceId => {
                      const entry = directInwardEntries.find(e => e.id === invoiceId);
                      return entry ? (
                        <div key={invoiceId} className="flex items-center gap-1 bg-purple-600 text-white px-2 py-1 rounded text-sm">
                          <span>{entry.inward_invoice_no || entry.invoice_no}</span>
                          <button
                            type="button"
                            onClick={() => {
                              const newInwardIds = (formData.inward_invoice_ids || []).filter(id => id !== invoiceId);
                              handleDirectInwardSelect(newInwardIds);
                            }}
                            className="hover:bg-purple-700 rounded-full p-0.5"
                          >
                            ×
                          </button>
                        </div>
                      ) : null;
                    })}
                  </div>
                )}
                {(formData.inward_invoice_ids || []).length > 0 && (
                  <p className="text-xs text-purple-600 mt-2">
                    ✓ Products auto-populated from Direct Inward Invoice(s)
                  </p>
                )}
              </div>
            )}

            {/* Line Items */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <Label className="text-lg font-semibold">Products</Label>
                {formData.dispatch_type === 'direct_export' && (
                  <Button type="button" size="sm" onClick={handleAddLineItem}>
                    <Plus size={14} className="mr-1" />
                    Add Product
                  </Button>
                )}
              </div>

              {formData.line_items.length === 0 ? (
                <div className="text-center py-8 text-slate-500 border rounded">
                  {formData.dispatch_type === 'direct_export'
                    ? 'Select Direct Inward Invoice or click "Add Product" to add items manually'
                    : 'Select PI to load products'}
                </div>
              ) : (
                <div className="space-y-4">
                  {formData.line_items.map((item, index) => (
                    <div key={index} className="border rounded p-4 bg-slate-50 relative">
                      <div className="flex justify-between items-start mb-3">
                        <h4 className="font-semibold text-slate-700">Product {index + 1} - {item.product_name || 'New Product'}</h4>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => handleRemoveLineItem(index)}
                          className="text-red-600 hover:text-red-800 hover:bg-red-50 border-red-300"
                          title="Remove this product"
                        >
                          <X size={16} className="mr-1" />
                          Remove
                        </Button>
                      </div>

                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <Label>Product Name</Label>
                          <Input
                            value={item.product_name || ''}
                            onChange={(e) => handleLineItemChange(index, 'product_name', e.target.value)}
                            placeholder="Product name"
                            readOnly={formData.dispatch_type !== 'direct_export'}
                          />
                        </div>

                        <div>
                          <Label>SKU</Label>
                          <Input
                            value={item.sku || ''}
                            onChange={(e) => handleLineItemChange(index, 'sku', e.target.value)}
                            placeholder="SKU"
                            readOnly={formData.dispatch_type !== 'direct_export'}
                          />
                        </div>

                        {formData.dispatch_type !== 'direct_export' && (
                          <div>
                            <Label>PI Total Quantity</Label>
                            <Input
                              value={item.pi_total_quantity || 0}
                              readOnly
                              className="bg-slate-100"
                            />
                          </div>
                        )}

                        {/* Show Inward Quantity for Direct Export when invoice is selected */}
                        {formData.dispatch_type === 'direct_export' && item.inward_quantity !== undefined && (
                          <div>
                            <Label>Inward Quantity</Label>
                            <Input
                              value={item.inward_quantity || 0}
                              readOnly
                              className="bg-blue-50 font-semibold text-blue-700 border-blue-300"
                            />
                          </div>
                        )}

                        <div>
                          <Label>Rate</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.rate || 0}
                            onChange={(e) => handleLineItemChange(index, 'rate', parseFloat(e.target.value) || 0)}
                            placeholder="Rate"
                          />
                        </div>

                        {/* Available Quantity Display */}
                        {availableQuantities[item.product_id] !== undefined && (
                          <div>
                            <Label>Available Quantity</Label>
                            <Input
                              value={availableQuantities[item.product_id] || 0}
                              readOnly
                              className="bg-green-50 font-semibold text-green-700 border-green-300"
                            />
                          </div>
                        )}

                        <div>
                          <Label>Dispatch Quantity *</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.dispatch_quantity || 0}
                            onChange={(e) => handleLineItemChange(index, 'dispatch_quantity', parseFloat(e.target.value) || 0)}
                            placeholder="Dispatch qty"
                            className={
                              availableQuantities[item.product_id] !== undefined &&
                                item.dispatch_quantity > availableQuantities[item.product_id]
                                ? 'border-red-500 bg-red-50'
                                : ''
                            }
                          />
                          {availableQuantities[item.product_id] !== undefined && (
                            <p className={`text-xs mt-1 ${item.dispatch_quantity > availableQuantities[item.product_id]
                              ? 'text-red-600 font-semibold'
                              : 'text-slate-500'
                              }`}>
                              Max: {availableQuantities[item.product_id]}
                              {item.dispatch_quantity > availableQuantities[item.product_id] &&
                                ' ⚠️ Exceeds available!'}
                            </p>
                          )}
                        </div>

                        <div>
                          <Label>Dimensions</Label>
                          <Input
                            value={item.dimensions || ''}
                            onChange={(e) => handleLineItemChange(index, 'dimensions', e.target.value)}
                            placeholder="L x W x H"
                          />
                        </div>

                        <div>
                          <Label>Weight (kg)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.weight || 0}
                            onChange={(e) => handleLineItemChange(index, 'weight', parseFloat(e.target.value) || 0)}
                            placeholder="Weight"
                          />
                        </div>

                        <div>
                          <Label>Amount</Label>
                          <Input
                            value={item.amount?.toFixed(2) || '0.00'}
                            readOnly
                            className="bg-slate-100"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Total Amount */}
            {formData.line_items.length > 0 && (
              <div className="flex justify-end">
                <div className="text-right">
                  <Label className="text-slate-600">Total Amount</Label>
                  <div className="text-2xl font-bold text-blue-600">
                    ₹{formData.line_items.reduce((sum, item) => sum + (item.amount || 0), 0).toFixed(2)}
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="button" onClick={handleSubmit} className="bg-blue-600 hover:bg-blue-700">
                {editingEntry ? 'Update' : 'Create'}
              </Button>
            </div>
          </div>

        </DialogContent>
      </Dialog>

      {/* View Dialog - Will be implemented next */}
      {/* View Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {viewingEntry?.dispatch_type === 'dispatch_plan' && 'Dispatch Plan Details'}
              {viewingEntry?.dispatch_type === 'export_invoice' && 'Export Invoice Details'}
              {viewingEntry?.dispatch_type === 'direct_export' && 'Direct Export Details'}
            </DialogTitle>
          </DialogHeader>

          {viewingEntry && (
            <div className="space-y-6">
              {/* Basic Information */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-lg">
                <div>
                  <label className="text-sm font-semibold text-slate-600">Date</label>
                  <p className="text-slate-900">{new Date(viewingEntry.date).toLocaleDateString()}</p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-slate-600">Invoice No</label>
                  <p className="text-slate-900">{viewingEntry.export_invoice_no}</p>
                </div>
                {/* <div>
                  <label className="text-sm font-semibold text-slate-600">Invoice Number</label>
                  <p className="text-slate-900">{viewingEntry.export_invoice_number || '-'}</p>
                </div> */}
                <div>
                  <label className="text-sm font-semibold text-slate-600">Mode</label>
                  <p className="text-slate-900">{viewingEntry.mode}</p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-slate-600">Type</label>
                  <p className="text-slate-900 capitalize">{viewingEntry.dispatch_type?.replace('_', ' ')}</p>
                </div>
                {viewingEntry.dispatch_plan_id && (
                  <div>
                    <label className="text-sm font-semibold text-slate-600">Linked Dispatch Plan</label>
                    <p className="text-slate-900">✓ Yes</p>
                  </div>
                )}
              </div>

              {/* PI References */}
              {viewingEntry.pi_ids && viewingEntry.pi_ids.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-600 mb-2">PI References</h3>
                  <div className="flex flex-wrap gap-2">
                    {viewingEntry.pi_ids.map((piId, idx) => (
                      <span key={idx} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                        PI #{idx + 1}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Line Items */}
              <div>
                <h3 className="text-sm font-semibold text-slate-600 mb-3">Line Items</h3>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead>SKU</TableHead>
                        <TableHead>Rate</TableHead>
                        <TableHead>Quantity</TableHead>
                        <TableHead>Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {viewingEntry.line_items?.map((item, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{item.product_name}</TableCell>
                          <TableCell>{item.sku || '-'}</TableCell>
                          <TableCell>₹{item.rate?.toFixed(2) || '0.00'}</TableCell>
                          <TableCell className="font-semibold">
                            {item.dispatch_quantity || item.quantity || 0}
                          </TableCell>
                          <TableCell className="font-semibold">
                            ₹{item.amount?.toFixed(2) || '0.00'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {/* Total Amount */}
              <div className="flex justify-end p-4 bg-slate-50 rounded-lg">
                <div className="text-right">
                  <label className="text-sm font-semibold text-slate-600">Total Amount</label>
                  <p className="text-2xl font-bold text-slate-900">
                    ₹{viewingEntry.total_amount?.toFixed(2) || '0.00'}
                  </p>
                </div>
              </div>

              {/* Created/Updated Info */}
              <div className="text-xs text-slate-500 pt-4 border-t">
                <p>Created: {new Date(viewingEntry.created_at).toLocaleString()}</p>
                {viewingEntry.updated_at && (
                  <p>Updated: {new Date(viewingEntry.updated_at).toLocaleString()}</p>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default OutwardStockNew;
