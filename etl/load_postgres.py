"""
Load cleaned UPI CSV datasets into PostgreSQL / Neon.

Usage:
    Set DATABASE_URL in environment or .env file:
    DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
    python etl/load_postgres.py
"""

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = BASE_DIR / "data" / "clean"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    env_file = BASE_DIR / ".env"
    if not url and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not url:
        raise RuntimeError(
            "DATABASE_URL not found. Set it as an environment variable or in .env"
        )
    return url


def main() -> None:
    engine = create_engine(get_database_url())
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_PATH.read_text(encoding="utf-8")))

    tables = [
        ("dim_bank", "dim_bank.csv", ["bank_id", "bank_name"]),
        (
            "fact_upi_monthly",
            "fact_upi_monthly.csv",
            [
                "month_date",
                "banks_live",
                "volume_mn",
                "value_cr",
                "avg_ticket_size_inr",
                "fiscal_year",
                "is_partial_month",
            ],
        ),
        (
            "fact_app_share",
            "fact_app_share.csv",
            [
                "month_date",
                "app_name",
                "volume_mn",
                "value_cr",
                "rank_in_month",
                "volume_share_pct",
                "value_share_pct",
                "avg_ticket_size_inr",
            ],
        ),
        (
            "fact_bank_performance",
            "fact_bank_performance.csv",
            [
                "month_date",
                "role",
                "bank_id",
                "rank_in_month",
                "volume_mn",
                "approved_pct",
                "bd_pct",
                "td_pct",
                "deemed_approved_pct",
                "udir_auto_update_sr_pct",
                "estimated_td_txns_mn",
            ],
        ),
        (
            "fact_p2p_p2m_monthly",
            "fact_p2p_p2m_monthly.csv",
            [
                "month_date",
                "total_volume_mn",
                "total_value_cr",
                "p2p_volume_mn",
                "p2p_value_cr",
                "p2m_volume_mn",
                "p2m_value_cr",
                "p2p_volume_share_pct",
                "p2m_volume_share_pct",
                "p2p_avg_ticket_inr",
                "p2m_avg_ticket_inr",
            ],
        ),
        (
            "fact_statewise_oct2026",
            "fact_statewise_oct2026.csv",
            [
                "month_date",
                "sr_no",
                "state_ut",
                "district",
                "volume_mn",
                "volume_contribution_pct",
                "value_cr",
                "value_contribution_pct",
                "avg_ticket_size_inr",
            ],
        ),
    ]

    with engine.begin() as conn:
        for tbl in reversed([t[0] for t in tables]):
            conn.execute(text(f"TRUNCATE TABLE {tbl} CASCADE;"))

    for tbl, fname, cols in tables:
        df = pd.read_csv(CLEAN_DIR / fname)[cols]
        df.to_sql(tbl, engine, if_exists="append", index=False, method="multi")
        print(f"Loaded {len(df)} rows into {tbl}")


if __name__ == "__main__":
    main()
