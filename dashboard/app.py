"""
Interactive Streamlit + Plotly Dashboard for UPI Digital Payments Trend Analysis.

Run locally:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = BASE_DIR / "data" / "clean"

st.set_page_config(
    page_title="UPI Digital Payments Trend Analysis",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_data():
    monthly = pd.read_csv(CLEAN_DIR / "fact_upi_monthly.csv", parse_dates=["month_date"])
    full = monthly[~monthly["is_partial_month"]].sort_values("month_date").reset_index(drop=True)
    full["mom_vol_pct"] = full["volume_mn"].pct_change(1) * 100.0
    full["yoy_vol_pct"] = full["volume_mn"].pct_change(12) * 100.0
    full["yoy_val_pct"] = full["value_cr"].pct_change(12) * 100.0
    apps = pd.read_csv(CLEAN_DIR / "fact_app_share.csv", parse_dates=["month_date"])
    banks = pd.read_csv(CLEAN_DIR / "fact_bank_performance.csv", parse_dates=["month_date"])
    p2p_p2m = pd.read_csv(CLEAN_DIR / "fact_p2p_p2m_monthly.csv", parse_dates=["month_date"])
    statewise = pd.read_csv(CLEAN_DIR / "fact_statewise_oct2026.csv", parse_dates=["month_date"])
    stl = pd.read_csv(CLEAN_DIR / "stl_decomposition.csv", parse_dates=["month_date"])
    fc = pd.read_csv(CLEAN_DIR / "forecast_6m.csv", parse_dates=["month_date"])
    summary = json.loads((CLEAN_DIR / "analysis_summary.json").read_text(encoding="utf-8"))
    return full, apps, banks, p2p_p2m, statewise, stl, fc, summary


full, apps, banks, p2p_p2m, statewise, stl, fc, summary = load_data()

st.sidebar.title("💳 UPI Analytics")
st.sidebar.caption("Source: NPCI Official Product & Ecosystem Statistics (2016–2026)")
page = st.sidebar.radio(
    "Navigate",
    [
        "1. Overview",
        "2. Seasonality & Growth",
        "3. Market Structure",
        "4. Bank Reliability",
        "5. Forecast",
    ],
)

if page == "1. Overview":
    st.title("UPI Digital Payments Trend Analysis — Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        f"Volume ({summary['latest_full_month']})",
        f"{summary['latest_volume_bn']:.2f} Bn",
        f"+{summary['latest_yoy_vol_growth_pct']:.1f}% YoY",
    )
    c2.metric(
        f"Value ({summary['latest_full_month']})",
        f"₹{summary['latest_value_lakh_cr']:.2f} Lakh Cr",
        f"+{summary['latest_yoy_val_growth_pct']:.1f}% YoY",
    )
    c3.metric(
        "Avg Ticket Size",
        f"₹{summary['latest_ticket_size_inr']:,.0f}",
        f"from ₹{summary['oct_2021_ticket_size_inr']:,.0f} (Oct'21)",
    )
    c4.metric(
        "P2M Merchant Share",
        f"{summary['p2m_vol_share_oct26_pct']:.1f}%",
        f"Ticket: ₹{summary['p2m_ticket_oct26_inr']:,.0f}",
    )

    col1, col2 = st.columns(2)
    with col1:
        fig_vol = px.area(
            full,
            x="month_date",
            y=full["volume_mn"] / 1000.0,
            title="Monthly UPI Volume (Billions, 2016–2026)",
            labels={"month_date": "Month", "y": "Volume (Billion Txns)"},
        )
        st.plotly_chart(fig_vol, use_container_width=True)
    with col2:
        fig_ts = px.line(
            full[full["month_date"] >= "2018-01-01"],
            x="month_date",
            y="avg_ticket_size_inr",
            title="Average Ticket Size Trend (₹ per Transaction, 2018–2026)",
            labels={"month_date": "Month", "avg_ticket_size_inr": "Avg Ticket Size (₹)"},
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    fig_p2m = px.bar(
        p2p_p2m,
        x="month_date",
        y=["p2m_volume_share_pct", "p2p_volume_share_pct"],
        title="P2M (Merchant) vs P2P Volume Share (Nov 2025 – Oct 2026)",
        labels={"value": "Share (%)", "month_date": "Month", "variable": "Segment"},
    )
    st.plotly_chart(fig_p2m, use_container_width=True)

elif page == "2. Seasonality & Growth":
    st.title("Seasonality & Growth Deceleration")
    c1, c2 = st.columns(2)
    c1.metric("5-Year CMGR (Oct'21–Oct'26)", f"{summary['cmgr_5y_pct']:.2f}%")
    c2.metric("2-Year CMGR (Oct'24–Oct'26)", f"{summary['cmgr_2y_pct']:.2f}%")

    fig_yoy = px.line(
        full[full["month_date"] >= "2019-01-01"],
        x="month_date",
        y=["yoy_vol_pct", "yoy_val_pct"],
        title="Year-over-Year Growth Rate (Volume vs Value, 2019–2026)",
        labels={"value": "YoY Growth (%)", "month_date": "Month", "variable": "Metric"},
    )
    st.plotly_chart(fig_yoy, use_container_width=True)

    # Month-by-Year Heatmap of MoM growth
    heat_df = full[full["month_date"] >= "2019-01-01"].copy()
    heat_df["Year"] = heat_df["month_date"].dt.year
    heat_df["Month"] = heat_df["month_date"].dt.strftime("%b")
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    piv = heat_df.pivot(index="Year", columns="Month", values="mom_vol_pct")[month_order]
    fig_heat = px.imshow(
        piv,
        text_auto=".1f",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        title="Month-over-Month Volume Growth (%) Heatmap (Festival & Fiscal Year-End Patterns)",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    fig_stl = px.line(
        stl,
        x="month_date",
        y=["observed", "trend", "seasonal"],
        title="STL Decomposition (Observed, Trend & Seasonal Components in Millions)",
        labels={"value": "Volume (Mn)", "month_date": "Month", "variable": "Component"},
    )
    st.plotly_chart(fig_stl, use_container_width=True)

elif page == "3. Market Structure":
    st.title("App Market Concentration (HHI) & Geographic Footprint")
    c1, c2, c3 = st.columns(3)
    c1.metric("App HHI (Oct 2026)", f"{summary['latest_app_hhi']:,.1f}", f"from {summary['earliest_app_hhi']:,.1f} (Nov'25)")
    c2.metric("Top-2 App Share", f"{summary['latest_top2_app_share_pct']:.2f}%")
    c3.metric("Top-3 App Share", f"{summary['latest_top3_app_share_pct']:.2f}%")

    top_app_names = apps.groupby("app_name")["volume_mn"].sum().nlargest(7).index.tolist()
    apps_plot = apps.copy()
    apps_plot["app_group"] = apps_plot["app_name"].where(apps_plot["app_name"].isin(top_app_names), "Others")
    apps_grp = apps_plot.groupby(["month_date", "app_group"], as_index=False)["volume_share_pct"].sum()

    col1, col2 = st.columns(2)
    with col1:
        fig_share = px.area(
            apps_grp,
            x="month_date",
            y="volume_share_pct",
            color="app_group",
            title="UPI App Volume Market Share (%)",
            labels={"volume_share_pct": "Share (%)", "month_date": "Month"},
        )
        st.plotly_chart(fig_share, use_container_width=True)
    with col2:
        hhi_ts = (
            apps.groupby("month_date")
            .apply(lambda g: (g["volume_share_pct"] ** 2).sum())
            .reset_index(name="HHI")
        )
        fig_hhi = px.line(hhi_ts, x="month_date", y="HHI", markers=True, title="Herfindahl-Hirschman Index (HHI) Over Time")
        fig_hhi.add_hline(y=2500, line_dash="dash", line_color="red", annotation_text="High Concentration (2,500)")
        st.plotly_chart(fig_hhi, use_container_width=True)

    st.subheader("Top 15 States by UPI Volume (Oct 2026)")
    st_clean = statewise[~statewise["state_ut"].str.contains("Unclassified", case=False, na=False)]
    st_agg = (
        st_clean.groupby("state_ut", as_index=False)
        .agg(volume_mn=("volume_mn", "sum"), value_cr=("value_cr", "sum"))
        .sort_values("volume_mn", ascending=False)
        .head(15)
    )
    fig_st = px.bar(
        st_agg,
        x="volume_mn",
        y="state_ut",
        orientation="h",
        title="Top 15 States/UTs by Volume (Mn, Oct 2026, excluding Unclassified)",
        labels={"volume_mn": "Volume (Mn)", "state_ut": "State / UT"},
    )
    fig_st.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_st, use_container_width=True)

elif page == "4. Bank Reliability":
    st.title("Bank Reliability & Technical Decline (TD%) Hotspots")
    role_choice = st.radio("Select Bank Role", ["remitter", "beneficiary"], horizontal=True)
    months_avail = sorted(banks["month_date"].dt.strftime("%Y-%m").unique(), reverse=True)
    sel_month = st.selectbox("Select Month", months_avail, index=0)
    min_vol = st.slider("Minimum Monthly Volume (Mn)", 10, 500, 50, step=10)

    sub = banks[
        (banks["role"] == role_choice)
        & (banks["month_date"].dt.strftime("%Y-%m") == sel_month)
        & (banks["volume_mn"] >= min_vol)
    ].sort_values("td_pct", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        fig_td = px.bar(
            sub.head(15),
            x="td_pct",
            y="bank_name",
            orientation="h",
            title=f"Top 15 {role_choice.title()} Banks by Technical Decline Rate ({sel_month})",
            labels={"td_pct": "Technical Decline (%)", "bank_name": "Bank"},
        )
        fig_td.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_td, use_container_width=True)
    with col2:
        fig_imp = px.scatter(
            sub,
            x="volume_mn",
            y="td_pct",
            size="estimated_td_txns_mn",
            hover_name="bank_name",
            title=f"Volume vs. TD% (Bubble Size = Est. Failed Txns in Mn, {sel_month})",
            labels={"volume_mn": "Monthly Volume (Mn)", "td_pct": "Technical Decline (%)"},
        )
        st.plotly_chart(fig_imp, use_container_width=True)

    st.dataframe(
        sub[["bank_name", "volume_mn", "approved_pct", "bd_pct", "td_pct", "estimated_td_txns_mn"]].reset_index(drop=True),
        use_container_width=True,
    )

elif page == "5. Forecast":
    st.title("6-Month Volume Forecast & Model Validation")
    c1, c2, c3 = st.columns(3)
    c1.metric("Best Model (6M Holdout)", summary["best_forecast_model"], f"MAPE: {summary['holdout_mape'][summary['best_forecast_model']]:.2f}%")
    c2.metric("Holt-Winters MAPE", f"{summary['holdout_mape']['Holt-Winters']:.2f}%")
    c3.metric("Seasonal Naive Baseline MAPE", f"{summary['holdout_mape']['Seasonal Naive']:.2f}%")

    hist_24 = full.tail(24)
    hold = fc[fc["split"] == "holdout"]
    fut = fc[fc["split"] == "forecast"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_24["month_date"], y=hist_24["volume_mn"] / 1000.0, name="Actuals (24M)", line=dict(color="#1f77b4", width=2.5)))
    fig.add_trace(go.Scatter(x=hold["month_date"], y=hold["forecast_mn"] / 1000.0, name=f"Holdout Pred ({summary['best_forecast_model']})", mode="lines+markers", line=dict(color="#ff7f0e", dash="dash")))
    fig.add_trace(go.Scatter(x=fut["month_date"], y=fut["forecast_mn"] / 1000.0, name="6M Forecast", mode="lines+markers", line=dict(color="#2ca02c", width=3)))
    fig.add_trace(go.Scatter(x=pd.concat([fut["month_date"], fut["month_date"][::-1]]), y=pd.concat([fut["upper_95_mn"] / 1000.0, fut["lower_95_mn"][::-1] / 1000.0]), fill="toself", fillcolor="rgba(44,160,44,0.18)", line=dict(color="rgba(255,255,255,0)"), name="95% Prediction Interval"))
    fig.update_layout(title="UPI Monthly Volume Forecast (Nov 2026 – Apr 2027, Billions)", xaxis_title="Month", yaxis_title="Volume (Billion Txns)")
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "**Forecasting Limits:** Time-series models extrapolate historical trend and seasonality; actual UPI volume remains sensitive to RBI/NPCI policy changes (e.g., MDR rules, UPI Lite/Credit Line limits), major festival timing shifts, and bank infrastructure upgrades."
    )
    st.dataframe(fut[["month_date", "forecast_mn", "lower_95_mn", "upper_95_mn"]].reset_index(drop=True), use_container_width=True)
