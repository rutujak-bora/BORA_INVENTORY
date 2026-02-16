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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Plus, Eye, Edit, Trash2, RefreshCw, DollarSign, X, Search, Calendar } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import { getSafeSelectContentProps } from '../utils/selectHelpers';

const ExpenseCalculation = () => {
  const [expenses, setExpenses] = useState([]);
  const [exportInvoices, setExportInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [viewingExpense, setViewingExpense] = useState(null);
  const [dateFilter, setDateFilter] = useState({ from: '', to: '' });

  const [formData, setFormData] = useState({
    expense_reference_no: '',
    date: new Date().toISOString().split('T')[0],
    export_invoice_ids: [],
    export_invoice_nos_manual: '',
    freight_charges: 0,
    freight_vendor: '',
    cha_charges: 0,
    cha_vendor: '',
    other_charges: 0,
    other_charges_description: '',
    payment_status: 'Pending',
    notes: ''
  });

  const { toast } = useToast();
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchData();
    fetchExportInvoices();
  }, []);

  const fetchData = async (fromDate = '', toDate = '') => {
    setLoading(true);
    try {
      let url = '/expenses';
      if (fromDate && toDate) {
        url += `?from_date=${fromDate}&to_date=${toDate}`;
      }
      const response = await api.get(url);
      setExpenses(response.data);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch expenses', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const fetchExportInvoices = async () => {
    try {
      const response = await api.get('/outward-stock');
      // Filter only Export Invoice and Direct Export types
      const filtered = response.data.filter(o =>
        ['export_invoice', 'direct_export'].includes(o.dispatch_type)
      );
      setExportInvoices(filtered);
    } catch (error) {
      console.error('Failed to fetch export invoices:', error);
    }
  };

  const handleExportInvoiceToggle = (invoiceId) => {
    setFormData(prev => {
      const currentIds = prev.export_invoice_ids;
      const isSelected = currentIds.includes(invoiceId);

      if (isSelected) {
        return {
          ...prev,
          export_invoice_ids: currentIds.filter(id => id !== invoiceId)
        };
      } else {
        return {
          ...prev,
          export_invoice_ids: [...currentIds, invoiceId]
        };
      }
    });
  };

  const calculateTotal = () => {
    return (
      parseFloat(formData.freight_charges) +
      parseFloat(formData.cha_charges) +
      parseFloat(formData.other_charges)
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.export_invoice_ids.length === 0 && !formData.export_invoice_nos_manual) {
      toast({
        title: 'Error',
        description: 'Please select at least one export invoice or enter manually',
        variant: 'destructive'
      });
      return;
    }

    try {
      if (editingExpense) {
        await api.put(`/expenses/${editingExpense.id}`, formData);
        toast({ title: 'Success', description: 'Expense updated successfully' });
      } else {
        await api.post('/expenses', formData);
        toast({ title: 'Success', description: 'Expense record created successfully' });
      }

      fetchData();
      setDialogOpen(false);
      resetForm();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Operation failed',
        variant: 'destructive'
      });
    }
  };

  const handleEdit = async (expense) => {
    try {
      const fullExpense = await api.get(`/expenses/${expense.id}`);
      setEditingExpense(fullExpense.data);
      setFormData({
        expense_reference_no: fullExpense.data.expense_reference_no,
        date: fullExpense.data.date.split('T')[0],
        export_invoice_ids: fullExpense.data.export_invoice_ids || [],
        export_invoice_nos_manual: fullExpense.data.export_invoice_nos_manual || '',
        freight_charges: fullExpense.data.freight_charges || 0,
        freight_vendor: fullExpense.data.freight_vendor || '',
        cha_charges: fullExpense.data.cha_charges || 0,
        cha_vendor: fullExpense.data.cha_vendor || '',
        other_charges: fullExpense.data.other_charges || 0,
        other_charges_description: fullExpense.data.other_charges_description || '',
        payment_status: fullExpense.data.payment_status || 'Pending',
        notes: fullExpense.data.notes || ''
      });
      setDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch expense details', variant: 'destructive' });
    }
  };

  const handleView = async (expense) => {
    try {
      const fullExpense = await api.get(`/expenses/${expense.id}`);
      setViewingExpense(fullExpense.data);
      setViewDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch expense details', variant: 'destructive' });
    }
  };

  const handleDelete = async (expense) => {
    if (window.confirm('Are you sure you want to delete this expense record?')) {
      try {
        await api.delete(`/expenses/${expense.id}`);
        toast({ title: 'Success', description: 'Expense deleted successfully' });
        fetchData();
      } catch (error) {
        toast({ title: 'Error', description: 'Failed to delete expense', variant: 'destructive' });
      }
    }
  };

  const resetForm = () => {
    setFormData({
      expense_reference_no: '',
      date: new Date().toISOString().split('T')[0],
      export_invoice_ids: [],
      export_invoice_nos_manual: '',
      freight_charges: 0,
      freight_vendor: '',
      cha_charges: 0,
      cha_vendor: '',
      other_charges: 0,
      other_charges_description: '',
      payment_status: 'Pending',
      notes: ''
    });
    setEditingExpense(null);
  };

  const openCreateDialog = () => {
    resetForm();
    setDialogOpen(true);
  };

  const handleDateFilter = () => {
    if (dateFilter.from && dateFilter.to) {
      fetchData(dateFilter.from, dateFilter.to);
    }
  };

  const clearDateFilter = () => {
    setDateFilter({ from: '', to: '' });
    fetchData();
  };

  const getPaymentStatusBadge = (status) => {
    const colors = {
      'Paid': 'bg-green-100 text-green-800',
      'Pending': 'bg-yellow-100 text-yellow-800',
      'Partial': 'bg-orange-100 text-orange-800'
    };
    return <Badge className={colors[status] || 'bg-gray-100 text-gray-800'}>{status}</Badge>;
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
          <h1 className="text-3xl font-bold text-slate-900">Expense Calculation</h1>
          <p className="text-slate-600 mt-1">Track shipment expenses tied to Export Invoices</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={fetchData} variant="outline">
            <RefreshCw size={16} className="mr-2" />
            Refresh
          </Button>
          <Button onClick={openCreateDialog}>
            <Plus size={16} className="mr-2" />
            Create Expense
          </Button>
        </div>
      </div>

      {/* Date Filter */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <Label className="text-xs">From Date</Label>
              <Input
                type="date"
                value={dateFilter.from}
                onChange={(e) => setDateFilter(prev => ({ ...prev, from: e.target.value }))}
              />
            </div>
            <div className="flex-1">
              <Label className="text-xs">To Date</Label>
              <Input
                type="date"
                value={dateFilter.to}
                onChange={(e) => setDateFilter(prev => ({ ...prev, to: e.target.value }))}
              />
            </div>
            <Button onClick={handleDateFilter}>
              <Calendar size={16} className="mr-2" />
              Apply Filter
            </Button>
            <Button variant="outline" onClick={clearDateFilter}>
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Expenses Table */}
      <Card>
        <CardHeader>
          <CardTitle>Expense Records ({expenses.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Reference No</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Export Invoices</TableHead>
                  <TableHead className="text-right">Freight</TableHead>
                  <TableHead className="text-right">CHA</TableHead>
                  <TableHead className="text-right">Other</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead>Payment</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {expenses.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-slate-500 py-8">
                      No expense records found
                    </TableCell>
                  </TableRow>
                ) : (
                  expenses.map((expense) => (
                    <TableRow key={expense.id}>
                      <TableCell className="font-medium">{expense.expense_reference_no}</TableCell>
                      <TableCell>{new Date(expense.date).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <div className="max-w-[200px]">
                          {expense.export_invoice_details?.length > 0 ? (
                            <div className="text-sm space-y-1">
                              {expense.export_invoice_details.map(inv => (
                                <div key={inv.id}>
                                  <span className="font-medium">{inv.export_invoice_no}</span>
                                  {inv.export_invoice_number && (
                                    <span className="text-blue-600 ml-2">({inv.export_invoice_number})</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span className="text-sm text-slate-500">{expense.export_invoice_nos_manual || 'N/A'}</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">₹{formatCurrency(expense.freight_charges)}</TableCell>
                      <TableCell className="text-right">₹{formatCurrency(expense.cha_charges)}</TableCell>
                      <TableCell className="text-right">₹{formatCurrency(expense.other_charges)}</TableCell>
                      <TableCell className="text-right font-bold text-blue-600">₹{formatCurrency(expense.total_expense)}</TableCell>
                      <TableCell>{getPaymentStatusBadge(expense.payment_status)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => handleView(expense)} title="View">
                            <Eye size={16} className="text-blue-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(expense)}>
                            <Edit size={16} className="text-slate-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(expense)}>
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

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingExpense ? 'Edit Expense Record' : 'Create Expense Record'}</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Info */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Reference No</Label>
                <Input
                  value={formData.expense_reference_no}
                  onChange={(e) => setFormData({ ...formData, expense_reference_no: e.target.value })}
                  placeholder="Auto-generated if empty"
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
              <div>
                <Label>Payment Status</Label>
                <Select
                  value={formData.payment_status}
                  onValueChange={(value) => {
                    setTimeout(() => setFormData({ ...formData, payment_status: value }), 0);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent {...getSafeSelectContentProps()}>
                    <SelectItem value="Pending">Pending</SelectItem>
                    <SelectItem value="Partial">Partial</SelectItem>
                    <SelectItem value="Paid">Paid</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Export Invoice Selection */}
            <div className="bg-blue-50 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Export Invoices (Select Multiple)</h3>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2 max-h-[200px] overflow-y-auto p-2 bg-white rounded border">
                  {exportInvoices.map(invoice => {
                    const isSelected = formData.export_invoice_ids.includes(invoice.id);
                    return (
                      <div
                        key={invoice.id}
                        onClick={() => handleExportInvoiceToggle(invoice.id)}
                        className={`p-3 rounded border cursor-pointer transition-all ${isSelected
                            ? 'bg-blue-100 border-blue-500'
                            : 'bg-white border-slate-200 hover:border-blue-300'
                          }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-semibold text-sm">{invoice.export_invoice_no}</div>
                            {invoice.export_invoice_number && (
                              <div className="text-xs text-blue-600 font-medium">Invoice #: {invoice.export_invoice_number}</div>
                            )}
                            <div className="text-xs text-slate-600">{invoice.dispatch_type}</div>
                          </div>
                          {isSelected && (
                            <Badge className="bg-blue-500">Selected</Badge>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div>
                  <Label>Or Enter Manually (comma-separated)</Label>
                  <Input
                    value={formData.export_invoice_nos_manual}
                    onChange={(e) => setFormData({ ...formData, export_invoice_nos_manual: e.target.value })}
                    placeholder="e.g., EXP-001, EXP-002"
                  />
                </div>

                {formData.export_invoice_ids.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    <Label className="w-full">Selected: </Label>
                    {formData.export_invoice_ids.map(id => {
                      const invoice = exportInvoices.find(inv => inv.id === id);
                      return invoice ? (
                        <Badge key={id} variant="outline" className="flex items-center gap-1">
                          {invoice.export_invoice_no}
                          <X
                            size={14}
                            className="cursor-pointer hover:text-red-600"
                            onClick={() => handleExportInvoiceToggle(id)}
                          />
                        </Badge>
                      ) : null;
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Expense Details */}
            <div className="bg-slate-50 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Expense Breakdown</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Freight Charges (₹)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.freight_charges}
                      onChange={(e) => setFormData({ ...formData, freight_charges: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div>
                    <Label>Freight Vendor</Label>
                    <Input
                      value={formData.freight_vendor}
                      onChange={(e) => setFormData({ ...formData, freight_vendor: e.target.value })}
                      placeholder="Enter vendor name"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>CHA Charges (₹)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.cha_charges}
                      onChange={(e) => setFormData({ ...formData, cha_charges: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div>
                    <Label>CHA Vendor</Label>
                    <Input
                      value={formData.cha_vendor}
                      onChange={(e) => setFormData({ ...formData, cha_vendor: e.target.value })}
                      placeholder="Enter vendor name"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Other Charges (₹)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.other_charges}
                      onChange={(e) => setFormData({ ...formData, other_charges: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div>
                    <Label>Other Charges Description</Label>
                    <Input
                      value={formData.other_charges_description}
                      onChange={(e) => setFormData({ ...formData, other_charges_description: e.target.value })}
                      placeholder="e.g., Documentation, Handling"
                    />
                  </div>
                </div>

                <div className="bg-blue-100 p-4 rounded">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-lg">Total Expense:</span>
                    <span className="font-bold text-2xl text-blue-700">₹{formatCurrency(calculateTotal())}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Notes */}
            <div>
              <Label>Notes</Label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full min-h-[80px] p-2 border rounded-md"
                placeholder="Enter any additional notes..."
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">
                {editingExpense ? 'Update Expense' : 'Create Expense'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Expense Details - {viewingExpense?.expense_reference_no}</DialogTitle>
          </DialogHeader>

          {viewingExpense && (
            <div className="space-y-4">
              {/* Header */}
              <div className="bg-slate-50 rounded-lg p-4">
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <Label className="text-sm text-slate-600">Reference No</Label>
                    <div className="font-semibold">{viewingExpense.expense_reference_no}</div>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Date</Label>
                    <div>{new Date(viewingExpense.date).toLocaleDateString()}</div>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Payment Status</Label>
                    <div>{getPaymentStatusBadge(viewingExpense.payment_status)}</div>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Total Expense</Label>
                    <div className="font-bold text-blue-600 text-xl">₹{formatCurrency(viewingExpense.total_expense)}</div>
                  </div>
                </div>
              </div>

              {/* Expense Breakdown */}
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">Freight Charges</div>
                    <div className="text-2xl font-bold text-slate-900">₹{formatCurrency(viewingExpense.freight_charges)}</div>
                    {viewingExpense.freight_vendor && (
                      <div className="text-xs text-slate-500 mt-1">Vendor: {viewingExpense.freight_vendor}</div>
                    )}
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">CHA Charges</div>
                    <div className="text-2xl font-bold text-slate-900">₹{formatCurrency(viewingExpense.cha_charges)}</div>
                    {viewingExpense.cha_vendor && (
                      <div className="text-xs text-slate-500 mt-1">Vendor: {viewingExpense.cha_vendor}</div>
                    )}
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">Other Charges</div>
                    <div className="text-2xl font-bold text-slate-900">₹{formatCurrency(viewingExpense.other_charges)}</div>
                    {viewingExpense.other_charges_description && (
                      <div className="text-xs text-slate-500 mt-1">{viewingExpense.other_charges_description}</div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Export Invoices and Stock Items */}
              {viewingExpense.export_invoice_details?.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3">Export Invoices & Stock Items</h3>
                  {viewingExpense.export_invoice_details.map((invoice, idx) => (
                    <div key={idx} className="mb-4 border rounded-lg p-4 bg-green-50">
                      <div className="flex justify-between items-center mb-3">
                        <div>
                          <div className="font-semibold text-lg">{invoice.export_invoice_no}</div>
                          <div className="text-sm text-slate-600">
                            {invoice.dispatch_type} | {invoice.mode} | {invoice.status}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-slate-600">Stock Value</div>
                          <div className="font-bold text-green-700">₹{formatCurrency(invoice.items_total_value)}</div>
                        </div>
                      </div>

                      <div className="border rounded-lg overflow-hidden bg-white">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>SKU</TableHead>
                              <TableHead>Product</TableHead>
                              <TableHead className="text-right">Quantity</TableHead>
                              <TableHead className="text-right">Rate</TableHead>
                              <TableHead className="text-right">Amount</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {invoice.line_items?.map((item, itemIdx) => (
                              <TableRow key={itemIdx}>
                                <TableCell className="font-mono">{item.sku}</TableCell>
                                <TableCell>{item.product_name}</TableCell>
                                <TableCell className="text-right">{formatNumber(item.quantity)}</TableCell>
                                <TableCell className="text-right">₹{formatCurrency(item.rate)}</TableCell>
                                <TableCell className="text-right font-semibold">₹{formatCurrency(item.amount)}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  ))}

                  <div className="bg-blue-100 p-4 rounded-lg mt-4">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold">Total Stock Value (All Invoices):</span>
                      <span className="font-bold text-xl text-blue-700">₹{formatCurrency(viewingExpense.total_stock_value)}</span>
                    </div>
                  </div>
                </div>
              )}

              {viewingExpense.export_invoice_nos_manual && (
                <div className="bg-yellow-50 rounded-lg p-4">
                  <Label className="text-sm text-slate-600">Manual Export Invoice Numbers</Label>
                  <div className="font-mono mt-1">{viewingExpense.export_invoice_nos_manual}</div>
                </div>
              )}

              {/* Notes */}
              {viewingExpense.notes && (
                <div className="bg-slate-50 rounded-lg p-4">
                  <h3 className="font-semibold mb-2">Notes</h3>
                  <p className="text-sm">{viewingExpense.notes}</p>
                </div>
              )}

              {/* Close Button */}
              <div className="flex justify-end">
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

export default ExpenseCalculation;
