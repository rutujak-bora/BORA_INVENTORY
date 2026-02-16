import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Building2,
  Package,
  Warehouse,
  Banknote,
  FileText,
  ShoppingCart,
  TrendingUp,
  TrendingDown,
  CreditCard,
  DollarSign,
  BarChart3,
  Menu,
  X,
  LogOut,
  User,
} from 'lucide-react';

const Layout = ({ children }) => {
  const { user, logout, isDNSUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = user?.section === 'dns'
    ? [
        { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { path: '/products', label: 'Product Master', icon: Package },
        { path: '/pi', label: 'proforma Invoice', icon: FileText },
        { path: '/po', label: 'Purchase Order', icon: ShoppingCart },
        { path: '/payments', label: 'Payment Tracking', icon: CreditCard },
      ]
    : [
        { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
        {
          label: 'Master Data',
          children: [
            { path: '/companies', label: 'Companies', icon: Building2 },
            { path: '/products', label: 'Products', icon: Package },
            { path: '/warehouses', label: 'Warehouses', icon: Warehouse },
            { path: '/banks', label: 'Banks', icon: Banknote },
          ],
        },
        {
          label: 'Transactions',
          children: [
            { path: '/pi', label: 'proforma Invoice', icon: FileText },
            { path: '/po', label: 'Purchase Order', icon: ShoppingCart },
          ],
        },
        {
          label: 'Stock Management',
          children: [
            { path: '/inward', label: 'Inward Stock', icon: TrendingDown },
            { path: '/outward', label: 'Outward Stock', icon: TrendingUp },
            { path: '/stock-summary', label: 'Stock Summary', icon: BarChart3 },
          ],
        },
        {
          label: 'Customer Management',
          children: [
            { path: '/customer-management', label: 'Customer Tracking', icon: User },
            { path: '/purchase-analysis', label: 'Purchase Analysis', icon: TrendingUp },
          ],
        },
        {
          label: 'Payment Management',
          children: [
            { path: '/payments', label: 'Payment Tracking', icon: CreditCard },
          ],
        },
        {
          label: 'Reports',
          children: [
            { path: '/expenses', label: 'Expense Calculation', icon: DollarSign },
            { path: '/pl-report', label: 'P&L Reporting', icon: TrendingUp },
          ],
        },
      ];

  const isActive = (path) => location.pathname === path;

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-slate-900 text-white transition-all duration-300 flex flex-col`}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-700 flex items-center justify-between">
          {sidebarOpen && (
            <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Bora Mobility
            </h1>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            data-testid="sidebar-toggle-btn"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Menu */}
        <nav className="flex-1 overflow-y-auto py-4 px-2">
          {menuItems.map((item, index) => (
            <div key={index} className="mb-2">
              {item.children ? (
                <div>
                  {sidebarOpen && (
                    <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase">
                      {item.label}
                    </div>
                  )}
                  {item.children.map((child) => {
                    const Icon = child.icon;
                    return (
                      <Link
                        key={child.path}
                        to={child.path}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                          isActive(child.path)
                            ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/50'
                            : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                        }`}
                        data-testid={`nav-${child.label.toLowerCase().replace(/ /g, '-')}`}
                      >
                        <Icon size={20} />
                        {sidebarOpen && <span className="text-sm">{child.label}</span>}
                      </Link>
                    );
                  })}
                </div>
              ) : (
                <Link
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                    isActive(item.path)
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/50'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                  data-testid={`nav-${item.label.toLowerCase().replace(/ /g, '-')}`}
                >
                  {item.icon && <item.icon size={20} />}
                  {sidebarOpen && <span className="text-sm">{item.label}</span>}
                </Link>
              )}
            </div>
          ))}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center">
              <User size={20} />
            </div>
            {sidebarOpen && (
              <div className="flex-1">
                <div className="text-sm font-medium">{user?.username}</div>
                <div className="text-xs text-slate-400 capitalize">{user?.role}</div>
              </div>
            )}
          </div>
          {sidebarOpen && (
            <button
              onClick={handleLogout}
              className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors text-sm"
              data-testid="logout-btn"
            >
              <LogOut size={16} />
              Logout
            </button>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
};

export default Layout;
