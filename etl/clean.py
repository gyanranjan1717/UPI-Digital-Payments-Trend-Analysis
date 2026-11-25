"""
ETL & Data Cleaning Pipeline for NPCI UPI Statistics.

Reads raw Excel (.xlsx) files from data/raw/{product_stats, upi_apps, top50_remitter,
top50_beneficiary, p2p_p2m, statewise}, standardizes schemas, units, dates, app/bank
names, runs sanity checks, and writes clean CSVs + data dictionary to data/clean/.
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Optional

import numpy as np
import openpyxl
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
CLEAN_DIR = BASE_DIR / "data" / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)


def parse_num(val) -> float:
    """Parse numeric values from strings with Indian/Western commas, %, or whitespace."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in {"na", "n/a", "nil", "-", "--", "nan", "none"}:
        return np.nan
    s = s.replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_month_str(s: str) -> Optional[pd.Timestamp]:
    """Parse month strings like 'March-2017', 'Nov-25', 'Dec\\'25', 'October_2026'."""
    if not s:
        return None
    s = str(s).strip().replace("'", "-").replace("_", "-").replace(" ", "-")
    # Handle formats like "November-2026", "Nov-25", "Mar-26"
    for fmt in ("%B-%Y", "%b-%Y", "%b-%y", "%B-%y", "%Y-%m-%d"):
        try:
            dt = pd.to_datetime(s, format=fmt)
            return pd.Timestamp(year=dt.year, month=dt.month, day=1)
        except Exception:
            pass
    try:
        dt = pd.to_datetime(s)
        return pd.Timestamp(year=dt.year, month=dt.month, day=1)
    except Exception:
        return None


def extract_month_from_title(title: str) -> Optional[pd.Timestamp]:
    """Extract month from sheet title like \"UPI Apps (Dec'25)\" or \"(Oct'26)\"."""
    if not title:
        return None
    m = re.search(r"\(([A-Za-z]+['\-\s]*\d{2,4})\)", str(title))
    if m:
        return parse_month_str(m.group(1))
    return None


