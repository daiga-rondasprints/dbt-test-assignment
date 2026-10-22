# Analytics engineer challenge

Timed take-home for analytics engineer candidates. You will **normalize** a denormalized retail extract with **dbt + DuckDB**, then present insights in a short **PowerPoint** for a CEO audience.

**Start here:** [ASSIGNMENT.md](./ASSIGNMENT.md)

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Python 3.12+ (uv will fetch it if needed)

## Setup (≈2 minutes)

```bash
# From the repo root
uv sync

# Confirm dbt + DuckDB adapter
uv run dbt --version

# Point dbt at the in-repo profiles.yml and verify the connection
export DBT_PROFILES_DIR="$(pwd)"
uv run dbt debug
```

Optional: add `export DBT_PROFILES_DIR="$(pwd)"` to your shell session, or prefix every dbt command with it.

## Useful commands

```bash
export DBT_PROFILES_DIR="$(pwd)"

# Parse / compile
uv run dbt parse
uv run dbt compile

# Explore the landing extract
uv run dbt show --inline "select * from {{ source('raw', 'consolidated_transactions') }}" --limit 5

# Build your project (after you add models)
uv run dbt build

# Query a model
uv run dbt show --select <model_name> --limit 20
```

DuckDB database file: `retail.duckdb` at the repo root (gitignored).

## Project layout

```text
ASSIGNMENT.md          # Candidate brief
SPEC.md                # Model grain and analytical assumptions
DATA_CONTRACT.md       # Proposed upstream schema and delivery rules
METRIC_DICTIONARY.md   # Shared global metrics and team-specific KPI views
AI-LOG.md              # AI use and validation summary
data/raw/              # consolidated_transactions.csv — do not edit
models/staging/        # Start here (_sources.yml + sample staging model)
models/intermediate/   # Normalization / business logic
models/marts/          # Dims + facts
presentation/          # CEO debrief PowerPoint + dashboard deck (PPTX/PDF)
dashboard/             # Streamlit app: every assignment question answered in words + one chart
analyses/              # Optional ad-hoc SQL for Part B
profiles.yml
dbt_project.yml
pyproject.toml
```

## Implemented model and decisions

The normalized design has one sales **event fact** (one selected row per
`transaction_id`), plus date, product and store dimensions. It is not an OBT or
a periodic snapshot: the input contains transactions, not balances. Annual and
monthly reporting models aggregate the fact and dimensions.

Staging is a persisted DuckDB table rebuilt from the immutable CSV on every
`dbt build`. dbt replaces the table instead of appending, and tests check the
source row count and unique row fingerprint. Re-running the same build therefore
does not accumulate duplicate staging records; it is a full refresh, not CDC.

The source is retained in staging. Duplicate transaction versions, missing or
placeholder keys, missing standard cost, negative quantities, and conflicting
product/store profiles are exposed in `mart_data_quality_triage`. Missing keys
are mapped to explicit Unknown dimension members, and negative quantities remain
in signed sales. The triage table is rebuilt from source; it is not an editable
workflow queue. See [SPEC.md](./SPEC.md) and [DATA_CONTRACT.md](./DATA_CONTRACT.md)
for grain, cost assumptions, exception handling, and the proposed upstream
contract. The fact reports the source quantity unchanged. `pack_size` supplies a
separate provisional physical-unit calculation; do not alter revenue unless the
upstream team confirms quantity and price grain. See
[METRIC_DICTIONARY.md](./METRIC_DICTIONARY.md) for one global formula set and
the Finance, Merchandising, Store Operations, and Sales Ops report views.

## Build the presentation

After a successful dbt build, export slide inputs from the marts and create the
speaker-noted PowerPoint:

```bash
uv run python scripts/export_presentation_metrics.py
npm ci
npm run build:presentation
```

The resulting deck is `presentation/retail_ceo_debrief.pptx` (12 slides). Slide
metrics are read from the built DuckDB marts; no slide query re-aggregates the
raw CSV. It includes the row-count/disposition flow, dimension hierarchies,
per-square-foot metrics, and cross-team KPI views.

## Run the dashboard

An interactive Streamlit app answers the modelling questions (facts/dimensions,
event vs snapshot, dirty-data triage, Kimball vs OBT, SCD2), draws the row-count
flow, and works through the business questions (category profitability by
region/state, store size vs performance, products losing favour, cost vs margin,
quantity vs margin, store type vs profitability overall and per category,
seasonality by product and by state/store) plus store-month and product-hierarchy
outlier scatters. Every number is read from the built DuckDB marts, never the CSV.

```bash
uv sync --group dashboard
uv run --group dashboard streamlit run dashboard/app.py
```

Open http://localhost:8501. Use the left pane to set the year, regions and
categories. Add `?section=3` to the URL to open one section on its own. Each
chart has an "Audit CSV" button that downloads the aggregate behind it. Styling
follows the Storytelling-with-Data rules in `dashboard/swd.py` (grey baseline,
one accent colour, action titles, no chart junk).

## Export the dashboard as a slide deck (PPTX + PDF)

With the dashboard running, capture every collapsible visual as a slide:

```bash
uv run --group dashboard --with playwright python scripts/export_dashboard_deck.py
```

Writes `presentation/retail_dashboard_deck.pptx` and `.pdf` (title, agenda, one divider per tab,
one slide per visual). Playwright needs a Chromium; set `DASHBOARD_CHROME=/path/to/chrome` to use an
existing binary. PDF conversion uses LibreOffice when installed.

## Stack

| Tool | Role |
|------|------|
| [uv](https://docs.astral.sh/uv/) | Package / environment manager |
| [dbt-core](https://docs.getdbt.com/) + [dbt-duckdb](https://github.com/duckdb/dbt-duckdb) | Transformation framework |
| [DuckDB](https://duckdb.org/) | Local analytical database |
| [Streamlit](https://streamlit.io/) + [Plotly](https://plotly.com/python/) | Interactive dashboard (optional `dashboard` dependency group) |

## Verify the environment

```bash
./scripts/verify_env.sh
```

This checks that dependencies install, dbt can connect, and the consolidated source is readable.

The implemented intermediate and mart models remove the unused-path warnings.
