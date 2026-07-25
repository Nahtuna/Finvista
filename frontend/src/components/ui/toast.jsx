import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "info", duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, message, type }]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="toast-container" style={{
        position: "fixed",
        bottom: "1.5rem",
        right: "1.5rem",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
        maxWidth: "380px"
      }}>
        {toasts.map(toast => {
          let bg = "rgba(30, 41, 59, 0.95)";
          let border = "rgba(255, 255, 255, 0.1)";
          let icon = <Info color="#3b82f6" size={18} />;

          if (toast.type === "success") {
            bg = "rgba(6, 78, 59, 0.95)";
            border = "rgba(16, 185, 129, 0.4)";
            icon = <CheckCircle2 color="#10b981" size={18} />;
          } else if (toast.type === "error") {
            bg = "rgba(127, 29, 29, 0.95)";
            border = "rgba(239, 68, 68, 0.4)";
            icon = <AlertCircle color="#ef4444" size={18} />;
          }

          return (
            <div
              key={toast.id}
              className="toast-item"
              style={{
                background: bg,
                border: `1px solid ${border}`,
                borderRadius: "0.5rem",
                padding: "0.85rem 1rem",
                color: "#fff",
                boxShadow: "0 10px 15px -3px rgba(0,0,0,0.5)",
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                fontSize: "0.875rem",
                lineHeight: "1.25",
                animation: "toastSlideIn 0.25s ease-out forwards"
              }}
            >
              <div style={{ flexShrink: 0 }}>{icon}</div>
              <div style={{ flexGrow: 1 }}>{toast.message}</div>
              <button
                onClick={() => removeToast(toast.id)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "rgba(255,255,255,0.6)",
                  cursor: "pointer",
                  padding: "0.2rem",
                  display: "flex",
                  alignItems: "center"
                }}
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