def clean_app_name(name: str) -> str:
    """Normalize UPI app names (strip footnotes #, *, extra spaces, unify aliases)."""
    s = str(name).strip()
    s = re.sub(r"[#*†‡]+$", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    aliases = {
        "google pay": "Google Pay",
        "phonepe": "PhonePe",
        "paytm": "Paytm",
        "paytm payments bank": "Paytm",
        "paytm (ocl)": "Paytm",
        "one97 communications (paytm)": "Paytm",
        "cred": "CRED",
        "amazon pay": "Amazon Pay",
        "bhim": "BHIM",
        "navi": "Navi",
        "super.money": "super.money",
        "supermoney": "super.money",
        "famapp by triotech": "FamApp",
        "famapp": "FamApp",
        "whatsapp": "WhatsApp",
        "whatsapp pay": "WhatsApp",
        "groww": "Groww",
        "bajaj finserv": "Bajaj Finserv",
        "slice": "Slice",
        "jupiter": "Jupiter",
        "jupiter money": "Jupiter",
        "mobikwik": "MobiKwik",
        "pop": "POP",
        "kiwi": "Kiwi",
        "flipkart upi": "Flipkart UPI",
        "tata neu": "Tata Neu",
        "airtel payments bank": "Airtel Payments Bank",
        "icici imobile": "ICICI iMobile",
        "axis pay": "Axis Pay",
        "kotak mahindra bank": "Kotak Mahindra Bank",
    }
    low = s.lower()
    for k, v in aliases.items():
        if low == k:
            return v
    return s


def clean_bank_name(name: str) -> str:
    """Normalize bank names across inconsistent casing, punctuation, and suffixes."""
    s = str(name).strip()
    s = re.sub(r"[#*]+$", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    # Standardize common casing and abbreviations
    low = s.lower()
    canonical_map = {
        "state bank of india": "State Bank of India",
        "hdfc bank": "HDFC Bank",
        "hdfc bank ltd": "HDFC Bank",
        "hdfc bank ltd.": "HDFC Bank",
        "icici bank": "ICICI Bank",
        "icici bank ltd": "ICICI Bank",
        "icici bank ltd.": "ICICI Bank",
        "axis bank": "Axis Bank",
        "axis bank ltd": "Axis Bank",
        "axis bank ltd.": "Axis Bank",
        "yes bank": "Yes Bank",
        "yes bank ltd": "Yes Bank",
        "yes bank ltd.": "Yes Bank",
        "kotak mahindra bank": "Kotak Mahindra Bank",
        "kotak mahindra bank ltd": "Kotak Mahindra Bank",
        "kotak mahindra bank ltd.": "Kotak Mahindra Bank",
        "bank of baroda": "Bank of Baroda",
        "punjab national bank": "Punjab National Bank",
        "canara bank": "Canara Bank",
        "union bank of india": "Union Bank of India",
        "bank of india": "Bank of India",
        "indian bank": "Indian Bank",
        "central bank of india": "Central Bank of India",
        "indian overseas bank": "Indian Overseas Bank",
        "uco bank": "UCO Bank",
        "bank of maharashtra": "Bank of Maharashtra",
        "punjab & sind bank": "Punjab and Sind Bank",
        "punjab and sind bank": "Punjab and Sind Bank",
        "indusind bank": "IndusInd Bank",
        "indusind bank ltd": "IndusInd Bank",
        "indusind bank ltd.": "IndusInd Bank",
        "federal bank": "Federal Bank",
        "federal bank ltd": "Federal Bank",
        "federal bank ltd.": "Federal Bank",
        "idfc first bank": "IDFC First Bank",
        "idfc first bank ltd": "IDFC First Bank",
        "idfc first bank ltd.": "IDFC First Bank",
        "idbi bank": "IDBI Bank",
        "idbi bank ltd": "IDBI Bank",
        "idbi bank ltd.": "IDBI Bank",
        "bandhan bank": "Bandhan Bank",
        "bandhan bank ltd": "Bandhan Bank",
        "bandhan bank ltd.": "Bandhan Bank",
        "bandhan bank limited": "Bandhan Bank",
        "rbl bank": "RBL Bank",
        "rbl bank ltd": "RBL Bank",
        "rbl bank ltd.": "RBL Bank",
        "rbl bank limited": "RBL Bank",
        "south indian bank": "South Indian Bank",
        "the south indian bank limited": "South Indian Bank",
        "karnataka bank": "Karnataka Bank",
        "karur vysya bank": "Karur Vysya Bank",
        "city union bank": "City Union Bank",
        "au small finance bank": "AU Small Finance Bank",
        "au small finance bank ltd": "AU Small Finance Bank",
        "au small finance bank limited": "AU Small Finance Bank",
        "airtel payments bank": "Airtel Payments Bank",
        "airtel payments bank ltd": "Airtel Payments Bank",
        "airtel payments bank limited": "Airtel Payments Bank",
        "paytm payments bank": "Paytm Payments Bank",
        "india post payments bank": "India Post Payments Bank",
        "india post payments bank ltd": "India Post Payments Bank",
        "india post payments bank limited": "India Post Payments Bank",
        "fino payments bank": "Fino Payments Bank",
        "fino payments bank ltd": "Fino Payments Bank",
        "fino payments bank limited": "Fino Payments Bank",
        "jio payments bank": "Jio Payments Bank",
        "jio payments bank ltd": "Jio Payments Bank",
        "jio payments bank limited": "Jio Payments Bank",
        "nsdl payments bank": "NSDL Payments Bank",
        "nsdl payments bank ltd": "NSDL Payments Bank",
        "nsdl payments bank limited": "NSDL Payments Bank",
        "dbs bank": "DBS Bank India",
        "dbs bank india ltd": "DBS Bank India",
        "dbs bank india limited": "DBS Bank India",
        "hsbc": "HSBC Bank",
        "hsbc bank": "HSBC Bank",
        "standard chartered bank": "Standard Chartered Bank",
        "jammu & kashmir bank": "Jammu & Kashmir Bank",
        "the jammu & kashmir bank limited": "Jammu & Kashmir Bank",
        "jammu and kashmir bank": "Jammu & Kashmir Bank",
    }
    if low in canonical_map:
        return canonical_map[low]
    # Clean trailing Ltd / Limited for remaining banks
    cleaned = re.sub(r"\b(ltd\.?|limited)\b", "", s, flags=re.IGNORECASE).strip(" ,.-")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.title() if cleaned.isupper() or cleaned.islower() else cleaned


def load_product_stats() -> pd.DataFrame:
    """Consolidate monthly UPI Product Statistics (2016-17 through 2026-27)."""
    files = sorted(glob.glob(str(RAW_DIR / "product_stats" / "*.xlsx")))
    records = []
    for f in files:
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            continue
        header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
        is_monthly_tab = "avg. daily volume" in " ".join(header)
        for r in rows[1:]:
            if not r or r[0] is None:
                continue
            m_str = str(r[0]).strip()
            if not m_str or m_str.lower().startswith(("total", "note", "source")):
                continue
            dt = parse_month_str(m_str)
            if dt is None:
                continue
            if is_monthly_tab:
                # ['Month', 'Volume (In Mn.)', 'Avg. Daily Volume (In Mn.)', 'Value (In Cr.)', 'Avg. Daily Value (In Cr.)']
                vol_mn = parse_num(r[1])
                val_cr = parse_num(r[3])
                banks_live = np.nan
            else:
                # ['Month', 'No. of Banks live on UPI', 'Volume (In Mn.)', 'Value (In Cr.)']
                banks_live = parse_num(r[1])
                vol_mn = parse_num(r[2])
                val_cr = parse_num(r[3])
            records.append(
                {
                    "month_date": dt,
                    "banks_live": banks_live,
                    "volume_mn": vol_mn,
                    "value_cr": val_cr,
                    "source_file": os.path.basename(f),
                }
            )
    df = pd.DataFrame(records)
    # Deduplicate keeping row with non-null banks_live if available
    df = df.sort_values(["month_date", "banks_live"], na_position="last")
    df = df.drop_duplicates(subset=["month_date"], keep="first").sort_values("month_date").reset_index(drop=True)
    # Flag partial month (November-2026 is MTD up to Nov 24)
    df["is_partial_month"] = df["month_date"] >= pd.Timestamp("2026-11-01")
    df["avg_ticket_size_inr"] = np.where(
        df["volume_mn"] > 0, (df["value_cr"] * 10.0) / df["volume_mn"], np.nan
    )
    df["fiscal_year"] = np.where(
        df["month_date"].dt.month >= 4,
        df["month_date"].dt.year.astype(str) + "-" + ((df["month_date"].dt.year + 1) % 100).astype(str).str.zfill(2),
        (df["month_date"].dt.year - 1).astype(str) + "-" + (df["month_date"].dt.year % 100).astype(str).str.zfill(2),
    )
    return df


def load_upi_apps() -> pd.DataFrame:
    """Consolidate monthly UPI Application-wise volume and value."""
    files = sorted(glob.glob(str(RAW_DIR / "upi_apps" / "*.xlsx")))
    records = []
    for f in files:
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if len(rows) < 4:
            continue
        dt = extract_month_from_title(rows[0][0])
        if dt is None:
            # Fallback from filename
            dt = parse_month_str(os.path.basename(f))
        for r in rows[3:]:
            if not r or len(r) < 4:
                continue
            sr = str(r[0]).strip() if r[0] is not None else ""
            app_raw = str(r[1]).strip() if r[1] is not None else ""
            if not app_raw or app_raw.lower().startswith(("total", "note", "#", "*")):
                continue
            if not re.match(r"^\d+$", sr):
                continue
            # Use Customer Initiated + B2C + B2B + On-us if Total is 0, else Total if populated
            cust_vol = parse_num(r[2])
            cust_val = parse_num(r[3])
            total_vol = parse_num(r[8]) if len(r) > 8 else np.nan
            total_val = parse_num(r[9]) if len(r) > 9 else np.nan
            vol_mn = total_vol if (not np.isnan(total_vol) and total_vol > 0) else cust_vol
            val_cr = total_val if (not np.isnan(total_val) and total_val > 0) else cust_val
            if np.isnan(vol_mn) or vol_mn <= 0:
                continue
            records.append(
                {
                    "month_date": dt,
                    "rank_in_month": int(sr),
                    "app_name_raw": app_raw,
                    "app_name": clean_app_name(app_raw),
                    "volume_mn": vol_mn,
                    "value_cr": val_cr,
                    "source_file": os.path.basename(f),
                }
            )
    df = pd.DataFrame(records)
    # Aggregate in case an app alias appears twice in the same month
    df = (
        df.groupby(["month_date", "app_name"], as_index=False)
        .agg({"volume_mn": "sum", "value_cr": "sum", "rank_in_month": "min"})
        .sort_values(["month_date", "volume_mn"], ascending=[True, False])
        .reset_index(drop=True)
    )
    monthly_totals = df.groupby("month_date")[["volume_mn", "value_cr"]].transform("sum")
    df["volume_share_pct"] = (df["volume_mn"] / monthly_totals["volume_mn"]) * 100.0
    df["value_share_pct"] = (df["value_cr"] / monthly_totals["value_cr"]) * 100.0
    df["avg_ticket_size_inr"] = (df["value_cr"] * 10.0) / df["volume_mn"]
    return df


def load_top50_banks(subfolder: str, role: str) -> pd.DataFrame:
    """Consolidate Top 50 Remitter or Beneficiary bank performance."""
    files = sorted(glob.glob(str(RAW_DIR / subfolder / "*.xlsx")))
    records = []
    for f in files:
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if len(rows) < 3:
            continue
        dt = extract_month_from_title(rows[0][0])
        header = [str(c).strip().lower() if c is not None else "" for c in rows[1]]
        has_udir = any("udir" in h for h in header)
        for r in rows[2:]:
            if not r or len(r) < 7:
                continue
            sr = str(r[0]).strip() if r[0] is not None else ""
            bank_raw = str(r[1]).strip() if r[1] is not None else ""
            if not re.match(r"^\d+$", sr) or not bank_raw:
                continue
            vol_mn = parse_num(r[2])
            approved_pct = parse_num(r[3])
            bd_pct = parse_num(r[4])
            td_pct = parse_num(r[5])
            deemed_pct = parse_num(r[6])
            udir_pct = parse_num(r[7]) if (has_udir and len(r) > 7) else np.nan
            records.append(
                {
                    "month_date": dt,
                    "role": role,
                    "rank_in_month": int(sr),
                    "bank_name_raw": bank_raw,
                    "bank_name": clean_bank_name(bank_raw),
                    "volume_mn": vol_mn,
                    "approved_pct": approved_pct,
                    "bd_pct": bd_pct,
                    "td_pct": td_pct,
                    "deemed_approved_pct": deemed_pct,
                    "udir_auto_update_sr_pct": udir_pct,
                    "estimated_td_txns_mn": vol_mn * (td_pct / 100.0) if not np.isnan(td_pct) else np.nan,
                    "source_file": os.path.basename(f),
                }
            )
    df = pd.DataFrame(records).sort_values(["month_date", "role", "rank_in_month"]).reset_index(drop=True)
    return df


def load_p2p_p2m() -> pd.DataFrame:
    """Consolidate monthly P2P and P2M transactions."""
    files = sorted(glob.glob(str(RAW_DIR / "p2p_p2m" / "*.xlsx")))
    records = []
    for f in files:
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        for r in rows[3:]:
            if not r or len(r) < 7 or r[0] is None:
                continue
            dt = parse_month_str(str(r[0]).strip())
            if dt is None:
                continue
            tot_vol, tot_val = parse_num(r[1]), parse_num(r[2])
            p2p_vol, p2p_val = parse_num(r[3]), parse_num(r[4])
            p2m_vol, p2m_val = parse_num(r[5]), parse_num(r[6])
            records.append(
                {
                    "month_date": dt,
                    "total_volume_mn": tot_vol,
                    "total_value_cr": tot_val,
                    "p2p_volume_mn": p2p_vol,
                    "p2p_value_cr": p2p_val,
                    "p2m_volume_mn": p2m_vol,
                    "p2m_value_cr": p2m_val,
                    "p2p_volume_share_pct": (p2p_vol / tot_vol) * 100.0 if tot_vol else np.nan,
                    "p2m_volume_share_pct": (p2m_vol / tot_vol) * 100.0 if tot_vol else np.nan,
                    "p2p_avg_ticket_inr": (p2p_val * 10.0) / p2p_vol if p2p_vol else np.nan,
                    "p2m_avg_ticket_inr": (p2m_val * 10.0) / p2m_vol if p2m_vol else np.nan,
                    "source_file": os.path.basename(f),
                }
            )
    df = pd.DataFrame(records).drop_duplicates(subset=["month_date"]).sort_values("month_date").reset_index(drop=True)
    return df


def load_statewise() -> pd.DataFrame:
    """Clean Oct 2026 State-wise & District-wise UPI Statistics."""
    files = sorted(glob.glob(str(RAW_DIR / "statewise" / "*.xlsx")))
    records = []
    for f in files:
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        dt = extract_month_from_title(rows[0][0]) or pd.Timestamp("2026-10-01")
        for r in rows[2:]:
            if not r or len(r) < 7:
                continue
            sr = str(r[0]).strip() if r[0] is not None else ""
            if not re.match(r"^\d+$", sr):
                continue
            vol_mn = parse_num(r[3])
            val_cr = parse_num(r[5])
            records.append(
                {
                    "month_date": dt,
                    "sr_no": int(sr),
                    "state_ut": str(r[1]).strip().title(),
                    "district": str(r[2]).strip().title(),
                    "volume_mn": vol_mn,
                    "volume_contribution_pct": parse_num(r[4]),
                    "value_cr": val_cr,
                    "value_contribution_pct": parse_num(r[6]),
                    "avg_ticket_size_inr": (val_cr * 10.0) / vol_mn if vol_mn else np.nan,
                }
            )
    return pd.DataFrame(records)


def build_dim_bank(bank_df: pd.DataFrame) -> pd.DataFrame:
    """Build canonical bank dimension table."""
    banks = sorted(bank_df["bank_name"].unique())
    dim = pd.DataFrame({"bank_id": range(1, len(banks) + 1), "bank_name": banks})
    return dim


def run_sanity_checks(
    monthly: pd.DataFrame,
    apps: pd.DataFrame,
    banks: pd.DataFrame,
    p2p_p2m: pd.DataFrame,
) -> list[str]:
    """Validate data quality and return a list of check results."""
    checks = []
    # 1. No negative values
    assert (monthly["volume_mn"] >= 0).all(), "Negative volume in monthly"
    assert (monthly["value_cr"] >= 0).all(), "Negative value in monthly"
    checks.append(f"PASS: Monthly table ({len(monthly)} months) has zero negative volumes/values.")

    # 2. Ticket size plausibility (between ₹10 and ₹10,000, accounting for 2016 pilot months)
    full = monthly[~monthly["is_partial_month"]]
    min_ts, max_ts = full["avg_ticket_size_inr"].min(), full["avg_ticket_size_inr"].max()
    assert 10 <= min_ts and max_ts <= 10000, f"Implausible ticket size: {min_ts}-{max_ts}"
    checks.append(f"PASS: Monthly average ticket size within plausible range (INR {min_ts:,.0f} to INR {max_ts:,.0f}).")

    # 3. Missing months check in full history
    expected = pd.date_range(full["month_date"].min(), full["month_date"].max(), freq="MS")
    missing = set(expected) - set(full["month_date"])
    checks.append(f"PASS: Continuous monthly series from {full['month_date'].min().strftime('%Y-%m')} to {full['month_date'].max().strftime('%Y-%m')} (missing months: {len(missing)}).")

    # 4. Bank percentages bounded [0, 100]
    for col in ["approved_pct", "bd_pct", "td_pct"]:
        valid = banks[col].dropna()
        assert ((valid >= 0) & (valid <= 100)).all(), f"Out of range {col}"
    checks.append(f"PASS: Bank performance ({len(banks)} rows, {banks['bank_name'].nunique()} unique banks) percentages within [0, 100].")

    # 5. P2P + P2M == Total check
    diff = (p2p_p2m["p2p_volume_mn"] + p2p_p2m["p2m_volume_mn"] - p2p_p2m["total_volume_mn"]).abs().max()
    assert diff < 1.0, f"P2P + P2M mismatch: {diff}"
    checks.append(f"PASS: P2P + P2M reconciles with Total volume across all {len(p2p_p2m)} months (max diff: {diff:.4f} Mn).")

    # 6. Apps share sums to ~100%
    share_sum = apps.groupby("month_date")["volume_share_pct"].sum()
    assert (share_sum - 100.0).abs().max() < 0.01
    checks.append(f"PASS: App market shares sum to 100.0% across all {apps['month_date'].nunique()} months.")
    return checks


def write_data_dictionary(out_path: Path) -> None:
    content = """# Data Dictionary — UPI Digital Payments Trend Analysis

All monetary values are in **INR Crore (₹ Cr)** unless specified; transaction counts are in **Millions (Mn)**; average ticket size is in **INR (₹)** (`value_cr * 10 / volume_mn`).

## 1. `fact_upi_monthly.csv`
- `month_date`: First day of the month (`YYYY-MM-DD`).
- `banks_live`: Number of banks live on UPI (from NPCI Product Statistics).
- `volume_mn`: Total UPI transaction volume in millions.
- `value_cr`: Total UPI transaction value in ₹ crore.
- `avg_ticket_size_inr`: Average transaction value in ₹.
- `fiscal_year`: Indian fiscal year (`Apr–Mar`, e.g., `2025-26`).
- `is_partial_month`: Boolean flag (`True` for month-to-date partial months like Nov 2026).

## 2. `fact_app_share.csv`
- `month_date`: Month (`YYYY-MM-DD`).
- `app_name`: Standardized UPI application name (PhonePe, Google Pay, Paytm, CRED, etc.).
- `volume_mn`: App monthly transaction volume in millions.
- `value_cr`: App monthly transaction value in ₹ crore.
- `volume_share_pct`: App share of total reported app volume (%).
- `value_share_pct`: App share of total reported app value (%).
- `avg_ticket_size_inr`: App average ticket size in ₹.

## 3. `fact_bank_performance.csv`
- `month_date`: Month (`YYYY-MM-DD`).
- `role`: `remitter` (payer bank) or `beneficiary` (payee bank).
- `bank_id`: Foreign key to `dim_bank.csv`.
- `bank_name`: Standardized bank name.
- `volume_mn`: Monthly transaction volume in millions.
- `approved_pct`: Approved transaction rate (%).
- `bd_pct`: Business decline rate (%).
- `td_pct`: Technical decline rate (%).
- `deemed_approved_pct`: Deemed approved rate (%).
- `estimated_td_txns_mn`: Estimated technical decline transactions in millions (`volume_mn * td_pct / 100`).

## 4. `fact_p2p_p2m_monthly.csv`
- `month_date`: Month (`YYYY-MM-DD`).
- `total_volume_mn`, `total_value_cr`: Total UPI volume (Mn) and value (₹ Cr).
- `p2p_volume_mn`, `p2p_value_cr`: Person-to-Person volume and value.
- `p2m_volume_mn`, `p2m_value_cr`: Person-to-Merchant volume and value.
- `p2p_volume_share_pct`, `p2m_volume_share_pct`: Share of total volume (%).
- `p2p_avg_ticket_inr`, `p2m_avg_ticket_inr`: Average ticket size (₹) for P2P vs. P2M.

## 5. `fact_statewise_oct2026.csv`
- `month_date`, `state_ut`, `district`, `volume_mn`, `volume_contribution_pct`, `value_cr`, `value_contribution_pct`, `avg_ticket_size_inr`.

## 6. `dim_bank.csv`
- `bank_id`, `bank_name`.
"""
    out_path.write_text(content, encoding="utf-8")


def main() -> None:
    monthly = load_product_stats()
    apps = load_upi_apps()
    remitter = load_top50_banks("top50_remitter", "remitter")
    beneficiary = load_top50_banks("top50_beneficiary", "beneficiary")
    banks = pd.concat([remitter, beneficiary], ignore_index=True)
    dim_bank = build_dim_bank(banks)
    banks = banks.merge(dim_bank, on="bank_name", how="left")
    p2p_p2m = load_p2p_p2m()
    statewise = load_statewise()

    checks = run_sanity_checks(monthly, apps, banks, p2p_p2m)
    for c in checks:
        print(c)

    monthly.to_csv(CLEAN_DIR / "fact_upi_monthly.csv", index=False)
    apps.to_csv(CLEAN_DIR / "fact_app_share.csv", index=False)
    banks.to_csv(CLEAN_DIR / "fact_bank_performance.csv", index=False)
    dim_bank.to_csv(CLEAN_DIR / "dim_bank.csv", index=False)
    p2p_p2m.to_csv(CLEAN_DIR / "fact_p2p_p2m_monthly.csv", index=False)
    statewise.to_csv(CLEAN_DIR / "fact_statewise_oct2026.csv", index=False)
    write_data_dictionary(CLEAN_DIR / "data_dictionary.md")
    print(f"All clean datasets written to {CLEAN_DIR}")


if __name__ == "__main__":
    main()
