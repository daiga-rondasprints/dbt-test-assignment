#!/usr/bin/env python3
"""Export presentation inputs from built dbt marts, never from the landing CSV."""

import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "retail.duckdb"
OUTPUT = ROOT / "target" / "presentation_metrics.json"


def rows_as_dicts(connection, sql):
    cursor = connection.execute(sql)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def main():
    connection = duckdb.connect(str(DATABASE), read_only=True)
    tables = {
        row[0]: row[1]
        for row in connection.execute(
            """
            select table_name, table_schema
            from information_schema.tables
            where table_name in (
                'stg_consolidated_transactions',
                'dim_product',
                'dim_store',
                'fct_sales',
                'mart_annual_sales',
                'mart_product_performance',
                'mart_region_performance',
                'mart_store_performance',
                'mart_data_quality_triage'
            )
            """
        ).fetchall()
    }

    required = {
        "stg_consolidated_transactions",
        "dim_product",
        "dim_store",
        "fct_sales",
        "mart_annual_sales",
        "mart_product_performance",
        "mart_region_performance",
        "mart_store_performance",
        "mart_data_quality_triage",
    }
    missing = required - tables.keys()
    if missing:
        raise RuntimeError(
            "Missing built dbt relations: "
            + ", ".join(sorted(missing))
            + ". Run `uv run dbt build` first."
        )

    def relation(name):
        return f'"{tables[name]}"."{name}"'

    annual = rows_as_dicts(
        connection,
        f"""
        select
            year,
            net_sales,
            net_sales_yoy_change,
            net_sales_yoy_pct,
            net_units_sold,
            average_selling_price,
            gross_profit,
            gross_margin_pct,
            landed_gross_profit,
            landed_gross_margin_pct,
            gross_profit_yoy_change,
            gross_profit_yoy_pct,
            transaction_count,
            return_or_adjustment_count,
            standard_cost_coverage_pct
        from {relation('mart_annual_sales')}
        order by year
        """,
    )
    current = next(row for row in annual if row["year"] == 2022)
    previous = next(row for row in annual if row["year"] == 2021)
    volume_effect = (
        current["net_units_sold"] - previous["net_units_sold"]
    ) * previous["average_selling_price"]
    price_mix_effect = current["net_units_sold"] * (
        current["average_selling_price"] - previous["average_selling_price"]
    )

    result = {
        "source_rows": connection.execute(
            f"select count(*) from {relation('stg_consolidated_transactions')}"
        ).fetchone()[0],
        "fact_rows": connection.execute(
            f"select count(*) from {relation('fct_sales')}"
        ).fetchone()[0],
        "product_dimension_rows": connection.execute(
            f"select count(*) from {relation('dim_product')} where not is_unknown"
        ).fetchone()[0],
        "store_dimension_rows": connection.execute(
            f"select count(*) from {relation('dim_store')} where not is_unknown"
        ).fetchone()[0],
        "deduplicated_transaction_ids": connection.execute(
            f"""
            select count(*) from {relation('fct_sales')}
            where duplicate_source_row_count > 1
            """
        ).fetchone()[0],
        "annual": annual,
        "growth_decomposition": {
            "volume_effect": volume_effect,
            "price_mix_effect": price_mix_effect,
        },
        "products_2022": rows_as_dicts(
            connection,
            f"""
            select
                product_name,
                product_category,
                net_sales,
                net_sales_yoy_change,
                net_sales_yoy_pct,
                gross_profit,
                gross_margin_pct
            from {relation('mart_product_performance')}
            where year = 2022 and product_key != -1
            order by net_sales_yoy_change desc
            """,
        ),
        "low_margin_products_2022": rows_as_dicts(
            connection,
            f"""
            select product_name, net_sales, gross_profit, gross_margin_pct
            from {relation('mart_product_performance')}
            where year = 2022 and product_key != -1 and net_sales >= 250000
            order by gross_margin_pct
            limit 5
            """,
        ),
        "regions_2022": rows_as_dicts(
            connection,
            f"""
            select
                region_name,
                net_sales,
                net_sales_yoy_change,
                net_sales_yoy_pct,
                gross_profit,
                gross_margin_pct
            from {relation('mart_region_performance')}
            where year = 2022
            order by net_sales_yoy_change desc
            """,
        ),
        "stores_2022": rows_as_dicts(
            connection,
            f"""
            select store_name, region_name, net_sales, net_sales_yoy_change,
                   gross_profit, gross_margin_pct
            from {relation('mart_store_performance')}
            where year = 2022 and store_key != -1
            order by net_sales desc
            limit 5
            """,
        ),
        "triage_counts": rows_as_dicts(
            connection,
            f"""
            select issue_code, severity, count(*) as row_count
            from {relation('mart_data_quality_triage')}
            group by issue_code, severity
            order by issue_code
            """,
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    connection.close()
    print(f"Exported mart-based metrics to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
