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
import { Plus, Eye, Edit, Trash2, RefreshCw, DollarSign, Search, Package, Receipt } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import { getSafeSelectContentProps } from '../utils/selectHelpers';
import ExtraPaymentPanel from '../components/PaymentTracking/ExtraPaymentPanel';

const PaymentTracking = () => {
  const [payments, setPayments] = useState([]);
  const [pis, setPis] = useState([]);
  const [banks, setBanks] = useState([]);
  const [outwardStock, setOutwardStock] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [paymentEntryDialogOpen, setPaymentEntryDialogOpen] = useState(false);
  const [exportDetailsDialogOpen, setExportDetailsDialogOpen] = useState(false);
  const [extraPaymentDialogOpen, setExtraPaymentDialogOpen] = useState(false);
  const [shortPaymentDialogOpen, setShortPaymentDialogOpen] = useState(false);
  const [editingPayment, setEditingPayment] = useState(null);
  const [viewingPayment, setViewingPayment] = useState(null);
  const [selectedPaymentForEntry, setSelectedPaymentForEntry] = useState(null);
  const [selectedPaymentForExport, setSelectedPaymentForExport] = useState(null);
  const [selectedPaymentForExtra, setSelectedPaymentForExtra] = useState(null);
  const [selectedPaymentForShort, setSelectedPaymentForShort] = useState(null);
  const [shortPaymentNote, setShortPaymentNote] = useState('');
  const [exportDetails, setExportDetails] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  const [formData, setFormData] = useState({
    pi_id: '',
    date: new Date().toISOString().split('T')[0],
    total_amount: 0,
    total_quantity: 0,
    advance_payment: 0,
    received_amount: 0,
    bank_id: '',
    bank_name: '',
    bank_details: '',
    dispatch_qty: 0,
    pending_qty: 0,
    dispatch_date: '',
    export_invoice_no: '',
    dispatch_goods_value: 0,
    notes: '',
    manual_entry: '',
  });

  const [paymentEntryForm, setPaymentEntryForm] = useState({
    date: new Date().toISOString().split('T')[0],
    received_amount: 0,
    receipt_number: '',
    bank_id: '',
    notes: ''
  });

  const { toast } = useToast();
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchData();
    fetchPIs();
    fetchBanks();
    fetchOutwardStock();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/payments');
      setPayments(response.data);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch payments', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const fetchPIs = async () => {
    try {
      const response = await api.get('/pi');
      setPis(response.data);
    } catch (error) {
      console.error('Failed to fetch PIs:', error);
    }
  };

  const fetchOutwardStock = async () => {
    try {
      const response = await api.get('/outward-stock');
      setOutwardStock(response.data);
    } catch (error) {
      console.error('Failed to fetch outward stock:', error);
    }
  };

  const fetchBanks = async () => {
    try {
      const response = await api.get('/banks');
      setBanks(response.data);
    } catch (error) {
      console.error('Failed to fetch banks:', error);
    }
  };


  const handlePISelect = async (piId) => {
    setFormData(prev => ({ ...prev, pi_id: piId }));

    if (!piId) return;

    try {
      // Fetch PI details
      const piResponse = await api.get(`/pi/${piId}`);
      const pi = piResponse.data;

      // Calculate total amount and quantity
      const lineItems = pi.line_items || [];
      const totalAmount = lineItems.reduce((sum, item) => sum + (item.amount || 0), 0);
      const totalQuantity = lineItems.reduce((sum, item) => sum + (item.quantity || 0), 0);

      // Fetch dispatch quantities from outward stock
      const outwardResponse = await api.get(`/outward-stock`);
      const dispatches = outwardResponse.data.filter(o =>
        (o.pi_id === piId || o.pi_ids?.includes(piId)) &&
        ['export_invoice', 'dispatch_plan'].includes(o.dispatch_type)
      );

      let dispatchQty = 0;
      let dispatchValue = 0;
      let exportInvoiceNos = [];

      dispatches.forEach(dispatch => {
        dispatch.line_items?.forEach(item => {
          dispatchQty += item.quantity || 0;
          dispatchValue += item.amount || 0;
        });
        if (dispatch.export_invoice_no) {
          exportInvoiceNos.push(dispatch.export_invoice_no);
        }
      });

      const pendingQty = totalQuantity - dispatchQty;

      setFormData(prev => ({
        ...prev,
        total_amount: totalAmount,
        total_quantity: totalQuantity,
        dispatch_qty: dispatchQty,
        pending_qty: pendingQty,
        dispatch_goods_value: dispatchValue,
        export_invoice_no: exportInvoiceNos.join(', ')
      }));

      toast({
        title: 'PI Details Loaded',
        description: `Total Amount: ₹${formatCurrency(totalAmount)}, Quantity: ${formatNumber(totalQuantity)}`
      });

    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch PI details', variant: 'destructive' });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.pi_id) {
      toast({ title: 'Error', description: 'Please select a PI', variant: 'destructive' });
      return;
    }

    try {
      if (editingPayment) {
        await api.put(`/payments/${editingPayment.id}`, formData);
        toast({ title: 'Success', description: 'Payment updated successfully' });
      } else {
        await api.post('/payments', formData);
        toast({ title: 'Success', description: 'Payment record created successfully' });
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

  const handleEdit = async (payment) => {
    try {
      const fullPayment = await api.get(`/payments/${payment.id}`);
      setEditingPayment(fullPayment.data);
      setFormData({
        pi_id: fullPayment.data.pi_id,
        date: fullPayment.data.date.split('T')[0],
        total_amount: fullPayment.data.total_amount || 0,
        total_quantity: fullPayment.data.total_quantity || 0,
        advance_payment: fullPayment.data.advance_payment || 0,
        received_amount: fullPayment.data.received_amount || 0,
        bank_name: fullPayment.data.bank_name || '',
        bank_details: fullPayment.data.bank_details || '',
        dispatch_qty: fullPayment.data.dispatch_qty || 0,
        pending_qty: fullPayment.data.pending_qty || 0,
        dispatch_date: fullPayment.data.dispatch_date || '',
        export_invoice_no: fullPayment.data.export_invoice_no || '',
        dispatch_goods_value: fullPayment.data.dispatch_goods_value || 0,
        notes: fullPayment.data.notes || ''
      });
      setDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch payment details', variant: 'destructive' });
    }
  };

  const handleView = async (payment) => {
    try {
      const fullPayment = await api.get(`/payments/${payment.id}`);
      setViewingPayment(fullPayment.data);
      setViewDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch payment details', variant: 'destructive' });
    }
  };

  const handleDelete = async (payment) => {
    if (window.confirm('Are you sure you want to delete this payment record?')) {
      try {
        await api.delete(`/payments/${payment.id}`);
        toast({ title: 'Success', description: 'Payment deleted successfully' });
        fetchData();
      } catch (error) {
        toast({ title: 'Error', description: 'Failed to delete payment', variant: 'destructive' });
      }
    }
  };

  const resetForm = () => {
    setFormData({
      pi_id: '',
      date: new Date().toISOString().split('T')[0],
      total_amount: 0,
      total_quantity: 0,
      advance_payment: 0,
      received_amount: 0,
      bank_id: '',
      bank_name: '',
      bank_details: '',
      dispatch_qty: 0,
      pending_qty: 0,
      dispatch_date: '',
      export_invoice_no: '',
      dispatch_goods_value: 0,
      notes: ''
    });
    setEditingPayment(null);
  };

  const handleAddPaymentEntry = async () => {
    if (!selectedPaymentForEntry) return;

    try {
      const response = await api.post(`/payments/${selectedPaymentForEntry.id}/entries`, paymentEntryForm);
      toast({ title: 'Success', description: 'Payment entry added successfully' });
      fetchData();
      setPaymentEntryDialogOpen(false);
      setPaymentEntryForm({
        date: new Date().toISOString().split('T')[0],
        received_amount: 0,
        receipt_number: '',
        bank_id: '',
        notes: ''
      });
    } catch (error) {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Failed to add payment entry', variant: 'destructive' });
    }
  };

  const handleDeleteEntry = async (entryId) => {
    if (!viewingPayment) return;

    if (window.confirm('Are you sure you want to delete this payment entry? Data will be adjusted in the Remaining section.')) {
      try {
        await api.delete(`/payments/${viewingPayment.id}/entries/${entryId}`);
        toast({ title: 'Success', description: 'Payment entry deleted successfully' });

        // Find the entry being deleted to update local state
        const deletedEntry = viewingPayment.payment_entries.find(e => e.id === entryId);
        const amountToSubtract = deletedEntry?.received_amount || 0;

        // Update local viewingPayment state
        setViewingPayment(prev => {
          const updatedEntries = prev.payment_entries.filter(e => e.id !== entryId);
          const newReceivedVal = (prev.received_amount || 0) - amountToSubtract;
          const newTotalReceived = (prev.total_received || 0) - amountToSubtract;
          const newRemaining = (prev.remaining_payment || 0) + amountToSubtract;

          return {
            ...prev,
            payment_entries: updatedEntries,
            received_amount: newReceivedVal,
            total_received: newTotalReceived,
            remaining_payment: newRemaining,
            is_fully_paid: newRemaining <= 0
          };
        });

        // Refresh all payments
        fetchData();
      } catch (error) {
        toast({
          title: 'Error',
          description: error.response?.data?.detail || 'Failed to delete payment entry',
          variant: 'destructive'
        });
      }
    }
  };

  const handleBankSelect = async (bankId) => {
    setFormData(prev => ({ ...prev, bank_id: bankId }));

    if (!bankId) return;

    try {
      const response = await api.get(`/banks/${bankId}`);
      const bank = response.data;

      setFormData(prev => ({
        ...prev,
        bank_name: bank.bank_name || '',
        bank_details: `IFSC: ${bank.ifsc_code || ''}, AD Code: ${bank.ad_code || ''}, Account: ${bank.account_number || ''}`
      }));
    } catch (error) {
      console.error('Failed to fetch bank details:', error);
    }
  };

  const handleBankSelectForEntry = async (bankId) => {
    setPaymentEntryForm(prev => ({ ...prev, bank_id: bankId }));
  };

  const handleViewExportDetails = async (payment) => {
    setSelectedPaymentForExport(payment);
    try {
      const response = await api.get(`/payments/${payment.id}/export-details`);
      setExportDetails(response.data);
      setExportDetailsDialogOpen(true);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch export details', variant: 'destructive' });
    }
  };

  const openPaymentEntryDialog = (payment) => {
    // Check if short payment
    if (payment.short_payment_status) {
      if (!checkShortPaymentBeforeAction(payment, 'payment')) {
        return;
      }
    }

    // Check if fully paid
    if (payment.is_fully_paid) {
      toast({ title: 'Info', description: 'This payment is already fully paid', variant: 'default' });
      return;
    }

    setSelectedPaymentForEntry(payment);
    setPaymentEntryForm({
      date: new Date().toISOString().split('T')[0],
      received_amount: payment.remaining_payment || 0,
      receipt_number: '',
      bank_id: '',
      notes: ''
    });
    setPaymentEntryDialogOpen(true);
  };

  const openExtraPaymentDialog = (payment) => {
    // Check if short payment
    if (payment.short_payment_status) {
      if (!checkShortPaymentBeforeAction(payment, 'extra-payment')) {
        return;
      }
    }

    setSelectedPaymentForExtra(payment);
    setExtraPaymentDialogOpen(true);
  };

  const handleExtraPaymentSave = () => {
    // Refresh payments to show updated totals
    fetchData();
  };

  const openShortPaymentDialog = (payment) => {
    setSelectedPaymentForShort(payment);
    setShortPaymentNote('');
    setShortPaymentDialogOpen(true);
  };

  const handleMarkShortPayment = async () => {
    if (!shortPaymentNote.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Please enter a note explaining why this is a short payment',
        variant: 'destructive'
      });
      return;
    }

    try {
      await api.post(`/payments/${selectedPaymentForShort.id}/short-payment`, {
        note: shortPaymentNote
      });

      toast({
        title: 'Success',
        description: 'Payment marked as Short Payment successfully'
      });

      setShortPaymentDialogOpen(false);
      setShortPaymentNote('');
      fetchData();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to mark as short payment',
        variant: 'destructive'
      });
    }
  };

  const handleReopenShortPayment = async (payment) => {
    if (!confirm('Do you want to reopen this PI for receiving payments?')) {
      return;
    }

    try {
      await api.post(`/payments/${payment.id}/reopen-short-payment`);

      toast({
        title: 'Success',
        description: 'Short payment reopened successfully. You can now add payments.'
      });

      fetchData();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to reopen short payment',
        variant: 'destructive'
      });
    }
  };

  const checkShortPaymentBeforeAction = (payment, action) => {
    if (payment.short_payment_status) {
      if (confirm('This PI is marked as Short Payment. Do you want to reopen it to add a payment?')) {
        handleReopenShortPayment(payment);
      }
      return false;
    }
    return true;
  };

  const openCreateDialog = () => {
    resetForm();
    setDialogOpen(true);
  };

  const filteredPayments = payments.filter(payment =>
    payment.pi_voucher_no?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    payment.company_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getPaymentStatusBadge = (payment) => {
    // Check for short payment first
    if (payment.short_payment_status) {
      return <Badge className="bg-red-100 text-red-800">Short Payment Closed</Badge>;
    }

    const remaining = payment.remaining_payment || 0;
    if (remaining <= 0) {
      return <Badge className="bg-green-100 text-green-800">Fully Paid</Badge>;
    } else if (payment.advance_payment > 0 || payment.received_amount > 0) {
      return <Badge className="bg-yellow-100 text-yellow-800">Partial Payment</Badge>;
    } else {
      return <Badge className="bg-red-100 text-red-800">Pending</Badge>;
    }
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
          <h1 className="text-3xl font-bold text-slate-900">Payment Tracking</h1>
          <p className="text-slate-600 mt-1">Track payments against proforma Invoices</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={fetchData} variant="outline">
            <RefreshCw size={16} className="mr-2" />
            Refresh
          </Button>
          <Button onClick={openCreateDialog}>
            <Plus size={16} className="mr-2" />
            Create Payment Record
          </Button>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2">
            <Search size={20} className="text-slate-400" />
            <Input
              placeholder="Search by PI number or company..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-md"
            />
          </div>
        </CardContent>
      </Card>

      {/* Payments Table */}
      <Card>
        <CardHeader>
          <CardTitle>Payment Records ({filteredPayments.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>PI Number</TableHead>
                  <TableHead>Manual PI Entry</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead className="text-right">Total Amount</TableHead>
                  <TableHead className="text-right">Advance</TableHead>
                  <TableHead className="text-right">Received</TableHead>
                  <TableHead className="text-right">Remaining</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPayments.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-slate-500 py-8">
                      No payment records found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredPayments.map((payment) => (
                    <TableRow key={payment.id}>
                      <TableCell className="font-medium">{payment.pi_voucher_no}</TableCell>
                      <TableCell className="font-medium">{payment.manual_entry}</TableCell>
                      <TableCell>{new Date(payment.date).toLocaleDateString()}</TableCell>
                      <TableCell>{payment.company_name || 'N/A'}</TableCell>
                      <TableCell className="text-right font-semibold">₹{formatCurrency(payment.total_amount)}</TableCell>
                      <TableCell className="text-right text-blue-600">₹{formatCurrency(payment.advance_payment)}</TableCell>
                      <TableCell className="text-right text-green-600">
                        <div>
                          ₹{formatCurrency(payment.total_received || (payment.advance_payment || 0) + (payment.received_amount || 0))}
                        </div>
                        {payment.extra_payments_total > 0 && (
                          <div className="text-xs text-slate-500">
                            (incl. ₹{formatCurrency(payment.extra_payments_total)} extra)
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-semibold">
                        <span className={payment.remaining_payment < 0 ? 'text-red-600' : 'text-orange-600'}>
                          ₹{formatCurrency(payment.remaining_payment)}
                        </span>
                        {payment.remaining_payment < 0 && (
                          <div className="text-xs text-red-500">Overpaid</div>
                        )}
                      </TableCell>
                      <TableCell>{getPaymentStatusBadge(payment)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openPaymentEntryDialog(payment)}
                            title="Add Payment"
                            disabled={payment.is_fully_paid}
                            className={payment.is_fully_paid ? 'opacity-50 cursor-not-allowed' : ''}
                          >
                            <DollarSign size={16} className="text-green-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openExtraPaymentDialog(payment)}
                            title="Extra Payment"
                          >
                            <Receipt size={16} className="text-orange-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => payment.short_payment_status ? handleReopenShortPayment(payment) : openShortPaymentDialog(payment)}
                            title={payment.short_payment_status ? "Reopen Short Payment" : "Mark as Short Payment"}
                            className={payment.short_payment_status ? 'bg-red-50' : ''}
                          >
                            <DollarSign size={16} className={payment.short_payment_status ? "text-red-600" : "text-slate-600"} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewExportDetails(payment)}
                            title="Export Details"
                          >
                            <Package size={16} className="text-purple-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleView(payment)} title="View">
                            <Eye size={16} className="text-blue-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(payment)}>
                            <Edit size={16} className="text-slate-600" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(payment)}>
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
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingPayment ? 'Edit Payment Record' : 'Create Payment Record'}</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* PI Selection */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>proforma Invoice (PI) *</Label>
                <Select
                  value={formData.pi_id}
                  onValueChange={(value) => {
                    setTimeout(() => handlePISelect(value), 0);
                  }}
                  disabled={!!editingPayment}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select PI" />
                  </SelectTrigger>
                  <SelectContent {...getSafeSelectContentProps()}>
                    {pis.map(pi => (
                      <SelectItem key={pi.id} value={pi.id}>
                        {pi.voucher_no} - {pi.consignee}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="col-span-4">
                <Label>Add PI Entry</Label>
                <Input
                  value={formData.manual_entry}
                  onChange={(e) =>
                    setFormData({ ...formData, manual_entry: e.target.value })
                  }
                  placeholder="Enter manual reference / remarks"
                />
              </div>
              <div>
                <Label>Date</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                />
              </div>
            </div>

            {/* Payment Details */}
            <div className="bg-slate-50 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Payment Details</h3>
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <Label>PI Total Amount (₹)</Label>
                  <Input
                    type="number"
                    value={formData.total_amount}
                    readOnly
                    className="bg-gray-100 font-semibold"
                  />
                </div>
                <div>
                  <Label>Advance Payment (₹)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.advance_payment}
                    onChange={(e) => setFormData({ ...formData, advance_payment: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div>
                  <Label>Received Amount (₹)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.received_amount}
                    onChange={(e) => setFormData({ ...formData, received_amount: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div>
                  <Label>Remaining Payment (Auto)</Label>
                  <Input
                    type="text"
                    value={`₹${formatCurrency(formData.total_amount - formData.advance_payment - formData.received_amount)}`}
                    disabled
                    className="bg-gray-100"
                  />
                </div>
              </div>
            </div>

            {/* Bank Details */}
            <div className="bg-blue-50 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Bank Details</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Select Bank *</Label>
                  <Select
                    value={formData.bank_id}
                    onValueChange={handleBankSelect}
                    {...getSafeSelectContentProps()}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select bank" />
                    </SelectTrigger>
                    <SelectContent>
                      {banks.map(bank => (
                        <SelectItem key={bank.id} value={bank.id}>
                          {bank.bank_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Bank Details (Auto-filled)</Label>
                  <Input
                    value={formData.bank_details}
                    readOnly
                    placeholder="IFSC, AD Code, Account will auto-fill"
                    className="bg-gray-100"
                  />
                </div>
              </div>
            </div>

            {/* Dispatch Details */}
            <div className="bg-green-50 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Dispatch Details (Auto-calculated, Editable)</h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label>Dispatch Quantity</Label>
                  <Input
                    type="number"
                    value={formData.dispatch_qty}
                    onChange={(e) => setFormData({ ...formData, dispatch_qty: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div>
                  <Label>Pending Quantity</Label>
                  <Input
                    type="number"
                    value={formData.pending_qty}
                    onChange={(e) => setFormData({ ...formData, pending_qty: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div>
                  <Label>Dispatch Date</Label>
                  <Input
                    type="date"
                    value={formData.dispatch_date}
                    onChange={(e) => setFormData({ ...formData, dispatch_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div>
                  <Label>Export Invoice No (Auto-filled, Editable)</Label>
                  <Input
                    value={formData.export_invoice_no}
                    onChange={(e) => setFormData({ ...formData, export_invoice_no: e.target.value })}
                    placeholder="Enter or select export invoice"
                  />
                </div>
                <div>
                  <Label>Dispatch Goods Value (₹)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.dispatch_goods_value}
                    onChange={(e) => setFormData({ ...formData, dispatch_goods_value: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
            </div>

            {/* Notes */}
            <div>
              <Label>Notes</Label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full min-h-[100px] p-2 border rounded-md"
                placeholder="Enter any notes or remarks..."
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">
                {editingPayment ? 'Update Payment' : 'Create Payment'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Payment Details</DialogTitle>
          </DialogHeader>

          {viewingPayment && (
            <div className="space-y-4">
              {/* Header Info */}
              <div className="bg-slate-50 rounded-lg p-4">
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-sm text-slate-600">PI Number</Label>
                    <div className="font-semibold">{viewingPayment.pi_voucher_no}</div>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Date</Label>
                    <div>{new Date(viewingPayment.date).toLocaleDateString()}</div>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Status</Label>
                    <div>{getPaymentStatusBadge(viewingPayment)}</div>
                  </div>
                </div>
              </div>

              {/* Short Payment Warning */}
              {viewingPayment.short_payment_status && (
                <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
                  <div className="flex items-start">
                    <div className="flex-1">
                      <h3 className="text-red-800 font-semibold mb-2">⚠️ Short Payment Closed</h3>
                      <p className="text-sm text-red-700 mb-2">
                        <strong>Reason:</strong> {viewingPayment.short_payment_note}
                      </p>
                      <p className="text-xs text-red-600">
                        Marked on: {viewingPayment.short_payment_date ? new Date(viewingPayment.short_payment_date).toLocaleString() : 'N/A'}
                      </p>
                      {viewingPayment.short_payment_reopened_at && (
                        <p className="text-xs text-green-600 mt-1">
                          Reopened on: {new Date(viewingPayment.short_payment_reopened_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="ml-4"
                      onClick={() => handleReopenShortPayment(viewingPayment)}
                    >
                      Reopen
                    </Button>
                  </div>
                </div>
              )}

              {/* Payment Summary */}
              <div className="grid grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">Total Amount</div>
                    <div className="text-2xl font-bold text-slate-900">₹{formatCurrency(viewingPayment.total_amount)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">Advance Payment</div>
                    <div className="text-2xl font-bold text-blue-600">₹{formatCurrency(viewingPayment.advance_payment)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">Payments Received</div>
                    <div className="text-2xl font-bold text-green-600">
                      ₹{formatCurrency(viewingPayment.received_amount || 0)}
                    </div>
                    {viewingPayment.payment_entries && viewingPayment.payment_entries.length > 0 && (
                      <div className="text-xs text-slate-500 mt-1">
                        ({viewingPayment.payment_entries.length} payment{viewingPayment.payment_entries.length > 1 ? 's' : ''})
                      </div>
                    )}
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">Remaining</div>
                    <div className={`text-2xl font-bold ${viewingPayment.remaining_payment < 0 ? 'text-red-600' : 'text-orange-600'}`}>
                      ₹{formatCurrency(viewingPayment.remaining_payment)}
                    </div>
                    {viewingPayment.is_fully_paid && (
                      <div className="text-xs text-green-600 mt-1 font-semibold">✓ Fully Paid</div>
                    )}
                    {viewingPayment.remaining_payment < 0 && (
                      <div className="text-xs text-red-500 mt-1 font-semibold">⚠️ Overpaid</div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Calculation Formula */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <h3 className="font-semibold mb-3 text-slate-700">Payment Calculation</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Total Amount:</span>
                    <span className="font-semibold">₹{formatCurrency(viewingPayment.total_amount)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Less: Advance Payment:</span>
                    <span className="font-semibold text-blue-600">- ₹{formatCurrency(viewingPayment.advance_payment || 0)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Less: Received Payments:</span>
                    <span className="font-semibold text-green-600">- ₹{formatCurrency(viewingPayment.received_amount || 0)}</span>
                  </div>
                  {viewingPayment.extra_payments_total > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-slate-600">Less: Extra Payments:</span>
                      <span className="font-semibold text-orange-600">- ₹{formatCurrency(viewingPayment.extra_payments_total)}</span>
                    </div>
                  )}
                  <div className="border-t border-slate-300 pt-2 mt-2">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-slate-700">Remaining Payment:</span>
                      <span className={`text-lg font-bold ${viewingPayment.remaining_payment < 0 ? 'text-red-600' : 'text-orange-600'}`}>
                        ₹{formatCurrency(viewingPayment.remaining_payment)}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs text-slate-500 mt-2 italic">
                    Formula: Total - Advance - Received - Extra = Remaining
                  </div>
                </div>
              </div>

              {/* Bank Details */}
              {(viewingPayment.bank_name || viewingPayment.bank_details) && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="font-semibold mb-2">Bank Details</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-sm text-slate-600">Bank Name</Label>
                      <div>{viewingPayment.bank_name || 'N/A'}</div>
                    </div>
                    <div>
                      <Label className="text-sm text-slate-600">Bank Details</Label>
                      <div>{viewingPayment.bank_details || 'N/A'}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Dispatch Details */}
              <div className="bg-green-50 rounded-lg p-4">
                <h3 className="font-semibold mb-2">Dispatch Information</h3>
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <Label className="text-sm text-slate-600">Dispatch Qty</Label>
                    <div className="font-semibold">{viewingPayment.dispatch_qty || 0}</div>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Pending Qty</Label>
                    <div className="font-semibold">{viewingPayment.pending_qty || 0}</div>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Dispatch Date</Label>
                    <div>{viewingPayment.dispatch_date ? new Date(viewingPayment.dispatch_date).toLocaleDateString() : 'N/A'}</div>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Goods Value</Label>
                    <div className="font-semibold">₹{formatCurrency(viewingPayment.dispatch_goods_value)}</div>
                  </div>
                </div>
                {viewingPayment.export_invoice_no && (
                  <div className="mt-4">
                    <Label className="text-sm text-slate-600">Export Invoice No</Label>
                    <div className="font-mono">{viewingPayment.export_invoice_no}</div>
                  </div>
                )}
              </div>

              {/* Notes */}
              {viewingPayment.notes && (
                <div className="bg-yellow-50 rounded-lg p-4">
                  <h3 className="font-semibold mb-2">Notes</h3>
                  <p className="text-sm">{viewingPayment.notes}</p>
                </div>
              )}

              {/* PI Line Items */}
              {viewingPayment.pi_details?.line_items && (
                <div>
                  <h3 className="font-semibold mb-3">PI Line Items</h3>
                  <div className="border rounded-lg overflow-hidden">
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
                        {viewingPayment.pi_details.line_items.map((item, index) => (
                          <TableRow key={index}>
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
              )}

              {/* Payment Entries History */}
              {viewingPayment.payment_entries && viewingPayment.payment_entries.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3">Payment Entries History</h3>
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Date</TableHead>
                          <TableHead>Receipt No</TableHead>
                          <TableHead className="text-right">Received Amount</TableHead>
                          <TableHead>Bank</TableHead>
                          <TableHead>Notes</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {viewingPayment.payment_entries.map((entry, index) => (
                          <TableRow key={index}>
                            <TableCell>{entry.date ? new Date(entry.date).toLocaleDateString() : 'N/A'}</TableCell>
                            <TableCell className="font-mono">{entry.receipt_number || '-'}</TableCell>
                            <TableCell className="text-right font-semibold text-green-600">
                              ₹{formatCurrency(entry.received_amount)}
                            </TableCell>
                            <TableCell>{entry.bank_id ? banks.find(b => b.id === entry.bank_id)?.bank_name : '-'}</TableCell>
                            <TableCell className="text-slate-600 text-sm">{entry.notes || '-'}</TableCell>
                            <TableCell className="text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteEntry(entry.id)}
                                className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                title="Delete Entry"
                              >
                                <Trash2 size={16} />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                        <TableRow className="bg-slate-100">
                          <TableCell colSpan={2} className="font-semibold">Total Received</TableCell>
                          <TableCell className="text-right font-bold text-green-600">
                            ₹{formatCurrency(viewingPayment.payment_entries.reduce((sum, e) => sum + (e.received_amount || 0), 0))}
                          </TableCell>
                          <TableCell colSpan={3}></TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
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


      {/* Add Payment Entry Dialog */}
      <Dialog open={paymentEntryDialogOpen} onOpenChange={setPaymentEntryDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Add Payment Entry</DialogTitle>
          </DialogHeader>

          {selectedPaymentForEntry && (
            <div className="space-y-4">
              {/* Payment Info */}
              <div className="bg-slate-50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-slate-600">PI Number:</span>
                    <span className="font-semibold ml-2">{selectedPaymentForEntry.pi_voucher_no}</span>
                  </div>
                  <div>
                    <span className="text-slate-600">Total Amount:</span>
                    <span className="font-semibold ml-2">₹{formatCurrency(selectedPaymentForEntry.total_amount)}</span>
                  </div>
                  <div>
                    <span className="text-slate-600">Already Received:</span>
                    <span className="font-semibold ml-2 text-green-600">₹{formatCurrency((selectedPaymentForEntry.advance_payment || 0) + (selectedPaymentForEntry.total_received || 0))}</span>
                  </div>
                  <div>
                    <span className="text-slate-600">Remaining:</span>
                    <span className="font-semibold ml-2 text-orange-600">₹{formatCurrency(selectedPaymentForEntry.remaining_payment)}</span>
                  </div>
                </div>
              </div>

              {/* Payment Entry Form */}
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Date *</Label>
                    <Input
                      type="date"
                      value={paymentEntryForm.date}
                      onChange={(e) => setPaymentEntryForm({ ...paymentEntryForm, date: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label>Received Amount *</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={paymentEntryForm.received_amount}
                      onChange={(e) => setPaymentEntryForm({ ...paymentEntryForm, received_amount: parseFloat(e.target.value) || 0 })}
                      placeholder="Enter amount"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Receipt Number</Label>
                    <Input
                      value={paymentEntryForm.receipt_number}
                      onChange={(e) => setPaymentEntryForm({ ...paymentEntryForm, receipt_number: e.target.value })}
                      placeholder="Enter receipt number"
                    />
                  </div>
                  <div>
                    <Label>Bank</Label>
                    <Select
                      value={paymentEntryForm.bank_id}
                      onValueChange={handleBankSelectForEntry}
                      {...getSafeSelectContentProps()}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select bank" />
                      </SelectTrigger>
                      <SelectContent>
                        {banks.map(bank => (
                          <SelectItem key={bank.id} value={bank.id}>
                            {bank.bank_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <Label>Notes</Label>
                  <Input
                    value={paymentEntryForm.notes}
                    onChange={(e) => setPaymentEntryForm({ ...paymentEntryForm, notes: e.target.value })}
                    placeholder="Optional notes"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setPaymentEntryDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAddPaymentEntry}>
                  Add Payment
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Export Details Dialog */}
      <Dialog open={exportDetailsDialogOpen} onOpenChange={setExportDetailsDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Export Details</DialogTitle>
          </DialogHeader>

          {exportDetails && selectedPaymentForExport && (
            <div className="space-y-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">PI Total Quantity</div>
                    <div className="text-2xl font-bold text-slate-900">{formatNumber(exportDetails.pi_total_quantity)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">Total Exported</div>
                    <div className="text-2xl font-bold text-green-600">{formatNumber(exportDetails.total_exported)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-600">Remaining for Export</div>
                    <div className="text-2xl font-bold text-orange-600">{formatNumber(exportDetails.remaining_for_export)}</div>
                  </CardContent>
                </Card>
              </div>

              {/* Export Invoice Details */}
              <div>
                <h3 className="font-semibold mb-3">Export Invoice Details</h3>
                {exportDetails.export_invoices && exportDetails.export_invoices.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Export Invoice No</TableHead>
                          <TableHead>Date</TableHead>
                          <TableHead>Mode</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="text-right">PI Total Qty</TableHead>
                          <TableHead className="text-right">Exported Qty</TableHead>
                          <TableHead className="text-right">Remaining</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {exportDetails.export_invoices.map((invoice, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-mono">{invoice.export_invoice_no}</TableCell>
                            <TableCell>{invoice.date ? new Date(invoice.date).toLocaleDateString() : 'N/A'}</TableCell>
                            <TableCell>
                              <Badge variant="outline">{invoice.mode || 'N/A'}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant={invoice.status === 'Delivered' ? 'success' : 'default'}>
                                {invoice.status || 'N/A'}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{formatNumber(invoice.pi_total_quantity)}</TableCell>
                            <TableCell className="text-right font-semibold text-green-600">
                              {formatNumber(invoice.exported_quantity)}
                            </TableCell>
                            <TableCell className="text-right font-semibold text-orange-600">
                              {formatNumber(invoice.remaining_for_export)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    No export invoices found for this PI
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <Button variant="outline" onClick={() => setExportDetailsDialogOpen(false)}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Extra Payment Dialog */}
      <Dialog open={extraPaymentDialogOpen} onOpenChange={setExtraPaymentDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Extra Payments</DialogTitle>
          </DialogHeader>

          {selectedPaymentForExtra && (
            <ExtraPaymentPanel
              piNumber={selectedPaymentForExtra.pi_voucher_no}
              onClose={() => setExtraPaymentDialogOpen(false)}
              onSave={handleExtraPaymentSave}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Short Payment Dialog */}
      <Dialog open={shortPaymentDialogOpen} onOpenChange={setShortPaymentDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Mark as Short Payment</DialogTitle>
          </DialogHeader>

          {selectedPaymentForShort && (
            <div className="space-y-4">
              <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded">
                <p className="text-sm text-yellow-800">
                  <strong>Warning:</strong> Marking this PI as "Short Payment" will close it for further payment entries.
                </p>
                <p className="text-sm text-yellow-700 mt-2">
                  You can reopen it later if needed by clicking the Short Payment button again.
                </p>
              </div>

              <div>
                <Label className="text-sm font-medium text-slate-600">PI Number</Label>
                <div className="mt-1 p-2 bg-slate-50 rounded border">
                  {selectedPaymentForShort.pi_voucher_no}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label className="text-sm font-medium text-slate-600">Total Amount</Label>
                  <div className="mt-1 p-2 bg-slate-50 rounded border font-semibold">
                    ₹{formatCurrency(selectedPaymentForShort.total_amount)}
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-600">Total Received</Label>
                  <div className="mt-1 p-2 bg-slate-50 rounded border font-semibold text-green-600">
                    ₹{formatCurrency((selectedPaymentForShort.advance_payment || 0) + (selectedPaymentForShort.received_amount || 0) + (selectedPaymentForShort.extra_payments_total || 0))}
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-600">Remaining</Label>
                  <div className="mt-1 p-2 bg-slate-50 rounded border font-semibold text-orange-600">
                    ₹{formatCurrency(selectedPaymentForShort.remaining_payment)}
                  </div>
                </div>
              </div>

              <div>
                <Label className="text-sm font-medium text-slate-700">
                  Note <span className="text-red-500">*</span>
                </Label>
                <p className="text-xs text-slate-500 mb-2">
                  Explain why this payment will not be fully received (e.g., deduction, discount, goods damaged, cancellation, adjustment)
                </p>
                <textarea
                  value={shortPaymentNote}
                  onChange={(e) => setShortPaymentNote(e.target.value)}
                  placeholder="Enter reason for short payment..."
                  className="w-full p-3 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShortPaymentDialogOpen(false);
                    setShortPaymentNote('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleMarkShortPayment}
                  className="bg-red-600 hover:bg-red-700"
                  disabled={!shortPaymentNote.trim()}
                >
                  Mark as Short Payment
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

    </div>
  );
};

export default PaymentTracking;
