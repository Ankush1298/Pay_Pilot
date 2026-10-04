"use client";

import { createContext, useContext, useState, ReactNode } from "react";

type ToastType = "ok" | "warn" | "crit" | "info";

interface ToastMsg {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextType {
  show: (type: ToastType, message: string) => void;
}

const ToastContext = createContext<ToastContextType>({ show: () => {} });

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMsg[]>([]);

  const show = (type: ToastType, message: string) => {
    const id = Math.random().toString(36).substring(7);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div className="toast-area">
        {toasts.map((t) => (
          <div key={t.id} className="toast" style={{ borderColor: 
            t.type === "crit" ? "var(--danger)" : 
            t.type === "warn" ? "var(--warn)" : 
            t.type === "ok" ? "var(--success)" : "var(--info)"
          }}>
            <span style={{ color: 
              t.type === "crit" ? "var(--danger)" : 
              t.type === "warn" ? "var(--warn)" : 
              t.type === "ok" ? "var(--success)" : "var(--info)"
            }}>
              {t.type === "crit" ? "✕" : t.type === "warn" ? "⚠" : t.type === "ok" ? "✓" : "i"}
            </span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
