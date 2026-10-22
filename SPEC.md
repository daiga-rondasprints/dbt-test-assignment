# Retail analytics modeling specification

## Grain and model flow

- `stg_consolidated_transactions` is a **persisted DuckDB table** rebuilt from the
  complete immutable CSV on each `dbt build`. dbt's table materialization replaces
  the existing relation rather than appending to it: a repeat build yields the same
  509,480 source rows. A unique content fingerprint and source-count equality test
  guard against duplicate/missing landing rows. This is a reproducible full reload,
  not an incremental CDC ingestion service.
- `int_transaction_versions` preserves every staged source row with a ranked
  `selected_for_fact` / `triage_duplicate_version` disposition.
- `int_sales_transactions` selects one record per `transaction_id`; transaction date,
  quantity, selling price, product/store keys, pack size, and landed cost are identical
  across each observed ID collision. Source standard/unit costs and lineage can differ.
- `dim_date`, `dim_product` and `dim_store` hold 1,461 calendar days, 16 known products
  plus Unknown, and 287 known stores plus Unknown, respectively. The fact grain is one
  selected transaction ID, with signed quantity and date/product/store keys.
- `mart_annual_sales`, `mart_monthly_sales`, `mart_product_performance`,
  `mart_store_performance`, `mart_region_performance`, and `mart_team_kpi_scorecard`
  are derived from the fact and dimensions, not from the CSV. These are aggregated
  reporting marts, not additional atomic or periodic-snapshot facts.

## Hierarchies, calendar, and pack size

- **Product rollup:** `product_category` -> `product_key` / catalog product name.
  There is no subcategory or brand field. The 16 known product keys represent 17
  catalog labels because one source key has conflicting names; the dimension chooses
  its modal profile. `pack_size` is a packaging attribute, not another product
  hierarchy level. Each known product has exactly one observed pack size (1 or 2) in
  this extract.
- **Store rollup:** Census region -> state -> `store_key` / store name. `store_type`
  (nine values) is a slice/filter, not part of this geographic hierarchy. Store name
  alone is not unique, so aggregate by store key. The 287 known stores contain 286
  with positive reported area; Louisville (store 200) has `store_sqft = 0` and is
  excluded from per-area denominators, but its sales remain in all unfiltered
  company totals.
- **Date dimension:** 1,461 days from 2019-01-01 to 2022-12-31 support year, quarter,
  month, and day filters. The extract's 499,665 selected events all occur on the
  first day of a month (48 distinct dates). These look like monthly snapshots of
  transaction activity, but the rows are still transaction events; do not infer
  daily activity or inventory balances.
- **Quantity interpretation:** retain source `quantity` as reported for global sales
  (`quantity * unit_price`). A separate `quantity / pack_size` pack-equivalent measure
  is exposed only under the assumption that quantity counts eaches. Standard-cost
  gross profit divides standard cost by pack size based on the observed cost ratio;
  Finance also gets the unadjusted standard-cost scenario and landed-cost sensitivity.
  Do not promote one pack interpretation as accounting truth until upstream confirms
  quantity, price, and all cost grains.

## Decisions and evidence

- **Duplicate IDs:** 9,815 transaction IDs each have two source rows (19,630 rows total;
  9,815 excess rows). The newer `ingested_at` version is selected into the fact and the
  older version is moved to `mart_data_quality_triage` (one triage row per collision). For all such pairs the observed sales payload (date, quantity,
  price, pack size, product, store, landed cost) matches; unit/standard costs and
  ingestion/source metadata are the fields that can differ.
  Keep the latest `ingested_at`, as Sales Ops proposes. Ties prefer POS, then ERP, then
  Manual, then higher standard and unit costs. `duplicate_source_row_count` preserves
  collision visibility. Rejected: summing all versions (double counts sales) and
  deduplicating on transaction ID without checking economics.
- **Economic versus lineage time:** `transaction_date` drives all reporting; `ingested_at`
  is only a version-selection and audit field.
- **Unknown keys:** missing IDs and source placeholder `99901` map to dimension key `-1`.
  Rows remain in net sales and reporting; they are not discarded or mistaken for a real
  product/store.
- **Conflicting attributes:** choose the most frequent observed attribute profile for
  products and stores, with a deterministic lexical tie-break. Store region is derived
  from state code using US Census regions when available. This resolves the Maryland
  store labelled Northeast/South inconsistently as South. Store attributes are not
  summed across fact rows.
- **Cost grain:** for pack size 2, standard cost is almost exactly 2x landed unit cost
  (99% of observed ratios are within 1% of 2.0); for pack size 1, the amounts are
  approximately equal. Treat standard cost as pack-level where pack size indicates
  multiple units and divide by pack size before extending quantity. This is an evidence-
  based assumption pending confirmation from Finance/AP. Finance's standard cost is the
  primary gross-profit basis; landed unit cost remains an alternate actual-cost view.
- **Returns:** retain negative quantity and its negative sales/cost impact; report the
  number of negative-quantity lines. No attempt is made to infer return reason.
- **Profit language:** net sales are signed quantity times unit price. Gross profit is
  net sales less standard cost of sales (only on standard-cost-covered rows); gross
  margin is that gross profit divided by the matching standard-costed net sales. Landed
  gross profit/margin use landed unit cost as a separate sensitivity. Neither is net
  profit; taxes, central costs, and full operating expenses are absent.
- **Store opex period (FP&A vs Store Finance):** `direct_store_operating_costs` is read
  as **annual**. Evidence: read as annual it totals $3.35m in 2022 (26% of net sales,
  66% of gross profit); read as monthly (x12) it would be $40m, eight times gross profit,
  and only 4 of 287 stores would cover it. The monthly reading is kept only as a
  labelled sensitivity (`gross_profit_less_direct_cost_monthly_scenario`).

## Known limits to investigate

- Verify the pack-level interpretation of standard cost and the effective date of cost
  changes, particularly the 2022 divergence between standard and landed cost.
- Reconcile the product-name/catalog conflict and store 50's restated operating cost.
- Have Store Finance confirm the annual reading of direct store operating cost; the
  model would need only a config change if it is monthly.
- Resolve source unknown IDs and review negative-quantity adjustments and returns.
- Confirm whether transaction quantity is packs or individual items and the exact
  grains of unit price, standard cost, and landed cost before promoting physical-unit
  KPIs or changing the global sales/cost formula.
