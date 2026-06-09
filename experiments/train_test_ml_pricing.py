# -*- coding: utf-8 -*-
"""
🤖 ML PRICING MODEL - TRAIN, TEST, SIMULATE
============================================
Train ML model on historical CW data, test performance, and simulate trading.

Based on research showing ML can outperform traditional option pricing models.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

from src.quant.pricing.pricing_core import RISK_FREE_RATE

print("=" * 80)
print("ML PRICING MODEL - TRAIN, TEST, SIMULATE")
print("=" * 80)

# ==========================================
# 1. LOAD DATA
# ==========================================

print("\n" + "=" * 80)
print("1. LOAD HISTORICAL DATA")
print("=" * 80)

from src.common.database import engine

# Load market opportunities data
df = pd.read_sql('SELECT * FROM market_opportunities', engine)

print(f"📊 Total CWs: {len(df)}")

# Filter valid data
df = df.dropna(subset=[
    'price', 'theoretical_price', 'underlying_price', 'strike_price', 
    'days_to_maturity', 'implied_volatility_pct'
])

print(f"📊 Valid CWs after filtering: {len(df)}")

# Parse conversion ratio (e.g. '2:1' or '4.0000')
def parse_ratio(ratio_val):
    if pd.isna(ratio_val): return 1.0
    if isinstance(ratio_val, str):
        if ':' in ratio_val:
            parts = ratio_val.split(':')
            try: return float(parts[0]) / float(parts[1]) if float(parts[1]) != 0 else 1.0
            except: return 1.0
        try: return float(ratio_val)
        except: return 1.0
    return float(ratio_val)

df['parsed_ratio'] = df['ratio'].apply(parse_ratio)

# Normalize price to 1 underlying share
df['normalized_price'] = df['price'] * df['parsed_ratio']

# ==========================================
# 2. PREPARE FEATURES
# ==========================================

print("\n" + "=" * 80)
print("2. PREPARE FEATURES FOR ML MODEL")
print("=" * 80)

def create_features(df):
    """Create features for ML pricing model based on research."""
    features = pd.DataFrame()
    
    # Basic pricing inputs
    features['S'] = df['underlying_price']
    features['K'] = df['strike_price']
    features['T'] = df['days_to_maturity'] / 365.0
    features['r'] = RISK_FREE_RATE  # Dynamic Risk-free rate
    
    # Moneyness features (important for option pricing)
    features['moneyness'] = df['underlying_price'] / df['strike_price']
    features['log_moneyness'] = np.log(features['moneyness'])
    
    # Volatility features
    features['implied_volatility'] = df['implied_volatility_pct'] / 100.0
    features['historical_volatility'] = df.get('historical_volatility_pct', 45.0) / 100.0
    
    # Liquidity features
    features['volume'] = df['volume']
    features['turnover'] = df['turnover']
    
    # Greeks (useful features)
    features['delta'] = df['delta']
    features['gamma'] = df['gamma']
    features['theta'] = df['theta_burn_day']
    features['vega'] = df['vega']
    
    # Risk metrics
    features['premium_pct'] = df['premium_pct'] / 100.0
    features['gearing'] = df['gearing']
    
    # Probability features
    features['prob_itm'] = df['prob_itm']
    
    # Additional derived features
    features['S_K_ratio'] = features['S'] / features['K']
    features['T_sqrt'] = np.sqrt(features['T'])
    features['volatility_T'] = features['implied_volatility'] * features['T_sqrt']
    
    return features

X = create_features(df)
y = df['normalized_price']  # Target: normalized market price

print(f"📊 Features shape: {X.shape}")
print(f"📊 Target shape: {y.shape}")

# ==========================================
# 3. SPLIT TRAIN/TEST
# ==========================================

print("\n" + "=" * 80)
print("3. SPLIT TRAIN/TEST SETS")
print("=" * 80)

# Use 80% train, 20% test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"📊 Train set: {len(X_train)} samples")
print(f"📊 Test set: {len(X_test)} samples")

# ==========================================
# 4. TRAIN ML MODEL
# ==========================================

print("\n" + "=" * 80)
print("4. TRAIN XGBOOST MODEL (Anti-Overfitting)")
print("=" * 80)

model = xgb.XGBRegressor(
    n_estimators=500,
    learning_rate=0.03,
    max_depth=3,               # Reduced from 6 to prevent deep memorization
    min_child_weight=5,        # Require more samples in a node to split
    subsample=0.7,
    colsample_bytree=0.7,
    reg_alpha=0.5,             # L1 regularization to penalize complex trees
    reg_lambda=2.0,            # L2 regularization
    random_state=42,
    n_jobs=-1,
    early_stopping_rounds=30
)

print("🔄 Training model...")
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)
print("✅ Training completed!")

# Feature importance
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n📊 Top 10 Important Features:")
print(feature_importance.head(10).to_string(index=False))

# ==========================================
# 5. TEST MODEL
# ==========================================

print("\n" + "=" * 80)
print("5. TEST MODEL PERFORMANCE")
print("=" * 80)

# Predictions
y_train_pred = model.predict(X_train)
y_test_pred = model.predict(X_test)

# Metrics
train_mae = mean_absolute_error(y_train, y_train_pred)
train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
train_r2 = r2_score(y_train, y_train_pred)

test_mae = mean_absolute_error(y_test, y_test_pred)
test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
test_r2 = r2_score(y_test, y_test_pred)

print(f"\n📈 TRAIN SET PERFORMANCE:")
print(f"   MAE: {train_mae:.2f}")
print(f"   RMSE: {train_rmse:.2f}")
print(f"   R²: {train_r2:.4f}")

print(f"\n📈 TEST SET PERFORMANCE:")
print(f"   MAE: {test_mae:.2f}")
print(f"   RMSE: {test_rmse:.2f}")
print(f"   R²: {test_r2:.4f}")

# Percentage errors
train_pct_errors = np.abs((y_train - y_train_pred) / y_train) * 100
test_pct_errors = np.abs((y_test - y_test_pred) / y_test) * 100

print(f"\n📈 TRAIN SET - Percentage Errors:")
print(f"   Mean: {np.mean(train_pct_errors):.2f}%")
print(f"   Median: {np.median(train_pct_errors):.2f}%")
print(f"   Std: {np.std(train_pct_errors):.2f}%")

print(f"\n📈 TEST SET - Percentage Errors:")
print(f"   Mean: {np.mean(test_pct_errors):.2f}%")
print(f"   Median: {np.median(test_pct_errors):.2f}%")
print(f"   Std: {np.std(test_pct_errors):.2f}%")

# ==========================================
# 6. COMPARE WITH TRADITIONAL MODELS
# ==========================================

print("\n" + "=" * 80)
print("6. COMPARE WITH TRADITIONAL MODELS")
print("=" * 80)

from src.quant.pricing.pricing_core import calculate_d1_d2
from scipy.stats import norm

# Calculate Black-Scholes prices for test set
bs_prices = []
for idx in X_test.index:
    row = df.loc[idx]
    S = row['underlying_price']
    K = row['strike_price']
    T = row['days_to_maturity'] / 365.0
    r = 0.045
    sigma = row['implied_volatility_pct'] / 100.0
    
    if T > 0 and S > 0 and K > 0:
        d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
        bs_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        bs_prices.append(bs_price)
    else:
        bs_prices.append(row['intrinsic_value'])

bs_prices = np.array(bs_prices)
bs_mae = mean_absolute_error(y_test, bs_prices)
bs_rmse = np.sqrt(mean_squared_error(y_test, bs_prices))
bs_pct_errors = np.abs((y_test - bs_prices) / y_test) * 100

print(f"\n📈 BLACK-SCHOLES (Test Set):")
print(f"   MAE: {bs_mae:.2f}")
print(f"   RMSE: {bs_rmse:.2f}")
print(f"   Mean Pct Error: {np.mean(bs_pct_errors):.2f}%")

print(f"\n📈 ML MODEL (Test Set):")
print(f"   MAE: {test_mae:.2f}")
print(f"   RMSE: {test_rmse:.2f}")
print(f"   Mean Pct Error: {np.mean(test_pct_errors):.2f}%")

# Improvement
mae_improvement = (bs_mae - test_mae) / bs_mae * 100
rmse_improvement = (bs_rmse - test_rmse) / bs_rmse * 100
pct_improvement = (np.mean(bs_pct_errors) - np.mean(test_pct_errors)) / np.mean(bs_pct_errors) * 100

print(f"\n🏆 ML MODEL IMPROVEMENT:")
print(f"   MAE: {mae_improvement:+.2f}%")
print(f"   RMSE: {rmse_improvement:+.2f}%")
print(f"   Pct Error: {pct_improvement:+.2f}%")

# ==========================================
# 7. SIMULATION - TRADING PERFORMANCE
# ==========================================

print("\n" + "=" * 80)
print("7. SIMULATION - TRADING PERFORMANCE")
print("=" * 80)

# Simulate trading based on model predictions
# Strategy: Buy when model predicts price < market price (undervalued)
# Sell when model predicts price > market price (overvalued)

test_df = df.loc[X_test.index].copy()
test_df['ml_predicted_price'] = y_test_pred
test_df['bs_predicted_price'] = bs_prices
test_df['actual_price'] = y_test

# Calculate upside/downside
test_df['ml_upside'] = (test_df['ml_predicted_price'] - test_df['actual_price']) / test_df['actual_price'] * 100
test_df['bs_upside'] = (test_df['bs_predicted_price'] - test_df['actual_price']) / test_df['actual_price'] * 100

# Trading signals
test_df['ml_signal'] = np.where(test_df['ml_upside'] > 10, 'BUY', 
                                np.where(test_df['ml_upside'] < -10, 'SELL', 'HOLD'))
test_df['bs_signal'] = np.where(test_df['bs_upside'] > 10, 'BUY',
                                np.where(test_df['bs_upside'] < -10, 'SELL', 'HOLD'))

print(f"\n📊 ML Model Signals:")
print(test_df['ml_signal'].value_counts())

print(f"\n📊 Black-Scholes Signals:")
print(test_df['bs_signal'].value_counts())

# Calculate potential profit if signals were correct
# For simplicity, assume we buy when signal is BUY and price goes to predicted price
ml_buy_signals = test_df[test_df['ml_signal'] == 'BUY']
if len(ml_buy_signals) > 0:
    avg_ml_upside = ml_buy_signals['ml_upside'].mean()
    print(f"\n📈 ML Model - Average upside for BUY signals: {avg_ml_upside:.2f}%")

bs_buy_signals = test_df[test_df['bs_signal'] == 'BUY']
if len(bs_buy_signals) > 0:
    avg_bs_upside = bs_buy_signals['bs_upside'].mean()
    print(f"📈 Black-Scholes - Average upside for BUY signals: {avg_bs_upside:.2f}%")

# ==========================================
# 8. ACCURACY DISTRIBUTION
# ==========================================

print("\n" + "=" * 80)
print("8. ACCURACY DISTRIBUTION")
print("=" * 80)

# ML Model accuracy distribution
ml_good = (test_pct_errors < 10).sum()
ml_acceptable = ((test_pct_errors >= 10) & (test_pct_errors < 30)).sum()
ml_poor = (test_pct_errors >= 30).sum()

total_test = len(y_test)

print(f"\n📊 ML Model (Test Set):")
print(f"   Tốt (< 10% sai số): {ml_good} ({ml_good/total_test*100:.1f}%)")
print(f"   Chấp nhận được (10-30%): {ml_acceptable} ({ml_acceptable/total_test*100:.1f}%)")
print(f"   Kém (> 30%): {ml_poor} ({ml_poor/total_test*100:.1f}%)")

# Black-Scholes accuracy distribution
bs_good = (bs_pct_errors < 10).sum()
bs_acceptable = ((bs_pct_errors >= 10) & (bs_pct_errors < 30)).sum()
bs_poor = (bs_pct_errors >= 30).sum()

print(f"\n📊 Black-Scholes (Test Set):")
print(f"   Tốt (< 10% sai số): {bs_good} ({bs_good/total_test*100:.1f}%)")
print(f"   Chấp nhận được (10-30%): {bs_acceptable} ({bs_acceptable/total_test*100:.1f}%)")
print(f"   Kém (> 30%): {bs_poor} ({bs_poor/total_test*100:.1f}%)")

# ==========================================
# 9. OVERALL ASSESSMENT
# ==========================================

print("\n" + "=" * 80)
print("9. OVERALL ASSESSMENT")
print("=" * 80)

# Calculate accuracy scores
ml_accuracy = max(0, 100 - np.mean(test_pct_errors))
bs_accuracy = max(0, 100 - np.mean(bs_pct_errors))

print(f"\n🏆 Điểm chính xác (Test Set):")
print(f"   ML Model: {ml_accuracy:.1f}/100")
print(f"   Black-Scholes: {bs_accuracy:.1f}/100")

if ml_accuracy > bs_accuracy:
    improvement = ml_accuracy - bs_accuracy
    print(f"\n✅ ML MODEL TỐT HƠN Black-Scholes: +{improvement:.1f} điểm")
    print(f"\n💡 KHUYẾN NGHỊ:")
    print(f"   - Sử dụng ML Model thay thế Black-Scholes")
    print(f"   - ML Model capture được non-linear relationships")
    print(f"   - Feature importance cho biết các yếu tố quan trọng")
elif ml_accuracy < bs_accuracy:
    decline = bs_accuracy - ml_accuracy
    print(f"\n⚠️  ML MODEL KÉM HƠN Black-Scholes: -{decline:.1f} điểm")
    print(f"\n💡 KHUYẾN NGHỊ:")
    print(f"   - Cần thêm features hoặc tune hyperparameters")
    print(f"   - Cân nhắc dùng Hybrid approach")
else:
    print(f"\n⚖️  HAI MÔ HÌNH CÓ ĐỘ CHÍNH XÁC TƯƠNG ĐƯƠNG")
    print(f"\n💡 KHUYẾN NGHỊ:")
    print(f"   - Có thể dùng cả 2 model để cross-validate")

# ==========================================
# 10. SAVE MODEL
# ==========================================

print("\n" + "=" * 80)
print("10. SAVE MODEL")
print("=" * 80)

import joblib
import os

model_dir = 'models'
if not os.path.exists(model_dir):
    os.makedirs(model_dir)

model_path = os.path.join(model_dir, 'ml_pricing_model.pkl')
joblib.dump(model, model_path)

print(f"✅ Model saved to: {model_path}")

# Save feature names
feature_names_path = os.path.join(model_dir, 'feature_names.pkl')
joblib.dump(X.columns.tolist(), feature_names_path)

print(f"✅ Feature names saved to: {feature_names_path}")

print("\n" + "=" * 80)
print("HOÀN THÀNH TRAIN, TEST, SIMULATE")
print("=" * 80)
