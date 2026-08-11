import "../../node_modules/@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

vi.stubEnv("VITE_AUTH_ENABLED", "true");

// lightweight-charts / fancy-canvas require matchMedia, ResizeObserver, and
// real canvas APIs that JSDOM doesn't support. Mock the whole library so any
// component that imports it renders as a no-op <div> instead of crashing.
vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => ({
    addCandlestickSeries: vi.fn(() => ({ setData: vi.fn(), setMarkers: vi.fn(), applyOptions: vi.fn() })),
    addLineSeries: vi.fn(() => ({ setData: vi.fn(), setMarkers: vi.fn(), applyOptions: vi.fn() })),
    addHistogramSeries: vi.fn(() => ({ setData: vi.fn(), applyOptions: vi.fn() })),
    timeScale: vi.fn(() => ({ fitContent: vi.fn(), scrollToPosition: vi.fn(), subscribeVisibleLogicalRangeChange: vi.fn(), unsubscribeVisibleLogicalRangeChange: vi.fn() })),
    subscribeCrosshairMove: vi.fn(),
    unsubscribeCrosshairMove: vi.fn(),
    applyOptions: vi.fn(),
    resize: vi.fn(),
    remove: vi.fn()
  }))
}));

if (!window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn()
    }))
  });
}

if (!window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

afterEach(() => {
  cleanup();
  localStorage.clear();
});
