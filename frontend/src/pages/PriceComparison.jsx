import React, { useState, useEffect } from 'react';
import api from '../utils/api';
import { formatCurrency } from '../utils/formatters';
import { Card, CardContent } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { TrendingUp, TrendingDown, Minus, ArrowRightLeft, FileText, ShoppingCart, Search, Package } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { SearchableSelect } from '../components/SearchableSelect';

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
    const [skuFilter, setSkuFilter] = useState('all');
    
    // Price persistence state
    const [priceOverrides, setPriceOverrides] = useState({}); // { sku: overriddenPrice }
    
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
        setSkuFilter('all');
        setPriceOverrides({});
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

    // Available SKUs extracted from current loaded data
    const skus = Array.from(new Set([
        ...(newInvoiceData?.line_items?.map(item => item.sku || item.product_id) || []),
        ...(oldInvoiceData?.line_items?.map(item => item.sku || item.product_id) || [])
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
            if (skuFilter !== 'all' && sku !== skuFilter) return;
            
            productMap.set(sku, {
                sku: sku,
                product_name: item.product_name,
                category: item.category,
                qty: item.qty || item.quantity || 0,
                newPrice: priceOverrides[sku] !== undefined ? priceOverrides[sku] : item.rate,
                actualNewPrice: item.rate,
                oldPrice: null
            });
        });

        // Process Old Invoice
        oldInvoiceData?.line_items?.forEach(item => {
            if (categoryFilter !== 'all' && item.category !== categoryFilter) return;
            const sku = item.sku || item.product_id;
            if (skuFilter !== 'all' && sku !== skuFilter) return;
            
            if (productMap.has(sku)) {
                const existing = productMap.get(sku);
                existing.oldPrice = item.rate;
            } else {
                productMap.set(sku, {
                    sku: sku,
                    product_name: item.product_name,
                    category: item.category,
                    qty: 0, // Not in new doc
                    newPrice: priceOverrides[sku] !== undefined ? priceOverrides[sku] : null,
                    oldPrice: item.rate
                });
            }
        });

        return Array.from(productMap.values()).sort((a, b) => a.product_name.localeCompare(b.product_name));
    };

    const handlePriceChange = (sku, value) => {
        const numValue = value === '' ? undefined : parseFloat(value);
        setPriceOverrides(prev => ({
            ...prev,
            [sku]: isNaN(numValue) ? undefined : numValue
        }));
    };

    const comparisonData = getComparisonData();

    const getPriceDiff = (newP, oldP) => {
        if (newP === null || oldP === null || newP === undefined) return null;
        const diff = newP - oldP;
        const percent = oldP !== 0 ? (diff / oldP) * 100 : 0;
        return { diff, percent };
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900">Price Comparison</h1>
                    <p className="text-slate-600 mt-1">Compare product rates and analyze variations</p>
                </div>
            </div>

            <Card className="border-slate-200 shadow-sm overflow-hidden">
                <CardContent className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 border-b border-slate-100 pb-8">
                        {/* 1. Document Type */}
                        <div className="space-y-2">
                            <Label className="text-sm font-bold text-slate-700 flex items-center gap-2">
                                <Search size={14} className="text-blue-500" />
                                1. Document Type
                            </Label>
                            <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
                                <Button 
                                    variant={invoiceType === 'pi' ? 'default' : 'ghost'}
                                    className={`flex-1 ${invoiceType === 'pi' ? 'bg-white text-blue-600 shadow-sm hover:bg-white' : 'text-slate-500'}`}
                                    onClick={() => setInvoiceType('pi')}
                                >
                                    <FileText size={16} className="mr-2" />
                                    PI
                                </Button>
                                <Button 
                                    variant={invoiceType === 'po' ? 'default' : 'ghost'}
                                    className={`flex-1 ${invoiceType === 'po' ? 'bg-white text-blue-600 shadow-sm hover:bg-white' : 'text-slate-500'}`}
                                    onClick={() => setInvoiceType('po')}
                                >
                                    <ShoppingCart size={16} className="mr-2" />
                                    PO
                                </Button>
                            </div>
                        </div>

                        {/* 2. Product Category */}
                        <div className="space-y-2">
                            <Label className="text-sm font-bold text-slate-700">2. Product Category</Label>
                            <SearchableSelect 
                                value={categoryFilter}
                                onValueChange={setCategoryFilter}
                                options={[
                                    { value: 'all', label: 'All Categories' },
                                    ...categories.map(cat => ({ value: cat, label: cat }))
                                ]}
                                placeholder="All Categories"
                                searchPlaceholder="Search categories..."
                            />
                        </div>

                        {/* 3. SKU Filter */}
                        <div className="space-y-2">
                            <Label className="text-sm font-bold text-slate-700">3. SKU Name</Label>
                            <SearchableSelect 
                                value={skuFilter}
                                onValueChange={setSkuFilter}
                                options={[
                                    { value: 'all', label: 'All SKUs' },
                                    ...skus.map(s => ({ value: s, label: s }))
                                ]}
                                placeholder="All SKUs"
                                searchPlaceholder="Search SKUs..."
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        {/* Date Filters */}
                        <div className="space-y-2">
                            <Label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Start Date</Label>
                            <Input 
                                type="date" 
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                className="border-slate-200"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">End Date</Label>
                            <Input 
                                type="date" 
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                className="border-slate-200"
                            />
                        </div>

                        {/* Column A (New Selection) */}
                        <div className="space-y-2">
                            <Label className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Column A (New Selection)</Label>
                            <SearchableSelect 
                                value={newInvoiceId}
                                onValueChange={setNewInvoiceId}
                                options={filteredInvoices.map(inv => ({
                                    value: inv.id,
                                    label: `${inv.voucher_no} (${new Date(inv.date).toLocaleDateString()})`
                                }))}
                                placeholder="Select newest voucher..."
                            />
                        </div>

                        {/* Column B (Old Selection) */}
                        <div className="space-y-2">
                            <Label className="text-xs font-semibold text-orange-600 uppercase tracking-wider">Column B (Old Selection)</Label>
                            <SearchableSelect 
                                value={oldInvoiceId}
                                onValueChange={setOldInvoiceId}
                                options={filteredInvoices
                                    .filter(inv => inv.id !== newInvoiceId)
                                    .map(inv => ({
                                        value: inv.id,
                                        label: `${inv.voucher_no} (${new Date(inv.date).toLocaleDateString()})`
                                    }))}
                                placeholder="Select previous voucher..."
                            />
                        </div>
                    </div>

                    <div className="flex justify-end mt-4">
                        <Button variant="ghost" className="text-slate-400 hover:text-slate-600 text-xs" onClick={resetComparison}>
                            Clear all filters
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Comparison Table */}
            <div className="border border-slate-200 rounded-xl bg-white shadow-sm overflow-hidden">
                <Table>
                    <TableHeader className="bg-slate-50/80 border-b">
                        <TableRow>
                            <TableHead className="w-1/3">Product Details & SKU</TableHead>
                            <TableHead className="text-center w-24">Qty</TableHead>
                            <TableHead className="text-center bg-blue-50/30">New Price (A)</TableHead>
                            <TableHead className="text-center bg-orange-50/30">Old Price (B)</TableHead>
                            <TableHead className="text-right">Price Variance</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {!newInvoiceId || !oldInvoiceId ? (
                            <TableRow>
                                <TableCell colSpan={5} className="h-80 text-center text-slate-400">
                                    <div className="flex flex-col items-center gap-4">
                                        <div className="p-4 bg-slate-100 rounded-full">
                                            <ArrowRightLeft size={48} className="text-slate-300" />
                                        </div>
                                        <div className="max-w-xs">
                                            <p className="font-semibold text-slate-600">No Comparison Active</p>
                                            <p className="text-sm">Select two documents from the dropdowns above to begin Price Comparison</p>
                                        </div>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ) : comparisonData.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5} className="h-64 text-center text-slate-400">
                                    No products found matching the selected filters.
                                </TableCell>
                            </TableRow>
                        ) : (
                            comparisonData.map((data, idx) => {
                                const stats = getPriceDiff(data.newPrice, data.oldPrice);
                                return (
                                    <TableRow key={idx} className="group hover:bg-slate-50/50 transition-colors">
                                        <TableCell>
                                            <div className="flex items-start gap-3">
                                                <div className="mt-1 p-1.5 bg-slate-100 rounded-md group-hover:bg-white border border-transparent group-hover:border-slate-200 transition-all">
                                                    <Package size={16} className="text-slate-500" />
                                                </div>
                                                <div>
                                                    <div className="font-semibold text-slate-900">{data.product_name}</div>
                                                    <div className="flex items-center gap-2 mt-0.5">
                                                        <span className="text-[10px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded uppercase">{data.sku}</span>
                                                        <span className="text-[10px] text-slate-400">•</span>
                                                        <span className="text-[10px] text-slate-500">{data.category}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-center">
                                            <span className="inline-flex items-center justify-center min-w-8 h-8 px-2 bg-slate-100 rounded-lg text-xs font-bold text-slate-700">
                                                {formatNumber(data.qty)}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-center bg-blue-50/10">
                                            <div className="flex items-center justify-center gap-1 group/input">
                                                <span className="text-blue-400 text-sm">₹</span>
                                                <Input 
                                                    type="number" 
                                                    value={data.newPrice !== null ? data.newPrice : ''}
                                                    onChange={(e) => handlePriceChange(data.sku, e.target.value)}
                                                    placeholder={data.actualNewPrice || "0.00"}
                                                    className="w-24 h-9 text-center font-bold text-blue-700 bg-transparent border-transparent group-hover/input:border-blue-200 focus:bg-white focus:border-blue-500 transition-all"
                                                />
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-center bg-orange-50/10">
                                            {data.oldPrice !== null ? (
                                                <div className="font-bold text-orange-700">₹{formatCurrency(data.oldPrice)}</div>
                                            ) : (
                                                <Minus className="mx-auto text-slate-300" />
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {stats ? (
                                                <div className="flex flex-col items-end">
                                                    <span className={`flex items-center gap-1 font-bold ${stats.diff > 0 ? 'text-red-500' : stats.diff < 0 ? 'text-emerald-500' : 'text-slate-500'}`}>
                                                        {stats.diff > 0 ? <TrendingUp size={14} /> : stats.diff < 0 ? <TrendingDown size={14} /> : null}
                                                        {stats.diff > 0 ? '+' : ''}₹{formatCurrency(Math.abs(stats.diff))}
                                                    </span>
                                                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold mt-1 ${stats.diff > 0 ? 'bg-red-50 text-red-600' : stats.diff < 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-600'}`}>
                                                        {stats.percent > 0 ? '+' : ''}{stats.percent.toFixed(2)}%
                                                    </span>
                                                </div>
                                            ) : (
                                                <span className="text-slate-400 text-[10px] uppercase font-bold tracking-widest italic">Incomplete</span>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                );
                            })
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
};

// Internal formatter for number if not imported
const formatNumber = (num) => {
    return new Intl.NumberFormat('en-IN').format(num);
};

export default PriceComparison;
