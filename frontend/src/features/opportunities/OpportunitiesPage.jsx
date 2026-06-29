import React, { useEffect, useRef, useState } from "react";
import { Bookmark, RefreshCw, Save, Search, Trash2 } from "lucide-react";

import { getMarketMetadata, getOpportunities } from "../../api.js";
import { useAuth } from "../../auth/AuthProvider.jsx";
import { STORAGE_KEYS, VN30_UNDERLYINGS } from "../../app/config.js";
import { Button } from "../../components/ui/button.jsx";
import { Input } from "../../components/ui/input.jsx";
import { ErrorBox, LoadingBox } from "../../components/ui/status.jsx";
import { formatMoney, formatNumber, formatSignal, signalClass } from "../../lib/formatters.js";

const ENGLISH_INDUSTRIES = {
  "Ngân hàng": "Banking",
  "Chứng khoán": "Securities",
  "Bảo hiểm": "Insurance",
  "Bất động sản": "Real estate",
  "Tiện ích": "Utilities",
  "Năng lượng": "Energy",
  "Thép": "Steel",
  "Cao su": "Rubber",
  "Hóa chất": "Chemicals",
  "Thực phẩm": "Food & Beverage",
  "Bán lẻ": "Retail",
  "Công nghệ": "Technology",
  "Vận tải": "Transportation",
  "Logistics": "Logistics",
  "Vật liệu xây dựng": "Construction materials",
  "Công nghệ và thông tin": "Technology & information",
  "Thực phẩm - Đồ uống": "Food & beverage",
  "Vận tải - kho bãi": "Transportation & logistics",
  "SX Nhựa - Hóa chất": "Plastics & chemicals",
  "Khác": "Others",
  "Unknown": "Unknown"
};

function displayIndustry(industry, language) {
  if (!industry) return "";
  if (language !== "en") return industry;
  return ENGLISH_INDUSTRIES[industry] || industry;
}

