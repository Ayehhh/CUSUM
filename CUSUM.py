import io
import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ReportLab Imports for PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CUSUM Analysis & Degradation Monitoring",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main-header { font-size:2.2rem; font-weight:700; color:#1E3A8A; margin-bottom:0rem; }
    .sub-header { font-size:1.0rem; color:#4B5563; margin-bottom:1.5rem; }
    .card { background-color:#F8FAFC; border-radius:10px; padding:15px; border:1px solid #E2E8F0; margin-bottom:15px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# KNOWLEDGE BASE EXPANDER
# -----------------------------------------------------------------------------
st.markdown('<div class="main-header">CUSUM Analysis & Equipment Degradation</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Monitoring subtle baseline shifts and early-stage component degradation</div>', unsafe_allow_html=True)

with st.expander("📚 Knowledge Base & CUSUM Definitions (Click to expand/collapse)", expanded=False):
    st.markdown("""
    ### What is CUSUM (Cumulative Sum Control Chart)?
    The **CUSUM** chart is a *Statistical Process Control (SPC)* technique that is highly sensitive to **small process mean shifts** ($\mu$), which are typically difficult to detect early using standard Shewhart charts (e.g., $X$-bar chart).

    #### Key CUSUM Parameters:
    * **Target / Baseline ($\mu_0$)**: The normal operating baseline value of the equipment (e.g., normal rod drop offset, baseline temperature, or normal vibration level).
    * **Standard Deviation ($\sigma$)**: Process standard deviation during stable baseline operation.
    * **Allowance / Reference value ($k$)**: Sensitivity parameter. Typically set to $k = 0.5 \sigma$ to detect a shift of size $1\sigma$.
    * **Decision Limit / Threshold ($h$)**: Warning control limit. Commonly set to $h = 4\sigma$ or $h = 5\sigma$. When CUSUM exceeds $h$, the process/equipment is considered **Out of Control** or undergoing **degradation**.

    #### Tabular CUSUM Formulas:
    * **Upper CUSUM ($C^+$)** - Detects upward drift/offset:
      $$C_i^+ = \max(0, x_i - (\mu_0 + k) + C_{i-1}^+)$$
    * **Lower CUSUM ($C^-$)** - Detects downward drift/offset:
      $$C_i^- = \max(0, (\mu_0 - k) - x_i + C_{i-1}^-)$$
    """)

st.divider()

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def generate_sample_data():
    """Generates 90 days of equipment degradation/shift sample data."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.date.today(), periods=90, freq='D')
    
    # Baseline normal values
    baseline = 10.0
    noise = np.random.normal(0, 0.3, size=90)
    
    # Inject slight upward degradation shift after day 50
    shift = np.zeros(90)
    shift[50:] = np.linspace(0, 1.8, 40)
    
    values = baseline + noise + shift
    return pd.DataFrame({
        "Timestamp": dates,
        "Reading": values
    })

def calculate_cusum(df, value_col, target, std_dev, k_val, h_val):
    """Calculates Tabular CUSUM (C+ and C-)."""
    df = df.copy()
    c_plus = np.zeros(len(df))
    c_minus = np.zeros(len(df))
    
    values = df[value_col].values
    
    for i in range(1, len(df)):
        c_plus[i] = max(0, values[i] - (target + k_val) + c_plus[i-1])
        c_minus[i] = max(0, (target - k_val) - values[i] + c_minus[i-1])
        
    df['C_plus'] = c_plus
    df['C_minus'] = c_minus
    df['Upper_Limit'] = h_val
    df['Lower_Limit'] = -h_val
    df['Alarm_Upper'] = df['C_plus'] > h_val
    df['Alarm_Lower'] = df['C_minus'] > h_val
    df['Alarm'] = df['Alarm_Upper'] | df['Alarm_Lower']
    
    return df

def create_pdf_report(df, target, std_dev, k_val, h_val, date_col, val_col):
    """Generates a downloadable PDF report using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1E3A8A'), spaceAfter=12)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#1E3A8A'), spaceAfter=8)
    normal_style = styles['Normal']
    
    # Title & Metadata
    story.append(Paragraph("<b>CUSUM Analysis & Equipment Degradation Report</b>", title_style))
    story.append(Paragraph(f"<b>Generated Date:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=15))
    
    # Parameter Summary Table
    story.append(Paragraph("<b>1. Analysis Parameters & Baseline Settings</b>", heading_style))
    param_data = [
        ["Parameter", "Configured Value", "Description"],
        ["Target Mean (μ₀)", f"{target:.4f}", "Baseline mean value"],
        ["Std Deviation (σ)", f"{std_dev:.4f}", "Estimated process standard deviation"],
        ["Allowance (k)", f"{k_val:.4f}", f"Reference allowance ({k_val/std_dev:.2f} σ)"],
        ["Decision Limit (h)", f"{h_val:.4f}", f"Threshold limit ({h_val/std_dev:.2f} σ)"]
    ]
    t_param = Table(param_data, colWidths=[150, 120, 240])
    t_param.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t_param)
    story.append(Spacer(1, 15))
    
    # Statistical Highlights
    total_records = len(df)
    total_alarms = df['Alarm'].sum()
    max_c_plus = df['C_plus'].max()
    max_c_minus = df['C_minus'].max()
    
    story.append(Paragraph("<b>2. Executive Summary & Anomaly Signals</b>", heading_style))
    summary_text = f"""
    * <b>Total Data Points Analyzed:</b> {total_records}<br/>
    * <b>Out-of-Control Points (Alarms):</b> <font color="{'red' if total_alarms > 0 else 'green'}"><b>{total_alarms}</b></font><br/>
    * <b>Maximum C+ (Upper Drift):</b> {max_c_plus:.4f}<br/>
    * <b>Maximum C- (Lower Drift):</b> {max_c_minus:.4f}<br/>
    * <b>Status:</b> {'⚠️ ATTENTION REQUIRED - Baseline shift detected!' if total_alarms > 0 else '✅ NORMAL - Process operating within statistical limits.'}
    """
    story.append(Paragraph(summary_text, normal_style))
    story.append(Spacer(1, 15))
    
    # Recent Alarms Table
    story.append(Paragraph("<b>3. Recent Alarm Events (Upper Limit > h or Lower Limit > h)</b>", heading_style))
    alarm_df = df[df['Alarm']][[date_col, val_col, 'C_plus', 'C_minus']].tail(10)
    
    if len(alarm_df) == 0:
        story.append(Paragraph("<i>No alarm signals detected in the dataset.</i>", normal_style))
    else:
        alarm_table_data = [["Timestamp", "Reading Value", "C+ Value", "C- Value"]]
        for _, row in alarm_df.iterrows():
            ts_str = str(row[date_col]).split("T")[0] if "T" in str(row[date_col]) else str(row[date_col])[:10]
            alarm_table_data.append([
                ts_str,
                f"{row[val_col]:.4f}",
                f"{row['C_plus']:.4f}",
                f"{row['C_minus']:.4f}"
            ])
        t_alarm = Table(alarm_table_data, colWidths=[130, 120, 130, 130])
        t_alarm.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#DC2626')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FCA5A5')),
        ]))
        story.append(t_alarm)
        
    doc.build(story)
    buffer.seek(0)
    return buffer

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Data Input & Configuration")

data_source = st.sidebar.radio("Select Data Source:", ["Use Sample Data", "Upload Excel/CSV File"])
