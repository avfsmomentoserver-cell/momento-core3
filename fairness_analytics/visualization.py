"""
Fairness Analytics System - Visualization

This module provides forex-style visualizations for crash game fairness analysis.

Key Visualizations:
- Cumulative Drift Chart
- Realized vs Theoretical Edge
- Drift Histogram
- Mean Reversion Plot
- Round-based Candlesticks
- Anomaly Detection Plot
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from typing import Optional, Tuple


class FairnessVisualizer:
    """
    Creates visualizations for fairness analysis of crash game data.
    
    Args:
        style: Matplotlib style to use
        figsize: Default figure size
    """
    
    def __init__(self, style: str = 'seaborn-v0_8', figsize: Tuple[int, int] = (12, 6)):
        plt.style.use(style)
        self.figsize = figsize
        
    def plot_cumulative_drift(self, df: pd.DataFrame, round_col: str = 'round_id',
                             drift_col: str = 'cumulative_pnl',
                             title: str = 'Cumulative Fairness Drift',
                             save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot cumulative drift over time.
        
        Args:
            df: DataFrame containing drift data
            round_col: Name of the column with round IDs
            drift_col: Name of the column with cumulative drift
            title: Plot title
            save_path: Path to save the figure
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        ax.plot(df[round_col], df[drift_col], label='Cumulative Drift', linewidth=1.5)
        ax.axhline(0, color='red', linestyle='--', label='Neutral Baseline')
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Round ID', fontsize=12)
        ax.set_ylabel('Cumulative Points', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_realized_vs_theoretical(self, df: pd.DataFrame, round_col: str = 'round_id',
                                     realized_col: str = 'realized_edge',
                                     theoretical_edge: float = 0.03,
                                     title: str = 'Realized vs Theoretical House Edge',
                                     save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot realized house edge vs theoretical edge over time.
        
        Args:
            df: DataFrame containing edge data
            round_col: Name of the column with round IDs
            realized_col: Name of the column with realized edge
            theoretical_edge: Theoretical house edge
            title: Plot title
            save_path: Path to save the figure
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        ax.plot(df[round_col], df[realized_col] * 100, label='Realized Edge', linewidth=1.5)
        ax.axhline(theoretical_edge * 100, color='red', linestyle='--', 
                  label=f'Theoretical Edge ({theoretical_edge*100:.1f}%)')
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Round ID', fontsize=12)
        ax.set_ylabel('House Edge (%)', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_drift_histogram(self, df: pd.DataFrame, drift_col: str = 'drift',
                            title: str = 'Drift Distribution',
                            save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot histogram of drift values.
        
        Args:
            df: DataFrame containing drift data
            drift_col: Name of the column with drift values
            title: Plot title
            save_path: Path to save the figure
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        drift_values = df[drift_col].dropna() * 100  # Convert to percentage
        
        sns.histplot(drift_values, bins=50, kde=True, ax=ax, color='skyblue')
        ax.axvline(0, color='red', linestyle='--', label='Neutral Baseline')
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Drift (%)', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_mean_reversion(self, df: pd.DataFrame, drift_col: str = 'drift',
                           title: str = 'Mean Reversion Analysis',
                           save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot drift vs lagged drift to analyze mean reversion.
        
        Args:
            df: DataFrame containing drift data
            drift_col: Name of the column with drift values
            title: Plot title
            save_path: Path to save the figure
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        drift_values = df[drift_col].dropna().values
        lagged_drift = np.roll(drift_values, 1)
        
        # Align the arrays (remove the first element of drift_values and last of lagged_drift)
        drift_values_aligned = drift_values[1:]
        lagged_drift_aligned = lagged_drift[1:]
        
        ax.scatter(lagged_drift_aligned, drift_values_aligned, alpha=0.5, color='blue')
        ax.axhline(0, color='red', linestyle='--')
        ax.axvline(0, color='red', linestyle='--')
        
        # Add trend line
        if len(lagged_drift_aligned) > 1:
            z = np.polyfit(lagged_drift_aligned, drift_values_aligned, 1)
            p = np.poly1d(z)
            x_range = np.linspace(lagged_drift_aligned.min(), lagged_drift_aligned.max(), 100)
            ax.plot(x_range, p(x_range), "r--", linewidth=2)
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Lagged Drift', fontsize=12)
        ax.set_ylabel('Current Drift', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_candlesticks(self, df: pd.DataFrame, round_col: str = 'round_id',
                         points_col: str = 'points', window_size: int = 5,
                         title: str = 'Round-Based Candlesticks',
                         save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot round-based candlesticks (NOT time-based).
        
        Args:
            df: DataFrame containing points data
            round_col: Name of the column with round IDs
            points_col: Name of the column with points
            window_size: Number of rounds per candle
            title: Plot title
            save_path: Path to save the figure
            
        Returns:
            Matplotlib figure
        """
        # Create candles from round-based windows
        candles = []
        for i in range(0, len(df) - window_size + 1, window_size):
            window = df.iloc[i:i+window_size]
            candle = {
                'round_start': window[round_col].iloc[0],
                'round_end': window[round_col].iloc[-1],
                'open': window[points_col].iloc[0],
                'high': window[points_col].max(),
                'low': window[points_col].min(),
                'close': window[points_col].iloc[-1]
            }
            candles.append(candle)
        
        candles_df = pd.DataFrame(candles)
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Plot candlesticks
        for _, candle in candles_df.iterrows():
            x = candle['round_start']
            width = candle['round_end'] - candle['round_start']
            
            # Body
            body_color = 'green' if candle['close'] >= candle['open'] else 'red'
            ax.bar(x, candle['close'] - candle['open'], width=width, 
                   bottom=candle['open'], color=body_color, linewidth=1)
            
            # Wicks
            ax.plot([x, x], [candle['low'], candle['high']], color='black', linewidth=0.5)
            ax.plot([x, x], [candle['open'], candle['low']], color='black', linewidth=0.5)
            ax.plot([x, x], [candle['close'], candle['high']], color='black', linewidth=0.5)
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Round ID', fontsize=12)
        ax.set_ylabel('Points', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_anomalies(self, df: pd.DataFrame, round_col: str = 'round_id',
                      drift_col: str = 'drift', anomaly_col: str = 'is_anomaly',
                      title: str = 'Anomaly Detection',
                      save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot drift with anomalies highlighted.
        
        Args:
            df: DataFrame containing drift and anomaly data
            round_col: Name of the column with round IDs
            drift_col: Name of the column with drift values
            anomaly_col: Name of the column with anomaly flags
            title: Plot title
            save_path: Path to save the figure
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Plot normal drift
        normal_df = df[~df[anomaly_col]]
        ax.scatter(normal_df[round_col], normal_df[drift_col] * 100, 
                  color='blue', label='Normal', alpha=0.6)
        
        # Plot anomalies
        anomaly_df = df[df[anomaly_col]]
        ax.scatter(anomaly_df[round_col], anomaly_df[drift_col] * 100, 
                  color='red', label='Anomaly', alpha=0.8)
        
        ax.axhline(0, color='black', linestyle='--', label='Neutral Baseline')
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Round ID', fontsize=12)
        ax.set_ylabel('Drift (%)', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def create_plotly_candlestick(self, df: pd.DataFrame, round_col: str = 'round_id',
                                  points_col: str = 'points', window_size: int = 5,
                                  title: str = 'Interactive Candlesticks') -> go.Figure:
        """
        Create an interactive Plotly candlestick chart.
        
        Args:
            df: DataFrame containing points data
            round_col: Name of the column with round IDs
            points_col: Name of the column with points
            window_size: Number of rounds per candle
            title: Chart title
            
        Returns:
            Plotly figure
        """
        # Create candles from round-based windows
        candles = []
        for i in range(0, len(df) - window_size + 1, window_size):
            window = df.iloc[i:i+window_size]
            candle = {
                'round_start': window[round_col].iloc[0],
                'round_end': window[round_col].iloc[-1],
                'open': window[points_col].iloc[0],
                'high': window[points_col].max(),
                'low': window[points_col].min(),
                'close': window[points_col].iloc[-1]
            }
            candles.append(candle)
        
        candles_df = pd.DataFrame(candles)
        
        fig = go.Figure(data=[go.Candlestick(
            x=candles_df['round_start'],
            open=candles_df['open'],
            high=candles_df['high'],
            low=candles_df['low'],
            close=candles_df['close']
        )])
        
        fig.update_layout(
            title=title,
            xaxis_title='Round ID',
            yaxis_title='Points',
            xaxis_rangeslider_visible=False
        )
        
        return fig


def plot_all_metrics(df: pd.DataFrame, output_dir: str = 'visualizations') -> dict:
    """
    Generate all visualizations and save to output directory.
    
    Args:
        df: DataFrame containing all metrics
        output_dir: Directory to save visualizations
        
    Returns:
        Dictionary with figure paths
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    visualizer = FairnessVisualizer()
    
    figures = {}
    
    # Cumulative Drift
    fig = visualizer.plot_cumulative_drift(df, save_path=f'{output_dir}/cumulative_drift.png')
    figures['cumulative_drift'] = f'{output_dir}/cumulative_drift.png'
    
    # Realized vs Theoretical Edge
    fig = visualizer.plot_realized_vs_theoretical(df, save_path=f'{output_dir}/realized_vs_theoretical.png')
    figures['realized_vs_theoretical'] = f'{output_dir}/realized_vs_theoretical.png'
    
    # Drift Histogram
    fig = visualizer.plot_drift_histogram(df, save_path=f'{output_dir}/drift_histogram.png')
    figures['drift_histogram'] = f'{output_dir}/drift_histogram.png'
    
    # Mean Reversion
    fig = visualizer.plot_mean_reversion(df, save_path=f'{output_dir}/mean_reversion.png')
    figures['mean_reversion'] = f'{output_dir}/mean_reversion.png'
    
    # Candlesticks
    fig = visualizer.plot_candlesticks(df, save_path=f'{output_dir}/candlesticks.png')
    figures['candlesticks'] = f'{output_dir}/candlesticks.png'
    
    return figures