export function OpportunitiesPage({ setPage, setSelectedSymbol, language = "vi" }) {
  const auth = useAuth();
  const isEnglish = language === "en";
  const [strategy, setStrategy] = useState("balanced");
  const [underlying, setUnderlying] = useState("");
  const [limit, setLimit] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const [maturityMax, setMaturityMax] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [gearMin, setGearMin] = useState("");
  const [deltaMin, setDeltaMin] = useState("");
  const [thetaMax, setThetaMax] = useState("");
  const [ivHvMax, setIvHvMax] = useState("");
  const [signalFilter, setSignalFilter] = useState("all");
  const [industryFilter, setIndustryFilter] = useState("");
  const [marketMeta, setMarketMeta] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pendingSymbol, setPendingSymbol] = useState("");
  const [presetName, setPresetName] = useState("");
  const [filterPresets, setFilterPresets] = useState([]);
  const [activePresetId, setActivePresetId] = useState("");
  const tableScrollRef = useRef(null);
  const tableDragRef = useRef(null);
  const suppressTableRowClickUntilRef = useRef(0);

  const [debouncedUnderlying, setDebouncedUnderlying] = useState(underlying);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedUnderlying(underlying);
    }, 300);
    return () => clearTimeout(timer);
  }, [underlying]);

  async function loadOpportunities({ forceRefresh = false, underlyingOverride } = {}) {
    setLoading(true);
    setError("");
    try {
      const searchUnderlying = underlyingOverride !== undefined ? underlyingOverride : debouncedUnderlying;
      const [result, metadata] = await Promise.all([
        getOpportunities({
          strategy,
          underlying: searchUnderlying,
          limit: 1000, // Fetch up to 1000 elements for frontend pagination
          forceRefresh,
          industry: industryFilter
        }),
        getMarketMetadata({ forceRefresh })
      ]);
      setData(result);
      setMarketMeta(metadata);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOpportunities({ underlyingOverride: debouncedUnderlying });
  }, [strategy, debouncedUnderlying, industryFilter]);

  useEffect(() => {
    setCurrentPage(1);
  }, [strategy, debouncedUnderlying, limit, industryFilter, maturityMax, priceMax, gearMin, deltaMin, thetaMax, ivHvMax, signalFilter]);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.filterPresets) || "[]");
      if (Array.isArray(saved)) setFilterPresets(saved);
    } catch {
      setFilterPresets([]);
    }
  }, []);

  function currentFilterConfig() {
    return {
      strategy,
      underlying,
      limit,
      maturityMax,
      priceMax,
      gearMin,
      deltaMin,
      thetaMax,
      ivHvMax,
      industryFilter,
      signalFilter
    };
  }

  function persistPresets(nextPresets) {
    setFilterPresets(nextPresets);
    localStorage.setItem(STORAGE_KEYS.filterPresets, JSON.stringify(nextPresets));
  }

  function saveFilterPreset() {
    const name = presetName.trim();
    if (!name) return;
    const nextPreset = {
      id: `${Date.now()}`,
      name,
      config: currentFilterConfig()
    };
    const nextPresets = [
      nextPreset,
      ...filterPresets.filter((preset) => preset.name.toLowerCase() !== name.toLowerCase())
    ].slice(0, 12);
    persistPresets(nextPresets);
    setPresetName("");
  }

  function setFilterConfig(config = {}) {
    setStrategy(config.strategy || "balanced");
    setUnderlying(config.underlying || "");
    setLimit(config.limit || 10);
    setMaturityMax(config.maturityMax || "");
    setPriceMax(config.priceMax || "");
    setGearMin(config.gearMin || "");
    setDeltaMin(config.deltaMin || "");
    setThetaMax(config.thetaMax || "");
    setIvHvMax(config.ivHvMax || "");
    setIndustryFilter(config.industryFilter || "");
    setSignalFilter(config.signalFilter || "all");
  }

  function clearFilterPreset() {
    setFilterConfig();
    setActivePresetId("");
  }

  function applyFilterPreset(preset) {
    if (activePresetId === preset.id) {
      clearFilterPreset();
      return;
    }
    const config = preset.config || {};
    setFilterConfig(config);
    setActivePresetId(preset.id);
  }

  function deleteFilterPreset(id) {
    persistPresets(filterPresets.filter((preset) => preset.id !== id));
    if (activePresetId === id) setActivePresetId("");
  }

  function handleOpportunitySectionClick(event) {
    if (!pendingSymbol) return;
    if (event.target.closest("tbody tr")) return;
    setPendingSymbol("");
  }

  const rows = data?.recommendations || [];
  const availableIndustries = [
    ...new Set([
      ...(marketMeta?.industries || []),
      ...rows.map((row) => row.underlying_industry).filter(Boolean)
    ])
  ].sort((a, b) => a.localeCompare(b));
  const filteredRows = rows.filter((row) => {
    const activeOk = Number(row.days_to_maturity) > 0;
    const maturityOk =
      !maturityMax || Number(row.days_to_maturity) <= Number(maturityMax);
    const priceOk = !priceMax || Number(row.market_price) <= Number(priceMax);
    const gearOk = !gearMin || Number(row.effective_gearing) >= Number(gearMin);
    const deltaOk = !deltaMin || Number(row.delta) >= Number(deltaMin);
    const thetaOk = !thetaMax || Math.abs(Number(row.theta_daily_burn)) <= Number(thetaMax);
    const ivHvSpread = Math.abs(Number(row.implied_volatility_pct) - Number(row.historical_volatility_pct));
    const ivHvOk = !ivHvMax || ivHvSpread <= Number(ivHvMax);
    const signal = row.recommendation_signal?.toUpperCase() || "";
    const signalOk =
      signalFilter === "all" ||
      (signalFilter === "strong_buy" && signal.includes("STRONG")) ||
      (signalFilter === "buy" && signal.includes("BUY") && !signal.includes("STRONG")) ||
      (signalFilter === "skip" && signal.includes("SKIP"));
    const industryOk =
      !industryFilter ||
      (row.underlying_industry || "Unknown").toLowerCase() === industryFilter.toLowerCase();

    return activeOk && maturityOk && priceOk && gearOk && deltaOk && thetaOk && ivHvOk && signalOk && industryOk;
  });

  const totalPages = Math.ceil(filteredRows.length / limit);
  const safeCurrentPage = Math.min(currentPage, Math.max(1, totalPages));
  const startIndex = (safeCurrentPage - 1) * limit;
  const endIndex = Math.min(startIndex + limit, filteredRows.length);
  const paginatedRows = filteredRows.slice(startIndex, endIndex);

  function handleFilterEnter(event) {
    if (event.key === "Enter") {
      loadOpportunities();
    }
  }

  function openDetail(symbol) {
    const normalized = symbol.trim().toUpperCase();
    setSelectedSymbol(normalized);
    setPage("detail");
  }

  function handleRowClick(symbol) {
    if (Date.now() < suppressTableRowClickUntilRef.current) {
      return;
    }
    const normalized = symbol.trim().toUpperCase();
    if (pendingSymbol === normalized) {
      openDetail(normalized);
      return;
    }
    setPendingSymbol(normalized);
  }

  function handleTablePointerDown(event) {
    if (event.button !== 0) return;
    if (event.target.closest("button, input, select, a")) return;
    const tableWrap = tableScrollRef.current;
    if (!tableWrap || tableWrap.scrollWidth <= tableWrap.clientWidth) return;
    tableDragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      scrollLeft: tableWrap.scrollLeft,
      moved: false,
      active: false
    };
  }

  function handleTablePointerMove(event) {
    const drag = tableDragRef.current;
    const tableWrap = tableScrollRef.current;
    if (!drag || !tableWrap || drag.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - drag.startX;
    if (Math.abs(deltaX) > 12) {
      drag.moved = true;
      if (!drag.active) {
        drag.active = true;
        tableWrap.setPointerCapture?.(event.pointerId);
        tableWrap.classList.add("is-dragging");
      }
      event.preventDefault();
      tableWrap.scrollLeft = drag.scrollLeft - deltaX;
    }
  }

  function endTableDrag(event) {
    const drag = tableDragRef.current;
    const tableWrap = tableScrollRef.current;
    if (!drag || !tableWrap) return;
    tableWrap.releasePointerCapture?.(drag.pointerId || event.pointerId);
    tableWrap.classList.remove("is-dragging");
    if (drag.moved) {
      suppressTableRowClickUntilRef.current = Date.now() + 180;
    }
    tableDragRef.current = null;
  }

  return (
    <section className="page-section" onClick={handleOpportunitySectionClick}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isEnglish ? "Covered warrants" : "Chứng quyền"}</p>
          <h2>{isEnglish ? "CW Opportunities" : "Cơ hội CW"}</h2>
        </div>
        <div className="section-actions">
          <Button onClick={() => loadOpportunities()}>
            <Search size={16} />
            {isEnglish ? "Load data" : "Tải dữ liệu"}
          </Button>
          <Button variant="secondary" onClick={() => loadOpportunities({ forceRefresh: true })}>
            <RefreshCw size={16} />
            {isEnglish ? "Refresh live" : "Quét thị trường"}
          </Button>
        </div>
      </div>

      <div className="filters">
        <label>
          {isEnglish ? "Strategy" : "Chiến lược"}
          <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
            <option value="balanced">{isEnglish ? "Balanced" : "Cân bằng"}</option>
            <option value="safe">{isEnglish ? "Safe" : "An toàn"}</option>
            <option value="aggressive">{isEnglish ? "Aggressive" : "Mạo hiểm"}</option>
          </select>
        </label>
        <label>
          {isEnglish ? "Underlying" : "Mã cơ sở"}
          <input
            value={underlying}
            onChange={(e) => setUnderlying(e.target.value.toUpperCase())}
            onKeyDown={handleFilterEnter}
            placeholder="HPG, FPT..."
          />
        </label>
        <label>
          {isEnglish ? "Rows per page" : "Số dòng / trang"}
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={55}>55</option>
            <option value={100}>100</option>
          </select>
        </label>
      </div>

      <div className="quick-filters" aria-label={isEnglish ? "Quick filters" : "Bộ lọc nhanh"}>
        <label>
          {isEnglish ? "Maturity max" : "Đáo hạn tối đa"}
          <input
            type="number"
            min="1"
            value={maturityMax}
            onChange={(e) => setMaturityMax(e.target.value)}
            onKeyDown={handleFilterEnter}
            placeholder={isEnglish ? "Days" : "Ngày"}
          />
        </label>
        <label>
          {isEnglish ? "Buy price max" : "Giá mua tối đa"}
          <input
            type="number"
            min="0"
            value={priceMax}
            onChange={(e) => setPriceMax(e.target.value)}
            onKeyDown={handleFilterEnter}
            placeholder="VD: 2500"
          />
        </label>
        <label>
          Signal
          <select
            value={signalFilter}
            onChange={(e) => setSignalFilter(e.target.value)}
          >
            <option value="all">{isEnglish ? "All signals" : "Tất cả tín hiệu"}</option>
            <option value="strong_buy">STRONG BUY</option>
            <option value="buy">BUY</option>
            <option value="skip">SKIP</option>
          </select>
        </label>
        <label>
          {isEnglish ? "Sector" : "Ngành / lĩnh vực"}
          <select
            value={industryFilter}
            onChange={(e) => setIndustryFilter(e.target.value)}
          >
            <option value="">{isEnglish ? "All sectors" : "Tất cả ngành"}</option>
            {availableIndustries.map((industryName) => (
              <option key={industryName} value={industryName}>
                {displayIndustry(industryName, language)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="quick-filters advanced-filters" aria-label="Quant filters">
        <label>
          Gear min
          <input
            type="number"
            min="0"
            step="0.1"
            value={gearMin}
            onChange={(e) => setGearMin(e.target.value)}
            onKeyDown={handleFilterEnter}
            placeholder="VD: 3"
          />
        </label>
        <label>
          Delta min
          <input
            type="number"
            min="0"
            max="1"
            step="0.01"
            value={deltaMin}
            onChange={(e) => setDeltaMin(e.target.value)}
            onKeyDown={handleFilterEnter}
            placeholder="VD: 0.25"
          />
        </label>
        <label>
          Theta max
          <input
            type="number"
            min="0"
            step="1"
            value={thetaMax}
            onChange={(e) => setThetaMax(e.target.value)}
            onKeyDown={handleFilterEnter}
            placeholder="VD: 15"
          />
        </label>
        <label>
          IV-HV max
          <input
            type="number"
            min="0"
            step="1"
            value={ivHvMax}
            onChange={(e) => setIvHvMax(e.target.value)}
            onKeyDown={handleFilterEnter}
            placeholder="VD: 20"
          />
        </label>
      </div>

      <div className="filter-presets" aria-label={isEnglish ? "Saved filter presets" : "Bộ lọc đã lưu"}>
        <div className="preset-save">
          <label>
            {isEnglish ? "Preset name" : "Tên bộ lọc"}
            <input
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveFilterPreset()}
              placeholder={isEnglish ? "High liquidity setup" : "Thanh khoản cao"}
            />
          </label>
          <Button variant="secondary" onClick={saveFilterPreset} disabled={!presetName.trim()}>
            <Save size={16} />
            {isEnglish ? "Save setup" : "Lưu bộ lọc"}
          </Button>
        </div>
        {filterPresets.length ? (
          <div className="preset-list">
            {filterPresets.map((preset) => (
              <span className={`preset-chip ${activePresetId === preset.id ? "active" : ""}`} key={preset.id}>
                <button type="button" onClick={() => applyFilterPreset(preset)}>
                  <Bookmark size={14} />
                  {preset.name}
                </button>
                <button
                  type="button"
                  className="preset-delete"
                  onClick={() => deleteFilterPreset(preset.id)}
                  aria-label={`Delete ${preset.name}`}
                >
                  <Trash2 size={14} />
                </button>
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {error ? <ErrorBox message={error} language={language} /> : null}
      {loading ? <LoadingBox message={isEnglish ? "Loading CW opportunities..." : "Đang tải cơ hội CW..."} /> : null}
      {pendingSymbol ? (
        <div className="notice info">
          {isEnglish ? "Selected" : "Đã chọn"} <strong>{pendingSymbol}</strong>.
          {isEnglish
            ? " Click the same code again to open its detail page."
            : " Bấm cùng mã này lần nữa để mở trang chi tiết."}
        </div>
      ) : null}

      <div
        ref={tableScrollRef}
        className="table-wrap draggable-table"
        onPointerDown={handleTablePointerDown}
        onPointerMove={handleTablePointerMove}
        onPointerUp={endTableDrag}
        onPointerCancel={endTableDrag}
        onPointerLeave={endTableDrag}
      >
        <table>
          <thead>
            <tr>
              <th>{isEnglish ? "CW code" : "Mã CW"}</th>
              <th>CPCS</th>
              <th>{isEnglish ? "Sector" : "Ngành"}</th>
              <th>TCPH</th>
              <th className="align-right">{isEnglish ? "Price" : "Giá"}</th>
              <th className="align-right">{isEnglish ? "Underlying px" : "Giá CPCS"}</th>
              <th className="align-right">Premium</th>
              <th className="align-right">Volume</th>
              <th className="align-right">{isEnglish ? "Score" : "Điểm"}</th>
              <th className="align-right">Gearing</th>
              <th className="align-right">Delta</th>
              <th className="align-right">Theta</th>
              <th className="align-right">IV/HV</th>
              <th className="align-center">{isEnglish ? "Days left" : "Còn lại"}</th>
              <th className="align-center">{isEnglish ? "Signal" : "Tín hiệu"}</th>
            </tr>
          </thead>
          <tbody>
            {paginatedRows.length === 0 && !loading ? (
              <tr>
                <td colSpan="15" className="empty-cell">
                  {isEnglish
                    ? "No matching rows. Adjust filters or reload data."
                    : "Không có dòng phù hợp. Hãy đổi bộ lọc hoặc tải lại dữ liệu."}
                </td>
              </tr>
            ) : null}
            {paginatedRows.map((row) => (
              <tr
                key={row.warrant_symbol}
                className={pendingSymbol === row.warrant_symbol ? "selected-row" : ""}
                onClick={() => handleRowClick(row.warrant_symbol)}
                onDoubleClick={() => openDetail(row.warrant_symbol)}
              >
                <td className="strong-cell">{row.warrant_symbol}</td>
                <td>{row.underlying_symbol}</td>
                <td>{displayIndustry(row.underlying_industry, language) || "-"}</td>
                <td>{row.issuer || "-"}</td>
                <td className="align-right">{formatMoney(row.market_price)}đ</td>
                <td className="align-right">{formatMoney(row.underlying_price)}đ</td>
                <td className="align-right">{formatNumber(row.premium_pct, 1)}%</td>
                <td className="align-right">{formatMoney(row.volume)}</td>
                <td className="align-right">{formatNumber(row.composite_g_score, 1)}</td>
                <td className="align-right">{formatNumber(row.effective_gearing, 2)}x</td>
                <td className="align-right">{formatNumber(row.delta, 4)}</td>
                <td className="align-right">{formatNumber(row.theta_daily_burn, 0)}đ</td>
                <td className="align-right">
                  {formatNumber(row.implied_volatility_pct, 1)}% /{"  "}
                  {formatNumber(row.historical_volatility_pct, 1)}%
                </td>
                <td className="align-center">
                  {row.days_to_maturity ?? "-"} {isEnglish ? "days" : "ngày"}
                </td>
                <td className="align-center">
                  <span className={signalClass(row.recommendation_signal)}>
                    {formatSignal(row.recommendation_signal, isEnglish)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 ? (
        <div className="pagination-wrapper">
          <Button
            variant="secondary"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={safeCurrentPage === 1}
          >
            {isEnglish ? "Previous" : "Trang trước"}
          </Button>
          <span className="pagination-text">
            {isEnglish ? `Page ${safeCurrentPage} of ${totalPages}` : `Trang ${safeCurrentPage} / ${totalPages}`}
            <span className="pagination-sub">
              ({isEnglish ? `Showing ${startIndex + 1}-${endIndex} of ${filteredRows.length}` : `Hiển thị ${startIndex + 1}-${endIndex} của ${filteredRows.length} mã`})
            </span>
          </span>
          <Button
            variant="secondary"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={safeCurrentPage === totalPages}
          >
            {isEnglish ? "Next" : "Trang sau"}
          </Button>
        </div>
      ) : null}

      <p className="helper-text">
        {isEnglish
          ? "Click a row to select it, then click it again to open CW Detail."
          : "Bấm một dòng để chọn, sau đó bấm lại để mở Chi tiết CW."}
        {auth.isAdmin && filteredRows.length === 0 ? (
          <>
            {" "}
            {isEnglish ? "Admin note: refresh market data if the table remains empty." : "Ghi chú quản trị: hãy làm mới dữ liệu thị trường nếu bảng vẫn trống."}
          </>
        ) : null}
      </p>
    </section>
  );
}
