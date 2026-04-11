import React, { useState, useEffect } from 'react';
import api from '../utils/api';
import { formatCurrency, formatNumber } from '../utils/formatters';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Info, TrendingUp, TrendingDown, Minus, ArrowRightLeft, FileText, ShoppingCart } from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const PriceComparison = () => {
    const [invoiceType, setInvoiceType] = useState('pi'); // 'pi' or 'po'
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(false);
    
    const [newInvoiceId, setNewInvoiceId] = useState('');
    const [oldInvoiceId, setOldInvoiceId] = useState('');
    
    // Filtering states
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('all');
    
    const [newInvoiceData, setNewInvoiceData] = useState(null);
    const [oldInvoiceData, setOldInvoiceData] = useState(null);
    
    const { toast } = useToast();

    useEffect(() => {
        fetchInvoices();
        resetComparison();
    }, [invoiceType]);

    const fetchInvoices = async () => {
        setLoading(true);
        try {
            const endpoint = invoiceType === 'pi' ? '/pi' : '/po';
            const response = await api.get(endpoint);
            setInvoices(response.data.sort((a, b) => new Date(b.date) - new Date(a.date)));
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to fetch invoices',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    const resetComparison = () => {
        setNewInvoiceId('');
        setOldInvoiceId('');
        setStartDate('');
        setEndDate('');
        setCategoryFilter('all');
        setNewInvoiceData(null);
        setOldInvoiceData(null);
    };

    const fetchInvoiceDetails = async (id, side) => {
        if (!id) return;
        try {
            const endpoint = invoiceType === 'pi' ? `/pi/${id}` : `/po/${id}`;
            const response = await api.get(endpoint);
            if (side === 'new') {
                setNewInvoiceData(response.data);
            } else {
                setOldInvoiceData(response.data);
            }
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to fetch invoice details',
                variant: 'destructive',
            });
        }
    };

    useEffect(() => {
        if (newInvoiceId) fetchInvoiceDetails(newInvoiceId, 'new');
    }, [newInvoiceId]);

    useEffect(() => {
        if (oldInvoiceId) fetchInvoiceDetails(oldInvoiceId, 'old');
    }, [oldInvoiceId]);

    // Available categories extracted from current loaded data
    const categories = Array.from(new Set([
        ...(newInvoiceData?.line_items?.map(item => item.category) || []),
        ...(oldInvoiceData?.line_items?.map(item => item.category) || [])
    ])).filter(Boolean).sort();

    // Filtered Invoices based on date range
    const filteredInvoices = invoices.filter(inv => {
        if (!startDate && !endDate) return true;
        const invDate = new Date(inv.date);
        const start = startDate ? new Date(startDate) : null;
        const end = endDate ? new Date(endDate) : null;
        
        if (start && invDate < start) return false;
        if (end && invDate > end) return false;
        return true;
    });

    const getComparisonData = () => {
        const productMap = new Map();

        // Process New Invoice
        newInvoiceData?.line_items?.forEach(item => {
            if (categoryFilter !== 'all' && item.category !== categoryFilter) return;
            
            const sku = item.sku || item.product_id;
            productMap.set(sku, {
                sku: sku,
                product_name: item.product_name,
                category: item.category,
                newPrice: item.rate,
                oldPrice: null
            });
        });

        // Process Old Invoice
        oldInvoiceData?.line_items?.forEach(item => {
            if (categoryFilter !== 'all' && item.category !== categoryFilter) return;
            
            const sku = item.sku || item.product_id;
            if (productMap.has(sku)) {
                const existing = productMap.get(sku);
                existing.oldPrice = item.rate;
            } else {
                productMap.set(sku, {
                    sku: sku,
                    product_name: item.product_name,
                    category: item.category,
                    newPrice: null,
                    oldPrice: item.rate
                });
            }
        });

        return Array.from(productMap.values()).sort((a, b) => a.product_name.localeCompare(b.product_name));
    };

    const comparisonData = getComparisonData();

    const getPriceDiff = (newP, oldP) => {
        if (newP === null || oldP === null) return null;
        const diff = newP - oldP;
        const percent = (diff / oldP) * 100;
        return { diff, percent };
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900">Price Comparison</h1>
                    <p className="text-slate-600 mt-1">Compare product rates between different Vouchers</p>
                </div>
            </div>

            <Card>
                <CardContent className="pt-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6 pb-6 border-b border-slate-100">
                        {/* Date Range Filter */}
                        <div className="space-y-2">
                            <Label className="text-sm font-semibold">Start Date</Label>
                            <Input 
                                type="date" 
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-semibold">End Date</Label>
                            <Input 
                                type="date" 
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                            />
                        </div>

                        {/* Category Filter */}
                        <div className="space-y-2">
                            <Label className="text-sm font-semibold">Product Category</Label>
                            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                                <SelectTrigger>
                                    <SelectValue placeholder="All Categories" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Categories</SelectItem>
                                    {categories.map(cat => (
                                        <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Actions */}
                        <div className="flex items-end pb-0.5">
                            <Button variant="ghost" className="text-slate-500 text-xs" onClick={resetComparison}>
                                Reset Filters
                            </Button>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Type Selection */}
                        <div className="space-y-2">
                            <Label className="text-sm font-semibold">Select Document Type</Label>
                            <div className="flex gap-2">
                                <Button 
                                    variant={invoiceType === 'pi' ? 'default' : 'outline'}
                                    className={invoiceType === 'pi' ? 'bg-blue-600' : ''}
                                    onClick={() => setInvoiceType('pi')}
                                >
                                    <FileText size={18} className="mr-2" />
                                    PI
                                </Button>
                                <Button 
                                    variant={invoiceType === 'po' ? 'default' : 'outline'}
                                    className={invoiceType === 'po' ? 'bg-blue-600' : ''}
                                    onClick={() => setInvoiceType('po')}
                                >
                                    <ShoppingCart size={18} className="mr-2" />
                                    PO
                                </Button>
                            </div>
                        </div>

                        {/* New Price Selection */}
                        <div className="space-y-2">
                            <Label className="text-sm font-semibold">Column A (New Selection)</Label>
                            <Select value={newInvoiceId} onValueChange={setNewInvoiceId}>
                                <SelectTrigger className="w-full">
                                    <SelectValue placeholder="Select newest voucher..." />
                                </SelectTrigger>
                                <SelectContent className="max-h-60 overflow-y-auto">
                                    {filteredInvoices.map(inv => (
                                        <SelectItem key={inv.id} value={inv.id}>
                                            {inv.voucher_no} - {new Date(inv.date).toLocaleDateString()}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Old Price Selection */}
                        <div className="space-y-2">
                            <Label className="text-sm font-semibold">Column B (Old Selection)</Label>
                            <Select value={oldInvoiceId} onValueChange={setOldInvoiceId}>
                                <SelectTrigger className="w-full">
                                    <SelectValue placeholder="Select previous voucher..." />
                                </SelectTrigger>
                                <SelectContent className="max-h-60 overflow-y-auto">
                                    {filteredInvoices.map(inv => (
                                        <SelectItem key={inv.id} value={inv.id} disabled={inv.id === newInvoiceId}>
                                            {inv.voucher_no} - {new Date(inv.date).toLocaleDateString()}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Comparison Table */}
            <div className="border rounded-xl bg-white shadow-sm overflow-hidden">
                <Table>
                    <TableHeader className="bg-slate-50 border-b">
                        <TableRow>
                            <TableHead className="w-1/3">Product Details</TableHead>
                            <TableHead className="text-center bg-blue-50/50">New Price (A)</TableHead>
                            <TableHead className="text-center bg-orange-50/50">Old Price (B)</TableHead>
                            <TableHead className="text-right">Variance</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {!newInvoiceId || !oldInvoiceId ? (
                            <TableRow>
                                <TableCell colSpan={4} className="h-64 text-center text-slate-400">
                                    <div className="flex flex-col items-center gap-3">
                                        <ArrowRightLeft size={48} className="text-slate-200" />
                                        <p>Please select two documents to begin comparison</p>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ) : comparisonData.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={4} className="h-64 text-center text-slate-400">
                                    No products found in these documents.
                                </TableCell>
                            </TableRow>
                        ) : (
                            comparisonData.map((data, idx) => {
                                const stats = getPriceDiff(data.newPrice, data.oldPrice);
                                return (
                                    <TableRow key={idx} className="hover:bg-slate-50 transition-colors">
                                        <TableCell>
                                            <div className="font-medium text-slate-900">{data.product_name}</div>
                                            <div className="text-xs font-mono text-slate-500">{data.sku}</div>
                                        </TableCell>
                                        <TableCell className="text-center font-bold text-blue-700 bg-blue-50/20">
                                            {data.newPrice !== null ? `₹${formatCurrency(data.newPrice)}` : <Minus className="mx-auto text-slate-300" />}
                                        </TableCell>
                                        <TableCell className="text-center font-bold text-orange-700 bg-orange-50/20">
                                            {data.oldPrice !== null ? `₹${formatCurrency(data.oldPrice)}` : <Minus className="mx-auto text-slate-300" />}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {stats ? (
                                                <div className="flex flex-col items-end">
                                                    <span className={`flex items-center gap-1 font-bold ${stats.diff > 0 ? 'text-red-500' : stats.diff < 0 ? 'text-emerald-500' : 'text-slate-500'}`}>
                                                        {stats.diff > 0 ? <TrendingUp size={16} /> : stats.diff < 0 ? <TrendingDown size={16} /> : null}
                                                        {stats.diff > 0 ? '+' : ''}₹{formatCurrency(Math.abs(stats.diff))}
                                                    </span>
                                                    <span className="text-[10px] bg-slate-100 px-1.5 rounded-full font-medium">
                                                        {stats.percent > 0 ? '+' : ''}{stats.percent.toFixed(2)}%
                                                    </span>
                                                </div>
                                            ) : (
                                                <span className="text-slate-400 text-xs italic">N/A</span>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                );
                            })
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Comparison Summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-blue-50/30 border-blue-100">
                    <CardHeader className="py-4">
                        <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <Info size={16} className="text-blue-600" />
                            Column A Summary
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pb-4">
                        <div className="text-xs text-slate-600">
                            Voucher: <span className="font-bold">{newInvoiceData?.voucher_no || '-'}</span><br/>
                            Total Items: <span className="font-bold">{newInvoiceData?.line_items?.length || 0}</span>
                        </div>
                    </CardContent>
                </Card>
                <Card className="bg-orange-50/30 border-orange-100">
                    <CardHeader className="py-4">
                        <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <Info size={16} className="text-orange-600" />
                            Column B Summary
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pb-4">
                        <div className="text-xs text-slate-600">
                            Voucher: <span className="font-bold">{oldInvoiceData?.voucher_no || '-'}</span><br/>
                            Total Items: <span className="font-bold">{oldInvoiceData?.line_items?.length || 0}</span>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default PriceComparison;
