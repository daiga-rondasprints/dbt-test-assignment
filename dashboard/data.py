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
        f.quantity, f.net_sales, f.standard_cost_of_sales, f.gross_profit, f.landed_gross_profit, f.landed_cost_of_sales,
        f.standard_unit_cost, f.landed_unit_cost,
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
        "store_names": scalar(f"select count(distinct store_name) from {DIM_STORE} where not is_unknown"),
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
        select product_id, product_name_catalog, cast(product_effective_from as date) as product_effective_from,
               cast(product_effective_to as date) as product_effective_to,
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


def dbt_inventory() -> dict:
    """Models, tests and last run status from dbt's own artifacts (target/manifest.json, run_results.json)."""
    import json
    from collections import Counter

    out = {"models": 0, "layers": {}, "tests": 0, "test_types": {}, "singular": 0, "packages": [], "sources": 0,
           "dbt_version": "", "adapter": "", "last_run_pass": None, "last_run_total": None}
    manifest = ROOT / "target" / "manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text())
        nodes = m["nodes"].values()
        models = [n for n in nodes if n["resource_type"] == "model"]
        tests = [n for n in nodes if n["resource_type"] == "test"]
        out["models"] = len(models)
        out["layers"] = dict(Counter(n["path"].split("/")[0] for n in models))
        out["tests"] = len(tests)
        types = Counter()
        for t in tests:
            meta = t.get("test_metadata")
            types[meta["name"] if meta else "singular SQL"] += 1
        out["test_types"] = dict(types)
        out["singular"] = types.get("singular SQL", 0)
        out["packages"] = sorted({t["package_name"] for t in tests})
        out["sources"] = sum(1 for n in m.get("sources", {}).values())
        out["dbt_version"] = m["metadata"].get("dbt_version", "")
        out["adapter"] = m["metadata"].get("adapter_type", "")
    results = ROOT / "target" / "run_results.json"
    if results.exists():
        r = json.loads(results.read_text())["results"]
        out["last_run_total"] = len(r)
        out["last_run_pass"] = sum(1 for x in r if x["status"] in ("pass", "success"))
    return out


def icon_svg(name: str, color: str = "#212529", size: int = 30) -> str:
    """Inline SVG for a Simple Icons glyph stored under dashboard/assets/icons (CC0)."""
    path = Path(__file__).resolve().parent / "assets" / "icons" / f"{name}.svg"
    if not path.exists():
        return ""
    svg = path.read_text().strip()
    return svg.replace("<svg ", f'<svg fill="{color}" width="{size}" height="{size}" style="vertical-align:middle" ', 1)
