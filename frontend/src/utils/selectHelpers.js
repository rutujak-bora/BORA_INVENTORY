/**
 * Helper utilities for Select components to prevent ResizeObserver errors
 */

/**
 * Enhanced onValueChange handler that prevents ResizeObserver errors
 * Uses requestAnimationFrame for smoother DOM updates
 */
export const createSafeOnValueChange = (setter, field, formData) => {
  return (value) => {
    // Use requestAnimationFrame for smooth DOM updates
    requestAnimationFrame(() => {
      // Add a small delay to prevent rapid state changes
      setTimeout(() => {
        if (typeof setter === 'function') {
          if (field && formData) {
            setter({ ...formData, [field]: value });
          } else {
            setter(value);
          }
        }
      }, 0);
    });
  };
};

/**
 * Safe props for Select components
 */
export const getSafeSelectProps = (options = {}) => {
  return {
    className: options.className || '',
    ...options,
    // Add props that help prevent ResizeObserver issues
    onOpenChange: (open) => {
      // Debounce open/close events
      if (options.onOpenChange) {
        requestAnimationFrame(() => {
          options.onOpenChange(open);
        });
      }
    }
  };
};

/**
 * Safe props for SelectContent components
 */
export const getSafeSelectContentProps = (options = {}) => {
  return {
    className: `max-h-60 overflow-y-auto ${options.className || ''}`,
    ...options,
    // Prevent layout shifts
    sideOffset: options.sideOffset || 4,
    align: options.align || 'start'
  };
};

/**
 * Debounced function creator
 */
export const createDebounced = (func, delay = 16) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(null, args), delay);
  };
};

export default {
  createSafeOnValueChange,
  getSafeSelectProps,
  getSafeSelectContentProps,
  createDebounced
};