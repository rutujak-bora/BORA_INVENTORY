import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Building2, FileStack } from 'lucide-react';

const ModeSelection = () => {
  const navigate = useNavigate();
  const { isDNSUser } = useAuth();

  const handleModeSelect = (mode) => {
    if (mode === 'all') {
      navigate('/dashboard');
    } else {
      navigate('/dashboard');
    }
  };

  if (isDNSUser()) {
    // DNS users automatically go to limited dashboard
    navigate('/dashboard');
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-5xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">Select Access Mode</h1>
          <p className="text-slate-400 text-lg">Choose how you want to access the system</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* All Companies Documentary */}
          <div
            className="bg-white rounded-2xl shadow-2xl p-8 hover:shadow-blue-600/20 transition-all cursor-pointer group"
            onClick={() => handleModeSelect('all')}
            data-testid="all-companies-mode-btn"
          >
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-lg shadow-blue-600/50">
              <Building2 size={40} className="text-white" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">All Companies Documentary</h2>
            <p className="text-slate-600 mb-6">
              Full access to all modules including companies, products, warehouses, PI, PO, stock
              management, payments, expenses, and P&L reports.
            </p>
            <Button className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white">
              Enter Full Access
            </Button>
          </div>

          {/* DNS Documentary */}
          <div
            className="bg-white rounded-2xl shadow-2xl p-8 hover:shadow-emerald-600/20 transition-all cursor-pointer group"
            onClick={() => handleModeSelect('dns')}
            data-testid="dns-mode-btn"
          >
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-lg shadow-emerald-600/50">
              <FileStack size={40} className="text-white" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">DNS Documentary</h2>
            <p className="text-slate-600 mb-6">
              Limited access focused on core operations: proforma Invoice, Purchase Order, and Payment
              Tracking modules.
            </p>
            <Button className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white">
              Enter Limited Access
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModeSelection;
