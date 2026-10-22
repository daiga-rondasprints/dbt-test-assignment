"""Storytelling-with-data styling for Plotly (same rules as the dashboard template).

- Explanatory, not exploratory: one chart makes one point; the title states it, top-left.
- Declutter: no borders, gridlines, legend boxes; light grey axes; labels next to the data.
- Focus: everything grey, ONE accent colour where the eye should land.
- Bars start at zero and are sorted; categories read as horizontal bars; time reads as lines.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

GREY = "#B5B5B5"
GREY_DARK = "#666666"
GREY_LIGHT = "#D9D9D9"
TEXT = "#212529"
ACCENT = "#95C11F"
ACCENT_DARK = "#6E9117"
ACCENT_ALT = "#212529"
WARN = "#D9822B"  # orange, used only for a warning/outlier call-out (colour-blind safe against lime)
BG_SOFT = "#F8F9FA"
FONT = "Open Sans, Arial"
SEQUENTIAL = [[0, "#F1F3F5"], [0.5, "#C9DD8F"], [1, "#6E9117"]]


def base_layout(title: str, subtitle: str | None = None, height: int = 340) -> dict:
    heading = f"<b>{title}</b>"
    if subtitle:
        heading += f"<br><span style='font-size:12px;color:{GREY_DARK}'>{subtitle}</span>"
    return dict(
        title=dict(text=heading, x=0, xanchor="left", font=dict(size=16, color=TEXT, family=FONT)),
        font=dict(family=FONT, color=TEXT, size=12),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=8, r=16, t=74, b=30),
        height=height,
        showlegend=False,
        bargap=0.3,
        xaxis=dict(showgrid=False, zeroline=False, showline=False, tickangle=0, tickfont=dict(color=GREY_DARK), automargin=True),
        yaxis=dict(showgrid=False, zeroline=False, showline=False, tickangle=0, tickfont=dict(color=GREY_DARK), automargin=True),
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, color=TEXT)),
    )


def tile(label: str, value: str, delta: str | None = None, good: bool | None = None) -> str:
    color = TEXT if good is None else (ACCENT_DARK if good else WARN)
    delta_html = f"<div style='font-size:12px;color:{color}'>{delta}</div>" if delta else ""
    return (
        f"<div style='padding:10px 12px;border-left:4px solid {ACCENT};background:{BG_SOFT};margin-bottom:6px;min-height:92px'>"
        f"<div style='font-size:12px;color:{GREY_DARK};font-family:{FONT}'>{label}</div>"
        f"<div style='font-size:26px;color:{TEXT};font-family:{FONT};font-weight:600'>{value}</div>{delta_html}</div>"
    )


def answer(question: str, text: str) -> str:
    """A question in bold charcoal and the plain-English answer under it."""
    return (
        f"<div style='margin:6px 0 10px 0'><div style='font-size:15px;font-weight:600;color:{TEXT}'>{question}</div>"
        f"<div style='font-size:14px;color:{GREY_DARK};line-height:1.45'>{text}</div></div>"
    )


def bar_ranked(df: pd.DataFrame, category: str, value: str, title: str, subtitle: str | None = None,
               highlight: str | list[str] | None = None, fmt: str = "{:,.0f}", top_n: int | None = None,
               label_all: bool = False, height: int = 340) -> go.Figure:
    hl = {highlight} if isinstance(highlight, str) else set(highlight or [])
    d = df.sort_values(value, ascending=False)
    if top_n:
        d = d.head(top_n)
    d = d.iloc[::-1]
    if not hl and len(d):
        hl = {d[category].iloc[-1]}
    colors = [ACCENT if c in hl else GREY for c in d[category]]
    labels = [fmt.format(v) if (label_all or c in hl) else "" for c, v in zip(d[category], d[value])]
    fig = go.Figure(go.Bar(
        x=d[value], y=d[category], orientation="h", marker_color=colors,
        text=labels, textposition="outside", cliponaxis=False,
        textfont=dict(color=GREY_DARK, size=12),
        customdata=d[category], hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(**base_layout(title, subtitle, height=height))
    fig.update_xaxes(visible=False)
    return fig


def line_trend(df: pd.DataFrame, x: str, y: str, title: str, subtitle: str | None = None,
               series: str | None = None, highlight: str | list[str] | None = None, fmt: str = "{:,.0f}",
               height: int = 360, label_all: bool = True) -> go.Figure:
    hl = {highlight} if isinstance(highlight, str) else set(highlight or [])
    fig = go.Figure()
    groups = [(None, df)] if series is None else list(df.groupby(series))
    if not hl and series is not None and groups:
        hl = {max(groups, key=lambda g: g[1][y].iloc[-1])[0]}
    for name, g in groups:
        g = g.sort_values(x)
        is_hl = series is None or name in hl
        fig.add_trace(go.Scatter(
            x=g[x], y=g[y], mode="lines", name=str(name),
            line=dict(color=ACCENT if is_hl else GREY_LIGHT, width=3 if is_hl else 1.5),
            customdata=[name] * len(g), hovertemplate=f"{name or ''} %{{x}}: %{{y:,.2f}}<extra></extra>",
        ))
        if len(g) and (is_hl or label_all):
            fig.add_annotation(
                x=g[x].iloc[-1], y=g[y].iloc[-1], xanchor="left", showarrow=False,
                text=f" {str(name) + ' ' if name is not None else ''}{fmt.format(g[y].iloc[-1])}",
                font=dict(color=ACCENT_DARK if is_hl else GREY_DARK, size=11),
            )
    fig.update_layout(**base_layout(title, subtitle, height=height))
    fig.update_yaxes(showline=False, ticks="")
    fig.update_xaxes(showline=True, linecolor=GREY_LIGHT)
    fig.update_layout(margin=dict(r=150))
    return fig


def scatter_points(df: pd.DataFrame, x: str, y: str, label: str, title: str, subtitle: str | None = None,
                   highlight: list[str] | None = None, size: str | None = None, x_title: str = "", y_title: str = "",
                   x_fmt: str = ",.0f", y_fmt: str = ",.2f", log_x: bool = False, height: int = 420,
                   highlight_color: str = ACCENT, label_highlight: bool = True, hover_extra: list[str] | None = None,
                   x_ref: float | None = None, y_ref: float | None = None) -> go.Figure:
    """Grey points; the highlighted labels in the accent (or warning) colour, labelled directly."""
    hl = set(highlight or [])
    d = df.copy()
    d["_hl"] = d[label].isin(hl)
    sizes = None
    if size:
        s = d[size].clip(lower=0)
        sizes = 7 + 28 * np.sqrt(s / max(s.max(), 1e-9))
    extra = hover_extra or []
    custom = d[[label] + extra].to_numpy()
    hover = f"<b>%{{customdata[0]}}</b><br>{x_title or x}: %{{x:{x_fmt}}}<br>{y_title or y}: %{{y:{y_fmt}}}"
    for i, col in enumerate(extra, start=1):
        hover += f"<br>{col}: %{{customdata[{i}]}}"
    hover += "<extra></extra>"
    fig = go.Figure()
    trace_cls = go.Scattergl if len(d) > 3000 else go.Scatter  # WebGL keeps 10k+ store-months responsive
    for is_hl, g in d.groupby("_hl", sort=True):
        idx = g.index
        fig.add_trace(trace_cls(
            x=g[x], y=g[y], mode="markers+text" if (is_hl and label_highlight) else "markers",
            text=g[label] if is_hl else None, textposition="top center",
            textfont=dict(color=ACCENT_DARK if highlight_color == ACCENT else WARN, size=11),
            marker=dict(color=highlight_color if is_hl else GREY, size=(sizes.loc[idx] if sizes is not None else (10 if is_hl else 7)),
                        opacity=0.95 if is_hl else 0.55, line=dict(width=0)),
            customdata=custom[[d.index.get_loc(i) for i in idx]], hovertemplate=hover,
        ))
    fig.update_layout(**base_layout(title, subtitle, height=height))
    fig.update_xaxes(showline=True, linecolor=GREY_LIGHT, title=dict(text=x_title, font=dict(color=GREY_DARK, size=12)))
    if log_x:
        fig.update_xaxes(type="log")
    fig.update_yaxes(showline=True, linecolor=GREY_LIGHT, title=dict(text=y_title, font=dict(color=GREY_DARK, size=12)))
    if x_ref is not None:
        fig.add_vline(x=x_ref, line=dict(color=GREY_LIGHT, width=1, dash="dot"))
    if y_ref is not None:
        fig.add_hline(y=y_ref, line=dict(color=GREY_LIGHT, width=1, dash="dot"))
    return fig


def heatmap(pivot: pd.DataFrame, title: str, subtitle: str | None = None, fmt: str = "{:.0%}",
            height: int = 380, zmin: float | None = None, zmax: float | None = None,
            counts: pd.DataFrame | None = None) -> go.Figure:
    """Light-to-lime heat map with the number written in every cell; hover shows a count if supplied."""
    z = pivot.to_numpy(dtype=float)
    text = [[("" if pd.isna(v) else fmt.format(v)) for v in row] for row in z]
    custom = counts.reindex(index=pivot.index, columns=pivot.columns).to_numpy() if counts is not None else None
    hover = "%{y} / %{x}: %{text}" + ("<br>n = %{customdata:,.0f}" if custom is not None else "") + "<extra></extra>"
    fig = go.Figure(go.Heatmap(
        z=z, x=list(pivot.columns), y=list(pivot.index), text=text, texttemplate="%{text}",
        textfont=dict(size=11, color=TEXT), colorscale=SEQUENTIAL, showscale=False, zmin=zmin, zmax=zmax,
        customdata=custom, hovertemplate=hover, xgap=2, ygap=2,
    ))
    fig.update_layout(**base_layout(title, subtitle, height=height))
    fig.update_yaxes(autorange="reversed")
    return fig


def pipeline_flow(stages: list[tuple[str, int, list[str]]], branch: tuple[str, int, list[str]], title: str,
                  subtitle: str | None = None, height: int = 330) -> go.Figure:
    """Left-to-right boxes with row counts and arrows; the last stage splits into kept (accent) and removed (warning)."""
    fig = go.Figure()
    n = len(stages)
    fig.update_xaxes(visible=False, range=[0, 10 * n + 1])
    fig.update_yaxes(visible=False, range=[0, 10])

    def box(x0, y0, x1, y1, head, value, lines, color, fill):
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=color, width=2), fillcolor=fill)
        fig.add_annotation(x=(x0 + x1) / 2, y=y1 - 0.7, text=f"<b>{head}</b>", showarrow=False, font=dict(color=TEXT, size=12))
        fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2 + 0.2, text=f"<b>{value:,}</b>", showarrow=False,
                           font=dict(color=color if color != GREY_LIGHT else TEXT, size=22))
        fig.add_annotation(x=(x0 + x1) / 2, y=y0 + 1.1, text="<br>".join(lines), showarrow=False, font=dict(color=GREY_DARK, size=10))

    for i, (head, value, lines) in enumerate(stages):
        x0 = 10 * i + 0.5
        last = i == n - 1
        box(x0, 4.2 if not last else 5.6, x0 + 8.4, 9.4, head, value, lines, ACCENT if last else GREY_LIGHT, BG_SOFT if last else "white")
        if i < n - 1:
            fig.add_annotation(x=x0 + 10.4, y=6.8 if i < n - 2 else 7.5, ax=x0 + 8.5, ay=6.8, xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=2, arrowcolor=GREY_DARK, arrowwidth=1.6, text="")
    head, value, lines = branch
    x0 = 10 * (n - 1) + 0.5
    box(x0, 0.4, x0 + 8.4, 4.4, head, value, lines, WARN, "#FBF1E8")
    fig.add_annotation(x=x0 + 4.2, y=4.5, ax=x0 - 1.4, ay=6.5, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2,
                       arrowcolor=WARN, arrowwidth=1.6, text="")
    fig.update_layout(**base_layout(title, subtitle, height=height))
    fig.update_layout(margin=dict(l=8, r=8, t=74, b=8))
    return fig


def star_schema(fact: str, fact_lines: list[str], dims: dict[str, list[str]], title: str, subtitle: str | None = None,
                height: int = 420) -> go.Figure:
    """Simple star drawn with shapes: fact in the middle, dimensions around it."""
    fig = go.Figure()
    fig.update_xaxes(visible=False, range=[0, 10])
    fig.update_yaxes(visible=False, range=[0, 10])

    def box(x0, y0, x1, y1, head, lines, accent):
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=ACCENT if accent else GREY_LIGHT, width=2),
                      fillcolor=BG_SOFT if accent else "white")
        fig.add_annotation(x=(x0 + x1) / 2, y=y1 - 0.45, text=f"<b>{head}</b>", showarrow=False,
                           font=dict(color=ACCENT_DARK if accent else TEXT, size=13))
        fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2 - 0.35, text="<br>".join(lines), showarrow=False,
                           font=dict(color=GREY_DARK, size=11), align="center")

    box(3.1, 3.2, 6.9, 6.8, fact, fact_lines, True)
    positions = [(0.3, 6.5, 3.0, 9.6), (7.0, 6.5, 9.7, 9.6), (0.3, 0.4, 3.0, 3.5), (7.0, 0.4, 9.7, 3.5)]
    for (name, lines), (x0, y0, x1, y1) in zip(dims.items(), positions):
        box(x0, y0, x1, y1, name, lines, False)
        fig.add_shape(type="line", x0=(x0 + x1) / 2, y0=(y0 + y1) / 2, x1=5, y1=5, line=dict(color=GREY_LIGHT, width=1.5), layer="below")
    fig.update_layout(**base_layout(title, subtitle, height=height))
    fig.update_layout(margin=dict(l=8, r=8, t=74, b=8))
    return fig


def prose(text: str) -> str:
    """Plain-English answer paragraph without a repeated question (used inside expanders)."""
    return f"<div style='font-size:14px;color:{GREY_DARK};line-height:1.45;margin:0 0 8px 0'>{text}</div>"
