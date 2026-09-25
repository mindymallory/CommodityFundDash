"""Static PNG charts for the newsletter (matplotlib)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import config as C


def _pct_lines(ax, x, color="darkred"):
    s = np.percentile(x, [10, 50, 90])
    for v, lab in zip(s, ["P10", "P50", "P90"]):
        ax.axvline(v, color=color, linestyle="--", linewidth=1.2)
        ax.text(v, ax.get_ylim()[1] * 0.92, f" {lab} {v:,.0f}" if v > 20
                else f" {lab} {v:.2f}", color=color, fontsize=9,
                rotation=0, va="top")
    return s


def ending_stocks_hist(draws, summary, path, base_val):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = draws["ending"]
    lo, hi = -200, 3500  # display window; tails annotated, not hidden
    ax.hist(x[(x >= lo) & (x <= hi)], bins=60, color="steelblue",
            edgecolor="white", alpha=0.85)
    _pct_lines(ax, x)
    ax.axvline(base_val, color="black", linewidth=1.6, label="WASDE #675: 1,567")
    tail_lo = (x < lo).mean() * 100
    tail_hi = (x > hi).mean() * 100
    ax.text(0.98, 0.85,
            f"{tail_lo:.1f}% of draws < {lo:,}\n{tail_hi:.1f}% of draws > {hi:,}",
            transform=ax.transAxes, ha="right", va="top", fontsize=8,
            color="dimgray")
    ax.set_xlim(lo, hi)
    ax.set_xlabel("2026/27 ending stocks (M bu)")
    ax.set_ylabel("Draws")
    ax.set_title("Monte Carlo: 2026/27 U.S. corn ending stocks (n=10,000)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def price_hist(draws, summary, path, base_val):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = draws["price"]
    lo, hi = 2.0, 12.0  # display window; the inverse curve blows up as
    # stocks-to-use -> 0, so extreme tails are annotated, not hidden
    ax.hist(x[(x >= lo) & (x <= hi)], bins=60, color="darkgreen",
            edgecolor="white", alpha=0.85)
    s = np.percentile(x, [10, 50, 90])
    for v, lab in zip(s, ["P10", "P50", "P90"]):
        ax.axvline(v, color="darkred", linestyle="--", linewidth=1.2)
        ax.text(v, ax.get_ylim()[1] * 0.92, f" {lab} ${v:.2f}",
                color="darkred", fontsize=9, va="top")
    ax.axvline(base_val, color="black", linewidth=1.6,
               label="WASDE #675: $4.80")
    tail_lo = (x < lo).mean() * 100
    tail_hi = (x > hi).mean() * 100
    ax.text(0.98, 0.85,
            f"{tail_lo:.1f}% of draws < ${lo:.0f}\n{tail_hi:.1f}% of draws > ${hi:.0f}\n"
            "(left tail = near-zero stocks-to-use draws)",
            transform=ax.transAxes, ha="right", va="top", fontsize=8,
            color="dimgray")
    ax.set_xlim(lo, hi)
    ax.set_xlabel("Season-average price ($/bu)")
    ax.set_ylabel("Draws")
    ax.set_title("Monte Carlo: 2026/27 U.S. corn season-average price (n=10,000)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def price_vs_stocks(draws, price_params, path):
    """Draw cloud + fitted curve + historical points + WASDE point."""
    fig, ax = plt.subplots(figsize=(8, 5))
    su_grid = np.linspace(0.05, 0.25, 200)
    ax.plot(su_grid * 100, price_params["a"] + price_params["b"] / su_grid,
            color="black", linewidth=1.5, label="Fitted: P = a + b/(s/u)")
    idx = np.random.default_rng(7).choice(len(draws["price"]), 3000,
                                          replace=False)
    ax.scatter(draws["stocks_use"][idx] * 100, draws["price"][idx],
               s=6, alpha=0.25, color="steelblue", label="MC draws (3k shown)")
    ax.scatter(price_params["su"] * 100, price_params["px"],
               s=28, color="darkgreen", zorder=5,
               label="History 2010/11-2025/26")
    ax.scatter([C.BASE_STOCKS_USE * 100], [C.BASE_PRICE], s=70,
               color="red", marker="*", zorder=6, label="WASDE #675 2026/27")
    ax.set_xlim(4, 26)
    ax.set_ylim(2, 12)
    ax.text(0.02, 0.98,
            "Axes clipped: 8.8% of draws fall outside $2–$12\n"
            "(inverse curve explodes as stocks-to-use → 0)",
            transform=ax.transAxes, ha="left", va="top", fontsize=8,
            color="dimgray")
    ax.set_xlabel("Stocks-to-use (%)")
    ax.set_ylabel("Season-average price ($/bu)")
    ax.set_title("Price vs stocks-to-use: fitted curve and MC cloud")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def scenario_delta(base_summary, shock_summary, path):
    labels = ["P50 price ($/bu)", "P50 ending (M bu)", "P(s/u<10%) (%)"]
    b = [base_summary["price"]["p50"], base_summary["ending"]["p50"],
         base_summary["p_su_lt_10"] * 100]
    s = [shock_summary["price"]["p50"], shock_summary["ending"]["p50"],
         shock_summary["p_su_lt_10"] * 100]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    w = 0.35
    ax.bar(x - w / 2, b, w, label="Base (WASDE #675)", color="steelblue")
    ax.bar(x + w / 2, s, w, label="-5 bu/ac yield shock (-443 M bu)",
           color="darkorange")
    for i in range(len(labels)):
        ax.text(i - w / 2, b[i], f"{b[i]:,.1f}", ha="center", va="bottom",
                fontsize=9)
        ax.text(i + w / 2, s[i], f"{s[i]:,.1f}", ha="center", va="bottom",
                fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_title("Scenario delta: -5 bu/acre yield shock vs base")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
