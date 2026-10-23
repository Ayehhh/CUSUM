import io
import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ReportLab Imports for PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CUSUM Analysis & Degradation Monitoring",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header { font-size:2.2rem; font-weight:700; color:#1E3A8A; margin-bottom:0rem; }
    .sub-header { font-size:1.0rem; color:#4B5563; margin-bottom:1.5rem; }
    .card { background-color:#F8FAFC; border-radius:10px; padding:15px; border:1px solid #E2E8F0; margin-bottom:15px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# KNOWLEDGE BASE EXPANDER
# -----------------------------------------------------------------------------
st.markdown('<div class="main-header">CUSUM Analysis & Equipment Degradation</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Monitoring subtle baseline shifts and early-stage component degradation</div>', unsafe_allow_html=True)

with st.expander("📚 Knowledge Sharing & CUSUM Definitions (Klik untuk buka/tutup)", expanded=False):
    st.markdown("""
    ### Apa itu CUSUM (Cumulative Sum Control Chart)?
    Carta **CUSUM** ialah teknik *Statistical Process Control (SPC)* yang sangat sensitif untuk mengesan **perubahan kecil (small shifts)** pada purata proses ($\mu$), yang biasanya tidak dapat dikesan oleh carta Shewhart biasa (contoh: $X$-bar chart) secara awal.

    #### Parameter Utama CUSUM:
    * **Target / Baseline ($\mu_0$)**: Nilai operasi normal atau baseline peralatan (contoh: rod drop normal offset, suhu asas, atau tahap getaran normal).
    * **Standard Deviation ($\sigma$)**: Sisihan piawai proses semasa beroperasi secara stabil.
    * **Allowance / Reference value ($k$)**: Parameter sensitiviti. Lazimnya dilaraskan kepada $k = 0.5 \sigma$ (mengesan perubahan bersaiz $1\sigma$).
    * **Decision Limit / Threshold ($h$)**: Ahad kawalan amaran. Lazimnya $h = 4\sigma$ atau $h = 5\sigma$. Apabila nilai CUSUM melebihi $h$, proses/peralatan dianggap **Out of Control** atau mula mengalami **degradation**.

    #### Formula Tabular CUSUM:
    * **Upper CUSUM ($C^+$)** - Mengesan peningkatan drift/offset:
      $$C_i^+ = \max(0, x_i - (\mu_0 + k) + C_{i-1}^+)$$
    * **Lower CUSUM ($C^-$)** - Mengesan penurunan drift/offset:
      $$C_i^- = \max(0, (\mu_0 - k) - x_i + C_{i-1}^-)$$
    """)

st.divider()

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def generate_sample_data():
    """Generates 90 days of equipment degradation/shift sample data."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.date.today(), periods=90, freq="D")
    
    # Baseline normal values
    baseline = 10.0
    noise = np.random.normal(0, 0.3, size=90)
    
    # Inject slight upward degradation shift after day 50
    shift = np.zeros(90)
    shift[50:] = np.linspace(0, 1.8, 40)
    
    values = baseline + noise + shift
    return pd.DataFrame({"Timestamp": dates, "Reading": values})


def calculate_cusum(df, value_col, target, std_dev, k_val, h_val):
    """Calculates Tabular CUSUM (C+ and C-)."""
    df = df.copy()
    c_plus = np.zeros(len(df))
    c_minus = np.zeros(len(df))
    
    values = df[value_col].values
    
    for i in range(1, len(df)):
        c_plus[i] = max(0, values[i] - (target + k_val) + c_plus[i-1])
        c_minus[i] = max(0, (target - k_val) - values[i] + c_minus[i-1])
        
    df["C_plus"] = c_plus
    df["C_minus"] = c_minus
    df["Upper_Limit"] = h_val
    df["Lower_Limit"] = -h_val
    df["Alarm_Upper"] = df["C_plus"] > h_val
    df["Alarm_Lower"] = df["C_minus"] > h_val
    df["Alarm"] = df["Alarm_Upper"] | df["Alarm_Lower"]
    
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

data_source = st.sidebar.radio("Pilih Sumber Data:", ["Guna Sample Data", "Upload Fail Excel/CSV"])

if data_source == "Upload Fail Excel/CSV":
    uploaded_file = st.sidebar.file_uploader("Upload Excel (.xlsx) atau CSV", type=["xlsx", "csv"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
            st.sidebar.success("Fail berjaya di-upload!")
        except Exception as e:
            st.sidebar.error(f"Ralat membaca fail: {e}")
            st.stop()
    else:
        st.info("Sila muat naik fail Excel/CSV anda untuk bermula, atau pilih 'Guna Sample Data'.")
        st.stop()
else:
    df_raw = generate_sample_data()

# Column Selection
st.sidebar.subheader("Pilih Ruangan Data")
columns = df_raw.columns.tolist()

timestamp_col = st.sidebar.selectbox("Ruangan Timestamp / Tarikh:", columns, index=0)
value_col = st.sidebar.selectbox("Ruangan Data / Reading Value:", columns, index=1 if len(columns) > 1 else 0)

# Preprocessing Data
df_raw[timestamp_col] = pd.to_datetime(df_raw[timestamp_col])
df_raw = df_raw.sort_values(by=timestamp_col).reset_index(drop=True)

# 7-Day Rolling Mean
df_raw["Rolling_7D"] = df_raw[value_col].rolling(window=7, min_periods=1).mean()

# CUSUM Parameter Inputs
st.sidebar.subheader("Parameter CUSUM")
auto_calc = st.sidebar.checkbox("Kira Target & Std Dev Otomatik (dari data)", value=True)

if auto_calc:
    default_target = float(df_raw[value_col].mean())
    default_std = float(df_raw[value_col].std())
else:
    default_target = 10.0
    default_std = 0.5

target_val = st.sidebar.number_input("Target Baseline (μ₀)", value=default_target, format="%.4f")
std_val = st.sidebar.number_input("Standard Deviation (σ)", value=default_std, format="%.4f", min_value=0.0001)

k_sigma = st.sidebar.slider("Allowance Factor (k in σ)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
h_sigma = st.sidebar.slider("Decision Limit (h in σ)", min_value=1.0, max_value=10.0, value=4.0, step=0.5)

k_value = k_sigma * std_val
h_value = h_sigma * std_val

# -----------------------------------------------------------------------------
# CUSUM CALCULATION
# -----------------------------------------------------------------------------
df_cusum = calculate_cusum(df_raw, value_col, target_val, std_val, k_value, h_value)

# -----------------------------------------------------------------------------
# METRICS DASHBOARD
# -----------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

total_points = len(df_cusum)
alarm_points = df_cusum["Alarm"].sum()
max_c_plus = df_cusum["C_plus"].max()
latest_val = df_cusum[value_col].iloc[-1]

col1.metric("Jumlah Rekod Data", f"{total_points}")
col2.metric("Nilai Terkini", f"{latest_val:.3f}")
col3.metric("Max Upper CUSUM (C+)", f"{max_c_plus:.3f}")
col4.metric(
    "Status Amaran / Out-of-Control",
    f"{alarm_points} Titik",
    delta="⚠️ Attention" if alarm_points > 0 else "Normal",
    delta_color="inverse" if alarm_points > 0 else "normal",
)

st.divider()

# Image Download Config for Plotly Charts
plotly_img_config = {
    'toImageButtonOptions': {
        'format': 'png', # format muat turun gambar: 'png', 'svg', 'jpeg', 'webp'
        'filename': 'CUSUM_Chart_Export',
        'height': 600,
        'width': 1200,
        'scale': 2 # Resolusi tinggi HD
    },
    'displayModeBar': True
}

# -----------------------------------------------------------------------------
# CHART 1: RAW DATA & 7-DAY ROLLING MEAN
# -----------------------------------------------------------------------------
st.subheader("1. Carta Data Masa Real & 7-Day Rolling Mean")
st.caption("💡 *Nota: Anda boleh memuat turun gambar carta ini secara terus dengan menekan ikon kamera 📷 di sudut kanan atas carta.*")

fig1 = go.Figure()

# Raw Data Line
fig1.add_trace(
    go.Scatter(
        x=df_cusum[timestamp_col],
        y=df_cusum[value_col],
        mode="lines+markers",
        name="Data Mentah (Reading)",
        line=dict(color="#2563EB", width=1.5),
        marker=dict(size=4),
    )
)

# 7-Day Rolling Mean Line
fig1.add_trace(
    go.Scatter(
        x=df_cusum[timestamp_col],
        y=df_cusum["Rolling_7D"],
        mode="lines",
        name="7-Day Rolling Mean",
        line=dict(color="#D97706", width=2.5, dash="dash"),
    )
)

# Target Line
fig1.add_trace(
    go.Scatter(
        x=df_cusum[timestamp_col],
        y=[target_val] * len(df_cusum),
        mode="lines",
        name=f"Target Baseline (μ₀={target_val:.2f})",
        line=dict(color="#059669", width=1.5, dash="dot"),
    )
)

fig1.update_layout(
    xaxis_title="Timestamp / Tarikh",
    yaxis_title="Nilai / Measurement",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=30, b=20),
    template="plotly_white",
)

st.plotly_chart(fig1, use_container_width=True, config=plotly_img_config)

# -----------------------------------------------------------------------------
# CHART 2: CUSUM CONTROL CHART (C+ & C-)
# -----------------------------------------------------------------------------
st.subheader("2. Carta Kawalan CUSUM (Upper C+ & Lower C-)")

fig2 = go.Figure()

# C+ Line
fig2.add_trace(
    go.Scatter(
        x=df_cusum[timestamp_col],
        y=df_cusum["C_plus"],
        mode="lines",
        name="Upper CUSUM (C+)",
        line=dict(color="#DC2626", width=2),
    )
)

# C- Line (Plotted as negative values for standard CUSUM view)
fig2.add_trace(
    go.Scatter(
        x=df_cusum[timestamp_col],
        y=-df_cusum["C_minus"],
        mode="lines",
        name="Lower CUSUM (-C-)",
        line=dict(color="#2563EB", width=2),
    )
)

# Upper Decision Limit +h
fig2.add_trace(
    go.Scatter(
        x=df_cusum[timestamp_col],
        y=df_cusum["Upper_Limit"],
        mode="lines",
        name=f"Upper Limit (+h={h_value:.2f})",
        line=dict(color="#991B1B", width=1.5, dash="dash"),
    )
)

# Lower Decision Limit -h
fig2.add_trace(
    go.Scatter(
        x=df_cusum[timestamp_col],
        y=df_cusum["Lower_Limit"],
        mode="lines",
        name=f"Lower Limit (-h=-{h_value:.2f})",
        line=dict(color="#1E3A8A", width=1.5, dash="dash"),
    )
)

# Highlight Alarm Points
alarm_df = df_cusum[df_cusum["Alarm"]]
if not alarm_df.empty:
    fig2.add_trace(
        go.Scatter(
            x=alarm_df[timestamp_col],
            y=alarm_df["C_plus"].where(alarm_df["Alarm_Upper"], -alarm_df["C_minus"]),
            mode="markers",
            name="⚠️ Alarm / Out of Control",
            marker=dict(color="#EF4444", size=10, symbol="x"),
        )
    )

fig2.update_layout(
    xaxis_title="Timestamp / Tarikh",
    yaxis_title="Nilai Akumulasi CUSUM",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=30, b=20),
    template="plotly_white",
)

st.plotly_chart(fig2, use_container_width=True, config=plotly_img_config)

st.divider()

# -----------------------------------------------------------------------------
# DATA TABLE & REPORT DOWNLOAD SECTION
# -----------------------------------------------------------------------------
st.subheader("📋 Data Jadual & Muat Turun Laporan")

# Tab navigation for table and downloads
tab_data, tab_download = st.tabs(["Jadual Hasil CUSUM", "📥 Muat Turun Laporan & CSV"])

with tab_data:
    display_cols = [timestamp_col, value_col, "Rolling_7D", "C_plus", "C_minus", "Alarm"]
    
    # Safe dataframe display without pandas styling dependency issue
    st.dataframe(
        df_cusum[display_cols],
        use_container_width=True
    )

with tab_download:
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        st.markdown("### 📄 Muat Turun Laporan PDF")
        st.write("Jana laporan ringkasan analisis CUSUM lengkap berformat PDF untuk difailkan atau dibentangkan.")
        
        pdf_buffer = create_pdf_report(
            df_cusum, target_val, std_val, k_value, h_value, timestamp_col, value_col
        )
        
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_buffer,
            file_name=f"CUSUM_Analysis_Report_{datetime.date.today()}.pdf",
            mime="application/pdf",
        )
        
    with col_dl2:
        st.markdown("### 📊 Muat Turun Data CSV")
        st.write("Muat turun jadual pengiraan CUSUM ($C^+$, $C^-$) lengkap dalam format CSV.")
        
        csv_data = df_cusum.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Download Computed Data (CSV)",
            data=csv_data,
            file_name=f"CUSUM_Calculated_Data_{datetime.date.today()}.csv",
            mime="text/csv",
        )

st.caption("Pembangunan Bersama — CUSUM Analysis & Equipment Condition Monitoring App")
