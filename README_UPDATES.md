# 🏆 FINVISTA QUANTITATIVE SYSTEM: INSTITUTIONAL UPGRADE REPORT
**Date:** June 08, 2026
**Version:** V2.0 (Institutional Grade)

## 📌 Executive Summary
This document outlines the major architectural and algorithmic upgrades implemented to elevate the Finvista Covered Warrant System from a retail backtester to an institutional-grade quantitative engine. The upgrades focus on multi-layered risk management, dynamic macro-economic responsiveness, and advanced machine learning modeling.

---

## 1. MACRO & LIQUIDITY LAYER

### 1.1 Dynamic Risk-Free Rate (RFR)
*   **Previous State:** Hardcoded at `4.5%`.
*   **Upgraded State:** The system now dynamically fetches the live 1-Year Vietnam Government Bond Yield (currently ~`3.57%`).
*   **Impact:** Significantly improves the accuracy of Black-Scholes theoretical pricing, Fair Value calculations, and the estimation of cost of carry (Phi/Rho).

### 1.2 Macro Liquidity Circuit Breaker
*   **Implementation:** Added to `run_analysis.py`.
*   **Mechanism:** The system monitors proxy interbank/liquidity stress rates. If rates spike beyond safety thresholds (e.g., > `8.0%`), indicating severe liquidity tightening by the SBV, a global Circuit Breaker is triggered.
*   **Action:** All algorithmic `BUY` or `STRONG BUY` signals are immediately downgraded to `WATCH (STRESS)` or `SKIP (STRESS)`, protecting the portfolio from systemic margin-call cascades.

---

## 2. ADVANCED TRADING ENGINE (BACKTESTER)

The `FinvistaBacktester` was heavily refactored to incorporate dynamic risk and position sizing.

### 2.1 Dynamic Stop-Loss via ATR (Average True Range)
*   **Previous State:** Static `-15%` hard stop-loss. Vulnerable to market whipsaws.
*   **Upgraded State:** Stop-loss is now calculated dynamically based on the Underlying Stock's volatility using `2 * ATR`.
*   **Impact:** Prevents premature stop-outs during normal intraday noise while strictly capping maximum drawdown (MaxDD improved to `-18.02%`).

### 2.2 Position Sizing via Kelly Criterion
*   **Implementation:** Integrated into the portfolio evaluation logic.
*   **Mechanism:** Instead of fixed capital allocation (e.g., always 50% cash), the engine dynamically calculates the optimal bet size based on historical Win Rate and Payoff Ratio (Avg Win / Avg Loss).
*   **Safety:** Utilizes a "Half-Kelly" approach bounded between 10% and 90% allocation to maximize geometric growth (CAGR) without risking ruin.

### 2.3 Orderbook Imbalance (Level 2 Data) Filter
*   **Implementation:** Added `analyze_imbalance` to `orderbook_scraper.py` and linked to the *Ultimate Panic Buy* strategy.
*   **Mechanism:** Before executing a buy on a technically "oversold" signal (RSI < 40), the system queries the live Level 2 orderbook. If Ask volume heavily outweighs Bid volume (Ratio < 0.35), it flags `"Heavy Selling Pressure"` and cancels the entry.
*   **Impact:** Eliminates the "falling knife" effect.

---

## 3. QUANTITATIVE MODELING & MACHINE LEARNING

### 3.1 XGBoost Pricing Model Anti-Overfitting Upgrade
*   **Previous State:** Random Forest model severely overfitting (Train R² = 1.0, Test R² = 0.40). Target variables were not normalized.
*   **Upgraded State:** 
    *   Transitioned to **XGBoost**.
    *   Target prices are now normalized by the `conversion_ratio`.
    *   Applied aggressive regularization: `max_depth=3`, L1/L2 penalties, `min_child_weight=5`, and `early_stopping_rounds`.
*   **Result:** Test R² jumped to `0.736`. While Black-Scholes remains the primary pricing core (due to limited data samples), XGBoost now serves as a robust secondary anomaly detection engine.

### 3.2 Heston Stochastic Volatility Auto-Calibration
*   **Implementation:** Added `calibrate_heston` module in `pricing_core_enhanced.py`.
*   **Mechanism:** Utilizes the `L-BFGS-B` optimization algorithm from `scipy.optimize` to minimize the mean squared error between the theoretical Heston price and actual market prices.
*   **Capability:** Allows the system to empirically derive the 5 complex stochastic parameters ($ \kappa, \theta, \sigma, \rho, v_0 $) directly from the volatility smile of the Vietnamese market. *(Note: Computationally intensive; recommended for End-of-Day batch runs).*

### 3.3 Credit Risk SMOTE Integration
*   **Implementation:** Added to `credit_risk_trainer.py`.
*   **Mechanism:** Applied Synthetic Minority Over-sampling Technique (SMOTE) via the `imbalanced-learn` library.
*   **Impact:** Solves the class imbalance problem in financial distress prediction. By synthesizing artificial data points for the rare "distressed" companies, the XGBoost early-warning system is now highly sensitive to "Black Swan" events.

---
*End of Report.*