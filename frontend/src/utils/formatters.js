/**
 * Format a number as currency using simplified Indian Locale (e.g., 1,00,000.00)
 * Uses toLocaleString('en-IN') but ensures 2 decimal places.
 * @param {number|string} amount - The amount to format
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (amount) => {
    const num = Number(amount);
    if (isNaN(num)) return '0.00';

    return num.toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
};

/**
 * Format a number without decimals (unless necessary) using Indian Locale (e.g., 1,00,000)
 * Useful for quantities.
 * @param {number|string} value - The value to format
 * @returns {string} Formatted number string
 */
export const formatNumber = (value) => {
    const num = Number(value);
    if (isNaN(num)) return '0';

    return num.toLocaleString('en-IN');
};
