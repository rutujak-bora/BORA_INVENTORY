import * as XLSX from 'xlsx';

/**
 * Utility functions for exporting data to CSV and Excel
 */

/**
 * Export data to CSV format
 * @param {Array} data - Array of objects to export
 * @param {string} filename - Name of the file (without extension)
 */
export const exportToCSV = (data, filename = 'export') => {
  if (!data || data.length === 0) {
    alert('No data to export');
    return;
  }

  // Convert data to CSV format
  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row => 
      headers.map(header => {
        const value = row[header];
        // Handle values with commas or quotes
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      }).join(',')
    )
  ].join('\n');

  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

/**
 * Export data to Excel format
 * @param {Array} data - Array of objects to export
 * @param {string} filename - Name of the file (without extension)
 * @param {string} sheetName - Name of the sheet
 */
export const exportToExcel = (data, filename = 'export', sheetName = 'Data') => {
  if (!data || data.length === 0) {
    alert('No data to export');
    return;
  }

  // Create worksheet
  const ws = XLSX.utils.json_to_sheet(data);
  
  // Create workbook
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  
  // Generate file name with timestamp
  const timestamp = new Date().toISOString().split('T')[0];
  const fileName = `${filename}_${timestamp}.xlsx`;
  
  // Save file
  XLSX.writeFile(wb, fileName);
};

/**
 * Format data for export by removing internal IDs and formatting dates
 * @param {Array} data - Raw data from API
 * @param {Object} fieldMapping - Map of field names to display names
 * @returns {Array} Formatted data ready for export
 */
export const formatDataForExport = (data, fieldMapping = {}) => {
  return data.map(item => {
    const formattedItem = {};
    
    Object.keys(item).forEach(key => {
      // Skip internal fields
      if (key === '_id' || key === 'id' || key === 'created_by' || key === 'updated_by') {
        return;
      }
      
      // Use mapped name or original key
      const displayKey = fieldMapping[key] || key;
      
      // Format dates
      if (key.includes('_at') || key.includes('date')) {
        const dateValue = item[key];
        if (dateValue) {
          formattedItem[displayKey] = new Date(dateValue).toLocaleDateString();
        } else {
          formattedItem[displayKey] = '';
        }
      } else {
        formattedItem[displayKey] = item[key];
      }
    });
    
    return formattedItem;
  });
};
