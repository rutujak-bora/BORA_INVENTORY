import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { AlertTriangle, TrendingDown, TrendingUp, Package, Search, Filter, RefreshCw, Eye, Trash2, Edit, ArrowUpCircle, ArrowDownCircle } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import { createSafeOnValueChange, getSafeSelectContentProps } from '../utils/selectHelpers';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';

const StockSummary = () => {
  const [stockData, setStockData] = useState([]);
  const [lowStockAlerts, setLowStockAlerts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [products, setProducts] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filter states
  const [filters, setFilters] = useState({
    warehouse_id: 'all',
    company_id: 'all',
    sku: '',
    pi_number: '',
    category: 'all',
    low_stock_only: false,
    low_stock_threshold: 10
  });

  // Summary stats
  const [summaryStats, setSummaryStats] = useState({
    totalProducts: 0,
    totalInward: 0,
    totalOutward: 0,
    totalStock: 0,
    lowStockCount: 0,
    outOfStockCount: 0
  });

  const { toast } = useToast();

  // Use custom hook to suppress ResizeObserver errors
  useResizeObserverErrorFix();

  // Dialog states
  const [viewTransactionsDialog, setViewTransactionsDialog] = useState(false);
  const [viewingTransactions, setViewingTransactions] = useState(null);
  const [transactionHistory, setTransactionHistory] = useState([]);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingStock, setEditingStock] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingStock, setDeletingStock] = useState(null);
  const [deleteTransactions, setDeleteTransactions] = useState([]);
  const [selectedTransactionType, setSelectedTransactionType] = useState('all');

  // Stock action handlers
  const handleViewStock = async (item) => {
    try {
      const response = await api.get(`/stock-transactions/${item.product_id}/${item.warehouse_id}`);
      setTransactionHistory(response.data.transactions || []);
      setViewingTransactions(item);
      setViewTransactionsDialog(true);
    } catch (error) {
      toast({ 
        title: 'Error', 
        description: 'Failed to fetch transaction history', 
        variant: 'destructive' 
      });
    }
  };

  const handleEditStock = (item) => {
    setEditingStock(item);
    setEditDialogOpen(true);
  };

  const handleDeleteStock = async (item) => {
    // Validate required fields
    if (!item.product_id) {
      toast({ 
        title: 'Error', 
        description: 'Product ID is missing. Cannot fetch transactions.', 
        variant: 'destructive' 
      });
      return;
    }

    try {
      // Fetch all transactions for this product-warehouse combination
      const response = await api.get(`/stock-transactions/${item.product_id}/${item.warehouse_id || ''}`);
      setDeleteTransactions(response.data.transactions || []);
      setDeletingStock(item);
      setDeleteDialogOpen(true);
    } catch (error) {
      console.error('Error fetching transactions:', error);
      toast({ 
        title: 'Error', 
        description: error.response?.data?.detail || 'Failed to fetch transactions. Please try again.', 
        variant: 'destructive' 
      });
    }
  };
  
  const confirmDeleteTransaction = async (transaction) => {
    if (!window.confirm(`Are you sure you want to delete this ${transaction.type} transaction? This action cannot be undone.`)) {
      return;
    }
    
    try {
      // Delete based on transaction type
      if (transaction.type === 'inward') {
        await api.delete(`/inward-stock/${transaction.transaction_id}`);
      } else if (transaction.type === 'outward') {
        await api.delete(`/outward-stock/${transaction.transaction_id}`);
      }
      
      toast({ 
        title: 'Success', 
        description: 'Transaction deleted successfully' 
      });
      
      // Refresh data
      setDeleteDialogOpen(false);
      fetchStockSummary();
    } catch (error) {
      toast({ 
        title: 'Error', 
        description: error.response?.data?.detail || 'Failed to delete transaction', 
        variant: 'destructive' 
      });
    }
  };

  useEffect(() => {
    fetchData();
    fetchAlerts();
  }, []);

  useEffect(() => {
    fetchStockSummary();
  }, [filters]);

  const fetchData = async () => {
    try {
      const [warehousesRes, productsRes, companiesRes] = await Promise.all([
        api.get('/warehouses'),
        api.get('/products'),
        api.get('/companies')
      ]);
      setWarehouses(warehousesRes.data);
      setProducts(productsRes.data);
      setCompanies(companiesRes.data);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch basic data', variant: 'destructive' });
    }
  };

  const fetchStockSummary = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== '' && value !== false && value !== 0 && value !== 'all') {
          params.append(key, value.toString());
        }
      });
      
      const response = await api.get(`/stock-summary?${params.toString()}`);
      const data = response.data || [];
      setStockData(data);
      
      // Calculate summary statistics
      const stats = data.reduce((acc, item) => {
        acc.totalProducts += 1;
        acc.totalInward += item.quantity_inward || 0;
        acc.totalOutward += item.quantity_outward || 0;
        acc.totalStock += item.remaining_stock || 0;
        
        if (item.stock_status === 'Low Stock' || item.stock_status === 'Running Low') {
          acc.lowStockCount += 1;
        }
        if (item.stock_status === 'Out of Stock') {
          acc.outOfStockCount += 1;
        }
        
        return acc;
      }, {
        totalProducts: 0,
        totalInward: 0,
        totalOutward: 0,
        totalStock: 0,
        lowStockCount: 0,
        outOfStockCount: 0
      });
      
      setSummaryStats(stats);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch stock summary', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await api.get(`/low-stock-alerts?threshold=${filters.low_stock_threshold}`);
      setLowStockAlerts(response.data);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch alerts', variant: 'destructive' });
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => {
    setFilters({
      warehouse_id: 'all',
      company_id: 'all',
      sku: '',
      pi_number: '',
      category: 'all',
      low_stock_only: false,
      low_stock_threshold: 10
    });
  };

  const getStatusBadge = (status, stock) => {
    switch (status) {
      case 'Out of Stock':
        return <Badge variant="destructive" className="text-xs">Out of Stock</Badge>;
      case 'Low Stock':
        return <Badge variant="secondary" className="text-xs bg-red-100 text-red-800">Low Stock</Badge>;
      case 'Running Low':
        return <Badge variant="secondary" className="text-xs bg-yellow-100 text-yellow-800">Running Low</Badge>;
      default:
        return <Badge variant="secondary" className="text-xs bg-green-100 text-green-800">Normal</Badge>;
    }
  };

  const getStockAgeIndicator = (days) => {
    if (days > 90) return <span className="text-red-600 text-xs">Aging ({days}d)</span>;
    if (days > 30) return <span className="text-yellow-600 text-xs">Old ({days}d)</span>;
    return <span className="text-green-600 text-xs">Fresh ({days}d)</span>;
  };

  // Get unique categories from products
  const categories = [...new Set(products.map(p => p.category).filter(Boolean))];

  if (loading && stockData.length === 0) {
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
          <h1 className="text-3xl font-bold text-slate-900">Stock Summary</h1>
          <p className="text-slate-600 mt-1">Consolidated view of current inventory across all warehouses</p>
        </div>
        <Button 
          onClick={() => { fetchStockSummary(); fetchAlerts(); }}
          variant="outline"
          className="flex items-center gap-2"
        >
          <RefreshCw size={16} />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Total Products</CardDescription>
            <CardTitle className="text-2xl text-blue-600">{summaryStats.totalProducts}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Total Inward</CardDescription>
            <CardTitle className="text-2xl text-green-600">{summaryStats.totalInward.toFixed(0)}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Total Outward</CardDescription>
            <CardTitle className="text-2xl text-orange-600">{summaryStats.totalOutward.toFixed(0)}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Current Stock</CardDescription>
            <CardTitle className="text-2xl text-purple-600">{summaryStats.totalStock.toFixed(0)}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Low Stock Items</CardDescription>
            <CardTitle className="text-2xl text-yellow-600">{summaryStats.lowStockCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Out of Stock</CardDescription>
            <CardTitle className="text-2xl text-red-600">{summaryStats.outOfStockCount}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Low Stock Alerts */}
      {lowStockAlerts.length > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-800">
              <AlertTriangle size={20} />
              Low Stock Alerts ({lowStockAlerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {lowStockAlerts.slice(0, 5).map((alert, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-white rounded border">
                  <div className="flex items-center gap-3">
                    <AlertTriangle size={16} className={alert.alert_level === 'critical' ? 'text-red-600' : 'text-yellow-600'} />
                    <div>
                      <div className="font-medium text-slate-900">{alert.product_name}</div>
                      <div className="text-sm text-slate-600">{alert.sku} • {alert.warehouse_name}</div>
                    </div>
                  </div>
                  <Badge variant={alert.alert_level === 'critical' ? 'destructive' : 'secondary'}>
                    {alert.current_stock} left
                  </Badge>
                </div>
              ))}
              {lowStockAlerts.length > 5 && (
                <div className="text-sm text-slate-600 text-center pt-2">
                  And {lowStockAlerts.length - 5} more alerts...
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}


      {/* Stock Logic Explanation Banner */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 rounded-lg p-4 mb-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
          </div>
          <div>
            <h4 className="font-semibold text-blue-900 mb-1">📊 Stock Summary Calculation (Simplified)</h4>
            <div className="text-sm text-blue-800 space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold bg-green-100 text-green-800 px-2 py-0.5 rounded">✅ INWARD</span>
                <span>All inward entries (Pick-up + Warehouse) add to stock immediately</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-semibold bg-red-100 text-red-800 px-2 py-0.5 rounded">📤 OUTWARD</span>
                <span>Only Export Invoices reduce stock (Dispatch Plans don't affect stock)</span>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="font-semibold text-purple-800">🔢 Formula:</span>
                <span className="font-mono bg-purple-50 px-2 py-0.5 rounded">Remaining Stock = Total Inward - Total Export Invoices</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter size={20} />
            Filters & Search
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <div>
              <Label className="text-xs">Warehouse</Label>
              <Select
                value={filters.warehouse_id}
                onValueChange={(value) => {
                  setTimeout(() => handleFilterChange('warehouse_id', value), 0);
                }}
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="All warehouses" />
                </SelectTrigger>
                <SelectContent {...getSafeSelectContentProps()}>
                  <SelectItem value="all">All Warehouses</SelectItem>
                  {warehouses.map(warehouse => (
                    <SelectItem key={warehouse.id} value={warehouse.id}>
                      {warehouse.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Company</Label>
              <Select
                value={filters.company_id}
                onValueChange={(value) => {
                  setTimeout(() => handleFilterChange('company_id', value), 0);
                }}
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="All companies" />
                </SelectTrigger>
                <SelectContent {...getSafeSelectContentProps()}>
                  <SelectItem value="all">All Companies</SelectItem>
                  {companies.map(company => (
                    <SelectItem key={company.id} value={company.id}>
                      {company.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">SKU</Label>
              <Input
                placeholder="Search SKU..."
                className="h-8"
                value={filters.sku}
                onChange={(e) => handleFilterChange('sku', e.target.value)}
              />
            </div>
            <div>
              <Label className="text-xs">PI Number</Label>
              <Input
                placeholder="Search PI..."
                className="h-8"
                value={filters.pi_number}
                onChange={(e) => handleFilterChange('pi_number', e.target.value)}
              />
            </div>
            <div>
              <Label className="text-xs">Category</Label>
              <Select
                value={filters.category}
                onValueChange={(value) => {
                  setTimeout(() => handleFilterChange('category', value), 0);
                }}
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="All categories" />
                </SelectTrigger>
                <SelectContent {...getSafeSelectContentProps()}>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categories.map(category => (
                    <SelectItem key={category} value={category}>
                      {category}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Low Stock Threshold</Label>
              <Input
                type="number"
                className="h-8"
                value={filters.low_stock_threshold}
                onChange={(e) => handleFilterChange('low_stock_threshold', parseInt(e.target.value) || 10)}
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={filters.low_stock_only}
                  onChange={(e) => handleFilterChange('low_stock_only', e.target.checked)}
                />
                Low Stock Only
              </label>
            </div>
            <div className="flex items-end">
              <Button onClick={resetFilters} variant="outline" className="h-8 text-xs">
                Reset Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stock Summary Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package size={20} />
            Stock Summary ({stockData?.length || 0} items)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead>PI Number</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Warehouse</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead className="text-right">Inward</TableHead>
                  <TableHead className="text-right">Outward</TableHead>
                  <TableHead className="text-right">Remaining</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Age</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!stockData || stockData.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={12} className="text-center text-slate-500 py-8">
                      {filters.low_stock_only 
                        ? 'No low stock items found.'
                        : 'No stock data found. Try adjusting your filters.'
                      }
                    </TableCell>
                  </TableRow>
                ) : (
                  stockData.map((item, index) => (
                    <TableRow key={index} className={item.stock_status === 'Out of Stock' ? 'bg-red-50' : ''}>
                      <TableCell className="font-medium">{item.product_name}</TableCell>
                      <TableCell className="font-mono text-sm">{item.sku}</TableCell>
                      <TableCell className="font-mono text-xs text-blue-600">{item.pi_number || 'N/A'}</TableCell>
                      <TableCell>{item.category || '-'}</TableCell>
                      <TableCell>{item.warehouse_name || 'No Warehouse'}</TableCell>
                      <TableCell className="text-blue-700 font-medium">{item.company_name || 'N/A'}</TableCell>
                      <TableCell className="text-right text-green-600 font-semibold">
                        <div className="flex items-center justify-end gap-1">
                          <TrendingUp size={12} />
                          {item.quantity_inward}
                        </div>
                      </TableCell>
                      <TableCell className="text-right text-orange-600 font-semibold">
                        <div className="flex items-center justify-end gap-1">
                          <TrendingDown size={12} />
                          {item.quantity_outward}
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-bold">
                        <span className={`${
                          item.remaining_stock === 0 ? 'text-red-600' :
                          item.remaining_stock <= filters.low_stock_threshold ? 'text-yellow-600' :
                          'text-green-600'
                        }`}>
                          {item.remaining_stock}
                        </span>
                      </TableCell>
                      <TableCell>
                        {getStatusBadge(item.stock_status, item.remaining_stock)}
                      </TableCell>
                      <TableCell>
                        {getStockAgeIndicator(item.stock_age_days)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => handleViewStock(item)}>
                            <Eye size={16} className="text-blue-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleEditStock(item)}>
                            Edit
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDeleteStock(item)}>
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
        </CardContent>
      </Card>

      {/* View Transactions Dialog */}
      <Dialog open={viewTransactionsDialog} onOpenChange={setViewTransactionsDialog}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Transaction History</DialogTitle>
          </DialogHeader>
          
          {viewingTransactions && (
            <div className="space-y-4">
              {/* Product & Warehouse Info */}
              <div className="bg-slate-50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Product</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-semibold">
                      {viewingTransactions.product_name}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">SKU</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-mono">
                      {viewingTransactions.sku}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Warehouse</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {viewingTransactions.warehouse_name || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Current Stock</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-bold text-green-700">
                      {viewingTransactions.remaining_stock} units
                    </div>
                  </div>
                </div>
              </div>

              {/* Transaction History Table */}
              <div>
                <h3 className="text-lg font-semibold mb-3">All Transactions ({transactionHistory.length})</h3>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Type</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Reference No</TableHead>
                        <TableHead>Sub Type</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                        <TableHead className="text-right">Rate</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {transactionHistory.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} className="text-center text-slate-500 py-8">
                            No transactions found
                          </TableCell>
                        </TableRow>
                      ) : (
                        transactionHistory.map((txn, index) => (
                          <TableRow key={index}>
                            <TableCell>
                              <Badge variant={txn.type === 'inward' ? 'default' : 'secondary'} className="flex items-center gap-1 w-fit">
                                {txn.type === 'inward' ? <ArrowUpCircle size={14} /> : <ArrowDownCircle size={14} />}
                                {txn.type === 'inward' ? 'Inward' : 'Outward'}
                              </Badge>
                            </TableCell>
                            <TableCell>{new Date(txn.date).toLocaleDateString()}</TableCell>
                            <TableCell className="font-mono text-sm">{txn.reference_no}</TableCell>
                            <TableCell className="text-sm text-slate-600">
                              {txn.type === 'inward' ? txn.inward_type : txn.dispatch_type}
                            </TableCell>
                            <TableCell className={`text-right font-semibold ${txn.type === 'inward' ? 'text-green-600' : 'text-orange-600'}`}>
                              {txn.type === 'inward' ? '+' : '-'}{txn.quantity}
                            </TableCell>
                            <TableCell className="text-right">₹{txn.rate?.toFixed(2)}</TableCell>
                            <TableCell className="text-right font-semibold">₹{txn.amount?.toFixed(2)}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg">
                <div className="text-center">
                  <div className="text-sm text-slate-600">Total Inward</div>
                  <div className="text-2xl font-bold text-green-600">{viewingTransactions.quantity_inward}</div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-slate-600">Total Outward</div>
                  <div className="text-2xl font-bold text-orange-600">{viewingTransactions.quantity_outward}</div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-slate-600">Remaining</div>
                  <div className="text-2xl font-bold text-blue-600">{viewingTransactions.remaining_stock}</div>
                </div>
              </div>

              {/* Close Button */}
              <div className="flex justify-end">
                <Button variant="outline" onClick={() => setViewTransactionsDialog(false)}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Stock Dialog (Manual Adjustment) */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Manual Stock Adjustment</DialogTitle>
          </DialogHeader>
          
          {editingStock && (
            <div className="space-y-4">
              <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
                <p className="text-sm text-blue-800">
                  <strong>Note:</strong> To adjust stock levels, please navigate to:
                </p>
                <ul className="list-disc list-inside text-sm text-blue-700 mt-2 space-y-1">
                  <li><strong>Inward Stock</strong> page to add stock (increase quantity)</li>
                  <li><strong>Outward Stock</strong> page to reduce stock (decrease quantity)</li>
                </ul>
              </div>

              <div className="bg-slate-50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Product</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {editingStock.product_name}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Current Stock</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-bold text-green-700">
                      {editingStock.remaining_stock} units
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                  Close
                </Button>
                <Button onClick={() => {
                  setEditDialogOpen(false);
                  window.location.href = '/inward';
                }}>
                  Go to Inward Stock
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Transaction Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Delete Transaction</DialogTitle>
          </DialogHeader>
          
          {deletingStock && (
            <div className="space-y-4">
              <div className="bg-orange-50 border-l-4 border-orange-500 p-4 rounded">
                <p className="text-sm text-orange-800">
                  <strong>Warning:</strong> Deleting a transaction will update the stock summary. Select a transaction below to delete.
                </p>
              </div>

              <div className="bg-slate-50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Product</Label>
                    <div className="mt-1 p-2 bg-white rounded border font-semibold">
                      {deletingStock.product_name}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-slate-600">Warehouse</Label>
                    <div className="mt-1 p-2 bg-white rounded border">
                      {deletingStock.warehouse_name}
                    </div>
                  </div>
                </div>
              </div>

              {/* Transaction Type Filter */}
              <div>
                <Label className="text-sm font-medium">Filter by Transaction Type</Label>
                <Select
                  value={selectedTransactionType}
                  onValueChange={(value) => {
                    setTimeout(() => setSelectedTransactionType(value), 0);
                  }}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="All Transactions" />
                  </SelectTrigger>
                  <SelectContent {...getSafeSelectContentProps()}>
                    <SelectItem value="all">All Transactions</SelectItem>
                    <SelectItem value="inward">Inward Only</SelectItem>
                    <SelectItem value="outward">Outward Only</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Transactions List */}
              <div>
                <h3 className="text-lg font-semibold mb-3">Select Transaction to Delete</h3>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Type</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Reference No</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {deleteTransactions
                        .filter(txn => selectedTransactionType === 'all' || txn.type === selectedTransactionType)
                        .map((txn, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Badge variant={txn.type === 'inward' ? 'default' : 'secondary'} className="flex items-center gap-1 w-fit">
                              {txn.type === 'inward' ? <ArrowUpCircle size={14} /> : <ArrowDownCircle size={14} />}
                              {txn.type === 'inward' ? 'Inward' : 'Outward'}
                            </Badge>
                          </TableCell>
                          <TableCell>{new Date(txn.date).toLocaleDateString()}</TableCell>
                          <TableCell className="font-mono text-sm">{txn.reference_no}</TableCell>
                          <TableCell className={`text-right font-semibold ${txn.type === 'inward' ? 'text-green-600' : 'text-orange-600'}`}>
                            {txn.type === 'inward' ? '+' : '-'}{txn.quantity}
                          </TableCell>
                          <TableCell className="text-right">₹{txn.amount?.toFixed(2)}</TableCell>
                          <TableCell className="text-right">
                            <Button 
                              variant="destructive" 
                              size="sm" 
                              onClick={() => confirmDeleteTransaction(txn)}
                            >
                              <Trash2 size={14} className="mr-1" />
                              Delete
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                      {deleteTransactions.filter(txn => selectedTransactionType === 'all' || txn.type === selectedTransactionType).length === 0 && (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center text-slate-500 py-8">
                            No transactions found
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {/* Close Button */}
              <div className="flex justify-end">
                <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default StockSummary;