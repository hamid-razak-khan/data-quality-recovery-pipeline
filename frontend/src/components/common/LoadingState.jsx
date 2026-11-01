import React from 'react';
import { Loader2 } from 'lucide-react';

export default function LoadingState({ message = 'Loading pipeline data...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
      <p className="text-sm font-medium text-slate-500">{message}</p>
    </div>
  );
}
