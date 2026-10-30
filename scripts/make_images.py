"""Render EXPLAIN ANALYZE screenshots and a 1-page dashboard PNG.
Usage: python scripts/make_images.py
Reads results/explain_*.txt and dashboard/v_churn_dashboard.csv (exported from the v_churn_dashboard view).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "images"
DASH = ROOT / "dashboard"
IMG.mkdir(exist_ok=True)

# ---------- EXPLAIN ANALYZE screenshots ----------
for name, title in [("explain_before", "BEFORE index (Seq Scan)"), ("explain_after", "AFTER index (Bitmap Index Scan)")]:
    txt = (ROOT / "results" / f"{name}.txt").read_text(encoding="utf-8")
    lines = txt.splitlines()
    fig = plt.figure(figsize=(12, 0.45 + 0.28 * len(lines)), facecolor="#1e1e1e")
    fig.text(0.01, 1 - 0.25 / fig.get_figheight() * 1.2, f"EXPLAIN ANALYZE - {title}", color="#4fc3f7",
             family="monospace", fontsize=10, weight="bold", va="top")
    fig.text(0.01, 1 - 0.65 / fig.get_figheight() * 1.2 + 0.0, "\n".join(lines), color="#d4d4d4",
             family="monospace", fontsize=8, va="top", linespacing=1.5)
    fig.set_figheight(0.9 + 0.2 * len(lines) * 1.5)
    fig.savefig(IMG / f"{name}.png", dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)

# ---------- 1-page dashboard ----------
df = pd.read_csv(DASH / "v_churn_dashboard.csv")
total, churned = len(df), int(df.churn_flag.sum())
rate = 100 * churned / total
lost_m = df.loc[df.churn_flag == 1, "monthly_charges"].sum()
lost_y = lost_m * 12

RED, BLUE, GREY, BG, INK = "#d64545", "#2f6fb5", "#9aa5b1", "#f6f8fa", "#1f2933"


def rate_by(col, order=None):
    g = df.groupby(col).churn_flag.agg(["mean", "size"])
    g["mean"] *= 100
    return g.reindex(order) if order is not None else g


fig = plt.figure(figsize=(16, 9), facecolor=BG)
fig.text(0.03, 0.95, "Telecom Customer Churn Dashboard", fontsize=22, weight="bold", color=INK, va="center")
fig.text(0.03, 0.915, "Source: PostgreSQL view v_churn_dashboard | IBM Telco Customer Churn, 7,043 customers",
         fontsize=10, color=GREY, va="center")

# KPI tiles
kpis = [("Churn rate", f"{rate:.1f}%", f"{churned:,} of {total:,} customers"),
        ("Monthly revenue lost", f"${lost_m:,.0f}", f"{100 * lost_m / df.monthly_charges.sum():.1f}% of total MRR"),
        ("Annualized revenue lost", f"${lost_y / 1e6:.2f}M", "monthly lost x 12"),
        ("High-risk band churn", f"{100 * df[df.risk_band == 'High Risk'].churn_flag.mean():.1f}%",
         f"{(df.risk_band == 'High Risk').sum():,} customers")]
for i, (t, v, s) in enumerate(kpis):
    ax = fig.add_axes([0.03 + i * 0.2375, 0.76, 0.22, 0.11])
    ax.set_facecolor("white"); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#d9dee3")
    ax.text(0.05, 0.78, t, fontsize=10, color=GREY, transform=ax.transAxes)
    ax.text(0.05, 0.36, v, fontsize=24, weight="bold", color=RED if i else INK, transform=ax.transAxes)
    ax.text(0.05, 0.08, s, fontsize=8.5, color=GREY, transform=ax.transAxes)


def bar(ax, g, title, color=BLUE, hbar=False):
    labels = [str(x) for x in g.index]
    ax.set_facecolor("white")
    bars = (ax.barh if hbar else ax.bar)(labels, g["mean"], color=color)
    for b, v in zip(bars, g["mean"]):
        if hbar:
            ax.text(v + 0.8, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=9, color=INK)
        else:
            ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.1f}%", ha="center", fontsize=9, color=INK)
    ax.set_title(title, loc="left", fontsize=11, weight="bold", color=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=9)
    (ax.set_xlim if hbar else ax.set_ylim)(0, g["mean"].max() * 1.2)
    if hbar:
        ax.invert_yaxis()


c = rate_by("contract", ["Month-to-month", "One year", "Two year"])
bar(fig.add_axes([0.05, 0.40, 0.26, 0.28]), c, "Churn rate by contract (%)", [RED, BLUE, BLUE])

t = rate_by("tenure_bucket").sort_index()
t.index = [s.split(". ", 1)[1] for s in t.index]
bar(fig.add_axes([0.38, 0.40, 0.26, 0.28]), t, "Churn rate by tenure (%)", [RED, BLUE, BLUE, BLUE])

# risk band: churn rate
rb = rate_by("risk_band", ["High Risk", "Medium Risk", "Low Risk"])
bar(fig.add_axes([0.71, 0.40, 0.26, 0.28]), rb, "Actual churn rate by risk band (%)", [RED, "#e8a33d", BLUE])

# revenue lost by contract x internet
ax = fig.add_axes([0.15, 0.07, 0.16, 0.24]); ax.set_facecolor("white")
rl =(df[df.churn_flag == 1].groupby(["contract", "internet_service"]).monthly_charges.sum()
      .sort_values(ascending=False).head(5))
labs = [f"{a} / {b}" for a, b in rl.index]
ax.barh(labs, rl.values, color=RED); ax.invert_yaxis()
for i, v in enumerate(rl.values):
    ax.text(v + 800, i, f"${v:,.0f}", va="center", fontsize=9, color=INK)
ax.set_xlim(0, rl.max() * 1.45)
ax.set_xticks([0, 50000, 100000]); ax.set_xticklabels(["0", "50K", "100K"])
ax.set_title("Monthly revenue lost - top 5 segments", loc="left", fontsize=11, weight="bold", color=INK)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.tick_params(labelsize=8.5)

# risk band: revenue at stake
ax = fig.add_axes([0.40, 0.07, 0.24, 0.24]); ax.set_facecolor("white")
rs = df.groupby("risk_band").monthly_charges.sum().reindex(["High Risk", "Medium Risk", "Low Risk"])
ax.pie(rs, labels=[f"{k}\n${v:,.0f}" for k, v in rs.items()], colors=[RED, "#e8a33d", BLUE],
       wedgeprops=dict(width=0.45), textprops=dict(fontsize=9, color=INK), startangle=90)
ax.set_title("Monthly revenue by risk band", loc="left", fontsize=11, weight="bold", color=INK)

# payment method
pm = rate_by("payment_method").sort_values("mean", ascending=False)
bar(fig.add_axes([0.78, 0.07, 0.19, 0.24]), pm, "Churn rate by payment method (%)",
    [RED] + [BLUE] * 3, hbar=True)

fig.savefig(DASH / "churn_dashboard.png", dpi=130, facecolor=BG)
print("images written")
