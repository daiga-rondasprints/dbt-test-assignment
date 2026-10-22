# Proposed upstream transaction-data contract

This contract is a target for the source team, not a claim that the current CSV
already complies. Keep the raw landing file immutable; validate it and publish
row/entity-level exceptions to `mart_data_quality_triage` for review.

## Required event fields

| Field | Contract |
|---|---|
| `transaction_id` | Non-null business event identifier. If one transaction can contain multiple product lines, provide a stable `transaction_line_id`; do not reuse a header ID as a line key. |
| `transaction_date` | Valid economic date in ISO `YYYY-MM-DD`, with timezone/date semantics documented. Do not substitute ingestion time. |
| `quantity` | Signed integer in the declared selling-unit grain. Negative values require a return/adjustment reason and, where possible, the original transaction reference. |
| `unit_price` | Non-negative decimal in an explicitly declared currency and selling-unit grain. State whether discounts/tax are included. |
| `product_id`, `store_id` | Non-null references to governed entities. Use an explicit, documented unknown code only when genuinely unavailable; do not use null and `99901` interchangeably. |
| `pack_size` | Positive integer. Define whether quantity/price are per each or per pack and how every cost field relates to that unit. |
| `standard_unit_cost`, `landed_unit_cost`, `unit_cost` | Decimal, currency and effective date required. Name and document each measure's grain (each vs pack), scope, and accounting meaning; do not send competing unlabeled bases. |
| `source_system`, `ingested_at` | Required lineage. `ingested_at` is a UTC timestamp and never replaces economic date. |

## Entity attributes and revisions

- Product/store names, categories, state and region should come from governed
  entity records rather than drift on each transaction row.
- If attributes are historically effective, provide `valid_from` and exclusive
  `valid_to` dates with a non-overlapping interval per key. Until then, consumers
  should not infer slowly changing history from conflicting repeated values.
- Region should be derived from a validated state/location mapping or supplied
  consistently. Store operating cost must include currency and explicit period
  (monthly/annual), effective dates, and whether it is fully loaded.

## Delivery and quality gates

- Deliver idempotently with a stable event/line key and an explicit upsert or
  correction policy. A repeated key is a version only when its event payload is
  unchanged; changed economic fields must be identified as corrections or new lines.
- Publish schema/version changes before rollout. Reject malformed types, impossible
  dates, non-positive pack size, missing event IDs, and invalid price/cost values
  with an accountable source owner and reason.
- Track duplicate/version counts, missing or unknown keys, cost coverage, attribute
  conflicts, and negative-quantity rates. Do not silently discard exceptions.
- Preserve both source and ingestion timestamps, and retain enough lineage to trace
  every exception to a delivered file/record. The current source has no explicit
  line ID; a content hash is only a temporary locator, not a substitute.

## Current handling

The dbt project retains source rows in staging, selects one version for the event
fact, maps unknown keys to explicit dimension members, preserves returns, and
materializes the current exception set for triage. The triage model is rebuilt from
source data and must not be edited to record dispositions; use a governed ticket or
append-only issue workflow for durable ownership/status.
