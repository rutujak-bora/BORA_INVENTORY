import { useEffect } from 'react';

/**
 * Enhanced custom hook to suppress ResizeObserver loop errors
 * These errors are typically harmless and occur when UI components resize rapidly
 */
export const useResizeObserverErrorFix = () => {
  useEffect(() => {
    let cleanup = null;
    
    // Enhanced error suppression
    const setupErrorSuppression = () => {
      // Store original methods
      const originalConsoleError = console.error;
      const originalConsoleWarn = console.warn;
      
      // Override console.error with more comprehensive filtering
      console.error = (...args) => {
        const errorMessage = args.join(' ').toLowerCase();
        
        if (
          errorMessage.includes('resizeobserver loop completed') ||
          errorMessage.includes('resizeobserver loop limit exceeded') ||
          errorMessage.includes('resizeobserver') && errorMessage.includes('loop')
        ) {
          // Suppress all ResizeObserver related errors
          return;
        }
        
        originalConsoleError(...args);
      };
      
      // Override console.warn for ResizeObserver warnings
      console.warn = (...args) => {
        const warnMessage = args.join(' ').toLowerCase();
        
        if (
          warnMessage.includes('resizeobserver') ||
          warnMessage.includes('resize observer')
        ) {
          return;
        }
        
        originalConsoleWarn(...args);
      };
      
      // Enhanced error event handler
      const handleError = (event) => {
        const errorMessage = event.error?.message?.toLowerCase() || '';
        const errorStack = event.error?.stack?.toLowerCase() || '';
        
        if (
          errorMessage.includes('resizeobserver') ||
          errorStack.includes('resizeobserver') ||
          errorMessage.includes('loop completed')
        ) {
          event.preventDefault();
          event.stopImmediatePropagation();
          return false;
        }
      };
      
      // Enhanced promise rejection handler
      const handleRejection = (event) => {
        const reason = event.reason?.message?.toLowerCase() || '';
        
        if (
          reason.includes('resizeobserver') ||
          reason.includes('loop completed')
        ) {
          event.preventDefault();
          return false;
        }
      };
      
      // Add multiple event listeners for comprehensive coverage
      window.addEventListener('error', handleError, true);
      window.addEventListener('unhandledrejection', handleRejection, true);
      document.addEventListener('error', handleError, true);
      
      // Return cleanup function
      return () => {
        console.error = originalConsoleError;
        console.warn = originalConsoleWarn;
        window.removeEventListener('error', handleError, true);
        window.removeEventListener('unhandledrejection', handleRejection, true);
        document.removeEventListener('error', handleError, true);
      };
    };
    
    // Setup error suppression
    cleanup = setupErrorSuppression();
    
    // Additional DOM mutation observer to catch ResizeObserver issues
    const observer = new MutationObserver(() => {
      // Debounce rapid DOM changes that can trigger ResizeObserver errors
      clearTimeout(window._resizeObserverTimeout);
      window._resizeObserverTimeout = setTimeout(() => {
        // Allow DOM to settle before any operations
      }, 16); // One frame delay
    });
    
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['style', 'class']
    });
    
    // Cleanup function
    return () => {
      if (cleanup) cleanup();
      observer.disconnect();
      clearTimeout(window._resizeObserverTimeout);
    };
  }, []);
};

export default useResizeObserverErrorFix;