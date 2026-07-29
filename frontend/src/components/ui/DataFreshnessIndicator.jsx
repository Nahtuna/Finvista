import React, { useState, useEffect } from "react";
import { Clock, RefreshCw, AlertCircle, CheckCircle } from "lucide-react";

export function DataFreshnessIndicator({ 
  timestamp, 
  thresholds = { fresh: 60, stale: 300, expired: 3600 },
  onRefresh,
  showLabel = true,
  compact = false 
}) {
  const [freshness, setFreshness] = useState({
    status: "unknown",
    ageSeconds: 0,
    ageHuman: "0s",
    isFresh: false
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    if (!timestamp) return;

    const calculateFreshness = () => {
      const now = new Date();
      const dataTime = new Date(timestamp);
      const ageSeconds = (now - dataTime) / 1000;

      let status = "unknown";
      if (ageSeconds <= thresholds.fresh) {
        status = "fresh";
      } else if (ageSeconds <= thresholds.stale) {
        status = "stale";
      } else if (ageSeconds <= thresholds.expired) {
        status = "warning";
      } else {
        status = "expired";
      }

      const ageHuman = ageSeconds < 60 
        ? `${Math.round(ageSeconds)}s`
        : ageSeconds < 3600
        ? `${Math.round(ageSeconds / 60)}m`
        : `${Math.round(ageSeconds / 3600)}h`;

      setFreshness({
        status,
        ageSeconds,
        ageHuman,
        isFresh: ageSeconds <= thresholds.fresh
      });
    };

    calculateFreshness();
    const interval = setInterval(calculateFreshness, 1000); // Update every second

    return () => clearInterval(interval);
  }, [timestamp, thresholds]);

  const handleRefresh = async () => {
    if (onRefresh && !isRefreshing) {
      setIsRefreshing(true);
      try {
        await onRefresh();
      } finally {
        setIsRefreshing(false);
      }
    }
  };

  const getStatusConfig = () => {
    switch (freshness.status) {
      case "fresh":
        return {
          color: "#10b981",
          bgColor: "rgba(16, 185, 129, 0.1)",
          icon: CheckCircle,
          label: "Fresh"
        };
      case "stale":
        return {
          color: "#f59e0b",
          bgColor: "rgba(245, 158, 11, 0.1)",
          icon: Clock,
          label: "Stale"
        };
      case "warning":
        return {
          color: "#f97316",
          bgColor: "rgba(249, 115, 22, 0.1)",
          icon: AlertCircle,
          label: "Warning"
        };
      case "expired":
        return {
          color: "#ef4444",
          bgColor: "rgba(239, 68, 68, 0.1)",
          icon: AlertCircle,
          label: "Expired"
        };
      default:
        return {
          color: "#6b7280",
          bgColor: "rgba(107, 114, 128, 0.1)",
          icon: Clock,
          label: "Unknown"
        };
    }
  };

  const config = getStatusConfig();
  const StatusIcon = config.icon;

  if (compact) {
    return (
      <div 
        style={{ 
          display: "flex", 
          alignItems: "center", 
          gap: "0.35rem",
          padding: "0.25rem 0.5rem",
          borderRadius: "0.25rem",
          background: config.bgColor,
          color: config.color,
          fontSize: "0.72rem",
          fontWeight: "600"
        }}
      >
        <StatusIcon size={12} />
        <span>{freshness.ageHuman}</span>
      </div>
    );
  }

  return (
    <div 
      style={{ 
        display: "flex", 
        alignItems: "center", 
        gap: "0.5rem",
        padding: "0.5rem 0.75rem",
        borderRadius: "0.375rem",
        background: config.bgColor,
        border: `1px solid ${config.color}33`,
        color: config.color,
        fontSize: "0.78rem",
        fontWeight: "600"
      }}
    >
      <StatusIcon size={14} />
      {showLabel && (
        <span style={{ opacity: 0.8 }}>{config.label}:</span>
      )}
      <span>{freshness.ageHuman} ago</span>
      {onRefresh && (
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          style={{
            background: "transparent",
            border: "none",
            color: config.color,
            cursor: isRefreshing ? "not-allowed" : "pointer",
            padding: "0.1rem",
            display: "flex",
            alignItems: "center",
            opacity: isRefreshing ? 0.5 : 1
          }}
          title="Refresh data"
        >
          <RefreshCw size={12} style={{ animation: isRefreshing ? "spin 1s linear infinite" : "none" }} />
        </button>
      )}
    </div>
  );
}

// Hook for WebSocket-based data freshness updates
export function useDataFreshnessWebSocket() {
  const [socket, setSocket] = useState(null);
  const [freshnessData, setFreshnessData] = useState({});

  useEffect(() => {
    const wsUrl = `ws://localhost:8008/api/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("Data freshness WebSocket connected");
      // Subscribe to data freshness events
      ws.send(JSON.stringify({
        action: "subscribe",
        events: ["data_freshness", "cw_scan_completed", "atc_sync_completed"]
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.event === "data_freshness") {
        setFreshnessData(data.data);
      } else if (data.event === "cw_scan_completed") {
        setFreshnessData(prev => ({
          ...prev,
          cw_scan: {
            timestamp: data.timestamp,
            cache_invalidated: data.cache_invalidated
          }
        }));
      } else if (data.event === "atc_sync_completed") {
        setFreshnessData(prev => ({
          ...prev,
          atc_sync: {
            timestamp: data.timestamp,
            trading_day: data.trading_day,
            cache_invalidated: data.cache_invalidated
          }
        }));
      }
    };

    ws.onerror = (error) => {
      console.error("Data freshness WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("Data freshness WebSocket disconnected");
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, []);

  return { socket, freshnessData };
}
