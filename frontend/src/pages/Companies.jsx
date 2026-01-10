import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import Layout from '../components/Layout';
import DataTable from '../components/DataTable';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Plus } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';

const Companies = () => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    gstn: '',
    apob: '',
    address: '',
    contact_details: '',
    country: '',
    city: '',
  });
  const { toast } = useToast();
  
  // Use custom hook to suppress ResizeObserver errors
  useResizeObserverErrorFix();

  useEffect(() => {
    fetchCompanies();
  }, []);

  const fetchCompanies = async () => {
    try {
      const response = await api.get('/companies');
      console.log(response.data);
      setCompanies(response.data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch companies',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingCompany) {
        await api.put(`/companies/${editingCompany.id}`, formData);
        toast({ title: 'Success', description: 'Company updated successfully' });
      } else {
        await api.post('/companies', formData);
        toast({ title: 'Success', description: 'Company created successfully' });
      }
      fetchCompanies();
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

  const handleEdit = (company) => {
    setEditingCompany(company);
    setFormData({
      name: company.name,
      gstn: company.gstn || '',
      apob: company.apob || '',
      address: company.address || '',
      contact_details: company.contact_details || '',
      country: company.country || '',
      city: company.city || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = async (company) => {
    if (window.confirm('Are you sure you want to delete this company?')) {
      try {
        await api.delete(`/companies/${company.id}`);
        toast({ title: 'Success', description: 'Company deleted successfully' });
        fetchCompanies();
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Failed to delete company',
          variant: 'destructive',
        });
      }
    }
  };

  const handleBulkUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/companies/bulk', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      toast({
        title: 'Success',
        description: response.data.message,
      });
      fetchCompanies();
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Bulk upload failed',
        variant: 'destructive',
      });
    }
    e.target.value = '';
  };

  const resetForm = () => {
    setFormData({
      name: '',
      gstn: '',
      apob: '',
      address: '',
      contact_details: '',
      country: '',
      city: '',
    });
    setEditingCompany(null);
  };

  const columns = [
    { header: 'Name', accessor: 'name' },
    { header: 'GSTN', accessor: 'gstn' },
    { header: 'City', accessor: 'city' },
    { header: 'Country', accessor: 'country' },
    { header: 'Contact', accessor: 'contact_details' },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="companies-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Companies</h1>
          <p className="text-slate-600 mt-1">Manage your company master data</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => window.open(`${window.location.origin}/api/templates/companies`, '_blank')}
            data-testid="download-template-btn"
            className="border-emerald-600 text-emerald-600 hover:bg-emerald-50"
          >
            Download Template
          </Button>
          <input
            type="file"
            id="bulk-upload"
            accept=".xlsx,.xls,.csv"
            onChange={handleBulkUpload}
            className="hidden"
            data-testid="bulk-upload-input"
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById('bulk-upload').click()}
            data-testid="bulk-upload-btn"
          >
            <Plus size={20} className="mr-2" />
            Bulk Upload (Excel)
          </Button>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button
                className="bg-blue-600 hover:bg-blue-700 text-white"
                onClick={resetForm}
                data-testid="add-company-btn"
              >
                <Plus size={20} className="mr-2" />
                Add Company
              </Button>
            </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingCompany ? 'Edit Company' : 'Add New Company'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Company Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    data-testid="company-name-input"
                  />
                </div>
                <div>
                  <Label htmlFor="gstn">GSTN</Label>
                  <Input
                    id="gstn"
                    value={formData.gstn}
                    onChange={(e) => setFormData({ ...formData, gstn: e.target.value })}
                    data-testid="company-gstn-input"
                  />
                </div>
                <div>
                  <Label htmlFor="apob">APOB</Label>
                  <Input
                    id="apob"
                    value={formData.apob}
                    onChange={(e) => setFormData({ ...formData, apob: e.target.value })}
                    data-testid="company-apob-input"
                  />
                </div>
                <div>
                  <Label htmlFor="city">City</Label>
                  <Input
                    id="city"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    data-testid="company-city-input"
                  />
                </div>
                <div>
                  <Label htmlFor="country">Country</Label>
                  <Input
                    id="country"
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                    data-testid="company-country-input"
                  />
                </div>
                <div>
                  <Label htmlFor="contact_details">Contact Details</Label>
                  <Input
                    id="contact_details"
                    value={formData.contact_details}
                    onChange={(e) => setFormData({ ...formData, contact_details: e.target.value })}
                    data-testid="company-contact-input"
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="address">Address</Label>
                <Textarea
                  id="address"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  rows={3}
                  data-testid="company-address-input"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" className="bg-blue-600 hover:bg-blue-700" data-testid="save-company-btn">
                  {editingCompany ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
        </div>
      </div>

      <DataTable columns={columns} data={companies} onEdit={handleEdit} onDelete={handleDelete} />
    </div>
  );
};

export default Companies;
