import React, { useState, useCallback } from "react";
import { 
  Plus, Trash2, Save, Play, Settings, TrendingUp, 
  ArrowUp, ArrowDown, Minus, MoreHorizontal, X,
  GripVertical, ChevronDown, ChevronRight
} from "lucide-react";

// Available indicators library
const INDICATOR_LIBRARY = [
  {
    category: "Price Action",
    items: [
      { id: "sma_20", name: "SMA 20", description: "Simple Moving Average 20 periods", params: [{ name: "period", default: 20, type: "number" }] },
      { id: "sma_50", name: "SMA 50", description: "Simple Moving Average 50 periods", params: [{ name: "period", default: 50, type: "number" }] },
      { id: "ema_12", name: "EMA 12", description: "Exponential Moving Average 12 periods", params: [{ name: "period", default: 12, type: "number" }] },
      { id: "ema_26", name: "EMA 26", description: "Exponential Moving Average 26 periods", params: [{ name: "period", default: 26, type: "number" }] },
      { id: "rsi", name: "RSI", description: "Relative Strength Index", params: [{ name: "period", default: 14, type: "number" }] },
      { id: "macd", name: "MACD", description: "Moving Average Convergence Divergence", params: [] },
      { id: "bollinger", name: "Bollinger Bands", description: "Volatility bands", params: [{ name: "period", default: 20, type: "number" }, { name: "std", default: 2, type: "number" }] },
    ]
  },
  {
    category: "Volume",
    items: [
      { id: "volume_sma", name: "Volume SMA", description: "Volume Moving Average", params: [{ name: "period", default: 20, type: "number" }] },
      { id: "volume_ratio", name: "Volume Ratio", description: "Current volume / Average volume", params: [{ name: "period", default: 20, type: "number" }] },
    ]
  },
  {
    category: "Volatility",
    items: [
      { id: "atr", name: "ATR", description: "Average True Range", params: [{ name: "period", default: 14, type: "number" }] },
      { id: "hv", name: "Historical Volatility", description: "Historical volatility calculation", params: [{ name: "period", default: 20, type: "number" }] },
      { id: "iv", name: "Implied Volatility", description: "Option implied volatility", params: [] },
    ]
  },
  {
    category: "CW Specific",
    items: [
      { id: "moneyness", name: "Moneyness", description: "Underlying price / Strike price", params: [] },
      { id: "delta", name: "Delta", description: "Option delta sensitivity", params: [] },
      { id: "theta", name: "Theta", description: "Time decay", params: [] },
      { id: "gamma", name: "Gamma", description: "Rate of delta change", params: [] },
      { id: "days_to_expiry", name: "Days to Expiry", description: "Days until maturity", params: [] },
      { id: "iv_hv_spread", name: "IV-HV Spread", description: "Implied vs Historical volatility spread", params: [] },
      { id: "conversion_ratio", name: "Conversion Ratio", description: "CW conversion ratio", params: [] },
    ]
  },
  {
    category: "Market Regime",
    items: [
      { id: "market_regime", name: "Market Regime", description: "Bullish/Bearish/Sideways regime", params: [] },
      { id: "vni_index", name: "VN-Index", description: "Vietnam market index", params: [] },
      { id: "underlying_trend", name: "Underlying Trend", description: "Stock underlying price trend", params: [] },
    ]
  }
];

// Comparison operators
const OPERATORS = [
  { id: "gt", symbol: ">", label: "Greater than" },
  { id: "gte", symbol: ">=", label: "Greater or equal" },
  { id: "lt", symbol: "<", label: "Less than" },
  { id: "lte", symbol: "<=", label: "Less or equal" },
  { id: "eq", symbol: "=", label: "Equal to" },
  { id: "ne", symbol: "!=", label: "Not equal" },
  { id: "cross_above", symbol: "↗", label: "Crosses above" },
  { id: "cross_below", symbol: "↘", label: "Crosses below" },
];

// Logical operators
const LOGICAL_OPERATORS = [
  { id: "and", label: "AND" },
  { id: "or", label: "OR" },
];

