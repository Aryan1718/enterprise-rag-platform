import { useEffect } from "react";

export type ToastState = {
  id: number;
  message: string;
  type: "success" | "error";
};

type ToastProps = {
  toast: ToastState | null;
  onClose: () => void;
  durationMs?: number;
};

export default function Toast({ toast, onClose, durationMs = 3200 }: ToastProps) {
  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeout = window.setTimeout(onClose, durationMs);
    return () => window.clearTimeout(timeout);
  }, [durationMs, onClose, toast]);

  if (!toast) {
    return null;
  }

  const isError = toast.type === "error";

  return (
    <div className="pointer-events-none fixed bottom-4 left-1/2 z-50 w-[92%] max-w-md -translate-x-1/2">
      <div
        className={`pointer-events-auto rounded-xl border px-4 py-3 text-sm shadow-glow ${
          isError
            ? "border-app-danger/50 bg-app-surface text-red-300"
            : "border-app-accent/60 bg-app-surface text-app-text"
        }`}
        role="status"
        aria-live="polite"
      >
        <div className="flex items-start justify-between gap-3">
          <p>{toast.message}</p>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-0.5 text-app-muted transition hover:bg-app-elevated hover:text-app-text"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
