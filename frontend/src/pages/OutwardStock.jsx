import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { SearchableSelect } from '../components/SearchableSelect';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Plus, Trash2, Eye, X, Ship, FileText, PackageX, Download } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import { createSafeOnValueChange, getSafeSelectContentProps } from '../utils/selectHelpers';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

const OutwardStock = () => {
  const [outwardEntries, setOutwardEntries] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [pis, setPIs] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [availableStock, setAvailableStock] = useState([]);
  const [pendingDispatchPlans, setPendingDispatchPlans] = useState([]);
  const [availableQuantities, setAvailableQuantities] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dispatch');
  
  // Dialog states
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [viewingEntry, setViewingEntry] = useState(null);

  const [formData, setFormData] = useState({
    export_invoice_no: '',
    // export_invoice_number: '', // NEW: Manually typed export invoice number
    date: new Date().toISOString().split('T')[0],
    company_id: '',
    pi_ids: [], // Changed from pi_id to pi_ids for multiple PI selection
    warehouse_id: '',
    mode: '', // Sea, Air
    containers_pallets: '', // Number of Containers (Sea) or Pallets (Air)
    dispatch_type: 'dispatch_plan', // dispatch_plan, export_invoice, direct_export
    dispatch_plan_id: '', // NEW: Link to dispatch plan for export invoice
    status: 'Pending Dispatch',
    line_items: [{
      product_id: '',
      product_name: '',
      sku: '',
      quantity: 0,
      rate: 0,
      amount: 0,
      dimensions: '',
      weight: 0
    }]
  });

  const { toast } = useToast();

  // Use custom hook to suppress ResizeObserver errors
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [outwardRes, companiesRes, pisRes, warehousesRes, stockRes, dispatchPlansRes] = await Promise.all([
        api.get('/outward-stock'),
        api.get('/companies'),
        api.get('/pi'),
        api.get('/warehouses'),
        api.get('/available-stock'),
        api.get('/outward-stock/dispatch-plans-pending')
      ]);
      setOutwardEntries(outwardRes.data || []);
      setCompanies(companiesRes.data || []);
      setPIs(pisRes.data || []);
      setWarehouses(warehousesRes.data || []);
      setAvailableStock(stockRes.data || []);
      setPendingDispatchPlans(dispatchPlansRes.data || []);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch data', variant: 'destructive' });
      // Set defaults on error
      setOutwardEntries([]);
      setCompanies([]);
      setPIs([]);
      setWarehouses([]);
      setAvailableStock([]);
      setPendingDispatchPlans([]);
    } finally {
      setLoading(false);
    }
  };

  const handlePISelect = async (piId) => {
    try {
      const pi = pis.find(p => p.id === piId);
      if (pi) {
        // Check if PI is already selected
        const isAlreadySelected = formData.pi_ids.includes(piId);
        
        if (isAlreadySelected) {
          // Remove PI from selection and its associated line items
          const updatedPIIds = formData.pi_ids.filter(id => id !== piId);
          const updatedLineItems = formData.line_items.filter(item => item.pi_id !== piId);
          
          setFormData(prev => ({
            ...prev,
            pi_ids: updatedPIIds,
            line_items: updatedLineItems.length > 0 ? updatedLineItems : [{
              product_id: '',
              product_name: '',
              sku: '',
              quantity: 0,
              rate: 0,
              amount: 0,
              dimensions: '',
              weight: 0
            }]
          }));
        } else {
          // Add PI to selection and merge line items
          const fullPI = await api.get(`/pi/${piId}`);
          const newLineItems = fullPI.data.line_items?.map(item => ({
            product_id: item.product_id,
            product_name: item.product_name,
            sku: item.sku,
            quantity: 0, // User will input export quantity
            rate: item.rate,
            amount: 0,
            dimensions: '',
            weight: 0,
            pi_id: piId, // Track which PI this item came from
            pi_voucher_no: pi.voucher_no
          })) || [];
          
          // Remove empty line items - filter out items without product_name or with pi_id
          const existingItems = formData.line_items.filter(item => 
            item.pi_id || (item.product_name && item.product_name.trim() !== '')
          );
          
          setFormData(prev => ({
            ...prev,
            pi_ids: [...prev.pi_ids, piId],
            company_id: pi.company_id || prev.company_id,
            line_items: [...existingItems, ...newLineItems]
          }));
        }
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch PI details', variant: 'destructive' });
    }
  };


  const handleDispatchPlanSelect = async (dispatchPlanId) => {
    if (!dispatchPlanId) {
      // Clear dispatch plan selection
      setFormData(prev => ({
        ...prev,
        dispatch_plan_id: '',
        pi_ids: [],
        line_items: [{
          product_id: '',
          product_name: '',
          sku: '',
          quantity: 0,
          rate: 0,
          amount: 0,
          dimensions: '',
          weight: 0
        }]
      }));
      setAvailableQuantities({});
      return;
    }

    try {
      const dispatchPlan = pendingDispatchPlans.find(dp => dp.id === dispatchPlanId);
      if (dispatchPlan) {
        // Auto-populate from dispatch plan
        const lineItems = dispatchPlan.line_items?.map(item => ({
          ...item,
          quantity: item.quantity // Pre-fill with dispatch plan quantity (user can modify)
        })) || [];

        setFormData(prev => ({
          ...prev,
          dispatch_plan_id: dispatchPlanId,
          company_id: dispatchPlan.company_id,
          warehouse_id: dispatchPlan.warehouse_id,
          pi_ids: dispatchPlan.pi_ids || [],
          mode: dispatchPlan.mode || '',
          line_items: lineItems.length > 0 ? lineItems : prev.line_items
        }));

        // Fetch available quantities for all products
        const quantities = {};
        for (const item of lineItems) {
          try {
            const res = await api.get(`/outward-stock/available-quantity/${item.product_id}?warehouse_id=${dispatchPlan.warehouse_id}`);
            quantities[item.product_id] = res.data.available_quantity;
          } catch (err) {
            console.error(`Failed to fetch quantity for ${item.product_id}`, err);
            quantities[item.product_id] = 0;
          }
        }
        setAvailableQuantities(quantities);

        toast({
          title: 'Dispatch Plan Selected',
          description: 'Products and quantities auto-populated. You can modify quantities as needed.'
        });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to load dispatch plan details', variant: 'destructive' });
    }
  };

  const fetchAvailableQuantity = async (productId, warehouseId) => {
    if (!productId || !warehouseId) return 0;
    try {
      const res = await api.get(`/outward-stock/available-quantity/${productId}?warehouse_id=${warehouseId}`);
      return res.data.available_quantity;
    } catch (error) {
      console.error('Failed to fetch available quantity', error);
      return 0;
    }
  };


  const handleLineItemChange = async (index, field, value) => {
    const newLineItems = [...formData.line_items];
    newLineItems[index][field] = value;
    
    // Auto-calculate amount
    if (field === 'quantity' || field === 'rate') {
      newLineItems[index].amount = newLineItems[index].quantity * newLineItems[index].rate;
    }
    
    // Fetch available quantity when product changes
    if (field === 'product_id' && value && formData.warehouse_id) {
      const availableQty = await fetchAvailableQuantity(value, formData.warehouse_id);
      setAvailableQuantities(prev => ({
        ...prev,
        [value]: availableQty
      }));
    }
    
    setFormData({ ...formData, line_items: newLineItems });
  };

  const addLineItem = () => {
    setFormData({
      ...formData,
      line_items: [...formData.line_items, {
        product_id: '',
        product_name: '',
        sku: '',
        quantity: 0,
        rate: 0,
        amount: 0,
        dimensions: '',
        weight: 0
      }]
    });
  };

  const removeLineItem = (index) => {
    if (formData.line_items.length > 1) {
      const newLineItems = formData.line_items.filter((_, i) => i !== index);
      setFormData({ ...formData, line_items: newLineItems });
    }
  };

  const getAvailableQuantity = (productId, warehouseId) => {
    // First check if we have fetched available quantity from new API
    if (availableQuantities[productId] !== undefined) {
      return availableQuantities[productId];
    }
    
    // Fallback to old method
    const stock = availableStock.find(s => 
      s.product_id === productId && s.warehouse_id === warehouseId
    );
    return stock ? stock.available_stock : 0;
  };

  const validateStock = () => {
    // Only validate items that have product_id, product_name, and quantity > 0
    const validItems = formData.line_items.filter(item => 
      item.product_id && item.product_name && item.quantity > 0
    );
    
    for (let item of validItems) {
      const available = getAvailableQuantity(item.product_id, formData.warehouse_id);
      if (item.quantity > available) {
        toast({
          title: 'Insufficient Stock',
          description: `${item.product_name} - Available: ${available}, Required: ${item.quantity}`,
          variant: 'destructive'
        });
        return false;
      }
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    console.log('Form submitted with data:', formData);
    
    // Validate required fields
    if (!formData.company_id) {
      toast({ title: 'Error', description: 'Please select a company', variant: 'destructive' });
      return;
    }
    
    if (!formData.warehouse_id) {
      toast({ title: 'Error', description: 'Please select a warehouse', variant: 'destructive' });
      return;
    }
    
    if (formData.dispatch_type !== 'direct_export' && formData.pi_ids.length === 0) {
      toast({ title: 'Error', description: 'Please select at least one PI', variant: 'destructive' });
      return;
    }
    
    // Validate line items - check if there's at least one valid line item with product name
    const validLineItems = formData.line_items.filter(item => item.product_name && item.product_name.trim() !== '');
    if (validLineItems.length === 0) {
      toast({ title: 'Error', description: 'Please add at least one product', variant: 'destructive' });
      return;
    }
    
    // Validate that valid line items have quantity > 0
    const itemsWithoutQuantity = validLineItems.filter(item => !item.quantity || item.quantity <= 0);
    if (itemsWithoutQuantity.length > 0) {
      toast({ 
        title: 'Error', 
        description: `Please enter quantity for: ${itemsWithoutQuantity.map(i => i.product_name).join(', ')}`, 
        variant: 'destructive' 
      });
      return;
    }
    
    // Validate stock availability (only for valid line items)
    if (!validateStock()) {
      return;
    }

    try {
      // Filter out empty line items before submission
      const validLineItems = formData.line_items.filter(item => 
        item.product_name && item.product_name.trim() !== '' && item.quantity > 0
      );
      
      // Prepare data for API
      const submitData = {
        ...formData,
        line_items: validLineItems, // Only send valid line items
        pi_id: formData.pi_ids.length > 0 ? formData.pi_ids[0] : null, // For backward compatibility, send first PI
        pi_ids: formData.pi_ids // Send multiple PIs
      };
      
      console.log('Submitting data to API:', submitData);
      
      if (editingEntry) {
        await api.put(`/outward-stock/${editingEntry.id}`, submitData);
        toast({ title: 'Success', description: 'Outward entry updated successfully' });
      } else {
        const response = await api.post('/outward-stock', submitData);
        console.log('API response:', response);
        toast({ title: 'Success', description: 'Outward entry created successfully' });
      }
      fetchData();
      setDialogOpen(false);
      resetForm();
    } catch (error) {
      console.error('Submit error:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Operation failed',
        variant: 'destructive',
      });
    }
  };

  const handleView = async (entry) => {
    try {
      const fullEntry = await api.get(`/outward-stock/${entry.id}`);
      setViewingEntry(fullEntry.data);
      setViewDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch entry details', variant: 'destructive' });
    }
  };

  const handleEdit = async (entry) => {
    try {
      const fullEntry = await api.get(`/outward-stock/${entry.id}`);
      setEditingEntry(fullEntry.data);
      setFormData({
        export_invoice_no: fullEntry.data.export_invoice_no,
        export_invoice_number: fullEntry.data.export_invoice_number || '',
        date: fullEntry.data.date.split('T')[0],
        company_id: fullEntry.data.company_id,
        pi_ids: fullEntry.data.pi_ids || (fullEntry.data.pi_id ? [fullEntry.data.pi_id] : []), // Support both old and new format
        warehouse_id: fullEntry.data.warehouse_id,
        mode: fullEntry.data.mode || '',
        containers_pallets: fullEntry.data.containers_pallets || '',
        dispatch_type: fullEntry.data.dispatch_type,
        status: fullEntry.data.status,
        line_items: fullEntry.data.line_items || []
      });
      setDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch entry details', variant: 'destructive' });
    }
  };

  const handleDelete = async (entry) => {
    if (window.confirm('Are you sure you want to delete this outward entry?')) {
      try {
        await api.delete(`/outward-stock/${entry.id}`);
        toast({ title: 'Success', description: 'Outward entry deleted successfully' });
        fetchData();
      } catch (error) {
        toast({ title: 'Error', description: 'Failed to delete entry', variant: 'destructive' });
      }
    }
  };

  const handleDownloadPDF = async (entry) => {
    try {
      console.log('Starting PDF download for entry:', entry.id);
      
      // Fetch full entry details
      const fullEntry = await api.get(`/outward-stock/${entry.id}`);
      const data = fullEntry.data;
      console.log('Fetched entry data:', data);
      
      // Create PDF
      const doc = new jsPDF();
      console.log('jsPDF instance created');
      
      // Title
      doc.setFontSize(18);
      doc.setFont('helvetica', 'bold');
      doc.text('DISPATCH PLAN', 105, 20, { align: 'center' });
      
      // Header Information
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      
      let yPos = 35;
      doc.text(`Reference No: ${data.export_invoice_no}`, 15, yPos);
      doc.text(`Date: ${new Date(data.date).toLocaleDateString()}`, 150, yPos);
      
      yPos += 8;
      doc.text(`Ship Mode: ${data.mode || 'N/A'}`, 15, yPos);
      const containerLabel = data.mode === 'Air' ? 'Pallets' : 'Containers';
      doc.text(`${containerLabel}: ${data.containers_pallets || 'N/A'}`, 150, yPos);
      
      yPos += 8;
      doc.text(`Status: ${data.status}`, 15, yPos);
      doc.text(`Warehouse: ${data.warehouse?.name || 'N/A'}`, 150, yPos);
      
      // Line Items Table
      yPos += 12;
      
      console.log('Preparing table data...');
      const tableData = data.line_items.map((item, index) => [
        index + 1,
        item.sku || 'N/A',
        item.product_name || 'N/A',
        item.quantity || 0,
        `Rs ${(item.rate || 0).toFixed(2)}`,
        `Rs ${(item.amount || 0).toFixed(2)}`,
        item.dimensions || 'N/A',
        item.weight || 0
      ]);
      
      console.log('Checking if autoTable exists:', typeof doc.autoTable);
      
      // Check if autoTable is available
      if (typeof doc.autoTable !== 'function') {
        throw new Error('autoTable plugin not loaded');
      }
      
      doc.autoTable({
        startY: yPos,
        head: [['#', 'SKU', 'Product Name', 'Quantity', 'Rate', 'Amount', 'Dimensions', 'Weight (kg)']],
        body: tableData,
        theme: 'striped',
        headStyles: { fillColor: [59, 130, 246], textColor: [255, 255, 255] },
        styles: { fontSize: 9 },
        columnStyles: {
          0: { halign: 'center', cellWidth: 10 },
          3: { halign: 'right' },
          4: { halign: 'right' },
          5: { halign: 'right' },
          7: { halign: 'right' }
        }
      });
      
      console.log('Table added to PDF');
      
      // Total Amount
      const totalAmount = data.line_items.reduce((sum, item) => sum + (item.amount || 0), 0);
      yPos = doc.lastAutoTable.finalY + 10;
      doc.setFontSize(11);
      doc.setFont('helvetica', 'bold');
      doc.text(`Total Amount: Rs ${totalAmount.toFixed(2)}`, 150, yPos);
      
      // Footer
      yPos = doc.internal.pageSize.height - 20;
      doc.setFontSize(8);
      doc.setFont('helvetica', 'italic');
      doc.text(`Generated on: ${new Date().toLocaleString()}`, 105, yPos, { align: 'center' });
      
      // Save PDF
      console.log('Saving PDF...');
      doc.save(`Dispatch_Plan_${data.export_invoice_no}.pdf`);
      console.log('PDF saved successfully');
      
      toast({ title: 'Success', description: 'PDF downloaded successfully' });
    } catch (error) {
      console.error('PDF generation error:', error);
      console.error('Error details:', error.message, error.stack);
      toast({ 
        title: 'Error', 
        description: `Failed to generate PDF: ${error.message}`, 
        variant: 'destructive' 
      });
    }
  };

  const resetForm = () => {
    const dispatchType = activeTab === 'dispatch' ? 'dispatch_plan' : activeTab === 'export' ? 'export_invoice' : 'direct_export';
    
    setFormData({
      export_invoice_no: '',
      export_invoice_number: '',
      date: new Date().toISOString().split('T')[0],
      company_id: '',
      pi_ids: [], // Reset to empty array
      warehouse_id: '',
      mode: '',
      containers_pallets: '',
      dispatch_type: dispatchType,
      dispatch_plan_id: '',
      status: 'Pending Dispatch',
      line_items: dispatchType === 'direct_export' ? [{
        product_id: '',
        product_name: '',
        sku: '',
        quantity: 0,
        rate: 0,
        amount: 0,
        dimensions: '',
        weight: 0
      }] : [] // Empty for PI-based types, will be populated when PI selected
    });
    setEditingEntry(null);
  };

  const openCreateDialog = (type) => {
    console.log('openCreateDialog called with type:', type);
    resetForm();
    setFormData(prev => ({
      ...prev,
      export_invoice_no: '',
      export_invoice_number: '',
      dispatch_type: type,
      mode: '',
      containers_pallets: '',
      line_items: type === 'direct_export' ? [{
        product_id: '',
        product_name: '',
        sku: '',
        quantity: 0,
        rate: 0,
        amount: 0,
        dimensions: '',
        weight: 0
      }] : [] // Start with empty array for PI-based types
    }));
    console.log('Setting dialogOpen to true');
    setDialogOpen(true);
    console.log('Dialog should be open now');
  };

  // Enhanced handler with explicit event handling for React 19 compatibility
  const handleCreateButtonClick = (event, type) => {
    console.log('Create button clicked, type:', type);
    event.preventDefault();
    event.stopPropagation();
    console.log('Opening dialog for type:', type);
    openCreateDialog(type);
  };

  const getTotalAmount = () => {
    return formData.line_items.reduce((sum, item) => sum + (item.amount || 0), 0).toFixed(2);
  };

  // Filter entries by type
  const dispatchEntries = outwardEntries.filter(e => e.dispatch_type === 'dispatch_plan');
  const exportEntries = outwardEntries.filter(e => e.dispatch_type === 'export_invoice');
  const directExportEntries = outwardEntries.filter(e => e.dispatch_type === 'direct_export');

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Outward Stock Operations</h1>
          <p className="text-slate-600 mt-1">Manage dispatch plans, export invoices, and direct exports</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="dispatch" className="flex items-center gap-2">
            <Ship size={16} />
            Dispatch Plan
          </TabsTrigger>
          <TabsTrigger value="export" className="flex items-center gap-2">
            <FileText size={16} />
            Export Invoice
          </TabsTrigger>
          <TabsTrigger value="direct" className="flex items-center gap-2">
            <PackageX size={16} />
            Direct Export
          </TabsTrigger>
        </TabsList>

        {/* Dispatch Plan Tab */}
        <TabsContent value="dispatch" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Dispatch Plans</h2>
            <Button 
              onClick={(e) => handleCreateButtonClick(e, 'dispatch_plan')}
              className="bg-blue-600 hover:bg-blue-700"
              type="button"
            >
              <Plus size={16} className="mr-2" />
              Create Dispatch Plan
            </Button>
          </div>
          
          <div className="border rounded-lg overflow-hidden bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Export Invoice No</TableHead>
                  {/* <TableHead>Export Invoice Number</TableHead> */}
                  <TableHead>Date</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>PI Reference</TableHead>
                  <TableHead>Warehouse</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Total Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dispatchEntries.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={11} className="text-center text-slate-500 py-8">
                      No dispatch plans found. Create your first dispatch plan.
                    </TableCell>
                  </TableRow>
                ) : (
                  dispatchEntries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="font-medium">{entry.export_invoice_no}</TableCell>
                      {/* <TableCell>{entry.export_invoice_number || '-'}</TableCell> */}
                      <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                      <TableCell>{entry.company?.name || '-'}</TableCell>
                      <TableCell>{entry.pi?.voucher_no || '-'}</TableCell>
                      <TableCell>{entry.warehouse?.name || '-'}</TableCell>
                      <TableCell>{entry.mode || '-'}</TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {entry.line_items_count} items
                        </div>
                      </TableCell>
                      <TableCell className="font-semibold">₹{entry.total_amount?.toFixed(2)}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          entry.status === 'Delivered' ? 'bg-green-100 text-green-800' :
                          entry.status === 'Dispatched' ? 'bg-blue-100 text-blue-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {entry.status}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => handleView(entry)} title="View">
                            <Eye size={16} className="text-blue-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDownloadPDF(entry)} title="Download PDF">
                            <Download size={16} className="text-green-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(entry)}>
                            Edit
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(entry)}>
                            <Trash2 size={16} className="text-red-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* Export Invoice Tab */}
        <TabsContent value="export" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Export Invoices</h2>
            <Button 
              onClick={(e) => handleCreateButtonClick(e, 'export_invoice')}
              className="bg-green-600 hover:bg-green-700"
              type="button"
            >
              <Plus size={16} className="mr-2" />
              Create Export Invoice
            </Button>
          </div>
          
          <div className="border rounded-lg overflow-hidden bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Export Invoice No</TableHead>
                  {/* <TableHead>Export Invoice Number</TableHead> */}
                  <TableHead>Date</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>PI Reference</TableHead>
                  <TableHead>Warehouse</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Total Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {exportEntries.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center text-slate-500 py-8">
                      No export invoices found. Create your first export invoice.
                    </TableCell>
                  </TableRow>
                ) : (
                  exportEntries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="font-medium">{entry.export_invoice_no}</TableCell>
                      <TableCell>{entry.export_invoice_number || '-'}</TableCell>
                      <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                      <TableCell>{entry.company?.name || '-'}</TableCell>
                      <TableCell>{entry.pi?.voucher_no || '-'}</TableCell>
                      <TableCell>{entry.warehouse?.name || '-'}</TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {entry.line_items_count} items
                        </div>
                      </TableCell>
                      <TableCell className="font-semibold">₹{entry.total_amount?.toFixed(2)}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          entry.status === 'Delivered' ? 'bg-green-100 text-green-800' :
                          entry.status === 'Dispatched' ? 'bg-blue-100 text-blue-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {entry.status}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => handleView(entry)} title="View">
                            <Eye size={16} className="text-blue-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDownloadPDF(entry)} title="Download PDF">
                            <Download size={16} className="text-green-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(entry)}>
                            Edit
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(entry)}>
                            <Trash2 size={16} className="text-red-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* Direct Export Tab */}
        <TabsContent value="direct" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Direct Export</h2>
            <Button 
              onClick={(e) => handleCreateButtonClick(e, 'direct_export')}
              className="bg-purple-600 hover:bg-purple-700"
              type="button"
            >
              <Plus size={16} className="mr-2" />
              Create Direct Export
            </Button>
          </div>
          
          <div className="border rounded-lg overflow-hidden bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Export Invoice No</TableHead>
                  {/* <TableHead>Export Invoice Number</TableHead> */}
                  <TableHead>Date</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Warehouse</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Total Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {directExportEntries.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-slate-500 py-8">
                      No direct exports found. Create your first direct export.
                    </TableCell>
                  </TableRow>
                ) : (
                  directExportEntries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="font-medium">{entry.export_invoice_no}</TableCell>
                      <TableCell>{entry.export_invoice_number || '-'}</TableCell>
                      <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                      <TableCell>{entry.company?.name || '-'}</TableCell>
                      <TableCell>{entry.warehouse?.name || '-'}</TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {entry.line_items_count} items
                        </div>
                      </TableCell>
                      <TableCell className="font-semibold">₹{entry.total_amount?.toFixed(2)}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          entry.status === 'Delivered' ? 'bg-green-100 text-green-800' :
                          entry.status === 'Dispatched' ? 'bg-blue-100 text-blue-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {entry.status}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => handleView(entry)} title="View">
                            <Eye size={16} className="text-blue-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDownloadPDF(entry)} title="Download PDF">
                            <Download size={16} className="text-green-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(entry)}>
                            Edit
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(entry)}>
                            <Trash2 size={16} className="text-red-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
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
                'Direct Export'
              }
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Header Information */}
            <div className="grid grid-cols-4 gap-4">
              <div>
                <Label>Export Invoice No</Label>
                <Input
                  value={formData.export_invoice_no}
                  onChange={(e) => setFormData({...formData, export_invoice_no: e.target.value})}
                  placeholder="Auto-generated if empty"
                />
              </div>
              {/* <div>
                <Label>Export Invoice Number</Label>
                <Input
                  value={formData.export_invoice_number || ''}
                  onChange={(e) => setFormData({...formData, export_invoice_number: e.target.value})}
                  placeholder="Enter export invoice number"
                />
              </div> */}
              <div>
                <Label>Date *</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({...formData, date: e.target.value})}
                  required
                />
              </div>
              <div>
                <Label>Company *</Label>
                <Select
                  value={formData.company_id}
                  onValueChange={createSafeOnValueChange(setFormData, 'company_id', formData)}
                  required
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select company" />
                  </SelectTrigger>
                  <SelectContent {...getSafeSelectContentProps()}>
                    {companies.map(company => (
                      <SelectItem key={company.id} value={company.id}>
                        {company.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* NEW: Dispatch Plan Selection for Export Invoice */}
              {formData.dispatch_type === 'export_invoice' && (
                <div className="col-span-2 bg-blue-50 p-3 rounded border border-blue-200">
                  <Label className="text-blue-800 font-semibold">Link to Dispatch Plan (Optional)</Label>
                  <Select
                    value={formData.dispatch_plan_id}
                    onValueChange={handleDispatchPlanSelect}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Dispatch Plan (or create new)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Create New (No Dispatch Plan)</SelectItem>
                      {(pendingDispatchPlans || []).map(dp => (
                        <SelectItem key={dp.id} value={dp.id}>
                          {dp.export_invoice_no} | {new Date(dp.date).toLocaleDateString()} | {dp.line_items_count} items
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {formData.dispatch_plan_id && (
                    <p className="text-xs text-blue-600 mt-1">
                      ✓ Products and quantities auto-filled from Dispatch Plan. You can modify as needed.
                    </p>
                  )}
                </div>
              )}
              
              {formData.dispatch_type !== 'direct_export' && (
                <div className="col-span-2">
                  <Label>PI Reference (Multiple Selection)</Label>
                  <div className="space-y-2">
                    <SearchableSelect
                      value=""
                      onValueChange={handlePISelect}
                      options={pis.map(pi => ({
                        value: pi.id,
                        label: `${pi.voucher_no} | ${new Date(pi.date).toLocaleDateString()}`
                      }))}
                      placeholder="Search and select PIs..."
                      searchPlaceholder="Search PI..."
                    />
                    {formData.pi_ids.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {formData.pi_ids.map(piId => {
                          const pi = pis.find(p => p.id === piId);
                          return pi ? (
                            <div key={piId} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm flex items-center gap-2">
                              {pi.voucher_no}
                              <button
                                type="button"
                                onClick={() => handlePISelect(piId)}
                                className="text-blue-600 hover:text-blue-800"
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
              )}
              <div>
                <Label>Warehouse *</Label>
                <Select
                  value={formData.warehouse_id}
                  onValueChange={createSafeOnValueChange(setFormData, 'warehouse_id', formData)}
                  required
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select warehouse" />
                  </SelectTrigger>
                  <SelectContent {...getSafeSelectContentProps()}>
                    {warehouses.map(warehouse => (
                      <SelectItem key={warehouse.id} value={warehouse.id}>
                        {warehouse.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Mode</Label>
                <Select
                  value={formData.mode}
                  onValueChange={createSafeOnValueChange(setFormData, 'mode', formData)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select mode" />
                  </SelectTrigger>
                  <SelectContent {...getSafeSelectContentProps()}>
                    <SelectItem value="Sea">Sea</SelectItem>
                    <SelectItem value="Air">Air</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>
                  {formData.mode === 'Air' ? 'Number of Pallets *' : formData.mode === 'Sea' ? 'Number of Containers *' : 'Containers/Pallets *'}
                </Label>
                <Input
                  type="number"
                  value={formData.containers_pallets}
                  onChange={(e) => setFormData({...formData, containers_pallets: e.target.value})}
                  placeholder={formData.mode === 'Air' ? 'Enter pallets' : formData.mode === 'Sea' ? 'Enter containers' : 'Select mode first'}
                  disabled={!formData.mode}
                  required={!!formData.mode}
                />
              </div>
              <div>
                <Label>Status</Label>
                <Select
                  value={formData.status}
                  onValueChange={createSafeOnValueChange(setFormData, 'status', formData)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent {...getSafeSelectContentProps()}>
                    <SelectItem value="Pending Dispatch">Pending Dispatch</SelectItem>
                    <SelectItem value="Dispatched">Dispatched</SelectItem>
                    <SelectItem value="Delivered">Delivered</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Line Items */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-lg font-semibold">Products / Line Items</Label>
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

                    {/* Conditional fields based on dispatch type */}
                    {formData.dispatch_type === 'dispatch_plan' ? (
                      // Dispatch Plan Fields: Product, SKU, Dispatch Quantity, Rate, Amount, Dimensions, Weight
                      <div className="grid grid-cols-6 gap-3">
                        <div>
                          <Label>Product Name *</Label>
                          <Input
                            value={item.product_name}
                            onChange={(e) => handleLineItemChange(index, 'product_name', e.target.value)}
                            placeholder="Enter product name"
                            required
                            disabled={formData.pi_ids.length > 0 && !editingEntry}
                          />
                        </div>
                        <div>
                          <Label>SKU</Label>
                          <Input
                            value={item.sku}
                            onChange={(e) => handleLineItemChange(index, 'sku', e.target.value)}
                            placeholder="SKU"
                            disabled={formData.pi_ids.length > 0 && !editingEntry}
                          />
                        </div>
                        <div>
                          <Label>Dispatch Quantity *</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.quantity || ''}
                            onChange={(e) => handleLineItemChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                            placeholder="Dispatch quantity"
                            required
                          />
                        </div>
                        <div>
                          <Label>Rate</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.rate || ''}
                            onChange={(e) => handleLineItemChange(index, 'rate', parseFloat(e.target.value) || 0)}
                            placeholder="Rate"
                            disabled={formData.pi_ids.length > 0 && !editingEntry}
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
                          <Label>Dimensions</Label>
                          <Input
                            value={item.dimensions}
                            onChange={(e) => handleLineItemChange(index, 'dimensions', e.target.value)}
                            placeholder="L x W x H"
                          />
                        </div>
                        <div>
                          <Label>Weight (kg)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.weight || ''}
                            onChange={(e) => handleLineItemChange(index, 'weight', parseFloat(e.target.value) || 0)}
                            placeholder="Weight"
                          />
                        </div>
                      </div>
                    ) : formData.dispatch_type === 'export_invoice' ? (
                      // Export Invoice Fields: Product, SKU, Available Quantity, Rate, Export Quantity, Total Amount
                      <div className="grid grid-cols-6 gap-3">
                        <div>
                          <Label>Product Name *</Label>
                          <Input
                            value={item.product_name}
                            onChange={(e) => handleLineItemChange(index, 'product_name', e.target.value)}
                            placeholder="Enter product name"
                            required
                            disabled={formData.pi_ids.length > 0 && !editingEntry}
                          />
                        </div>
                        <div>
                          <Label>SKU</Label>
                          <Input
                            value={item.sku}
                            onChange={(e) => handleLineItemChange(index, 'sku', e.target.value)}
                            placeholder="SKU"
                            disabled={formData.pi_ids.length > 0 && !editingEntry}
                          />
                        </div>
                        <div>
                          <Label>Available Quantity</Label>
                          <Input
                            value={formData.warehouse_id && item.product_id ? getAvailableQuantity(item.product_id, formData.warehouse_id) : '0'}
                            disabled
                            className="bg-green-50 font-semibold text-green-800"
                          />
                        </div>
                        <div>
                          <Label>Rate</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.rate || ''}
                            onChange={(e) => handleLineItemChange(index, 'rate', parseFloat(e.target.value) || 0)}
                            placeholder="Rate"
                            disabled={formData.pi_ids.length > 0 && !editingEntry}
                          />
                        </div>
                        <div>
                          <Label>Export Quantity *</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.quantity || ''}
                            onChange={(e) => handleLineItemChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                            placeholder="Export quantity"
                            required
                            className={
                              formData.warehouse_id && item.product_id && 
                              item.quantity > getAvailableQuantity(item.product_id, formData.warehouse_id)
                                ? 'border-red-500 bg-red-50'
                                : ''
                            }
                          />
                          {formData.warehouse_id && item.product_id && (
                            <div className={`text-xs mt-1 ${
                              item.quantity > getAvailableQuantity(item.product_id, formData.warehouse_id)
                                ? 'text-red-600 font-semibold'
                                : 'text-slate-500'
                            }`}>
                              Max: {getAvailableQuantity(item.product_id, formData.warehouse_id)}
                              {item.quantity > getAvailableQuantity(item.product_id, formData.warehouse_id) && 
                                ' ⚠️ Exceeds available!'}
                            </div>
                          )}
                        </div>
                        <div>
                          <Label>Total Amount (Auto-calc)</Label>
                          <Input
                            value={`₹${item.amount.toFixed(2)}`}
                            disabled
                            className="bg-blue-50 font-semibold"
                          />
                        </div>
                      </div>
                    ) : (
                      // Direct Export Fields: Product, SKU, Quantity, Rate, Total Amount (no PI linkage)
                      <div className="grid grid-cols-5 gap-3">
                        <div>
                          <Label>Product Name *</Label>
                          <Input
                            value={item.product_name}
                            onChange={(e) => handleLineItemChange(index, 'product_name', e.target.value)}
                            placeholder="Enter product name"
                            required
                          />
                        </div>
                        <div>
                          <Label>SKU</Label>
                          <Input
                            value={item.sku}
                            onChange={(e) => handleLineItemChange(index, 'sku', e.target.value)}
                            placeholder="SKU"
                          />
                        </div>
                        <div>
                          <Label>Export Quantity *</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.quantity || ''}
                            onChange={(e) => handleLineItemChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                            placeholder="Export quantity"
                            required
                          />
                          {formData.warehouse_id && item.product_id && (
                            <div className="text-xs text-slate-500 mt-1">
                              Available: {getAvailableQuantity(item.product_id, formData.warehouse_id)}
                            </div>
                          )}
                        </div>
                        <div>
                          <Label>Rate *</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.rate || ''}
                            onChange={(e) => handleLineItemChange(index, 'rate', parseFloat(e.target.value) || 0)}
                            placeholder="Rate"
                            required
                          />
                        </div>
                        <div>
                          <Label>Total Amount (Auto-calc)</Label>
                          <Input
                            value={`₹${item.amount.toFixed(2)}`}
                            disabled
                            className="bg-blue-50 font-semibold"
                          />
                        </div>
                      </div>
                    )}
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
              <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                {editingEntry ? 'Update' : 'Create'} Entry
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>View Outward Stock Details</DialogTitle>
          </DialogHeader>
          
          {viewingEntry && (
            <div className="space-y-6">
              {/* Entry Header Information */}
              <div className="bg-slate-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Export Information</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Export Invoice No</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-semibold">
                      {viewingEntry.export_invoice_no}
                    </div>
                  </div>
                  {/* <div>
                    <Label className="text-sm font-medium text-slate-600">Export Invoice Number</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-semibold">
                      {viewingEntry.export_invoice_number || '-'}
                    </div>
                  </div> */}
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Date</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {new Date(viewingEntry.date).toLocaleDateString()}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Type</Label>
                    <div className="mt-1">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        viewingEntry.dispatch_type === 'dispatch_plan' ? 'bg-blue-100 text-blue-800' :
                        viewingEntry.dispatch_type === 'export_invoice' ? 'bg-green-100 text-green-800' :
                        'bg-purple-100 text-purple-800'
                      }`}>
                        {viewingEntry.dispatch_type === 'dispatch_plan' ? 'Dispatch Plan' :
                         viewingEntry.dispatch_type === 'export_invoice' ? 'Export Invoice' : 'Direct Export'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Company</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingEntry.company?.name || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Warehouse</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingEntry.warehouse?.name || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Mode</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingEntry.mode || 'Not specified'}
                    </div>
                  </div>
                </div>
              </div>

              {/* PI Information */}
              {viewingEntry.pi && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4 text-blue-800">PI Reference Information</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-sm font-medium text-blue-600">PI Voucher No</Label>
                      <div className="mt-1 p-2 bg-white rounded border">
                        {viewingEntry.pi.voucher_no}
                      </div>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-blue-600">PI Date</Label>
                      <div className="mt-1 p-2 bg-white rounded border">
                        {new Date(viewingEntry.pi.date).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Line Items */}
              <div>
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Line Items</h3>
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-slate-100">
                      <tr>
                        <th className="text-left p-3 font-medium text-slate-700">Product Name</th>
                        <th className="text-left p-3 font-medium text-slate-700">SKU</th>
                        <th className="text-right p-3 font-medium text-slate-700">Quantity</th>
                        <th className="text-right p-3 font-medium text-slate-700">Rate</th>
                        <th className="text-right p-3 font-medium text-slate-700">Amount</th>
                        <th className="text-left p-3 font-medium text-slate-700">Dimensions</th>
                        <th className="text-right p-3 font-medium text-slate-700">Weight</th>
                      </tr>
                    </thead>
                    <tbody>
                      {viewingEntry.line_items?.map((item, index) => (
                        <tr key={index} className="border-t">
                          <td className="p-3">{item.product_name}</td>
                          <td className="p-3 font-mono text-sm">{item.sku}</td>
                          <td className="p-3 text-right">{item.quantity}</td>
                          <td className="p-3 text-right">₹{item.rate?.toFixed(2)}</td>
                          <td className="p-3 text-right font-semibold">₹{item.amount?.toFixed(2)}</td>
                          <td className="p-3">{item.dimensions || '-'}</td>
                          <td className="p-3 text-right">{item.weight ? `${item.weight} kg` : '-'}</td>
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
                      ₹{viewingEntry.line_items?.reduce((sum, item) => sum + (item.amount || 0), 0).toFixed(2)}
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
    </div>
  );
};

export default OutwardStock;