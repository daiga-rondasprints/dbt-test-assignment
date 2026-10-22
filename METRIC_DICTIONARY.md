# Shared KPI definitions and team views

## Global formulae (the single company-wide source of truth)

Use the same signed events, calendar, currency, and cost coverage in every team
view. Team tabs are filters over shared metrics, not alternative formulae chosen
to flatter an individual function.

| Metric | Global formula | Notes |
|---|---|---|
| Net sales (the extract's revenue proxy) | `sum(quantity * unit_price)` | Signed returns included; taxes/discount decomposition and currency are not supplied. |
| Standard cost of sales | `sum(quantity * standard_unit_cost / pack_size)` when standard cost exists | Pack-level standard cost is an evidence-based assumption; confirm price, quantity, and cost grains with Finance/AP. |
| Gross profit (standard) | `net sales - standard cost of sales` for cost-covered events | Pre-operating expense. Not net profit. |
| Gross margin (standard) | standard gross profit / corresponding standard-cost-covered net sales | Do not divide by all sales while excluding missing costs from profit. |
| Landed gross profit (sensitivity) | `sum(quantity * (unit_price - landed_unit_cost))` | Alternate AP cost basis shown separately, not blended into the standard global KPI. |
| YoY sales change | current full-calendar-year net sales minus prior full-calendar-year net sales | Percent change divides by prior-year net sales. |
| Selling quantity | sum signed source `quantity` | Preserve as supplied; do not label pieces until source grain is agreed. |
| Pack equivalents (provisional) | `sum(quantity / pack_size)` | Only if source quantity counts individual eaches; do not label as physical units until source grain is confirmed. |
| Net sales / square foot | known-store net sales where area > 0 / sum modal positive store sqft | Weighted portfolio ratio; show area coverage and the excluded zero-area store. Not a lease productivity measure unless floor-area definition is confirmed. |
| Gross profit / square foot | standard-basis gross profit from positive-area stores / their summed sqft | Excludes unknown store and stores with invalid area; denominator and scope must accompany the KPI. |
| Return/adjustment line rate | negative-quantity event count / selected event count | Negative quantity has no reason or original-sale link in the source. |

## Report tabs and the questions each team should own

All tabs carry the shared net sales, standard gross profit/margin, and YoY
definitions above. Team-specific measures add context but do not replace the
company scorecard.

| View / accountable team | Primary KPIs | Guardrail against one-sided interpretation |
|---|---|---|
| **CEO / Management** | Net sales, gross profit, gross margin, YoY change, cost basis sensitivity, gross profit less direct store cost scenario | Optimize sustainable total-company gross profit; do not claim net income without full opex/tax. |
| **Finance** | Standard and landed gross profit/margin side-by-side, standard-cost coverage, signed COGS, YoY gross-profit change, direct-store-cost annual and monthly scenarios | Store opex is read as annual (decision, see SPEC.md); the monthly x12 reading is a sensitivity only. Costless sales stay visible. |
| **Merchandising / Buying** | Category/product sales and growth, gross profit and margin, selling quantity, provisional pack equivalents and price per equivalent (only if quantity grain is confirmed), returns | High revenue with poor margin is not a win; label pack-size interpretation and promotion/cost basis. |
| **Store Operations** | Store/region sales, cost and gross profit per sqft, store area coverage, returns, YoY | Compare only like-for-like positive areas; exclude store 200's zero sqft from area ratios, not from sales. |
| **Sales Operations** | Sales per event, sales/quantity, return-adjustment line rate, transaction-ID collision rate | Event key is not line ID; do not count source versions as extra sales. |
| **Data / Analytics Engineering** | Source-to-stage row count, exact-row fingerprint uniqueness, duplicate versions, unknown-key/cost coverage, attribute conflicts | Triage is reviewable and rebuildable, not a persistent disposition workflow. |

## Pack-size and cost interpretations

The supplied known product IDs have one observed pack size each: Dining products
Cocktail Glasses and Dinnerware use pack size 2; the other categories use 1.
Pack size is product packaging metadata, not a category hierarchy. At present,
the standard-cost-led gross-profit basis divides standard cost by pack size because
standard cost is about twice landed cost on pack-size-2 rows. Sales remain the
source `quantity * price` formula. Finance sees both this pack-adjusted standard
view and the unadjusted `quantity * standard_unit_cost` sensitivity alongside
landed cost. Confirm source quantity, price, and all cost grains before selecting
one interpretation as accounting truth.
