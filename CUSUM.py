import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Rod Drop CUSUM Analysis", layout="wide")
st.title("Rod Drop Trend & CUSUM")
st.caption("CUSUM detects sustained shifts relative to a selected baseline. It is not a direct wear-rate or clearance measurement.")

with st.sidebar:
    st.header("Settings")
    rolling_days = st.number_input("Rolling median window (days)", 1, 30, 7)
    k = st.number_input("CUSUM allowance k (standard deviations)", 0.1, 3.0, 0.5, 0.1)
    h = st.number_input("CUSUM threshold h", 1.0, 20.0, 5.0, 0.5)

file = st.file_uploader("Upload CSV or tab-separated file", type=["csv", "txt"])
if file is None:
    st.info("Upload a file with a timestamp column and an Average Probe Position column.")
    st.code("Timestamp,Average Probe Position\n08/10/2025 05:37,31.538126\n08/10/2025 05:43,33.871440")
    st.stop()

try:
    df = pd.read_csv(file, sep=None, engine="python")
except Exception as exc:
    st.error(f"Unable to read file: {exc}")
    st.stop()

if df.empty:
    st.error("The uploaded file is empty.")
    st.stop()

cols = list(df.columns)
a, b = st.columns(2)
with a:
    timestamp_col = st.selectbox("Timestamp column", cols, index=0)
with b:
    likely = next((i for i, name in enumerate(cols) if any(x in str(name).lower() for x in ["average probe position", "avg probe", "probe position", "position"])), min(1, len(cols)-1))
    value_col = st.selectbox("Average Probe Position column", cols, index=likely)

data = df[[timestamp_col, value_col]].copy()
data.columns = ["Timestamp", "AverageProbePosition"]
# dayfirst=True reads 08/10/2025 as 8 October 2025.
data["Timestamp"] = pd.to_datetime(data["Timestamp"], errors="coerce", dayfirst=True)
data["AverageProbePosition"] = pd.to_numeric(data["AverageProbePosition"], errors="coerce")
data = data.dropna(subset=["Timestamp", "AverageProbePosition"]).sort_values("Timestamp")
data = data.drop_duplicates("Timestamp", keep="last").reset_index(drop=True)

if len(data) < 30:
    st.error("Fewer than 30 valid samples. Check the selected columns and file format.")
    st.stop()

st.write(f"Valid samples: **{len(data):,}** | From **{data.Timestamp.min()}** to **{data.Timestamp.max()}**")

min_date, max_date = data.Timestamp.min().date(), data.Timestamp.max().date()
st.subheader("Choose a healthy baseline period")
c1, c2 = st.columns(2)
with c1:
    start = st.date_input("Baseline start", value=min_date, min_value=min_date, max_value=max_date)
with c2:
    proposed_end = min(max_date, (pd.Timestamp(start) + pd.Timedelta(days=14)).date())
    end = st.date_input("Baseline end", value=proposed_end, min_value=min_date, max_value=max_date)

start_ts = pd.Timestamp(start)
end_ts = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
baseline_mask = data.Timestamp.between(start_ts, end_ts)
baseline = data.loc[baseline_mask, "AverageProbePosition"]
if len(baseline) < 30:
    st.warning("Baseline has fewer than 30 samples. Select a longer representative healthy period.")
    st.stop()

mu = float(baseline.mean())
sigma = float(baseline.std(ddof=1))
if not np.isfinite(sigma) or sigma <= 0:
    st.error("Baseline standard deviation is zero or invalid. Choose another baseline.")
    st.stop()

# Standardised one-sided CUSUM: C+ detects upward shifts, C- detects downward shifts.
z = ((data.AverageProbePosition - mu) / sigma).to_numpy()
up = np.zeros(len(data))
down = np.zeros(len(data))
for i in range(1, len(data)):
    up[i] = max(0.0, up[i-1] + z[i] - k)
    down[i] = max(0.0, down[i-1] - z[i] - k)

data["CUSUM_Up"] = up
data["CUSUM_Down"] = down
data["DetectionStatus"] = np.select(
    [data.CUSUM_Up >= h, data.CUSUM_Down >= h],
    ["UPWARD SHIFT", "DOWNWARD SHIFT"],
    default="NORMAL"
)
data["RollingMedian"] = (
    data.set_index("Timestamp")["AverageProbePosition"]
    .rolling(f"{int(rolling_days)}D", min_periods=30).median().to_numpy()
)
