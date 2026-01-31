import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { SearchableSelect } from '../components/SearchableSelect';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Plus, Trash2, Eye, X, Package, Truck, Warehouse as WarehouseIcon, Search, Filter, Save, RefreshCw } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import BulkActionToolbar from '../components/BulkActionToolbar';
import DeleteConfirmDialog from '../components/DeleteConfirmDialog';
import { exportToCSV, exportToExcel, formatDataForExport } from '../utils/exportUtils';

const InwardStock = () => {
  const [inwardEntries, setInwardEntries] = useState([]);
  const [pos, setPos] = useState([]);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pickup');

  // Pick-up (In-Transit) state
  const [selectedPo, setSelectedPo] = useState('');
  const [poLineStats, setPoLineStats] = useState(null);
  const [pickupEntries, setPickupEntries] = useState([]);
  // console.log("this is pickupEntries", pickupEntries);
  const [pickupFormData, setPickupFormData] = useState({
    pickup_date: new Date().toISOString().split('T')[0],
    manual: '',
    notes: '',
    line_items: []
  });


  // Warehouse Inward state
  const [selectedWarehousePo, setSelectedWarehousePo] = useState('');
  const [warehousePoLineStats, setWarehousePoLineStats] = useState(null);
  const [warehouseEntries, setWarehouseEntries] = useState([]);
  const [warehouseInwardFormData, setWarehouseInwardFormData] = useState({
    warehouse_id: '',
    inward_date: new Date().toISOString().split('T')[0],
    inward_invoice_no: '',
    line_items: []
  });
  const [warehouseFilter, setWarehouseFilter] = useState('all');

  // Search and Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    warehouse: 'all',
    inwardType: 'all'
  });
  const [filteredInward, setFilteredInward] = useState([]);

  // Dialog states
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  // Inward and done dialogs removed - in-transit feature deprecated
  const [editingEntry, setEditingEntry] = useState(null);
  const [viewingEntry, setViewingEntry] = useState(null);
  const [selectedPickupEntry, setSelectedPickupEntry] = useState(null);
  const [pickupViewOpen, setPickupViewOpen] = useState(false);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState('');

  // Bulk operations state
  const [selectedPickupIds, setSelectedPickupIds] = useState([]);
  const [selectedWarehouseIds, setSelectedWarehouseIds] = useState([]);
  const [selectedDirectIds, setSelectedDirectIds] = useState([]);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState(null);

  //modal

  const [formData, setFormData] = useState({
    inward_invoice_no: '',
    date: new Date().toISOString().split('T')[0],
    po_id: '',
    po_ids: [], // Array for multiple PO selection
    warehouse_id: '',
    inward_type: 'warehouse', // warehouse, direct
    source_type: 'warehouse_inward', // warehouse_inward, direct_inward
    line_items: [{
      product_id: '',
      product_name: '',
      sku: '',
      quantity: 0,
      rate: 0,
      amount: 0
    }]
  });

  const { toast } = useToast();

  // Use custom hook to suppress ResizeObserver errors
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchData();
    fetchWarehouseEntries();
  }, []);

  // Apply search and filters
  useEffect(() => {
    let filtered = [...inwardEntries];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(item =>
        item.inward_invoice_no?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.po_no?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.line_items?.some(li =>
          li.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          li.sku?.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }

    // Date range filter
    if (filters.dateFrom) {
      filtered = filtered.filter(item => new Date(item.date) >= new Date(filters.dateFrom));
    }
    if (filters.dateTo) {
      filtered = filtered.filter(item => new Date(item.date) <= new Date(filters.dateTo));
    }

    // Warehouse filter
    if (filters.warehouse !== 'all') {
      filtered = filtered.filter(item => item.warehouse_id === filters.warehouse);
    }

    // Inward Type filter
    if (filters.inwardType !== 'all') {
      filtered = filtered.filter(item => item.inward_type === filters.inwardType);
    }

    setFilteredInward(filtered);
  }, [inwardEntries, searchTerm, filters]);

  const fetchData = async () => {
    try {
      const [inwardRes, posRes, productsRes, warehousesRes, pickupsRes] = await Promise.all([
        api.get('/inward-stock').catch(err => {
          console.error('Failed to fetch inward stock:', err);
          return { data: [] };
        }),
        api.get('/purchase-orders').catch(err => {
          console.error('Failed to fetch purchase orders:', err);
          return { data: [] };
        }),
        api.get('/products').catch(err => {
          console.error('Failed to fetch products:', err);
          return { data: [] };
        }),
        api.get('/warehouses').catch(err => {
          console.error('Failed to fetch warehouses:', err);
          return { data: [] };
        }),
        api.get('/pickups').catch(err => {
          console.error('Failed to fetch pickups:', err);
          return { data: [] };
        })
      ]);

      // Safely set data with Array validation
      setInwardEntries(Array.isArray(inwardRes.data) ? inwardRes.data : []);
      setPos(Array.isArray(posRes.data) ? posRes.data : []);
      setProducts(Array.isArray(productsRes.data) ? productsRes.data : []);
      setWarehouses(Array.isArray(warehousesRes.data) ? warehousesRes.data : []);
      setPickupEntries(Array.isArray(pickupsRes.data) ? pickupsRes.data : []);

      // Show warning if any critical data is missing
      if (!Array.isArray(posRes.data) || posRes.data.length === 0) {
        toast({
          title: 'Warning',
          description: 'No Purchase Orders found. Create a PO first to proceed with inward entries.',
          variant: 'default'
        });
      }
    } catch (error) {
      console.error('Inward Stock fetch error:', error);
      toast({
        title: 'Error',
        description: 'Unable to load data. Please refresh the page or contact support.',
        variant: 'destructive'
      });
      // Set empty arrays as fallback to prevent crashes
      setInwardEntries([]);
      setPos([]);
      setProducts([]);
      setWarehouses([]);
      setPickupEntries([]);
    } finally {
      setLoading(false);
    }
  };

  // Pick-up (In-Transit) Functions
  const fetchPickupEntries = async () => {
    try {
      const response = await api.get('/pickups');
      setPickupEntries(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Failed to fetch pickup entries:', error);
    }
  };

  // const handlePoSelection = async (voucher_no) => {
  //   if (!voucher_no) {
  //     setSelectedPo('');
  //     setPoLineStats(null);
  //     setPickupFormData({
  //       pickup_date: new Date().toISOString().split('T')[0],
  //       manual: '',
  //       notes: '',
  //       line_items: []
  //     });
  //     return;
  //   }

  //   try {
  //     setSelectedPo(voucher_no);
  //     const response = await api.get(`/pos/lines-with-stats?voucher_no=${encodeURIComponent(voucher_no)}`);
  //     setPoLineStats(response.data);

  //     // Initialize form data with line items
  //     const lineItems = response.data.line_items.map(item => ({
  //       id: item.id,
  //       product_id: item.product_id,
  //       product_name: item.product_name,
  //       sku: item.sku,
  //       quantity: 0,
  //       rate: item.rate,
  //       pi_quantity: item.pi_quantity,
  //       po_quantity: item.po_quantity,
  //       already_inwarded: item.already_inwarded,
  //       in_transit: item.in_transit,
  //       available_for_pickup: item.available_for_pickup
  //     }));

  //     setPickupFormData(prev => ({
  //       ...prev,
  //       line_items: lineItems
  //     }));
  //   } catch (error) {
  //     console.error('Failed to fetch PO line stats:', error);
  //     toast({
  //       title: 'Error',
  //       description: error.response?.data?.detail || 'Failed to load PO details',
  //       variant: 'destructive'
  //     });
  //   }
  // };

  const handlePoSelection = async (voucher_no) => {
    if (!voucher_no) {
      setSelectedPo('');
      setPoLineStats(null);
      setPickupFormData({
        pickup_date: new Date().toISOString().split('T')[0],
        manual: '',
        notes: '',
        line_items: []
      });
      return;
    }

    try {
      setSelectedPo(voucher_no);
      const response = await api.get(`/pos/lines-with-stats?voucher_no=${encodeURIComponent(voucher_no)}`);
      setPoLineStats(response.data);

      // 🔍 DEBUG: Check what the API returns
      console.log('API Response:', response.data);
      console.log('Line Items from API:', response.data.line_items);

      // Initialize form data with line items
      const lineItems = response.data.line_items.map(item => {
        // 🔍 DEBUG: Check each item's id
        console.log('Item ID:', item.id, 'Product:', item.product_name);

        return {
          id: item.id, // ✅ PO line item ID - MUST be present in API response
          product_id: item.product_id,
          product_name: item.product_name,
          sku: item.sku,
          quantity: 0,
          rate: item.rate,
          pi_quantity: item.pi_quantity,
          po_quantity: item.po_quantity,
          already_inwarded: item.already_inwarded,
          in_transit: item.in_transit,
          available_for_pickup: item.available_for_pickup
        };
      });

      // 🔍 DEBUG: Check the mapped line items
      console.log('Mapped Line Items:', lineItems);

      setPickupFormData(prev => ({
        ...prev,
        line_items: lineItems
      }));
    } catch (error) {
      console.error('Failed to fetch PO line stats:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to load PO details',
        variant: 'destructive'
      });
    }
  };

  const handlePickupQuantityChange = (index, value) => {
    const newQuantity = parseFloat(value) || 0;
    const lineItem = pickupFormData.line_items[index];

    // Validation: Check if new quantity exceeds available
    if (newQuantity > lineItem.available_for_pickup) {
      toast({
        title: 'Invalid Quantity',
        description: `Cannot exceed available quantity (${lineItem.available_for_pickup}) for ${lineItem.product_name}`,
        variant: 'destructive'
      });
      return;
    }

    const updatedLineItems = [...pickupFormData.line_items];
    updatedLineItems[index].quantity = newQuantity;
    setPickupFormData(prev => ({ ...prev, line_items: updatedLineItems }));
  };

  // const handlePickupSubmit = async (e) => {
  //   e.preventDefault();

  //   if (!poLineStats) {
  //     toast({
  //       title: 'Error',
  //       description: 'Please select a Purchase Order first',
  //       variant: 'destructive'
  //     });
  //     return;
  //   }

  //   // Filter line items with quantity > 0
  //   const validLineItems = pickupFormData.line_items.filter(item => item.quantity > 0);

  //   if (validLineItems.length === 0) {
  //     toast({
  //       title: 'Error',
  //       description: 'Please enter at least one quantity greater than 0',
  //       variant: 'destructive'
  //     });
  //     return;
  //   }

  //   try {
  //     const pickupData = {
  //       po_id: poLineStats.po_id,
  //       pickup_date: pickupFormData.pickup_date,
  //       manual: pickupFormData.manual,
  //       notes: pickupFormData.notes,
  //       line_items: validLineItems.map(item => ({
  //         id: item.id,
  //         product_name: item.product_name,
  //         sku: item.sku,
  //         quantity: item.quantity,
  //         rate: item.rate
  //       }))
  //     };

  //     await api.post('/pickups', pickupData);

  //     toast({
  //       title: 'Success',
  //       description: 'Pickup (In-Transit) entry created successfully',
  //       variant: 'default'
  //     });

  //     // Reset form and refresh data
  //     setSelectedPo('');
  //     setPoLineStats(null);
  //     setPickupFormData({
  //       pickup_date: new Date().toISOString().split('T')[0],
  //       notes: '',
  //       line_items: []
  //     });
  //     fetchPickupEntries();
  //   } catch (error) {
  //     console.error('Failed to create pickup:', error);
  //     toast({
  //       title: 'Error',
  //       description: error.response?.data?.detail || 'Failed to create pickup entry',
  //       variant: 'destructive'
  //     });
  //   }
  // };

  const handlePickupSubmit = async (e) => {
    e.preventDefault();

    if (!poLineStats) {
      toast({
        title: 'Error',
        description: 'Please select a Purchase Order first',
        variant: 'destructive'
      });
      return;
    }

    // Filter line items with quantity > 0
    const validLineItems = pickupFormData.line_items.filter(item => item.quantity > 0);

    if (validLineItems.length === 0) {
      toast({
        title: 'Error',
        description: 'Please enter at least one quantity greater than 0',
        variant: 'destructive'
      });
      return;
    }

    try {
      const pickupData = {
        po_id: poLineStats.po_id,
        pickup_date: pickupFormData.pickup_date,
        manual: pickupFormData.manual,
        notes: pickupFormData.notes,
        line_items: validLineItems.map(item => ({
          id: item.id, // ✅ PO line item ID (not product_id)
          product_name: item.product_name,
          sku: item.sku,
          quantity: item.quantity,
          rate: item.rate
        }))
      };

      // 🔍 DEBUG: Check the payload before sending
      console.log('Pickup Data Being Sent:', pickupData);
      console.log('Line Items in Payload:', pickupData.line_items);

      await api.post('/pickups', pickupData);

      toast({
        title: 'Success',
        description: 'Pickup (In-Transit) entry created successfully',
        variant: 'default'
      });

      // Reset form and refresh data
      setSelectedPo('');
      setPoLineStats(null);
      setPickupFormData({
        pickup_date: new Date().toISOString().split('T')[0],
        manual: '',
        notes: '',
        line_items: []
      });
      fetchPickupEntries();
    } catch (error) {
      console.error('Failed to create pickup:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create pickup entry',
        variant: 'destructive'
      });
    }
  };

  const handleDeletePickup = async (pickupId) => {
    if (!window.confirm('Are you sure you want to delete this pickup entry?')) {
      return;
    }

    try {
      await api.delete(`/pickups/${pickupId}`);
      toast({
        title: 'Success',
        description: 'Pickup entry deleted successfully',
        variant: 'default'
      });
      fetchPickupEntries();

      // Refresh PO line stats if a PO is selected
      if (selectedPo) {
        handlePoSelection(selectedPo);
      }
    } catch (error) {
      console.error('Failed to delete pickup:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete pickup entry',
        variant: 'destructive'
      });
    }
  };

  const handleViewPickup = (entry) => {
    setSelectedPickupEntry(entry);
    setPickupViewOpen(true);
  };


  //this is for the section where we are adding the transit to inward

  const handleInwardPickup = async (pickupId) => {
    if (!window.confirm("Are you sure you want to inward this pickup?")) {
      return;
    }

    try {
      const res = await api.post(
        `${pickupId}/inward`
      );

      toast({
        title: "Success",
        description: res.data.message || "Inward completed successfully",
        variant: "default",
      });

      // Refresh pickup list
      fetchPickupEntries();

      // Optional: refresh PO stats
      if (selectedPo) {
        handlePoSelection(selectedPo);
      }

    } catch (error) {
      console.error("Inward failed:", error);

      toast({
        title: "Error",
        description:
          error.response?.data?.detail || "Failed to inward pickup",
        variant: "destructive",
      });
    }
  };



  // Warehouse Inward Functions
  const fetchWarehouseEntries = async () => {
    try {
      const response = await api.get('/inward-stock?inward_type=warehouse');
      setWarehouseEntries(Array.isArray(response.data) ? response.data : []);
      // console.log("here is the response of the warehouse", response.data);
    } catch (error) {
      console.error('Failed to fetch warehouse entries:', error);
    }
  };

  const handleWarehousePoSelection = async (voucher_no) => {
    if (!voucher_no) {
      setSelectedWarehousePo('');
      setWarehousePoLineStats(null);
      setWarehouseInwardFormData({
        warehouse_id: '',
        inward_date: new Date().toISOString().split('T')[0],
        inward_invoice_no: '',
        line_items: []
      });
      return;
    }

    try {
      setSelectedWarehousePo(voucher_no);
      const response = await api.get(`/pos/lines-with-stats?voucher_no=${encodeURIComponent(voucher_no)}`);
      console.log("this is the posline with stats ", response);

      setWarehousePoLineStats(response.data);

      // Initialize form data with line items
      const lineItems = response.data.line_items.map(item => ({
        id: item.id,
        product_id: item.product_id,
        product_name: item.product_name,
        sku: item.sku,
        pi_quantity: item.pi_quantity,
        po_quantity: item.po_quantity,
        already_inwarded: item.already_inwarded,
        in_transit: item.in_transit,
        new_inward_qty: 0,
        rate: item.rate
      }));

      setWarehouseInwardFormData(prev => ({
        ...prev,
        line_items: lineItems
      }));
    } catch (error) {
      console.error('Failed to fetch PO line stats:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to load PO details',
        variant: 'destructive'
      });
    }
  };

  const handleWarehouseInwardQuantityChange = (index, value) => {
    const newQuantity = parseFloat(value) || 0;
    const lineItem = warehouseInwardFormData.line_items[index];
    const remainingAllowed = lineItem.po_quantity - lineItem.already_inwarded - lineItem.in_transit;

    // Validation: Check if new quantity exceeds remaining allowed
    if (newQuantity > remainingAllowed) {
      toast({
        title: 'Invalid Quantity',
        description: `Inward qty exceeds remaining allowed for SKU ${lineItem.sku}. Remaining allowed: ${remainingAllowed}`,
        variant: 'destructive'
      });
      return;
    }

    const updatedLineItems = [...warehouseInwardFormData.line_items];
    updatedLineItems[index].new_inward_qty = newQuantity;
    setWarehouseInwardFormData(prev => ({ ...prev, line_items: updatedLineItems }));
  };

  const handleWarehouseInwardSubmit = async (e) => {
    e.preventDefault();

    if (!warehousePoLineStats) {
      toast({
        title: 'Error',
        description: 'Please select a Purchase Order first',
        variant: 'destructive'
      });
      return;
    }

    if (!warehouseInwardFormData.warehouse_id) {
      toast({
        title: 'Error',
        description: 'Please select a Warehouse',
        variant: 'destructive'
      });
      return;
    }

    // Filter line items with quantity > 0
    const validLineItems = warehouseInwardFormData.line_items.filter(item => item.new_inward_qty > 0);

    if (validLineItems.length === 0) {
      toast({
        title: 'Error',
        description: 'Please enter at least one quantity greater than 0',
        variant: 'destructive'
      });
      return;
    }

    // Validate remaining allowed
    for (const item of validLineItems) {
      const remainingAllowed = item.po_quantity - item.already_inwarded - item.in_transit;
      if (item.new_inward_qty > remainingAllowed) {
        toast({
          title: 'Validation Error',
          description: `Inward qty exceeds remaining allowed for SKU ${item.sku}. Remaining allowed: ${remainingAllowed}`,
          variant: 'destructive'
        });
        return;
      }
    }

    try {
      const inwardData = {
        po_voucher_no: warehousePoLineStats.po_voucher_no,
        po_id: warehousePoLineStats.po_id,
        warehouse_id: warehouseInwardFormData.warehouse_id,
        date: warehouseInwardFormData.inward_date,
        inward_invoice_no: warehouseInwardFormData.inward_invoice_no || `INW-${Date.now()}`,
        inward_type: 'warehouse',
        line_items: validLineItems.map(item => ({
          id: item.id,
          product_id: item.product_id,
          product_name: item.product_name,
          sku: item.sku,
          quantity: item.new_inward_qty,
          rate: item.rate
        }))
      };

      await api.post('/inward-stock', inwardData);

      toast({
        title: 'Success',
        description: 'Warehouse inward entry created successfully',
        variant: 'default'
      });

      // Reset form and refresh data
      setSelectedWarehousePo('');
      setWarehousePoLineStats(null);
      setWarehouseInwardFormData({
        warehouse_id: '',
        inward_date: new Date().toISOString().split('T')[0],
        inward_invoice_no: '',
        line_items: []
      });
      fetchWarehouseEntries();
      fetchData(); // Refresh all data including stock summary
    } catch (error) {
      console.error('Failed to create warehouse inward:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create warehouse inward entry',
        variant: 'destructive'
      });
    }
  };

  // Calculate totals for filtered data
  const calculateTotals = () => {
    const totalQuantity = filteredInward.reduce((sum, item) => {
      const itemTotal = item.line_items?.reduce((s, li) => s + (parseFloat(li.quantity) || 0), 0) || 0;
      return sum + itemTotal;
    }, 0);

    const totalAmount = filteredInward.reduce((sum, item) => {
      const itemTotal = item.line_items?.reduce((s, li) => s + (parseFloat(li.amount) || 0), 0) || 0;
      return sum + itemTotal;
    }, 0);

    return { totalQuantity, totalAmount: totalAmount.toFixed(2) };
  };

  const resetFilters = () => {
    setSearchTerm('');
    setFilters({
      dateFrom: '',
      dateTo: '',
      warehouse: 'all',
      inwardType: 'all'
    });
  };

  const handlePOSelect = async (selectedPoIds) => {
    try {
      if (!Array.isArray(selectedPoIds) || selectedPoIds.length === 0) {
        setFormData(prev => ({
          ...prev,
          po_ids: [],
          pi_id: '',
          line_items: [{
            product_id: '',
            product_name: '',
            sku: '',
            quantity: 0,
            rate: 0,
            amount: 0
          }]
        }));
        return;
      }

      // Aggregate data from all selected POs
      const aggregatedProducts = new Map();
      const piQuantitiesMap = new Map();
      const alreadyInwardedMap = new Map();
      const allLinkedPIs = [];

      // Process each selected PO
      for (const poId of selectedPoIds) {
        try {
          const fullPO = await api.get(`/po/${poId}`);
          const poData = fullPO.data;

          // Get linked PIs (support both single and multiple)
          const linkedPIs = poData.reference_pis || [];
          allLinkedPIs.push(...linkedPIs);

          // Fetch all PIs to get PI quantities
          if (Array.isArray(linkedPIs) && linkedPIs.length > 0) {
            for (const linkedPI of linkedPIs) {
              try {
                const piResponse = await api.get(`/pi/${linkedPI.id}`);
                const piData = piResponse.data || {};

                // Aggregate PI quantities by product
                piData.line_items?.forEach(item => {
                  const productKey = item.product_id;
                  if (piQuantitiesMap.has(productKey)) {
                    piQuantitiesMap.set(productKey, piQuantitiesMap.get(productKey) + (item.quantity || 0));
                  } else {
                    piQuantitiesMap.set(productKey, item.quantity || 0);
                  }
                });
              } catch (err) {
                console.error('Error fetching PI:', err);
              }
            }
          }

          // Fetch already inwarded quantities for this PO
          try {
            const inwardResponse = await api.get('/inward-stock');
            const inwardEntries = inwardResponse.data.filter(entry => entry.po_id === poId);

            inwardEntries.forEach(entry => {
              entry.line_items?.forEach(item => {
                const productKey = item.product_id;
                if (alreadyInwardedMap.has(productKey)) {
                  alreadyInwardedMap.set(productKey, alreadyInwardedMap.get(productKey) + (item.quantity || 0));
                } else {
                  alreadyInwardedMap.set(productKey, item.quantity || 0);
                }
              });
            });
          } catch (err) {
            console.error('Error fetching inward stock:', err);
          }

          // Aggregate line items from this PO
          poData.line_items?.forEach(item => {
            const productKey = item.product_id;
            if (aggregatedProducts.has(productKey)) {
              const existing = aggregatedProducts.get(productKey);
              existing.po_quantity += item.quantity || 0;
              // Keep the rate from first PO (or could average)
            } else {
              aggregatedProducts.set(productKey, {
                product_id: item.product_id,
                product_name: item.product_name,
                sku: item.sku,
                po_quantity: item.quantity || 0,
                rate: item.rate || 0
              });
            }
          });
        } catch (err) {
          console.error(`Error fetching PO ${poId}:`, err);
          toast({
            title: 'Error',
            description: `Failed to fetch PO details for ${poId}`,
            variant: 'destructive'
          });
        }
      }

      // Convert aggregated products to line items
      const lineItemsFromPOs = Array.from(aggregatedProducts.values()).map(item => ({
        product_id: item.product_id,
        product_name: item.product_name,
        sku: item.sku,
        pi_quantity: piQuantitiesMap.get(item.product_id) || 0,
        po_quantity: item.po_quantity,
        already_inwarded: alreadyInwardedMap.get(item.product_id) || 0,
        quantity: 0,  // Manual entry (Inward Quantity)
        rate: item.rate,  // From PO
        amount: 0  // Will calculate based on quantity
      }));

      setFormData(prev => ({
        ...prev,
        po_ids: selectedPoIds,
        pi_id: allLinkedPIs.length > 0 ? allLinkedPIs[0].id : '',
        line_items: lineItemsFromPOs.length > 0 ? lineItemsFromPOs : prev.line_items
      }));

      // Show success message with PI info
      if (allLinkedPIs.length > 0) {
        const uniquePIs = [...new Set(allLinkedPIs.map(pi => pi.voucher_no))];
        toast({
          title: `${selectedPoIds.length} PO(s) Selected`,
          description: `Linked to ${uniquePIs.length} PI(s): ${uniquePIs.join(', ')}. Products auto-filled with aggregated PI & PO quantities. Enter Inward Quantity manually.`
        });
      } else {
        toast({
          title: `${selectedPoIds.length} PO(s) Selected`,
          description: 'Products aggregated from all selected POs. Enter Inward Quantity manually.'
        });
      }
    } catch (error) {
      console.error('Error in handlePOSelect:', error);
      toast({ title: 'Error', description: 'Failed to process PO selection', variant: 'destructive' });
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
      line_items: [...formData.line_items, {
        product_id: '',
        product_name: '',
        sku: '',
        quantity: 0,
        rate: 0,
        amount: 0
      }]
    });
  };

  const removeLineItem = (index) => {
    const newLineItems = formData.line_items.filter((_, i) => i !== index);
    // Keep at least one empty item if all are removed
    if (newLineItems.length === 0) {
      setFormData({
        ...formData,
        line_items: [{
          product_id: '',
          product_name: '',
          sku: '',
          quantity: 0,
          rate: 0,
          amount: 0
        }]
      });
    } else {
      setFormData({ ...formData, line_items: newLineItems });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingEntry) {
        await api.put(`/inward-stock/${editingEntry.id}`, formData);
        toast({ title: 'Success', description: 'Inward entry updated successfully' });
      } else {
        await api.post('/inward-stock', formData);
        toast({ title: 'Success', description: 'Inward entry created successfully' });
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

  const handleView = async (entry) => {
    try {
      const fullEntry = await api.get(`/inward-stock/${entry.id}`);
      setViewingEntry(fullEntry.data);
      setViewDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch entry details', variant: 'destructive' });
    }
  };

  const handleEdit = async (entry) => {
    try {
      const fullEntry = await api.get(`/inward-stock/${entry.id}`);
      setEditingEntry(fullEntry.data);
      setFormData({
        inward_invoice_no: fullEntry.data.inward_invoice_no,
        date: fullEntry.data.date.split('T')[0],
        po_ids: fullEntry.data.po_ids || (fullEntry.data.po_id ? [fullEntry.data.po_id] : []),  // Support both po_ids and po_id
        pi_id: fullEntry.data.pi_id || '',
        warehouse_id: fullEntry.data.warehouse_id || '',
        inward_type: fullEntry.data.inward_type,
        source_type: fullEntry.data.source_type || '',
        line_items: fullEntry.data.line_items || []
      });
      setDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch entry details', variant: 'destructive' });
    }
  };



  // handleInward function removed - in-transit feature deprecated

  const handleDelete = async (entry) => {
    if (window.confirm('Are you sure you want to delete this inward entry?')) {
      try {
        await api.delete(`/inward-stock/${entry.id}`);
        toast({ title: 'Success', description: 'Inward entry deleted successfully' });
        fetchData();
      } catch (error) {
        toast({ title: 'Error', description: 'Failed to delete entry', variant: 'destructive' });
      }
    }
  };

  // ===== BULK OPERATIONS HANDLERS FOR PICKUP TAB =====
  const handleSelectAllPickups = (checked) => {
    if (checked) {
      setSelectedPickupIds(pickupEntries.map(item => item.id));
    } else {
      setSelectedPickupIds([]);
    }
  };

  const handleSelectPickup = (id, checked) => {
    if (checked) {
      setSelectedPickupIds([...selectedPickupIds, id]);
    } else {
      setSelectedPickupIds(selectedPickupIds.filter(selectedId => selectedId !== id));
    }
  };

  const handleExportPickupCSV = () => {
    const dataToExport = selectedPickupIds.length > 0
      ? pickupEntries.filter(item => selectedPickupIds.includes(item.id))
      : pickupEntries;

    const fieldMapping = {
      'po_voucher_no': 'PO Number',
      'pickup_date': 'Pickup Date',
      'notes': 'Notes',
      'created_at': 'Created At'
    };

    exportToCSV(formatDataForExport(dataToExport, fieldMapping), 'pickup-entries');
    toast({ title: 'Success', description: 'Pickup entries exported to CSV' });
  };

  const handleExportPickupExcel = () => {
    const dataToExport = selectedPickupIds.length > 0
      ? pickupEntries.filter(item => selectedPickupIds.includes(item.id))
      : pickupEntries;

    const fieldMapping = {
      'po_voucher_no': 'PO Number',
      'pickup_date': 'Pickup Date',
      'notes': 'Notes',
      'created_at': 'Created At'
    };

    exportToExcel(formatDataForExport(dataToExport, fieldMapping), 'pickup-entries', 'Pickup Entries');
    toast({ title: 'Success', description: 'Pickup entries exported to Excel' });
  };

  const handleBulkDeletePickups = async () => {
    if (!window.confirm(`Delete ${selectedPickupIds.length} selected pickup entries? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await api.post('/pickups/bulk-delete', { ids: selectedPickupIds });

      if (response.data.deleted_count > 0) {
        toast({
          title: 'Success',
          description: `${response.data.deleted_count} pickup entry(s) deleted successfully`,
        });
      }

      if (response.data.failed_count > 0) {
        toast({
          title: 'Partial Success',
          description: `${response.data.failed_count} pickup entry(s) could not be deleted`,
          variant: 'destructive'
        });
      }

      setSelectedPickupIds([]);
      fetchPickupEntries();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete pickup entries',
        variant: 'destructive'
      });
    }
  };

  // ===== BULK OPERATIONS HANDLERS FOR WAREHOUSE TAB =====
  const handleSelectAllWarehouse = (checked) => {
    if (checked) {
      setSelectedWarehouseIds(warehouseEntries.map(item => item.id));
    } else {
      setSelectedWarehouseIds([]);
    }
  };

  const handleSelectWarehouse = (id, checked) => {
    if (checked) {
      setSelectedWarehouseIds([...selectedWarehouseIds, id]);
    } else {
      setSelectedWarehouseIds(selectedWarehouseIds.filter(selectedId => selectedId !== id));
    }
  };

  const handleExportWarehouseCSV = () => {
    const dataToExport = selectedWarehouseIds.length > 0
      ? warehouseEntries.filter(item => selectedWarehouseIds.includes(item.id))
      : warehouseEntries;

    const fieldMapping = {
      'inward_invoice_no': 'Invoice No',
      'date': 'Date',
      'warehouse_name': 'Warehouse',
      'total_amount': 'Total Amount',
      'created_at': 'Created At'
    };

    exportToCSV(formatDataForExport(dataToExport, fieldMapping), 'warehouse-inward');
    toast({ title: 'Success', description: 'Warehouse inward entries exported to CSV' });
  };

  const handleExportWarehouseExcel = () => {
    const dataToExport = selectedWarehouseIds.length > 0
      ? warehouseEntries.filter(item => selectedWarehouseIds.includes(item.id))
      : warehouseEntries;

    const fieldMapping = {
      'inward_invoice_no': 'Invoice No',
      'date': 'Date',
      'warehouse_name': 'Warehouse',
      'total_amount': 'Total Amount',
      'created_at': 'Created At'
    };

    exportToExcel(formatDataForExport(dataToExport, fieldMapping), 'warehouse-inward', 'Warehouse Inward');
    toast({ title: 'Success', description: 'Warehouse inward entries exported to Excel' });
  };

  const handleBulkDeleteWarehouse = async () => {
    if (!window.confirm(`Delete ${selectedWarehouseIds.length} selected warehouse inward entries? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await api.post('/inward-stock/bulk-delete', { ids: selectedWarehouseIds });

      if (response.data.deleted_count > 0) {
        toast({
          title: 'Success',
          description: `${response.data.deleted_count} warehouse inward entry(s) deleted successfully`,
        });
      }

      if (response.data.failed_count > 0) {
        toast({
          title: 'Partial Success',
          description: `${response.data.failed_count} warehouse inward entry(s) could not be deleted`,
          variant: 'destructive'
        });
      }

      setSelectedWarehouseIds([]);
      fetchWarehouseEntries();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete warehouse inward entries',
        variant: 'destructive'
      });
    }
  };

  // ===== BULK OPERATIONS HANDLERS FOR DIRECT TAB =====
  const handleSelectAllDirect = (checked) => {
    if (checked) {
      setSelectedDirectIds(directEntries.map(item => item.id));
    } else {
      setSelectedDirectIds([]);
    }
  };

  const handleSelectDirect = (id, checked) => {
    if (checked) {
      setSelectedDirectIds([...selectedDirectIds, id]);
    } else {
      setSelectedDirectIds(selectedDirectIds.filter(selectedId => selectedId !== id));
    }
  };

  const handleExportDirectCSV = () => {
    const dataToExport = selectedDirectIds.length > 0
      ? directEntries.filter(item => selectedDirectIds.includes(item.id))
      : directEntries;

    const fieldMapping = {
      'inward_invoice_no': 'Invoice No',
      'date': 'Date',
      'warehouse.name': 'Warehouse',
      'total_amount': 'Total Amount',
      'status': 'Status'
    };

    exportToCSV(formatDataForExport(dataToExport, fieldMapping), 'direct-inward');
    toast({ title: 'Success', description: 'Direct inward entries exported to CSV' });
  };

  const handleExportDirectExcel = () => {
    const dataToExport = selectedDirectIds.length > 0
      ? directEntries.filter(item => selectedDirectIds.includes(item.id))
      : directEntries;

    const fieldMapping = {
      'inward_invoice_no': 'Invoice No',
      'date': 'Date',
      'warehouse.name': 'Warehouse',
      'total_amount': 'Total Amount',
      'status': 'Status'
    };

    exportToExcel(formatDataForExport(dataToExport, fieldMapping), 'direct-inward', 'Direct Inward');
    toast({ title: 'Success', description: 'Direct inward entries exported to Excel' });
  };

  const handleBulkDeleteDirect = async () => {
    if (!window.confirm(`Delete ${selectedDirectIds.length} selected direct inward entries? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await api.post('/inward-stock/bulk-delete', { ids: selectedDirectIds });

      if (response.data.deleted_count > 0) {
        toast({
          title: 'Success',
          description: `${response.data.deleted_count} direct inward entry(s) deleted successfully`,
        });
      }

      if (response.data.failed_count > 0) {
        toast({
          title: 'Partial Success',
          description: `${response.data.failed_count} direct inward entry(s) could not be deleted`,
          variant: 'destructive'
        });
      }

      setSelectedDirectIds([]);
      fetchData();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete direct inward entries',
        variant: 'destructive'
      });
    }
  };

  const resetForm = () => {
    setFormData({
      inward_invoice_no: '',
      date: new Date().toISOString().split('T')[0],
      po_ids: [],  // Changed from po_id to po_ids (array)
      pi_id: '',
      warehouse_id: '',
      inward_type: activeTab === 'warehouse' ? 'warehouse' : 'direct',
      source_type: activeTab === 'warehouse' ? 'warehouse_inward' : 'direct_inward',
      line_items: [{
        product_id: '',
        product_name: '',
        sku: '',
        quantity: 0,
        rate: 0,
        amount: 0
      }]
    });
    setEditingEntry(null);
  };

  const openCreateDialog = (type) => {
    resetForm();
    setFormData(prev => ({
      ...prev,
      inward_type: type,
      source_type: type === 'direct' ? 'direct_inward' : 'warehouse_inward'
    }));
    setDialogOpen(true);
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

  // Filter entries by type and warehouse (with safety checks) - AFTER loading check

  const filteredWarehouseEntries = (filteredInward || []).filter(e => {
    const matchesType = e.inward_type === 'warehouse';
    const matchesWarehouse = !warehouseFilter || warehouseFilter === 'all' || e.warehouse_id === warehouseFilter;
    return matchesType && matchesWarehouse;
  });

  const directEntries = (filteredInward || []).filter(e => {
    const matchesType = e.source_type === 'direct_inward';
    const matchesWarehouse = !warehouseFilter || warehouseFilter === 'all' || e.warehouse_id === warehouseFilter;
    return matchesType && matchesWarehouse;
  });

  // Filter pending pickup entries by warehouse (with safety checks)
  // Note: pickup pending functionality has been removed
  const filteredPickupPending = [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Inward Stock Operations</h1>
          <p className="text-slate-600 mt-1">Manage stock receipts and warehouse entries</p>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex-1">
          {/* Warehouse Filter */}
          <div className="max-w-xs">
            <Label>Filter by Warehouse</Label>
            <Select
              value={warehouseFilter}
              onValueChange={setWarehouseFilter}
            >
              <SelectTrigger>
                <SelectValue placeholder="All Warehouses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Warehouses</SelectItem>
                {(warehouses || []).map(warehouse => (
                  <SelectItem key={warehouse.id} value={warehouse.id}>
                    {warehouse.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="pickup" className="flex items-center gap-2">
            <Truck size={16} />
            Pick-up (In-Transit)
          </TabsTrigger>
          <TabsTrigger value="warehouse" className="flex items-center gap-2">
            <WarehouseIcon size={16} />
            Inward to Warehouse
          </TabsTrigger>
          <TabsTrigger value="direct" className="flex items-center gap-2">
            <Package size={16} />
            Direct Inward
          </TabsTrigger>
        </TabsList>

        {/* Pick-up Inward Tab */}
        <TabsContent value="pickup" className="space-y-6">
          {/* Create New Pickup Entry */}
          <Card>
            <CardHeader>
              <CardTitle>Create New Pickup Entry</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePickupSubmit} className="space-y-6">
                {/* PO Selection, Warehouse, and Date */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <Label>Manual Entry</Label>
                    <Input
                      type="text"
                      placeholder="Enter Manual"
                      value={pickupFormData.manual}
                      onChange={(e) => setPickupFormData({ ...pickupFormData, manual: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="po">Purchase Order *</Label>
                    <Select value={selectedPo} onValueChange={handlePoSelection}>
                      <SelectTrigger id="po">
                        <SelectValue placeholder="Select PO" />
                      </SelectTrigger>
                      <SelectContent>
                        {pos.map((po) => (
                          <SelectItem key={po.id} value={po.voucher_no}>
                            {po.voucher_no} - {po.supplier}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="warehouse">Warehouse *</Label>
                    <Select
                      value={pickupFormData.warehouse_id}
                      onValueChange={(value) => setPickupFormData({ ...pickupFormData, warehouse_id: value })}
                    >
                      <SelectTrigger id="warehouse">
                        <SelectValue placeholder="Select Warehouse" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Warehouses</SelectItem>
                        {(warehouses || []).map(warehouse => (
                          <SelectItem key={warehouse.id} value={warehouse.id}>
                            {warehouse.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="pickup_date">Pickup Date *</Label>
                    <Input
                      id="pickup_date"
                      type="date"
                      value={pickupFormData.pickup_date}
                      onChange={(e) => setPickupFormData({ ...pickupFormData, pickup_date: e.target.value })}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="notes">Notes</Label>
                    <Input
                      id="notes"
                      type="text"
                      placeholder="Optional notes"
                      value={pickupFormData.notes}
                      onChange={(e) => setPickupFormData({ ...pickupFormData, notes: e.target.value })}
                    />
                  </div>
                </div>

                {/* Line Items Table */}
                {poLineStats && (
                  <div className="space-y-4">
                    <div className="bg-blue-50 p-4 rounded-md">
                      <h3 className="font-semibold mb-2">PO Details</h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                        <div>
                          <span className="text-gray-600">PO Number:</span>
                          <span className="ml-2 font-medium">{poLineStats.po_voucher_no}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Date:</span>
                          <span className="ml-2 font-medium">{poLineStats.po_date}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Supplier:</span>
                          <span className="ml-2 font-medium">{poLineStats.supplier}</span>
                        </div>
                      </div>
                    </div>

                    <div className="border rounded-lg overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Product</TableHead>
                            <TableHead>SKU</TableHead>
                            <TableHead className="text-right">PI Qty</TableHead>
                            <TableHead className="text-right">PO Qty</TableHead>
                            <TableHead className="text-right">Already Inwarded</TableHead>
                            <TableHead className="text-right">In-Transit</TableHead>
                            <TableHead className="text-right">Available</TableHead>
                            <TableHead className="text-right">New In-Transit Qty *</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {pickupFormData.line_items.map((item, index) => (
                            <TableRow key={item.product_id}>
                              <TableCell className="font-medium">{item.product_name}</TableCell>
                              <TableCell>{item.sku}</TableCell>
                              <TableCell className="text-right">{item.pi_quantity}</TableCell>
                              <TableCell className="text-right">{item.po_quantity}</TableCell>
                              <TableCell className="text-right">{item.already_inwarded}</TableCell>
                              <TableCell className="text-right">{item.in_transit}</TableCell>
                              <TableCell className="text-right font-semibold text-green-600">
                                {item.available_for_pickup}
                              </TableCell>
                              <TableCell>
                                <Input
                                  type="number"
                                  min="0"
                                  max={item.available_for_pickup}
                                  step="0.01"
                                  value={item.quantity}
                                  onChange={(e) => handlePickupQuantityChange(index, e.target.value)}
                                  className="w-32 text-right"
                                  disabled={item.available_for_pickup <= 0}
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>

                    <div className="flex justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          setSelectedPo('');
                          setPoLineStats(null);
                          setPickupFormData({
                            pickup_date: new Date().toISOString().split('T')[0],
                            warehouse_id: '',
                            notes: '',
                            line_items: []
                          });
                        }}
                      >
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Reset
                      </Button>
                      <Button type="submit">
                        <Save className="h-4 w-4 mr-2" />
                        Save Pickup Entry
                      </Button>
                    </div>
                  </div>
                )}
              </form>
            </CardContent>
          </Card>

          {/* Existing Pickup Entries */}
          <Card>
            <CardHeader>
              <CardTitle>Existing Pickup Entries</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Bulk Action Toolbar */}
              <BulkActionToolbar
                selectedCount={selectedPickupIds.length}
                onClearSelection={() => setSelectedPickupIds([])}
                onBulkDelete={handleBulkDeletePickups}
                onExportCSV={handleExportPickupCSV}
                onExportExcel={handleExportPickupExcel}
              />

              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">
                        <input
                          type="checkbox"
                          checked={selectedPickupIds.length === pickupEntries.length && pickupEntries.length > 0}
                          onChange={(e) => handleSelectAllPickups(e.target.checked)}
                          className="rounded border-gray-300"
                        />
                      </TableHead>
                      <TableHead>PO Number</TableHead>
                      <TableHead>Pickup Date</TableHead>
                      <TableHead>Items</TableHead>
                      {/* <TableHead>Notes</TableHead> */}
                      <TableHead>In Transit</TableHead>
                      <TableHead>Created At</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pickupEntries.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-gray-500 py-8">
                          No pickup entries found
                        </TableCell>
                      </TableRow>
                    ) : (
                      pickupEntries.map((entry) => (
                        <TableRow key={entry.id}>
                          <TableCell>
                            <input
                              type="checkbox"
                              checked={selectedPickupIds.includes(entry.id)}
                              onChange={(e) => handleSelectPickup(entry.id, e.target.checked)}
                              className="rounded border-gray-300"
                            />
                          </TableCell>
                          <TableCell className="font-medium">{entry.po_voucher_no}</TableCell>
                          <TableCell>{entry.pickup_date}</TableCell>
                          <TableCell>
                            <div className="text-sm">
                              {entry.line_items?.length || 0} items
                            </div>
                          </TableCell>
                          {/* <TableCell>{entry?.line_items?.map(item => item.quantity)}</TableCell> */}
                          <TableCell>
                            {entry?.line_items?.reduce(
                              (total, item) => total + (item.quantity || 0),
                              0
                            )}
                          </TableCell>
                          <TableCell>{new Date(entry.created_at).toLocaleDateString()}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">

                              <Button variant="ghost" size="sm" onClick={() => handleViewPickup(entry)}>
                                <Eye size={16} className="text-blue-600" />
                              </Button>

                              <button
                                onClick={() => handleDeletePickup(entry.id)}
                                className="text-red-600 hover:text-red-800 p-1"
                                title="Delete pickup"
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
            </CardContent>
          </Card>
        </TabsContent>

        {/* Inward to Warehouse Tab */}
        <TabsContent value="warehouse" className="space-y-6">
          {/* Create New Inward Entry */}
          <Card>
            <CardHeader>
              <CardTitle>Inward to Warehouse</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleWarehouseInwardSubmit} className="space-y-6">
                {/* PO Selection, Warehouse, and Date */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="warehouse_po">Purchase Order *</Label>
                    <Select value={selectedWarehousePo} onValueChange={handleWarehousePoSelection}>
                      <SelectTrigger id="warehouse_po">
                        <SelectValue placeholder="Select PO" />
                      </SelectTrigger>
                      <SelectContent>
                        {pos.map((po) => (
                          <SelectItem key={po.id} value={po.voucher_no}>
                            {po.voucher_no} - {po.supplier}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="warehouse_select">Warehouse *</Label>
                    <Select
                      value={warehouseInwardFormData.warehouse_id}
                      onValueChange={(value) => setWarehouseInwardFormData({ ...warehouseInwardFormData, warehouse_id: value })}
                    >
                      <SelectTrigger id="warehouse_select">
                        <SelectValue placeholder="Select Warehouse" />
                      </SelectTrigger>
                      <SelectContent>
                        {warehouses.map((wh) => (
                          <SelectItem key={wh.id} value={wh.id}>
                            {wh.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="inward_date">Inward Date *</Label>
                    <Input
                      id="inward_date"
                      type="date"
                      value={warehouseInwardFormData.inward_date}
                      onChange={(e) => setWarehouseInwardFormData({ ...warehouseInwardFormData, inward_date: e.target.value })}
                      required
                    />
                  </div>
                </div>

                {/* Line Items Table */}
                {warehousePoLineStats && (
                  <div className="space-y-4">
                    <div className="bg-blue-50 p-4 rounded-md">
                      <h3 className="font-semibold mb-2">PO Details</h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                        <div>
                          <span className="text-gray-600">PO Number:</span>
                          <span className="ml-2 font-medium">{warehousePoLineStats.po_voucher_no}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Date:</span>
                          <span className="ml-2 font-medium">{warehousePoLineStats.po_date}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Supplier:</span>
                          <span className="ml-2 font-medium">{warehousePoLineStats.supplier}</span>
                        </div>
                      </div>
                    </div>

                    <div className="border rounded-lg overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Product Name</TableHead>
                            <TableHead>SKU</TableHead>
                            <TableHead className="text-right">PI Qty</TableHead>
                            <TableHead className="text-right">PO Qty</TableHead>
                            <TableHead className="text-right">Already Inwarded</TableHead>
                            <TableHead className="text-right">In-Transit</TableHead>
                            <TableHead className="text-right">Remaining Allowed</TableHead>
                            <TableHead className="text-right">New Inward Qty *</TableHead>
                            <TableHead className="text-right">Rate</TableHead>
                            <TableHead className="text-right">Amount</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {warehouseInwardFormData.line_items.map((item, index) => {
                            const remainingAllowed = item.po_quantity - item.already_inwarded - item.in_transit;
                            const amount = item.new_inward_qty * item.rate;

                            return (
                              <TableRow key={item.product_id}>
                                <TableCell className="font-medium">{item.product_name}</TableCell>
                                <TableCell>{item.sku}</TableCell>
                                <TableCell className="text-right">{item.pi_quantity}</TableCell>
                                <TableCell className="text-right">{item.po_quantity}</TableCell>
                                <TableCell className="text-right">{item.already_inwarded}</TableCell>
                                <TableCell className="text-right">{item.in_transit}</TableCell>
                                <TableCell className="text-right font-semibold text-green-600" title={`Remaining = PO Qty (${item.po_quantity}) - Already Inwarded (${item.already_inwarded}) - In-Transit (${item.in_transit})`}>
                                  {remainingAllowed}
                                </TableCell>
                                <TableCell>
                                  <Input
                                    type="number"
                                    min="0"
                                    max={remainingAllowed}
                                    step="0.01"
                                    value={item.new_inward_qty}
                                    onChange={(e) => handleWarehouseInwardQuantityChange(index, e.target.value)}
                                    className="w-32 text-right"
                                    disabled={remainingAllowed <= 0}
                                    title={remainingAllowed <= 0 ? "No quantity remaining to inward" : `Max allowed: ${remainingAllowed}`}
                                  />
                                </TableCell>
                                <TableCell className="text-right">{item.rate.toFixed(2)}</TableCell>
                                <TableCell className="text-right font-semibold">₹{amount.toFixed(2)}</TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>

                    <div className="flex justify-between items-center bg-gray-50 p-4 rounded-md">
                      <div className="text-lg font-semibold">
                        Total Amount: ₹
                        {warehouseInwardFormData.line_items.reduce((sum, item) => sum + (item.new_inward_qty * item.rate), 0).toFixed(2)}
                      </div>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => {
                            setSelectedWarehousePo('');
                            setWarehousePoLineStats(null);
                            setWarehouseInwardFormData({
                              warehouse_id: '',
                              inward_date: new Date().toISOString().split('T')[0],
                              inward_invoice_no: '',
                              line_items: []
                            });
                          }}
                        >
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Reset
                        </Button>
                        <Button type="submit" disabled={!warehouseInwardFormData.warehouse_id}>
                          <Save className="h-4 w-4 mr-2" />
                          Save Inward Entry
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </form>
            </CardContent>
          </Card>

          {/* Existing Inward Entries */}
          <Card>
            <CardHeader>
              <CardTitle>Existing Warehouse Inward Entries</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Bulk Action Toolbar */}
              <BulkActionToolbar
                selectedCount={selectedWarehouseIds.length}
                onClearSelection={() => setSelectedWarehouseIds([])}
                onBulkDelete={handleBulkDeleteWarehouse}
                onExportCSV={handleExportWarehouseCSV}
                onExportExcel={handleExportWarehouseExcel}
              />

              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">
                        <input
                          type="checkbox"
                          checked={selectedWarehouseIds.length === warehouseEntries.length && warehouseEntries.length > 0}
                          onChange={(e) => handleSelectAllWarehouse(e.target.checked)}
                          className="rounded border-gray-300"
                        />
                      </TableHead>
                      <TableHead>Invoice No</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Warehouse</TableHead>
                      <TableHead>Items</TableHead>
                      <TableHead>Total Amount</TableHead>
                      <TableHead>Already Inwarded</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {warehouseEntries.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-gray-500 py-8">
                          No warehouse inward entries found
                        </TableCell>
                      </TableRow>
                    ) : (
                      warehouseEntries.map((entry) => (
                        <TableRow key={entry.id}>
                          <TableCell>
                            <input
                              type="checkbox"
                              checked={selectedWarehouseIds.includes(entry.id)}
                              onChange={(e) => handleSelectWarehouse(entry.id, e.target.checked)}
                              className="rounded border-gray-300"
                            />
                          </TableCell>
                          <TableCell className="font-medium">{entry.inward_invoice_no || 'N/A'}</TableCell>
                          <TableCell>{entry.date}</TableCell>
                          <TableCell>{entry?.warehouse?.warehouseName || 'Unknown'}</TableCell>
                          <TableCell>
                            <div className="text-sm">
                              {entry.line_items?.length || 0} items
                            </div>
                          </TableCell>
                          <TableCell className="font-semibold">₹{entry.total_amount?.toFixed(2)}</TableCell>
                          {/* <TableCell>
                            {entry?.line_items?.map((item, index) => (
                              <div key={index}>
                                {item.quantity}
                              </div>
                            ))}
                          </TableCell> */}
                          <TableCell>
                            {entry?.line_items?.reduce(
                              (sum, item) => sum + (item.quantity || 0),
                              0
                            )}
                          </TableCell>

                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleView(entry)}
                                className="text-blue-600 hover:text-blue-800 p-1"
                                title="View details"
                              >
                                <Eye className="h-4 w-4" />
                              </button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}

                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          {/* Pickup Entries Card */}
          <Card>
            <CardHeader>
              <CardTitle>Pickup Entries</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">
                        <input
                          type="checkbox"
                          checked={selectedPickupIds.length === pickupEntries.length && pickupEntries.length > 0}
                          onChange={(e) => handleSelectAllPickups(e.target.checked)}
                          className="rounded border-gray-300"
                        />
                      </TableHead>
                      <TableHead>PO Number</TableHead>
                      <TableHead>Pickup Date</TableHead>
                      <TableHead>Warehouse</TableHead>
                      <TableHead>Items</TableHead>
                      <TableHead>Total Amount</TableHead>
                      <TableHead>Created At</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pickupEntries.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={selectedPickupIds.includes(entry.id)}
                            onChange={(e) => handleSelectPickup(entry.id, e.target.checked)}
                            className="rounded border-gray-300"
                          />
                        </TableCell>
                        <TableCell className="font-medium">{entry.po_voucher_no}</TableCell>
                        <TableCell>{entry.pickup_date}</TableCell>
                        <TableCell>-</TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {entry.line_items?.length || 0} items
                          </div>
                        </TableCell>
                        <TableCell className="font-semibold">
                          ₹{(entry.line_items?.reduce((sum, item) => sum + (item.quantity * item.rate), 0) || 0).toFixed(2)}
                        </TableCell>
                        <TableCell>{new Date(entry.created_at).toLocaleDateString()}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            {/* View */}
                            <Button variant="ghost" size="sm" onClick={() => handleViewPickup(entry)}>
                              <Eye size={16} className="text-blue-600" />
                            </Button>

                            {/* Inward */}
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={entry.is_inwarded}
                              onClick={() => handleInwardPickup(entry.id)}
                            >
                              {entry.is_inwarded ? "Inwarded" : "Inward"}
                            </Button>

                            {/* Delete */}
                            <button
                              onClick={() => handleDeletePickup(entry.id)}
                              className="text-red-600 hover:text-red-800 p-1"
                              title="Delete pickup"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </TableCell>

                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        {/* Direct Inward Tab */}
        <TabsContent value="direct" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Direct Inward to Warehouse</h2>
            <Button
              onClick={() => openCreateDialog('direct')}
              className="bg-purple-600 hover:bg-purple-700"
            >
              <Plus size={16} className="mr-2" />
              Record Direct Inward
            </Button>
          </div>

          {/* Bulk Action Toolbar */}
          <BulkActionToolbar
            selectedCount={selectedDirectIds.length}
            onClearSelection={() => setSelectedDirectIds([])}
            onBulkDelete={handleBulkDeleteDirect}
            onExportCSV={handleExportDirectCSV}
            onExportExcel={handleExportDirectExcel}
          />

          <div className="border rounded-lg overflow-hidden bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <input
                      type="checkbox"
                      checked={selectedDirectIds.length === directEntries.length && directEntries.length > 0}
                      onChange={(e) => handleSelectAllDirect(e.target.checked)}
                      className="rounded border-gray-300"
                    />
                  </TableHead>
                  <TableHead>Invoice No</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Warehouse</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Total Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!Array.isArray(directEntries) || directEntries.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-slate-500 py-8">
                      No direct inward entries found. Record your first direct inward.
                    </TableCell>
                  </TableRow>
                ) : (
                  directEntries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selectedDirectIds.includes(entry.id)}
                          onChange={(e) => handleSelectDirect(entry.id, e.target.checked)}
                          className="rounded border-gray-300"
                        />
                      </TableCell>
                      <TableCell className="font-medium">{entry.inward_invoice_no}</TableCell>
                      <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                      <TableCell>{entry.warehouse?.name || '-'}</TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {entry.line_items_count} items
                        </div>
                      </TableCell>
                      <TableCell className="font-semibold">₹{entry.total_amount?.toFixed(2)}</TableCell>
                      <TableCell>
                        <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                          {entry.status}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleView(entry)}
                            className="text-blue-600 hover:text-blue-800 p-1"
                            title="View details"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(entry)}
                            className="text-red-600 hover:text-red-800 p-1"
                            title="Delete entry"
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
        </TabsContent>
      </Tabs>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingEntry ? 'Edit' : 'Create'} {
                formData.inward_type === 'in_transit' ? 'Pick-up Inward (In-Transit)' :
                  formData.inward_type === 'warehouse' ? 'Inward to Warehouse' :
                    'Direct Inward to Warehouse'
              }
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Header Information */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Inward Invoice No *</Label>
                <Input
                  value={formData.inward_invoice_no}
                  onChange={(e) => setFormData({ ...formData, inward_invoice_no: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>Date *</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  required
                />
              </div>
              {formData.source_type !== 'direct_inward' && (
                <div>
                  <Label>PO Voucher No (Multiple Selection)</Label>
                  <div className="space-y-2">
                    {/* Selected POs Display */}
                    <div className="border rounded-md p-2 min-h-[40px] flex flex-wrap gap-2 bg-white">
                      {!Array.isArray(formData.po_ids) || formData.po_ids.length === 0 ? (
                        <span className="text-gray-400 text-sm">No PO selected</span>
                      ) : (
                        formData.po_ids.map(poId => {
                          const po = Array.isArray(pos) ? pos.find(p => p?.id === poId) : null;
                          return (
                            <span key={poId} className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 px-2 py-1 rounded-md text-sm">
                              {po?.voucher_no || poId}
                              <button
                                type="button"
                                onClick={() => {
                                  const newPoIds = formData.po_ids.filter(id => id !== poId);
                                  handlePOSelect(newPoIds);
                                }}
                                className="text-blue-600 hover:text-blue-800"
                              >
                                <X size={14} />
                              </button>
                            </span>
                          );
                        })
                      )}
                    </div>

                    {/* Dropdown to Select POs */}
                    <div className="border rounded-md max-h-48 overflow-y-auto bg-white">
                      {!Array.isArray(pos) || pos.length === 0 ? (
                        <div className="p-3 text-sm text-gray-500 text-center">No POs available</div>
                      ) : (
                        pos.map(po => {
                          const isSelected = Array.isArray(formData.po_ids) && formData.po_ids.includes(po?.id);
                          return (
                            <label
                              key={po.id}
                              className="flex items-center gap-3 p-2 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                            >
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={(e) => {
                                  let newPoIds;
                                  if (e.target.checked) {
                                    // Add PO
                                    newPoIds = [...formData.po_ids, po.id];
                                  } else {
                                    // Remove PO
                                    newPoIds = formData.po_ids.filter(id => id !== po.id);
                                  }
                                  handlePOSelect(newPoIds);
                                }}
                                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                              />
                              <div className="flex-1 text-sm">
                                <div className="font-medium text-gray-900">{po.voucher_no}</div>
                                <div className="text-xs text-gray-500">{new Date(po.date).toLocaleDateString()}</div>
                              </div>
                            </label>
                          );
                        })
                      )}
                    </div>
                    <p className="text-xs text-gray-500">Check multiple POs to select them</p>
                  </div>
                </div>
              )}
              {(formData.inward_type === 'warehouse' || formData.source_type === 'direct_inward') && (
                <div>
                  <Label>Warehouse *</Label>
                  <Select
                    value={formData.warehouse_id}
                    onValueChange={(value) => setFormData({ ...formData, warehouse_id: value })}
                    required={formData.inward_type === 'warehouse' || formData.source_type === 'direct_inward'}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select warehouse" />
                    </SelectTrigger>
                    <SelectContent>
                      {warehouses.map(warehouse => (
                        <SelectItem key={warehouse.id} value={warehouse.id}>
                          {warehouse.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
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

              {formData.po_ids.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                  <div className="flex items-start gap-2">
                    <div className="text-blue-600 mt-0.5">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="16" x2="12" y2="12" />
                        <line x1="12" y1="8" x2="12.01" y2="8" />
                      </svg>
                    </div>
                    <div className="text-xs text-blue-800">
                      <strong>Inward Validation Logic:</strong> You can only inward up to <strong>PO Quantity</strong>.
                      <strong> Remaining Allowed</strong> = PO Qty - Already Inwarded.
                      If you exceed, the system will <strong className="text-red-600">BLOCK</strong> the entry.
                    </div>
                  </div>
                </div>
              )}


              <div className="space-y-4">
                {formData.line_items.map((item, index) => (
                  <div key={index} className="border rounded-lg p-4 bg-slate-50 relative">
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-medium text-slate-700">Item {index + 1} - {item.product_name || 'New Product'}</span>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => removeLineItem(index)}
                        className="text-red-600 hover:text-red-800 hover:bg-red-50 border-red-300"
                        title="Remove this product"
                      >
                        <X size={16} className="mr-1" />
                        Remove
                      </Button>
                    </div>

                    <div className="grid grid-cols-9 gap-3">
                      <div>
                        <Label>Product Name *</Label>
                        <Input
                          value={item.product_name}
                          onChange={(e) => handleLineItemChange(index, 'product_name', e.target.value)}
                          placeholder="Enter product name"
                          required
                          disabled={formData.po_ids.length > 0 && !editingEntry} // Disabled if POs selected and not editing
                        />
                      </div>
                      <div>
                        <Label>SKU</Label>
                        <Input
                          value={item.sku}
                          onChange={(e) => handleLineItemChange(index, 'sku', e.target.value)}
                          placeholder="SKU"
                          disabled={formData.po_id && !editingEntry}
                        />
                      </div>
                      {/* <div>
                        <Label className="text-xs">PI Qty (From Invoice)</Label>
                        <Input
                          value={item.pi_quantity || 0}
                          disabled
                          className="bg-blue-50 font-semibold text-blue-700"
                          title="Total quantity from Performa Invoice"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">PO Qty (Ordered)</Label>
                        <Input
                          value={item.po_quantity || 0}
                          disabled
                          className="bg-green-50 font-semibold text-green-700"
                          title="Purchase Order quantity - Maximum allowed to inward"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Already Inwarded</Label>
                        <Input
                          value={item.already_inwarded || 0}
                          disabled
                          className="bg-orange-50 font-semibold text-orange-700"
                          title="Cumulative quantity already inwarded for this PO"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">
                          Remaining Allowed
                          <span className="ml-1 text-xs text-slate-500">(PO - Already)</span>
                        </Label>
                        <Input
                          value={(item.po_quantity || 0) - (item.already_inwarded || 0)}
                          disabled
                          className="bg-purple-50 font-bold text-purple-700"
                          title="Maximum quantity you can inward now"
                        />
                      </div> */}
                      <div>
                        <Label className="text-xs">New Inward Qty *</Label>
                        <Input
                          type="number"
                          step="0.01"
                          value={item.quantity || ''}
                          onChange={(e) => handleLineItemChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                          placeholder="Enter quantity"
                          required
                          className={
                            item.quantity && ((item.already_inwarded || 0) + item.quantity) > (item.po_quantity || 0)
                              ? 'border-red-500 bg-red-50'
                              : ''
                          }
                        />
                        {item.quantity && ((item.already_inwarded || 0) + item.quantity) > (item.po_quantity || 0) && (
                          <p className="text-xs text-red-600 mt-1">
                            ⚠️ Exceeds PO Qty! Will be blocked.
                          </p>
                        )}
                      </div>
                      <div>
                        <Label>Rate</Label>
                        <Input
                          type="number"
                          step="0.01"
                          value={item.rate || ''}
                          onChange={(e) => handleLineItemChange(index, 'rate', parseFloat(e.target.value) || 0)}
                          placeholder="Rate"
                          disabled={formData.po_id && !editingEntry}
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
              <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                {editingEntry ? 'Update' : 'Create'} Entry
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={pickupViewOpen} onOpenChange={setPickupViewOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Pickup Entry Details</DialogTitle>
          </DialogHeader>

          {selectedPickupEntry && (
            <div className="space-y-6">
              <div className="bg-slate-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Pickup Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-slate-600">PO Number</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-semibold">
                      {selectedPickupEntry.po_voucher_no}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Pickup Date</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {selectedPickupEntry.pickup_date}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Manual</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {selectedPickupEntry.manual || '-'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Notes</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {selectedPickupEntry.notes || '-'}
                    </div>
                  </div>
                  <div className="col-span-2">
                    <Label className="text-sm font-medium text-slate-600">Created At</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {new Date(selectedPickupEntry.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Line Items</h3>
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-slate-100">
                      <tr>
                        <th className="text-left p-3 font-medium text-slate-700">Product Name</th>
                        <th className="text-left p-3 font-medium text-slate-700">SKU</th>
                        <th className="text-right p-3 font-medium text-slate-700">Quantity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedPickupEntry.line_items?.map((item, index) => (
                        <tr key={item.id || index} className="border-t">
                          <td className="p-3">{item.product_name}</td>
                          <td className="p-3 font-mono text-sm">{item.sku}</td>
                          <td className="p-3 text-right">{item.quantity}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="flex justify-end gap-2 border-t pt-4">
                <Button variant="outline" onClick={() => setPickupViewOpen(false)}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* View Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>View Inward Stock Details</DialogTitle>
          </DialogHeader>

          {viewingEntry && (
            <div className="space-y-6">
              {/* Entry Header Information */}
              <div className="bg-slate-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-4 text-slate-800">Entry Information</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Invoice No</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-semibold">
                      {viewingEntry.inward_invoice_no}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Date</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {new Date(viewingEntry.date).toLocaleDateString()}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Type</Label>
                    <div className="mt-1">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${viewingEntry.inward_type === 'in_transit' ? 'bg-blue-100 text-blue-800' :
                        viewingEntry.inward_type === 'warehouse' ? 'bg-green-100 text-green-800' :
                          'bg-purple-100 text-purple-800'
                        }`}>
                        {viewingEntry.inward_type === 'in_transit' ? 'In-Transit' :
                          viewingEntry.inward_type === 'warehouse' ? 'Warehouse' : 'Direct'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* PO/PI Information */}
              {(viewingEntry.po || viewingEntry.pi) && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4 text-blue-800">Purchase Order Information</h3>
                  <div className="grid grid-cols-2 gap-4">
                    {viewingEntry.po && (
                      <>
                        <div>
                          <Label className="text-sm font-medium text-blue-600">PO Voucher No</Label>
                          <div className="mt-1 p-2 bg-white rounded border">
                            {viewingEntry.po.voucher_no}
                          </div>
                        </div>
                        <div>
                          <Label className="text-sm font-medium text-blue-600">PO Date</Label>
                          <div className="mt-1 p-2 bg-white rounded border">
                            {new Date(viewingEntry.po.date).toLocaleDateString()}
                          </div>
                        </div>
                      </>
                    )}
                    {viewingEntry.pi && (
                      <>
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
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Warehouse Information */}
              {viewingEntry.warehouse && (
                <div className="bg-green-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4 text-green-800">Warehouse Information</h3>
                  <div>
                    <Label className="text-sm font-medium text-green-600">Warehouse</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingEntry.warehouse.name}
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


      {/* Inward Dialog */}

    </div>
  );
};

export default InwardStock;
