from __future__ import annotations
import os
import sys
import warnings
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM


def align_states(model: GaussianHMM) -> GaussianHMM:
    """Sort the states of GaussianHMM by average volatility in ascending order.
    State 0 will be the lowest volatility (usually Bull), and the last state will be the highest volatility (Bear).
    """
    if not hasattr(model, "_covars_"):
        return model
    
    # Calculate average variance/volatility for each state
    if model.covariance_type == "diag":
        state_vols = np.mean(model._covars_, axis=1)
    elif model.covariance_type == "full":
        state_vols = np.array([np.trace(cov) for cov in model._covars_])
    else:
        state_vols = np.arange(model.n_components)
    
    idx_sort = np.argsort(state_vols)
    
    # Permute parameters using internal raw attributes to bypass setter validation issues
    model.means_ = model.means_[idx_sort]
    model._covars_ = model._covars_[idx_sort]
    model.startprob_ = model.startprob_[idx_sort]
    model.transmat_ = model.transmat_[np.ix_(idx_sort, idx_sort)]
    
    return model


def fit_hmm(returns: pd.DataFrame, n_states: int = 3, covariance_type: str = "full", random_state: int = 42) -> GaussianHMM:
    x = np.asarray(returns.values, dtype=float)
    model = GaussianHMM(
        n_components=n_states,
        covariance_type=covariance_type,
        n_iter=500,
        tol=1e-4,
        random_state=random_state,
        verbose=False,
        init_params="mcs",
        params="mcs",
    )
    devnull = open(os.devnull, "w")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = devnull
    sys.stderr = devnull
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(x)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        devnull.close()
    
    # Align states by volatility to prevent state swapping in rolling windows
    if is_valid_model(model):
        model = align_states(model)
        
    return model


def is_valid_model(model: GaussianHMM) -> bool:
    if not hasattr(model, "startprob_") or model.startprob_ is None:
        return False
    sp = model.startprob_
    tm = model.transmat_
    if not np.isfinite(sp).all():
        return False
    if not np.isfinite(tm).all():
        return False
    if abs(sp.sum() - 1.0) > 0.01:
        return False
    if not (tm.sum(axis=1) > 0.5).all():
        return False
    return True


def posterior_probs(model: GaussianHMM, returns: pd.DataFrame) -> pd.DataFrame:
    x = np.asarray(returns.values, dtype=float)
    _, post = model.score_samples(x)
    return pd.DataFrame(post, index=returns.index, columns=[f"state_{i}" for i in range(model.n_components)])


def viterbi_path(model: GaussianHMM, returns: pd.DataFrame) -> pd.Series:
    x = np.asarray(returns.values, dtype=float)
    states = model.predict(x)
    return pd.Series(states, index=returns.index, name="state")


def regime_stats_by_label(returns: pd.DataFrame, labels: pd.Series):
    stats = {}
    for k in np.unique(labels.values):
        mask = (labels.values == k)
        r = returns.iloc[mask]
        mu = r.mean()
        cov = r.cov()
        stats[int(k)] = {"mu": mu, "cov": cov, "returns": r}
    return stats


def compute_bic(model: GaussianHMM, returns: pd.DataFrame) -> float:
    """Calculates Bayesian Information Criterion (BIC) for the HMM."""
    x = np.asarray(returns.values, dtype=float)
    log_likelihood = model.score(x)
    n_features = returns.shape[1]
    n_states = model.n_components
    n_params = n_states * (n_states - 1) + (n_states - 1) + n_states * n_features
    if model.covariance_type == "diag":
        n_params += n_states * n_features
    elif model.covariance_type == "full":
        n_params += n_states * n_features * (n_features + 1) // 2
    
    n_samples = x.shape[0]
    return -2.0 * log_likelihood + n_params * np.log(n_samples)


def compute_aic(model: GaussianHMM, returns: pd.DataFrame) -> float:
    """Calculates Akaike Information Criterion (AIC) for the HMM."""
    x = np.asarray(returns.values, dtype=float)
    log_likelihood = model.score(x)
    n_features = returns.shape[1]
    n_states = model.n_components
    n_params = n_states * (n_states - 1) + (n_states - 1) + n_states * n_features
    if model.covariance_type == "diag":
        n_params += n_states * n_features
    elif model.covariance_type == "full":
        n_params += n_states * n_features * (n_features + 1) // 2
    
    return -2.0 * log_likelihood + 2.0 * n_params


