import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Plus, Save, Trash2, X, Edit } from 'lucide-react';
import { useToast } from '../../hooks/use-toast';
import { getSafeSelectContentProps } from '../../utils/selectHelpers';

const ExtraPaymentPanel = ({ piNumber, onClose, onSave }) => {
  const [extraPayments, setExtraPayments] = useState([]);
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();
  
  useEffect(() => {
    fetchExtraPayments();
    fetchBanks();
  }, [piNumber]);
  
  const fetchExtraPayments = async () => {
    try {
      const response = await api.get(`/extra-payments?pi_number=${encodeURIComponent(piNumber)}`);
      setExtraPayments(response.data.map(payment => ({
        ...payment,
        isEditing: false,
        isNew: false
      })));
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch extra payments',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };
  
  const fetchBanks = async () => {
    try {
      const response = await api.get('/banks');
      const activeBanks = response.data.filter(bank => bank.is_active);
      setBanks(activeBanks);
      
      if (activeBanks.length === 0) {
        toast({
          title: 'Warning',
          description: 'No banks available. Please add banks in the Banks module first.',
          variant: 'default'
        });
      }
    } catch (error) {
      console.error('Failed to fetch banks:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch banks from the Banks module',
        variant: 'destructive'
      });
    }
  };
  
  const addNewRow = () => {
    const newPayment = {
      id: `temp-${Date.now()}`,
      date: new Date().toISOString().split('T')[0],
      receipt: '',
      bank_id: '',
      bank_name: '',
      amount: 0,
      isEditing: true,
      isNew: true
    };
    setExtraPayments([newPayment, ...extraPayments]);
  };
  
  const handleFieldChange = (id, field, value) => {
    setExtraPayments(extraPayments.map(payment => {
      if (payment.id === id) {
        const updated = { ...payment, [field]: value };
        
        // Update bank_name when bank_id changes
        if (field === 'bank_id') {
          const selectedBank = banks.find(bank => bank.id === value);
          updated.bank_name = selectedBank ? selectedBank.bank_name : '';
        }
        
        return updated;
      }
      return payment;
    }));
  };
  
  const validatePayment = (payment) => {
    if (!payment.date) {
      toast({
        title: 'Validation Error',
        description: 'Date is required',
        variant: 'destructive'
      });
      return false;
    }
    
    if (!payment.bank_id) {
      toast({
        title: 'Validation Error',
        description: 'Bank is required',
        variant: 'destructive'
      });
      return false;
    }
    
    if (!payment.amount || payment.amount <= 0) {
      toast({
        title: 'Validation Error',
        description: 'Amount must be greater than 0',
        variant: 'destructive'
      });
      return false;
    }
    
    return true;
  };
  
  const savePayment = async (payment) => {
    if (!validatePayment(payment)) {
      return;
    }
    
    setSaving(true);
    
    try {
      const paymentData = {
        date: payment.date,
        receipt: payment.receipt || '',
        bank_id: payment.bank_id,
        amount: parseFloat(payment.amount)
      };
      
      if (payment.isNew) {
        // Create new payment
        const response = await api.post(
          `/extra-payments?pi_number=${encodeURIComponent(piNumber)}`,
          paymentData
        );
        
        // Replace the temporary entry with the saved one
        setExtraPayments(extraPayments.map(p => 
          p.id === payment.id 
            ? { ...response.data, isEditing: false, isNew: false } 
            : p
        ));
        
        // After a short delay, refetch all data to ensure consistency
        setTimeout(() => {
          fetchExtraPayments();
        }, 500);
      } else {
        // Update existing payment
        const response = await api.put(
          `/extra-payments/${payment.id}?pi_number=${encodeURIComponent(piNumber)}`,
          paymentData
        );
        
        // Update the entry in view mode
        setExtraPayments(extraPayments.map(p => 
          p.id === payment.id 
            ? { ...response.data, isEditing: false, isNew: false } 
            : p
        ));
      }
      
      toast({
        title: 'Success',
        description: 'Extra payment saved successfully'
      });
      
      // Notify parent component
      if (onSave) {
        onSave();
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save extra payment',
        variant: 'destructive'
      });
    } finally {
      setSaving(false);
    }
  };
  
  const deletePayment = async (payment) => {
    if (!confirm('Are you sure you want to delete this extra payment?')) {
      return;
    }
    
    setSaving(true);
    
    try {
      if (payment.isNew) {
        // Just remove from local state if not saved yet
        setExtraPayments(extraPayments.filter(p => p.id !== payment.id));
      } else {
        // Delete from backend
        await api.delete(`/extra-payments/${payment.id}?pi_number=${encodeURIComponent(piNumber)}`);
        setExtraPayments(extraPayments.filter(p => p.id !== payment.id));
      }
      
      toast({
        title: 'Success',
        description: 'Extra payment deleted successfully'
      });
      
      // Notify parent component
      if (onSave) {
        onSave();
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete extra payment',
        variant: 'destructive'
      });
    } finally {
      setSaving(false);
    }
  };
  
  const enableEdit = (payment) => {
    setExtraPayments(extraPayments.map(p => 
      p.id === payment.id ? { ...p, isEditing: true } : p
    ));
  };
  
  const cancelEdit = (payment) => {
    if (payment.isNew) {
      // Remove unsaved new payment
      setExtraPayments(extraPayments.filter(p => p.id !== payment.id));
    } else {
      // Revert changes by refetching
      fetchExtraPayments();
    }
  };
  
  const getTotalAmount = () => {
    return extraPayments.reduce((sum, payment) => {
      return sum + (parseFloat(payment.amount) || 0);
    }, 0);
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Extra Payments</h3>
          <p className="text-sm text-slate-600">PI Number: {piNumber}</p>
        </div>
        <Button onClick={addNewRow} size="sm" className="flex items-center gap-2">
          <Plus size={16} />
          Add Row
        </Button>
      </div>
      
      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[150px]">Date</TableHead>
              <TableHead className="w-[200px]">Receipt</TableHead>
              <TableHead className="w-[250px]">Bank</TableHead>
              <TableHead className="w-[150px] text-right">Amount</TableHead>
              <TableHead className="w-[150px] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {extraPayments.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-slate-500 py-8">
                  No extra payments added yet. Click "Add Row" to add one.
                </TableCell>
              </TableRow>
            ) : (
              extraPayments.map((payment) => (
                <TableRow key={payment.id}>
                  <TableCell>
                    {payment.isEditing ? (
                      <Input
                        type="date"
                        value={payment.date}
                        onChange={(e) => handleFieldChange(payment.id, 'date', e.target.value)}
                        className="h-8"
                      />
                    ) : (
                      new Date(payment.date).toLocaleDateString()
                    )}
                  </TableCell>
                  <TableCell>
                    {payment.isEditing ? (
                      <Input
                        type="text"
                        value={payment.receipt}
                        onChange={(e) => handleFieldChange(payment.id, 'receipt', e.target.value)}
                        placeholder="Optional"
                        className="h-8"
                      />
                    ) : (
                      payment.receipt || '-'
                    )}
                  </TableCell>
                  <TableCell>
                    {payment.isEditing ? (
                      <Select
                        value={payment.bank_id}
                        onValueChange={(value) => {
                          setTimeout(() => handleFieldChange(payment.id, 'bank_id', value), 0);
                        }}
                      >
                        <SelectTrigger className="h-8">
                          <SelectValue placeholder={banks.length > 0 ? "Select Bank" : "No banks available"} />
                        </SelectTrigger>
                        <SelectContent {...getSafeSelectContentProps()}>
                          {banks.length === 0 ? (
                            <div className="px-2 py-4 text-sm text-slate-500 text-center">
                              No banks available. Please add banks in the Banks module.
                            </div>
                          ) : (
                            banks.map((bank) => (
                              <SelectItem key={bank.id} value={bank.id}>
                                {bank.bank_name}
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                    ) : (
                      payment.bank_name || '-'
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {payment.isEditing ? (
                      <Input
                        type="number"
                        value={payment.amount}
                        onChange={(e) => handleFieldChange(payment.id, 'amount', e.target.value)}
                        min="0"
                        step="0.01"
                        className="h-8 text-right"
                      />
                    ) : (
                      <span className="font-semibold">₹{parseFloat(payment.amount).toFixed(2)}</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      {payment.isEditing ? (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => savePayment(payment)}
                            disabled={saving}
                            title="Save"
                          >
                            <Save size={16} className="text-green-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => cancelEdit(payment)}
                            disabled={saving}
                            title="Cancel"
                          >
                            <X size={16} className="text-slate-600" />
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => enableEdit(payment)}
                            disabled={saving}
                            title="Edit"
                          >
                            <Edit size={16} className="text-blue-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => deletePayment(payment)}
                            disabled={saving}
                            title="Delete"
                          >
                            <Trash2 size={16} className="text-red-600" />
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      
      {/* Summary */}
      {extraPayments.length > 0 && (
        <div className="flex justify-end items-center gap-4 p-4 bg-slate-50 rounded-lg">
          <span className="text-sm font-medium text-slate-600">Total Extra Payments:</span>
          <span className="text-lg font-bold text-green-600">₹{getTotalAmount().toFixed(2)}</span>
        </div>
      )}
      
      {/* Footer */}
      <div className="flex justify-end gap-2 pt-4 border-t">
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </div>
    </div>
  );
};

export default ExtraPaymentPanel;
