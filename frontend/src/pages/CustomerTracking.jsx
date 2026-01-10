// Updated: 2025-01-04 - PI to PO Mapping section removed
import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Eye, RefreshCw, Filter, Users, Package, TrendingUp, TrendingDown, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';

const CustomerTracking = () => {
  const [loading, setLoading] = useState(true);
  const [trackingData, setTrackingData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  
  // Filter states
  const [filters, setFilters] = useState({
    customer_name: '',
    pi_number: '',
    sku: '',
    status: 'all'
  });
  
  // Dialog states
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [viewingItem, setViewingItem] = useState(null);
  
  const { toast } = useToast();
  useResizeObserverErrorFix();
  
  useEffect(() => {
    fetchTrackingData();
  }, []);
  
  useEffect(() => {
    applyFilters();
  }, [trackingData, filters]);
  
  const fetchTrackingData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/customer-tracking');
      setTrackingData(response.data || []);
    } catch (error) {
      console.error('Error fetching customer tracking:', error);
      toast({ 
        title: 'Error', 
        description: 'Failed to fetch customer tracking data', 
        variant: 'destructive' 
      });
    } finally {
      setLoading(false);
    }
  };
  
  const applyFilters = () => {
    let filtered = [...trackingData];
    
    if (filters.customer_name) {
      filtered = filtered.filter(item => 
        item.customer_name.toLowerCase().includes(filters.customer_name.toLowerCase())
      );
    }
    
    if (filters.pi_number) {
      filtered = filtered.filter(item => 
        item.pi_number.toLowerCase().includes(filters.pi_number.toLowerCase())
      );
    }
    
    if (filters.sku) {
      filtered = filtered.filter(item => 
        item.sku.toLowerCase().includes(filters.sku.toLowerCase())
      );
    }
    
    if (filters.status !== 'all') {
      filtered = filtered.filter(item => 
        item.status.toLowerCase() === filters.status.toLowerCase()
      );
    }
    
    setFilteredData(filtered);
  };
  
  const handleView = (item) => {
    console.log('View clicked for item:', item);
    setViewingItem(item);
    setViewDialogOpen(true);
  };
  
  const resetFilters = () => {
    setFilters({
      customer_name: '',
      pi_number: '',
      sku: '',
      status: 'all'
    });
  };
  
  // Calculate summary stats
  const summaryStats = {
    totalPIs: new Set(trackingData.map(item => item.pi_number)).size,
    totalCustomers: new Set(trackingData.map(item => item.customer_name)).size,
    totalProducts: trackingData.length,
    completedOrders: trackingData.filter(item => item.status === 'Completed').length,
    pendingOrders: trackingData.filter(item => item.status === 'Pending').length,
    totalPIQuantity: trackingData.reduce((sum, item) => sum + item.pi_quantity, 0),
    totalInwarded: trackingData.reduce((sum, item) => sum + item.inwarded_quantity, 0),
    totalDispatched: trackingData.reduce((sum, item) => sum + item.dispatched_quantity, 0)
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Customer Tracking</h1>
          <p className="text-slate-600 mt-1">Track customer orders from PI to Dispatch - Updated v2.0</p>
        </div>
        <Button 
          onClick={fetchTrackingData}
          variant="outline"
          className="flex items-center gap-2"
        >
          <RefreshCw size={16} />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs flex items-center gap-1">
              <FileText size={14} />
              Total PIs
            </CardDescription>
            <CardTitle className="text-2xl text-blue-600">{summaryStats.totalPIs}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs flex items-center gap-1">
              <Users size={14} />
              Customers
            </CardDescription>
            <CardTitle className="text-2xl text-purple-600">{summaryStats.totalCustomers}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs flex items-center gap-1">
              <CheckCircle size={14} />
              Completed
            </CardDescription>
            <CardTitle className="text-2xl text-green-600">{summaryStats.completedOrders}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs flex items-center gap-1">
              <AlertCircle size={14} />
              Pending
            </CardDescription>
            <CardTitle className="text-2xl text-orange-600">{summaryStats.pendingOrders}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Filter size={18} />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <Label>Customer Name</Label>
              <Input
                placeholder="Search customer..."
                value={filters.customer_name}
                onChange={(e) => setFilters({ ...filters, customer_name: e.target.value })}
              />
            </div>
            <div>
              <Label>PI Number</Label>
              <Input
                placeholder="Search PI..."
                value={filters.pi_number}
                onChange={(e) => setFilters({ ...filters, pi_number: e.target.value })}
              />
            </div>
            <div>
              <Label>SKU</Label>
              <Input
                placeholder="Search SKU..."
                value={filters.sku}
                onChange={(e) => setFilters({ ...filters, sku: e.target.value })}
              />
            </div>
            <div>
              <Label>Status</Label>
              <select
                className="w-full border rounded-md px-3 py-2 text-sm"
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
              </select>
            </div>
            <div className="flex items-end">
              <Button variant="outline" onClick={resetFilters} className="w-full">
                Reset Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Data Table */}
      <Card>
        <CardHeader>
          <CardTitle>Customer Tracking Data</CardTitle>
          <CardDescription>Showing {filteredData.length} of {trackingData.length} records</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer Name</TableHead>
                  <TableHead>PI Number</TableHead>
                  <TableHead>Product / SKU</TableHead>
                  <TableHead className="text-right">PI Qty</TableHead>
                  <TableHead className="text-right bg-green-50">Inwarded</TableHead>
                  <TableHead className="text-right bg-green-50">Remaining (Inward)</TableHead>
                  <TableHead className="text-right bg-orange-50">Dispatched</TableHead>
                  <TableHead className="text-right bg-orange-50">Remaining (Dispatch)</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredData.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center text-slate-500 py-8">
                      No tracking data found. Try adjusting your filters.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredData.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">{item.customer_name}</TableCell>
                      <TableCell className="font-mono text-sm">{item.pi_number}</TableCell>
                      <TableCell>
                        <div className="font-medium">{item.product_name}</div>
                        <div className="text-xs text-slate-500">{item.sku}</div>
                      </TableCell>
                      <TableCell className="text-right font-semibold">{item.pi_quantity}</TableCell>
                      <TableCell className="text-right text-green-600 font-semibold bg-green-50">
                        {item.inwarded_quantity}
                      </TableCell>
                      <TableCell className="text-right font-semibold bg-green-50">
                        <span className={item.remaining_quantity_inward > 0 ? 'text-orange-600' : 'text-green-600'}>
                          {item.remaining_quantity_inward}
                        </span>
                      </TableCell>
                      <TableCell className="text-right text-orange-600 font-semibold bg-orange-50">
                        {item.dispatched_quantity}
                      </TableCell>
                      <TableCell className="text-right font-semibold bg-orange-50">
                        <span className={item.remaining_quantity_dispatch > 0 ? 'text-orange-600' : 'text-green-600'}>
                          {item.remaining_quantity_dispatch}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={item.status === 'Completed' ? 'default' : 'secondary'}
                          className={item.status === 'Completed' ? 'bg-green-600' : 'bg-orange-500'}>
                          {item.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" onClick={() => handleView(item)}>
                          <Eye size={16} className="text-blue-600" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
                {filteredData.length > 0 && (
                  <TableRow className="bg-blue-50 border-t-2 border-blue-400 font-bold">
                    <TableCell colSpan={3} className="text-right text-blue-900">TOTALS:</TableCell>
                    <TableCell className="text-right text-blue-900">
                      {filteredData.reduce((sum, item) => sum + item.pi_quantity, 0)}
                    </TableCell>
                    <TableCell className="text-right text-green-900 bg-green-50">
                      {filteredData.reduce((sum, item) => sum + item.inwarded_quantity, 0)}
                    </TableCell>
                    <TableCell className="text-right text-orange-900 bg-green-50">
                      {filteredData.reduce((sum, item) => sum + item.remaining_quantity_inward, 0)}
                    </TableCell>
                    <TableCell className="text-right text-orange-900 bg-orange-50">
                      {filteredData.reduce((sum, item) => sum + item.dispatched_quantity, 0)}
                    </TableCell>
                    <TableCell className="text-right text-orange-900 bg-orange-50">
                      {filteredData.reduce((sum, item) => sum + item.remaining_quantity_dispatch, 0)}
                    </TableCell>
                    <TableCell className="text-blue-900">
                      {filteredData.length} Records
                    </TableCell>
                    <TableCell></TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* View Details Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Customer Tracking Details</DialogTitle>
          </DialogHeader>
          
          {viewingItem && (
            <div className="space-y-6">
              {/* PI and Customer Info */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-lg">
                <div>
                  <Label className="text-sm font-semibold text-slate-600">Customer Name</Label>
                  <p className="text-slate-900 font-medium">{viewingItem.customer_name}</p>
                </div>
                <div>
                  <Label className="text-sm font-semibold text-slate-600">PI Number</Label>
                  <p className="text-slate-900 font-mono">{viewingItem.pi_number}</p>
                </div>
                <div>
                  <Label className="text-sm font-semibold text-slate-600">Product Name</Label>
                  <p className="text-slate-900">{viewingItem.product_name}</p>
                </div>
                <div>
                  <Label className="text-sm font-semibold text-slate-600">SKU</Label>
                  <p className="text-slate-900 font-mono">{viewingItem.sku}</p>
                </div>
                <div>
                  <Label className="text-sm font-semibold text-slate-600">PI Total Quantity</Label>
                  <p className="text-slate-900 font-bold text-lg">{viewingItem.pi_quantity}</p>
                </div>
                <div>
                  <Label className="text-sm font-semibold text-slate-600">Status</Label>
                  <Badge variant={viewingItem.status === 'Completed' ? 'default' : 'secondary'}
                    className={viewingItem.status === 'Completed' ? 'bg-green-600' : 'bg-orange-500'}>
                    {viewingItem.status}
                  </Badge>
                </div>
              </div>

              {/* Linked PO Numbers */}
              {viewingItem.linked_po_numbers && viewingItem.linked_po_numbers.length > 0 && (
                <div>
                  <Label className="text-sm font-semibold text-slate-600 mb-2">Linked PO Numbers</Label>
                  <div className="flex flex-wrap gap-2">
                    {viewingItem.linked_po_numbers.map((po_no, idx) => (
                      <Badge key={idx} variant="outline" className="font-mono">
                        {po_no}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Inward Details */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-green-700 flex items-center gap-2">
                  <TrendingUp size={18} />
                  Inward Tracking
                </h3>
                <div className="grid grid-cols-3 gap-4 mb-4 p-4 bg-green-50 rounded-lg">
                  <div>
                    <Label className="text-xs text-green-700">Total Inwarded</Label>
                    <p className="text-2xl font-bold text-green-700">{viewingItem.inwarded_quantity}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-orange-700">Remaining to Inward</Label>
                    <p className="text-2xl font-bold text-orange-700">{viewingItem.remaining_quantity_inward}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-slate-600">Inward %</Label>
                    <p className="text-2xl font-bold text-slate-700">
                      {((viewingItem.inwarded_quantity / viewingItem.pi_quantity) * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
                
                {viewingItem.inward_details && viewingItem.inward_details.length > 0 && (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>PO Number</TableHead>
                        <TableHead>Inward Invoice No</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {viewingItem.inward_details.map((detail, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-mono">{detail.po_number}</TableCell>
                          <TableCell className="font-mono">{detail.inward_invoice_no}</TableCell>
                          <TableCell>{new Date(detail.date).toLocaleDateString()}</TableCell>
                          <TableCell className="text-right font-semibold text-green-600">{detail.quantity}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>

              {/* Dispatch Details */}
              <div>
                <h3 className="text-lg font-semibold mb-3 text-orange-700 flex items-center gap-2">
                  <TrendingDown size={18} />
                  Dispatch Tracking
                </h3>
                <div className="grid grid-cols-3 gap-4 mb-4 p-4 bg-orange-50 rounded-lg">
                  <div>
                    <Label className="text-xs text-orange-700">Total Dispatched</Label>
                    <p className="text-2xl font-bold text-orange-700">{viewingItem.dispatched_quantity}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-orange-700">Remaining to Dispatch</Label>
                    <p className="text-2xl font-bold text-orange-700">{viewingItem.remaining_quantity_dispatch}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-slate-600">Dispatch %</Label>
                    <p className="text-2xl font-bold text-slate-700">
                      {((viewingItem.dispatched_quantity / viewingItem.pi_quantity) * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
                
                {viewingItem.dispatch_details && viewingItem.dispatch_details.length > 0 && (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Export Invoice No</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {viewingItem.dispatch_details.map((detail, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-mono">{detail.export_invoice_no}</TableCell>
                          <TableCell>{new Date(detail.date).toLocaleDateString()}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{detail.dispatch_type}</Badge>
                          </TableCell>
                          <TableCell className="text-right font-semibold text-orange-600">{detail.quantity}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CustomerTracking;