class HybridRegimeModel:
    """
    Wraps a 2-state GaussianHMM and a binary Trend indicator to expose
    a unified 4-state interface compatible with the portfolio backtester.
    """
    def __init__(self, hmm_model, scaler, trends, train_states, train_probs, transmat, startprob):
        self.hmm_model = hmm_model
        self.scaler = scaler
        self.trends = np.asarray(trends, dtype=int)
        self.train_states = np.asarray(train_states, dtype=int)
        self.train_probs = np.asarray(train_probs, dtype=float)
        self.n_components = 4
        self.transmat_ = transmat
        self.startprob_ = startprob

    def predict(self, X) -> np.ndarray:
        if len(X) == len(self.train_states):
            return self.train_states
        return self.train_states[-len(X):]

    def predict_proba(self, X) -> np.ndarray:
        if len(X) == len(self.train_probs):
            return self.train_probs
        # If length is different, calculate HMM probs and map using the corresponding trends
        hmm_probs = self.hmm_model.predict_proba(X)
        probs = np.zeros((len(X), 4), dtype=float)
        for t in range(len(X)):
            idx = -len(X) + t
            tr = self.trends[idx] if abs(idx) <= len(self.trends) else 1
            if tr == 1:
                probs[t] = [hmm_probs[t, 0], hmm_probs[t, 1], 0.0, 0.0]
            else:
                probs[t] = [0.0, 0.0, hmm_probs[t, 0], hmm_probs[t, 1]]
        return probs


def calculate_kama(series: pd.Series, er_period: int = 10, fast: int = 2, slow: int = 30) -> pd.Series:
    """Calculates Kaufman's Adaptive Moving Average (KAMA)."""
    change = series.diff(er_period).abs()
    volatility = series.diff(1).abs().rolling(window=er_period).sum()
    
    er = change / volatility.replace(0, np.nan)
    er = er.fillna(0)
    
    fast_alpha = 2.0 / (fast + 1)
    slow_alpha = 2.0 / (slow + 1)
    
    sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
    
    kama = np.zeros_like(series.values, dtype=float)
    kama[:] = np.nan
    
    first_valid = sc.first_valid_index()
    if first_valid is None:
        return pd.Series(kama, index=series.index)
        
    start_idx = series.index.get_loc(first_valid)
    kama[start_idx] = series.iloc[start_idx]
    
    prices = series.values
    sc_vals = sc.values
    
    for i in range(start_idx + 1, len(series)):
        kama[i] = kama[i-1] + sc_vals[i] * (prices[i] - kama[i-1])
        
    return pd.Series(kama, index=series.index)


