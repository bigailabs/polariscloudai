"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

type ToastType = "success" | "error" | "warning" | "info";

type Toast = {
  id: string;
  type: ToastType;
  message: string;
  createdAt: number;
};

type ToastApi = {
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
};

const TOAST_DURATION = 4000;

const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((prev) => [{ id, type, message, createdAt: Date.now() }, ...prev]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const api: ToastApi = {
    success: useCallback((msg: string) => addToast("success", msg), [addToast]),
    error: useCallback((msg: string) => addToast("error", msg), [addToast]),
    warning: useCallback((msg: string) => addToast("warning", msg), [addToast]),
    info: useCallback((msg: string) => addToast("info", msg), [addToast]),
  };

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onDismiss={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

const typeStyles: Record<
  ToastType,
  { bg: string; border: string; text: string; icon: string; progress: string }
> = {
  success: {
    bg: "bg-white",
    border: "border-fern/30",
    text: "text-fern",
    icon: "\u2713",
    progress: "bg-fern",
  },
  error: {
    bg: "bg-white",
    border: "border-red-200",
    text: "text-red-700",
    icon: "\u2717",
    progress: "bg-red-500",
  },
  warning: {
    bg: "bg-white",
    border: "border-copper/30",
    text: "text-copper",
    icon: "!",
    progress: "bg-copper",
  },
  info: {
    bg: "bg-white",
    border: "border-forest/20",
    text: "text-forest",
    icon: "i",
    progress: "bg-forest",
  },
};

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: () => void;
}) {
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const style = typeStyles[toast.type];

  useEffect(() => {
    // Trigger slide-in on next frame
    requestAnimationFrame(() => setVisible(true));

    timerRef.current = setTimeout(() => {
      setExiting(true);
      setTimeout(onDismiss, 200);
    }, TOAST_DURATION);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [onDismiss]);

  function handleClose() {
    if (timerRef.current) clearTimeout(timerRef.current);
    setExiting(true);
    setTimeout(onDismiss, 200);
  }

  return (
    <div
      className={`pointer-events-auto relative w-80 overflow-hidden rounded-xl border ${style.bg} ${style.border} shadow-lg transition-all duration-200 ${
        visible && !exiting
          ? "translate-x-0 opacity-100"
          : "translate-x-8 opacity-0"
      }`}
    >
      <div className="flex items-start gap-3 px-4 py-3">
        {/* Icon */}
        <span
          className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white ${style.progress}`}
        >
          {style.icon}
        </span>

        {/* Message */}
        <p className="flex-1 text-sm font-medium text-forest-dark">
          {toast.message}
        </p>

        {/* Close */}
        <button
          onClick={handleClose}
          className="shrink-0 text-forest-dark/30 hover:text-forest-dark/60 transition-colors"
          aria-label="Close notification"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-0.5 w-full bg-mist">
        <div
          className={`h-full ${style.progress} transition-none`}
          style={{
            animation: `toast-progress ${TOAST_DURATION}ms linear forwards`,
          }}
        />
      </div>

      <style>{`
        @keyframes toast-progress {
          from { width: 100%; }
          to { width: 0%; }
        }
      `}</style>
    </div>
  );
}
