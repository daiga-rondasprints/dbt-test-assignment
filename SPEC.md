# Retail analytics modeling specification

## Grain and model flow

- `stg_consolidated_transactions` is a typed, row-preserving view of the landing CSV.
- `int_sales_transactions` selects one record per `transaction_id`; transaction date,
  quantity, selling price, product/store keys, pack size, and landed cost are identical
  across each observed ID collision. Source standard/unit costs and lineage can differ.
- `dim_product` and `dim_store` hold one row per source key plus an explicit `-1` Unknown
  member. The fact grain is one selected transaction ID, with a signed quantity and FKs.
- `mart_annual_sales`, `mart_monthly_sales`, `mart_product_performance`,
  `mart_store_performance`, and `mart_region_performance` are derived from the fact and
  dimensions, not from the CSV.

## Decisions and evidence

- **Duplicate IDs:** 9,815 transaction IDs each have two source rows (19,630 rows total;
  9,815 excess rows). For all such pairs the observed sales payload (date, quantity,
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
  gross profit/margin use landed unit cost as a separate sensitivity. Opex timing is
  ambiguous, so store marts show annual and monthly direct-cost scenarios separately.
  Neither is net profit; taxes, central costs, and full operating expenses are absent.

## Known limits to investigate

- Verify the pack-level interpretation of standard cost and the effective date of cost
  changes, particularly the 2022 divergence between standard and landed cost.
- Reconcile the product-name/catalog conflict and store 50's restated operating cost.
- Confirm whether direct store operating cost is annual or monthly before using the
  contribution scenarios for budgeting.
- Resolve source unknown IDs and review negative-quantity adjustments and returns.
