"use client";

import { useToastState, pauseToast, resumeToast, Toast } from "@/hooks/use-toast";
import { Check, Info, X } from "lucide-react";

const iconMap: Record<Toast["type"], React.ReactNode> = {
  success: <Check className="size-4 text-emerald-400" />,
  info: <Info className="size-4 text-blue-400" />,
  error: <X className="size-4 text-red-400" />,
};

export function ToastContainer() {
  const toasts = useToastState();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-card border border-border shadow-lg animate-in slide-in-from-bottom-2 fade-in duration-200 text-sm cursor-default"
          onMouseEnter={() => pauseToast(toast.id)}
          onMouseLeave={() => resumeToast(toast.id)}
        >
          {iconMap[toast.type]}
          <span>{toast.message}</span>
        </div>
      ))}
    </div>
  );
}
