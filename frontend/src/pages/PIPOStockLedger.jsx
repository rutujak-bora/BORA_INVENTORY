import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { formatCurrency, formatNumber } from '../utils/formatters';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Badge } from '../components/ui/badge';
import { FileText, ShoppingCart, TrendingDown, TrendingUp, Package, Filter, Download, RefreshCw, ArrowRightLeft } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import * as XLSX from 'xlsx';

const PIPOStockLedger = () => {
  const [ledgerData, setLedgerData] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [pis, setPis] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    company_id: 'all',
    pi_id: 'all',
    sku: ''
  });
  const { toast } = useToast();

  useEffect(() => {
    fetchInitialData();
  }, []);

  useEffect(() => {
    fetchLedger();
  }, [filters.company_id, filters.pi_id]);

  const fetchInitialData = async () => {
    try {
      const [companiesRes, pisRes] = await Promise.all([
        api.get('/companies'),
        api.get('/pi')
      ]);
      setCompanies(companiesRes.data || []);
      setPis(pisRes.data || []);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch filter data', variant: 'destructive' });
    }
  };

  const fetchLedger = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.company_id !== 'all') params.append('company_id', filters.company_id);
      if (filters.pi_id !== 'all') params.append('pi_id', filters.pi_id);
      
      const response = await api.get(`/pi-po-stock-ledger?${params.toString()}`);
      setLedgerData(response.data || []);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch ledger data', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const filteredData = ledgerData.filter(item => 
    !filters.sku || item.sku.toLowerCase().includes(filters.sku.toLowerCase()) || 
    item.product_name.toLowerCase().includes(filters.sku.toLowerCase())
  );

  const stats = filteredData.reduce((acc, item) => ({
    totalPI: acc.totalPI + item.pi_quantity,
    totalPO: acc.totalPO + item.po_quantity,
    totalStock: acc.totalStock + item.warehouse_stock,
    totalInward: acc.totalInward + item.inward_quantity,
    totalOutward: acc.totalOutward + item.outward_quantity,
  }), { totalPI: 0, totalPO: 0, totalStock: 0, totalInward: 0, totalOutward: 0 });

  const exportToExcel = () => {
    const exportData = filteredData.map(item => ({
      'PI Number': item.pi_voucher_no,
      'Buyer': item.buyer,
      'Product': item.product_name,
      'SKU': item.sku,
      'PI Qty': item.pi_quantity,
      'PO Qty': item.po_quantity,
      'PI Balance': item.pi_balance,
      'Inward Qty': item.inward_quantity,
      'Outward Qty': item.outward_quantity,
      'WH Stock': item.warehouse_stock,
      'Linked POs': item.po_numbers.join(', ')
    }));

    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Stock Ledger');
    XLSX.writeFile(wb, `PI_PO_Stock_Ledger_${new Date().toISOString().split('T')[0]}.xlsx`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <ArrowRightLeft className="text-blue-600" size={32} />
            Document Stock Ledger
          </h1>
          <p className="text-slate-600 mt-1">Full lifecycle tracking: PI → PO → Inward → Outward</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={exportToExcel} variant="outline" className="flex items-center gap-2">
            <Download size={16} />
            Export Excel
          </Button>
          <Button onClick={fetchLedger} variant="outline" className="flex items-center gap-2">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card className="bg-blue-50 border-blue-100">
          <CardHeader className="pb-2 text-center">
            <CardDescription className="text-xs font-semibold text-blue-700">TOTAL PI UNITS</CardDescription>
            <CardTitle className="text-2xl text-blue-900">{formatNumber(stats.totalPI)}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="bg-indigo-50 border-indigo-100">
          <CardHeader className="pb-2 text-center">
            <CardDescription className="text-xs font-semibold text-indigo-700">LINKED PO UNITS</CardDescription>
            <CardTitle className="text-2xl text-indigo-900">{formatNumber(stats.totalPO)}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="bg-green-50 border-green-100">
          <CardHeader className="pb-2 text-center">
            <CardDescription className="text-xs font-semibold text-green-700">STOCK INWARD</CardDescription>
            <CardTitle className="text-2xl text-green-900">{formatNumber(stats.totalInward)}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="bg-orange-50 border-orange-100">
          <CardHeader className="pb-2 text-center">
            <CardDescription className="text-xs font-semibold text-orange-700">STOCK OUTWARD</CardDescription>
            <CardTitle className="text-2xl text-orange-900">{formatNumber(stats.totalOutward)}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="bg-purple-50 border-purple-100 shadow-sm border-2">
          <CardHeader className="pb-2 text-center">
            <CardDescription className="text-xs font-semibold text-purple-700">CURRENT WH STOCK</CardDescription>
            <CardTitle className="text-2xl text-purple-900">{formatNumber(stats.totalStock)}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium">Company</Label>
              <Select value={filters.company_id} onValueChange={(v) => handleFilterChange('company_id', v)}>
                <SelectTrigger>
                  <SelectValue placeholder="All Companies" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Companies</SelectItem>
                  {companies.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">PI Number</Label>
              <Select value={filters.pi_id} onValueChange={(v) => handleFilterChange('pi_id', v)}>
                <SelectTrigger>
                  <SelectValue placeholder="All PIs" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All PIs</SelectItem>
                  {pis.filter(p => filters.company_id === 'all' || p.company_id === filters.company_id).map(p => (
                    <SelectItem key={p.id} value={p.id}>{p.voucher_no}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">Product / SKU Search</Label>
              <div className="relative">
                <Input 
                  placeholder="Search by SKU or Name..." 
                  value={filters.sku} 
                  onChange={(e) => handleFilterChange('sku', e.target.value)}
                />
              </div>
            </div>
            <div className="flex items-end">
              <Button onClick={() => setFilters({company_id: 'all', pi_id: 'all', sku: ''})} variant="ghost" className="text-xs text-slate-500 underline">
                Clear all filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Ledger Table */}
      <Card>
        <CardHeader className="border-b bg-slate-50 py-4 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">Document Transactions & Balances</CardTitle>
            <CardDescription>Real-time linkage and stock aging metrics</CardDescription>
          </div>
          <Badge variant="outline" className="bg-white">
            {filteredData.length} records found
          </Badge>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-100 hover:bg-slate-100">
                <TableHead className="font-bold border-r w-[20%]">Document Info</TableHead>
                <TableHead className="font-bold border-r w-[25%]">Product Details</TableHead>
                <TableHead className="text-right font-bold border-r bg-blue-50/50">PI (Target)</TableHead>
                <TableHead className="text-right font-bold border-r bg-indigo-50/50">PO (Ordered)</TableHead>
                <TableHead className="text-right font-bold border-r bg-green-50/50">Inward (WH)</TableHead>
                <TableHead className="text-right font-bold border-r bg-orange-50/50">Outward (Exp)</TableHead>
                <TableHead className="text-right font-bold bg-purple-50/50 text-purple-900 font-bold">WH Balance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="animate-spin text-blue-600" size={20} />
                      Loading document ledger...
                    </div>
                  </TableCell>
                </TableRow>
              ) : filteredData.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-slate-500">
                    No documents found matching the filters.
                  </TableCell>
                </TableRow>
              ) : (
                filteredData.map((item, idx) => (
                  <TableRow key={idx} className="hover:bg-slate-50 border-b">
                    {/* Document Info */}
                    <TableCell className="border-r py-3">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-1.5 font-bold text-blue-600">
                          <FileText size={14} />
                          {item.pi_voucher_no}
                        </div>
                        <div className="text-[11px] text-slate-500 font-medium">{item.buyer}</div>
                        <div className="text-[10px] text-slate-400">{new Date(item.date).toLocaleDateString()}</div>
                      </div>
                    </TableCell>

                    {/* Product Details */}
                    <TableCell className="border-r py-3">
                      <div className="flex flex-col gap-0.5">
                        <div className="text-sm font-semibold text-slate-900 leading-tight">{item.product_name}</div>
                        <div className="text-xs font-mono text-slate-500 flex items-center gap-1">
                          <Package size={12} /> {item.sku}
                        </div>
                        {item.po_numbers.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {item.po_numbers.map((po, i) => (
                              <span key={i} className="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[9px] font-bold border border-slate-200">
                                {po}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </TableCell>

                    {/* PI Target */}
                    <TableCell className="text-right border-r bg-blue-50/20">
                      <div className="font-bold text-blue-900">{formatNumber(item.pi_quantity)}</div>
                      <div className="text-[10px] text-blue-500 italic">Target Units</div>
                    </TableCell>

                    {/* PO Linkage */}
                    <TableCell className="text-right border-r bg-indigo-50/20">
                      <div className="font-bold text-indigo-900">{formatNumber(item.po_quantity)}</div>
                      <div className={`text-[10px] font-bold ${item.pi_balance > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                        {item.pi_balance > 0 ? `${formatNumber(item.pi_balance)} Left` : 'Fully Ordered'}
                      </div>
                    </TableCell>

                    {/* Inward */}
                    <TableCell className="text-right border-r bg-green-50/20">
                      <div className="font-bold text-green-700">{formatNumber(item.inward_quantity)}</div>
                      <div className="text-[10px] text-slate-400">Arrived</div>
                    </TableCell>

                    {/* Outward */}
                    <TableCell className="text-right border-r bg-orange-50/20">
                      <div className="font-bold text-orange-700">{formatNumber(item.outward_quantity)}</div>
                      <div className="text-[10px] text-slate-400">Shipped</div>
                    </TableCell>

                    {/* WH Balance */}
                    <TableCell className="text-right bg-purple-50/20">
                      <div className="text-lg font-black text-purple-900 leading-none">
                        {formatNumber(item.warehouse_stock)}
                      </div>
                      <Badge variant="outline" className={`mt-1 h-5 text-[9px] uppercase font-bold border-purple-200 ${item.warehouse_stock > 0 ? 'bg-purple-100 text-purple-800' : 'bg-slate-100 text-slate-400'}`}>
                        {item.warehouse_stock > 0 ? 'In Stock' : 'Empty'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default PIPOStockLedger;
