import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Toaster } from './components/ui/sonner';
import Layout from './components/Layout';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Companies from './pages/Companies';
import Products from './pages/Products';
import Warehouses from './pages/Warehouses';
import Banks from './pages/Banks';
import PlaceholderPage from './pages/PlaceholderPage';
import PerformaInvoice from './pages/PerformaInvoice';
import PurchaseOrder from './pages/PurchaseOrder';
import InwardStock from './pages/InwardStock';
import OutwardStock from './pages/OutwardStockNew';
import StockSummary from './pages/StockSummaryNew';
import CustomerManagement from './pages/CustomerManagement';
import CustomerTracking from './pages/CustomerTracking';
import PurchaseAnalysis from './pages/PurchaseAnalysis';
import PaymentTracking from './pages/PaymentTracking';
import ExpenseCalculation from './pages/ExpenseCalculation';
import PLReporting from './pages/PLReporting';
import ErrorBoundary from './components/ErrorBoundary';
import './utils/resizeObserverFix';
import '@/App.css';

// Comprehensive ResizeObserver error suppression
const suppressResizeObserverErrors = () => {
  // Store original methods
  const originalError = console.error;
  const originalWarn = console.warn;

  // Override console.error - MORE AGGRESSIVE
  console.error = (...args) => {
    // Check first argument (most common case)
    const firstArg = args[0];
    if (firstArg) {
      const argStr = String(firstArg);
      if (
        argStr.includes('ResizeObserver') ||
        argStr.includes('resize observer') ||
        argStr.includes('loop completed') ||
        argStr.includes('loop limit exceeded')
      ) {
        // Completely suppress - don't log at all
        return;
      }
    }

    // Check if any argument mentions ResizeObserver
    const hasResizeObserverError = args.some(arg => {
      if (arg && typeof arg === 'object') {
        const argStr = JSON.stringify(arg).toLowerCase();
        return argStr.includes('resizeobserver') || argStr.includes('loop completed');
      }
      if (arg) {
        const argStr = String(arg).toLowerCase();
        return argStr.includes('resizeobserver') || argStr.includes('loop completed');
      }
      return false;
    });

    if (hasResizeObserverError) {
      return; // Suppress completely
    }

    originalError(...args);
  };

  // Override console.warn for ResizeObserver warnings
  console.warn = (...args) => {
    const hasResizeObserverWarning = args.some(arg => {
      if (arg) {
        const argStr = String(arg).toLowerCase();
        return argStr.includes('resizeobserver');
      }
      return false;
    });

    if (hasResizeObserverWarning) {
      return; // Suppress completely
    }

    originalWarn(...args);
  };

  // Global error event handler - HIGHEST PRIORITY
  const handleError = (event) => {
    if (event.error) {
      const errorMessage = String(event.error.message || event.error || '').toLowerCase();
      if (
        errorMessage.includes('resizeobserver') ||
        errorMessage.includes('loop completed') ||
        errorMessage.includes('loop limit')
      ) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        return true; // Mark as handled
      }
    }
    // Check event.message as well
    if (event.message) {
      const message = String(event.message).toLowerCase();
      if (message.includes('resizeobserver') || message.includes('loop completed')) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        return true;
      }
    }
  };

  // Global unhandled promise rejection handler
  const handleRejection = (event) => {
    if (event.reason) {
      const reasonMessage = String(event.reason.message || event.reason || '').toLowerCase();
      if (
        reasonMessage.includes('resizeobserver') ||
        reasonMessage.includes('loop completed') ||
        reasonMessage.includes('loop limit')
      ) {
        event.preventDefault();
        return true;
      }
    }
  };

  // Add global event listeners with capture phase (HIGHEST PRIORITY)
  window.addEventListener('error', handleError, true);
  window.addEventListener('unhandledrejection', handleRejection, true);
  document.addEventListener('error', handleError, true);

  return () => {
    // Cleanup function
    console.error = originalError;
    console.warn = originalWarn;
    window.removeEventListener('error', handleError, true);
    window.removeEventListener('unhandledrejection', handleRejection, true);
    document.removeEventListener('error', handleError, true);
  };
};

// Initialize global ResizeObserver error suppression IMMEDIATELY
suppressResizeObserverErrors();

const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" />;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/companies"
        element={
          <PrivateRoute>
            <Layout>
              <Companies />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/products"
        element={
          <PrivateRoute>
            <Layout>
              <Products />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/warehouses"
        element={
          <PrivateRoute>
            <Layout>
              <Warehouses />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/banks"
        element={
          <PrivateRoute>
            <Layout>
              <Banks />
            </Layout>
          </PrivateRoute>
        }
      />

      <Route
        path="/pi"
        element={
          <PrivateRoute>
            <Layout>
              <PerformaInvoice />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/po"
        element={
          <PrivateRoute>
            <Layout>
              <PurchaseOrder />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/inward"
        element={
          <PrivateRoute>
            <Layout>
              <InwardStock />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/outward"
        element={
          <PrivateRoute>
            <Layout>
              <OutwardStock />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/stock-summary"
        element={
          <PrivateRoute>
            <Layout>
              <StockSummary />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/customer-management"
        element={
          <PrivateRoute>
            <Layout>
              <CustomerManagement />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/customer-tracking"
        element={
          <PrivateRoute>
            <Layout>
              <CustomerTracking />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/purchase-analysis"
        element={
          <PrivateRoute>
            <Layout>
              <PurchaseAnalysis />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/payments"
        element={
          <PrivateRoute>
            <Layout>
              <PaymentTracking />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/expenses"
        element={
          <PrivateRoute>
            <Layout>
              <ExpenseCalculation />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/pl-report"
        element={
          <PrivateRoute>
            <Layout>
              <PLReporting />
            </Layout>
          </PrivateRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
          <Toaster />
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
