/**
 * Comprehensive ResizeObserver Error Fix Utility
 * This utility provides multiple layers of protection against ResizeObserver loop errors
 */

class ResizeObserverErrorSuppressor {
  constructor() {
    this.isInitialized = false;
    this.originalMethods = {};
    this.eventListeners = [];
    this.init();
  }

  init() {
    if (this.isInitialized) return;
    
    this.suppressConsoleErrors();
    this.suppressWindowErrors();
    this.suppressResizeObserverDirectly();
    this.isInitialized = true;
    
    console.log('ResizeObserver error suppression initialized');
  }

  suppressConsoleErrors() {
    // Store original console methods
    this.originalMethods.error = console.error;
    this.originalMethods.warn = console.warn;
    
    // Override console.error
    console.error = (...args) => {
      if (this.isResizeObserverError(args)) return;
      this.originalMethods.error(...args);
    };
    
    // Override console.warn
    console.warn = (...args) => {
      if (this.isResizeObserverError(args)) return;
      this.originalMethods.warn(...args);
    };
  }

  suppressWindowErrors() {
    const errorHandler = (event) => {
      if (this.isResizeObserverErrorEvent(event)) {
        event.preventDefault();
        event.stopImmediatePropagation();
        return false;
      }
    };

    const rejectionHandler = (event) => {
      if (this.isResizeObserverRejection(event)) {
        event.preventDefault();
        return false;
      }
    };

    // Add event listeners with capture phase
    window.addEventListener('error', errorHandler, true);
    window.addEventListener('unhandledrejection', rejectionHandler, true);
    document.addEventListener('error', errorHandler, true);

    this.eventListeners.push(
      () => window.removeEventListener('error', errorHandler, true),
      () => window.removeEventListener('unhandledrejection', rejectionHandler, true),
      () => document.removeEventListener('error', errorHandler, true)
    );
  }

  suppressResizeObserverDirectly() {
    // Monkey patch ResizeObserver itself
    if (typeof window.ResizeObserver !== 'undefined') {
      const OriginalResizeObserver = window.ResizeObserver;
      
      window.ResizeObserver = class extends OriginalResizeObserver {
        constructor(callback) {
          const wrappedCallback = (entries, observer) => {
            try {
              callback(entries, observer);
            } catch (error) {
              if (this.isResizeObserverCallbackError(error)) {
                // Suppress ResizeObserver callback errors
                return;
              }
              throw error;
            }
          };
          
          super(wrappedCallback);
        }
      };
      
      // Preserve static methods if any
      Object.setPrototypeOf(window.ResizeObserver, OriginalResizeObserver);
      Object.defineProperty(window.ResizeObserver, 'name', {
        value: 'ResizeObserver'
      });
    }
  }

  isResizeObserverError(args) {
    const message = args.join(' ').toLowerCase();
    return (
      message.includes('resizeobserver loop completed') ||
      message.includes('resizeobserver loop limit exceeded') ||
      message.includes('resizeobserver') && message.includes('loop') ||
      message.includes('resize observer') && message.includes('loop')
    );
  }

  isResizeObserverErrorEvent(event) {
    if (!event.error) return false;
    
    const message = event.error.message?.toLowerCase() || '';
    const stack = event.error.stack?.toLowerCase() || '';
    
    return (
      message.includes('resizeobserver') ||
      stack.includes('resizeobserver') ||
      message.includes('loop completed') ||
      message.includes('loop limit exceeded')
    );
  }

  isResizeObserverRejection(event) {
    if (!event.reason) return false;
    
    const message = event.reason.message?.toLowerCase() || '';
    return (
      message.includes('resizeobserver') ||
      message.includes('loop completed') ||
      message.includes('loop limit exceeded')
    );
  }

  isResizeObserverCallbackError(error) {
    const message = error.message?.toLowerCase() || '';
    const stack = error.stack?.toLowerCase() || '';
    
    return (
      message.includes('resizeobserver') ||
      stack.includes('resizeobserver') ||
      message.includes('loop completed')
    );
  }

  destroy() {
    // Restore original console methods
    if (this.originalMethods.error) {
      console.error = this.originalMethods.error;
    }
    if (this.originalMethods.warn) {
      console.warn = this.originalMethods.warn;
    }
    
    // Remove event listeners
    this.eventListeners.forEach(cleanup => cleanup());
    this.eventListeners = [];
    
    this.isInitialized = false;
  }
}

// Create and initialize global instance
let globalSuppressor = null;

export const initResizeObserverFix = () => {
  if (!globalSuppressor) {
    globalSuppressor = new ResizeObserverErrorSuppressor();
  }
  return globalSuppressor;
};

export const destroyResizeObserverFix = () => {
  if (globalSuppressor) {
    globalSuppressor.destroy();
    globalSuppressor = null;
  }
};

// Auto-initialize when imported
initResizeObserverFix();

export default {
  init: initResizeObserverFix,
  destroy: destroyResizeObserverFix
};