export function StrategyBuilder({ 
  preferences = {}, 
  onRunBacktest, 
  onSaveStrategy, 
  onLoadStrategy,
  onDeleteStrategy,
  savedStrategies = [] 
}) {
  const { isDark, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);
  
  const [strategyName, setStrategyName] = useState("");
  const [entryConditions, setEntryConditions] = useState([{ id: 1, indicator: null, operator: "gt", value: "", logicalOp: "and" }]);
  const [exitConditions, setExitConditions] = useState([{ id: 1, indicator: null, operator: "lt", value: "", logicalOp: "and" }]);
  const [riskParams, setRiskParams] = useState({
    stopLoss: 8,
    takeProfit: 50,
    maxPositionSize: 15,
    maxPositions: 5,
    capital: 100000000
  });
  const [expandedCategories, setExpandedCategories] = useState({});
  const [showSavedPanel, setShowSavedPanel] = useState(false);

  const toggleCategory = useCallback((category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  }, []);

  const addCondition = (type) => {
    const newId = Date.now();
    const setter = type === "entry" ? setEntryConditions : setExitConditions;
    const current = type === "entry" ? entryConditions : exitConditions;
    
    setter([...current, {
      id: newId,
      indicator: null,
      operator: type === "entry" ? "gt" : "lt",
      value: "",
      logicalOp: "and"
    }]);
  };

  const removeCondition = (type, id) => {
    const setter = type === "entry" ? setEntryConditions : setExitConditions;
    const current = type === "entry" ? entryConditions : exitConditions;
    
    if (current.length > 1) {
      setter(current.filter(c => c.id !== id));
    }
  };

  const updateCondition = (type, id, field, value) => {
    const setter = type === "entry" ? setEntryConditions : setExitConditions;
    const current = type === "entry" ? entryConditions : exitConditions;
    
    setter(current.map(c => c.id === id ? { ...c, [field]: value } : c));
  };

  const handleDragStart = (e, indicator) => {
    e.dataTransfer.setData("indicator", JSON.stringify(indicator));
  };

  const handleDrop = (e, type, conditionId) => {
    e.preventDefault();
    const indicatorData = e.dataTransfer.getData("indicator");
    if (indicatorData) {
      const indicator = JSON.parse(indicatorData);
      updateCondition(type, conditionId, "indicator", indicator);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const saveStrategy = () => {
    if (!strategyName.trim()) {
      alert("Vui lòng nhập tên chiến lược!");
      return;
    }

    const strategy = {
      id: Date.now(),
      name: strategyName,
      entryConditions,
      exitConditions,
      riskParams,
      createdAt: new Date().toISOString()
    };

    onSaveStrategy(strategy);
    setStrategyName("");
  };

  const loadStrategy = (strategy) => {
    setStrategyName(strategy.name);
    setEntryConditions(strategy.entryConditions);
    setExitConditions(strategy.exitConditions);
    setRiskParams(strategy.riskParams);
    setShowSavedPanel(false);
  };

  const deleteStrategy = (id) => {
    if (window.confirm("Bạn có chắc muốn xóa chiến lược này?")) {
      onDeleteStrategy(id);
    }
  };

  const runBacktest = () => {
    const strategyConfig = {
      name: strategyName || "Custom Strategy",
      entryConditions,
      exitConditions,
      riskParams
    };
    
    onRunBacktest(strategyConfig);
  };

  const renderConditionRow = (condition, type, index) => (
    <div 
      key={condition.id}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        padding: "0.5rem",
        background: subBg,
        border: `1px solid ${borderColor}`,
        borderRadius: "0.375rem",
        marginBottom: index > 0 ? "0.5rem" : 0
      }}
      onDragOver={handleDragOver}
      onDrop={(e) => handleDrop(e, type, condition.id)}
    >
      {index > 0 && (
        <select
          value={condition.logicalOp}
          onChange={(e) => updateCondition(type, condition.id, "logicalOp", e.target.value)}
          style={{
            background: cardBg,
            border: `1px solid ${borderColor}`,
            color: textColor,
            padding: "0.3rem",
            borderRadius: "0.25rem",
            fontSize: "0.75rem",
            fontWeight: "700"
          }}
        >
          {LOGICAL_OPERATORS.map(op => (
            <option key={op.id} value={op.id}>{op.label}</option>
          ))}
        </select>
      )}

      <GripVertical size={16} style={{ color: mutedText, cursor: "grab" }} />
      
      <div
        style={{
          flex: 1,
          padding: "0.4rem 0.6rem",
          background: condition.indicator ? "rgba(37,99,235,0.1)" : "rgba(100,116,139,0.1)",
          border: `1px dashed ${borderColor}`,
          borderRadius: "0.25rem",
          fontSize: "0.8rem",
          color: condition.indicator ? "#60a5fa" : mutedText,
          minHeight: "32px",
          display: "flex",
          alignItems: "center"
        }}
      >
        {condition.indicator ? condition.indicator.name : "Kéo indicator vào đây"}
      </div>

      <select
        value={condition.operator}
        onChange={(e) => updateCondition(type, condition.id, "operator", e.target.value)}
        style={{
          background: cardBg,
          border: `1px solid ${borderColor}`,
          color: textColor,
          padding: "0.3rem",
          borderRadius: "0.25rem",
          fontSize: "0.75rem",
          fontWeight: "700"
        }}
      >
        {OPERATORS.map(op => (
          <option key={op.id} value={op.id}>{op.symbol} {op.label}</option>
        ))}
      </select>

      <input
        type="text"
        value={condition.value}
        onChange={(e) => updateCondition(type, condition.id, "value", e.target.value)}
        placeholder="Giá trị"
        style={{
          width: "80px",
          background: cardBg,
          border: `1px solid ${borderColor}`,
          color: textColor,
          padding: "0.3rem",
          borderRadius: "0.25rem",
          fontSize: "0.8rem"
        }}
      />

      <button
        onClick={() => removeCondition(type, condition.id)}
        style={{
          background: "rgba(239,68,68,0.1)",
          color: "#ef4444",
          border: "1px solid rgba(239,68,68,0.3)",
          padding: "0.3rem",
          borderRadius: "0.25rem",
          cursor: "pointer"
        }}
      >
        <Trash2 size={14} />
      </button>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", color: textColor }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: "900", margin: 0, color: "#60a5fa" }}>
          🎨 Visual Strategy Builder
        </h3>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={() => setShowSavedPanel(!showSavedPanel)}
            style={{
              background: subBg,
              color: textColor,
              border: `1px solid ${borderColor}`,
              padding: "0.4rem 0.8rem",
              borderRadius: "0.375rem",
              fontSize: "0.8rem",
              fontWeight: "700",
              cursor: "pointer"
            }}
          >
            📁 Chiến lược đã lưu ({savedStrategies.length})
          </button>
        </div>
      </div>

      {/* Strategy Name Input */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem" }}>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input
            type="text"
            value={strategyName}
            onChange={(e) => setStrategyName(e.target.value)}
            placeholder="Tên chiến lược (ví dụ: Alpha Hunter v1)"
            style={{
              flex: 1,
              background: subBg,
              border: `1px solid ${borderColor}`,
              color: textColor,
              padding: "0.5rem 0.75rem",
              borderRadius: "0.375rem",
              fontSize: "0.85rem",
              fontWeight: "700"
            }}
          />
          <button
            onClick={saveStrategy}
            style={{
              background: "#10b981",
              color: "#fff",
              border: "none",
              padding: "0.5rem 1rem",
              borderRadius: "0.375rem",
              fontSize: "0.85rem",
              fontWeight: "800",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.3rem"
            }}
          >
            <Save size={16} /> Lưu chiến lược
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "1rem" }}>
        
        {/* Indicator Library */}
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem", maxHeight: "600px", overflowY: "auto" }}>
          <h4 style={{ fontSize: "0.85rem", fontWeight: "800", margin: "0 0 0.75rem 0", color: textColor }}>
            📚 Thư viện Indicator
          </h4>
          
          {INDICATOR_LIBRARY.map(category => (
            <div key={category.category} style={{ marginBottom: "0.75rem" }}>
              <button
                onClick={() => toggleCategory(category.category)}
                style={{
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  color: textColor,
                  padding: "0.4rem 0",
                  fontSize: "0.8rem",
                  fontWeight: "800",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.4rem"
                }}
              >
                {expandedCategories[category.category] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                {category.category}
              </button>
              
              {expandedCategories[category.category] && (
                <div style={{ marginLeft: "0.5rem", marginTop: "0.25rem" }}>
                  {category.items.map(item => (
                    <div
                      key={item.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, item)}
                      style={{
                        padding: "0.4rem 0.6rem",
                        background: subBg,
                        border: `1px solid ${borderColor}`,
                        borderRadius: "0.25rem",
                        marginBottom: "0.25rem",
                        fontSize: "0.75rem",
                        color: textColor,
                        cursor: "grab",
                        transition: "all 0.15s"
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = "rgba(37,99,235,0.1)"}
                      onMouseLeave={(e) => e.currentTarget.style.background = subBg}
                    >
                      <div style={{ fontWeight: "700", color: "#60a5fa" }}>{item.name}</div>
                      <div style={{ fontSize: "0.7rem", color: mutedText }}>{item.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Builder Area */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          
          {/* Entry Conditions */}
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <h4 style={{ fontSize: "0.85rem", fontWeight: "800", margin: 0, color: "#10b981" }}>
                📈 Điều kiện VÀO (Entry)
              </h4>
              <button
                onClick={() => addCondition("entry")}
                style={{
                  background: "rgba(16,185,129,0.1)",
                  color: "#10b981",
                  border: "1px solid rgba(16,185,129,0.3)",
                  padding: "0.3rem 0.6rem",
                  borderRadius: "0.25rem",
                  fontSize: "0.75rem",
                  fontWeight: "700",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem"
                }}
              >
                <Plus size={14} /> Thêm điều kiện
              </button>
            </div>
            
            {entryConditions.map((condition, index) => renderConditionRow(condition, "entry", index))}
          </div>

          {/* Exit Conditions */}
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <h4 style={{ fontSize: "0.85rem", fontWeight: "800", margin: 0, color: "#ef4444" }}>
                📉 Điều kiện RA (Exit)
              </h4>
              <button
                onClick={() => addCondition("exit")}
                style={{
                  background: "rgba(239,68,68,0.1)",
                  color: "#ef4444",
                  border: "1px solid rgba(239,68,68,0.3)",
                  padding: "0.3rem 0.6rem",
                  borderRadius: "0.25rem",
                  fontSize: "0.75rem",
                  fontWeight: "700",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem"
                }}
              >
                <Plus size={14} /> Thêm điều kiện
              </button>
            </div>
            
            {exitConditions.map((condition, index) => renderConditionRow(condition, "exit", index))}
          </div>

          {/* Risk Parameters */}
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem" }}>
            <h4 style={{ fontSize: "0.85rem", fontWeight: "800", margin: "0 0 0.75rem 0", color: textColor }}>
              ⚙️ Thông số Quản lý rủi ro
            </h4>
            
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem" }}>
              <div>
                <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem", fontWeight: "700" }}>
                  Stop Loss (%)
                </label>
                <input
                  type="number"
                  value={riskParams.stopLoss}
                  onChange={(e) => setRiskParams({...riskParams, stopLoss: Number(e.target.value)})}
                  style={{
                    width: "100%",
                    background: subBg,
                    border: `1px solid ${borderColor}`,
                    color: "#ef4444",
                    padding: "0.4rem",
                    borderRadius: "0.25rem",
                    fontSize: "0.8rem",
                    fontWeight: "700"
                  }}
                />
              </div>
              
              <div>
                <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem", fontWeight: "700" }}>
                  Take Profit (%)
                </label>
                <input
                  type="number"
                  value={riskParams.takeProfit}
                  onChange={(e) => setRiskParams({...riskParams, takeProfit: Number(e.target.value)})}
                  style={{
                    width: "100%",
                    background: subBg,
                    border: `1px solid ${borderColor}`,
                    color: "#10b981",
                    padding: "0.4rem",
                    borderRadius: "0.25rem",
                    fontSize: "0.8rem",
                    fontWeight: "700"
                  }}
                />
              </div>
              
              <div>
                <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem", fontWeight: "700" }}>
                  Vốn ban đầu (VND)
                </label>
                <input
                  type="number"
                  value={riskParams.capital}
                  onChange={(e) => setRiskParams({...riskParams, capital: Number(e.target.value)})}
                  style={{
                    width: "100%",
                    background: subBg,
                    border: `1px solid ${borderColor}`,
                    color: textColor,
                    padding: "0.4rem",
                    borderRadius: "0.25rem",
                    fontSize: "0.8rem",
                    fontWeight: "700"
                  }}
                />
              </div>
              
              <div>
                <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem", fontWeight: "700" }}>
                  Max vị thế (%)
                </label>
                <input
                  type="number"
                  value={riskParams.maxPositionSize}
                  onChange={(e) => setRiskParams({...riskParams, maxPositionSize: Number(e.target.value)})}
                  style={{
                    width: "100%",
                    background: subBg,
                    border: `1px solid ${borderColor}`,
                    color: textColor,
                    padding: "0.4rem",
                    borderRadius: "0.25rem",
                    fontSize: "0.8rem",
                    fontWeight: "700"
                  }}
                />
              </div>
              
              <div>
                <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem", fontWeight: "700" }}>
                  Số vị thế tối đa
                </label>
                <input
                  type="number"
                  value={riskParams.maxPositions}
                  onChange={(e) => setRiskParams({...riskParams, maxPositions: Number(e.target.value)})}
                  style={{
                    width: "100%",
                    background: subBg,
                    border: `1px solid ${borderColor}`,
                    color: textColor,
                    padding: "0.4rem",
                    borderRadius: "0.25rem",
                    fontSize: "0.8rem",
                    fontWeight: "700"
                  }}
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button
              onClick={runBacktest}
              style={{
                flex: 2,
                background: "#2563eb",
                color: "#fff",
                border: "none",
                padding: "0.65rem 1.25rem",
                borderRadius: "0.375rem",
                fontSize: "0.88rem",
                fontWeight: "900",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "0.4rem"
              }}
            >
              <Play size={18} /> ▶ Chạy Backtest với Chiến lược Tùy chỉnh
            </button>
          </div>
        </div>
      </div>

      {/* Saved Strategies Panel */}
      {showSavedPanel && (
        <div style={{
          position: "fixed",
          top: 0,
          right: 0,
          width: "350px",
          height: "100vh",
          background: cardBg,
          borderLeft: `1px solid ${borderColor}`,
          padding: "1.5rem",
          overflowY: "auto",
          zIndex: 1000,
          boxShadow: "-4px 0 20px rgba(0,0,0,0.3)"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h4 style={{ fontSize: "0.9rem", fontWeight: "800", margin: 0, color: textColor }}>
              📁 Chiến lược đã lưu
            </h4>
            <button
              onClick={() => setShowSavedPanel(false)}
              style={{ background: "none", border: "none", color: textColor, cursor: "pointer" }}
            >
              <X size={20} />
            </button>
          </div>
          
          {savedStrategies.length === 0 ? (
            <div style={{ textAlign: "center", color: mutedText, fontSize: "0.8rem", padding: "2rem 0" }}>
              Chưa có chiến lược nào được lưu
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {savedStrategies.map(strategy => (
                <div
                  key={strategy.id}
                  style={{
                    background: subBg,
                    border: `1px solid ${borderColor}`,
                    borderRadius: "0.5rem",
                    padding: "1rem"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                    <div style={{ fontWeight: "800", color: "#60a5fa", fontSize: "0.85rem" }}>
                      {strategy.name}
                    </div>
                    <div style={{ fontSize: "0.7rem", color: mutedText }}>
                      {new Date(strategy.createdAt).toLocaleDateString("vi-VN")}
                    </div>
                  </div>
                  
                  <div style={{ fontSize: "0.75rem", color: mutedText, marginBottom: "0.75rem" }}>
                    {strategy.entryConditions.length} điều kiện vào · {strategy.exitConditions.length} điều kiện ra
                  </div>
                  
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button
                      onClick={() => loadStrategy(strategy)}
                      style={{
                        flex: 1,
                        background: "#2563eb",
                        color: "#fff",
                        border: "none",
                        padding: "0.4rem",
                        borderRadius: "0.25rem",
                        fontSize: "0.75rem",
                        fontWeight: "700",
                        cursor: "pointer"
                      }}
                    >
                      Load
                    </button>
                    <button
                      onClick={() => deleteStrategy(strategy.id)}
                      style={{
                        background: "rgba(239,68,68,0.1)",
                        color: "#ef4444",
                        border: "1px solid rgba(239,68,68,0.3)",
                        padding: "0.4rem",
                        borderRadius: "0.25rem",
                        fontSize: "0.75rem",
                        fontWeight: "700",
                        cursor: "pointer"
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function useThemeTokens(preferences) {
  const isDark = preferences.colorMode === "dark";
  return {
    isDark,
    bg: isDark ? "#0b0f19" : "#f8fafc",
    cardBg: isDark ? "#131b2e" : "#ffffff",
    subBg: isDark ? "rgba(255,255,255,0.04)" : "#f1f5f9",
    textColor: isDark ? "#e2e8f0" : "#1e293b",
    mutedText: isDark ? "#94a3b8" : "#64748b",
    borderColor: isDark ? "rgba(255,255,255,0.08)" : "#e2e8f0"
  };
}
