import React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export default function Toast({ toast, onClose }) {
  if (!toast) return null;

  const { type = 'success', message, title } = toast;

  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />,
    error: <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />,
    info: <Info className="w-5 h-5 text-blue-600 shrink-0" />,
  };

  const borders = {
    success: 'border-emerald-200 bg-emerald-50/95 text-emerald-900',
    error: 'border-rose-200 bg-rose-50/95 text-rose-900',
    info: 'border-blue-200 bg-blue-50/95 text-blue-900',
  };

  return (
    <div className="fixed bottom-4 right-4 left-4 sm:left-auto sm:right-5 sm:bottom-5 z-50 sm:max-w-md animate-in fade-in slide-in-from-bottom-5 duration-200 pointer-events-auto">
      <div className={`flex items-start gap-3 p-3.5 sm:p-4 rounded-xl border shadow-xl backdrop-blur-xs ${borders[type] || borders.info}`}>
        {icons[type] || icons.info}
        <div className="flex-1 text-xs sm:text-sm min-w-0">
          {title && <p className="font-semibold text-xs sm:text-sm">{title}</p>}
          <p className="opacity-90 break-words mt-0.5">{message}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md opacity-60 hover:opacity-100 transition-opacity shrink-0"
          aria-label="Dismiss notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
