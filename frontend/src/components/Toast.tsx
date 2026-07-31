"use client";

import { useEffect } from "react";


export type ToastTone = "success" | "error" | "info";

export type ToastMessage = {
  id: number;
  message: string;
  tone: ToastTone;
};

type ToastProps = {
  toast: ToastMessage | null;
  onDismiss: () => void;
};

const toneClasses: Record<ToastTone, string> = {
  success: "border-emerald-400/30 bg-emerald-950/95 text-emerald-100",
  error: "border-red-400/30 bg-red-950/95 text-red-100",
  info: "border-indigo-400/30 bg-indigo-950/95 text-indigo-100",
};

const toneIcons: Record<ToastTone, string> = {
  success: "✓",
  error: "!",
  info: "i",
};

export default function Toast({ toast, onDismiss }: ToastProps) {
  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeoutId = window.setTimeout(onDismiss, 3200);
    return () => window.clearTimeout(timeoutId);
  }, [toast, onDismiss]);

  if (!toast) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed right-4 top-20 z-50 w-[calc(100%-2rem)] max-w-sm sm:right-6 sm:top-24"
    >
      <div
        className={`pointer-events-auto flex items-start gap-3 rounded-2xl border px-4 py-3 shadow-2xl shadow-black/30 backdrop-blur ${toneClasses[toast.tone]}`}
      >
        <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full border border-current/30 text-xs font-bold">
          {toneIcons[toast.tone]}
        </span>
        <p className="min-w-0 flex-1 text-sm leading-6">{toast.message}</p>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss notification"
          className="rounded-md px-1 text-current/60 transition hover:bg-white/10 hover:text-current"
        >
          ×
        </button>
      </div>
    </div>
  );
}