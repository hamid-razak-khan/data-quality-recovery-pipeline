import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export default function Modal({ isOpen, onClose, title, children, maxWidth = 'max-w-2xl' }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Lock body scroll while modal is active
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/50 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="flex min-h-full items-center justify-center p-2.5 sm:p-4">
        <div className={`relative w-full ${maxWidth} max-w-[96vw] sm:max-w-2xl transform overflow-hidden rounded-xl bg-white shadow-2xl transition-all border border-slate-200 my-auto`}>
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-200 px-4 sm:px-6 py-3 sm:py-4 bg-slate-50/50">
            <h3 className="text-base sm:text-lg font-semibold text-slate-900 truncate pr-2">{title}</h3>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-600 transition-colors shrink-0"
              aria-label="Close dialog"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="px-4 sm:px-6 py-4 max-h-[85vh] sm:max-h-[80vh] overflow-y-auto">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
