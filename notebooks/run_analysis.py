"""
Comprehensive Statistical Analysis & Forecasting for NPCI UPI Data.

Computes:
1. Growth metrics (MoM, YoY, CMGR, deceleration check)
2. STL Time-Series Decomposition (trend, seasonal, residual)
3. Market Concentration (App & Bank HHI, Top-2 / Top-3 shares)
4. Bank Reliability Hotspots (Remitter & Beneficiary TD%, volume-weighted impact)
5. Ticket Size & P2P vs P2M Structural Shift
6. Forecasting: Seasonal Naive vs Holt-Winters vs SARIMA on 6-month holdout (MAPE),
   plus 6-month forward forecast with 95% prediction intervals.
7. Saves outputs to data/clean/ and high-res charts to reports/figures/.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = BASE_DIR / "data" / "clean"
FIG_DIR = BASE_DIR / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "font.size": 10,
    }
)


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100.0)


def main() -> None:
    monthly = pd.read_csv(CLEAN_DIR / "fact_upi_monthly.csv", parse_dates=["month_date"])
    full = monthly[~monthly["is_partial_month"]].sort_values("month_date").reset_index(drop=True)
    apps = pd.read_csv(CLEAN_DIR / "fact_app_share.csv", parse_dates=["month_date"])
    banks = pd.read_csv(CLEAN_DIR / "fact_bank_performance.csv", parse_dates=["month_date"])
    p2p_p2m = pd.read_csv(CLEAN_DIR / "fact_p2p_p2m_monthly.csv", parse_dates=["month_date"])
    statewise = pd.read_csv(CLEAN_DIR / "fact_statewise_oct2026.csv", parse_dates=["month_date"])

    # 1. Growth Metrics
    full["mom_vol_pct"] = full["volume_mn"].pct_change(1) * 100.0
    full["yoy_vol_pct"] = full["volume_mn"].pct_change(12) * 100.0
    full["yoy_val_pct"] = full["value_cr"].pct_change(12) * 100.0

    latest = full.iloc[-1]
    prev_yr = full.iloc[-13]
    # 5-year CMGR (Oct 2021 -> Oct 2026)
    row_5y = full[full["month_date"] == latest["month_date"] - pd.DateOffset(years=5)].iloc[0]
    cmgr_5y = ((latest["volume_mn"] / row_5y["volume_mn"]) ** (1.0 / 60.0) - 1.0) * 100.0
    # 2-year CMGR (Oct 2024 -> Oct 2026)
    row_2y = full[full["month_date"] == latest["month_date"] - pd.DateOffset(years=2)].iloc[0]
    cmgr_2y = ((latest["volume_mn"] / row_2y["volume_mn"]) ** (1.0 / 24.0) - 1.0) * 100.0

    # 2. STL Seasonality Decomposition (on 2019-01 onwards for stable scale)
    ts_df = full[full["month_date"] >= "2019-01-01"].set_index("month_date")["volume_mn"]
    ts_df.index.freq = "MS"
    stl = STL(ts_df, period=12, robust=True).fit()
    stl_out = pd.DataFrame(
        {
            "month_date": ts_df.index,
            "observed": stl.observed.values,
            "trend": stl.trend.values,
            "seasonal": stl.seasonal.values,
            "resid": stl.resid.values,
        }
    )
    stl_out.to_csv(CLEAN_DIR / "stl_decomposition.csv", index=False)

    # 3. Market Concentration (App HHI & Top-2 Share)
    app_hhi = (
        apps.sort_values(["month_date", "volume_share_pct"], ascending=[True, False])
        .groupby("month_date")
        .apply(
            lambda g: pd.Series(
                {
                    "hhi_volume": float((g["volume_share_pct"] ** 2).sum()),
                    "top2_share_pct": float(g["volume_share_pct"].head(2).sum()),
                    "top3_share_pct": float(g["volume_share_pct"].head(3).sum()),
                    "leader_app": g.iloc[0]["app_name"],
                    "leader_share_pct": float(g.iloc[0]["volume_share_pct"]),
                }
            )
        )
        .reset_index()
    )

    # 4. Bank Reliability Hotspots (Latest month & 12-month avg for remitter banks >= 50 Mn/mo)
    latest_bank_dt = banks["month_date"].max()
    rem_latest = banks[(banks["month_date"] == latest_bank_dt) & (banks["role"] == "remitter") & (banks["volume_mn"] >= 50)].copy()
    rem_latest = rem_latest.sort_values("td_pct", ascending=False)
    rem_12m = (
        banks[(banks["role"] == "remitter")]
        .groupby("bank_name", as_index=False)
        .agg(
            avg_volume_mn=("volume_mn", "mean"),
            avg_td_pct=("td_pct", "mean"),
            avg_bd_pct=("bd_pct", "mean"),
            total_est_td_txns_mn=("estimated_td_txns_mn", "sum"),
        )
    )
    rem_12m_major = rem_12m[rem_12m["avg_volume_mn"] >= 50].sort_values("avg_td_pct", ascending=False)

    # 5. Forecasting (Holdout: May 2026 - Oct 2026 = 6 months)
    train = ts_df.iloc[:-6]
    test = ts_df.iloc[-6:]

    # Model A: Seasonal Naive (same month prior year)
    snaive_pred = ts_df.iloc[-18:-12].values
    mape_snaive = mape(test.values, snaive_pred)

    # Model B: Holt-Winters (Additive Trend + Multiplicative Seasonality)
    hw_fit = ExponentialSmoothing(
        train, trend="add", seasonal="mul", seasonal_periods=12, damped_trend=True
    ).fit(optimized=True)
    hw_pred = hw_fit.forecast(6).values
    mape_hw = mape(test.values, hw_pred)

    # Model C: SARIMA(1,1,1)(1,1,0)[12]
    sarima_fit = SARIMAX(
        train, order=(1, 1, 1), seasonal_order=(1, 1, 0, 12), enforce_stationarity=False, enforce_invertibility=False
    ).fit(disp=False)
    sarima_pred = sarima_fit.forecast(6).values
    mape_sarima = mape(test.values, sarima_pred)

    # Select best model on holdout MAPE and refit on full series for Nov 2026 - Apr 2027
    scores = {"Seasonal Naive": mape_snaive, "Holt-Winters": mape_hw, "SARIMA": mape_sarima}
    best_model_name = min(scores, key=scores.get)

    # Refit SARIMA and Holt-Winters on full ts_df; use SARIMA for formal 95% PI if best or HW simulation
    full_sarima = SARIMAX(
        ts_df, order=(1, 1, 1), seasonal_order=(1, 1, 0, 12), enforce_stationarity=False, enforce_invertibility=False
    ).fit(disp=False)
    sarima_fc = full_sarima.get_forecast(steps=6)
    sarima_ci = sarima_fc.conf_int(alpha=0.05)

    full_hw = ExponentialSmoothing(
        ts_df, trend="add", seasonal="mul", seasonal_periods=12, damped_trend=True
    ).fit(optimized=True)
    hw_fc_vals = full_hw.forecast(6).values

    if best_model_name == "Holt-Winters":
        point_fc = hw_fc_vals
        # Residual-based 95% PI around HW forecast
        resid_std = float(np.std(full_hw.resid))
        horizon = np.arange(1, 7)
        lower_95 = point_fc - 1.96 * resid_std * np.sqrt(horizon)
        upper_95 = point_fc + 1.96 * resid_std * np.sqrt(horizon)
    else:
        point_fc = sarima_fc.predicted_mean.values
        lower_95 = sarima_ci.iloc[:, 0].values
        upper_95 = sarima_ci.iloc[:, 1].values

    future_dates = pd.date_range(ts_df.index[-1] + pd.DateOffset(months=1), periods=6, freq="MS")
    fc_df = pd.concat(
        [
            pd.DataFrame(
                {
                    "month_date": test.index,
                    "split": "holdout",
                    "actual_volume_mn": test.values,
                    "pred_snaive_mn": snaive_pred,
                    "pred_hw_mn": hw_pred,
                    "pred_sarima_mn": sarima_pred,
                    "forecast_mn": hw_pred if best_model_name == "Holt-Winters" else sarima_pred,
                    "lower_95_mn": np.nan,
                    "upper_95_mn": np.nan,
                }
            ),
            pd.DataFrame(
                {
                    "month_date": future_dates,
                    "split": "forecast",
                    "actual_volume_mn": np.nan,
                    "pred_snaive_mn": np.nan,
                    "pred_hw_mn": hw_fc_vals,
                    "pred_sarima_mn": sarima_fc.predicted_mean.values,
                    "forecast_mn": point_fc,
                    "lower_95_mn": lower_95,
                    "upper_95_mn": upper_95,
                }
            ),
        ],
        ignore_index=True,
    )
    fc_df.to_csv(CLEAN_DIR / "forecast_6m.csv", index=False)

    # Save JSON summary of exact verified numbers
    summary = {
        "latest_full_month": latest["month_date"].strftime("%Y-%m"),
        "latest_volume_mn": round(float(latest["volume_mn"]), 2),
        "latest_volume_bn": round(float(latest["volume_mn"]) / 1000.0, 2),
        "latest_value_cr": round(float(latest["value_cr"]), 2),
        "latest_value_lakh_cr": round(float(latest["value_cr"]) / 100000.0, 2),
        "latest_yoy_vol_growth_pct": round(float(latest["yoy_vol_pct"]), 2),
        "latest_yoy_val_growth_pct": round(float(latest["yoy_val_pct"]), 2),
        "latest_ticket_size_inr": round(float(latest["avg_ticket_size_inr"]), 2),
        "oct_2021_ticket_size_inr": round(float(row_5y["avg_ticket_size_inr"]), 2),
        "cmgr_5y_pct": round(float(cmgr_5y), 2),
        "cmgr_2y_pct": round(float(cmgr_2y), 2),
        "latest_app_hhi": round(float(app_hhi.iloc[-1]["hhi_volume"]), 1),
        "earliest_app_hhi": round(float(app_hhi.iloc[0]["hhi_volume"]), 1),
        "latest_top2_app_share_pct": round(float(app_hhi.iloc[-1]["top2_share_pct"]), 2),
        "latest_top3_app_share_pct": round(float(app_hhi.iloc[-1]["top3_share_pct"]), 2),
        "p2p_vol_share_oct26_pct": round(float(p2p_p2m.iloc[-1]["p2p_volume_share_pct"]), 2),
        "p2m_vol_share_oct26_pct": round(float(p2p_p2m.iloc[-1]["p2m_volume_share_pct"]), 2),
        "p2p_ticket_oct26_inr": round(float(p2p_p2m.iloc[-1]["p2p_avg_ticket_inr"]), 2),
        "p2m_ticket_oct26_inr": round(float(p2p_p2m.iloc[-1]["p2m_avg_ticket_inr"]), 2),
        "top_td_remitter_latest": rem_latest.head(5)[["bank_name", "volume_mn", "td_pct", "estimated_td_txns_mn"]].to_dict(orient="records"),
        "top_td_remitter_12m_avg": rem_12m_major.head(5).to_dict(orient="records"),
        "holdout_mape": {k: round(v, 2) for k, v in scores.items()},
        "best_forecast_model": best_model_name,
        "forecast_next_6m_min_bn": round(float(point_fc.min()) / 1000.0, 2),
        "forecast_next_6m_max_bn": round(float(point_fc.max()) / 1000.0, 2),
        "top_state_oct26": statewise.groupby("state_ut")["volume_mn"].sum().idxmax(),
    }
    (CLEAN_DIR / "analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    # --- Generate 4 High-Res Figures for README & Insights Report ---
    # Fig 1: Long-Term Growth & Ticket Size
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True)
    ax1.plot(full["month_date"], full["volume_mn"] / 1000.0, color="#1f77b4", lw=2.2, label="Volume (Billions)")
    ax1.set_ylabel("Volume (Billion Txns)")
    ax1.set_title("UPI Monthly Transaction Volume & Average Ticket Size (2016–2026)", fontweight="bold")
    ax1.legend(loc="upper left")
    ax2.plot(full["month_date"], full["avg_ticket_size_inr"], color="#d95f02", lw=2.0, label="Avg Ticket Size (INR)")
    ax2.set_ylabel("Avg Ticket Size (₹)")
    ax2.set_ylim(0, 5200)
    ax2.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "01_growth_and_ticket_size.png")
    plt.close(fig)

    # Fig 2: STL Decomposition
    fig, axes = plt.subplots(4, 1, figsize=(10, 7.5), sharex=True)
    for ax, col, title, clr in zip(
        axes,
        ["observed", "trend", "seasonal", "resid"],
        ["Observed Volume (Mn)", "Trend Component", "Seasonal Component", "Residual"],
        ["#1f77b4", "#2ca02c", "#ff7f0e", "#7f7f7f"],
    ):
        ax.plot(stl_out["month_date"], stl_out[col] / 1000.0, color=clr, lw=1.8)
        ax.set_ylabel("Bn Txns")
        ax.set_title(title, fontsize=10, fontweight="bold")
    fig.suptitle("STL Time-Series Decomposition of Monthly UPI Volume (2019–2026)", fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "02_stl_decomposition.png", bbox_inches="tight")
    plt.close(fig)

    # Fig 3: App Market Share & HHI
    top_apps = ["PhonePe", "Google Pay", "Paytm", "Navi", "CRED"]
    app_pivot = apps.pivot_table(index="month_date", columns="app_name", values="volume_share_pct", aggfunc="sum").fillna(0)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    for app in top_apps:
        if app in app_pivot.columns:
            ax1.plot(app_pivot.index, app_pivot[app], marker="o", ms=3, lw=2, label=app)
    ax1.set_title("UPI App Market Share (Nov 2025 – Oct 2026)", fontweight="bold")
    ax1.set_ylabel("Volume Share (%)")
    ax1.legend(fontsize=8)
    ax1.tick_params(axis="x", rotation=35)
    ax2.plot(app_hhi["month_date"], app_hhi["hhi_volume"], color="#7570b3", marker="s", lw=2.2)
    ax2.axhline(2500, color="red", ls="--", lw=1, label="DOJ High Concentration (2,500)")
    ax2.set_title("App Market Concentration (HHI)", fontweight="bold")
    ax2.set_ylabel("HHI (0–10,000)")
    ax2.legend(fontsize=8)
    ax2.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "03_market_concentration.png")
    plt.close(fig)

    # Fig 4: 6-Month Forecast + Holdout Validation
    fig, ax = plt.subplots(figsize=(10, 4.8))
    hist_recent = ts_df.iloc[-24:]
    ax.plot(hist_recent.index, hist_recent.values / 1000.0, color="#1f77b4", lw=2.2, label="Actuals (Recent 24M)")
    hold = fc_df[fc_df["split"] == "holdout"]
    fut = fc_df[fc_df["split"] == "forecast"]
    ax.plot(hold["month_date"], hold["forecast_mn"] / 1000.0, color="#ff7f0e", ls="--", marker="o", lw=2, label=f"Holdout Pred ({best_model_name}, MAPE {scores[best_model_name]:.2f}%)")
    ax.plot(fut["month_date"], fut["forecast_mn"] / 1000.0, color="#2ca02c", marker="o", lw=2.4, label="6-Month Forecast (Nov 2026–Apr 2027)")
    ax.fill_between(fut["month_date"], fut["lower_95_mn"] / 1000.0, fut["upper_95_mn"] / 1000.0, color="#2ca02c", alpha=0.18, label="95% Prediction Interval")
    ax.set_title("UPI Monthly Volume Forecast & Holdout Validation", fontweight="bold")
    ax.set_ylabel("Volume (Billion Txns)")
    ax.legend(loc="upper left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "04_volume_forecast.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
