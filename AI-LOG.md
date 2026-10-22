# AI use log

AI assistance was used to profile the provided extract, compare candidate cost and
deduplication rules, draft the dbt models/tests, and prepare the presentation. The raw
CSV was not edited. All reported figures are generated from the built DuckDB marts;
the deck labels modeling assumptions and alternate-cost sensitivity. The candidate
reviewed the choices and remains responsible for validation and interpretation.

## Validation performed

- `uv sync` using the committed lockfile and Python 3.12.
- `DBT_PROFILES_DIR="$PWD" uv run dbt debug`
- `DBT_PROFILES_DIR="$PWD" uv run dbt build` (11 models built, 44 tests passed; no warnings).
- `npm ci`, `npm audit` (no vulnerabilities), and PowerPoint generation from mart exports.
- LibreOffice PDF rendering verified 9 slides; the `.pptx` includes 9 speaker-note parts.
- Manual checks of transaction-ID collisions, key coverage, cost/pack-size ratios,
  region conflicts, and annual/mart reconciliations.
