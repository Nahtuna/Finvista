import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { HomePage } from "../features/home/HomePage.jsx";
import { AuthProvider } from "../auth/AuthProvider.jsx";

vi.mock("../api.js", () => ({
  getOpportunities: vi.fn(async () => ({ recommendations: [] })),
  setAuthTokenProvider: vi.fn(),
  API_BASE_URL: "http://127.0.0.1:8008"
}));


describe("Home navigation", () => {
  it("opens the market overview from Home and no longer renders the large CW pulse", async () => {
    const setPage = vi.fn();
    render(
      <AuthProvider>
        <HomePage
          language="en"
          setPage={setPage}
          setSelectedSymbol={vi.fn()}
        />
      </AuthProvider>
    );

    expect(screen.queryByRole("heading", { name: "Covered warrant pulse" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open market overview" }));
    expect(setPage).toHaveBeenCalledWith("market");
  });
});
