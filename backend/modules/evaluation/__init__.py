"""
Evaluation Module - SMC & Custom Indicators Performance Assessment
Provides metrics, backtesting, and benchmarking for indicator evaluation.
"""

from .metrics import SignalQualityMetrics
from .backtester import Backtester
from .advanced_backtester import AdvancedBacktester
from .visualizer import IndicatorVisualizer
from .benchmark import BenchmarkComparator
from .signal_generator import AdvancedSignalGenerator
from .regime_filter import RegimeSignalFilter
from .parameter_optimizer import ParameterOptimizer
from .production_integration import ProductionIntegration

__all__ = [
    'SignalQualityMetrics',
    'Backtester',
    'AdvancedBacktester',
    'IndicatorVisualizer',
    'BenchmarkComparator',
    'AdvancedSignalGenerator',
    'RegimeSignalFilter',
    'ParameterOptimizer',
    'ProductionIntegration'
]
