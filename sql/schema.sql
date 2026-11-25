-- PostgreSQL / Neon Warehouse Schema for UPI Digital Payments Trend Analysis

CREATE TABLE IF NOT EXISTS dim_bank (
    bank_id INTEGER PRIMARY KEY,
    bank_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_upi_monthly (
    month_date DATE PRIMARY KEY,
    banks_live INTEGER,
    volume_mn NUMERIC(14, 4) NOT NULL CHECK (volume_mn >= 0),
    value_cr NUMERIC(16, 4) NOT NULL CHECK (value_cr >= 0),
    avg_ticket_size_inr NUMERIC(12, 2),
    fiscal_year VARCHAR(10) NOT NULL,
    is_partial_month BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS fact_app_share (
    month_date DATE NOT NULL,
    app_name TEXT NOT NULL,
    volume_mn NUMERIC(14, 4) NOT NULL CHECK (volume_mn >= 0),
    value_cr NUMERIC(16, 4) NOT NULL CHECK (value_cr >= 0),
    rank_in_month INTEGER,
    volume_share_pct NUMERIC(8, 4),
    value_share_pct NUMERIC(8, 4),
    avg_ticket_size_inr NUMERIC(12, 2),
    PRIMARY KEY (month_date, app_name)
);

CREATE TABLE IF NOT EXISTS fact_bank_performance (
    month_date DATE NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('remitter', 'beneficiary')),
    bank_id INTEGER NOT NULL REFERENCES dim_bank(bank_id),
    rank_in_month INTEGER,
    volume_mn NUMERIC(14, 4) NOT NULL CHECK (volume_mn >= 0),
    approved_pct NUMERIC(6, 2),
    bd_pct NUMERIC(6, 2),
    td_pct NUMERIC(6, 2),
    deemed_approved_pct NUMERIC(6, 2),
    udir_auto_update_sr_pct NUMERIC(6, 2),
    estimated_td_txns_mn NUMERIC(14, 4),
    PRIMARY KEY (month_date, role, bank_id)
);

CREATE TABLE IF NOT EXISTS fact_p2p_p2m_monthly (
    month_date DATE PRIMARY KEY,
    total_volume_mn NUMERIC(14, 4),
    total_value_cr NUMERIC(16, 4),
    p2p_volume_mn NUMERIC(14, 4),
    p2p_value_cr NUMERIC(16, 4),
    p2m_volume_mn NUMERIC(14, 4),
    p2m_value_cr NUMERIC(16, 4),
    p2p_volume_share_pct NUMERIC(8, 4),
    p2m_volume_share_pct NUMERIC(8, 4),
    p2p_avg_ticket_inr NUMERIC(12, 2),
    p2m_avg_ticket_inr NUMERIC(12, 2)
);

CREATE TABLE IF NOT EXISTS fact_statewise_oct2026 (
    month_date DATE NOT NULL,
    sr_no INTEGER,
    state_ut TEXT NOT NULL,
    district TEXT NOT NULL,
    volume_mn NUMERIC(14, 4),
    volume_contribution_pct NUMERIC(8, 4),
    value_cr NUMERIC(16, 4),
    value_contribution_pct NUMERIC(8, 4),
    avg_ticket_size_inr NUMERIC(12, 2),
    PRIMARY KEY (month_date, state_ut, district)
);

CREATE INDEX IF NOT EXISTS idx_app_share_month ON fact_app_share(month_date);
CREATE INDEX IF NOT EXISTS idx_bank_perf_month_role ON fact_bank_performance(month_date, role);
