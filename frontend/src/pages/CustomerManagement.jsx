import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { formatCurrency, formatNumber } from '../utils/formatters';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Eye, RefreshCw, Filter, TrendingUp, TrendingDown, Edit, Trash2, ExternalLink, FileText, ChevronDown, ChevronRight } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import { getSafeSelectContentProps } from '../utils/selectHelpers';

const CustomerManagement = () => {
  const [activeTab, setActiveTab] = useState('pi-po-mapping');
  const [loading, setLoading] = useState(true);

  // Data states
  const [piPoMappingData, setPiPoMappingData] = useState([]);
  const [inwardData, setInwardData] = useState([]);
  const [outwardData, setOutwardData] = useState([]);

  // Pagination for PI-PO Mapping
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Filter states
  const [filters, setFilters] = useState({
    consignee: '',
    pi_number: '',
    po_number: '',
    sku: '',
    from_date: '',
    to_date: '',
    search: '',
    status: 'all'
  });

  // Dialog states
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [viewingData, setViewingData] = useState(null);
  const [viewDetailData, setViewDetailData] = useState(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingData, setEditingData] = useState(null);
  const [editType, setEditType] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingData, setDeletingData] = useState(null);

  // Expanded POs state for view dialog
  const [expandedPOs, setExpandedPOs] = useState({});

  const { toast } = useToast();
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchData();
  }, [activeTab, filters, page, pageSize]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'pi-po-mapping') {
        await fetchPiPoMapping();
      } else if (activeTab === 'inward-quantity') {
        await fetchInwardQuantity();
      } else if (activeTab === 'outward-quantity') {
        await fetchOutwardQuantity();
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch data',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchPiPoMapping = async () => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    if (filters.consignee) params.append('consignee', filters.consignee);
    if (filters.pi_number) params.append('pi_number', filters.pi_number);
    if (filters.po_number) params.append('po_number', filters.po_number);
    if (filters.sku) params.append('sku', filters.sku);
    if (filters.from_date) params.append('from_date', filters.from_date);
    if (filters.to_date) params.append('to_date', filters.to_date);
    if (filters.search) params.append('search', filters.search);

    const response = await api.get(`/pi-po-mapping?${params.toString()}`);
    setPiPoMappingData(response.data.data || []);
    setTotalPages(response.data.pagination?.total_pages || 1);
    setTotalCount(response.data.pagination?.total_count || 0);
  };

  const fetchInwardQuantity = async () => {
    const params = new URLSearchParams();
    if (filters.consignee) params.append('consignee', filters.consignee);
    if (filters.pi_number) params.append('pi_number', filters.pi_number);
    if (filters.po_number) params.append('po_number', filters.po_number);
    if (filters.sku) params.append('sku', filters.sku);

    const response = await api.get(`/customer-management/inward-quantity?${params.toString()}`);
    setInwardData(response.data);
  };

  const fetchOutwardQuantity = async () => {
    const params = new URLSearchParams();
    if (filters.consignee) params.append('consignee', filters.consignee);
    if (filters.pi_number) params.append('pi_number', filters.pi_number);
    if (filters.sku) params.append('sku', filters.sku);
    if (filters.status !== 'all') params.append('status', filters.status);

    const response = await api.get(`/customer-management/outward-quantity?${params.toString()}`);
    setOutwardData(response.data);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1); // Reset to first page on filter change
  };

  const resetFilters = () => {
    setFilters({
      consignee: '',
      pi_number: '',
      po_number: '',
      sku: '',
      from_date: '',
      to_date: '',
      search: '',
      status: 'all'
    });
    setPage(1);
  };

  const handleView = async (item) => {
    try {
      // Fetch detailed data
      const response = await api.get(`/pi-po-mapping/${item.id}`);
      setViewDetailData(response.data);
      setViewingData(item);
      setExpandedPOs({});
      setViewDialogOpen(true);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load details',
        variant: 'destructive'
      });
    }
  };

  const handleViewInward = (item) => {
    setViewingData(item);
    setViewDialogOpen(true);
  };

  const handleViewOutward = (item) => {
    setViewingData(item);
    setViewDialogOpen(true);
  };

  const togglePOExpansion = (poNumber) => {
    setExpandedPOs(prev => ({
      ...prev,
      [poNumber]: !prev[poNumber]
    }));
  };

  const handleEdit = (item) => {
    setEditingData(item);
    setEditType('pi-po-mapping');
    setEditDialogOpen(true);
  };

  const handleEditInward = (item) => {
    setEditingData({
      ...item,
      edit_dispatch_qty: item.inward_total_quantity,
      edit_pending_qty: item.remaining_quantity
    });
    setEditType('inward');
    setEditDialogOpen(true);
  };

  const handleEditOutward = (item) => {
    setEditingData({
      ...item,
      edit_dispatch_qty: item.outward_total_quantity,
      edit_pending_qty: item.remaining_quantity
    });
    setEditType('outward');
    setEditDialogOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editingData) return;

    try {
      if (editType === 'pi-po-mapping') {
        await api.put(`/pi-po-mapping/${editingData.id}`, {
          notes: editingData.notes || '',
          status: editingData.status || ''
        });
        toast({ title: 'Success', description: 'Mapping updated successfully' });
        fetchData();
      } else if (editType === 'inward' || editType === 'outward') {
        toast({
          title: 'Info',
          description: `${editType === 'inward' ? 'Inward' : 'Outward'} quantities are managed in their respective modules.`,
          variant: 'default'
        });
      }
      setEditDialogOpen(false);
      setEditingData(null);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to update', variant: 'destructive' });
    }
  };

  const handleDelete = (item) => {
    setDeletingData(item);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!deletingData) return;

    try {
      await api.delete(`/pi-po-mapping/${deletingData.id}`);
      toast({ title: 'Success', description: 'Mapping archived successfully' });
      setDeleteDialogOpen(false);
      setDeletingData(null);
      fetchData();
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to delete', variant: 'destructive' });
    }
  };

  const handleDeleteInward = async (item) => {
    if (!window.confirm(`Delete inward record for ${item.pi_number}?`)) return;
    toast({
      title: 'Info',
      description: 'Please delete from Inward Stock module',
      variant: 'default'
    });
  };

  const handleDeleteOutward = async (item) => {
    if (!window.confirm(`Delete outward record for ${item.pi_number}?`)) return;
    toast({
      title: 'Info',
      description: 'Please delete from Outward Stock module',
      variant: 'default'
    });
  };

  const getStatusBadge = (status) => {
    const statusColors = {
      'Not Started': 'bg-gray-100 text-gray-800',
      'In Progress': 'bg-blue-100 text-blue-800',
      'Completed': 'bg-green-100 text-green-800',
      'Partially Inwarded': 'bg-yellow-100 text-yellow-800',
      'Partially Outwarded': 'bg-orange-100 text-orange-800'
    };

    return (
      <Badge className={statusColors[status] || 'bg-gray-100 text-gray-800'}>
        {status}
      </Badge>
    );
  };

  if (loading && piPoMappingData.length === 0 && inwardData.length === 0 && outwardData.length === 0) {
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
          <h1 className="text-3xl font-bold text-slate-900">Customer Management</h1>
          <p className="text-slate-600 mt-1">
            {activeTab === 'pi-po-mapping'
              ? 'Track PI to PO mappings with SKU-level details'
              : 'Track inward and outward quantities'}
          </p>
        </div>
        <Button
          onClick={fetchData}
          variant="outline"
          className="flex items-center gap-2"
        >
          <RefreshCw size={16} />
          Refresh
        </Button>
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
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {activeTab === 'pi-po-mapping' && (
              <div className="col-span-2">
                <Label className="text-xs">Search</Label>
                <Input
                  placeholder="Search Consignee, PI, PO, SKU..."
                  className="h-8"
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                />
              </div>
            )}
            <div>
              <Label className="text-xs">Consignee</Label>
              <Input
                placeholder="Search consignee..."
                className="h-8"
                value={filters.consignee}
                onChange={(e) => handleFilterChange('consignee', e.target.value)}
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
            {activeTab !== 'outward-quantity' && (
              <div>
                <Label className="text-xs">PO Number</Label>
                <Input
                  placeholder="Search PO..."
                  className="h-8"
                  value={filters.po_number}
                  onChange={(e) => handleFilterChange('po_number', e.target.value)}
                />
              </div>
            )}
            <div>
              <Label className="text-xs">SKU</Label>
              <Input
                placeholder="Search SKU..."
                className="h-8"
                value={filters.sku}
                onChange={(e) => handleFilterChange('sku', e.target.value)}
              />
            </div>
            {activeTab === 'pi-po-mapping' && (
              <>
                <div>
                  <Label className="text-xs">From Date</Label>
                  <Input
                    type="date"
                    className="h-8"
                    value={filters.from_date}
                    onChange={(e) => handleFilterChange('from_date', e.target.value)}
                  />
                </div>
                <div>
                  <Label className="text-xs">To Date</Label>
                  <Input
                    type="date"
                    className="h-8"
                    value={filters.to_date}
                    onChange={(e) => handleFilterChange('to_date', e.target.value)}
                  />
                </div>
              </>
            )}
            {activeTab === 'outward-quantity' && (
              <div>
                <Label className="text-xs">Status</Label>
                <Select
                  value={filters.status}
                  onValueChange={(value) => {
                    setTimeout(() => handleFilterChange('status', value), 0);
                  }}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent {...getSafeSelectContentProps()}>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="Not Started">Not Started</SelectItem>
                    <SelectItem value="Partially Outwarded">Partially Outwarded</SelectItem>
                    <SelectItem value="Completed">Completed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="flex items-end">
              <Button variant="outline" size="sm" onClick={resetFilters} className="h-8">
                Reset
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="pi-po-mapping" className="flex items-center gap-2">
            <FileText size={16} />
            PI → PO Mapping
          </TabsTrigger>
          <TabsTrigger value="inward-quantity" className="flex items-center gap-2">
            <TrendingDown size={16} />
            Inward Quantity
          </TabsTrigger>
          <TabsTrigger value="outward-quantity" className="flex items-center gap-2">
            <TrendingUp size={16} />
            Outward Quantity
          </TabsTrigger>
        </TabsList>

        {/* PI → PO Mapping Tab */}
        <TabsContent value="pi-po-mapping" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>PI → PO Mapping ({totalCount} records)</span>
                <div className="text-sm font-normal text-slate-600">
                  Page {page} of {totalPages}
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Consignee</TableHead>
                      <TableHead>PI Number</TableHead>
                      <TableHead>PI Date</TableHead>
                      <TableHead className="text-right">PI Total Qty</TableHead>
                      <TableHead>Linked PO(s)</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {piPoMappingData.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-slate-500 py-8">
                          No PI-PO mapping data found
                        </TableCell>
                      </TableRow>
                    ) : (
                      piPoMappingData.map((item, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-medium">{item.consignee}</TableCell>
                          <TableCell>{item.pi_number}</TableCell>
                          <TableCell>{item.pi_date ? new Date(item.pi_date).toLocaleDateString() : 'N/A'}</TableCell>
                          <TableCell className="text-right font-semibold">{formatNumber(item.pi_total_quantity)}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="font-semibold">
                              {item.linked_po_count} PO(s)
                            </Badge>
                            {item.linked_pos && item.linked_pos.length > 0 && (
                              <div className="text-xs text-slate-500 mt-1">
                                {item.linked_pos[0].po_number}
                                {item.linked_pos.length > 1 && ` +${item.linked_pos.length - 1} more`}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button variant="ghost" size="sm" onClick={() => handleView(item)} title="View Details">
                                <Eye size={16} className="text-blue-600" />
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => handleEdit(item)} title="Edit Metadata">
                                <Edit size={16} className="text-green-600" />
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => handleDelete(item)} title="Archive">
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

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-sm">Page Size:</Label>
                    <Select
                      value={pageSize.toString()}
                      onValueChange={(value) => {
                        setPageSize(parseInt(value));
                        setPage(1);
                      }}
                    >
                      <SelectTrigger className="w-20 h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent {...getSafeSelectContentProps()}>
                        <SelectItem value="25">25</SelectItem>
                        <SelectItem value="50">50</SelectItem>
                        <SelectItem value="100">100</SelectItem>
                        <SelectItem value="200">200</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      Previous
                    </Button>
                    <span className="text-sm text-slate-600">
                      Page {page} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Inward Quantity Tab - keeping existing implementation */}
        <TabsContent value="inward-quantity" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Inward Quantity Tracking ({inwardData.length} records)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Consignee</TableHead>
                      <TableHead>PI Number</TableHead>
                      <TableHead>PO Number</TableHead>
                      <TableHead>PI Quantity</TableHead>
                      <TableHead>Inwarded</TableHead>
                      <TableHead>Remaining</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {inwardData.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-slate-500 py-8">
                          No inward quantity data found
                        </TableCell>
                      </TableRow>
                    ) : (
                      inwardData.map((item, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-medium">{item.consignee_name}</TableCell>
                          <TableCell>{item.pi_number}</TableCell>
                          <TableCell>{item.po_number}</TableCell>
                          <TableCell className="font-semibold">{formatNumber(item.pi_total_quantity)}</TableCell>
                          <TableCell className="text-green-600 font-semibold">{formatNumber(item.inward_total_quantity)}</TableCell>
                          <TableCell className="text-orange-600 font-semibold">{formatNumber(item.remaining_quantity)}</TableCell>
                          <TableCell>{getStatusBadge(item.status)}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button variant="ghost" size="sm" onClick={() => handleViewInward(item)} title="View">
                                <Eye size={16} className="text-blue-600" />
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => handleEditInward(item)} title="Edit">
                                <Edit size={16} className="text-green-600" />
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => handleDeleteInward(item)} title="Delete">
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
        </TabsContent>

        {/* Outward Quantity Tab - keeping existing implementation */}
        <TabsContent value="outward-quantity" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Outward Quantity Tracking ({outwardData.length} records)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Consignee</TableHead>
                      <TableHead>PI Number</TableHead>
                      <TableHead>PI Date</TableHead>
                      <TableHead>PI Quantity</TableHead>
                      <TableHead>Dispatched</TableHead>
                      <TableHead>Remaining</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {outwardData.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-slate-500 py-8">
                          No outward quantity data found
                        </TableCell>
                      </TableRow>
                    ) : (
                      outwardData.map((item, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-medium">{item.consignee_name}</TableCell>
                          <TableCell>{item.pi_number}</TableCell>
                          <TableCell>{item.pi_date ? new Date(item.pi_date).toLocaleDateString() : 'N/A'}</TableCell>
                          <TableCell className="font-semibold">{formatNumber(item.pi_total_quantity)}</TableCell>
                          <TableCell className="text-red-600 font-semibold">{formatNumber(item.outward_total_quantity)}</TableCell>
                          <TableCell className="text-orange-600 font-semibold">{formatNumber(item.remaining_quantity)}</TableCell>
                          <TableCell>{getStatusBadge(item.status)}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button variant="ghost" size="sm" onClick={() => handleViewOutward(item)} title="View">
                                <Eye size={16} className="text-blue-600" />
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => handleEditOutward(item)} title="Edit">
                                <Edit size={16} className="text-green-600" />
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => handleDeleteOutward(item)} title="Delete">
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
        </TabsContent>
      </Tabs>

      {/* View Dialog for PI → PO Mapping */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>PI → PO Mapping Details</DialogTitle>
          </DialogHeader>

          {viewDetailData && (
            <div className="space-y-6">
              {/* PI Header */}
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 rounded-lg">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-blue-100">PI Number</div>
                    <div className="text-lg font-bold">{viewDetailData.pi_number}</div>
                  </div>
                  <div>
                    <div className="text-xs text-blue-100">Consignee</div>
                    <div className="text-lg font-semibold">{viewDetailData.consignee}</div>
                  </div>
                  <div>
                    <div className="text-xs text-blue-100">PI Date</div>
                    <div className="text-lg font-semibold">
                      {viewDetailData.pi_date ? new Date(viewDetailData.pi_date).toLocaleDateString() : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-blue-100">Linked POs</div>
                    <div className="text-lg font-bold">
                      {viewDetailData.linked_po_count} PO(s)
                    </div>
                  </div>
                </div>
              </div>

              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-slate-600">PI Total Quantity</div>
                    <div className="text-2xl font-bold text-blue-600">{formatNumber(viewDetailData.pi_total_quantity)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-slate-600">Total PO Quantity</div>
                    <div className="text-2xl font-bold text-green-600">{formatNumber(viewDetailData.total_po_quantity)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-slate-600">Remaining Quantity</div>
                    <div className="text-2xl font-bold text-orange-600">{formatNumber(viewDetailData.total_remaining_quantity)}</div>
                  </CardContent>
                </Card>
              </div>

              {/* PI Items Summary */}
              <div>
                <h3 className="text-lg font-semibold mb-3">PI Items Summary</h3>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>SKU</TableHead>
                        <TableHead>Product Name</TableHead>
                        <TableHead className="text-right">PI Qty</TableHead>
                        <TableHead className="text-right">PI Rate</TableHead>
                        <TableHead className="text-right">Total PO Qty</TableHead>
                        <TableHead className="text-right">Remaining</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {viewDetailData.pi_items && viewDetailData.pi_items.map((item, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{item.sku}</TableCell>
                          <TableCell>{item.product_name}</TableCell>
                          <TableCell className="text-right font-semibold">{formatNumber(item.pi_quantity)}</TableCell>
                          <TableCell className="text-right">₹{formatCurrency(item.pi_rate)}</TableCell>
                          <TableCell className="text-right font-semibold text-green-600">{formatNumber(item.total_po_quantity)}</TableCell>
                          <TableCell className="text-right font-semibold text-orange-600">{formatNumber(item.remaining_quantity)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {/* Linked POs */}
              <div>
                <h3 className="text-lg font-semibold mb-3">Linked Purchase Orders</h3>
                {viewDetailData.linked_pos && viewDetailData.linked_pos.length === 0 ? (
                  <div className="text-center text-slate-500 py-8 border rounded-lg">
                    No Purchase Orders linked to this PI yet
                  </div>
                ) : (
                  <div className="space-y-4">
                    {viewDetailData.linked_pos && viewDetailData.linked_pos.map((po, poIdx) => (
                      <div key={poIdx} className="border rounded-lg overflow-hidden">
                        {/* PO Header */}
                        <div
                          className="bg-slate-100 p-3 flex items-center justify-between cursor-pointer hover:bg-slate-200 transition-colors"
                          onClick={() => togglePOExpansion(po.po_number)}
                        >
                          <div className="flex items-center gap-3">
                            {expandedPOs[po.po_number] ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                            <div>
                              <span className="font-semibold text-lg">{poIdx + 1}) PO Number: {po.po_number}</span>
                              <span className="text-sm text-slate-600 ml-4">
                                Date: {po.po_date ? new Date(po.po_date).toLocaleDateString() : 'N/A'}
                              </span>
                              <Badge variant="outline" className="ml-4">
                                {po.items?.length || 0} items
                              </Badge>
                            </div>
                          </div>
                        </div>

                        {/* PO Items Table (Collapsible) */}
                        {expandedPOs[po.po_number] && (
                          <div className="p-4">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>SKU</TableHead>
                                  <TableHead>Product Name</TableHead>
                                  <TableHead className="text-right">PI Qty</TableHead>
                                  <TableHead className="text-right">PI Rate</TableHead>
                                  <TableHead className="text-right">PO Qty</TableHead>
                                  <TableHead className="text-right">PO Rate</TableHead>
                                  <TableHead className="text-right">Remaining</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {po.items && po.items.map((item, itemIdx) => (
                                  <TableRow key={itemIdx}>
                                    <TableCell className="font-medium">{item.sku}</TableCell>
                                    <TableCell>{item.product_name}</TableCell>
                                    <TableCell className="text-right">{formatNumber(item.pi_quantity)}</TableCell>
                                    <TableCell className="text-right">₹{formatCurrency(item.pi_rate)}</TableCell>
                                    <TableCell className="text-right font-semibold text-green-600">{formatNumber(item.po_quantity)}</TableCell>
                                    <TableCell className="text-right">₹{formatCurrency(item.po_rate)}</TableCell>
                                    <TableCell className="text-right font-semibold">
                                      <span className={item.remaining_quantity > 0 ? 'text-orange-600' : 'text-green-600'}>
                                        {formatNumber(item.remaining_quantity)}
                                      </span>
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex justify-end">
                <Button onClick={() => setViewDialogOpen(false)}>Close</Button>
              </div>
            </div>
          )}

          {/* For inward/outward view */}
          {!viewDetailData && viewingData && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <Label className="text-sm font-medium text-slate-600">Consignee</Label>
                  <div className="mt-1 p-2 bg-slate-50 rounded border">{viewingData.consignee_name}</div>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-600">PI Number</Label>
                  <div className="mt-1 p-2 bg-slate-50 rounded border">{viewingData.pi_number}</div>
                </div>
                {viewingData.po_number && (
                  <div>
                    <Label className="text-sm font-medium text-slate-600">PO Number</Label>
                    <div className="mt-1 p-2 bg-slate-50 rounded border">{viewingData.po_number}</div>
                  </div>
                )}
                <div>
                  <Label className="text-sm font-medium text-slate-600">Total Quantity</Label>
                  <div className="mt-1 p-2 bg-slate-50 rounded border font-semibold">{formatNumber(viewingData.pi_total_quantity)}</div>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-600">
                    {viewingData.inward_total_quantity !== undefined ? 'Inwarded' : 'Dispatched'}
                  </Label>
                  <div className="mt-1 p-2 bg-slate-50 rounded border font-semibold text-green-700">
                    {formatNumber(viewingData.inward_total_quantity || viewingData.outward_total_quantity)}
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-600">Remaining</Label>
                  <div className="mt-1 p-2 bg-slate-50 rounded border font-semibold text-orange-600">
                    {formatNumber(viewingData.remaining_quantity)}
                  </div>
                </div>
              </div>

              {viewingData.sku_details && viewingData.sku_details.length > 0 && (
                <div>
                  <Label className="text-sm font-medium text-slate-700 mb-2 block">SKU Details</Label>
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>SKU</TableHead>
                          <TableHead>Product Name</TableHead>
                          <TableHead>PI Qty</TableHead>
                          <TableHead>{viewingData.inward_total_quantity !== undefined ? 'Inward Qty' : 'Outward Qty'}</TableHead>
                          <TableHead>Remaining</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {viewingData.sku_details.map((sku, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-medium">{sku.sku}</TableCell>
                            <TableCell>{sku.product_name}</TableCell>
                            <TableCell className="font-semibold">{formatNumber(sku.pi_quantity)}</TableCell>
                            <TableCell className="font-semibold text-green-600">
                              {formatNumber(sku.inward_quantity || sku.outward_quantity)}
                            </TableCell>
                            <TableCell className="font-semibold text-orange-600">{formatNumber(sku.remaining_quantity)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              <div className="flex justify-end">
                <Button onClick={() => setViewDialogOpen(false)}>Close</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editType === 'pi-po-mapping' ? 'Edit Mapping Metadata' :
                editType === 'inward' ? 'Edit Inward Quantities' : 'Edit Outward Quantities'}
            </DialogTitle>
          </DialogHeader>

          {editingData && (
            <div className="space-y-4">
              {editType === 'pi-po-mapping' ? (
                <>
                  <div>
                    <Label>PI Number</Label>
                    <Input value={editingData.pi_number} disabled className="bg-slate-50" />
                  </div>
                  <div>
                    <Label>Consignee</Label>
                    <Input value={editingData.consignee} disabled className="bg-slate-50" />
                  </div>
                  <div>
                    <Label>Notes</Label>
                    <Input
                      value={editingData.notes || ''}
                      onChange={(e) => setEditingData({ ...editingData, notes: e.target.value })}
                      placeholder="Add notes about this mapping..."
                    />
                  </div>
                  <div>
                    <Label>Status</Label>
                    <Input
                      value={editingData.status || ''}
                      onChange={(e) => setEditingData({ ...editingData, status: e.target.value })}
                      placeholder="e.g., In Progress, Completed"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
                    <p className="text-sm text-blue-800">
                      <strong>Note:</strong> Quantity adjustments should be done in the source modules.
                    </p>
                    <ul className="list-disc list-inside text-sm text-blue-700 mt-2 space-y-1">
                      <li><strong>Inward Stock</strong> module for inward quantity changes</li>
                      <li><strong>Outward Stock</strong> module for outward quantity changes</li>
                    </ul>
                  </div>

                  <div className="bg-slate-50 rounded-lg p-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-sm font-medium text-slate-600">Consignee</Label>
                        <div className="mt-1 p-2 bg-white rounded border">{editingData.consignee_name}</div>
                      </div>
                      <div>
                        <Label className="text-sm font-medium text-slate-600">PI Number</Label>
                        <div className="mt-1 p-2 bg-white rounded border">{editingData.pi_number}</div>
                      </div>
                      <div>
                        <Label className="text-sm font-medium text-slate-600">Total Quantity</Label>
                        <div className="mt-1 p-2 bg-white rounded border font-semibold">{formatNumber(editingData.pi_total_quantity)}</div>
                      </div>
                      <div>
                        <Label className="text-sm font-medium text-slate-600">
                          {editType === 'inward' ? 'Inwarded' : 'Dispatched'}
                        </Label>
                        <div className="mt-1 p-2 bg-white rounded border font-semibold text-green-700">
                          {formatNumber(editType === 'inward' ? editingData.inward_total_quantity : editingData.outward_total_quantity)}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setEditDialogOpen(false)}>Cancel</Button>
                {editType === 'pi-po-mapping' ? (
                  <Button onClick={handleSaveEdit}>Save Changes</Button>
                ) : (
                  <Button onClick={() => {
                    setEditDialogOpen(false);
                    window.location.href = editType === 'inward' ? '/inward' : '/outward';
                  }}>
                    <ExternalLink size={16} className="mr-2" />
                    Go to {editType === 'inward' ? 'Inward' : 'Outward'} Stock
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Archive PI Mapping</DialogTitle>
          </DialogHeader>

          {deletingData && (
            <div className="space-y-4">
              <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
                <p className="text-sm text-red-800">
                  <strong>Warning:</strong> This will archive the PI mapping. The PI and linked POs will be marked as inactive.
                </p>
              </div>

              <div className="space-y-2">
                <div><strong>PI Number:</strong> {deletingData.pi_number}</div>
                <div><strong>Consignee:</strong> {deletingData.consignee}</div>
                <div><strong>Linked POs:</strong> {deletingData.linked_po_count}</div>
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
                <Button variant="destructive" onClick={confirmDelete}>Archive</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CustomerManagement;
