import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, FileStack, ArrowRight } from 'lucide-react';
import { Button } from '../components/ui/button';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-lg">
              <Building2 size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Bora Mobility LLP</h1>
              <p className="text-sm text-slate-400">Inventory Management System</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-6xl mx-auto">
          {/* Title */}
          <div className="text-center mb-16">
            <h2 className="text-5xl font-bold text-white mb-4">
              Select Your Workspace
            </h2>
            <p className="text-xl text-slate-300">
              Choose the documentary section you want to access
            </p>
          </div>

          {/* Two Options */}
          <div className="grid md:grid-cols-2 gap-8">
            {/* All Companies Documentary */}
            <div
              className="group bg-white rounded-3xl p-8 hover:shadow-2xl hover:shadow-blue-600/20 transition-all duration-300 cursor-pointer border-2 border-transparent hover:border-blue-500"
              onClick={() => navigate('/login?section=all_companies')}
              data-testid="all-companies-section"
            >
              <div className="flex flex-col h-full">
                <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-xl">
                  <Building2 size={48} className="text-white" />
                </div>

                <h3 className="text-3xl font-bold text-slate-900 mb-4">
                  All Companies Documentary
                </h3>

                <p className="text-slate-600 text-lg mb-6 flex-grow">
                  Complete access to manage inventory, operations, and reporting across all company divisions.
                </p>

                <div className="space-y-3 mb-8">
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
                    <p className="text-slate-700">Company, Product & Warehouse Management</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
                    <p className="text-slate-700">PI, PO & Stock Operations</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
                    <p className="text-slate-700">Payment Tracking & P&L Reports</p>
                  </div>
                </div>

                <Button className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-lg py-6 group-hover:shadow-lg group-hover:shadow-blue-600/50">
                  Access Full System
                  <ArrowRight className="ml-2" size={20} />
                </Button>
              </div>
            </div>

            {/* DNS Documentary */}
            <div
              className="group bg-white rounded-3xl p-8 hover:shadow-2xl hover:shadow-emerald-600/20 transition-all duration-300 cursor-pointer border-2 border-transparent hover:border-emerald-500"
              onClick={() => navigate('/login?section=dns')}
              data-testid="dns-section"
            >
              <div className="flex flex-col h-full">
                <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-xl">
                  <FileStack size={48} className="text-white" />
                </div>

                <h3 className="text-3xl font-bold text-slate-900 mb-4">
                  DNS Documentary
                </h3>

                <p className="text-slate-600 text-lg mb-6 flex-grow">
                  Focused workspace for DNS operations with essential modules for streamlined workflow.
                </p>

                <div className="space-y-3 mb-8">
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 mt-2"></div>
                    <p className="text-slate-700">Product Master Management</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 mt-2"></div>
                    <p className="text-slate-700">Performa Invoice & Purchase Orders</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 mt-2"></div>
                    <p className="text-slate-700">Payment Tracking & Reports</p>
                  </div>
                </div>

                <Button className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white text-lg py-6 group-hover:shadow-lg group-hover:shadow-emerald-600/50">
                  Access DNS System
                  <ArrowRight className="ml-2" size={20} />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
