import React, { useState, useEffect } from "react";
import api from "../utils/api";
import { Eye, Trash2, RefreshCw, Filter, X, Download } from "lucide-react";
import * as XLSX from 'xlsx';

/**
 * STOCK SUMMARY - TWO SECTIONS
 * 1. Stock Entries: Warehouse Inward + Export Invoice (regular flow with PO/PI)
 * 2. Direct Stock Entries: Direct Inward + Direct Outward (direct flow without PO/PI)
 * Columns: Product | SKU | Color | PI & PO Number | Category | Warehouse | Company | Inward | Outward | Remaining | Status | Age | Actions
 */

const StockSummaryNew = () => {
  const [activeTab, setActiveTab] = useState("regular"); // regular or direct
  const [stockData, setStockData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Filter states
  const [filters, setFilters] = useState({
    company: "",
    warehouse: "",
    piNumber: "",
    poNumber: "",
    sku: "",
    category: ""
  });

  // Dropdown options
  const [companies, setCompanies] = useState([]);
  const [warehouses, setWarehouses] = useState([]);

  // View transaction dialog
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [transactions, setTransactions] = useState([]);

  // Delete confirmation dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [stockToDelete, setStockToDelete] = useState(null);

  useEffect(() => {
    fetchStockSummary();
    fetchDropdownOptions();
  }, [activeTab]); // Refetch when tab changes

  useEffect(() => {
    applyFilters();
  }, [stockData, filters]);

  const fetchStockSummary = async () => {
    try {
      setLoading(true);
      // Fetch based on active tab
      const response = await api.get(`/stock-summary?entry_type=${activeTab}`);
      setStockData(response.data);
    } catch (error) {
      console.error("Error fetching stock summary:", error);
      alert("Failed to load stock summary");
    } finally {
      setLoading(false);
    }
  };

  const fetchDropdownOptions = async () => {
    try {
      const [companiesRes, warehousesRes] = await Promise.all([
        api.get("/companies"),
        api.get("/warehouses")
      ]);
      setCompanies(companiesRes.data);
      setWarehouses(warehousesRes.data);
    } catch (error) {
      console.error("Error fetching dropdown options:", error);
    }
  };

  const applyFilters = () => {
    let filtered = [...stockData];

    if (filters.company) {
      filtered = filtered.filter(item =>
        item.company_name?.toLowerCase().includes(filters.company.toLowerCase())
      );
    }

    if (filters.warehouse) {
      filtered = filtered.filter(item =>
        item.warehouse_name?.toLowerCase().includes(filters.warehouse.toLowerCase())
      );
    }

    if (filters.piNumber) {
      filtered = filtered.filter(item =>
        item.pi_number?.toLowerCase().includes(filters.piNumber.toLowerCase())
      );
    }

    if (filters.poNumber) {
      filtered = filtered.filter(item =>
        item.po_number?.toLowerCase().includes(filters.poNumber.toLowerCase())
      );
    }

    if (filters.sku) {
      filtered = filtered.filter(item =>
        item.sku?.toLowerCase().includes(filters.sku.toLowerCase())
      );
    }

    if (filters.category) {
      filtered = filtered.filter(item =>
        item.category?.toLowerCase().includes(filters.category.toLowerCase())
      );
    }

    setFilteredData(filtered);
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const resetFilters = () => {
    setFilters({
      company: "",
      warehouse: "",
      piNumber: "",
      poNumber: "",
      sku: "",
      category: ""
    });
  };

  const handleView = async (stock) => {
    try {
      setSelectedStock(stock);
      const response = await api.get(
        `/stock-transactions/${stock.product_id}/${stock.warehouse_id}`
      );
      setTransactions(response.data.transactions || []);
      setViewDialogOpen(true);
    } catch (error) {
      console.error("Error fetching transactions:", error);
      alert("Failed to load transaction history");
    }
  };

  const handleDeleteClick = (stock) => {
    setStockToDelete(stock);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!stockToDelete) return;

    try {
      await api.delete(`/stock-summary/${stockToDelete.id}`);
      alert("Stock entry deleted successfully");
      setDeleteDialogOpen(false);
      setStockToDelete(null);
      fetchStockSummary(); // Refresh data
    } catch (error) {
      console.error("Error deleting stock:", error);
      alert("Failed to delete stock entry");
    }
  };

  const exportToExcel = () => {
    if (filteredData.length === 0) {
      alert("No data to export");
      return;
    }

    // Prepare data for export
    const exportData = filteredData.map(stock => ({
      'Product': stock.product_name,
      'SKU': stock.sku,
      'Color': stock.color || 'N/A',
      'PI & PO Number': stock.pi_po_number,
      'Category': stock.category,
      'Warehouse': stock.warehouse_name,
      'Company': stock.company_name,
      'In-Transit': stock.in_transit || 0,
      'Inward': stock.quantity_inward,
      'Outward': stock.quantity_outward,
      'Remaining': stock.remaining_stock,
      'Status': stock.status,
      'Age (Days)': stock.age_days
    }));

    // Create worksheet
    const ws = XLSX.utils.json_to_sheet(exportData);
    
    // Create workbook
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Stock Summary');
    
    // Generate file name with timestamp
    const timestamp = new Date().toISOString().split('T')[0];
    const fileName = `Stock_Summary_${timestamp}.xlsx`;
    
    // Download file
    XLSX.writeFile(wb, fileName);
  };

  const getStatusBadge = (status) => {
    const statusColors = {
      "Low Stock": "bg-red-100 text-red-800 border border-red-300",
      "Normal": "bg-green-100 text-green-800 border border-green-300"
    };

    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-semibold ${
          statusColors[status] || "bg-gray-100 text-gray-800"
        }`}
      >
        {status}
      </span>
    );
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Stock Summary</h1>
          <p className="text-gray-600 mt-1">
            Real-time stock tracking from Warehouse Inward and Export Invoice
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={exportToExcel}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            disabled={loading || filteredData.length === 0}
          >
            <Download className="w-4 h-4" />
            Export to Excel
          </button>
          <button
            onClick={fetchStockSummary}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab("regular")}
              className={`py-4 px-6 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "regular"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              📦 Stock Entries
              <span className="ml-2 text-xs text-gray-500">(Warehouse Inward + Export Invoice)</span>
            </button>
            <button
              onClick={() => setActiveTab("direct")}
              className={`py-4 px-6 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "direct"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              ⚡ Direct Stock Entries
              <span className="ml-2 text-xs text-gray-500">(Direct Inward + Direct Outward)</span>
            </button>
          </nav>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-800">
          {activeTab === "regular" ? (
            <>
              <strong>Stock Entries:</strong> Displays stock from{" "}
              <span className="font-semibold">Warehouse Inward</span> (PO-based) and{" "}
              <span className="font-semibold">Export Invoice</span> entries.
            </>
          ) : (
            <>
              <strong>Direct Stock Entries:</strong> Displays stock from{" "}
              <span className="font-semibold">Direct Inward</span> (no PO) and{" "}
              <span className="font-semibold">Direct Outward</span> entries.
            </>
          )}
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filters
          </h3>
          <button
            onClick={resetFilters}
            className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
          >
            <X className="w-4 h-4" />
            Reset All
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
                Company
              </label>
              <select
                value={filters.company}
                onChange={(e) => handleFilterChange("company", e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Companies</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.name}>
                    {company.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Warehouse
              </label>
              <select
                value={filters.warehouse}
                onChange={(e) => handleFilterChange("warehouse", e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Warehouses</option>
                {warehouses.map((warehouse) => (
                  <option key={warehouse.id} value={warehouse.name}>
                    {warehouse.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                PI Number
              </label>
              <input
                type="text"
                value={filters.piNumber}
                onChange={(e) => handleFilterChange("piNumber", e.target.value)}
                placeholder="Search PI..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                PO Number
              </label>
              <input
                type="text"
                value={filters.poNumber}
                onChange={(e) => handleFilterChange("poNumber", e.target.value)}
                placeholder="Search PO..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SKU
              </label>
              <input
                type="text"
                value={filters.sku}
                onChange={(e) => handleFilterChange("sku", e.target.value)}
                placeholder="Search SKU..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <input
                type="text"
                value={filters.category}
                onChange={(e) => handleFilterChange("category", e.target.value)}
                placeholder="Search Category..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Stock Summary Table */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Product
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    SKU
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Color
                  </th>
                  {/* <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    PI & PO Number
                  </th> */}
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Warehouse
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Company
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    In-transit
                  </th>
                  {/* <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Inward
                  </th> */}
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Outward
                  </th>
                  {/* <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Remaining
                  </th> */}
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Age (Days)
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan="14" className="px-4 py-8 text-center text-gray-500">
                      Loading...
                    </td>
                  </tr>
                ) : filteredData.length === 0 ? (
                  <tr>
                    <td colSpan="14" className="px-4 py-8 text-center text-gray-500">
                      No stock records found. Create Warehouse Inward entries to see data here.
                    </td>
                  </tr>
                ) : (
                  filteredData.map((stock) => (
                    <tr key={stock.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {stock.product_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {stock.sku}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {stock.color || 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {stock.pi_po_number}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {stock.category}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {stock.warehouse_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {stock.company_name}
                      </td>
                      <td className="px-4 py-3 text-center text-sm font-semibold text-purple-600">
                        {stock.in_transit || 0}
                      </td>
                      <td className="px-4 py-3 text-center text-sm font-semibold text-green-600">
                        {stock.quantity_inward || 0}
                      </td>
                      <td className="px-4 py-3 text-center text-sm font-semibold text-orange-600">
                        {stock.quantity_outward || 0}
                      </td>
                      <td className="px-4 py-3 text-center text-sm font-bold text-blue-600">
                        {stock.remaining_stock || 0}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {getStatusBadge(stock.status)}
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-600">
                        {stock.age_days}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex justify-center gap-2">
                          <button
                            onClick={() => handleView(stock)}
                            className="text-blue-600 hover:text-blue-800"
                            title="View Transactions"
                          >
                            <Eye className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleDeleteClick(stock)}
                            className="text-red-600 hover:text-red-800"
                            title="Delete Entry"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Summary Footer */}
          {filteredData.length > 0 && (
            <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
              <div className="flex justify-between items-center text-sm text-gray-700">
                <span>
                  Total Records: <strong>{filteredData.length}</strong>
                </span>
                <span>
                  Total In-Transit: <strong className="text-purple-600">
                    {filteredData.reduce((sum, item) => sum + (item.in_transit || 0), 0)}
                  </strong>
                  {" | "}
                  Total Inward: <strong className="text-green-600">
                    {filteredData.reduce((sum, item) => sum + (item.quantity_inward || 0), 0)}
                  </strong>
                  {" | "}
                  Total Outward: <strong className="text-orange-600">
                    {filteredData.reduce((sum, item) => sum + (item.quantity_outward || 0), 0)}
                  </strong>
                  {" | "}
                  Total Remaining: <strong className="text-blue-600">
                    {filteredData.reduce((sum, item) => sum + (item.remaining_stock || 0), 0)}
                  </strong>
                </span>
              </div>
            </div>
          )}
        </div>

        {/* View Transactions Dialog */}
        {viewDialogOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
              <div className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center">
                <h2 className="text-xl font-bold">Transaction History</h2>
                <button
                  onClick={() => setViewDialogOpen(false)}
                  className="text-white hover:text-gray-200"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
                {/* Stock Details */}
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <h3 className="font-semibold text-gray-900 mb-2">Stock Details</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div><strong>Product:</strong> {selectedStock?.product_name}</div>
                    <div><strong>SKU:</strong> {selectedStock?.sku}</div>
                    <div><strong>Warehouse:</strong> {selectedStock?.warehouse_name}</div>
                    <div><strong>Company:</strong> {selectedStock?.company_name}</div>
                  </div>
                </div>

                {/* Transactions Table */}
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          Type
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          Date
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          Reference No
                        </th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">
                          Quantity
                        </th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                          Rate
                        </th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                          Amount
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {transactions.length === 0 ? (
                        <tr>
                          <td colSpan="6" className="px-4 py-4 text-center text-gray-500">
                            No transactions found
                          </td>
                        </tr>
                      ) : (
                        transactions.map((txn, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-4 py-2">
                              <span
                                className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                  txn.type === "inward"
                                    ? "bg-green-100 text-green-800"
                                    : "bg-orange-100 text-orange-800"
                                }`}
                              >
                                {txn.type === "inward" ? "Inward" : "Outward"}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-sm text-gray-600">
                              {new Date(txn.date).toLocaleDateString()}
                            </td>
                            <td className="px-4 py-2 text-sm text-gray-600">
                              {txn.reference_no}
                            </td>
                            <td className="px-4 py-2 text-center text-sm font-semibold">
                              {txn.quantity}
                            </td>
                            <td className="px-4 py-2 text-right text-sm text-gray-600">
                              ₹{txn.rate.toFixed(2)}
                            </td>
                            <td className="px-4 py-2 text-right text-sm font-semibold">
                              ₹{txn.amount.toFixed(2)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Dialog */}
        {deleteDialogOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
              <div className="bg-red-600 text-white px-6 py-4">
                <h2 className="text-xl font-bold">Confirm Delete</h2>
              </div>

              <div className="p-6">
                <p className="text-gray-700 mb-4">
                  Are you sure you want to delete this stock entry?
                </p>
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <div className="text-sm">
                    <div><strong>Product:</strong> {stockToDelete?.product_name}</div>
                    <div><strong>SKU:</strong> {stockToDelete?.sku}</div>
                    <div><strong>Warehouse:</strong> {stockToDelete?.warehouse_name}</div>
                    <div><strong>Remaining:</strong> {stockToDelete?.remaining_stock} units</div>
                  </div>
                </div>
                <p className="text-sm text-red-600">
                  Note: This will only remove the entry from Stock Summary. Original inward/outward records will not be affected.
                </p>
              </div>

              <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3">
                <button
                  onClick={() => setDeleteDialogOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDelete}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
  );
};

export default StockSummaryNew;
