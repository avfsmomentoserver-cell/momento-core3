"""
Fairness Analytics System - Interactive Dashboard

This module provides a Streamlit-based interactive dashboard for
real-time monitoring of crash game fairness metrics.

Features:
- Upload CSV files with crash game data
- Configure parameters (cashout target, house edge)
- View real-time metrics and visualizations
- Detect anomalies and measure rate of balance
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Optional

try:
    from fairness_analytics.point_mapper import PointMapper
    from fairness_analytics.drift_calculator import DriftCalculator
    from fairness_analytics.visualization import FairnessVisualizer
except ImportError:
    # Fallback for when package is not installed
    import sys
    sys.path.insert(0, '/workspace/avfsmomentoserver-cell__momento-core3')
    from fairness_analytics.point_mapper import PointMapper
    from fairness_analytics.drift_calculator import DriftCalculator
    from fairness_analytics.visualization import FairnessVisualizer


def main():
    """Main dashboard function."""
    st.set_page_config(
        page_title="Crash Game Fairness Dashboard",
        page_icon="⚖️",
        layout="wide"
    )
    
    st.title("⚖️ Crash Game Fairness Analytics Dashboard")
    st.markdown("""
    This dashboard visualizes house edge fairness and measures drift from the theoretical equilibrium.
    It helps identify periods of excessive imbalance and quantifies the rate of balance restoration.
    """)
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    
    # Upload CSV file
    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV File",
        type=["csv"],
        help="Upload a CSV file containing crash game data with 'multiplier' column"
    )
    
    # Parameters
    cashout_target = st.sidebar.slider(
        "Cashout Target",
        min_value=1.1,
        max_value=10.0,
        value=1.5,
        step=0.1,
        help="Multiplier at which bets are automatically cashed out"
    )
    
    house_edge = st.sidebar.slider(
        "House Edge",
        min_value=0.01,
        max_value=0.10,
        value=0.03,
        step=0.01,
        help="Theoretical house edge (e.g., 0.03 for 3%)"
    )
    
    window_size = st.sidebar.slider(
        "Candlestick Window Size",
        min_value=3,
        max_value=15,
        value=5,
        step=1,
        help="Number of rounds per candlestick"
    )
    
    anomaly_threshold = st.sidebar.slider(
        "Anomaly Threshold (σ)",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.5,
        help="Number of standard deviations to flag as anomaly"
    )
    
    # Main content
    if uploaded_file is not None:
        # Load data
        df = pd.read_csv(uploaded_file)
        
        st.success(f"✅ Loaded {len(df)} rounds of data")
        
        # Show raw data preview
        with st.expander("Raw Data Preview"):
            st.dataframe(df.head(100))
        
        # Initialize components
        mapper = PointMapper(cashout_target, house_edge)
        calculator = DriftCalculator(house_edge, cashout_target)
        visualizer = FairnessVisualizer()
        
        # Map points
        df = mapper.map_dataframe(df)
        
        # Calculate metrics
        df = calculator.calculate_pnl(df)
        df = calculator.calculate_metrics(df)
        
        # Detect anomalies
        df = calculator.detect_anomalies(df, threshold_std=anomaly_threshold)
        
        # Calculate rate of balance
        rate_metrics = calculator.calculate_rate_of_balance(df['drift'])
        stats = calculator.calculate_statistics(df)
        
        # Display metrics
        st.header("📊 Fairness Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Current Drift",
                f"{stats['final_drift']*100:.2f}%",
                f"{stats['final_drift']*100 - stats['mean_drift']*100:.2f}%"
            )
        
        with col2:
            st.metric(
                "Max Drift",
                f"{stats['max_drift']*100:.2f}%",
                f"{stats['max_drift']*100 - stats['mean_drift']*100:.2f}%"
            )
        
        with col3:
            st.metric(
                "Half-Life",
                f"{rate_metrics['half_life']:.0f} rounds",
                f"{rate_metrics['half_life'] - 10:.0f}"
            )
        
        with col4:
            st.metric(
                "Mean Reversion",
                f"{rate_metrics['mean_reversion_rate']*100:.1f}%",
                f"{rate_metrics['mean_reversion_rate']*100 - 15:.1f}%"
            )
        
        # Additional metrics
        st.subheader("Detailed Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**Mean Drift:** {stats['mean_drift']*100:.4f}%")
            st.write(f"**Std Drift:** {stats['std_drift']*100:.4f}%")
        
        with col2:
            st.write(f"**Min Drift:** {stats['min_drift']*100:.4f}%")
            st.write(f"**Max Drift:** {stats['max_drift']*100:.4f}%")
        
        with col3:
            st.write(f"**Total Rounds:** {stats['n_rounds']}")
            st.write(f"**Is Mean-Reverting:** {'✅ Yes' if rate_metrics['is_mean_reverting'] else '❌ No'}")
        
        # Visualizations
        st.header("📈 Visualizations")
        
        # Cumulative Drift
        st.subheader("Cumulative Drift")
        fig = visualizer.plot_cumulative_drift(df)
        st.pyplot(fig)
        
        # Realized vs Theoretical Edge
        st.subheader("Realized vs Theoretical House Edge")
        fig = visualizer.plot_realized_vs_theoretical(df)
        st.pyplot(fig)
        
        # Drift Histogram
        st.subheader("Drift Distribution")
        fig = visualizer.plot_drift_histogram(df)
        st.pyplot(fig)
        
        # Mean Reversion
        st.subheader("Mean Reversion Analysis")
        fig = visualizer.plot_mean_reversion(df)
        st.pyplot(fig)
        
        # Candlesticks
        st.subheader(f"Round-Based Candlesticks (Window: {window_size} rounds)")
        fig = visualizer.create_plotly_candlestick(df, window_size=window_size)
        st.plotly_chart(fig, use_container_width=True)
        
        # Anomalies
        st.subheader("Anomaly Detection")
        anomaly_df = df[df['is_anomaly']]
        st.write(f"Detected {len(anomaly_df)} anomalous rounds")
        
        if len(anomaly_df) > 0:
            fig = visualizer.plot_anomalies(df)
            st.pyplot(fig)
            
            with st.expander("Anomaly Details"):
                st.dataframe(anomaly_df[['round_id', 'multiplier', 'drift', 'anomaly_duration']])
        
        # Forex Analyst Interpretation
        st.header("💡 Forex Analyst Interpretation")
        
        st.markdown("""
        ### Fairness Assessment
        """)
        
        if abs(stats['final_drift']) < 0.01:
            st.success("✅ Current drift is within normal range")
        elif abs(stats['final_drift']) < 0.05:
            st.warning("⚠️ Current drift is slightly elevated")
        else:
            st.error("❌ Current drift is significantly elevated")
        
        st.markdown("""
        ### Rate of Balance
        """)
        
        if rate_metrics['half_life'] < 10:
            st.success("✅ Fast balance restoration")
        elif rate_metrics['half_life'] < 30:
            st.info("ℹ️ Moderate balance restoration")
        else:
            st.warning("⚠️ Slow balance restoration")
        
        st.markdown("""
        ### Mean Reversion
        """)
        
        if rate_metrics['mean_reversion_rate'] > 0.15:
            st.success("✅ Strong mean reversion")
        elif rate_metrics['mean_reversion_rate'] > 0.05:
            st.info("ℹ️ Moderate mean reversion")
        else:
            st.warning("⚠️ Weak mean reversion")
        
        # Download processed data
        st.header("💾 Export Data")
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Processed Data",
            data=csv,
            file_name="fairness_analysis_results.csv",
            mime="text/csv"
        )
        
    else:
        st.info("📁 Please upload a CSV file to begin analysis")
        
        # Show example
        st.subheader("Example CSV Format")
        st.markdown("""
        Your CSV should contain at least the following columns:
        - `round_id`: Unique identifier for each round
        - `multiplier`: Crash game multiplier (e.g., 1.2, 2.5, 10.0)
        - `timestamp`: Optional timestamp for each round
        
        Example:
        ```csv
        round_id,source,timestamp,multiplier
        1,aviator,2026-07-24T13:42:05.062+00:00,1.21
        2,aviator,2026-07-24T13:42:24.568+00:00,1.82
        3,aviator,2026-07-24T13:43:05.401+00:00,12.64
        ```
        """)


if __name__ == "__main__":
    main()
