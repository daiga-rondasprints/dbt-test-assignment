"""Interpretation widget for every visual.

Two engines, chosen at runtime:
- Offline interpreter (default): deterministic sentences computed from the chart's aggregate table. No data leaves
  the machine. Always available, so the panel never dies.
- OpenAI-compatible chat endpoint, used only if AI_ENDPOINT and AI_API_KEY are set in the environment (for example an
  Azure OpenAI or GitHub Models deployment the business has approved). It receives the same small JSON payload the
  panel shows under "Payload sent": the question, the action title, filters and at most 40 aggregated rows. It never
  receives row-level data, SQL, or the database.
"""
from __future__ import annotations

import json
import os

import pandas as pd

ENDPOINT = os.getenv("AI_ENDPOINT", "")
API_KEY = os.getenv("AI_API_KEY", "")
MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
MAX_ROWS = 40

SYSTEM = ("You are a retail finance analyst. You receive a small JSON of aggregated chart data and a question. "
          "Answer in at most four short sentences: what the chart shows, the one number that matters, a caveat if the "
          "payload includes one, and a next step. Profit figures are gross profit, never net profit. Do not invent data.")


def engine_label() -> str:
    return f"OpenAI-compatible endpoint ({MODEL})" if ENDPOINT and API_KEY else "offline interpreter (no data leaves this machine)"


def build_payload(question: str, title: str, table: pd.DataFrame, filters: str, caveat: str = "") -> dict:
    numeric = table.select_dtypes("number").columns.tolist()
    rows = table.head(MAX_ROWS).copy()
    for c in rows.columns:
        if str(rows[c].dtype).startswith("datetime"):
            rows[c] = rows[c].astype(str)
    return {
        "question": question,
        "action_title": title,
        "filters": filters,
        "caveat": caveat,
        "columns": table.columns.tolist(),
        "numeric_columns": numeric,
        "row_count": int(len(table)),
        "rows": json.loads(rows.to_json(orient="records", date_format="iso")),
    }


def interpret(payload: dict) -> str:
    if ENDPOINT and API_KEY:
        try:
            return _remote(payload)
        except Exception as exc:  # fall back rather than break the page
            return _offline(payload) + f"\n\n_Remote engine failed ({type(exc).__name__}); offline interpretation shown._"
    return _offline(payload)


def _remote(payload: dict) -> str:
    import urllib.request

    body = json.dumps({"model": MODEL, "temperature": 0.2, "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(payload)},
    ]}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


def _offline(payload: dict) -> str:
    rows = payload.get("rows") or []
    numeric = payload.get("numeric_columns") or []
    if not rows or not numeric:
        return f"**{payload.get('action_title', '')}** — no numeric data to interpret for this scope."
    df = pd.DataFrame(rows)
    # The metric is the first numeric column that is not an identifier-like field.
    metric = next((c for c in numeric if not c.endswith(("_key", "_id", "year", "month_number")) and c in df), numeric[0])
    label_cols = [c for c in df.columns if c not in numeric and df[c].dtype == object]
    label = label_cols[0] if label_cols else None
    s = pd.to_numeric(df[metric], errors="coerce").dropna()
    if s.empty:
        return f"**{payload.get('action_title', '')}** — the metric column is empty for this scope."
    is_ratio = s.abs().max() <= 1.5 and ("margin" in metric or "pct" in metric or "index" in metric or "share" in metric)
    fmt = (lambda v: f"{v:.1%}") if is_ratio else (lambda v: f"{v:,.0f}")
    lines = [f"**{payload.get('action_title', '')}**"]
    top_i, bot_i = s.idxmax(), s.idxmin()
    top = f"{df.loc[top_i, label]} " if label else ""
    bot = f"{df.loc[bot_i, label]} " if label else ""
    lines.append(f"Across {payload.get('row_count', len(df)):,} rows, `{metric}` ranges from {bot}{fmt(s.min())} to {top}{fmt(s.max())}; "
                 f"the median is {fmt(s.median())}.")
    if not is_ratio and s.sum() != 0 and len(s) > 1:
        share = s.max() / s.sum()
        lines.append(f"The top item carries {share:.0%} of the total" + (" — concentrated." if share > 0.4 else " — spread out."))
    if len(s) >= 6:
        z = (s - s.mean()) / (s.std() or 1)
        n_out = int((z.abs() > 2).sum())
        if n_out:
            lines.append(f"{n_out} value(s) sit more than two standard deviations from the mean; check those first.")
    if payload.get("filters") and payload["filters"] != "none":
        lines.append(f"Scope: {payload['filters']}.")
    if payload.get("caveat"):
        lines.append(f"Caveat: {payload['caveat']}")
    lines.append("Figures are gross profit on standard cost unless the chart says otherwise; not net profit.")
    return " ".join(lines[:1]) + "\n\n" + " ".join(lines[1:])
