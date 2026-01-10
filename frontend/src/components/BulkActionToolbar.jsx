import React from 'react';
import { Button } from './ui/button';
import { Download, Trash2, X } from 'lucide-react';

/**
 * Reusable Bulk Action Toolbar
 * Shows when items are selected, provides bulk delete and export actions
 */
const BulkActionToolbar = ({ 
  selectedCount, 
  onClearSelection, 
  onBulkDelete, 
  onExportCSV, 
  onExportExcel,
  disableDelete = false 
}) => {
  if (selectedCount === 0) return null;

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <span className="font-semibold text-blue-900">
          {selectedCount} item{selectedCount > 1 ? 's' : ''} selected
        </span>
        <Button
          size="sm"
          variant="ghost"
          onClick={onClearSelection}
          className="text-blue-600 hover:text-blue-800"
        >
          <X className="h-4 w-4 mr-1" />
          Clear Selection
        </Button>
      </div>
      
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={onExportCSV}
          className="bg-white"
        >
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
        
        <Button
          size="sm"
          variant="outline"
          onClick={onExportExcel}
          className="bg-white"
        >
          <Download className="h-4 w-4 mr-2" />
          Export Excel
        </Button>
        
        {!disableDelete && (
          <Button
            size="sm"
            variant="destructive"
            onClick={onBulkDelete}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete Selected
          </Button>
        )}
      </div>
    </div>
  );
};

export default BulkActionToolbar;
