import React, { useEffect, useState } from "react";
import { Star, Trash2, Plus, AlertCircle } from "lucide-react";
import { useToast } from "../../components/ui/toast.jsx";
import { useThemeTokens } from "../../app/useThemeTokens.js";
import { useData } from "../../app/DataContext.jsx";

export function WatchlistPage({ language = "vi", preferences = {} }) {
  const { bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const isEnglish = language === "en";
  const { addToast } = useToast();
  const { opportunitiesData } = useData();
  const [activeTab, setActiveTab] = useState("chung_quyen");
  const [inputVal, setInputVal] = useState("");
  const [items, setItems] = useState([]);
  const [liveOppMap, setLiveOppMap] = useState({});
  const [stockItems, setStockItems] = useState([]);

  useEffect(() => {
    const opps = opportunitiesData?.opportunities || [];
    const map = {};
    opps.forEach(o => {
      map[o.symbol?.toUpperCase()] = o;
    });
    setLiveOppMap(map);
  }, [opportunitiesData]);

  useEffect(() => {
    const saved = localStorage.getItem("finvista-watchlist");
    let symbols = ["CVPB2404", "CHPG2405", "CVRE2402", "CFPT2401", "ACB", "SSI", "VCB"];
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          symbols = parsed;
        }
      } catch (e) {}
    }

    const list = symbols.map(sym => {
      const upperSym = sym.toUpperCase();
      const real = liveOppMap[upperSym];
      if (real) {
        const price = real.market_price || real.price;
        const changePct = real.price_change_pct;
        const sig = real.recommendation_signal || real.decision_signal || "THEO DÕI";
        return {
          symbol: upperSym,
          issuer: real.issuer || "HOSE",
          price: price,
          change: `${changePct >= 0 ? "+" : ""}${Math.round(price * (changePct / 100))}`,
          changePct: `${changePct >= 0 ? "+" : ""}${changePct.toFixed(2)}%`,
          volume: real.volume ? real.volume.toLocaleString() : "100,000",
          value: real.turnover_billion ? `${real.turnover_billion.toFixed(1)}B` : "100M",
          signal: sig,
          target: real.target_price ? real.target_price.toLocaleString() : "-",
          type: upperSym.match(/\d{4}$/) ? "cw" : "stock"
        };
      }
      const isCW = upperSym.match(/\d{4}$/);
      return { 
        symbol: upperSym, 
        issuer: "HOSE", 
        price: isCW ? 1200 : 25000, 
        change: isCW ? "+30" : "+500", 
        changePct: isCW ? "+2.5%" : "+2.0%", 
        volume: isCW ? "250,000" : "1,500,000", 
        value: isCW ? "312.5M" : "37.5B", 
        signal: "THEO DÕI (70)", 
        target: isCW ? "1,400" : "28,000",
        type: isCW ? "cw" : "stock"
      };
    });
    
    // Separate CW and stock items
    const cwItems = list.filter(item => item.type === "cw");
    const stockItemsOnly = list.filter(item => item.type === "stock");
    
    setItems(cwItems);
    setStockItems(stockItemsOnly);
  }, [liveOppMap]);

  function saveList(newList) {
    setItems(newList);
    localStorage.setItem("finvista-watchlist", JSON.stringify(newList.map(i => i.symbol)));
  }

  function handleAdd() {
    const sym = inputVal.trim().toUpperCase();
    if (!sym) return;
    
    // Check if already exists in either list
    const allItems = [...items, ...stockItems];
    if (allItems.some(i => i.symbol === sym)) {
      addToast(isEnglish ? `${sym} is already in Watchlist` : `${sym} đã có trong danh sách!`, "info");
      setInputVal("");
      return;
    }
    
    const isCW = sym.match(/\d{4}$/);
    const newItem = { 
      symbol: sym, 
      issuer: "HOSE", 
      price: isCW ? 1250 : 25000, 
      change: isCW ? "+30" : "+500", 
      changePct: isCW ? "+2.5%" : "+2.0%", 
      volume: isCW ? "250,000" : "1,500,000", 
      value: isCW ? "312.5M" : "37.5B", 
      signal: "THEO DÕI (70)", 
      target: isCW ? "1,400" : "28,000",
      type: isCW ? "cw" : "stock"
    };
    
    // Add to appropriate list
    if (isCW) {
      const newList = [newItem, ...items];
      setItems(newList);
    } else {
      const newList = [newItem, ...stockItems];
      setStockItems(newList);
    }
    
    // Save combined list
    localStorage.setItem("finvista-watchlist", JSON.stringify([...stockItems.map(i => i.symbol), ...items.map(i => i.symbol), sym]));
    setInputVal("");
    addToast(isEnglish ? `Added ${sym} to Watchlist!` : `Đã thêm ${sym} vào Watchlist thành công!`, "success");
  }

  function handleRemove(sym) {
    // Check which list the item belongs to
    const inCW = items.some(i => i.symbol === sym);
    const inStock = stockItems.some(i => i.symbol === sym);
    
    if (inCW) {
      const newList = items.filter(i => i.symbol !== sym);
      setItems(newList);
    } else if (inStock) {
      const newList = stockItems.filter(i => i.symbol !== sym);
      setStockItems(newList);
    }
    
    // Save combined list
    localStorage.setItem("finvista-watchlist", JSON.stringify([...stockItems.filter(i => i.symbol !== sym).map(i => i.symbol), ...items.filter(i => i.symbol !== sym).map(i => i.symbol)]));
    addToast(isEnglish ? `Removed ${sym}` : `Đã xóa ${sym} khỏi Watchlist`, "info");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg }}>
      
      {/* HEADER BAR (PDF Page 11) */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <h2 style={{ fontSize: "1.5rem", fontWeight: "900", margin: 0, color: textColor, letterSpacing: "0.5px" }}>
              {isEnglish ? "WATCHLIST" : "DANH SÁCH THEO DÕI"}
            </h2>
            <p style={{ fontSize: "0.82rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
              {isEnglish ? "Track price movements, volume, and set automatic price alerts for your favorite CW symbols." : "Theo dõi biến động giá, khối lượng và cài đặt cảnh báo giá tự động cho các mã CW quan tâm."}
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <input
              placeholder={isEnglish ? "Enter symbol..." : "Nhập mã CW..."}
              value={inputVal}
              onChange={e => setInputVal(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleAdd()}
              style={{ background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.4rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.8rem", width: "160px" }}
            />
            <button onClick={handleAdd} style={{ background: "#10b981", color: "#fff", border: "none", padding: "0.4rem 0.85rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <Plus size={14} /> {isEnglish ? "Add" : "Thêm mã"}
            </button>
          </div>
        </div>

        {/* PDF Page 11 Tabs: Chứng khoán cơ sở, Chứng quyền */}
        <div style={{ display: "flex", gap: "0.35rem", background: subBg, padding: "0.25rem", borderRadius: "0.5rem", width: "fit-content" }}>
          {[
            { id: "co_so", label: isEnglish ? "Underlying Stocks" : "Chứng khoán cơ sở" },
            { id: "chung_quyen", label: isEnglish ? "Covered Warrants" : "Chứng quyền" },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? "#2563eb" : "transparent",
                color: activeTab === tab.id ? "#fff" : mutedText,
                border: "none",
                borderRadius: "0.375rem",
                padding: "0.4rem 1.25rem",
                fontSize: "0.82rem",
                fontWeight: "700",
                cursor: "pointer"
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* WATCHLIST TABLE (PDF Page 11) */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: "800", margin: "0 0 1rem 0", color: textColor }}>
          {isEnglish ? "WATCHLIST" : "DANH SÁCH THEO DÕI"} ({activeTab === "chung_quyen" ? items.length : stockItems.length})
        </h3>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", textAlign: "left" }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${borderColor}`, color: mutedText }}>
              <th style={{ padding: "0.6rem" }}>{isEnglish ? "Favorite" : "Yêu thích"}</th>
              <th style={{ padding: "0.6rem" }}>{activeTab === "chung_quyen" ? (isEnglish ? "CW Symbol" : "Mã CW") : (isEnglish ? "Stock Symbol" : "Mã CK")}</th>
              <th style={{ padding: "0.6rem" }}>{isEnglish ? "Issuer" : "Tổ chức PH"}</th>
              <th style={{ padding: "0.6rem" }}>{isEnglish ? "Current Price" : "Giá hiện tại"}</th>
              <th style={{ padding: "0.6rem" }}>{isEnglish ? "Change" : "Thay đổi"}</th>
              <th style={{ padding: "0.6rem" }}>{isEnglish ? "% Change" : "% Thay đổi"}</th>
              <th style={{ padding: "0.6rem" }}>{isEnglish ? "Volume" : "Khối lượng"}</th>
              <th style={{ padding: "0.6rem" }}>{isEnglish ? "Value" : "Giá trị"}</th>
              <th style={{ padding: "0.6rem" }}>{isEnglish ? "G-Score Signal" : "Tín hiệu G-Score"}</th>
              <th style={{ padding: "0.6rem" }}>{isEnglish ? "Price Alert" : "Cảnh báo giá"}</th>
              <th style={{ padding: "0.6rem", textAlign: "center" }}>{isEnglish ? "Delete" : "Xóa"}</th>
            </tr>
          </thead>
          <tbody>
            {(activeTab === "chung_quyen" ? items : stockItems).map(item => (
              <tr key={item.symbol} style={{ borderBottom: `1px solid ${borderColor}` }}>
                <td style={{ padding: "0.75rem 0.6rem", color: "#f59e0b" }}>★</td>
                <td style={{ padding: "0.75rem 0.6rem", fontWeight: "800", color: "#2563eb" }}>{item.symbol}</td>
                <td style={{ padding: "0.75rem 0.6rem", color: textColor }}>{item.issuer}</td>
                <td style={{ padding: "0.75rem 0.6rem", fontWeight: "700", color: textColor }}>{item.price} đ</td>
                <td style={{ padding: "0.75rem 0.6rem", color: item.change.includes("+") ? "#10b981" : "#ef4444", fontWeight: "700" }}>{item.change}</td>
                <td style={{ padding: "0.75rem 0.6rem", color: item.changePct.includes("+") ? "#10b981" : "#ef4444", fontWeight: "700" }}>{item.changePct}</td>
                <td style={{ padding: "0.75rem 0.6rem", color: textColor }}>{item.volume}</td>
                <td style={{ padding: "0.75rem 0.6rem", color: textColor }}>{item.value}</td>
                <td style={{ padding: "0.75rem 0.6rem", color: "#10b981", fontWeight: "700" }}>{item.signal}</td>
                <td style={{ padding: "0.75rem 0.6rem", color: mutedText }}>&gt; {item.target} đ</td>
                <td style={{ padding: "0.75rem 0.6rem", textAlign: "center" }}>
                  <button onClick={() => handleRemove(item.symbol)} style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer" }}>🗑️ {isEnglish ? "Delete" : "Xóa"}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
}