def prepare_vnindex_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes hybrid HMM features for VNINDEX: KAMA Trend, Log Returns, 20D Volatility, Log Volume Ratio.
    df must have 'close' and 'volume' columns.
    """
    df = df.copy().sort_index()
    if len(df) < 50:
        raise ValueError("Not enough data to calculate rolling features (need >= 50 sessions for KAMA)")
        
    df['kama'] = calculate_kama(df['close'], er_period=10, fast=2, slow=30)
    df['trend'] = (df['close'].rolling(5, min_periods=1).mean() > df['kama']).astype(int)
    
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df['rolling_vol'] = df['log_return'].rolling(window=10).std() * np.sqrt(252)
    df['rolling_volume_ma'] = df['volume'].rolling(window=10).mean()
    df['log_volume_ratio'] = np.log(df['volume'] / df['rolling_volume_ma'].replace(0, np.nan))
    
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.dropna().copy()
    return df


def fit_vnindex_hmm(features_df: pd.DataFrame, n_states: int = 4, random_state: int = 42) -> tuple:
    """
    Fits a 2-state HMM on standardized features, combines it with the trend filter
    to produce a 4-state Hybrid model, and returns (HybridRegimeModel, scaler).
    """
    from sklearn.preprocessing import StandardScaler
    X_raw = features_df[['log_return', 'rolling_vol', 'log_volume_ratio']].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    
    # Train HMM Model (2 States: Low Vol vs High Vol)
    model = GaussianHMM(
        n_components=2,
        covariance_type="full",
        n_iter=500,
        tol=1e-4,
        random_state=random_state,
        init_params="mcs",
        params="mcs",
    )
    
    # Suppress output during training
    import os, sys, warnings
    devnull = open(os.devnull, "w")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = devnull
    sys.stderr = devnull
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(X_scaled)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        devnull.close()
        
    if is_valid_model(model):
        # State Alignment (Sort by volatility of log returns)
        states = model.predict(X_scaled)
        state_vols = []
        for k in range(2):
            mask = (states == k)
            state_vols.append(features_df.iloc[mask]['log_return'].std() if mask.any() else 999.0)
            
        idx_sort = np.argsort(state_vols)
        
        # Permute parameters
        model.startprob_ = model.startprob_[idx_sort]
        model.transmat_ = model.transmat_[np.ix_(idx_sort, idx_sort)]
        model.means_ = model.means_[idx_sort]
        model._covars_ = model._covars_[idx_sort]
        
    # Re-predict with aligned 2 HMM states (0: Low Vol, 1: High Vol)
    hmm_states = model.predict(X_scaled)
    
    # Combine HMM with trend to form 4 combined states
    trends = features_df['trend'].values.astype(int)
    combined_states = 2 * (1 - trends) + hmm_states
    
    # Generate 4-state probability matrix
    hmm_probs = model.predict_proba(X_scaled)
    T = len(X_scaled)
    combined_probs = np.zeros((T, 4), dtype=float)
    for t in range(T):
        tr = trends[t]
        p_low = hmm_probs[t, 0]
        p_high = hmm_probs[t, 1]
        if tr == 1:
            combined_probs[t] = [p_low, p_high, 0.0, 0.0]
        else:
            combined_probs[t] = [0.0, 0.0, p_low, p_high]
            
    # Calculate transition matrix and start probabilities for the 4 combined states
    # to pass validation checks
    transmat = np.zeros((4, 4), dtype=float)
    for i in range(T - 1):
        transmat[combined_states[i], combined_states[i+1]] += 1.0
    for i in range(4):
        s = transmat[i].sum()
        if s > 0:
            transmat[i] = transmat[i] / s
        else:
            transmat[i] = np.ones(4) / 4.0
            
    counts = np.bincount(combined_states, minlength=4)
    startprob = counts / float(T)
    
    hybrid_model = HybridRegimeModel(
        hmm_model=model,
        scaler=scaler,
        trends=trends,
        train_states=combined_states,
        train_probs=combined_probs,
        transmat=transmat,
        startprob=startprob
    )
    
    return hybrid_model, scaler


def fit_vnindex_hmm_walkforward(features_df: pd.DataFrame,
                                  train_window: int = 500,
                                  test_window: int = 50,
                                  n_restarts: int = 3,
                                  vol_threshold: float = 0.20,
                                  random_state: int = 42,
                                  three_state: bool = False) -> tuple:
    """
    Walk-forward validation for VNINDEX HMM regime detection.

    Parameters:
    - features_df: DataFrame with KAMA trend, log_return, rolling_vol, log_volume_ratio
    - train_window: Training window size in days (default 500)
    - test_window: Test window size in days (default 50)
    - n_restarts: Number of EM restarts per window to avoid local optima (default 3)
    - vol_threshold: Fixed, causal, absolute annualised-vol cutoff (default 0.20 = 20%/yr).
      A window's "high vol" cluster is only treated as a real High-Vol regime if its
      average annualised volatility clears this threshold. Otherwise, the whole test
      window is forced to "Low Vol" instead of being split by within-window rank alone.
    - random_state: Base random seed
    - three_state: If True, use 3-state HMM (Low/Medium/High Vol) instead of 2-state

    Returns:
    - walk_forward_states: full array of 4-state labels (NaN outside coverage) for 2-state
                             or 3-state labels (0,1,2) for three_state mode
    - walk_forward_probs:  full array of probabilities (NaN outside coverage)
    - coverage_mask:       boolean array, True where a walk-forward label exists
    - window_meta:         list of dicts, one per window, for auditing
    """
    from sklearn.preprocessing import StandardScaler
    import warnings

    T = len(features_df)
    if T < train_window + test_window:
        raise ValueError(f"Data too short: {T} days, need at least {train_window + test_window}")

    walk_forward_states = np.full(T, np.nan)
    walk_forward_probs = np.full((T, 3 if three_state else 4), np.nan)
    coverage_mask = np.zeros(T, dtype=bool)
    window_meta = []

    trends = features_df['trend'].values.astype(int)
    X_raw = features_df[['log_return', 'rolling_vol', 'log_volume_ratio']].values

    start_idx = 0
    while start_idx + train_window + test_window <= T:
        train_end = start_idx + train_window
        test_end = train_end + test_window

        print(f"  Window {start_idx}-{train_end} (train) -> {train_end}-{test_end} (test)")

        X_train_raw = X_raw[start_idx:train_end]
        trends_train = trends[start_idx:train_end]

        # Fit scaler ONLY on this training window (no look-ahead)
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train_raw)

        # Fit HMM with multiple restarts to avoid EM local optima
        n_hmm_states = 3 if three_state else 2
        best_model = None
        best_score = -np.inf
        for restart in range(n_restarts):
            rs = random_state + restart * 1000
            model = GaussianHMM(
                n_components=n_hmm_states, covariance_type="full",
                n_iter=500, tol=1e-4, random_state=rs,
                init_params="mcs", params="mcs",
            )
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(X_train)
                if is_valid_model(model):
                    score = model.score(X_train)
                    if score > best_score:
                        best_score = score
                        best_model = model
            except Exception as e:
                print(f"    Restart {restart} failed: {e}")
                continue

        if best_model is None:
            print(f"  [!] Window {start_idx}: no valid model found, skipping")
            start_idx += test_window
            continue

        hmm_states_train = best_model.predict(X_train)

        # Actual annualised vol of each raw HMM state cluster (train window)
        state_actual_vols = []
        for k in range(n_hmm_states):
            mask = hmm_states_train == k
            if mask.any():
                daily_std = features_df.iloc[start_idx:train_end].loc[mask, 'log_return'].std()
                state_actual_vols.append(daily_std * np.sqrt(252))
            else:
                state_actual_vols.append(0.0)

        # Keep internal Gaussian components ordered low->high (for transmat/means consistency)
        idx_sort = np.argsort(state_actual_vols)
        best_model.startprob_ = best_model.startprob_[idx_sort]
        best_model.transmat_ = best_model.transmat_[np.ix_(idx_sort, idx_sort)]
        best_model.means_ = best_model.means_[idx_sort]
        best_model._covars_ = best_model._covars_[idx_sort]
        sorted_vols = np.array(state_actual_vols)[idx_sort]  # [low_state_vol, ...]

        # For 2-state: window_had_real_crisis checks if high vol clears threshold
        # For 3-state: check if high vol (index 2) clears threshold
        if three_state:
            # 3-state: Low (0), Medium (1), High (2)
            # High vol regime only considered "real" if it clears threshold
            window_had_real_crisis = bool(sorted_vols[2] >= vol_threshold)
            window_meta.append({
                "start": start_idx, "train_end": train_end, "test_end": test_end,
                "low_state_vol": float(sorted_vols[0]), 
                "medium_state_vol": float(sorted_vols[1]),
                "high_state_vol": float(sorted_vols[2]),
                "window_had_real_crisis": window_had_real_crisis,
            })
        else:
            # 2-state: Low (0), High (1)
            window_had_real_crisis = bool(sorted_vols[1] >= vol_threshold)
            window_meta.append({
                "start": start_idx, "train_end": train_end, "test_end": test_end,
                "low_state_vol": float(sorted_vols[0]), "high_state_vol": float(sorted_vols[1]),
                "window_had_real_crisis": window_had_real_crisis,
            })

        # Predict on test window (scale with the SAME scaler fit on train)
        X_test_raw = X_raw[train_end:test_end]
        X_test = scaler.transform(X_test_raw)
        trends_test = trends[train_end:test_end]

        hmm_states_test = best_model.predict(X_test)       # already re-ordered 0=low, 1=med, 2=high (or 0=low, 1=high)
        hmm_probs_test = best_model.predict_proba(X_test)  # columns already re-ordered

        if three_state:
            # 3-State Logic:
            # If the highest-vol cluster clears threshold, use actual HMM states (0,1,2)
            # Otherwise, collapse: force everyone to "Low Vol" (state 0)
            if window_had_real_crisis:
                semantic_states_test = hmm_states_test  # 0, 1, 2 as-is
                p_low_test = hmm_probs_test[:, 0]
                p_med_test = hmm_probs_test[:, 1]
                p_high_test = hmm_probs_test[:, 2]
            else:
                # Collapse: whole window is calm -> force everyone "Low Vol"
                semantic_states_test = np.zeros(len(hmm_states_test), dtype=int)
                p_low_test = np.ones(len(hmm_states_test))
                p_med_test = np.zeros(len(hmm_states_test))
                p_high_test = np.zeros(len(hmm_states_test))

            # Combine with trend: 3 states × 2 trends = 6 possible, but we map to 3 semantic states
            # Since 3-state HMM already captures volatility levels, we use HMM states directly
            # The trend is logged but not used for state combination in 3-state mode
            combined_states_test = semantic_states_test
            combined_probs_test = np.column_stack([p_low_test, p_med_test, p_high_test])
        else:
            # 2-State Logic (original)
            if window_had_real_crisis:
                semantic_high_test = hmm_states_test                     # 0/1 as-is
                p_low_test = hmm_probs_test[:, 0]
                p_high_test = hmm_probs_test[:, 1]
            else:
                # Collapse: whole window is calm -> force everyone "Low Vol"
                semantic_high_test = np.zeros(len(hmm_states_test), dtype=int)
                p_low_test = np.ones(len(hmm_states_test))
                p_high_test = np.zeros(len(hmm_states_test))

            combined_states_test = 2 * (1 - trends_test) + semantic_high_test
            combined_probs_test = np.zeros((len(X_test), 4), dtype=float)
            for t in range(len(X_test)):
                tr = trends_test[t]
                if tr == 1:
                    combined_probs_test[t] = [p_low_test[t], p_high_test[t], 0.0, 0.0]
                else:
                    combined_probs_test[t] = [0.0, 0.0, p_low_test[t], p_high_test[t]]

        walk_forward_states[train_end:test_end] = combined_states_test
        walk_forward_probs[train_end:test_end] = combined_probs_test
        coverage_mask[train_end:test_end] = True

        start_idx += test_window

    return walk_forward_states, walk_forward_probs, coverage_mask, window_meta


def fit_vnindex_hmm_3state(features_df: pd.DataFrame, random_state: int = 42) -> tuple:
    """
    Fits a 3-state HMM directly on standardized features for 3-state HMM mode.
    Returns (HMMModelWrapper, scaler).
    """
    from sklearn.preprocessing import StandardScaler
    from hmmlearn.hmm import GaussianHMM
    import os, sys, warnings
    
    X_raw = features_df[['log_return', 'rolling_vol', 'log_volume_ratio']].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    
    # Train 3-State HMM Model
    model = GaussianHMM(
        n_components=3,
        covariance_type="full",
        n_iter=500,
        tol=1e-4,
        random_state=random_state,
        init_params="mcs",
        params="mcs",
    )
    
    # Suppress output during training
    devnull = open(os.devnull, "w")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = devnull
    sys.stderr = devnull
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(X_scaled)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        devnull.close()
    
    # Sort states by volatility
    if is_valid_model(model):
        states = model.predict(X_scaled)
        state_vols = []
        for k in range(3):
            mask = (states == k)
            if mask.any():
                state_vols.append(features_df.iloc[mask]['log_return'].std())
            else:
                state_vols.append(999.0)
        
        idx_sort = np.argsort(state_vols)
        
        # Permute parameters
        model.startprob_ = model.startprob_[idx_sort]
        model.transmat_ = model.transmat_[np.ix_(idx_sort, idx_sort)]
        model.means_ = model.means_[idx_sort]
        model._covars_ = model._covars_[idx_sort]
    
    return model, scaler
