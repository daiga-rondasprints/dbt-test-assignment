"""Retail assignment dashboard: every question answered in words and with one chart.

Run from the repo root after `uv run dbt build`:
    uv run --group dashboard streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data  # noqa: E402
import swd  # noqa: E402

st.set_page_config(page_title="Retail performance story", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
      h2, h3 { color: #212529; }
      .modebar { display: none !important; }
      div[data-testid="stExpander"] details { border: 0; border-top: 1px solid #ECECEC; border-radius: 0; margin-top: 8px; }
      div[data-testid="stExpander"] summary p { font-size: 15px; color: #212529; }
      button[data-baseweb="tab"] p { font-size: 15px; }
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
product_year = load(data.product_year)()
store_year = load(data.store_year)()
events = load(data.events)()
scorecard = load(data.scorecard)()

usd = lambda v, d=1: f"{'-' if v < 0 else ''}${abs(v) / 1e6:,.{d}f}m"  # noqa: E731
pct = lambda v, d=1: f"{v * 100:,.{d}f}%"  # noqa: E731
pp = lambda v: f"{v * 100:+.1f} pp"  # noqa: E731


def margin(df: pd.DataFrame) -> pd.Series:
    return df["gross_profit"] / df["costed_net_sales"].replace(0, np.nan)


def agg(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = df.groupby(by, as_index=False).agg(net_sales=("net_sales", "sum"), gross_profit=("gross_profit", "sum"),
                                           costed_net_sales=("costed_net_sales", "sum"), cost=("standard_cost_of_sales", "sum"),
                                           quantity=("quantity", "sum"), events=("transaction_id", "count"))
    g["gross_margin"] = margin(g)
    return g


def show(fig, table: pd.DataFrame, key: str, note: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", key=f"chart_{key}")
    c1, c2 = st.columns([1, 5])
    c1.download_button("Audit CSV", table.to_csv(index=False).encode(), f"{key}.csv", "text/csv", key=f"csv_{key}")
    if note:
        c2.caption(note)


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
st.sidebar.caption(f"Source: `{data.DB.name}` dbt marts. Profit = **gross** profit on standard cost (pack-adjusted); "
                   "not net profit. Unknown product/store rows stay in company totals but are excluded from cross-cuts.")

known = events[(events["product_key"] != -1) & (events["store_key"] != -1)]
scope = known[known["region_name"].isin(sel_regions) & known["product_category"].isin(sel_categories)]
scope_year = scope[scope["year"] == year]
prior_year = scope[scope["year"] == year - 1]
scope_note = f"{year}; regions: {', '.join(sel_regions) if len(sel_regions) < len(regions) else 'all'}; " \
             f"categories: {', '.join(sel_categories) if len(sel_categories) < len(categories) else 'all'}"

st.markdown("## Retail performance: what the data is, how it flows, and what is working")
st.caption("One question, one answer, one chart per section. Every figure is read from the built dbt marts.")

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

SECTION_LABELS = ["1 · What is this data set?", "2 · Row flow, staging and the model", "3 · Business questions", "4 · Outliers: what to do more of"]


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


# ============================================================================= 1. the data set
def render_model() -> None:
    st.markdown(swd.answer("What is in the file?",
                           f"One CSV, {flow['source_rows']:,} rows, {years[0]}–{years[-1]}: one sales line per row with product and store attributes repeated on every row."),
                unsafe_allow_html=True)
    st.dataframe(glossary(), hide_index=True, width="stretch", height=810,
                 column_config={"Column in the file": st.column_config.TextColumn(width="medium"),
                                "What we understand": st.column_config.TextColumn(width="large"),
                                "How the model uses it": st.column_config.TextColumn(width="large")})

    c1, c2 = st.columns([1.3, 1])
    with c1:
        st.markdown(swd.answer("How many facts and dimensions?",
                               f"<b>1 event fact</b> ({flow['fact_rows']:,} rows) and <b>3 dimensions</b>: product {flow['dim_product_known']}+Unknown, "
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

    st.markdown(swd.answer("What happens to dirty data?",
                           f"Nothing is deleted. Colliding IDs: newest <code>ingested_at</code> version goes to the fact, the older one to "
                           f"<code>mart_data_quality_triage</code>. Unknown keys, returns and missing costs stay in the fact and are flagged "
                           f"({flow['triage_rows']:,} issue rows; rebuilt every run). <code>DATA_CONTRACT.md</code> states what we expect upstream."),
                unsafe_allow_html=True)
    tri = triage.copy()
    tri["label"] = tri["issue_code"].str.replace("_", " ").str.capitalize()
    show(swd.bar_ranked(tri, "label", "rows", "Older duplicate versions are the biggest triage category; nothing is deleted",
                        "Issue rows in mart_data_quality_triage (one row per older duplicate version)", label_all=True,
                        highlight="Duplicate transaction id"), tri, "triage")

# ============================================================================= 2. row flow & model
def render_flow() -> None:
    st.markdown(swd.answer(
        "How many rows did we start with, and how many were de-duplicated or sent to triage?",
        f"Start: <b>{flow['source_rows']:,}</b> CSV rows → persisted staging <b>{flow['staging_rows']:,}</b> (1:1, {flow['distinct_fingerprints']:,} unique "
        f"fingerprints) → version audit <b>{flow['version_rows']:,}</b> → fact <b>{flow['fact_rows']:,}</b>. The only rows removed are the "
        f"<b>{flow['excluded_versions']:,}</b> older versions of the {flow['colliding_ids']:,} transaction IDs that appeared twice. Triage lists "
        f"{flow['triage_rows']:,} issue rows, but those are flags on retained rows, not further removals."), unsafe_allow_html=True)
    stages = [("Raw CSV", flow["source_rows"], ["immutable extract", "data/raw"]),
              ("Persisted staging", flow["staging_rows"], ["DuckDB table, full replace", f"{flow['distinct_fingerprints']:,} unique fingerprints"]),
              ("Version audit", flow["version_rows"], ["every row ranked per transaction ID", "disposition recorded"]),
              ("fct_sales", flow["fact_rows"], ["1 row per transaction ID", "latest ingestion wins"])]
    branch = ("Excluded older versions", flow["excluded_versions"], [f"{flow['colliding_ids']:,} IDs × 2 versions", "kept in triage, not in the fact"])
    st.plotly_chart(swd.pipeline_flow(stages, branch, "Only older duplicate versions leave the pipeline; every other row reaches the fact",
                                      f"Row counts per layer. Triage also flags {flow['triage_rows']:,} issue rows on retained rows (unknown keys, returns, missing cost)."),
                    width="stretch", key="rowflow")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(swd.answer(
            "Is staging a persisted table at the raw-CSV level, and is re-running safe?",
            f"Yes. <code>stg_consolidated_transactions</code> is a DuckDB <b>table</b> (not a view) rebuilt by full replacement on every "
            f"<code>dbt build</code>; it is never appended to. Two consecutive builds both landed {flow['staging_rows']:,} rows, and three tests guard "
            f"it: staging row count = source row count, the row fingerprint is unique, and fact rows = selected audit versions. Re-running "
            f"cannot create duplicates. (It is a reproducible full reload, not incremental CDC — that would need the line key we asked for in "
            f"the contract.)"), unsafe_allow_html=True)
        st.markdown(swd.answer(
            "How many dimensions were derived, and how many rows?",
            f"Three: product {flow['dim_product']} rows ({flow['dim_product_known']} known + Unknown), store {flow['dim_store']} rows "
            f"({flow['dim_store_known']} known + Unknown), date {flow['dim_date']:,} rows ({flow['date_min']} to {flow['date_max']})."), unsafe_allow_html=True)
        st.markdown(swd.answer(
            "How many fact tables, and do we need aggregates?",
            f"One atomic fact, {flow['fact_rows']:,} rows. Yes to aggregates: six marts (annual, monthly, product, store, region, team KPI "
            f"scorecard) pre-compute the shared formulae so every team reads the same net sales and gross margin. They are convenience "
            f"tables; the fact remains the source of truth and this dashboard re-derives cross-cuts from it."), unsafe_allow_html=True)
    with c2:
        st.markdown(swd.answer(
            "With an event fact, must every query carry a date range?",
            "No — a sum over the whole fact is mathematically valid. But a business report always should: it fixes the period for YoY, "
            "keeps partial periods out, and lets the engine prune by <code>date_key</code>. The marts bake the calendar-year window in so "
            "consumers cannot forget it."), unsafe_allow_html=True)
        st.markdown(swd.answer(
            "Would we have a date dimension?",
            f"Yes, <code>dim_date</code>: {flow['dim_date']:,} days with year, quarter, month, day-of-week flags. The fact joins on an integer "
            f"<code>date_key</code>. Even though events sit on {flow['event_dates']} first-of-month dates, a full calendar lets month/quarter "
            f"roll-ups and seasonality work without special cases."), unsafe_allow_html=True)
        st.markdown(swd.answer(
            "What derived metrics do we have?",
            "Net sales; standard cost of sales (pack-adjusted); gross profit and gross margin; YoY change in $ and %; average selling price "
            "and a price/volume bridge; landed-cost and unadjusted-standard sensitivities; net sales, cost and gross profit per square "
            "foot; pack-equivalent quantity (provisional); return-line rate; cost coverage; store-cost scenarios. Full formulae in "
            "<code>METRIC_DICTIONARY.md</code> and below."), unsafe_allow_html=True)
    metrics = scorecard[scorecard["year"] == year][["team_view", "metric_code", "metric_value", "metric_unit", "metric_basis", "formula"]]
    with st.expander("Derived metric catalogue (mart_team_kpi_scorecard)", expanded=False):
        st.dataframe(metrics, hide_index=True, width="stretch")

# ============================================================================= 3. business questions
def render_questions() -> None:
    st.caption(f"Scope: {scope_note}. Change it in the left pane.")
    if scope_year.empty:
        st.warning("No events in this scope.")
        return

    # Q1 category profitable where ------------------------------------------------------------
    cr = agg(scope_year, ["product_category", "region_name"])
    cs = agg(scope_year, ["product_category", "state_code"])
    best_state = cs.sort_values("gross_profit", ascending=False).groupby("product_category").head(1)
    best_region = cr.sort_values("gross_margin", ascending=False).groupby("product_category").head(1)
    lead = best_state["state_code"].mode().iloc[0] if len(best_state) else "—"
    top_region = best_region["region_name"].mode().iloc[0]
    thin_cat = cr.groupby("product_category")["gross_margin"].mean().idxmin()
    st.markdown(swd.answer(
        "Which product category is profitable where?",
        f"In {year} every category earned positive gross profit in every region. <b>{top_region}</b> has the "
        f"highest margin in {int((best_region['region_name'] == top_region).sum())} of {len(best_region)} categories, "
        f"and <b>{lead}</b> leads gross-profit dollars in {int((best_state['state_code'] == lead).sum())} of {len(best_state)}. "
        f"<b>{thin_cat}</b> is the thin category everywhere ({pct(cr.loc[cr['product_category'] == thin_cat, 'gross_margin'].min())} at worst)."),
        unsafe_allow_html=True)
    piv = cr.pivot(index="product_category", columns="region_name", values="gross_margin")
    cnt = cr.pivot(index="product_category", columns="region_name", values="events")
    show(swd.heatmap(piv, f"{top_region} out-earns the other regions in {int((best_region['region_name'] == top_region).sum())} of {len(best_region)} categories ({year})",
                     "Gross margin by category × region; hover for event count", counts=cnt, height=330), cr, "cat_region")
    with st.expander("Same view by state (gross profit $ and margin)"):
        piv_s = cs.pivot(index="product_category", columns="state_code", values="gross_margin")
        st.plotly_chart(swd.heatmap(piv_s, f"Margin by category × state ({year})", "Blank = no cost-covered sales", height=330,
                                    counts=cs.pivot(index="product_category", columns="state_code", values="events")), width="stretch", key="cat_state")
        st.dataframe(best_state[["product_category", "state_code", "net_sales", "gross_profit", "gross_margin"]].round(3), hide_index=True, width="stretch")

    # Q2 larger stores ------------------------------------------------------------------------
    sy = store_year[(store_year["year"] == year) & (store_year["store_sqft"] > 0) & store_year["region_name"].isin(sel_regions)].copy()
    sy["quartile"] = pd.qcut(sy["store_sqft"], 4, labels=["Q1 smallest", "Q2", "Q3", "Q4 largest"])
    q = sy.groupby("quartile", observed=True).agg(stores=("store_key", "count"), avg_sqft=("store_sqft", "mean"), avg_sales=("net_sales", "mean"),
                                                  net_sales=("net_sales", "sum"), gross_profit=("gross_profit", "sum"), costed=("standard_costed_net_sales", "sum"),
                                                  sqft=("store_sqft", "sum")).reset_index()
    q["gross_margin"] = q["gross_profit"] / q["costed"]
    q["sales_per_sqft"] = q["net_sales"] / q["sqft"]
    corr_sales = sy["store_sqft"].corr(sy["net_sales"])
    corr_margin = sy["store_sqft"].corr(sy["gross_margin_pct"])
    big, small = q.iloc[-1], q.iloc[0]
    st.markdown(swd.answer(
        "Are larger stores performing better than smaller stores?",
        f"<b>They sell more, but they are not more profitable per dollar.</b> Store area correlates with net sales (r = {corr_sales:.2f}) and the largest "
        f"quartile averages ${big['avg_sales']:,.0f} per store vs ${small['avg_sales']:,.0f} for the smallest, with higher sales per sqft "
        f"(${big['sales_per_sqft']:.2f} vs ${small['sales_per_sqft']:.2f}). But gross margin is <b>{pct(big['gross_margin'])}</b> in the largest quartile vs "
        f"<b>{pct(small['gross_margin'])}</b> in the smallest (r with area = {corr_margin:.2f}). Size buys volume, not margin — so the question for "
        f"expansion is mix and cost, not footprint."), unsafe_allow_html=True)
    top_sqft = sy.sort_values("net_sales_per_sqft", ascending=False).head(3)["store_name"].tolist()
    show(swd.scatter_points(sy, "store_sqft", "net_sales_per_sqft", "store_name", f"Bigger stores sell more per square foot, but margin does not follow ({year})",
                            "Each point is a store; accent = top 3 sales per sqft; hover for margin", highlight=top_sqft,
                            x_title="Store area, sqft", y_title="Net sales per sqft, $", hover_extra=["gross_margin_pct", "store_type", "state_code"],
                            x_ref=sy["store_sqft"].median(), y_ref=sy["net_sales_per_sqft"].median()), sy, "size",
         "Dotted lines are medians. Louisville (store 200) has 0 sqft and is excluded from area ratios, not from sales.")
    st.dataframe(q[["quartile", "stores", "avg_sqft", "avg_sales", "sales_per_sqft", "gross_margin"]], hide_index=True, width="stretch",
                 column_config={"avg_sqft": st.column_config.NumberColumn("avg sqft", format="%,.0f"),
                                "avg_sales": st.column_config.NumberColumn("avg net sales / store", format="$%,.0f"),
                                "sales_per_sqft": st.column_config.NumberColumn("net sales / sqft", format="$%.2f"),
                                "gross_margin": st.column_config.NumberColumn("gross margin", format="percent")})

    # Q3 falling out of favour --------------------------------------------------------------
    py = product_year[product_year["product_category"].isin(sel_categories)]
    wide = py.pivot(index="product_name", columns="year", values="net_sales")
    declines = wide.diff(axis=1).iloc[:, 1:]
    always_down = wide.index[(declines < 0).all(axis=1)].tolist()
    last_down = wide.index[declines.iloc[:, -1] < 0].tolist()
    idx = wide.div(wide.iloc[:, 0], axis=0)
    weakest = idx.iloc[:, -1].idxmin()
    st.markdown(swd.answer(
        "Has any product fallen out of favour so that we lose sales consistently?",
        (f"<b>No.</b> No product declined in every year {years[0]}–{years[-1]}, and {len(wide) - len(last_down)} of {len(wide)} grew in {years[-1]}. "
         if not always_down else f"<b>Yes:</b> {', '.join(always_down)} declined every year. ")
        + f"The slowest is <b>{weakest}</b> at {idx.iloc[:, -1].min():.0%} of its {years[0]} sales"
        + (f"; products down in {years[-1]}: {', '.join(last_down)}." if last_down else f". The 2020 dip was broad and recovered everywhere.")),
        unsafe_allow_html=True)
    idx_long = idx.reset_index().melt(id_vars="product_name", var_name="year", value_name="index")
    idx_long["year"] = idx_long["year"].astype(str)  # categorical axis: no "2,019.5" ticks
    n_below = int((idx.iloc[:, -1] < 1).sum())
    idx_title = (f"Every product is above its {years[0]} level; {weakest} grew least" if n_below == 0
                 else f"{n_below} of {len(idx)} products are below their {years[0]} level; {weakest} is weakest")
    fig_idx = swd.line_trend(idx_long, "year", "index", idx_title, f"Net sales indexed to {years[0]} = 1.00",
                             series="product_name", highlight=weakest, fmt="{:.2f}", height=420, label_all=False)
    fig_idx.update_xaxes(type="category")
    show(fig_idx, py, "favour")

    # Q4 lowest cost, highest margin ---------------------------------------------------------
    pp_ = agg(scope_year, ["product_category", "product_name"])
    pp_["cost_share"] = pp_["cost"] / pp_["costed_net_sales"]
    best = pp_.sort_values("gross_margin", ascending=False).iloc[0]
    st.markdown(swd.answer(
        "Where has our cost been lowest but margin highest?",
        f"Cost and margin are two faces of one ratio (margin = 1 − cost ÷ costed sales), so the right reading is cost <i>per sales dollar</i>. "
        f"<b>{best['product_name']}</b> ({best['product_category']}) spends only {pct(best['cost_share'])} of each sales dollar on standard cost and earns "
        f"{pct(best['gross_margin'])} margin on {usd(best['net_sales'], 2)} of sales in {year}. In absolute dollars the lowest-cost lines are the "
        f"small-volume ones, which is not the same question. Caveat: standard cost is pack-adjusted and still pending Finance confirmation."),
        unsafe_allow_html=True)
    show(swd.scatter_points(pp_, "cost", "gross_margin", "product_name", f"{best['product_name']} converts the least cost per sales dollar into the highest margin ({year})",
                            "x = standard cost of sales $; y = gross margin; bubble = net sales", highlight=[best["product_name"]], size="net_sales",
                            x_title="Standard cost of sales, $", y_title="Gross margin", y_fmt=".1%", hover_extra=["product_category", "cost_share"],
                            x_ref=pp_["cost"].median(), y_ref=pp_["gross_margin"].median()), pp_, "cost_margin")

    # Q5 lowest quantity, highest margin -----------------------------------------------------
    low = pp_.nsmallest(max(3, len(pp_) // 4), "quantity")
    low_best = low.sort_values("gross_margin", ascending=False).iloc[0]
    lowest = pp_.nsmallest(1, "quantity").iloc[0]
    st.markdown(swd.answer(
        "Which product sold the lowest quantity but gave us the highest margin?",
        f"The lowest quantity in {year} is <b>{lowest['product_name']}</b> ({lowest['quantity']:,.0f} units, {pct(lowest['gross_margin'])} margin) — low volume "
        f"but <i>not</i> high margin. Among the low-volume quartile, <b>{low_best['product_name']}</b> is the one that pairs few units "
        f"({low_best['quantity']:,.0f}) with a high margin ({pct(low_best['gross_margin'])}, {usd(low_best['gross_profit'], 2)} gross profit). "
        f"That is the 'small but rich' line worth protecting."), unsafe_allow_html=True)
    show(swd.scatter_points(pp_, "quantity", "gross_margin", "product_name", f"{low_best['product_name']}: few units, high margin ({year})",
                            "x = net quantity (log scale); y = gross margin; bubble = gross profit $", highlight=[low_best["product_name"], lowest["product_name"]],
                            size="gross_profit", x_title="Net quantity sold", y_title="Gross margin", y_fmt=".1%", log_x=True,
                            hover_extra=["product_category", "net_sales"], y_ref=pp_["gross_margin"].median()), pp_, "qty_margin")

    # Q6 store type vs profitability ----------------------------------------------------------
    stt = agg(scope_year, ["store_type"])
    stores_by_type = scope_year.groupby("store_type")["store_key"].nunique()
    stt["stores"] = stt["store_type"].map(stores_by_type)
    stt["label"] = stt["store_type"].str.strip() + " (" + stt["stores"].astype(str) + ")"
    city = stt[stt["store_type"].str.strip() == "City"]
    thin = stt[stt["stores"] <= 2]
    multi = stt[(stt["stores"] >= 3) & (stt["store_type"].str.strip() != "City")]
    gap_lo = (city["gross_margin"].iloc[0] - multi["gross_margin"].max()) * 100 if len(city) and len(multi) else float("nan")
    gap_hi = (city["gross_margin"].iloc[0] - multi["gross_margin"].min()) * 100 if len(city) and len(multi) else float("nan")
    st.markdown(swd.answer(
        "Is there a correlation between store type and profitability in general?",
        f"<b>A pattern, not a proven correlation.</b> City stores ({int(city['stores'].iloc[0]) if len(city) else 0} of them) earn "
        f"{pct(city['gross_margin'].iloc[0]) if len(city) else 'n/a'} margin and most of the company's gross profit; the other multi-store types "
        f"({', '.join(multi['store_type'].str.strip())}) sit {gap_lo:.0f}–{gap_hi:.0f} points lower. But {len(thin)} of the {len(stt)} types have one or two "
        f"stores, so their margins are single-store facts, not type effects. Treat store type as a slicer to investigate (location, assortment, "
        f"cost), not as a cause."), unsafe_allow_html=True)
    show(swd.bar_ranked(stt, "label", "gross_margin", f"City stores lead on margin; most other types are too small to judge ({year})",
                        "Gross margin by store type (store count in brackets)", fmt="{:.1%}", label_all=True,
                        highlight=city["label"].iloc[0] if len(city) else None, height=360), stt, "type")

    # Q7 store type × category ----------------------------------------------------------------
    short = {"Consolidated Government": "Consol. Govt", "Metropolitan Government": "Metro Govt", "Unified Government": "Unified Govt"}
    ct = agg(scope_year, ["product_category", "store_type"])
    ct["store_type"] = ct["store_type"].str.strip().replace(short)
    ct = ct[ct["events"] >= 30]  # cells with fewer events are noise
    order = ct.groupby("store_type")["events"].sum().sort_values(ascending=False).index
    piv = ct.pivot(index="product_category", columns="store_type", values="gross_margin").reindex(columns=order)
    gap = (piv.max(axis=1) - piv.min(axis=1)).sort_values(ascending=False)
    city_best = int((piv.idxmax(axis=1) == "City").sum()) if "City" in piv.columns else 0
    thin_type = piv.mean(axis=1).idxmin()
    st.markdown(swd.answer(
        "Is there a correlation between store type and profitability for each product category?",
        f"City stores have the best margin in <b>{city_best} of {len(piv)}</b> categories, but the size of the premium varies: the spread between the best "
        f"and worst store type is widest for <b>{gap.index[0]}</b> ({gap.iloc[0] * 100:.0f} points) and narrowest for <b>{gap.index[-1]}</b> "
        f"({gap.iloc[-1] * 100:.0f} points). <b>{thin_type}</b> is thin in every store type. Cells with fewer than 30 events are hidden; hover shows the count."),
        unsafe_allow_html=True)
    show(swd.heatmap(piv, f"City stores lead margin in {city_best} of {len(piv)} categories; the gap is largest in {gap.index[0]} ({year})",
                     "Gross margin by category × store type (cells with ≥ 30 events), columns ordered by event volume",
                     counts=ct.pivot(index="product_category", columns="store_type", values="events").reindex(columns=order), height=340), ct, "cat_type")

    # Q8 seasonality by product ---------------------------------------------------------------
    pm = agg(scope, ["product_name", "month_number"])
    pm["index"] = pm["net_sales"] / pm.groupby("product_name")["net_sales"].transform("mean")
    piv = pm.pivot(index="product_name", columns="month_number", values="index")
    piv.columns = [pd.Timestamp(2000, m, 1).strftime("%b") for m in piv.columns]
    amp = (piv.max(axis=1) - piv.min(axis=1)).sort_values(ascending=False)
    peak_month = piv.idxmax(axis=1).mode().iloc[0]
    low_month = piv.idxmin(axis=1).mode().iloc[0]
    st.markdown(swd.answer(
        "Is there a correlation between time of year and certain products' sales?",
        f"<b>Yes, and it is strongest for big-ticket lines.</b> Across {years[0]}–{years[-1]} most products peak in <b>{peak_month}</b> and trough in "
        f"<b>{low_month}</b>. The swing is largest for <b>{amp.index[0]}</b> ({piv.loc[amp.index[0]].max():.2f}× its monthly average in its best month, "
        f"{piv.loc[amp.index[0]].min():.2f}× in its worst) and smallest for <b>{amp.index[-1]}</b>. Four annual cycles and first-of-month dating "
        f"make this a strong pattern but not yet a forecast."), unsafe_allow_html=True)
    show(swd.heatmap(piv.loc[amp.index], f"December lifts everything; {amp.index[0]} swings the most", "Monthly net sales ÷ product's monthly average, all years in scope",
                     fmt="{:.2f}", height=460, zmin=0.5, zmax=2.0), pm, "season")

    # Q9 seasonality by state/city -------------------------------------------------------------
    st.markdown(swd.answer(
        "Is there a correlation between time of year and a product's sales in certain states or cities?",
        "Pick a product below. States are a clean hierarchy level; the data has no city field, so <i>store name</i> is the closest proxy "
        "(most store names are city names, but a few repeat across states). Compare the state rows: if the December lift is similar "
        "everywhere, the seasonality is national, not local."), unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    prod_choice = c1.selectbox("Product", sorted(scope["product_name"].unique()), index=sorted(scope["product_name"].unique()).index(amp.index[0]), key="prod")
    level = c2.radio("Level", ["State", "Store (city-name proxy)"], horizontal=True, key="level")
    col = "state_code" if level == "State" else "store_name"
    sel = scope[scope["product_name"] == prod_choice]
    spm = agg(sel, [col, "month_number"])
    totals = spm.groupby(col)["net_sales"].sum().sort_values(ascending=False)
    keep = totals.head(12).index
    spm = spm[spm[col].isin(keep)]
    spm["index"] = spm["net_sales"] / spm.groupby(col)["net_sales"].transform("mean")
    piv = spm.pivot(index=col, columns="month_number", values="index").reindex(keep)
    piv.columns = [pd.Timestamp(2000, m, 1).strftime("%b") for m in piv.columns]
    show(swd.heatmap(piv, f"{prod_choice}: seasonality by {level.lower()} (top 12 by sales)", "Monthly net sales ÷ that row's monthly average; same scale as above",
                     fmt="{:.2f}", height=440, zmin=0.5, zmax=2.0, counts=spm.pivot(index=col, columns="month_number", values="events").reindex(keep)),
         spm, "season_geo")

# ============================================================================= 4. outliers
def render_outliers() -> None:
    st.caption(f"Scope: regions {', '.join(sel_regions) if len(sel_regions) < len(regions) else 'all'}; categories "
               f"{', '.join(sel_categories) if len(sel_categories) < len(categories) else 'all'}; all years.")
    c1, c2, c3 = st.columns([1, 1, 1])
    measure = c1.selectbox("$ measure", ["net_sales", "gross_profit", "gross_profit_per_sqft"], format_func=lambda s: s.replace("_", " "), key="measure")
    rule = c2.radio("Outlier rule", ["Against peers in the same month", "Against the store's own history"], horizontal=False, key="rule")
    z_cut = c3.slider("Flag when |z| exceeds", 2.0, 4.0, 3.0, 0.5, key="zcut")

    sm = agg(scope, ["store_key", "store_name", "state_code", "region_name", "store_type", "store_sqft", "month_start"])
    sm["gross_profit_per_sqft"] = sm["gross_profit"] / sm["store_sqft"].replace(0, np.nan)
    sm["store"] = sm["store_name"] + ", " + sm["state_code"]
    grp = "month_start" if rule.startswith("Against peers") else "store_key"
    g = sm.groupby(grp)[measure]
    sm["z"] = (sm[measure] - g.transform("mean")) / g.transform("std").replace(0, np.nan)
    out = sm[sm["z"].abs() > z_cut]
    hi = out[out["z"] > 0].groupby("store")["z"].count().sort_values(ascending=False)
    lo = out[out["z"] < 0].groupby("store")["z"].count().sort_values(ascending=False)
    st.markdown(swd.answer(
        "Which stores are outliers over time — what should we do more of?",
        (f"<b>{len(out):,}</b> store-months exceed |z| {z_cut:.1f} on {measure.replace('_', ' ')}. "
         + (f"Persistently <b>above</b> peers: {', '.join(f'{k} ({v} months)' for k, v in hi.head(5).items())}. " if len(hi) else "")
         + (f"Persistently <b>below</b>: {', '.join(f'{k} ({v})' for k, v in lo.head(5).items())}. " if len(lo) else "")
         + ("Peer rule finds the structurally big winners (replicate their mix and location profile). " if grp == "month_start"
            else "Own-history rule finds months that broke a store's pattern (events, closures, data issues). ")
         + "Switch the rule and the measure to see both stories; gross profit per sqft removes the size advantage.")), unsafe_allow_html=True)
    sm_plot = sm.dropna(subset=[measure]).copy()
    sm_plot["label"] = sm_plot["store"] + " " + sm_plot["month_start"].astype(str).str[:7]
    flagged = sm_plot.loc[sm_plot["z"].abs() > z_cut, "label"].tolist()
    show(swd.scatter_points(sm_plot, "month_start", measure, "label", f"Store-months outside |z| {z_cut:.1f}: {len(flagged)} of {len(sm_plot):,}",
                            f"{measure.replace('_', ' ')} per store per month; orange = flagged ({rule.lower()})", highlight=flagged,
                            highlight_color=swd.WARN, label_highlight=False, x_title="Month", y_title=measure.replace("_", " ") + ", $",
                            hover_extra=["store_type", "region_name", "z"], height=480), out.sort_values("z", ascending=False), "store_outliers")
    with st.expander("Flagged store-months"):
        flagged_tbl = out.sort_values("z", ascending=False)[["store", "store_type", "region_name", "month_start", measure, "z"]]
        flagged_tbl["month_start"] = flagged_tbl["month_start"].astype(str).str[:7]
        st.dataframe(flagged_tbl.round(2), hide_index=True, width="stretch")

    st.markdown("---")
    hier = st.radio("Product hierarchy level", ["Category", "Product"], horizontal=True, key="hier")
    hcol = "product_category" if hier == "Category" else "product_name"
    pm2 = agg(scope, [hcol, "month_start"])
    pmeasure = "gross_profit" if measure == "gross_profit_per_sqft" else measure
    focus_opts = sorted(pm2[hcol].unique())
    focus = st.multiselect(f"Highlight {hier.lower()}", focus_opts, default=focus_opts[:1], key=f"focus_{hier}")
    growth = pm2.groupby(hcol).apply(lambda d: d.sort_values("month_start")[pmeasure].tail(12).sum() / max(d.sort_values("month_start")[pmeasure].head(12).sum(), 1e-9) - 1,
                                     include_groups=False).sort_values(ascending=False)
    plural = "categories" if hier == "Category" else "products"
    st.markdown(swd.answer(
        f"Which {plural} are pulling ahead over time?",
        f"Comparing the last 12 months in scope with the first 12: <b>{growth.index[0]}</b> grew most ({growth.iloc[0]:+.0%}) and <b>{growth.index[-1]}</b> least "
        f"({growth.iloc[-1]:+.0%}) on {pmeasure.replace('_', ' ')}. Every line shows the December spike; the gap between lines is the mix story. "
        f"Pick a {hier.lower()} to follow it in colour."), unsafe_allow_html=True)
    show(swd.line_trend(pm2, "month_start", pmeasure, f"{growth.index[0]} is the fastest-growing {hier.lower()} ({growth.iloc[0]:+.0%})",
                        f"{pmeasure.replace('_', ' ')} per month by {hier.lower()}", series=hcol, highlight=focus or None, fmt="${:,.0f}", height=460, label_all=hier == "Category"),
         pm2, "hier_trend")

    pq = agg(scope[scope["year"] == year], ["product_category", "product_name"])
    pq["do_more"] = (pq["net_sales"] >= pq["net_sales"].median()) & (pq["gross_margin"] >= pq["gross_margin"].median())
    winners = pq.loc[pq["do_more"], "product_name"].tolist()
    cash_cows = pq.loc[(pq["net_sales"] >= pq["net_sales"].median()) & (pq["gross_margin"] < pq["gross_margin"].median()), "product_name"].tolist()
    st.markdown(swd.answer(
        "So what is working — what should we do more of?",
        f"Top-right of the chart ({year}): above-median sales <i>and</i> above-median margin — <b>{', '.join(winners)}</b>. These are the lines to "
        f"give more space, more stock and more promotion, especially in the store types and regions where their margin is highest (sections above). "
        f"Bottom-right (high sales, low margin: <b>{', '.join(cash_cows) or 'none'}</b>) earns revenue but needs cost or price work before scaling."), unsafe_allow_html=True)
    show(swd.scatter_points(pq, "net_sales", "gross_margin", "product_name", f"Do more of the top-right: {len(winners)} products with high sales and high margin ({year})",
                            "x = net sales $ (log); y = gross margin; bubble = net quantity", highlight=winners, size="quantity", log_x=True,
                            x_title="Net sales, $", y_title="Gross margin", y_fmt=".1%", hover_extra=["product_category", "quantity"],
                            x_ref=pq["net_sales"].median(), y_ref=pq["gross_margin"].median(), height=460), pq, "do_more")


# ============================================================================= layout
SECTIONS = [render_model, render_flow, render_questions, render_outliers]
requested = st.query_params.get("section")  # ?section=3 renders one section on its own (deep links, screenshots)
if requested in {"1", "2", "3", "4"}:
    st.caption(f"Section {requested} of 4 · remove `?section=` from the URL to see all tabs.")
    SECTIONS[int(requested) - 1]()
else:
    for tab, render in zip(st.tabs(SECTION_LABELS), SECTIONS):
        with tab:
            render()
