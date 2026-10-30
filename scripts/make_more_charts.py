"""Extra charts + dashboard page 2, queried live from the PostgreSQL `customers` table.
Usage: python scripts/make_more_charts.py <pgdata_dir>   (same dir used with run_analysis.py)
Writes images/chart_*.png and dashboard/churn_dashboard_page2.png
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pgserver
import psycopg2

ROOT = Path(__file__).resolve().parent.parent
IMG, DASH = ROOT / "images", ROOT / "dashboard"
RED, BLUE, AMBER, GREY, BG, INK = "#d64545", "#2f6fb5", "#e8a33d", "#9aa5b1", "#f6f8fa", "#1f2933"

db = pgserver.get_server(sys.argv[1])
conn = psycopg2.connect(db.get_uri())
df = pd.read_sql("SELECT * FROM customers", conn)
df["churn_pct"] = df.churn_flag * 100


def style(ax, title):
    ax.set_facecolor("white")
    ax.set_title(title, loc="left", fontsize=11, weight="bold", color=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=9)


def labels(ax, bars, fmt="{:.1f}%", pad=0.8):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + pad, fmt.format(b.get_height()),
                ha="center", fontsize=8.5, color=INK)


# ---- chart functions: each draws on a given axes ----
def addons(ax):
    inet = df[df.internet_service != "No"]
    names = [("online_security", "Online\nSecurity"), ("tech_support", "Tech\nSupport"),
             ("online_backup", "Online\nBackup"), ("device_protection", "Device\nProtection")]
    no = [inet[inet[c] == "No"].churn_pct.mean() for c, _ in names]
    yes = [inet[inet[c] == "Yes"].churn_pct.mean() for c, _ in names]
    x = np.arange(len(names)); w = 0.38
    b1 = ax.bar(x - w / 2, no, w, color=RED, label="Without service")
    b2 = ax.bar(x + w / 2, yes, w, color=BLUE, label="With service")
    labels(ax, b1); labels(ax, b2)
    ax.set_xticks(x); ax.set_xticklabels([n for _, n in names]); ax.set_ylim(0, 52)
    ax.legend(frameon=False, fontsize=8.5)
    style(ax, "Add-on services cut churn (internet customers, %)")


def cumulative(ax):
    ch = df[df.churn_flag == 1].groupby("tenure_months").size()
    cum = 100 * ch.cumsum() / ch.sum()
    ax.plot(cum.index, cum.values, color=RED, lw=2.5)
    ax.fill_between(cum.index, cum.values, color=RED, alpha=0.12)
    for m in (1, 12, 24):
        ax.scatter([m], [cum[m]], color=INK, zorder=3)
        ax.annotate(f"month {m}: {cum[m]:.0f}%", (m, cum[m]), xytext=(m + 3, cum[m] - 9), fontsize=9, color=INK)
    ax.set_xlim(0, 72); ax.set_ylim(0, 105)
    ax.set_xlabel("Tenure (months)", fontsize=9)
    style(ax, "Cumulative share of all churners by tenure (%)")


def heat(ax, rows, cols, title, row_order=None, col_order=None, fig=None):
    p = df.pivot_table(index=rows, columns=cols, values="churn_pct", aggfunc="mean")
    if row_order: p = p.reindex(row_order)
    if col_order: p = p[col_order]
    im = ax.imshow(p.values, cmap="RdYlBu_r", vmin=0, vmax=60, aspect="auto")
    ax.set_xticks(range(p.shape[1])); ax.set_xticklabels([str(c).split(". ", 1)[-1] for c in p.columns], fontsize=8.5)
    ax.set_yticks(range(p.shape[0])); ax.set_yticklabels(p.index, fontsize=8.5)
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v = p.values[i, j]
            ax.text(j, i, "-" if np.isnan(v) else f"{v:.0f}%", ha="center", va="center", fontsize=9,
                    color="white" if (not np.isnan(v) and (v > 42 or v < 10)) else INK, weight="bold")
    ax.set_title(title, loc="left", fontsize=11, weight="bold", color=INK)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)


def heat_contract_tenure(ax):
    heat(ax, "contract", "tenure_bucket", "Churn % : contract x tenure",
         ["Month-to-month", "One year", "Two year"])


def heat_pay_inet(ax):
    heat(ax, "payment_method", "internet_service", "Churn % : payment method x internet service",
         col_order=["Fiber optic", "DSL", "No"])


def price_q(ax):
    q = pd.qcut(df.monthly_charges, 4, labels=False) + 1
    g = df.groupby(q).agg(lo=("monthly_charges", "min"), hi=("monthly_charges", "max"), r=("churn_pct", "mean"))
    b = ax.bar([f"Q{i}\n\\${r.lo:.0f}-\\${r.hi:.0f}" for i, r in g.iterrows()], g.r, color=[BLUE, BLUE, RED, AMBER])
    labels(ax, b); ax.set_ylim(0, 45)
    style(ax, "Churn by monthly price quartile (%)")


def demographics(ax):
    segs = [("Senior", df[df.senior_citizen == 1]), ("Non-senior", df[df.senior_citizen == 0]),
            ("Partner", df[df.has_partner]), ("No partner", df[~df.has_partner]),
            ("Dependents", df[df.has_dependents]), ("No dependents", df[~df.has_dependents]),
            ("Paperless", df[df.paperless_billing]), ("Paper bill", df[~df.paperless_billing])]
    b = ax.bar([s for s, _ in segs], [d.churn_pct.mean() for _, d in segs],
               color=[RED, BLUE] * 4)
    labels(ax, b); ax.set_ylim(0, 50)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    style(ax, "Churn by customer profile (%)")


def internet(ax):
    g = df.groupby("internet_service").churn_pct.mean().reindex(["Fiber optic", "DSL", "No"])
    b = ax.bar(["Fiber optic", "DSL", "No internet"], g, color=[RED, BLUE, BLUE])
    labels(ax, b); ax.set_ylim(0, 52)
    style(ax, "Churn by internet service (%)")


def clv(ax):
    g = df.groupby("churn_flag").agg(tenure=("tenure_months", "mean"), charge=("monthly_charges", "mean"),
                                    ltv=("total_charges", "mean"))
    x = np.arange(3); w = 0.38
    vals = [[g.loc[f, "tenure"], g.loc[f, "charge"], g.loc[f, "ltv"] / 30] for f in (0, 1)]
    ax.bar(x - w / 2, vals[0], w, color=BLUE, label="Retained")
    ax.bar(x + w / 2, vals[1], w, color=RED, label="Churned")
    txt = [[f"{g.loc[f,'tenure']:.1f} mo", f"${g.loc[f,'charge']:.2f}", f"${g.loc[f,'ltv']:,.0f}"] for f in (0, 1)]
    for i in range(3):
        ax.text(i - w / 2, vals[0][i] + 1, txt[0][i], ha="center", fontsize=8.5)
        ax.text(i + w / 2, vals[1][i] + 1, txt[1][i], ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels(["Avg tenure", "Avg monthly\ncharge", "Avg lifetime\nrevenue*"])
    ax.set_yticks([]); ax.set_ylim(0, 105); ax.legend(frameon=False, fontsize=8.5)
    ax.text(0.99, 0.02, "*bar scaled /30", transform=ax.transAxes, ha="right", fontsize=7.5, color=GREY)
    style(ax, "Churned vs retained customers")


CHARTS = {
    "chart_addon_services": addons, "chart_cumulative_churn": cumulative,
    "chart_heatmap_contract_tenure": heat_contract_tenure, "chart_heatmap_payment_internet": heat_pay_inet,
    "chart_price_quartile": price_q, "chart_customer_profile": demographics,
    "chart_internet_service": internet, "chart_clv_churned_vs_retained": clv,
}

for name, fn in CHARTS.items():
    fig, ax = plt.subplots(figsize=(7.5, 4.5), facecolor="white")
    fn(ax)
    fig.tight_layout()
    fig.savefig(IMG / f"{name}.png", dpi=140)
    plt.close(fig)

# ---- dashboard page 2 ----
fig = plt.figure(figsize=(16, 9), facecolor=BG)
fig.text(0.03, 0.95, "Churn Drivers & Segments (Page 2)", fontsize=22, weight="bold", color=INK, va="center")
fig.text(0.03, 0.915, "Source: PostgreSQL table customers | same 7,043 customers as page 1", fontsize=10,
         color=GREY, va="center")
grid = [(addons, [0.05, 0.54, 0.40, 0.31]), (cumulative, [0.56, 0.54, 0.40, 0.31]),
        (heat_contract_tenure, [0.11, 0.08, 0.25, 0.31]), (heat_pay_inet, [0.50, 0.08, 0.20, 0.31]),
        (price_q, [0.78, 0.08, 0.19, 0.31])]
for fn, pos in grid:
    fn(fig.add_axes(pos))
fig.savefig(DASH / "churn_dashboard_page2.png", dpi=130, facecolor=BG)
print("ok")
conn.close()
