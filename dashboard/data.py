"""Read-only access to the built dbt relations in retail.duckdb. Nothing here touches the CSV."""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.getenv("DUCKDB_PATH", ROOT / "retail.duckdb"))

STG = "main_staging.stg_consolidated_transactions"
VERSIONS = "main_intermediate.int_transaction_versions"
FACT = "main_marts.fct_sales"
DIM_PRODUCT = "main_marts.dim_product"
DIM_STORE = "main_marts.dim_store"
DIM_DATE = "main_marts.dim_date"
TRIAGE = "main_marts.mart_data_quality_triage"

# Shared, per-event cut: the single source for every cross-dimensional chart in the app.
EVENTS = f"""
    select
        f.transaction_id, f.transaction_date, d.calendar_year as year, d.month_number, d.month_name, d.month_start,
        p.product_key, p.product_name, p.product_category, p.pack_size,
        s.store_key, s.store_name, s.state_code, s.state, s.region_name, s.store_type, s.store_sqft,
        f.quantity, f.net_sales, f.standard_cost_of_sales, f.gross_profit,
        case when f.gross_profit is not null then f.net_sales end as costed_net_sales,
        f.is_return_or_adjustment
    from {FACT} f
    join {DIM_DATE} d on f.date_key = d.date_key
    join {DIM_PRODUCT} p on f.product_key = p.product_key
    join {DIM_STORE} s on f.store_key = s.store_key
"""


def query(sql: str) -> pd.DataFrame:
    with duckdb.connect(str(DB), read_only=True) as con:
        return con.execute(sql).df()


def scalar(sql: str):
    with duckdb.connect(str(DB), read_only=True) as con:
        return con.execute(sql).fetchone()[0]


def row_flow() -> dict:
    return {
        "source_rows": scalar(f"select count(*) from {STG}"),
        "staging_rows": scalar(f"select count(*) from {STG}"),
        "distinct_fingerprints": scalar(f"select count(distinct source_row_fingerprint) from {STG}"),
        "version_rows": scalar(f"select count(*) from {VERSIONS}"),
        "selected": scalar(f"select count(*) from {VERSIONS} where version_disposition = 'selected_for_fact'"),
        "excluded_versions": scalar(f"select count(*) from {VERSIONS} where version_disposition = 'triage_duplicate_version'"),
        "fact_rows": scalar(f"select count(*) from {FACT}"),
        "colliding_ids": scalar(f"select count(*) from {FACT} where duplicate_source_row_count > 1"),
        "triage_rows": scalar(f"select count(*) from {TRIAGE}"),
        "triage_fingerprints": scalar(f"select count(distinct source_row_fingerprint) from {TRIAGE}"),
        "dim_product": scalar(f"select count(*) from {DIM_PRODUCT}"),
        "dim_product_known": scalar(f"select count(*) from {DIM_PRODUCT} where not is_unknown"),
        "dim_store": scalar(f"select count(*) from {DIM_STORE}"),
        "dim_store_known": scalar(f"select count(*) from {DIM_STORE} where not is_unknown"),
        "dim_date": scalar(f"select count(*) from {DIM_DATE}"),
        "date_min": scalar(f"select min(date_day) from {DIM_DATE}"),
        "date_max": scalar(f"select max(date_day) from {DIM_DATE}"),
        "event_dates": scalar(f"select count(distinct transaction_date) from {FACT}"),
        "first_of_month_only": scalar(f"select bool_and(extract(day from transaction_date) = 1) from {FACT}"),
    }


def triage_counts() -> pd.DataFrame:
    return query(f"""
        select issue_code, severity, count(*) as rows, count(distinct source_row_fingerprint) as source_rows
        from {TRIAGE} group by 1, 2 order by rows desc
    """)


def product_name_conflict() -> pd.DataFrame:
    return query(f"""
        select product_id, product_name_catalog, product_effective_from, product_effective_to,
               min(transaction_date) as first_seen, max(transaction_date) as last_seen, count(*) as rows
        from {STG} where product_id = 19 group by 1, 2, 3, 4 order by 2
    """)


def annual() -> pd.DataFrame:
    return query("select * from main_marts.mart_annual_sales order by year")


def monthly() -> pd.DataFrame:
    return query("select * from main_marts.mart_monthly_sales order by month_start")


def product_year() -> pd.DataFrame:
    return query("select * from main_marts.mart_product_performance where product_key <> -1 order by product_name, year")


def store_year() -> pd.DataFrame:
    return query("select * from main_marts.mart_store_performance where store_key <> -1 order by store_name, year")


def events() -> pd.DataFrame:
    return query(EVENTS)


def scorecard() -> pd.DataFrame:
    return query("select * from main_marts.mart_team_kpi_scorecard order by year, team_view, metric_code")
