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
AI-LOG.md              # AI use and validation summary
data/raw/              # consolidated_transactions.csv — do not edit
models/staging/        # Start here (_sources.yml + sample staging model)
models/intermediate/   # Normalization / business logic
models/marts/          # Dims + facts
presentation/          # CEO debrief PowerPoint
analyses/              # Optional ad-hoc SQL for Part B
profiles.yml
dbt_project.yml
pyproject.toml
```

## Implemented model and decisions

The normalized design has one sales **event fact** (one selected row per
`transaction_id`), a product dimension, and a store dimension. It is not an
OBT or a periodic snapshot: the input contains transactions, not balances.
Annual and monthly reporting models are marts built from the fact and dimensions.

The source is retained in staging. Duplicate transaction versions, missing or
placeholder keys, missing standard cost, negative quantities, and conflicting
product/store profiles are exposed in `mart_data_quality_triage`. Missing keys
are mapped to explicit Unknown dimension members, and negative quantities remain
in signed sales. The triage table is rebuilt from source; it is not an editable
workflow queue. See [SPEC.md](./SPEC.md) and [DATA_CONTRACT.md](./DATA_CONTRACT.md)
for grain, cost assumptions, exception handling, and the proposed upstream
contract.

## Build the presentation

After a successful dbt build, export slide inputs from the marts and create the
speaker-noted PowerPoint:

```bash
uv run python scripts/export_presentation_metrics.py
npm ci
npm run build:presentation
```

The resulting deck is `presentation/retail_ceo_debrief.pptx`. Slide metrics are
read from the built DuckDB marts; no slide query re-aggregates the raw CSV.

## Stack

| Tool | Role |
|------|------|
| [uv](https://docs.astral.sh/uv/) | Package / environment manager |
| [dbt-core](https://docs.getdbt.com/) + [dbt-duckdb](https://github.com/duckdb/dbt-duckdb) | Transformation framework |
| [DuckDB](https://duckdb.org/) | Local analytical database |

## Verify the environment

```bash
./scripts/verify_env.sh
```

This checks that dependencies install, dbt can connect, and the consolidated source is readable.

The implemented intermediate and mart models remove the unused-path warnings.
