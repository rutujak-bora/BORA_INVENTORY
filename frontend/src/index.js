// ==================== ABSOLUTE FIRST: SUPPRESS RESIZEOBSERVER ERRORS ====================
// This MUST be the very first code that runs in the entire application
(function() {
  'use strict';
  
  // Store originals
  const originalError = console.error;
  const originalWarn = console.warn;
  
  // Override console.error - MOST AGGRESSIVE VERSION
  console.error = function(...args) {
    const firstArg = String(args[0] || '');
    if (
      firstArg.includes('ResizeObserver') ||
      firstArg.includes('loop completed') ||
      firstArg.includes('loop limit')
    ) {
      return; // Completely suppress
    }
    originalError.apply(console, args);
  };
  
  // Override console.warn
  console.warn = function(...args) {
    const firstArg = String(args[0] || '');
    if (firstArg.includes('ResizeObserver')) {
      return; // Completely suppress
    }
    originalWarn.apply(console, args);
  };
  
  // Global error handler - CAPTURE PHASE (highest priority)
  window.addEventListener('error', function(event) {
    const msg = String(event.message || event.error?.message || '');
    if (msg.includes('ResizeObserver') || msg.includes('loop completed')) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      return true;
    }
  }, true); // USE CAPTURE PHASE
  
  // Global rejection handler
  window.addEventListener('unhandledrejection', function(event) {
    const msg = String(event.reason?.message || event.reason || '');
    if (msg.includes('ResizeObserver') || msg.includes('loop completed')) {
      event.preventDefault();
      return true;
    }
  }, true); // USE CAPTURE PHASE
  
  console.log('✅ ResizeObserver suppression active (FIRST IN APPLICATION)');
})();

import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
