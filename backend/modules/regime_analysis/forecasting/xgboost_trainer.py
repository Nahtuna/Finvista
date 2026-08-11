import os
import warnings
warnings.filterwarnings('ignore')  # Silence XGBoost version warnings

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score
from backend.core import config

_MODEL_CACHE = {}

class XGBoostRegimeTrainer:
    """Trains XGBoost model using TimeSeriesSplit to prevent look-ahead bias."""

    def __init__(self, model_dir: str = None, horizon: int = 1):
        self.model_dir = model_dir or config.XGBOOST_REGIME_DIR
        os.makedirs(self.model_dir, exist_ok=True)
        self.horizon = horizon
        
        # Hyperparameters based on horizon - Tuned for lower overfitting and better trend generalization
        hp_config = {
            1: {'lr': 0.03, 'depth': 3, 'sub': 0.7, 'col': 0.7, 'est': 100, 'mcw': 10, 'alpha': 2.0, 'lam': 4.0, 'gamma': 0.5},
            5: {'lr': 0.025, 'depth': 3, 'sub': 0.65, 'col': 0.65, 'est': 90, 'mcw': 12, 'alpha': 3.0, 'lam': 5.0, 'gamma': 0.8}
        }
        hp = hp_config.get(horizon, hp_config[5])
        
        self.model = XGBClassifier(
            objective='multi:softprob', num_class=4, eval_metric='mlogloss',
            learning_rate=hp['lr'], max_depth=hp['depth'], subsample=hp['sub'],
            colsample_bytree=hp['col'], n_estimators=hp['est'], min_child_weight=hp['mcw'],
            reg_alpha=hp['alpha'], reg_lambda=hp['lam'], gamma=hp['gamma'], random_state=42
        )

    def train_and_evaluate(self, X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> XGBClassifier:
        """Evaluates model using walk-forward validation with regularization."""
        from sklearn.utils.class_weight import compute_sample_weight
        print(f"[INFO] Starting TimeSeries Walk-Forward Validation ({n_splits} splits)...")
        tscv = TimeSeriesSplit(n_splits=n_splits)
        accuracies = []
        
        for fold, (train_index, test_index) in enumerate(tscv.split(X), 1):
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            
            # Ensure y is numpy array
            y_train = y_train.values if hasattr(y_train, 'values') else y_train
            y_test = y_test.values if hasattr(y_test, 'values') else y_test
            
            # Compute balanced class weights for training slice
            train_weights = compute_sample_weight(class_weight='balanced', y=y_train)
            self.model.fit(X_train, y_train, sample_weight=train_weights, verbose=False)
            y_pred = self.model.predict(X_test)
            
            # Ensure y_test and y_pred are proper arrays
            y_test_arr = y_test if isinstance(y_test, np.ndarray) else np.array(y_test)
            y_pred_arr = y_pred if isinstance(y_pred, np.ndarray) else np.array(y_pred)
            
            # Handle case where predict returns probabilities
            if len(y_pred_arr.shape) > 1 and y_pred_arr.shape[1] > 1:
                y_pred_arr = np.argmax(y_pred_arr, axis=1)
            
            # Use simple manual accuracy calculation
            acc = np.mean(y_test_arr == y_pred_arr)
            accuracies.append(acc)
            print(f"  Fold {fold}: Accuracy = {acc:.2%}")
            
        cv_acc = sum(accuracies) / len(accuracies)
        print(f"[OK] Mean CV Accuracy: {cv_acc:.2%}")
        
        print("[INFO] Training final model on entire dataset with class weighting...")
        y_values = y.values if hasattr(y, 'values') else y
        final_weights = compute_sample_weight(class_weight='balanced', y=y_values)
        self.model.fit(X, y_values, sample_weight=final_weights)
        
        y_pred_full = self.model.predict(X)
        print("\n[REPORT] Final Model Training Report:")
        # Ensure both are numpy arrays
        y_true = y_values if isinstance(y_values, np.ndarray) else np.array(y_values)
        y_pred_final = y_pred_full if isinstance(y_pred_full, np.ndarray) else np.array(y_pred_full)
        
        # Handle case where predict returns probabilities
        if len(y_pred_final.shape) > 1 and y_pred_final.shape[1] > 1:
            y_pred_final = np.argmax(y_pred_final, axis=1)
        
        # Simple accuracy instead of classification_report to avoid metrics issues
        train_acc = np.mean(y_true == y_pred_final)
        print(f"Training Accuracy: {train_acc:.2%}")
        
        overfitting_gap = train_acc - cv_acc
        print(f"\n[ANALYSIS] Overfitting Check:")
        print(f"   Training Accuracy: {train_acc:.2%}")
        print(f"   CV Accuracy: {cv_acc:.2%}")
        print(f"   Gap: {overfitting_gap:.2%} {'(Acceptable < 15%)' if overfitting_gap < 0.15 else '(High - consider more regularization)'}")
        
        return self.model

    def save_model(self, filename: str = None):
        if filename is None:
            filename = f"xgboost_regime_SPY_T{self.horizon}.pkl"
        path = os.path.join(self.model_dir, filename)
        joblib.dump(self.model, path)
        print(f"[OK] Model saved to {path}")

    def load_model(self, filename: str = None):
        if filename is None:
            filename = f"xgboost_regime_SPY_T{self.horizon}.pkl"
        path = os.path.join(self.model_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model not found at {path}")
            
        if path in _MODEL_CACHE:
            self.model = _MODEL_CACHE[path]
            return self.model
            
        try:
            with open(path, "rb") as f:
                self.model = joblib.load(f)
            _MODEL_CACHE[path] = self.model
            print(f"[OK] Model loaded & cached from {path}")
        except Exception:
            self.model = joblib.load(path)
            _MODEL_CACHE[path] = self.model
            
        return self.model
