"""Retail assignment dashboard: every question answered in words and with one collapsible chart.

Run from the repo root after `uv run dbt build`:
    uv run --group dashboard streamlit run dashboard/app.py
Deep link to one section: http://localhost:8501/?section=5
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai  # noqa: E402
import data  # noqa: E402
import swd  # noqa: E402

st.set_page_config(page_title="Retail performance story", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
      h2, h3 { color: #212529; }
      .modebar { display: none !important; }
      div[data-testid="stExpander"] details { border: 0; border-top: 1px solid #ECECEC; border-radius: 0; margin-top: 6px; }
      div[data-testid="stExpander"] summary p { font-size: 15px; color: #212529; }
      button[data-baseweb="tab"] p { font-size: 14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not data.DB.exists():
    st.error(f"`{data.DB}` not found. Run `uv run dbt build` first; the dashboard reads only the built dbt relations.")
    st.stop()

load = st.cache_data(ttl=600, show_spinner=False)
flow = load(data.row_flow)()
triage = load(data.triage_counts)()
conflict = load(data.product_name_conflict)()
annual = load(data.annual)()
monthly = load(data.monthly)()
product_year = load(data.product_year)()
store_year = load(data.store_year)()
events = load(data.events)()
scorecard = load(data.scorecard)()
inv = load(data.dbt_inventory)()

usd = lambda v, d=1: f"{'-' if v < 0 else ''}${abs(v) / 1e6:,.{d}f}m"  # noqa: E731
pct = lambda v, d=1: f"{v * 100:,.{d}f}%"  # noqa: E731
pp = lambda v: f"{v * 100:+.1f} pp"  # noqa: E731
MONTHS = [pd.Timestamp(2000, m, 1).strftime("%b") for m in range(1, 13)]


def agg(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = df.groupby(by, as_index=False).agg(
        net_sales=("net_sales", "sum"), gross_profit=("gross_profit", "sum"), costed_net_sales=("costed_net_sales", "sum"),
        cost=("standard_cost_of_sales", "sum"), landed_gross_profit=("landed_gross_profit", "sum"), landed_cost=("landed_cost_of_sales", "sum"),
        quantity=("quantity", "sum"), events=("transaction_id", "count"), returns=("is_return_or_adjustment", "sum"))
    g["gross_margin"] = g["gross_profit"] / g["costed_net_sales"].replace(0, np.nan)
    g["landed_margin"] = g["landed_gross_profit"] / g["net_sales"].replace(0, np.nan)
    return g


# ----------------------------------------------------------------------------- sidebar
st.sidebar.markdown("### Scope")
years = sorted(events["year"].unique().tolist())
year = st.sidebar.selectbox("Year for point-in-time questions", years, index=len(years) - 1, key="year")
regions = sorted(events.loc[events["region_name"] != "Unknown", "region_name"].unique().tolist())
sel_regions = st.sidebar.multiselect("Region", regions, default=regions, key="regions")
categories = sorted(events.loc[events["product_key"] != -1, "product_category"].unique().tolist())
sel_categories = st.sidebar.multiselect("Product category", categories, default=categories, key="categories")
if st.sidebar.button("Reset"):
    st.rerun()
st.sidebar.caption(f"Source: `{data.DB.name}` dbt marts. Profit = **gross** profit on standard cost (pack-adjusted); not net profit. "
                   "Unknown product/store rows stay in company totals but are excluded from cross-cuts.")
st.sidebar.caption(f"Interpretation engine: {ai.engine_label()}")

known = events[(events["product_key"] != -1) & (events["store_key"] != -1)]
scope = known[known["region_name"].isin(sel_regions) & known["product_category"].isin(sel_categories)]
scope_year = scope[scope["year"] == year]
filters_text = "; ".join(x for x in [
    f"year {year}",
    f"regions: {', '.join(sel_regions)}" if len(sel_regions) < len(regions) else "",
    f"categories: {', '.join(sel_categories)}" if len(sel_categories) < len(categories) else ""] if x) or "none"


def visual(key: str, question: str, answer: str, fig, table: pd.DataFrame, note: str | None = None,
           expanded: bool = True, caveat: str = "", before=None) -> None:
    """One collapsible section: question in the header, answer, chart, audit download and the Interpret widget."""
    with st.expander(f"**{question}**", expanded=expanded):
        if before:
            before()
        if answer:
            st.markdown(swd.prose(answer), unsafe_allow_html=True)
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key=f"chart_{key}")
        c1, c2, c3 = st.columns([1, 1.1, 4.5])
        c1.download_button("Audit CSV", table.to_csv(index=False).encode(), f"{key}.csv", "text/csv", key=f"csv_{key}")
        title = fig.layout.title.text.split("<br>")[0].replace("<b>", "").replace("</b>", "") if fig is not None else question
        payload = ai.build_payload(question, title, table, filters_text, caveat)
        if c2.button("Interpret", key=f"ai_{key}", help=f"Engine: {ai.engine_label()}"):
            st.session_state[f"aiout_{key}"] = ai.interpret(payload)
        if note:
            c3.caption(note)
        if st.session_state.get(f"aiout_{key}"):
            st.markdown(st.session_state[f"aiout_{key}"])
            st.caption(f"Engine: {ai.engine_label()} · payload below is everything the engine saw")
            st.json(payload, expanded=False)


# ----------------------------------------------------------------------------- header + stakeholder tiles
st.markdown("## Retail performance: what the data is, how it flows, and what is working")
st.caption("One question, one answer, one chart per section; every chart collapses. Every figure is read from the built dbt marts.")

y = annual.set_index("year")
cur, prev = y.loc[year], (y.loc[year - 1] if year - 1 in y.index else None)
sy_all = store_year[(store_year["year"] == year)]
opex_annual = sy_all["direct_store_operating_costs"].sum()
gp_known = sy_all["gross_profit"].sum()
covered_annual = int((sy_all["direct_store_operating_costs"] <= sy_all["gross_profit"]).sum())
covered_monthly = int((sy_all["direct_store_operating_costs"] * 12 <= sy_all["gross_profit"]).sum())
landed_margin = cur["landed_gross_profit"] / cur["net_sales"]
yoy = lambda col: f"{usd(cur[col] - prev[col], 2)} / {pct(cur[col] / prev[col] - 1)} YoY" if prev is not None else ""  # noqa: E731

st.markdown(f"<div style='font-size:12px;color:{swd.GREY_DARK};margin-bottom:4px'>Headline {year}, one tile per stakeholder note. "
            f"Net sales {usd(cur['net_sales'], 2)} ({yoy('net_sales')}); average selling price ${cur['average_selling_price']:.2f}"
            + (f" ({cur['average_selling_price'] - prev['average_selling_price']:+.2f} / {pct(cur['average_selling_price'] / prev['average_selling_price'] - 1)} YoY)." if prev is not None else ".")
            + "</div>", unsafe_allow_html=True)
t = st.columns(4)
t[0].markdown(swd.tile("Finance planning · margin on standard_unit_cost", pct(cur["gross_margin_pct"]),
                       f"Gross profit {usd(cur['gross_profit'], 2)} ({yoy('gross_profit')})<br>margin {pp(cur['gross_margin_pct'] - prev['gross_margin_pct']) if prev is not None else ''} YoY · pack-adjusted",
                       cur["gross_profit_yoy_change"] >= 0 if prev is not None else None), unsafe_allow_html=True)
t[1].markdown(swd.tile("AP / Ops · margin on landed_unit_cost", pct(landed_margin),
                       f"Landed gross profit {usd(cur['landed_gross_profit'], 2)} ({yoy('landed_gross_profit')})<br>"
                       f"{(cur['gross_margin_pct'] - landed_margin) * 100:.1f} pp below the Finance view; shown as a sensitivity",
                       (cur["landed_gross_profit"] >= prev["landed_gross_profit"]) if prev is not None else None), unsafe_allow_html=True)
t[2].markdown(swd.tile("Sales ops · latest ingested_at wins", f"{flow['fact_rows']:,} events",
                       f"{flow['colliding_ids']:,} colliding IDs: newest version kept, {flow['excluded_versions']:,} older moved to triage<br>"
                       f"Net sales {usd(cur['net_sales'], 2)} ({yoy('net_sales')})", True), unsafe_allow_html=True)
t[3].markdown(swd.tile("FP&A vs Store Finance · opex read as ANNUAL", usd(gp_known - opex_annual, 2),
                       f"Gross profit less store opex {usd(opex_annual, 2)}; {covered_annual}/{len(sy_all)} stores cover it<br>"
                       f"Monthly reading rejected: x12 = {usd(opex_annual * 12, 1)}, only {covered_monthly} stores would cover it",
                       (gp_known - opex_annual) >= 0), unsafe_allow_html=True)

SECTION_LABELS = ["Solution map", "Data & model", "Row flow", "Management", "Finance", "AP / Ops", "Sales", "Stores", "Analysis", "Roadmap & AI"]
N_VISUALS = 37  # kept in sync by hand; shown on the solution map


# ============================================================================= 1. solution map
def render_solution() -> None:
    ic = data.icon_svg
    tt = inv["test_types"]
    generic = {k: v for k, v in tt.items() if k != "singular SQL"}

    def stage(icon_html, title, lines, accent=False):
        border = swd.ACCENT if accent else swd.GREY_LIGHT
        bg = swd.BG_SOFT if accent else "white"
        body = "".join(f"<div style='font-size:11.5px;color:{swd.GREY_DARK};line-height:1.35'>{x}</div>" for x in lines)
        return (f"<div style='flex:1;min-width:150px;border:2px solid {border};background:{bg};border-radius:8px;padding:10px 12px'>"
                f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px'>{icon_html}"
                f"<span style='font-weight:700;font-size:13px;color:{swd.TEXT}'>{title}</span></div>{body}</div>")

    arrow = f"<div style='align-self:center;color:{swd.GREY_DARK};font-size:22px;padding:0 4px'>&#8594;</div>"
    stages = [
        stage("<span style='font-size:26px'>&#128196;</span>", "CSV extract",
              [f"<b>{flow['source_rows']:,}</b> rows, {years[0]}–{years[-1]}", "data/raw/consolidated_transactions.csv", "immutable; never edited"]),
        stage(ic("uv") + ic("python"), "uv + Python 3.12",
              ["locked environment (uv.lock)", "dbt-duckdb adapter", "dashboard dependency group"]),
        stage(ic("dbt"), f"dbt {inv['dbt_version']}",
              [f"<b>{inv['models']}</b> models: " + ", ".join(f"{k} {v}" for k, v in inv["layers"].items()),
               f"<b>{inv['tests']}</b> tests · package <code>{', '.join(inv['packages']) or 'retail_challenge'}</code> (no external dbt packages)",
               "generic (dbt-core): " + ", ".join(f"{k} {v}" for k, v in generic.items()),
               f"singular SQL in tests/: {inv['singular']}",
               f"last build: {inv['last_run_pass']}/{inv['last_run_total']} passed" if inv["last_run_total"] else "run `uv run dbt build`"], accent=True),
        stage(ic("duckdb"), "DuckDB",
              ["retail.duckdb (local, file-based)", "schemas: staging · intermediate · marts", "1 event fact · 3 dims · 6 marts · 1 triage"]),
    ]
    outputs = [
        stage(ic("streamlit") + ic("plotly") + ic("pandas"), "Dashboard",
              [f"Streamlit + Plotly, {len(SECTION_LABELS)} tabs", f"{N_VISUALS} collapsible visuals, Audit CSV each", "offline/LLM interpretation widget"], accent=True),
        stage(ic("nodedotjs") + ic("python"), "Decks (PPTX + PDF)",
              ["CEO debrief: pptxgenjs, 12 slides + notes", "Dashboard deck: every visual captured → python-pptx, PDF via LibreOffice", "both read marts, never the CSV"]),
        stage("<span style='font-size:24px'>&#128221;</span>", "Documents",
              ["SPEC.md · DATA_CONTRACT.md", "METRIC_DICTIONARY.md · AI-LOG.md", "README.md (setup & commands)"]),
        stage(ic("github") + ic("githubcopilot"), "Repository",
              ["daiga-rondasprints/dbt-test-assignment", "commits with Copilot co-author trailer", "fork only; upstream untouched"]),
    ]
    st.markdown(f"<div style='font-size:14px;font-weight:600;color:{swd.TEXT};margin:4px 0'>From one CSV to four deliverables</div>", unsafe_allow_html=True)
    st.markdown("<div style='display:flex;gap:4px;align-items:stretch'>" + arrow.join(stages) + "</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;color:{swd.GREY_DARK};font-size:22px;margin:2px 0'>&#8595;</div>", unsafe_allow_html=True)
    st.markdown("<div style='display:flex;gap:10px;align-items:stretch'>" + "".join(outputs) + "</div>", unsafe_allow_html=True)
    st.caption("Vendor marks: Simple Icons (CC0); trademarks belong to their owners. Counts are read live from dbt's manifest.json and run_results.json.")

    tests_df = pd.DataFrame(sorted(tt.items(), key=lambda kv: -kv[1]), columns=["test", "count"])
    tests_df["test"] = tests_df["test"].map(lambda k: f"{k} (dbt-core generic)" if k != "singular SQL" else "singular SQL (tests/*.sql)")
    visual("tests", f"What do the {inv['tests']} dbt tests check?",
           f"{inv['tests'] - inv['singular']} are dbt-core generic tests declared in YAML (not_null, unique, accepted_values, relationships) and "
           f"{inv['singular']} are singular SQL assertions: staging row count = source, unique row fingerprint, fact = selected versions, one triage row per "
           f"collision, scorecard grain, and key agreement. No third-party dbt packages are needed yet (dbt_utils / dbt_expectations are on the roadmap).",
           swd.bar_ranked(tests_df, "test", "count", f"{inv['tests']} tests: mostly not-null and uniqueness guards, plus {inv['singular']} business assertions",
                          "Count by test type, from target/manifest.json", label_all=True, highlight="singular SQL (tests/*.sql)", height=300), tests_df)

    deliverables = pd.DataFrame([
        ("dbt project", "models/, tests/, dbt_project.yml", "Staging → versions → fact + dims → marts + triage", "uv run dbt build"),
        ("DuckDB database", "retail.duckdb", "All built relations; the single source for deck and dashboard", "created by dbt build"),
        ("Dashboard", "dashboard/app.py", "This app: model, row flow, team views, analysis, outliers", "uv run --group dashboard streamlit run dashboard/app.py"),
        ("CEO deck", "presentation/retail_ceo_debrief.pptx", "12 slides with speaker notes", "uv run python scripts/export_presentation_metrics.py && npm run build:presentation"),
        ("Dashboard deck", "presentation/retail_dashboard_deck.pptx / .pdf", "Every dashboard visual as a slide, one section per divider", "uv run --group dashboard --with playwright python scripts/export_dashboard_deck.py (app running)"),
        ("Specification", "SPEC.md", "Grain, decisions, evidence, known limits", "edit"),
        ("Data contract", "DATA_CONTRACT.md", "What upstream must deliver in the transactions file", "edit"),
        ("Metric dictionary", "METRIC_DICTIONARY.md", "Global formulae and team views", "edit"),
        ("AI log", "AI-LOG.md", "How AI assistance was used and validated", "edit"),
    ], columns=["Deliverable", "Where", "What it answers", "How to regenerate"])
    with st.expander("**Deliverables list**", expanded=False):
        st.dataframe(deliverables, hide_index=True, width="stretch")


# ============================================================================= 2. data & model
def glossary() -> pd.DataFrame:
    tc = triage.set_index("issue_code")["rows"]
    rows = [
        ("Transaction ID", f"Sales-line identifier. Not unique: {flow['colliding_ids']:,} IDs appear twice.", "Event key, after keeping the newest ingested_at version"),
        ("Transaction Date", f"Economic date of the sale. Only {flow['event_dates']} distinct dates, all the 1st of a month.", "date_key; YoY and seasonality"),
        ("quantity", f"Signed units; negative = return/adjustment ({tc.get('NEGATIVE_QUANTITY_REVIEW', 0):,} lines). Eaches vs packs unconfirmed.", "Net sales, volume; kept signed"),
        ("unit_price", "Selling price per quantity unit.", "Net sales = quantity x unit_price; average selling price"),
        ("unit_cost", "Third cost column; equals standard_unit_cost on ~98% of rows.", "Not used; contract asks upstream to drop or define it"),
        ("standard_unit_cost", f"Finance's budget cost. About 2x landed on pack_size 2, so read as a per-pack cost. Missing on {tc.get('MISSING_STANDARD_COST', 0):,} rows.", "Primary gross profit: quantity x standard / pack_size"),
        ("landed_unit_cost", "What AP actually paid per unit.", "AP/Ops margin sensitivity"),
        ("pack_size", "Units per pack (1 or 2); one value per product.", "Divides standard cost; provisional pack equivalents"),
        ("Product index", f"Product ID. Null or 99901 = unknown ({tc.get('UNKNOWN_PRODUCT_KEY', 0):,} rows).", "product_key (-1 for Unknown)"),
        ("Product Name", "Name on the transaction; can disagree with the catalog.", "Conflict detection only"),
        ("product_name_catalog", "Catalog name. Product 19 carries two names (Vanities / Cosmetics).", "dim_product name (modal profile)"),
        ("product_category", "Six categories.", "Top of the product hierarchy"),
        ("product_effective_from / to", "Intended validity window; identical for both product-19 names, so not a real history.", "Not used for SCD2 (evidence below)"),
        ("Store ID", f"Store key. Null or 99901 = unknown ({tc.get('UNKNOWN_STORE_KEY', 0):,} rows).", "store_key (-1 for Unknown)"),
        ("store_name", f"Mostly a city name; not unique ({flow['store_names']} names for {flow['dim_store_known']} stores).", "Label; city proxy in seasonality view"),
        ("state_code / state", "US state.", "Store hierarchy: region > state > store"),
        ("region_name", "Census region; disagrees across rows for one Maryland store.", "Recomputed from state_code"),
        ("store_type", "Nine civic types (City, Township, Borough, CDP, ...).", "Slicer, not a hierarchy level"),
        ("store_sqft", "Floor area; one store reports 0.", "Sales, cost and gross profit per sqft"),
        ("direct_store_operating_costs", "One figure per store, period unstated. Read as annual (see headline tile).", "Store contribution scenario"),
        ("source_system", "POS / ERP / Manual lineage.", "Tie-break when two versions share ingested_at"),
        ("ingested_at", "Load timestamp (lineage, not economic time).", "Newest version wins on colliding IDs"),
    ]
    return pd.DataFrame(rows, columns=["Column in the file", "What we understand", "How the model uses it"])


def render_model() -> None:
    with st.expander("**What is in the file?**", expanded=True):
        st.markdown(swd.prose(f"One CSV, {flow['source_rows']:,} rows, {years[0]}–{years[-1]}: one sales line per row with product and store attributes repeated on every row."),
                    unsafe_allow_html=True)
        st.dataframe(glossary(), hide_index=True, width="stretch", height=810,
                     column_config={"Column in the file": st.column_config.TextColumn(width="medium"),
                                    "What we understand": st.column_config.TextColumn(width="large"),
                                    "How the model uses it": st.column_config.TextColumn(width="large")})
    with st.expander("**How many facts and dimensions? Event or snapshot? Kimball or OBT? Type 2?**", expanded=True):
        c1, c2 = st.columns([1.3, 1])
        with c1:
            st.markdown(swd.prose(f"<b>1 event fact</b> ({flow['fact_rows']:,} rows) and <b>3 dimensions</b>: product {flow['dim_product_known']}+Unknown, "
                                  f"store {flow['dim_store_known']}+Unknown, date {flow['dim_date']:,} days. Six marts on top are aggregates, not more facts."),
                        unsafe_allow_html=True)
            st.plotly_chart(swd.star_schema(
                "fct_sales", [f"{flow['fact_rows']:,} events (1 per transaction ID)", "signed quantity · unit price · pack size",
                              "net sales · standard cost · gross profit", "landed-cost and unadjusted sensitivities"],
                {"dim_product": [f"{flow['dim_product']} rows", "category → product", "pack_size attribute"],
                 "dim_store": [f"{flow['dim_store']} rows", "region → state → store", "store_type, sqft, direct cost"],
                 "dim_date": [f"{flow['dim_date']:,} days", f"{flow['date_min']} → {flow['date_max']}", "year / quarter / month"],
                 "Aggregate marts": ["annual · monthly · product", "store · region · team KPI", "+ data-quality triage"]},
                "A Kimball star: one event fact, three conformed dimensions", "Marts are derived from the fact, never from the CSV"),
                width="stretch", key="star")
        with c2:
            st.markdown(swd.answer("Event fact or snapshot fact?",
                                   f"<b>Event.</b> Rows are sales/returns, not balances. All {flow['event_dates']} dates are the 1st of a month, so it looks "
                                   f"monthly, but the monthly marts are aggregates of events, not a periodic snapshot."), unsafe_allow_html=True)
            st.markdown(swd.answer("Kimball or One Big Table?",
                                   "<b>Kimball.</b> Product and store attributes conflict inside the file; conformed dimensions resolve each entity once, "
                                   "an OBT would sum the conflicts."), unsafe_allow_html=True)
            st.markdown(swd.answer("Type 2 dimension?",
                                   "<b>Not yet.</b> The effective dates are not a history: product 19 is 'Vanities' and 'Cosmetics' in every year with the "
                                   "same window. Type 1 now; SCD2 when upstream sends real valid_from/valid_to."), unsafe_allow_html=True)
            st.dataframe(conflict[["product_name_catalog", "product_effective_from", "product_effective_to", "first_seen", "last_seen", "rows"]],
                         hide_index=True, width="stretch", column_config={"rows": st.column_config.NumberColumn(format="%d")})
    tri = triage.copy()
    tri["label"] = tri["issue_code"].str.replace("_", " ").str.capitalize()
    visual("triage", "What happens to dirty data?",
           f"Nothing is deleted. Colliding IDs: newest <code>ingested_at</code> version goes to the fact, the older one to "
           f"<code>mart_data_quality_triage</code>. Unknown keys, returns and missing costs stay in the fact and are flagged "
           f"({flow['triage_rows']:,} issue rows; rebuilt every run). <code>DATA_CONTRACT.md</code> states what we expect upstream.",
           swd.bar_ranked(tri, "label", "rows", "Older duplicate versions are the biggest triage category; nothing is deleted",
                          "Issue rows in mart_data_quality_triage (one row per older duplicate version)", label_all=True, highlight="Duplicate transaction id"), tri)


# ============================================================================= 3. row flow
def render_flow() -> None:
    stages = [("Raw CSV", flow["source_rows"], ["immutable extract", "data/raw"]),
              ("Persisted staging", flow["staging_rows"], ["DuckDB table, full replace", f"{flow['distinct_fingerprints']:,} unique fingerprints"]),
              ("Version audit", flow["version_rows"], ["every row ranked per transaction ID", "disposition recorded"]),
              ("fct_sales", flow["fact_rows"], ["1 row per transaction ID", "latest ingestion wins"])]
    branch = ("Older versions → triage", flow["excluded_versions"], [f"{flow['colliding_ids']:,} IDs × 2 versions", "kept in triage, not in the fact"])
    flow_df = pd.DataFrame({"stage": [s[0] for s in stages] + [branch[0]], "rows": [s[1] for s in stages] + [branch[1]]})
    visual("rowflow", "How many rows did we start with, and how many were de-duplicated or sent to triage?",
           f"Start <b>{flow['source_rows']:,}</b> → staging <b>{flow['staging_rows']:,}</b> (1:1) → version audit <b>{flow['version_rows']:,}</b> → fact "
           f"<b>{flow['fact_rows']:,}</b>. The only rows leaving are the <b>{flow['excluded_versions']:,}</b> older versions of the {flow['colliding_ids']:,} IDs that "
           f"appeared twice. Triage flags {flow['triage_rows']:,} issue rows, but those are flags on retained rows.",
           swd.pipeline_flow(stages, branch, "Only older duplicate versions leave the pipeline; every other row reaches the fact",
                             f"Row counts per layer. Triage also flags {flow['triage_rows']:,} issue rows on retained rows (unknown keys, returns, missing cost)."), flow_df)
    with st.expander("**Is staging persisted and rerun-safe? Dimensions, facts, aggregates, date range, date dimension, derived metrics**", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(swd.answer("Persisted staging, rerun-safe?",
                                   f"Yes. <code>stg_consolidated_transactions</code> is a DuckDB <b>table</b> rebuilt by full replacement on every <code>dbt build</code>; "
                                   f"two builds both landed {flow['staging_rows']:,} rows. Tests: staging count = source, fingerprint unique, fact = selected versions. "
                                   f"Re-running cannot create duplicates (full reload, not CDC)."), unsafe_allow_html=True)
            st.markdown(swd.answer("Dimensions and rows",
                                   f"Three: product {flow['dim_product']} ({flow['dim_product_known']}+Unknown), store {flow['dim_store']} ({flow['dim_store_known']}+Unknown), "
                                   f"date {flow['dim_date']:,} ({flow['date_min']} to {flow['date_max']})."), unsafe_allow_html=True)
            st.markdown(swd.answer("Fact tables and aggregates",
                                   f"One atomic fact, {flow['fact_rows']:,} rows. Six aggregate marts (annual, monthly, product, store, region, team KPI) so every "
                                   f"team reads the same formulae; the fact stays the source of truth."), unsafe_allow_html=True)
        with c2:
            st.markdown(swd.answer("Must every query carry a date range?",
                                   "No, a whole-fact sum is valid. A business report always should: it fixes the YoY period, excludes partial periods and lets the "
                                   "engine prune on <code>date_key</code>. The marts bake the calendar year in."), unsafe_allow_html=True)
            st.markdown(swd.answer("Date dimension?",
                                   f"Yes, <code>dim_date</code>: {flow['dim_date']:,} days with year, quarter, month and weekday flags; the fact joins on an integer key."),
                        unsafe_allow_html=True)
            st.markdown(swd.answer("Derived metrics",
                                   "Net sales; standard cost of sales (pack-adjusted); gross profit and margin; YoY in $ and %; average selling price and a "
                                   "price/volume bridge; landed and unadjusted sensitivities; sales, cost and gross profit per sqft; pack equivalents (provisional); "
                                   "return-line rate; cost coverage; store-opex contribution. Formulae in <code>METRIC_DICTIONARY.md</code>."), unsafe_allow_html=True)
        metrics = scorecard[scorecard["year"] == year][["team_view", "metric_code", "metric_value", "metric_unit", "metric_basis", "formula"]]
        st.dataframe(metrics, hide_index=True, width="stretch", height=300)


# ============================================================================= 4. management
def render_management() -> None:
    a = annual.copy()
    long = a.melt(id_vars="year", value_vars=["net_sales", "gross_profit"], var_name="measure", value_name="usd")
    fig = swd.line_trend(long, "year", "usd", f"Sales {pct(cur['net_sales_yoy_pct'])} and gross profit {pct(cur['gross_profit_yoy_pct'])} YoY in {year}; margin {pp(cur['gross_margin_pct'] - prev['gross_margin_pct']) if prev is not None else ''}",
                         "Company-wide net sales and standard gross profit by calendar year", series="measure", highlight="gross_profit", fmt="${:,.0f}", height=340)
    fig.update_xaxes(dtick=1, tickformat="d")
    visual("mgmt_trend", "Are we growing profitably?",
           f"Net sales {usd(cur['net_sales'], 2)} ({yoy('net_sales')}); gross profit {usd(cur['gross_profit'], 2)} ({yoy('gross_profit')}); margin {pct(cur['gross_margin_pct'])}"
           + (f", {pp(cur['gross_margin_pct'] - prev['gross_margin_pct'])} YoY. Growth is real but margin is slipping: profit grows slower than sales." if prev is not None else "."),
           fig, a[["year", "net_sales", "gross_profit", "gross_margin_pct", "net_sales_yoy_pct", "gross_profit_yoy_pct"]])

    if prev is not None:
        vol = (cur["net_units_sold"] - prev["net_units_sold"]) * prev["average_selling_price"]
        pm = cur["net_units_sold"] * (cur["average_selling_price"] - prev["average_selling_price"])
        bridge = pd.DataFrame({"driver": ["Volume effect", "Price / mix effect"], "usd": [vol, pm]})
        visual("mgmt_bridge", "Where did the growth come from: price or volume?",
               f"Of the {usd(cur['net_sales_yoy_change'], 2)} increase, {usd(vol, 2)} ({vol / cur['net_sales_yoy_change']:.0%}) is volume and {usd(pm, 2)} is price/mix. "
               f"ASP moved ${prev['average_selling_price']:.2f} → ${cur['average_selling_price']:.2f}. The price/mix residual blends list-price moves with category mix; "
               f"it is not price elasticity.",
               swd.bar_ranked(bridge, "driver", "usd", f"{year} growth was {vol / cur['net_sales_yoy_change']:.0%} volume", "Exact arithmetic on mart units and average selling price",
                              fmt="${:,.0f}", label_all=True, highlight="Volume effect", height=240), bridge)

    rg = agg(scope_year, ["region_name"]).sort_values("gross_profit", ascending=False)
    visual("mgmt_region", "Which regions carry the company?",
           f"{rg.iloc[0]['region_name']} delivers {rg.iloc[0]['gross_profit'] / rg['gross_profit'].sum():.0%} of gross profit at {pct(rg.iloc[0]['gross_margin'])} margin; "
           f"{rg.iloc[-1]['region_name']} is smallest at {pct(rg.iloc[-1]['gross_margin'])}. Concentration risk and the margin gap are both management questions.",
           swd.bar_ranked(rg, "region_name", "gross_profit", f"{rg.iloc[0]['region_name']} earns {rg.iloc[0]['gross_profit'] / rg['gross_profit'].sum():.0%} of gross profit ({year})",
                          "Gross profit by region; hover for margin", fmt="${:,.0f}", label_all=True, height=260), rg)

    pq = agg(scope_year, ["product_category", "product_name"])
    pq["do_more"] = (pq["net_sales"] >= pq["net_sales"].median()) & (pq["gross_margin"] >= pq["gross_margin"].median())
    winners = pq.loc[pq["do_more"], "product_name"].tolist()
    cows = pq.loc[(pq["net_sales"] >= pq["net_sales"].median()) & (pq["gross_margin"] < pq["gross_margin"].median()), "product_name"].tolist()
    visual("mgmt_domore", "What is working, and what should we do more of?",
           f"Top-right: above-median sales <i>and</i> margin — <b>{', '.join(winners)}</b>: more space, stock and promotion, in the store types and regions where "
           f"their margin is highest. Bottom-right (high sales, low margin: {', '.join(cows) or 'none'}) earns revenue but needs cost or price work before scaling.",
           swd.scatter_points(pq, "net_sales", "gross_margin", "product_name", f"Do more of the top-right: {len(winners)} products with high sales and high margin ({year})",
                              "x = net sales $ (log); y = gross margin; bubble = net quantity", highlight=winners, size="quantity", log_x=True,
                              x_title="Net sales, $", y_title="Gross margin", y_fmt=".1%", hover_extra=["product_category", "quantity"],
                              x_ref=pq["net_sales"].median(), y_ref=pq["gross_margin"].median(), height=440), pq)

    so = sy_all[sy_all["region_name"].isin(sel_regions)].groupby("region_name", as_index=False).agg(
        gross_profit=("gross_profit", "sum"), opex=("direct_store_operating_costs", "sum"), stores=("store_key", "count"))
    so["contribution"] = so["gross_profit"] - so["opex"]
    visual("mgmt_opex", "After store operating cost, what is left?",
           f"Reading store opex as annual (decision in SPEC.md): {usd(so['contribution'].sum(), 2)} remains after {usd(so['opex'].sum(), 2)} of direct store cost. "
           f"{so.sort_values('contribution').iloc[0]['region_name']} is the weakest region on contribution. Not net profit: central costs and tax are absent.",
           swd.bar_ranked(so, "region_name", "contribution", f"Gross profit less annual store opex by region ({year})", "Contribution = gross profit − direct_store_operating_costs (annual)",
                          fmt="${:,.0f}", label_all=True, height=260), so, caveat="Opex period is a decision, not a confirmed fact; the monthly reading is implausible.")


# ============================================================================= 5. finance
def render_finance() -> None:
    a = annual.copy()
    bases = a.melt(id_vars="year", value_vars=["gross_margin_pct", "gross_margin_standard_unadjusted_pct", "landed_gross_margin_pct"], var_name="basis", value_name="margin")
    bases["basis"] = bases["basis"].map({"gross_margin_pct": "Standard (pack-adjusted) — primary", "gross_margin_standard_unadjusted_pct": "Standard unadjusted",
                                         "landed_gross_margin_pct": "Landed (AP)"})
    fig = swd.line_trend(bases, "year", "margin", f"Three cost bases, one direction: margin fell in {year} on all of them", "Gross margin by calendar year and cost basis",
                         series="basis", highlight="Standard (pack-adjusted) — primary", fmt="{:.1%}", height=340)
    fig.update_xaxes(dtick=1, tickformat="d")
    visual("fin_bases", "Which cost basis, and does the answer change with it?",
           f"Finance's <b>standard_unit_cost</b> is the primary basis (budget). Divided by pack_size it gives {pct(cur['gross_margin_pct'])}; left unadjusted it gives "
           f"{pct(cur['gross_margin_standard_unadjusted_pct'])}; AP's landed cost gives {pct(landed_margin)}. The level differs; the {year} direction does not.",
           fig, a[["year", "gross_margin_pct", "gross_margin_standard_unadjusted_pct", "landed_gross_margin_pct"]],
           caveat="Pack-level standard cost is an evidence-based assumption pending Finance/AP confirmation.")

    cat = agg(scope_year, ["product_category"]).sort_values("gross_margin", ascending=False)
    visual("fin_cat", "Which categories make the margin?",
           f"{cat.iloc[0]['product_category']} leads at {pct(cat.iloc[0]['gross_margin'])}; {cat.iloc[-1]['product_category']} trails at {pct(cat.iloc[-1]['gross_margin'])} "
           f"while contributing {usd(cat.iloc[-1]['net_sales'], 2)} of sales. Mix shift toward the low-margin categories explains part of the margin slide.",
           swd.bar_ranked(cat, "product_category", "gross_margin", f"{cat.iloc[0]['product_category']} earns the richest margin; {cat.iloc[-1]['product_category']} the thinnest ({year})",
                          "Standard gross margin by category; hover for $", fmt="{:.1%}", label_all=True, height=280), cat)

    cov = a[["year", "standard_cost_coverage_pct", "net_sales", "standard_costed_net_sales"]].copy()
    cov["uncosted_sales"] = cov["net_sales"] - cov["standard_costed_net_sales"]
    cov["year"] = cov["year"].astype(str)
    visual("fin_cov", "How much of sales has no standard cost?",
           f"{pct(cur['standard_cost_coverage_pct'], 2)} of {year} events carry a standard cost; {usd(cur['net_sales'] - cur['standard_costed_net_sales'], 2)} of sales is "
           f"uncosted and excluded from the margin denominator (never from sales). The data contract asks for a cost on every line.",
           swd.bar_ranked(cov, "year", "uncosted_sales", "Uncosted sales by year", "Net sales on rows with no standard_unit_cost", fmt="${:,.0f}", label_all=True, height=240), cov)

    ox = pd.DataFrame({"item": ["Gross profit (known stores)", "Store opex as ANNUAL", "Store opex if monthly (x12)"],
                       "usd": [gp_known, opex_annual, opex_annual * 12]})
    visual("fin_opex", "Store opex: annual or monthly? We say annual.",
           f"Read as annual, direct store cost is {usd(opex_annual, 2)} ({opex_annual / cur['net_sales']:.0%} of sales) and {covered_annual}/{len(sy_all)} stores cover it from gross "
           f"profit. Read as monthly it would be {usd(opex_annual * 12, 1)} — {opex_annual * 12 / gp_known:.0f}x gross profit, with only {covered_monthly} stores covering it. "
           f"Annual is the only reading consistent with a going concern; monthly is kept as a labelled sensitivity.",
           swd.bar_ranked(ox, "item", "usd", "The monthly reading would dwarf gross profit; annual is the credible one", f"{year}, stores with sales", fmt="${:,.0f}",
                          label_all=True, highlight="Store opex as ANNUAL", height=240), ox)

    cr = agg(scope_year, ["product_category", "region_name"])
    piv = cr.pivot(index="product_category", columns="region_name", values="gross_margin")
    visual("fin_heat", "Where is margin made: category × region",
           "Same shared formula in every cell; the darkest column is the region to learn from.",
           swd.heatmap(piv, f"Gross margin by category × region ({year})", "Hover for event count", counts=cr.pivot(index="product_category", columns="region_name", values="events"), height=320), cr)


# ============================================================================= 6. AP / Ops
def render_ap() -> None:
    pc = scope_year.groupby(["product_name", "product_category", "pack_size"], as_index=False).agg(
        standard=("standard_unit_cost", "mean"), landed=("landed_unit_cost", "mean"), events=("transaction_id", "count"))
    pc["ratio"] = pc["standard"] / pc["landed"]
    pack2 = pc.loc[pc["pack_size"] == 2, "product_name"].tolist()
    r1 = pc.loc[pc["pack_size"] == 1, "ratio"].median()
    r2 = pc.loc[pc["pack_size"] == 2, "ratio"].median()
    visual("ap_ratio", "How does what we paid (landed) compare with the budget cost (standard)?",
           f"For pack-size-1 products standard ≈ landed (median ratio {r1:.2f}). For pack-size-2 products the ratio is {r2:.2f}: standard cost is quoted per pack, "
           f"landed per unit. That is why the model divides standard cost by pack_size before computing margin.",
           swd.scatter_points(pc, "landed", "ratio", "product_name", "Pack-size-2 products carry a standard cost about twice their landed cost", "x = average landed unit cost $; y = standard ÷ landed",
                              highlight=pack2, x_title="Average landed unit cost, $", y_title="standard_unit_cost ÷ landed_unit_cost", y_fmt=".2f",
                              hover_extra=["product_category", "pack_size"], y_ref=1.0, height=380), pc)

    cat = agg(scope_year, ["product_category"]).sort_values("landed_margin", ascending=False)
    visual("ap_cat", "Margin on what we actually paid, by category",
           f"On landed cost, {cat.iloc[0]['product_category']} earns {pct(cat.iloc[0]['landed_margin'])} and {cat.iloc[-1]['product_category']} {pct(cat.iloc[-1]['landed_margin'])}. "
           f"Compare with the Finance tab: the ranking is the same, the level is lower.",
           swd.bar_ranked(cat, "product_category", "landed_margin", f"Landed-cost margin by category ({year})", "landed gross profit ÷ net sales", fmt="{:.1%}", label_all=True, height=280), cat)

    costed = scope[scope["standard_cost_of_sales"].notna()]
    m = scope.groupby("month_start", as_index=False).agg(landed_cost=("landed_cost_of_sales", "sum"), qty=("quantity", "sum"))
    mc = costed.groupby("month_start", as_index=False).agg(std_cost=("standard_cost_of_sales", "sum"), qty_costed=("quantity", "sum"))
    m = m.merge(mc, on="month_start", how="left")
    m["Standard cost per unit (pack-adjusted)"] = m["std_cost"] / m["qty_costed"]
    m["Landed cost per unit"] = m["landed_cost"] / m["qty"]
    ml = m.melt(id_vars="month_start", value_vars=["Standard cost per unit (pack-adjusted)", "Landed cost per unit"], var_name="basis", value_name="usd")
    gap_last = m.iloc[-1]["Standard cost per unit (pack-adjusted)"] / m.iloc[-1]["Landed cost per unit"] - 1
    visual("ap_trend", "Did landed cost move away from standard in 2022?",
           f"Average cost per unit on the two bases tracked closely until 2022; by {m.iloc[-1]['month_start']:%b %Y} standard is {gap_last:+.1%} vs landed. "
           f"That divergence is the margin gap AP sees and Finance does not.",
           swd.line_trend(ml, "month_start", "usd", "Standard and landed cost per unit diverge in 2022", "Average cost per unit sold, by month", series="basis",
                          highlight="Landed cost per unit", fmt="${:,.2f}", height=340), m)

    miss = scope_year[scope_year["standard_cost_of_sales"].isna()].groupby("product_name", as_index=False).agg(rows=("transaction_id", "count"), sales=("net_sales", "sum"))
    visual("ap_missing", "Which lines have no standard cost at all?",
           f"{int(miss['rows'].sum()):,} {year} lines ({usd(miss['sales'].sum(), 2)} of sales) have no standard_unit_cost; they still carry a landed cost. These are the rows AP can cost for Finance.",
           swd.bar_ranked(miss, "product_name", "rows", f"Lines missing a standard cost, by product ({year})", "Count of events", label_all=True, height=300), miss)

    ret = agg(scope_year, ["product_category"])
    ret["return_rate"] = ret["returns"] / ret["events"]
    visual("ap_returns", "Where are returns and adjustments concentrated?",
           f"{pct(ret['returns'].sum() / ret['events'].sum())} of {year} lines are negative-quantity; {ret.sort_values('return_rate').iloc[-1]['product_category']} has the highest rate. "
           f"The source gives no reason code or link to the original sale — asked for in the data contract.",
           swd.bar_ranked(ret, "product_category", "return_rate", f"Return / adjustment line rate by category ({year})", "negative-quantity lines ÷ all lines", fmt="{:.1%}", label_all=True, height=260), ret)


# ============================================================================= 7. sales
def render_sales() -> None:
    mo = scope.groupby("month_start", as_index=False).agg(net_sales=("net_sales", "sum"), quantity=("quantity", "sum"), events=("transaction_id", "count"))
    mo["yoy_pct"] = mo["net_sales"] / mo["net_sales"].shift(12) - 1
    last = mo.iloc[-1]
    visual("sales_month", "How are monthly sales trending, and what is the YoY?",
           f"{last['month_start']:%b %Y}: {usd(last['net_sales'], 2)}, {last['yoy_pct']:+.1%} vs the same month a year earlier. December is the peak every year; "
           f"the trough is August. The audit CSV carries YoY for every month.",
           swd.line_trend(mo, "month_start", "net_sales", f"Latest month {last['yoy_pct']:+.1%} YoY; every December is the year's peak", "Net sales by month, scope regions/categories",
                          fmt="${:,.0f}", height=340), mo)

    pr = agg(scope_year, ["product_name"]).sort_values("net_sales", ascending=False)
    visual("sales_products", "Which products sell the most?",
           f"{pr.iloc[0]['product_name']} leads with {usd(pr.iloc[0]['net_sales'], 2)} ({pr.iloc[0]['net_sales'] / pr['net_sales'].sum():.0%} of sales). "
           f"The top three are {', '.join(pr.head(3)['product_name'])}.",
           swd.bar_ranked(pr, "product_name", "net_sales", f"{pr.iloc[0]['product_name']} is the sales leader ({year})", "Net sales by product", fmt="${:,.0f}", label_all=True, height=420), pr)

    ry = agg(scope[scope["year"].isin([year - 1, year])], ["region_name", "year"])
    piv = ry.pivot(index="region_name", columns="year", values="net_sales")
    if year - 1 in piv.columns and year in piv.columns:
        piv["change"] = piv[year] - piv[year - 1]
        piv["change_pct"] = piv[year] / piv[year - 1] - 1
        rr = piv.reset_index()
        rr.columns = [str(c) for c in rr.columns]
        visual("sales_region", "Which regions grew, and which shrank?",
               f"{rr.sort_values('change').iloc[-1]['region_name']} added {usd(rr['change'].max(), 2)}; {rr.sort_values('change').iloc[0]['region_name']} "
               f"{'lost' if rr['change'].min() < 0 else 'added only'} {usd(abs(rr['change'].min()), 2)} ({rr['change_pct'].min():+.1%}).",
               swd.bar_ranked(rr, "region_name", "change", f"Net sales change {year - 1} → {year} by region", "$ change; hover for %", fmt="${:,.0f}", label_all=True, height=240), rr)

    asp = scope.groupby("year", as_index=False).agg(net_sales=("net_sales", "sum"), quantity=("quantity", "sum"))
    asp["asp"] = asp["net_sales"] / asp["quantity"]
    fig = swd.line_trend(asp, "year", "asp", f"Average selling price ${asp.iloc[-1]['asp']:.2f} in {years[-1]}", "Net sales ÷ net quantity, by year", fmt="${:,.2f}", height=260)
    fig.update_xaxes(dtick=1, tickformat="d")
    step = f"{asp.iloc[-1]['asp'] / asp.iloc[-2]['asp'] - 1:+.1%}" if len(asp) > 1 else "n/a"
    visual("sales_asp", "Talk about price: what is happening to the average selling price?",
           f"ASP moved from ${asp.iloc[0]['asp']:.2f} to ${asp.iloc[-1]['asp']:.2f} across {years[0]}–{years[-1]}; the latest step is {step}. "
           f"Derived price metrics: price/mix effect (Management tab), sales per event, sales per pack-equivalent (provisional).", fig, asp)

    ev = pd.DataFrame({"metric": ["Net sales per event", "Return / adjustment line rate", "Colliding IDs resolved"],
                       "value": [cur["net_sales"] / cur["transaction_count"], cur["return_or_adjustment_count"] / cur["transaction_count"], flow["colliding_ids"]]})
    with st.expander("**Sales-ops hygiene: sales per event, returns, collisions**", expanded=False):
        c = st.columns(3)
        c[0].markdown(swd.tile("Net sales per event", f"${cur['net_sales'] / cur['transaction_count']:.2f}", f"{int(cur['transaction_count']):,} events in {year}"), unsafe_allow_html=True)
        c[1].markdown(swd.tile("Return / adjustment line rate", pct(cur["return_or_adjustment_count"] / cur["transaction_count"]), f"{int(cur['return_or_adjustment_count']):,} negative-quantity lines"), unsafe_allow_html=True)
        c[2].markdown(swd.tile("Colliding transaction IDs", f"{flow['colliding_ids']:,}", "newest ingested_at kept; older to triage", True), unsafe_allow_html=True)
        st.download_button("Audit CSV", ev.to_csv(index=False).encode(), "sales_hygiene.csv", "text/csv", key="csv_sales_hyg")


# ============================================================================= 8. stores
def render_stores() -> None:
    pool = sy_all[sy_all["region_name"].isin(sel_regions)].copy()
    pool["label"] = pool["store_name"] + ", " + pool["state_code"] + " (#" + pool["store_key"].astype(str) + ")"
    pool = pool.sort_values("net_sales", ascending=False)
    pick = st.selectbox("Store", pool["label"].tolist(), key="store_pick")
    s = pool[pool["label"] == pick].iloc[0]
    short = pick.split(" (#")[0]
    rank = int((pool["net_sales"] > s["net_sales"]).sum() + 1)
    peers = pool[pool["store_type"] == s["store_type"]]
    c = st.columns(5)
    c[0].markdown(swd.tile("Net sales", usd(s["net_sales"], 3), f"rank {rank} of {len(pool)}" + (f" · {s['net_sales_yoy_pct']:+.1%} YoY" if pd.notna(s["net_sales_yoy_pct"]) else "")), unsafe_allow_html=True)
    c[1].markdown(swd.tile("Gross margin", pct(s["gross_margin_pct"]), f"peer median ({s['store_type'].strip()}): {pct(peers['gross_margin_pct'].median())}",
                           s["gross_margin_pct"] >= peers["gross_margin_pct"].median()), unsafe_allow_html=True)
    c[2].markdown(swd.tile("Net sales / sqft", f"${s['net_sales_per_sqft']:.2f}" if pd.notna(s["net_sales_per_sqft"]) else "n/a",
                           f"{s['store_sqft']:,.0f} sqft · peer median ${peers['net_sales_per_sqft'].median():.2f}"), unsafe_allow_html=True)
    c[3].markdown(swd.tile("Gross profit less annual opex", usd(s["gross_profit"] - s["direct_store_operating_costs"], 3), f"opex {usd(s['direct_store_operating_costs'], 3)} (annual reading)",
                           (s["gross_profit"] - s["direct_store_operating_costs"]) >= 0), unsafe_allow_html=True)
    c[4].markdown(swd.tile("Store", f"{s['store_type'].strip()}", f"{s['region_name']} · {s['state_code']} · {int(s['transaction_count']):,} events"), unsafe_allow_html=True)

    sk = int(s["store_key"])
    sm = scope.groupby(["store_key", "store_type", "month_start"], as_index=False).agg(net_sales=("net_sales", "sum"), gross_profit=("gross_profit", "sum"))
    mine = sm[sm["store_key"] == sk][["month_start", "net_sales"]].assign(series=short)
    peer_med = sm[sm["store_type"] == s["store_type"]].groupby("month_start", as_index=False)["net_sales"].median().assign(series=f"{s['store_type'].strip()} peer median")
    both = pd.concat([mine, peer_med])
    visual("store_trend", "How does this store track against its peers month by month?",
           f"The accent line is {short}; grey is the median {s['store_type'].strip()} store. A persistent gap is structure (size, location); a one-off spike is an event worth asking the store about.",
           swd.line_trend(both, "month_start", "net_sales", f"{short} vs peer median, monthly net sales", "All years in scope", series="series", highlight=short, fmt="${:,.0f}", height=340), both)

    mix_store = agg(scope_year[scope_year["store_key"] == sk], ["product_category"]).set_index("product_category")
    mix_all = agg(scope_year, ["product_category"]).set_index("product_category")
    piv = pd.DataFrame({"This store": mix_store["gross_margin"], "All stores": mix_all["gross_margin"]}).T
    visual("store_mix", "Which categories does this store do better or worse than the company?",
           f"Row 1 is this store, row 2 the company. Cells darker in row 1 than row 2 are the store's strengths; the store sells {len(mix_store)} of {len(mix_all)} categories.",
           swd.heatmap(piv, f"Gross margin by category: this store vs all stores ({year})", "", height=200), piv.reset_index())

    own = sm[sm["store_key"] == sk].copy()
    own["z"] = (own["net_sales"] - own["net_sales"].mean()) / (own["net_sales"].std() or 1)
    own["label"] = own["month_start"].astype(str).str[:7]
    flagged = own.loc[own["z"].abs() > 2, "label"].tolist()
    visual("store_outliers", "Which months broke this store's own pattern?",
           f"{len(flagged)} month(s) sit more than two standard deviations from the store's own mean: {', '.join(flagged) or 'none'}. Decembers are expected; anything else deserves a question.",
           swd.scatter_points(own, "month_start", "net_sales", "label", f"{short}: months outside ±2σ of its own history", "Orange = flagged month",
                              highlight=flagged, highlight_color=swd.WARN, x_title="Month", y_title="Net sales, $", height=300), own)


# ============================================================================= 9. analysis (the nine questions + outliers)
def render_analysis() -> None:
    st.caption(f"Scope: {filters_text}. Change it in the left pane.")
    if scope_year.empty:
        st.warning("No events in this scope.")
        return

    cr = agg(scope_year, ["product_category", "region_name"])
    cs = agg(scope_year, ["product_category", "state_code"])
    best_state = cs.sort_values("gross_profit", ascending=False).groupby("product_category").head(1)
    best_region = cr.sort_values("gross_margin", ascending=False).groupby("product_category").head(1)
    lead = best_state["state_code"].mode().iloc[0]
    top_region = best_region["region_name"].mode().iloc[0]
    thin_cat = cr.groupby("product_category")["gross_margin"].mean().idxmin()
    piv = cr.pivot(index="product_category", columns="region_name", values="gross_margin")
    visual("q_cat_region", "Which product category is profitable where?",
           f"In {year} every category earned positive gross profit in every region. <b>{top_region}</b> has the highest margin in "
           f"{int((best_region['region_name'] == top_region).sum())} of {len(best_region)} categories, and <b>{lead}</b> leads gross-profit dollars in "
           f"{int((best_state['state_code'] == lead).sum())} of {len(best_state)}. <b>{thin_cat}</b> is the thin category everywhere.",
           swd.heatmap(piv, f"{top_region} out-earns the other regions in {int((best_region['region_name'] == top_region).sum())} of {len(best_region)} categories ({year})",
                       "Gross margin by category × region; hover for event count", counts=cr.pivot(index="product_category", columns="region_name", values="events"), height=330), cr)

    sy = store_year[(store_year["year"] == year) & (store_year["store_sqft"] > 0) & store_year["region_name"].isin(sel_regions)].copy()
    sy["quartile"] = pd.qcut(sy["store_sqft"], 4, labels=["Q1 smallest", "Q2", "Q3", "Q4 largest"])
    q = sy.groupby("quartile", observed=True).agg(stores=("store_key", "count"), avg_sqft=("store_sqft", "mean"), avg_sales=("net_sales", "mean"), net_sales=("net_sales", "sum"),
                                                  gross_profit=("gross_profit", "sum"), costed=("standard_costed_net_sales", "sum"), sqft=("store_sqft", "sum")).reset_index()
    q["gross_margin"] = q["gross_profit"] / q["costed"]
    q["sales_per_sqft"] = q["net_sales"] / q["sqft"]
    big, small = q.iloc[-1], q.iloc[0]
    top_sqft = sy.sort_values("net_sales_per_sqft", ascending=False).head(3)["store_name"].tolist()

    def quartile_table():
        st.dataframe(q[["quartile", "stores", "avg_sqft", "avg_sales", "sales_per_sqft", "gross_margin"]], hide_index=True, width="stretch",
                     column_config={"avg_sqft": st.column_config.NumberColumn("avg sqft", format="%,.0f"), "avg_sales": st.column_config.NumberColumn("avg net sales / store", format="$%,.0f"),
                                    "sales_per_sqft": st.column_config.NumberColumn("net sales / sqft", format="$%.2f"), "gross_margin": st.column_config.NumberColumn("gross margin", format="percent")})
    visual("q_size", "Are larger stores performing better than smaller stores?",
           f"<b>They sell more, not more profitably.</b> Area correlates with net sales (r = {sy['store_sqft'].corr(sy['net_sales']):.2f}); the largest quartile averages "
           f"${big['avg_sales']:,.0f} per store vs ${small['avg_sales']:,.0f}, with higher sales per sqft (${big['sales_per_sqft']:.2f} vs ${small['sales_per_sqft']:.2f}). "
           f"But margin is <b>{pct(big['gross_margin'])}</b> vs <b>{pct(small['gross_margin'])}</b>. Size buys volume, not margin.",
           swd.scatter_points(sy, "store_sqft", "net_sales_per_sqft", "store_name", f"Bigger stores sell more per square foot, but margin does not follow ({year})",
                              "Each point is a store; accent = top 3 sales per sqft; hover for margin", highlight=top_sqft, x_title="Store area, sqft", y_title="Net sales per sqft, $",
                              hover_extra=["gross_margin_pct", "store_type", "state_code"], x_ref=sy["store_sqft"].median(), y_ref=sy["net_sales_per_sqft"].median()), sy,
           note="Dotted lines are medians. Louisville (store 200) has 0 sqft and is excluded from area ratios, not from sales.", before=quartile_table)

    py = product_year[product_year["product_category"].isin(sel_categories)]
    wide = py.pivot(index="product_name", columns="year", values="net_sales")
    declines = wide.diff(axis=1).iloc[:, 1:]
    always_down = wide.index[(declines < 0).all(axis=1)].tolist()
    last_down = wide.index[declines.iloc[:, -1] < 0].tolist()
    idx = wide.div(wide.iloc[:, 0], axis=0)
    weakest = idx.iloc[:, -1].idxmin()
    idx_long = idx.reset_index().melt(id_vars="product_name", var_name="year", value_name="index")
    n_below = int((idx.iloc[:, -1] < 1).sum())
    fig = swd.line_trend(idx_long, "year", "index", (f"Every product is above its {years[0]} level; {weakest} grew least" if n_below == 0 else
                                                     f"{n_below} of {len(idx)} products are below their {years[0]} level; {weakest} is weakest"),
                         f"Net sales indexed to {years[0]} = 1.00", series="product_name", highlight=weakest, fmt="{:.2f}", height=400, label_all=False)
    fig.update_xaxes(dtick=1, tickformat="d")
    visual("q_favour", "Has any product fallen out of favour so that we lose sales consistently?",
           (f"<b>No.</b> No product declined in every year {years[0]}–{years[-1]}, and {len(wide) - len(last_down)} of {len(wide)} grew in {years[-1]}. "
            if not always_down else f"<b>Yes:</b> {', '.join(always_down)} declined every year. ")
           + f"The slowest is <b>{weakest}</b> at {idx.iloc[:, -1].min():.0%} of its {years[0]} sales"
           + (f"; down in {years[-1]}: {', '.join(last_down)}." if last_down else ". The 2020 dip was broad and recovered everywhere."), fig, py)

    pp_ = agg(scope_year, ["product_category", "product_name"])
    pp_["cost_share"] = pp_["cost"] / pp_["costed_net_sales"]
    best = pp_.sort_values("gross_margin", ascending=False).iloc[0]
    visual("q_cost_margin", "Where has our cost been lowest but margin highest?",
           f"Cost and margin are one ratio (margin = 1 − cost ÷ sales), so read cost <i>per sales dollar</i>. <b>{best['product_name']}</b> spends {pct(best['cost_share'])} of each "
           f"sales dollar on standard cost and earns {pct(best['gross_margin'])} on {usd(best['net_sales'], 2)} in {year}. Absolute lowest cost belongs to the small-volume lines — a different question.",
           swd.scatter_points(pp_, "cost", "gross_margin", "product_name", f"{best['product_name']} converts the least cost per sales dollar into the highest margin ({year})",
                              "x = standard cost of sales $; y = gross margin; bubble = net sales", highlight=[best["product_name"]], size="net_sales", x_title="Standard cost of sales, $",
                              y_title="Gross margin", y_fmt=".1%", hover_extra=["product_category", "cost_share"], x_ref=pp_["cost"].median(), y_ref=pp_["gross_margin"].median()), pp_,
           caveat="Standard cost is pack-adjusted and pending Finance confirmation.")

    low = pp_.nsmallest(max(3, len(pp_) // 4), "quantity")
    low_best = low.sort_values("gross_margin", ascending=False).iloc[0]
    lowest = pp_.nsmallest(1, "quantity").iloc[0]
    visual("q_qty_margin", "Which product sold the lowest quantity but gave us the highest margin?",
           f"Lowest quantity in {year}: <b>{lowest['product_name']}</b> ({lowest['quantity']:,.0f} units, {pct(lowest['gross_margin'])}) — low volume but <i>not</i> high margin. "
           f"In the low-volume quartile, <b>{low_best['product_name']}</b> pairs few units ({low_best['quantity']:,.0f}) with {pct(low_best['gross_margin'])} margin "
           f"({usd(low_best['gross_profit'], 2)} gross profit): the 'small but rich' line to protect.",
           swd.scatter_points(pp_, "quantity", "gross_margin", "product_name", f"{low_best['product_name']}: few units, high margin ({year})",
                              "x = net quantity (log); y = gross margin; bubble = gross profit $", highlight=[low_best["product_name"], lowest["product_name"]], size="gross_profit",
                              x_title="Net quantity sold", y_title="Gross margin", y_fmt=".1%", log_x=True, hover_extra=["product_category", "net_sales"], y_ref=pp_["gross_margin"].median()), pp_)

    stt = agg(scope_year, ["store_type"])
    stt["stores"] = stt["store_type"].map(scope_year.groupby("store_type")["store_key"].nunique())
    stt["label"] = stt["store_type"].str.strip() + " (" + stt["stores"].astype(str) + ")"
    city = stt[stt["store_type"].str.strip() == "City"]
    thin = stt[stt["stores"] <= 2]
    multi = stt[(stt["stores"] >= 3) & (stt["store_type"].str.strip() != "City")]
    gap_lo = (city["gross_margin"].iloc[0] - multi["gross_margin"].max()) * 100 if len(city) and len(multi) else float("nan")
    gap_hi = (city["gross_margin"].iloc[0] - multi["gross_margin"].min()) * 100 if len(city) and len(multi) else float("nan")
    visual("q_type", "Is there a correlation between store type and profitability in general?",
           f"<b>A pattern, not a proven correlation.</b> City stores ({int(city['stores'].iloc[0]) if len(city) else 0}) earn {pct(city['gross_margin'].iloc[0]) if len(city) else 'n/a'}; "
           f"the other multi-store types ({', '.join(multi['store_type'].str.strip())}) sit {gap_lo:.0f}–{gap_hi:.0f} points lower. {len(thin)} of {len(stt)} types have one or two stores, "
           f"so their margins are single-store facts. Store type is a slicer to investigate, not a cause.",
           swd.bar_ranked(stt, "label", "gross_margin", f"City stores lead on margin; most other types are too small to judge ({year})", "Gross margin by store type (store count in brackets)",
                          fmt="{:.1%}", label_all=True, highlight=city["label"].iloc[0] if len(city) else None, height=340), stt)

    short = {"Consolidated Government": "Consol. Govt", "Metropolitan Government": "Metro Govt", "Unified Government": "Unified Govt"}
    ct = agg(scope_year, ["product_category", "store_type"])
    ct["store_type"] = ct["store_type"].str.strip().replace(short)
    ct = ct[ct["events"] >= 30]
    order = ct.groupby("store_type")["events"].sum().sort_values(ascending=False).index
    piv = ct.pivot(index="product_category", columns="store_type", values="gross_margin").reindex(columns=order)
    gap = (piv.max(axis=1) - piv.min(axis=1)).sort_values(ascending=False)
    city_best = int((piv.idxmax(axis=1) == "City").sum()) if "City" in piv.columns else 0
    visual("q_cat_type", "Is there a correlation between store type and profitability for each product category?",
           f"City stores have the best margin in <b>{city_best} of {len(piv)}</b> categories; the premium is widest for <b>{gap.index[0]}</b> ({gap.iloc[0] * 100:.0f} points) and narrowest "
           f"for <b>{gap.index[-1]}</b> ({gap.iloc[-1] * 100:.0f}). <b>{piv.mean(axis=1).idxmin()}</b> is thin in every store type. Cells under 30 events are hidden.",
           swd.heatmap(piv, f"City stores lead margin in {city_best} of {len(piv)} categories; the gap is largest in {gap.index[0]} ({year})",
                       "Gross margin by category × store type (≥ 30 events), columns by volume", counts=ct.pivot(index="product_category", columns="store_type", values="events").reindex(columns=order), height=330), ct)

    pm = agg(scope, ["product_name", "month_number"])
    pm["index"] = pm["net_sales"] / pm.groupby("product_name")["net_sales"].transform("mean")
    piv = pm.pivot(index="product_name", columns="month_number", values="index")
    piv.columns = [MONTHS[m - 1] for m in piv.columns]
    amp = (piv.max(axis=1) - piv.min(axis=1)).sort_values(ascending=False)
    visual("q_season", "Is there a correlation between time of year and certain products' sales?",
           f"<b>Yes, strongest for big-ticket lines.</b> Most products peak in <b>{piv.idxmax(axis=1).mode().iloc[0]}</b> and trough in <b>{piv.idxmin(axis=1).mode().iloc[0]}</b>. "
           f"The swing is largest for <b>{amp.index[0]}</b> ({piv.loc[amp.index[0]].max():.2f}× its average in the best month) and smallest for <b>{amp.index[-1]}</b>. "
           f"Four cycles and first-of-month dating: a strong pattern, not yet a forecast.",
           swd.heatmap(piv.loc[amp.index], f"December lifts everything; {amp.index[0]} swings the most", "Monthly net sales ÷ product's monthly average, all years in scope",
                       fmt="{:.2f}", height=460, zmin=0.5, zmax=2.0), pm)

    products = sorted(scope["product_name"].unique())
    default_prod = amp.index[0] if amp.index[0] in products else products[0]

    def geo_controls():
        c1, c2 = st.columns(2)
        c1.selectbox("Product", products, index=products.index(default_prod), key="prod")
        c2.radio("Level", ["State", "Store (city-name proxy)"], horizontal=True, key="level")
    prod_choice = st.session_state.get("prod", default_prod)
    level = st.session_state.get("level", "State")
    col = "state_code" if level == "State" else "store_name"
    spm = agg(scope[scope["product_name"] == prod_choice], [col, "month_number"])
    keep = spm.groupby(col)["net_sales"].sum().sort_values(ascending=False).head(12).index
    spm = spm[spm[col].isin(keep)]
    spm["index"] = spm["net_sales"] / spm.groupby(col)["net_sales"].transform("mean")
    piv = spm.pivot(index=col, columns="month_number", values="index").reindex(keep)
    piv.columns = [MONTHS[m - 1] for m in piv.columns]
    visual("q_season_geo", "Is there a correlation between time of year and a product's sales in certain states or cities?",
           "States are a clean hierarchy level; the file has no city field, so <i>store name</i> is the closest proxy. If the December lift is similar in every row, the seasonality is national, not local.",
           swd.heatmap(piv, f"{prod_choice}: seasonality by {level.lower()} (top 12 by sales)", "Monthly net sales ÷ that row's monthly average; same scale as above",
                       fmt="{:.2f}", height=430, zmin=0.5, zmax=2.0, counts=spm.pivot(index=col, columns="month_number", values="events").reindex(keep)), spm, before=geo_controls)

    # outliers ---------------------------------------------------------------------------------
    def outlier_controls():
        c1, c2, c3 = st.columns(3)
        c1.selectbox("$ measure", ["net_sales", "gross_profit", "gross_profit_per_sqft"], format_func=lambda s: s.replace("_", " "), key="measure")
        c2.radio("Outlier rule", ["Against peers in the same month", "Against the store's own history"], key="rule")
        c3.slider("Flag when |z| exceeds", 2.0, 4.0, 3.0, 0.5, key="zcut")
    measure = st.session_state.get("measure", "net_sales")
    rule = st.session_state.get("rule", "Against peers in the same month")
    z_cut = st.session_state.get("zcut", 3.0)
    sm = agg(scope, ["store_key", "store_name", "state_code", "region_name", "store_type", "store_sqft", "month_start"])
    sm["gross_profit_per_sqft"] = sm["gross_profit"] / sm["store_sqft"].replace(0, np.nan)
    sm["store"] = sm["store_name"] + ", " + sm["state_code"]
    grp = "month_start" if rule.startswith("Against peers") else "store_key"
    g = sm.groupby(grp)[measure]
    sm["z"] = (sm[measure] - g.transform("mean")) / g.transform("std").replace(0, np.nan)
    out = sm[sm["z"].abs() > z_cut]
    hi = out[out["z"] > 0].groupby("store")["z"].count().sort_values(ascending=False)
    lo = out[out["z"] < 0].groupby("store")["z"].count().sort_values(ascending=False)
    sm_plot = sm.dropna(subset=[measure]).copy()
    sm_plot["label"] = sm_plot["store"] + " " + sm_plot["month_start"].astype(str).str[:7]
    flagged = sm_plot.loc[sm_plot["z"].abs() > z_cut, "label"].tolist()
    visual("q_store_outliers", "Scatter: $ by time for each store — which stores are outliers?",
           (f"<b>{len(out):,}</b> store-months exceed |z| {z_cut:.1f} on {measure.replace('_', ' ')}. "
            + (f"Persistently <b>above</b> peers: {', '.join(f'{k} ({v} months)' for k, v in hi.head(5).items())}. " if len(hi) else "")
            + (f"Persistently <b>below</b>: {', '.join(f'{k} ({v})' for k, v in lo.head(5).items())}. " if len(lo) else "")
            + ("Peer rule finds the structurally big winners; " if grp == "month_start" else "Own-history rule finds months that broke a store's pattern; ")
            + "gross profit per sqft removes the size advantage."),
           swd.scatter_points(sm_plot, "month_start", measure, "label", f"Store-months outside |z| {z_cut:.1f}: {len(flagged)} of {len(sm_plot):,}",
                              f"{measure.replace('_', ' ')} per store per month; orange = flagged ({rule.lower()})", highlight=flagged, highlight_color=swd.WARN,
                              label_highlight=False, x_title="Month", y_title=measure.replace("_", " ") + ", $", hover_extra=["store_type", "region_name", "z"], height=460),
           out.sort_values("z", ascending=False), before=outlier_controls)

    def hier_controls():
        st.radio("Product hierarchy level", ["Category", "Product"], horizontal=True, key="hier")
    hier = st.session_state.get("hier", "Category")
    hcol = "product_category" if hier == "Category" else "product_name"
    pm2 = agg(scope, [hcol, "month_start"])
    pmeasure = "gross_profit" if measure == "gross_profit_per_sqft" else measure
    growth = pm2.groupby(hcol).apply(lambda d: d.sort_values("month_start")[pmeasure].tail(12).sum() / max(d.sort_values("month_start")[pmeasure].head(12).sum(), 1e-9) - 1,
                                     include_groups=False).sort_values(ascending=False)
    visual("q_hier", "Scatter by product hierarchy: which categories or products are pulling ahead over time?",
           f"Last 12 months in scope vs the first 12: <b>{growth.index[0]}</b> grew most ({growth.iloc[0]:+.0%}) and <b>{growth.index[-1]}</b> least ({growth.iloc[-1]:+.0%}) on "
           f"{pmeasure.replace('_', ' ')}. Every line shows the December spike; the gap between lines is the mix story.",
           swd.line_trend(pm2, "month_start", pmeasure, f"{growth.index[0]} is the fastest-growing {hier.lower()} ({growth.iloc[0]:+.0%})", f"{pmeasure.replace('_', ' ')} per month by {hier.lower()}",
                          series=hcol, highlight=growth.index[0], fmt="${:,.0f}", height=440, label_all=hier == "Category"), pm2, before=hier_controls)


# ============================================================================= 10. roadmap & AI
def render_roadmap() -> None:
    road = pd.DataFrame([
        ("Data contract", "Line-level key and explicit unknown codes from upstream", "Removes the fingerprint workaround and the 99901 guesswork", "Low", "Upstream team"),
        ("Data contract", "One labelled grain per cost column; drop unit_cost", "Ends the pack-size inference for standard cost", "Low", "Finance / AP"),
        ("Modelling", "SCD Type 2 product and store dimensions", "Historical attribute truth once valid_from/valid_to arrive", "Medium", "Upstream effective dates"),
        ("Modelling", "Incremental staging with merge on the line key", "Daily loads without full reload; CDC-style lineage", "Medium", "Line key"),
        ("Modelling", "Periodic-snapshot fact for stock / store state", "Answers inventory and days-of-cover questions", "High", "New source feeds"),
        ("Metrics", "dbt Semantic Layer / MetricFlow definitions", "One governed formula set consumed by every BI tool", "Medium", "dbt Cloud or MetricFlow"),
        ("Metrics", "Confirmed store opex period and central cost allocation", "Move from gross profit to a defensible contribution and operating profit", "Low", "Store Finance / FP&A"),
        ("Quality", "dbt_utils and dbt_expectations tests; source freshness SLAs", "Richer assertions (distributions, recency) without hand-written SQL", "Low", "Package install"),
        ("Quality", "Profiling report per load (price/cost distributions)", "Catch drift before marts rebuild", "Medium", ""),
        ("Platform", "Deploy to Snowflake / BigQuery with the same dbt project", "Shared warehouse, scheduling, RBAC; DuckDB stays for local dev", "Medium", "Cloud account"),
        ("Platform", "CI with GitHub Actions: dbt build + dashboard AppTest on every PR", "Every change proves the pipeline and the app still work", "Low", "CI secrets"),
        ("Dashboard", "Row-level security per store and per team tab", "Store managers see their store; finance sees all", "Medium", "Auth provider"),
        ("Dashboard", "Forecasting on the monthly series (seasonal naive / Prophet)", "Turn the December pattern into a plan, with error bands", "Medium", "48+ months of data"),
        ("Dashboard", "PPT / Excel export per visual on the company template", "Same chart in the deck and the app, one click", "Low", "Template file"),
        ("AI", "LLM interpretation on an approved endpoint, grounded in METRIC_DICTIONARY.md", "Natural-language answers that use the agreed formulae", "Medium", "Approved model, budget"),
        ("AI", "Anomaly narratives pushed to teams (weekly digest)", "The outlier scatter becomes an alert, not a chart to remember to open", "Medium", "Scheduler + email/Teams"),
    ], columns=["Area", "Enhancement", "Why it matters", "Effort", "Depends on"])
    with st.expander("**Future enhancements**", expanded=True):
        st.dataframe(road, hide_index=True, width="stretch", height=600,
                     column_config={"Enhancement": st.column_config.TextColumn(width="large"), "Why it matters": st.column_config.TextColumn(width="large")})
    with st.expander("**Is there an AI inference widget? Yes — the Interpret button under every visual**", expanded=True):
        st.markdown(swd.prose(
            f"Every chart has an <b>Interpret</b> button. Current engine: <b>{ai.engine_label()}</b>. The offline interpreter writes deterministic sentences from the chart's "
            f"aggregate table (range, median, concentration, outliers, caveat) so the widget always works and no data leaves the machine. Set <code>AI_ENDPOINT</code>, "
            f"<code>AI_API_KEY</code> and optionally <code>AI_MODEL</code> to route the same payload to an approved OpenAI-compatible endpoint (Azure OpenAI, GitHub Models). "
            f"The payload is shown under each interpretation: question, action title, filters, caveat and at most {ai.MAX_ROWS} aggregated rows — never row-level data, SQL or credentials."),
            unsafe_allow_html=True)
        demo = agg(scope_year, ["product_category"])[["product_category", "net_sales", "gross_margin"]]
        payload = ai.build_payload("Demo: which categories make the margin?", "Demo interpretation", demo, filters_text)
        st.markdown(ai.interpret(payload))
        st.json(payload, expanded=False)


# ============================================================================= layout
SECTIONS = [render_solution, render_model, render_flow, render_management, render_finance, render_ap, render_sales, render_stores, render_analysis, render_roadmap]
requested = st.query_params.get("section")  # ?section=5 renders one section on its own (deep links, screenshots)
if requested and requested.isdigit() and 1 <= int(requested) <= len(SECTIONS):
    st.caption(f"Section {requested} of {len(SECTIONS)} ({SECTION_LABELS[int(requested) - 1]}) · remove `?section=` from the URL to see all tabs.")
    SECTIONS[int(requested) - 1]()
else:
    for tab, render in zip(st.tabs(SECTION_LABELS), SECTIONS):
        with tab:
            render()
