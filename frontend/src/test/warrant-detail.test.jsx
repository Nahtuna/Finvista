import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WarrantDetailPage } from "../features/warrant-detail/WarrantDetailPage.jsx";
import { AuthProvider } from "../auth/AuthProvider.jsx";
import { DataProvider } from "../app/DataContext.jsx";


vi.mock("../api.js", () => ({
  getWarrantSimulation: vi.fn(async () => ({
    symbol: "CSHB2607",
    underlying_symbol: "SHB",
    current_price: 1170,
    underlying_current_price: 14000,
    volume: 50300,
    strike_price: 15500,
    premium_pct: 27.43,
    effective_gearing: 3.24,
    delta: 0.2704,
    theta_daily_burn: -3,
    implied_volatility_pct: 59.57,
    days_to_maturity: 250,
    scenarios: [
      {
        holding_days: 0,
        remaining_days: 250,
        matrix: [{ change_pct: 0, theoretical_price: 1200, p_l_pct: 2.56 }]
      }
    ]
  })),
  getWarrantHistory: vi.fn(async () => ({
    averages: {
      average_hv_pct: 31.42
    },
    history: [
      {
        date: "2026-06-05",
        warrant_price: 1170,
        underlying_price: 14000,
        theoretical_price: 0,
        pricing_gap_pct: -100,
        warrant_ohlc: { open: 1170, high: 1170, low: 1170, close: 1170, volume: 50300 },
        implied_volatility_pct: 59.57,
        historical_volatility_pct: 31.42
      }
    ]
  })),
  refreshMarketScan: vi.fn(async () => ({})),
  getPortfolio: vi.fn(async () => null),
  getMarketRegime: vi.fn(async () => null),
  getFireantArticles: vi.fn(async () => []),
  getOpportunities: vi.fn(async () => ({ recommendations: [] })),
  getUnderlyingMarket: vi.fn(async () => ({ indices: [] })),
  setAuthTokenProvider: vi.fn(),
  API_BASE_URL: "http://127.0.0.1:8008"
}));


describe("Warrant detail page", () => {
  it("shows HV in the summary and makes detail tables draggable", async () => {
    const { container } = render(
      <AuthProvider>
        <DataProvider>
          <WarrantDetailPage
            selectedSymbol="CSHB2607"
            setSelectedSymbol={vi.fn()}
            language="en"
          />
        </DataProvider>
      </AuthProvider>
    );

    expect((await screen.findAllByText("CSHB2607")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("HV").length).toBeGreaterThan(0);
    expect(screen.getByText("31.42%")).toBeInTheDocument();
    expect(container.querySelectorAll(".table-wrap.draggable-table")).toHaveLength(2);
  });
});
