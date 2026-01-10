import React from 'react';
import { FileQuestion } from 'lucide-react';

const PlaceholderPage = ({ title, description }) => {
  return (
    <div className="flex flex-col items-center justify-center h-96 text-center">
      <div className="w-20 h-20 rounded-full bg-slate-100 flex items-center justify-center mb-4">
        <FileQuestion size={40} className="text-slate-400" />
      </div>
      <h2 className="text-2xl font-bold text-slate-900 mb-2">{title}</h2>
      <p className="text-slate-600 max-w-md">{description || 'This module is under construction.'}</p>
    </div>
  );
};

export default PlaceholderPage;
