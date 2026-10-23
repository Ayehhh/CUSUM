import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="CUSUM Control Chart Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
    }
    .stAlert {
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# TITLE & KNOWLEDGE SHARING SECTION
# ==========================================
st.markdown('<div class="main-header">CUSUM Analysis & Degradation Monitoring</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Detect subtle process shifts, equipment degradation, or anomalies early using Cumulative Sum control charts.</div>', unsafe_allow_html=True)

# Collapsible Knowledge Base / Definitions
with st.expander("📚 **Knowledge Sharing & CUSUM Definitions (Click to Expand)**", expanded=False):
    st.markdown("""
    ### What is CUSUM Analysis?
    The **Cumulative Sum (CUSUM)** control chart is an advanced Statistical Process Control (SPC) technique designed to detect **small, persistent shifts** in a process mean that standard Shewhart charts (like X-bar charts) often miss.

    ---

    ### Key Mathematical Concepts & Parameters:
    
    1. **Target Mean ($\mu_0$)**:
       - The ideal or baseline operational mean of your parameter under stable conditions.
    
    2. **Standard Deviation ($\sigma$)**:
       - The inherent process variation during baseline operation.

    3. **Shift Distance / Slack Parameter ($k$)**:
       - Typically set to **$k = 0.5$** (expressed in standard units).
       - Represents half the size of the shift you wish to detect ($1.0\sigma$ shift detection by default).
       - Calculation allowance: 
         - Upper CUSUM: $C^+_i = \max(0, x_i - (\mu_0 + k\sigma) + C^+_{i-1})$
         - Lower CUSUM: $C^-_i = \max(0, (\mu_0 - k\sigma) - x_i + C^-_{i-1})$

    4. **Decision Interval / Threshold ($h$)**:
       - Typically set to **$h = 4.0$ or $5.0$** (in standard deviation units).
       - The alarm threshold. If $C^+$ or $C^-$ exceeds $h \cdot \sigma$, the process is flagged as **Out-of-Control** or showing significant degradation/drift.

    ---

    ### How to Interpret the Charts:
    * **Chart 1 (Time Series & 7-Day Rolling Mean)**: Shows real operational values alongside smoothed 7-day moving trends to reveal macro degradation patterns over time.
    * **Chart 2 (CUSUM Chart)**: Shows cumulative deviation buildup.
      * **Positive Accumulation ($C^+$)**: Indicates an upward shift (e.g., increased temperature, vibration, wear rate, or rod drop depth).
      * **Negative Accumulation ($C^-$)**: Indicates a downward shift (e.g., pressure loss, flow rate drop, efficiency loss).
      * **Red Highlight Markers**: Flags exact timestamps where the CUSUM statistic breached the decision limit ($h$).
    """)

# ==========================================
# SIDEBAR: DATA INPUT & PARAMETERS
# ==========================================
st.sidebar.header("📁 Data Input & Source")

data_source = st.sidebar.radio(
    "Choose Data Input Mode:",
    ["Use Demo Sample Data (Equipment Degradation)", "Upload Excel / CSV File"]
)

df_input = None

if data_source == "Use Demo Sample Data (Equipment Degradation)":
    st.sidebar.info("Using simulated daily equipment metric (e.g., wear, rod drop, or vibration) with a subtle shift introduced at day 40.")
    
    # Generate Synthetic Degradation Data
    np.random.seed(42)
    dates = pd.date_range(start=datetime.date.today() - datetime.timedelta(days=90), periods=90, freq='D')
    
    # Phase 1: Stable baseline (days 0-39)
    baseline = np.random.normal(loc=10.0, scale=0.8, size=40)
    
    # Phase 2: Degradation / Mean shift (days 40-89)
    shift = np.random.normal(loc=11.5, scale=0.9, size=50)
    
    data_values = np.concatenate([baseline, shift])
    df_input = pd.DataFrame({
        "Timestamp": dates,
        "Metric_Value": np.round(data_values, 3)
    })

else:
    uploaded_file = st.sidebar.file_uploader(
        "Upload Excel (.xlsx) or CSV file", 
        type=["csv", "xlsx", "xls"]
    )
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_input = pd.read_csv(uploaded_file)
            else:
                df_input = pd.read_excel(uploaded_file)
            st.sidebar.success(f"Successfully loaded {uploaded_file.name}")
        except Exception as e:
            st.sidebar.error(f"Error loading file: {e}")

if df_input is not None:
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Column Mapping")
    
    # Column Selector
    columns = list(df_input.columns)
    time_col = st.sidebar.selectbox("Select Timestamp/Date Column:", columns, index=0)
    val_col = st.sidebar.selectbox("Select Metric/Value Column:", columns, index=min(1, len(columns)-1))

    # Convert Timestamp to datetime
    try:
        df_input[time_col] = pd.to_datetime(df_input[time_col])
        df_input = df_input.sort_values(by=time_col).reset_index(drop=True)
    except Exception as e:
        st.warning(f"Could not parse '{time_col}' as DateTime. Plotted sequentially.")

    # Drop NaN in metric column
    df_input = df_input.dropna(subset=[val_col]).reset_index(drop=True)

    # ==========================================
    # CUSUM PARAMETERS CONFIGURATION
    # ==========================================
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ CUSUM Parameters")

    # Auto calculation defaults
    calc_mean = float(df_input[val_col].mean())
    calc_std = float(df_input[val_col].std()) if float(df_input[val_col].std()) > 0 else 1.0

    target_mean = st.sidebar.number_input(
        "Target Mean (μ₀):",
        value=round(calc_mean, 3),
        step=0.1,
        help="Expected operational mean during stable baseline."
    )

    use_manual_std = st.sidebar.checkbox("Specify Manual Standard Deviation (σ)", value=False)
    if use_manual_std:
        target_std = st.sidebar.number_input("Standard Deviation (σ):", value=round(calc_std, 3), min_value=0.001, step=0.1)
    else:
        target_std = calc_std
        st.sidebar.caption(f"Auto Standard Deviation (σ): **{calc_std:.3f}**")

    slack_k = st.sidebar.slider(
        "Allowance / Slack Parameter (k):",
        min_value=0.1, max_value=2.0, value=0.5, step=0.1,
        help="Half of the shift size you wish to detect (in units of σ). Default is 0.5."
    )

    threshold_h = st.sidebar.slider(
        "Decision Limit / Threshold (h):",
        min_value=1.0, max_value=10.0, value=4.5, step=0.5,
        help="Control limit multiplier. Signals breach when CUSUM > h * σ. Default is 4 to 5."
    )

    # ==========================================
    # CUSUM CALCULATION ALGORITHM
    # ==========================================
    df = df_input.copy()
    
    # Calculate 7-Day Rolling Mean
    df['7D_Rolling_Mean'] = df[val_col].rolling(window=7, min_periods=1).mean()

    # Calculate Tabular CUSUM
    k_val = slack_k * target_std
    h_val = threshold_h * target_std

    c_plus = np.zeros(len(df))
    c_minus = np.zeros(len(df))

    for i in range(1, len(df)):
        x_i = df[val_col].iloc[i]
        c_plus[i] = max(0, x_i - (target_mean + k_val) + c_plus[i-1])
        c_minus[i] = max(0, (target_mean - k_val) - x_i + c_minus[i-1])

    df['C_plus'] = c_plus
    df['C_minus'] = c_minus
    df['UCL'] = h_val
    df['LCL'] = -h_val

    # Out of control flags
    df['Alarm_Upper'] = df['C_plus'] > h_val
    df['Alarm_Lower'] = df['C_minus'] > h_val
    df['Alarm_Any'] = df['Alarm_Upper'] | df['Alarm_Lower']

    num_upper_alarms = df['Alarm_Upper'].sum()
    num_lower_alarms = df['Alarm_Lower'].sum()

    # ==========================================
    # EXECUTIVE SUMMARY METRICS
    # ==========================================
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Data Points", len(df))
    with col2:
        st.metric("Target Mean (μ₀)", f"{target_mean:.3f}")
    with col3:
        st.metric("Process Std Dev (σ)", f"{target_std:.3f}")
    with col4:
        total_alarms = num_upper_alarms + num_lower_alarms
        st.metric("Out-of-Control Points", f"{total_alarms}", delta=f"{total_alarms} alerts", delta_color="inverse")

    st.markdown("---")

    # ==========================================
    # DUAL CHARTS VISUALIZATION
    # ==========================================
    st.subheader("📊 Dynamic Process & CUSUM Charts")

    # Chart 1: Time Series & 7-Day Rolling Mean
    fig1 = go.Figure()

    # Raw Metric Trace
    fig1.add_trace(go.Scatter(
        x=df[time_col], y=df[val_col],
        mode='lines+markers',
        name='Raw Value',
        line=dict(color='#94A3B8', width=1.5),
        marker=dict(size=4)
    ))

    # 7-Day Rolling Mean Trace
    fig1.add_trace(go.Scatter(
        x=df[time_col], y=df['7D_Rolling_Mean'],
        mode='lines',
        name='7-Day Rolling Mean',
        line=dict(color='#2563EB', width=2.5)
    ))

    # Target Baseline
    fig1.add_trace(go.Scatter(
        x=df[time_col], y=[target_mean]*len(df),
        mode='lines',
        name='Target Baseline (μ₀)',
        line=dict(color='#16A34A', width=2, dash='dash')
    ))

    fig1.update_layout(
        title="<b>Chart 1: Raw Metric Time Series & 7-Day Rolling Trend</b>",
        xaxis_title="Timestamp / Date",
        yaxis_title=val_col,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=380
    )

    st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: CUSUM Chart (Upper & Lower CUSUM)
    fig2 = go.Figure()

    # Upper CUSUM (C+)
    fig2.add_trace(go.Scatter(
        x=df[time_col], y=df['C_plus'],
        mode='lines+markers',
        name='Upper CUSUM (C+)',
        line=dict(color='#E11D48', width=2),
        marker=dict(size=4)
    ))

    # Lower CUSUM (-C-)
    fig2.add_trace(go.Scatter(
        x=df[time_col], y=-df['C_minus'],
        mode='lines+markers',
        name='Lower CUSUM (-C-)',
        line=dict(color='#0284C7', width=2),
        marker=dict(size=4)
    ))

    # Decision Limits (UCL & LCL)
    fig2.add_trace(go.Scatter(
        x=df[time_col], y=df['UCL'],
        mode='lines',
        name=f'Upper Threshold (+{threshold_h}σ)',
        line=dict(color='#DC2626', width=2, dash='dash')
    ))

    fig2.add_trace(go.Scatter(
        x=df[time_col], y=df['LCL'],
        mode='lines',
        name=f'Lower Threshold (-{threshold_h}σ)',
        line=dict(color='#DC2626', width=2, dash='dash')
    ))

    # Highlight Alarm Points
    alarm_df_upper = df[df['Alarm_Upper']]
    if not alarm_df_upper.empty:
        fig2.add_trace(go.Scatter(
            x=alarm_df_upper[time_col], y=alarm_df_upper['C_plus'],
            mode='markers',
            name='Upper Alarm Point',
            marker=dict(color='#7F1D1D', size=10, symbol='triangle-up', line=dict(width=1, color='black'))
        ))

    alarm_df_lower = df[df['Alarm_Lower']]
    if not alarm_df_lower.empty:
        fig2.add_trace(go.Scatter(
            x=alarm_df_lower[time_col], y=-alarm_df_lower['C_minus'],
            mode='markers',
            name='Lower Alarm Point',
            marker=dict(color='#0C4A6E', size=10, symbol='triangle-down', line=dict(width=1, color='black'))
        ))

    fig2.update_layout(
        title=f"<b>Chart 2: Tabular CUSUM Control Chart (h = {threshold_h}, k = {slack_k})</b>",
        xaxis_title="Timestamp / Date",
        yaxis_title="Cumulative Deviation (Units)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=420
    )

    st.plotly_chart(fig2, use_container_width=True)

    # ==========================================
    # DATA TABLE & EXPORT
    # ==========================================
    st.markdown("---")
    st.subheader("📋 Calculated Data Table & Alarm Summary")

    if total_alarms > 0:
        st.warning(f"⚠️ **Out-of-Control Warning**: Detected **{total_alarms}** data point(s) breaching decision thresholds! Check highlighted rows below.")
    else:
        st.success("✅ **Process Stable**: No CUSUM decision limit breaches detected.")

    display_cols = [time_col, val_col, '7D_Rolling_Mean', 'C_plus', 'C_minus', 'Alarm_Upper', 'Alarm_Lower']
    
    st.dataframe(
        df[display_cols].style.highlight_between(
            subset=['C_plus'], left=h_val, right=float('inf'), color='#FECACA'
        ).highlight_between(
            subset=['C_minus'], left=h_val, right=float('inf'), color='#BAE6FD'
        ),
        use_container_width=True
    )

    # CSV Download Button
    csv_data = df[display_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CUSUM Results CSV",
        data=csv_data,
        file_name="CUSUM_Analysis_Results.csv",
        mime="text/csv"
    )

else:
    st.info("👆 Please upload an Excel/CSV file or select 'Use Demo Sample Data' in the left sidebar to begin analysis.")
