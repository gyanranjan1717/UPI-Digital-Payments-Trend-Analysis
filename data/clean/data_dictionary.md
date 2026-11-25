# Data Dictionary — UPI Digital Payments Trend Analysis

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
