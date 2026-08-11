import React from "react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Safe error logging - only log message and stack, not full objects
    console.error("ErrorBoundary caught an error:", error?.message || String(error));
    console.error("Component stack:", errorInfo?.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: "2rem",
          background: "#1e293b",
          border: "1px solid #ef4444",
          borderRadius: "0.5rem",
          textAlign: "center",
          color: "#fff"
        }}>
          <h3 style={{ color: "#ef4444", marginBottom: "0.5rem" }}>
            Something went wrong
          </h3>
          <p style={{ fontSize: "0.9rem", color: "#94a3b8" }}>
            {typeof this.props.fallback === "string"
              ? this.props.fallback
              : React.isValidElement(this.props.fallback)
              ? this.props.fallback
              : "An error occurred while loading this component."}
          </p>
          <div style={{
            fontSize: "0.8rem",
            color: "#ef4444",
            marginTop: "0.5rem",
            fontFamily: "monospace",
            wordBreak: "break-all"
          }}>
            {this.state.error?.message || String(this.state.error || "")}
          </div>
          {this.props.onRetry && (
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                this.props.onRetry();
              }}
              style={{
                marginTop: "1rem",
                padding: "0.5rem 1rem",
                background: "#3b82f6",
                color: "#fff",
                border: "none",
                borderRadius: "0.25rem",
                cursor: "pointer"
              }}
            >
              Retry
            </button>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
