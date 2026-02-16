import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { formatNumber } from '../utils/formatters';
import { Building2, Warehouse, FileText, ShoppingCart, TrendingDown, TrendingUp, Clock, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { useToast } from '../hooks/use-toast';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await api.get('/dashboard/stats');
      setStats(response.data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load dashboard statistics',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Companies',
      value: formatNumber(stats?.total_companies) || 0,
      icon: Building2,
      color: 'from-blue-500 to-blue-600',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600',
    },
    {
      title: 'Total Warehouses',
      value: formatNumber(stats?.total_warehouses) || 0,
      icon: Warehouse,
      color: 'from-purple-500 to-purple-600',
      bgColor: 'bg-purple-50',
      textColor: 'text-purple-600',
    },
    {
      title: 'proforma Invoices',
      value: formatNumber(stats?.total_pis) || 0,
      icon: FileText,
      color: 'from-emerald-500 to-emerald-600',
      bgColor: 'bg-emerald-50',
      textColor: 'text-emerald-600',
    },
    {
      title: 'Purchase Orders',
      value: formatNumber(stats?.total_pos) || 0,
      icon: ShoppingCart,
      color: 'from-amber-500 to-amber-600',
      bgColor: 'bg-amber-50',
      textColor: 'text-amber-600',
    },
    {
      title: 'Total Stock Inward',
      value: formatNumber(stats?.total_stock_inward) || 0,
      icon: TrendingDown,
      color: 'from-teal-500 to-teal-600',
      bgColor: 'bg-teal-50',
      textColor: 'text-teal-600',
    },
    {
      title: 'Total Stock Outward',
      value: formatNumber(stats?.total_stock_outward) || 0,
      icon: TrendingUp,
      color: 'from-rose-500 to-rose-600',
      bgColor: 'bg-rose-50',
      textColor: 'text-rose-600',
    },
    {
      title: 'Pending PIs',
      value: formatNumber(stats?.pending_pis) || 0,
      icon: Clock,
      color: 'from-orange-500 to-orange-600',
      bgColor: 'bg-orange-50',
      textColor: 'text-orange-600',
    },
    {
      title: 'Pending POs',
      value: formatNumber(stats?.pending_pos) || 0,
      icon: AlertCircle,
      color: 'from-red-500 to-red-600',
      bgColor: 'bg-red-50',
      textColor: 'text-red-600',
    },
  ];

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-600 mt-1">Welcome to Bora Mobility Inventory Management System</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="hover:shadow-lg transition-shadow" data-testid={`stat-card-${index}`}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-600 font-medium">{stat.title}</p>
                    <p className="text-3xl font-bold text-slate-900 mt-2">{stat.value}</p>
                  </div>
                  <div className={`p-4 rounded-xl ${stat.bgColor}`}>
                    <Icon className={stat.textColor} size={28} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button className="p-4 border-2 border-slate-200 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition-all text-center" data-testid="quick-action-new-pi">
              <FileText className="mx-auto mb-2 text-blue-600" size={32} />
              <span className="text-sm font-medium text-slate-700">New PI</span>
            </button>
            <button className="p-4 border-2 border-slate-200 rounded-xl hover:border-emerald-500 hover:bg-emerald-50 transition-all text-center" data-testid="quick-action-new-po">
              <ShoppingCart className="mx-auto mb-2 text-emerald-600" size={32} />
              <span className="text-sm font-medium text-slate-700">New PO</span>
            </button>
            <button className="p-4 border-2 border-slate-200 rounded-xl hover:border-teal-500 hover:bg-teal-50 transition-all text-center" data-testid="quick-action-inward-stock">
              <TrendingDown className="mx-auto mb-2 text-teal-600" size={32} />
              <span className="text-sm font-medium text-slate-700">Inward Stock</span>
            </button>
            <button className="p-4 border-2 border-slate-200 rounded-xl hover:border-rose-500 hover:bg-rose-50 transition-all text-center" data-testid="quick-action-outward-stock">
              <TrendingUp className="mx-auto mb-2 text-rose-600" size={32} />
              <span className="text-sm font-medium text-slate-700">Outward Stock</span>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
