-- Analytical SQL Queries (PostgreSQL / Neon)
-- Demonstrates Window Functions: LAG, Rolling Averages, RANK, DENSE_RANK, and HHI

-- 1. Monthly Volume & Value Growth (MoM, YoY, and 3-Month Rolling Average)
WITH full_months AS (
    SELECT
        month_date,
        volume_mn,
        value_cr,
        avg_ticket_size_inr
    FROM fact_upi_monthly
    WHERE NOT is_partial_month
)
SELECT
    month_date,
    ROUND(volume_mn, 2) AS volume_mn,
    ROUND(value_cr, 2) AS value_cr,
    ROUND(avg_ticket_size_inr, 2) AS avg_ticket_size_inr,
    ROUND(
        100.0 * (volume_mn - LAG(volume_mn, 1) OVER (ORDER BY month_date))
        / NULLIF(LAG(volume_mn, 1) OVER (ORDER BY month_date), 0),
        2
    ) AS mom_volume_growth_pct,
    ROUND(
        100.0 * (volume_mn - LAG(volume_mn, 12) OVER (ORDER BY month_date))
        / NULLIF(LAG(volume_mn, 12) OVER (ORDER BY month_date), 0),
        2
    ) AS yoy_volume_growth_pct,
    ROUND(
        AVG(volume_mn) OVER (
            ORDER BY month_date
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_3m_avg_volume_mn
FROM full_months
ORDER BY month_date DESC
LIMIT 24;


-- 2. App Market Concentration (Top-2 Share & Herfindahl-Hirschman Index)
WITH ranked_apps AS (
    SELECT
        month_date,
        app_name,
        volume_share_pct,
        ROW_NUMBER() OVER (PARTITION BY month_date ORDER BY volume_share_pct DESC) AS app_rank
    FROM fact_app_share
)
SELECT
    month_date,
    ROUND(SUM(POWER(volume_share_pct, 2)), 1) AS hhi_volume,
    ROUND(SUM(CASE WHEN app_rank <= 2 THEN volume_share_pct ELSE 0 END), 2) AS top2_share_pct,
    ROUND(SUM(CASE WHEN app_rank <= 3 THEN volume_share_pct ELSE 0 END), 2) AS top3_share_pct
FROM ranked_apps
GROUP BY month_date
ORDER BY month_date;


-- 3. Bank Reliability Hotspots (Latest Month Remitter Technical Decline Ranking & Volume-Weighted Impact)
WITH latest_month AS (
    SELECT MAX(month_date) AS max_dt FROM fact_bank_performance
)
SELECT
    b.bank_name,
    f.role,
    ROUND(f.volume_mn, 2) AS volume_mn,
    f.td_pct,
    f.bd_pct,
    f.approved_pct,
    ROUND(f.estimated_td_txns_mn, 3) AS estimated_td_txns_mn,
    RANK() OVER (PARTITION BY f.role ORDER BY f.td_pct DESC) AS td_rate_rank,
    RANK() OVER (PARTITION BY f.role ORDER BY f.estimated_td_txns_mn DESC) AS td_impact_rank
FROM fact_bank_performance f
JOIN dim_bank b ON f.bank_id = b.bank_id
JOIN latest_month lm ON f.month_date = lm.max_dt
WHERE f.role = 'remitter'
  AND f.volume_mn >= 50
ORDER BY f.td_pct DESC
LIMIT 15;


-- 4. P2P vs P2M Structural Shift (12-Month Trend)
SELECT
    month_date,
    ROUND(p2p_volume_share_pct, 2) AS p2p_vol_share_pct,
    ROUND(p2m_volume_share_pct, 2) AS p2m_vol_share_pct,
    ROUND(p2p_avg_ticket_inr, 2) AS p2p_ticket_inr,
    ROUND(p2m_avg_ticket_inr, 2) AS p2m_ticket_inr
FROM fact_p2p_p2m_monthly
ORDER BY month_date;


-- 5. Top 10 States by UPI Volume (Oct 2026)
SELECT
    state_ut,
    COUNT(DISTINCT district) AS num_districts,
    ROUND(SUM(volume_mn), 2) AS total_volume_mn,
    ROUND(SUM(value_cr), 2) AS total_value_cr,
    ROUND((SUM(value_cr) * 10.0) / NULLIF(SUM(volume_mn), 0), 2) AS avg_ticket_size_inr
FROM fact_statewise_oct2026
GROUP BY state_ut
ORDER BY total_volume_mn DESC
LIMIT 10;
