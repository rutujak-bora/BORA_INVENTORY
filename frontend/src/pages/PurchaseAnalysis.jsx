import React, { useState, useEffect } from 'react';
import api from '../utils/api';
import { formatNumber } from '../utils/formatters';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Filter, Download, TrendingUp, Package, RefreshCw } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import * as XLSX from 'xlsx';

const PurchaseAnalysis = () => {
  const [companies, setCompanies] = useState([]);
  const [pis, setPis] = useState([]);
  const [selectedCompanies, setSelectedCompanies] = useState([]);
  const [selectedPIs, setSelectedPIs] = useState([]);
  const [analysisData, setAnalysisData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filtersApplied, setFiltersApplied] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    fetchCompanies();
  }, []);

  useEffect(() => {
    if (selectedCompanies.length > 0) {
      fetchPIs();
    } else {
      setPis([]);
      setSelectedPIs([]);
    }
  }, [selectedCompanies]);

  const fetchCompanies = async () => {
    try {
      const response = await api.get('/companies');
      setCompanies(response.data || []);
    } catch (error) {
      console.error('Error fetching companies:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch companies',
        variant: 'destructive'
      });
    }
  };

  const fetchPIs = async () => {
    try {
      const response = await api.get('/pi');

      // Get names of selected companies to handle cases where pi.company_id is stored as a name string
      const selectedCompanyObjects = companies.filter(c => selectedCompanies.includes(c.id));
      const selectedCompanyNames = selectedCompanyObjects.map(c => c.name.toLowerCase());

      // Filter PIs by selected companies (match by ID or Name)
      const filteredPIs = response.data.filter(pi => {
        const piCompanyId = pi.company_id || "";
        return selectedCompanies.includes(piCompanyId) ||
          selectedCompanyNames.includes(piCompanyId.toLowerCase());
      });

      setPis(filteredPIs || []);
    } catch (error) {
      console.error('Error fetching PIs:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch PIs',
        variant: 'destructive'
      });
    }
  };

  const fetchAnalysisData = async () => {
    if (selectedCompanies.length === 0 || selectedPIs.length === 0) {
      toast({
        title: 'Warning',
        description: 'Please select both Company and PI Number',
        variant: 'destructive'
      });
      return;
    }

    setLoading(true);
    try {
      const companyIds = selectedCompanies.join(',');
      const piNumbers = selectedPIs.join(',');

      const response = await api.get(`/purchase-analysis?company_ids=${companyIds}&pi_numbers=${piNumbers}`);
      setAnalysisData(response.data.data || []);
      setFiltersApplied(true);

      toast({
        title: 'Success',
        description: `Loaded ${response.data.count || 0} records`,
        variant: 'default'
      });
    } catch (error) {
      console.error('Error fetching analysis data:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch purchase analysis data',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCompanyChange = (companyId) => {
    setSelectedCompanies(prev => {
      if (prev.includes(companyId)) {
        return prev.filter(id => id !== companyId);
      } else {
        return [...prev, companyId];
      }
    });
    setFiltersApplied(false);
  };

  const handlePIChange = (piNumber) => {
    setSelectedPIs(prev => {
      if (prev.includes(piNumber)) {
        return prev.filter(num => num !== piNumber);
      } else {
        return [...prev, piNumber];
      }
    });
    setFiltersApplied(false);
  };

  const resetFilters = () => {
    setSelectedCompanies([]);
    setSelectedPIs([]);
    setAnalysisData([]);
    setFiltersApplied(false);
  };

  const exportToExcel = () => {
    if (analysisData.length === 0) {
      toast({
        title: 'Warning',
        description: 'No data to export',
        variant: 'destructive'
      });
      return;
    }

    const exportData = analysisData.map(item => ({
      'Buyer': item.buyer,
      'Product Name': item.product_name,
      'SKU': item.sku,
      'PI Number': item.pi_number,
      'PI Quantity': item.pi_quantity,
      'PO Number': item.po_number,
      'PO Quantity': item.po_quantity,
      'In-Transit': item.intransit_quantity || 0,
      'Inward Quantity': item.inward_quantity,
      'Remaining': item.remaining_quantity
    }));

    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Purchase Analysis');
    XLSX.writeFile(wb, `Purchase_Analysis_${new Date().toISOString().split('T')[0]}.xlsx`);

    toast({
      title: 'Success',
      description: 'Data exported to Excel successfully',
      variant: 'default'
    });
  };

  // Calculate totals
  const totals = analysisData.reduce(
    (acc, item) => ({
      piQty: acc.piQty + item.pi_quantity,
      poQty: acc.poQty + item.po_quantity,
      inwardQty: acc.inwardQty + item.inward_quantity,
      intransitQty: acc.intransitQty + item.intransit_quantity,
      remainingQty: acc.remainingQty + item.remaining_quantity
    }),
    { piQty: 0, poQty: 0, inwardQty: 0, intransitQty: 0, remainingQty: 0 }
  );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <TrendingUp className="text-blue-600" size={32} />
            Purchase Analysis
          </h1>
          <p className="text-slate-600 mt-1">Comprehensive analysis of purchase cycle from PI to PO to Inward</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={exportToExcel}
            variant="outline"
            className="flex items-center gap-2"
            disabled={analysisData.length === 0}
          >
            <Download size={16} />
            Export to Excel
          </Button>
          <Button
            onClick={resetFilters}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RefreshCw size={16} />
            Reset
          </Button>
        </div>
      </div>

      {/* Filters Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter size={20} />
            Filters (Select Company & PI to load data)
          </CardTitle>
          <CardDescription>
            Select one or more companies and their PIs to analyze purchase data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Company Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Company Name <span className="text-red-500">*</span>
              </label>
              <div className="border rounded-lg p-3 max-h-48 overflow-y-auto bg-gray-50">
                {companies.length === 0 ? (
                  <p className="text-sm text-gray-500">No companies available</p>
                ) : (
                  companies.map(company => (
                    <label key={company.id} className="flex items-center gap-2 py-1 hover:bg-gray-100 px-2 rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedCompanies.includes(company.id)}
                        onChange={() => handleCompanyChange(company.id)}
                        className="w-4 h-4 text-blue-600"
                      />
                      <span className="text-sm">{company.name}</span>
                    </label>
                  ))
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Selected: {selectedCompanies.length} companies
              </p>
            </div>

            {/* PI Number Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                PI Number <span className="text-red-500">*</span>
              </label>
              <div className="border rounded-lg p-3 max-h-48 overflow-y-auto bg-gray-50">
                {selectedCompanies.length === 0 ? (
                  <p className="text-sm text-gray-500">Please select company first</p>
                ) : pis.length === 0 ? (
                  <p className="text-sm text-gray-500">No PIs found for selected companies</p>
                ) : (
                  pis.map(pi => (
                    <label key={pi.id} className="flex items-center gap-2 py-1 hover:bg-gray-100 px-2 rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedPIs.includes(pi.voucher_no)}
                        onChange={() => handlePIChange(pi.voucher_no)}
                        className="w-4 h-4 text-blue-600"
                      />
                      <span className="text-sm">{pi.voucher_no}</span>
                    </label>
                  ))
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Selected: {selectedPIs.length} PIs
              </p>
            </div>
          </div>

          {/* Apply Filters Button */}
          <div className="mt-4">
            <Button
              onClick={fetchAnalysisData}
              className="w-full md:w-auto"
              disabled={selectedCompanies.length === 0 || selectedPIs.length === 0 || loading}
            >
              {loading ? 'Loading...' : 'Apply Filters & Load Data'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Data Table */}
      {filtersApplied && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package size={20} />
              Purchase Analysis Results
            </CardTitle>
            <CardDescription>
              Showing {analysisData.length} records for selected filters
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-100">
                    <TableHead className="font-bold">Buyer</TableHead>
                    <TableHead className="font-bold">Product Name</TableHead>
                    <TableHead className="font-bold">SKU</TableHead>
                    <TableHead className="font-bold">PI Number</TableHead>
                    <TableHead className="text-right font-bold">PI Quantity</TableHead>
                    <TableHead className="font-bold">PO Number</TableHead>
                    <TableHead className="text-right font-bold">PO Quantity</TableHead>
                    <TableHead className="text-right font-bold">In-transit</TableHead>
                    <TableHead className="text-right font-bold">Inward Quantity</TableHead>
                    <TableHead className="text-right font-bold">Remaining</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {analysisData.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan="10" className="text-center py-8 text-gray-500">
                        No data found for selected filters
                      </TableCell>
                    </TableRow>
                  ) : (
                    <>
                      {analysisData.map((item, index) => (
                        <TableRow key={index} className="hover:bg-gray-50">
                          <TableCell className="font-medium">{item.buyer}</TableCell>
                          <TableCell>{item.product_name}</TableCell>
                          <TableCell className="font-mono text-sm">{item.sku}</TableCell>
                          <TableCell className="font-medium text-blue-600">{item.pi_number}</TableCell>
                          <TableCell className="text-right font-semibold">{formatNumber(item.pi_quantity)}</TableCell>
                          <TableCell className="font-medium text-green-600">{item.po_number}</TableCell>
                          <TableCell className="text-right font-semibold">{formatNumber(item.po_quantity)}</TableCell>
                          <TableCell className="text-right font-semibold text-purple-600">{formatNumber(item.intransit_quantity || 0)}</TableCell>
                          <TableCell className="text-right font-semibold text-green-600">{formatNumber(item.inward_quantity)}</TableCell>
                          <TableCell className={`text-right font-bold ${item.remaining_quantity > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                            {formatNumber(item.remaining_quantity)}
                          </TableCell>
                        </TableRow>
                      ))}
                      {/* Totals Row */}
                      <TableRow className="bg-blue-50 font-bold border-t-2 border-blue-300">
                        <TableCell colSpan="4" className="text-right">TOTALS:</TableCell>
                        <TableCell className="text-right">{formatNumber(totals.piQty)}</TableCell>
                        <TableCell></TableCell>
                        <TableCell className="text-right">{formatNumber(totals.poQty)}</TableCell>
                        <TableCell className="text-right text-purple-600">{formatNumber(totals.intransitQty)}</TableCell>
                        <TableCell className="text-right text-green-600">{formatNumber(totals.inwardQty)}</TableCell>
                        <TableCell className={`text-right ${totals.remainingQty > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                          {formatNumber(totals.remainingQty)}
                        </TableCell>
                      </TableRow>
                    </>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PurchaseAnalysis;
