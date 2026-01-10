import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { RefreshCw, Download, FileSpreadsheet, FileText, TrendingUp, X, Calendar } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useResizeObserverErrorFix } from '../hooks/useResizeObserverErrorFix';
import { getSafeSelectContentProps } from '../utils/selectHelpers';
import { jsPDF } from 'jspdf';
import 'jspdf-autotable';
import * as XLSX from 'xlsx';

const PLReporting = () => {
  const [exportInvoices, setExportInvoices] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [selectedInvoices, setSelectedInvoices] = useState([]);
  const [plReport, setPlReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);
  
  const [filters, setFilters] = useState({
    from_date: '',
    to_date: '',
    company_id: 'all',
    sku: ''
  });
  
  const { toast } = useToast();
  useResizeObserverErrorFix();
  
  useEffect(() => {
    fetchExportInvoices();
    fetchCompanies();
  }, []);
  
  const fetchExportInvoices = async (fromDate = '', toDate = '') => {
    setLoading(true);
    try {
      let url = '/pl-report/export-invoices';
      if (fromDate && toDate) {
        url += `?from_date=${fromDate}&to_date=${toDate}`;
      }
      const response = await api.get(url);
      setExportInvoices(response.data);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to fetch export invoices', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };
  
  const fetchCompanies = async () => {
    try {
      const response = await api.get('/companies');
      setCompanies(response.data);
    } catch (error) {
      console.error('Failed to fetch companies:', error);
    }
  };
  
  const handleInvoiceToggle = (invoiceId) => {
    setSelectedInvoices(prev => {
      if (prev.includes(invoiceId)) {
        return prev.filter(id => id !== invoiceId);
      } else {
        return [...prev, invoiceId];
      }
    });
  };
  
  const handleCalculatePL = async () => {
    if (selectedInvoices.length === 0) {
      toast({ title: 'Error', description: 'Please select at least one export invoice', variant: 'destructive' });
      return;
    }
    
    setLoadingReport(true);
    try {
      const response = await api.post('/pl-report/calculate', {
        export_invoice_ids: selectedInvoices,
        from_date: filters.from_date,
        to_date: filters.to_date,
        company_id: filters.company_id === 'all' ? '' : filters.company_id,
        sku: filters.sku
      });
      setPlReport(response.data);
      toast({ title: 'Success', description: 'P&L Report generated successfully' });
    } catch (error) {
      toast({ 
        title: 'Error', 
        description: error.response?.data?.detail || 'Failed to generate P&L report', 
        variant: 'destructive' 
      });
    } finally {
      setLoadingReport(false);
    }
  };
  
  const handleDownloadPDF = () => {
    if (!plReport) return;
    
    try {
      const doc = new jsPDF();
      
      // Title
      doc.setFontSize(18);
      doc.setFont('helvetica', 'bold');
      doc.text('PROFIT & LOSS REPORT', 105, 20, { align: 'center' });
      
      // Date
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      doc.text(`Generated on: ${new Date().toLocaleDateString()}`, 105, 28, { align: 'center' });
      
      // Summary Section
      let yPos = 40;
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('SUMMARY', 15, yPos);
      
      yPos += 10;
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      
      const summary = [
        ['Export Invoice Value', `Rs ${plReport.summary.total_export_value.toFixed(2)}`],
        ['Purchase Order Cost', `Rs ${plReport.summary.total_purchase_cost.toFixed(2)}`],
        ['Total Expenses', `Rs ${plReport.summary.total_expenses.toFixed(2)}`],
        ['Gross Total', `Rs ${plReport.summary.gross_total.toFixed(2)}`],
        ['GST (18%)', `Rs ${plReport.summary.gst_amount.toFixed(2)}`],
        ['Net Profit', `Rs ${plReport.summary.net_profit.toFixed(2)}`],
        ['Net Profit %', `${plReport.summary.net_profit_percentage.toFixed(2)}%`]
      ];
      
      doc.autoTable({
        startY: yPos,
        head: [['Description', 'Amount']],
        body: summary,
        theme: 'striped',
        headStyles: { fillColor: [59, 130, 246] },
        styles: { fontSize: 10 },
        columnStyles: {
          1: { halign: 'right', fontStyle: 'bold' }
        }
      });
      
      // Item Breakdown
      yPos = doc.lastAutoTable.finalY + 15;
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('ITEM-WISE BREAKDOWN', 15, yPos);
      
      yPos += 5;
      const itemData = plReport.item_breakdown.map(item => [
        item.export_invoice_no,
        item.sku,
        item.product_name,
        item.export_qty,
        `Rs ${item.export_rate.toFixed(2)}`,
        `Rs ${item.export_value.toFixed(2)}`,
        `Rs ${item.purchase_cost.toFixed(2)}`,
        `Rs ${item.item_gross.toFixed(2)}`
      ]);
      
      doc.autoTable({
        startY: yPos,
        head: [['Invoice No', 'SKU', 'Product', 'Qty', 'Rate', 'Export Value', 'Purchase Cost', 'Gross']],
        body: itemData,
        theme: 'grid',
        headStyles: { fillColor: [34, 197, 94] },
        styles: { fontSize: 8 },
        columnStyles: {
          3: { halign: 'right' },
          4: { halign: 'right' },
          5: { halign: 'right' },
          6: { halign: 'right' },
          7: { halign: 'right' }
        }
      });
      
      doc.save(`PL_Report_${new Date().toISOString().split('T')[0]}.pdf`);
      toast({ title: 'Success', description: 'PDF downloaded successfully' });
    } catch (error) {
      console.error('PDF generation error:', error);
      toast({ title: 'Error', description: 'Failed to generate PDF', variant: 'destructive' });
    }
  };
  
  const handleDownloadExcel = () => {
    if (!plReport) return;
    
    try {
      // Summary worksheet
      const summaryData = [
        ['PROFIT & LOSS REPORT'],
        [`Generated on: ${new Date().toLocaleDateString()}`],
        [],
        ['SUMMARY'],
        ['Description', 'Amount'],
        ['Export Invoice Value', plReport.summary.total_export_value.toFixed(2)],
        ['Purchase Order Cost', plReport.summary.total_purchase_cost.toFixed(2)],
        ['Total Expenses', plReport.summary.total_expenses.toFixed(2)],
        ['Gross Total', plReport.summary.gross_total.toFixed(2)],
        ['GST (18%)', plReport.summary.gst_amount.toFixed(2)],
        ['Net Profit', plReport.summary.net_profit.toFixed(2)],
        ['Net Profit %', plReport.summary.net_profit_percentage.toFixed(2) + '%']
      ];
      
      // Item breakdown worksheet
      const breakdownData = [
        ['ITEM-WISE BREAKDOWN'],
        [],
        ['Invoice No', 'SKU', 'Product', 'Quantity', 'Rate', 'Export Value', 'Purchase Cost', 'Gross']
      ];
      
      plReport.item_breakdown.forEach(item => {
        breakdownData.push([
          item.export_invoice_no,
          item.sku,
          item.product_name,
          item.export_qty,
          item.export_rate.toFixed(2),
          item.export_value.toFixed(2),
          item.purchase_cost.toFixed(2),
          item.item_gross.toFixed(2)
        ]);
      });
      
      // Create workbook
      const wb = XLSX.utils.book_new();
      const wsSummary = XLSX.utils.aoa_to_sheet(summaryData);
      const wsBreakdown = XLSX.utils.aoa_to_sheet(breakdownData);
      
      XLSX.utils.book_append_sheet(wb, wsSummary, 'Summary');
      XLSX.utils.book_append_sheet(wb, wsBreakdown, 'Item Breakdown');
      
      XLSX.writeFile(wb, `PL_Report_${new Date().toISOString().split('T')[0]}.xlsx`);
      toast({ title: 'Success', description: 'Excel downloaded successfully' });
    } catch (error) {
      console.error('Excel generation error:', error);
      toast({ title: 'Error', description: 'Failed to generate Excel', variant: 'destructive' });
    }
  };
  
  const handleApplyFilters = () => {
    if (filters.from_date && filters.to_date) {
      fetchExportInvoices(filters.from_date, filters.to_date);
    } else {
      fetchExportInvoices();
    }
  };
  
  const clearFilters = () => {
    setFilters({
      from_date: '',
      to_date: '',
      company_id: 'all',
      sku: ''
    });
    fetchExportInvoices();
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
          <h1 className="text-3xl font-bold text-slate-900">Profit & Loss Reporting</h1>
          <p className="text-slate-600 mt-1">Profitability analysis for export invoices</p>
        </div>
        <Button onClick={handleApplyFilters} variant="outline">
          <RefreshCw size={16} className="mr-2" />
          Refresh
        </Button>
      </div>
      
      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-4">
            <div>
              <Label className="text-xs">From Date</Label>
              <Input
                type="date"
                value={filters.from_date}
                onChange={(e) => setFilters(prev => ({ ...prev, from_date: e.target.value }))}
              />
            </div>
            <div>
              <Label className="text-xs">To Date</Label>
              <Input
                type="date"
                value={filters.to_date}
                onChange={(e) => setFilters(prev => ({ ...prev, to_date: e.target.value }))}
              />
            </div>
            <div>
              <Label className="text-xs">Company</Label>
              <Select
                value={filters.company_id}
                onValueChange={(value) => {
                  setTimeout(() => setFilters(prev => ({ ...prev, company_id: value })), 0);
                }}
              >
                <SelectTrigger className="h-9">
                  <SelectValue placeholder="All companies" />
                </SelectTrigger>
                <SelectContent {...getSafeSelectContentProps()}>
                  <SelectItem value="all">All Companies</SelectItem>
                  {companies.map(company => (
                    <SelectItem key={company.id} value={company.id}>{company.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">SKU</Label>
              <Input
                value={filters.sku}
                onChange={(e) => setFilters(prev => ({ ...prev, sku: e.target.value }))}
                placeholder="Filter by SKU"
                className="h-9"
              />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={handleApplyFilters} className="h-9">
                <Calendar size={16} className="mr-2" />
                Apply
              </Button>
              <Button onClick={clearFilters} variant="outline" className="h-9">
                Clear
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Export Invoice Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select Export Invoices ({selectedInvoices.length} selected)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3 max-h-[400px] overflow-y-auto p-2">
            {exportInvoices.map(invoice => {
              const isSelected = selectedInvoices.includes(invoice.id);
              return (
                <div
                  key={invoice.id}
                  onClick={() => handleInvoiceToggle(invoice.id)}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${
                    isSelected 
                      ? 'bg-blue-50 border-blue-500 shadow-md' 
                      : 'bg-white border-slate-200 hover:border-blue-300 hover:shadow'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-semibold text-lg">{invoice.export_invoice_no}</div>
                      {invoice.export_invoice_number && (
                        <div className="text-sm text-blue-600 font-medium">Invoice #: {invoice.export_invoice_number}</div>
                      )}
                      <div className="text-sm text-slate-600">{new Date(invoice.date).toLocaleDateString()}</div>
                      <div className="text-xs text-slate-500 mt-1">{invoice.dispatch_type}</div>
                      <div className="font-semibold text-green-700 mt-2">₹{invoice.total_value?.toFixed(2)}</div>
                    </div>
                    {isSelected && (
                      <Badge className="bg-blue-500">✓</Badge>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          
          {selectedInvoices.length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <div className="flex items-center justify-between">
                <div className="flex flex-wrap gap-2">
                  {selectedInvoices.map(id => {
                    const invoice = exportInvoices.find(inv => inv.id === id);
                    return invoice ? (
                      <Badge key={id} variant="outline" className="flex items-center gap-1">
                        {invoice.export_invoice_no}
                        <X 
                          size={14} 
                          className="cursor-pointer hover:text-red-600" 
                          onClick={(e) => {
                            e.stopPropagation();
                            handleInvoiceToggle(id);
                          }}
                        />
                      </Badge>
                    ) : null;
                  })}
                </div>
                <Button onClick={handleCalculatePL} disabled={loadingReport}>
                  {loadingReport ? (
                    <>
                      <RefreshCw size={16} className="mr-2 animate-spin" />
                      Calculating...
                    </>
                  ) : (
                    <>
                      <TrendingUp size={16} className="mr-2" />
                      Generate P&L Report
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* P&L Report Results */}
      {plReport && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-slate-600">Export Value</div>
                <div className="text-2xl font-bold text-blue-600">₹{plReport.summary.total_export_value.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-slate-600">Purchase Cost</div>
                <div className="text-2xl font-bold text-orange-600">₹{plReport.summary.total_purchase_cost.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-slate-600">Total Expenses</div>
                <div className="text-2xl font-bold text-red-600">₹{plReport.summary.total_expenses.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-slate-600">Gross Total</div>
                <div className="text-2xl font-bold text-green-600">₹{plReport.summary.gross_total.toFixed(2)}</div>
              </CardContent>
            </Card>
          </div>
          
          {/* Net Profit Section */}
          <Card className="bg-gradient-to-r from-green-50 to-blue-50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-slate-600">GST (18%)</div>
                  <div className="text-lg font-semibold text-slate-700">₹{plReport.summary.gst_amount.toFixed(2)}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-slate-600">Net Profit</div>
                  <div className="text-4xl font-bold text-green-700">₹{plReport.summary.net_profit.toFixed(2)}</div>
                  <div className="text-sm text-green-600 font-semibold mt-1">
                    {plReport.summary.net_profit_percentage.toFixed(2)}% margin
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleDownloadPDF} variant="outline">
                    <FileText size={16} className="mr-2" />
                    Download PDF
                  </Button>
                  <Button onClick={handleDownloadExcel} variant="outline">
                    <FileSpreadsheet size={16} className="mr-2" />
                    Download Excel
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
          
          {/* Item Breakdown Table */}
          <Card>
            <CardHeader>
              <CardTitle>Item-wise Breakdown ({plReport.item_breakdown.length} items)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Export Invoice</TableHead>
                      <TableHead>SKU</TableHead>
                      <TableHead>Product</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Export Rate</TableHead>
                      <TableHead className="text-right">Export Value</TableHead>
                      <TableHead className="text-right">Purchase Cost</TableHead>
                      <TableHead className="text-right">Item Gross</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {plReport.item_breakdown.map((item, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-medium">
                          <div>{item.export_invoice_no}</div>
                          {item.export_invoice_number && (
                            <div className="text-xs text-blue-600">({item.export_invoice_number})</div>
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-sm">{item.sku}</TableCell>
                        <TableCell>{item.product_name}</TableCell>
                        <TableCell className="text-right">{item.export_qty}</TableCell>
                        <TableCell className="text-right">₹{item.export_rate.toFixed(2)}</TableCell>
                        <TableCell className="text-right font-semibold text-blue-600">₹{item.export_value.toFixed(2)}</TableCell>
                        <TableCell className="text-right text-orange-600">₹{item.purchase_cost.toFixed(2)}</TableCell>
                        <TableCell className="text-right font-bold text-green-600">₹{item.item_gross.toFixed(2)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};

export default PLReporting;
