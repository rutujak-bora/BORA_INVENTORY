import React, { useState, useEffect, useMemo } from 'react';
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
    const [filterData, setFilterData] = useState({ categories: [], skus: [] });
    const [loading, setLoading] = useState(false);
    
    // Selection for Column A (Reference)
    const [referenceInvoiceId, setReferenceInvoiceId] = useState('');
    const [referenceInvoiceData, setReferenceInvoiceData] = useState(null);
    
    // Filtering states
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('all');
    const [skuFilter, setSkuFilter] = useState('all');
    
    // Manual prices for Column B
    const [manualPrices, setManualPrices] = useState({}); // { sku: price }
    
    const { toast } = useToast();

    // 1. Fetch Invoices and Filter Data on Mount
    useEffect(() => {
        fetchInvoices();
        fetchFilterData();
    }, [invoiceType]);

    const fetchInvoices = async () => {
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
        }
    };

    const fetchFilterData = async () => {
        setLoading(true);
        try {
            const response = await api.get('/products/transaction-filters');
            setFilterData(response.data);
        } catch (error) {
            toast({
                title: 'Error',
                description: 'Failed to fetch filter options',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    // 2. Fetch Reference Invoice Details
    useEffect(() => {
        const fetchDetails = async () => {
            if (!referenceInvoiceId) {
                setReferenceInvoiceData(null);
                return;
            }
            try {
                const endpoint = invoiceType === 'pi' ? `/pi/${referenceInvoiceId}` : `/po/${referenceInvoiceId}`;
                const response = await api.get(endpoint);
                setReferenceInvoiceData(response.data);
            } catch (error) {
                toast({
                    title: 'Error',
                    description: 'Failed to fetch document details',
                    variant: 'destructive',
                });
            }
        };
        fetchDetails();
    }, [referenceInvoiceId, invoiceType]);

    // 3. Cascading Filter Logic
    const categories = useMemo(() => {
        const typeData = filterData[invoiceType] || { categories: [] };
        return typeData.categories || [];
    }, [filterData, invoiceType]);

    const skus = useMemo(() => {
        const typeData = filterData[invoiceType] || { skus: [], sku_map: [] };
        if (categoryFilter === 'all') return typeData.skus || [];
        
        // Filter SKUs that belong to the selected category using the map
        return typeData.sku_map
            .filter(item => item.category === categoryFilter)
            .map(item => item.sku)
            .sort();
    }, [filterData, invoiceType, categoryFilter]);

    // Handle Reset when higher filters change
    useEffect(() => {
        setCategoryFilter('all');
        setSkuFilter('all');
        setReferenceInvoiceId('');
    }, [invoiceType]);

    useEffect(() => {
        setSkuFilter('all');
        setReferenceInvoiceId('');
    }, [categoryFilter]);

    useEffect(() => {
        setReferenceInvoiceId('');
    }, [skuFilter]);

    // 4. Smart Document Selection (Column A)
    const filteredInvoices = useMemo(() => {
        return invoices.filter(inv => {
            // 1. Date filter
            if (startDate || endDate) {
                const invDate = new Date(inv.date);
                const start = startDate ? new Date(startDate) : null;
                const end = endDate ? new Date(endDate) : null;
                if (start && invDate < start) return false;
                if (end && invDate > end) return false;
            }

            // 2. Content filter (Validation: Invoice must contain selected Category/SKU)
            const lineItems = inv.line_items || [];
            
            if (categoryFilter !== 'all') {
                const hasCategory = lineItems.some(item => item.category === categoryFilter);
                if (!hasCategory) return false;
            }

            if (skuFilter !== 'all') {
                const hasSku = lineItems.some(item => (item.sku || item.product_id) === skuFilter);
                if (!hasSku) return false;
            }

            return true;
        });
    }, [invoices, startDate, endDate, categoryFilter, skuFilter]);

    // 5. Comparison Data Generation
    const comparisonData = useMemo(() => {
        if (!referenceInvoiceData) return [];

        let items = referenceInvoiceData.line_items || [];
        
        // Final validation: show only matching products in table
        if (categoryFilter !== 'all') {
            items = items.filter(item => item.category === categoryFilter);
        }
        if (skuFilter !== 'all') {
            items = items.filter(item => (item.sku || item.product_id) === skuFilter);
        }

        return items.map(item => {
            const sku = item.sku || item.product_id;
            return {
                sku: sku,
                product_name: item.product_name || sku,
                category: item.category,
                qty: item.qty || item.quantity || 0,
                referencePrice: item.rate || null,
                manualPrice: manualPrices[sku] !== undefined ? manualPrices[sku] : (item.rate || null)
            };
        }).sort((a, b) => a.product_name.localeCompare(b.product_name));
    }, [referenceInvoiceData, categoryFilter, skuFilter, manualPrices]);

    const resetComparison = () => {
        setReferenceInvoiceId('');
        setStartDate('');
        setEndDate('');
        setCategoryFilter('all');
        setSkuFilter('all');
        setManualPrices({});
    };

    const handleManualPriceChange = (sku, value) => {
        const numValue = value === '' ? undefined : parseFloat(value);
        setManualPrices(prev => ({
            ...prev,
            [sku]: isNaN(numValue) ? undefined : numValue
        }));
    };

    const getPriceDiff = (manual, reference) => {
        if (manual === null || reference === null || manual === undefined) return null;
        const diff = manual - reference;
        const percent = reference !== 0 ? (diff / reference) * 100 : 0;
        return { diff, percent };
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900">Price Comparison</h1>
                    <p className="text-slate-600 mt-1">Compare reference vouchers with manual price entries</p>
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
                                onValueChange={(val) => {
                                    setCategoryFilter(val);
                                    setSkuFilter('all'); // Reset SKU when category changes
                                }}
                                options={[
                                    { value: 'all', label: 'All Categories' },
                                    ...categories.map(cat => ({ value: cat, label: cat }))
                                ]}
                                placeholder="Select Category..."
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
                                placeholder="Select SKU..."
                                searchPlaceholder="Search SKUs..."
                                disabled={categoryFilter === 'all' && skus.length === 0}
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        {/* Date Filters */}
                        <div className="space-y-2">
                            <Label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Reference Start Date</Label>
                            <Input 
                                type="date" 
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                className="border-slate-200"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Reference End Date</Label>
                            <Input 
                                type="date" 
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                className="border-slate-200"
                            />
                        </div>

                        {/* Column A (Reference Selection) */}
                        <div className="space-y-2 md:col-span-2">
                            <Label className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Column A: Reference Document Selection</Label>
                            <SearchableSelect 
                                value={referenceInvoiceId}
                                onValueChange={setReferenceInvoiceId}
                                options={filteredInvoices.map(inv => ({
                                    value: inv.id,
                                    label: `${inv.voucher_no} (${new Date(inv.date).toLocaleDateString()}) - ${inv.total_amount ? `₹${formatCurrency(inv.total_amount)}` : ''}`
                                }))}
                                placeholder="Choose a reference document..."
                            />
                            
                            {/* Dynamic Buyer/Supplier Display */}
                            {referenceInvoiceData && (
                                <div className="mt-2 flex items-center gap-2 p-2 bg-blue-50/50 rounded-lg border border-blue-100">
                                    <div className="p-1 bg-white rounded shadow-sm text-blue-600">
                                        {invoiceType === 'pi' ? <ShoppingCart size={14} /> : <ShoppingCart size={14} />}
                                    </div>
                                    <div className="text-sm">
                                        <span className="font-bold text-slate-500 uppercase text-[10px] tracking-wider block">
                                            {invoiceType === 'pi' ? 'Buyer Name' : 'Supplier Name'}
                                        </span>
                                        <span className="font-semibold text-slate-900">
                                            {invoiceType === 'pi' ? referenceInvoiceData.buyer : referenceInvoiceData.supplier || 'N/A'}
                                        </span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="flex justify-end mt-4">
                        <Button variant="ghost" className="text-slate-400 hover:text-slate-600 text-xs" onClick={resetComparison}>
                            Reset all filters
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
                            <TableHead className="text-center w-24">Qty (Ref)</TableHead>
                            <TableHead className="text-center bg-blue-50/30">Reference Price (A)</TableHead>
                            <TableHead className="text-center bg-emerald-50/30 font-bold">New Price (B - Manual)</TableHead>
                            <TableHead className="text-right">Price Variance</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {!referenceInvoiceId && categoryFilter === 'all' ? (
                            <TableRow>
                                <TableCell colSpan={5} className="h-80 text-center text-slate-400">
                                    <div className="flex flex-col items-center gap-4">
                                        <div className="p-4 bg-slate-100 rounded-full">
                                            <ArrowRightLeft size={48} className="text-slate-300" />
                                        </div>
                                        <div className="max-w-xs">
                                            <p className="font-semibold text-slate-600">No Comparison Active</p>
                                            <p className="text-sm">Select a reference document or filter by category to begin price entry</p>
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
                                const stats = getPriceDiff(data.manualPrice, data.referencePrice);
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
                                            {data.referencePrice !== null ? (
                                                <div className="font-bold text-blue-700">₹{formatCurrency(data.referencePrice)}</div>
                                            ) : (
                                                <Minus className="mx-auto text-slate-300" />
                                            )}
                                        </TableCell>
                                        <TableCell className="text-center bg-emerald-50/10">
                                            <div className="flex items-center justify-center gap-1 group/input">
                                                <span className="text-emerald-400 text-sm">₹</span>
                                                <Input 
                                                    type="number" 
                                                    value={data.manualPrice !== null ? data.manualPrice : ''}
                                                    onChange={(e) => handleManualPriceChange(data.sku, e.target.value)}
                                                    placeholder="0.00"
                                                    className="w-28 h-9 text-center font-bold text-emerald-700 bg-transparent border-transparent group-hover/input:border-emerald-200 focus:bg-white focus:border-emerald-500 transition-all"
                                                />
                                            </div>
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
                                                <span className="text-slate-400 text-[10px] uppercase font-bold tracking-widest italic">Ready</span>
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
