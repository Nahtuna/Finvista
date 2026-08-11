"""
Indicator Visualizer - Visualization Tools for Indicator Analysis
Implements plotting and visualization for indicator performance analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from backend.core.utils import get_logger

viz_logger = get_logger(__name__)


class IndicatorVisualizer:
    """
    Visualization tools for indicator analysis and performance assessment.
    
    Note: This is a simplified version. In production, you would use matplotlib/plotly
    for actual visualization. This provides the data structure for visualizations.
    """
    
    def __init__(self):
        """Initialize IndicatorVisualizer."""
        viz_logger.info("Initialized IndicatorVisualizer")
    
    def prepare_indicator_plot_data(self, df: pd.DataFrame, indicator_name: str, indicator_values: pd.Series) -> Dict[str, Any]:
        """
        Prepare data for indicator vs price plot.
        
        Args:
            df: DataFrame with OHLCV data
            indicator_name: Name of the indicator
            indicator_values: Series of indicator values
            
        Returns:
            Dictionary with plot data
        """
        plot_data = {
            'dates': df.index.strftime('%Y-%m-%d').tolist(),
            'price': df['close'].tolist(),
            'indicator_name': indicator_name,
            'indicator_values': indicator_values.tolist(),
            'high': df['high'].tolist(),
            'low': df['low'].tolist()
        }
        
        viz_logger.info(f"Prepared plot data for {indicator_name}")
        return plot_data
    
    def prepare_signal_plot_data(self, df: pd.DataFrame, signals: pd.Series) -> Dict[str, Any]:
        """
        Prepare data for signal visualization.
        
        Args:
            df: DataFrame with OHLCV data
            signals: Series of trading signals
            
        Returns:
            Dictionary with signal plot data
        """
        # Identify buy and sell points
        buy_signals = signals[signals == 1]
        sell_signals = signals[signals == -1]
        
        plot_data = {
            'dates': df.index.strftime('%Y-%m-%d').tolist(),
            'price': df['close'].tolist(),
            'buy_dates': buy_signals.index.strftime('%Y-%m-%d').tolist(),
            'buy_prices': df.loc[buy_signals.index, 'close'].tolist(),
            'sell_dates': sell_signals.index.strftime('%Y-%m-%d').tolist(),
            'sell_prices': df.loc[sell_signals.index, 'close'].tolist()
        }
        
        viz_logger.info(f"Prepared signal plot data: {len(buy_signals)} buys, {len(sell_signals)} sells")
        return plot_data
    
    def prepare_equity_curve_data(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data for equity curve visualization.
        
        Args:
            backtest_results: Results from backtester
            
        Returns:
            Dictionary with equity curve data
        """
        equity_curve = pd.Series(backtest_results['equity_curve'])
        
        plot_data = {
            'dates': equity_curve.index.strftime('%Y-%m-%d').tolist(),
            'equity': equity_curve.tolist(),
            'initial_capital': backtest_results['initial_capital'],
            'final_capital': backtest_results['final_capital'],
            'total_return_pct': backtest_results['total_return_pct']
        }
        
        viz_logger.info("Prepared equity curve data")
        return plot_data
    
    def prepare_drawdown_chart_data(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data for drawdown visualization.
        
        Args:
            backtest_results: Results from backtester
            
        Returns:
            Dictionary with drawdown data
        """
        equity_curve = pd.Series(backtest_results['equity_curve'])
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        
        plot_data = {
            'dates': equity_curve.index.strftime('%Y-%m-%d').tolist(),
            'drawdown': drawdown.tolist(),
            'max_drawdown': float(drawdown.min())
        }
        
        viz_logger.info("Prepared drawdown chart data")
        return plot_data
    
    def prepare_indicator_comparison_data(self, indicators: Dict[str, pd.Series]) -> Dict[str, Any]:
        """
        Prepare data for multi-indicator comparison.
        
        Args:
            indicators: Dictionary of indicator series
            
        Returns:
            Dictionary with comparison data
        """
        comparison_data = {
            'indicator_names': list(indicators.keys()),
            'dates': [],
            'values': {}
        }
        
        # Use the first indicator's dates as reference
        first_indicator = list(indicators.values())[0]
        comparison_data['dates'] = first_indicator.index.strftime('%Y-%m-%d').tolist()
        
        for name, values in indicators.items():
            comparison_data['values'][name] = values.tolist()
        
        viz_logger.info(f"Prepared comparison data for {len(indicators)} indicators")
        return comparison_data
    
    def prepare_metrics_dashboard_data(self, evaluation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data for metrics dashboard.
        
        Args:
            evaluation_results: Results from comprehensive evaluation
            
        Returns:
            Dictionary with dashboard data
        """
        dashboard_data = {
            'signal_quality': {
                'snr': evaluation_results.get('signal_to_noise_ratio', 0),
                'precision': evaluation_results.get('precision', 0),
                'recall': evaluation_results.get('recall', 0),
                'f1_score': evaluation_results.get('f1_score', 0)
            },
            'performance': {
                'total_return': evaluation_results.get('total_return', 0),
                'sharpe_ratio': evaluation_results.get('sharpe_ratio', 0),
                'max_drawdown': evaluation_results.get('max_drawdown', 0),
                'win_rate': evaluation_results.get('win_rate', 0)
            },
            'trading': {
                'num_signals': evaluation_results.get('num_signals', 0),
                'profit_factor': evaluation_results.get('profit_factor', 0),
                'avg_win': evaluation_results.get('avg_win', 0),
                'avg_loss': evaluation_results.get('avg_loss', 0)
            }
        }
        
        viz_logger.info("Prepared metrics dashboard data")
        return dashboard_data
    
    def generate_text_report(self, evaluation_results: Dict[str, Any], backtest_results: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate text-based evaluation report.
        
        Args:
            evaluation_results: Results from comprehensive evaluation
            backtest_results: Optional backtest results
            
        Returns:
            String with formatted report
        """
        report = []
        report.append("=" * 60)
        report.append("INDICATOR EVALUATION REPORT")
        report.append("=" * 60)
        
        # Signal Quality Section
        report.append("\nSIGNAL QUALITY METRICS")
        report.append("-" * 40)
        report.append(f"Signal-to-Noise Ratio: {evaluation_results.get('signal_to_noise_ratio', 0):.3f} dB")
        report.append(f"Precision: {evaluation_results.get('precision', 0):.3f}")
        report.append(f"Recall: {evaluation_results.get('recall', 0):.3f}")
        report.append(f"F1-Score: {evaluation_results.get('f1_score', 0):.3f}")
        
        # Performance Section
        report.append("\nPERFORMANCE METRICS")
        report.append("-" * 40)
        report.append(f"Total Return: {evaluation_results.get('total_return', 0):.3f}")
        report.append(f"Sharpe Ratio: {evaluation_results.get('sharpe_ratio', 0):.3f}")
        report.append(f"Max Drawdown: {evaluation_results.get('max_drawdown', 0):.3f}")
        report.append(f"Win Rate: {evaluation_results.get('win_rate', 0):.3f}")
        
        # Trading Section
        report.append("\nTRADING STATISTICS")
        report.append("-" * 40)
        report.append(f"Number of Signals: {evaluation_results.get('num_signals', 0)}")
        report.append(f"Profit Factor: {evaluation_results.get('profit_factor', 0):.3f}")
        report.append(f"Average Win: {evaluation_results.get('avg_win', 0):.3f}")
        report.append(f"Average Loss: {evaluation_results.get('avg_loss', 0):.3f}")
        
        # Backtest Results (if available)
        if backtest_results:
            report.append("\nBACKTEST RESULTS")
            report.append("-" * 40)
            report.append(f"Final Capital: {backtest_results['final_capital']:.2f}")
            report.append(f"Total Return: {backtest_results['total_return_pct']:.2f}%")
            report.append(f"Number of Trades: {backtest_results['num_trades']}")
            report.append(f"Winning Trades: {backtest_results['winning_trades']}")
            report.append(f"Losing Trades: {backtest_results['losing_trades']}")
        
        report.append("\n" + "=" * 60)
        
        report_text = "\n".join(report)
        viz_logger.info("Generated text evaluation report")
        return report_text
