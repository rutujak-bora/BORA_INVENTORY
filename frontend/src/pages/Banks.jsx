import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import DataTable from '../components/DataTable';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Plus } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';

const Banks = () => {
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBank, setEditingBank] = useState(null);
  const [formData, setFormData] = useState({
    bank_name: '',
    ifsc_code: '',
    ad_code: '',
    address: '',
    account_number: '',
  });
  const { toast } = useToast();
  
  // Use custom hook to suppress ResizeObserver errors
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchBanks();
  }, []);

  const fetchBanks = async () => {
    try {
      const response = await api.get('/banks');
      setBanks(response.data);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch banks', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingBank) {
        await api.put(`/banks/${editingBank.id}`, formData);
        toast({ title: 'Success', description: 'Bank updated successfully' });
      } else {
        await api.post('/banks', formData);
        toast({ title: 'Success', description: 'Bank created successfully' });
      }
      fetchBanks();
      setDialogOpen(false);
      resetForm();
    } catch (error) {
      toast({ title: 'Error', description: error.response?.data?.detail || 'Operation failed', variant: 'destructive' });
    }
  };

  const handleEdit = (bank) => {
    setEditingBank(bank);
    setFormData({
      bank_name: bank.bank_name,
      ifsc_code: bank.ifsc_code || '',
      ad_code: bank.ad_code || '',
      address: bank.address || '',
      account_number: bank.account_number || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = async (bank) => {
    if (window.confirm('Are you sure you want to delete this bank?')) {
      try {
        await api.delete(`/banks/${bank.id}`);
        toast({ title: 'Success', description: 'Bank deleted successfully' });
        fetchBanks();
      } catch (error) {
        toast({ title: 'Error', description: 'Failed to delete bank', variant: 'destructive' });
      }
    }
  };

  const resetForm = () => {
    setFormData({
      bank_name: '',
      ifsc_code: '',
      ad_code: '',
      address: '',
      account_number: '',
    });
    setEditingBank(null);
  };

  const columns = [
    { header: 'Bank Name', accessor: 'bank_name' },
    { header: 'IFSC Code', accessor: 'ifsc_code' },
    { header: 'AD Code', accessor: 'ad_code' },
    { header: 'Account Number', accessor: 'account_number' },
    { header: 'Address', accessor: 'address' },
  ];

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Bank Master</h1>
          <p className="text-gray-600">Manage bank details</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => resetForm()}>
              <Plus className="mr-2 h-4 w-4" /> Add Bank
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingBank ? 'Edit Bank' : 'Add New Bank'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="bank_name">Bank Name *</Label>
                  <Input
                    id="bank_name"
                    value={formData.bank_name}
                    onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                    required
                    placeholder="Enter bank name"
                  />
                </div>
                <div>
                  <Label htmlFor="ifsc_code">IFSC Code</Label>
                  <Input
                    id="ifsc_code"
                    value={formData.ifsc_code}
                    onChange={(e) => setFormData({ ...formData, ifsc_code: e.target.value })}
                    placeholder="Enter IFSC code"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="ad_code">AD Code</Label>
                  <Input
                    id="ad_code"
                    value={formData.ad_code}
                    onChange={(e) => setFormData({ ...formData, ad_code: e.target.value })}
                    placeholder="Enter AD code"
                  />
                </div>
                <div>
                  <Label htmlFor="account_number">Account Number</Label>
                  <Input
                    id="account_number"
                    value={formData.account_number}
                    onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                    placeholder="Enter account number"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="address">Address</Label>
                <Textarea
                  id="address"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="Enter bank address"
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit">
                  {editingBank ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <DataTable
        data={banks}
        columns={columns}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />
    </div>
  );
};

export default Banks;
