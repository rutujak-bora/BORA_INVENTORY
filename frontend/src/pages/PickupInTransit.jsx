import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Truck, Save, RefreshCw, Trash2 } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';

const PickupInTransit = () => {
  const [pos, setPos] = useState([]);
  const [selectedPo, setSelectedPo] = useState('');
  const [poLineStats, setPoLineStats] = useState(null);
  const [pickupEntries, setPickupEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    pickup_date: new Date().toISOString().split('T')[0],
    notes: '',
    line_items: []
  });

  const { toast } = useToast();
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchPOs();
    fetchPickupEntries();
  }, []);

  const fetchPOs = async () => {
    try {
      const response = await api.get('/purchase-orders');
      setPos(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Failed to fetch POs:', error);
      toast({
        title: 'Error',
        description: 'Failed to load Purchase Orders',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchPickupEntries = async () => {
    try {
      const response = await api.get('/pickups');
      setPickupEntries(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Failed to fetch pickup entries:', error);
    }
  };

  const handlePoSelection = async (voucher_no) => {
    if (!voucher_no) {
      setSelectedPo('');
      setPoLineStats(null);
      setFormData({
        pickup_date: new Date().toISOString().split('T')[0],
        notes: '',
        line_items: []
      });
      return;
    }

    try {
      setSelectedPo(voucher_no);
      const response = await api.get(`/pos/lines-with-stats?voucher_no=${encodeURIComponent(voucher_no)}`);
      setPoLineStats(response.data);
      
      // Initialize form data with line items
      const lineItems = response.data.line_items.map(item => ({
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
      }));
      
      setFormData(prev => ({
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

  const handleQuantityChange = (index, value) => {
    const newQuantity = parseFloat(value) || 0;
    const lineItem = formData.line_items[index];
    
    // Validation: Check if new quantity exceeds available
    if (newQuantity > lineItem.available_for_pickup) {
      toast({
        title: 'Invalid Quantity',
        description: `Cannot exceed available quantity (${lineItem.available_for_pickup}) for ${lineItem.product_name}`,
        variant: 'destructive'
      });
      return;
    }
    
    const updatedLineItems = [...formData.line_items];
    updatedLineItems[index].quantity = newQuantity;
    setFormData(prev => ({ ...prev, line_items: updatedLineItems }));
  };

  const handleSubmit = async (e) => {
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
    const validLineItems = formData.line_items.filter(item => item.quantity > 0);
    
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
        pickup_date: formData.pickup_date,
        notes: formData.notes,
        line_items: validLineItems.map(item => ({
          product_id: item.product_id,
          product_name: item.product_name,
          sku: item.sku,
          quantity: item.quantity,
          rate: item.rate
        }))
      };
      
      await api.post('/pickups', pickupData);
      
      toast({
        title: 'Success',
        description: 'Pickup (In-Transit) entry created successfully',
        variant: 'default'
      });
      
      // Reset form and refresh data
      setSelectedPo('');
      setPoLineStats(null);
      setFormData({
        pickup_date: new Date().toISOString().split('T')[0],
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Truck className="h-8 w-8 text-orange-600" />
          <div>
            <h1 className="text-3xl font-bold">Pick-up (In-Transit)</h1>
            <p className="text-sm text-gray-600">Record items picked up from supplier</p>
          </div>
        </div>
      </div>

      {/* Create Pickup Form */}
      <Card>
        <CardHeader>
          <CardTitle>Create New Pickup Entry</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* PO Selection and Date */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                <Label htmlFor="pickup_date">Pickup Date *</Label>
                <Input
                  id="pickup_date"
                  type="date"
                  value={formData.pickup_date}
                  onChange={(e) => setFormData({ ...formData, pickup_date: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Input
                  id="notes"
                  type="text"
                  placeholder="Optional notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
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
                      {formData.line_items.map((item, index) => (
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
                              onChange={(e) => handleQuantityChange(index, e.target.value)}
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
                      setFormData({
                        pickup_date: new Date().toISOString().split('T')[0],
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
          {pickupEntries.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No pickup entries found</p>
          ) : (
            <div className="space-y-4">
              {pickupEntries.map((entry) => (
                <div key={entry.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-semibold">PO: {entry.po_voucher_no}</h4>
                      <p className="text-sm text-gray-600">
                        Pickup Date: {entry.pickup_date} | Created: {new Date(entry.created_at).toLocaleDateString()}
                      </p>
                      {entry.notes && (
                        <p className="text-sm text-gray-600 mt-1">Notes: {entry.notes}</p>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDeletePickup(entry.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Product</TableHead>
                          <TableHead>SKU</TableHead>
                          <TableHead className="text-right">Quantity</TableHead>
                          <TableHead className="text-right">Rate</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {entry.line_items.map((item) => (
                          <TableRow key={item.id}>
                            <TableCell>{item.product_name}</TableCell>
                            <TableCell>{item.sku}</TableCell>
                            <TableCell className="text-right">{item.quantity}</TableCell>
                            <TableCell className="text-right">{item.rate}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default PickupInTransit;
