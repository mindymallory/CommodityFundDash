"""Static PNG charts for Monte Carlo v2 (structural) — newsletter-ready."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import structural_config as SC


def _pct(ax, x, color="darkred", fmt="${:.2f}", y=0.92):
    s = np.percentile(x, [10, 50, 90])
    for v, lab in zip(s, ["P10", "P50", "P90"]):
        ax.axvline(v, color=color, linestyle="--", linewidth=1.2)
        ax.text(v, ax.get_ylim()[1] * y, f" {lab} {fmt.format(v)}",
                color=color, fontsize=9, va="top")
    return s


def price_overlay(base_draws, shock_draws, path, base_price):
    """(a) Price distribution: yield_minus5 vs base."""
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.hist(base_draws["price"], bins=60, range=(2.5, 9.0), color="steelblue",
            alpha=0.65, edgecolor="white", label="Base (WASDE #675)")
    ax.hist(shock_draws["price"], bins=60, range=(2.5, 9.0), color="darkorange",
            alpha=0.65, edgecolor="white", label="Yield shock -5 bu/ac")
    _pct(ax, base_draws["price"], color="navy", y=0.97)
    _pct(ax, shock_draws["price"], color="darkred", y=0.82)
    ax.axvline(base_price, color="black", linewidth=1.6,
               label=f"WASDE #675: ${base_price:.2f}")
    ax.set_xlim(2.5, 9.0)
    ax.set_xlabel("Season-average price ($/bu)")
    ax.set_ylabel("Draws")
    ax.set_title("Structural MC: 2026/27 corn price — base vs -5 bu/ac yield "
                 "shock (n=10,000)")
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def waterfall(det_base, det_shock, path, dS):
    """(b) Demand-rationing waterfall: how the supply cut splits across
    demand categories and ending stocks. Deterministic, median elasticities,
    no uncertainty."""
    from . import structural as S
    labels = ["Exports", "Ethanol\ngrind", "Feed &\nresidual",
              "Food/seed\n& other", "Ending\nstocks"]
    q0, q1 = det_base["q1"], det_shock["q1"]
    cuts = q0 - q1                      # M bu absorbed per category
    assert abs(cuts.sum() + dS) < 1e-6, "waterfall must sum to the shock"
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(labels))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#d62728"]
    bottoms = np.zeros(len(labels))
    cum = 0.0
    for i, (lab, c, col) in enumerate(zip(labels, cuts, colors)):
        ax.bar(i, c, bottom=cum, color=col, edgecolor="white", width=0.62)
        if c >= 30:
            ax.text(i, cum + c / 2, f"{c:.0f}", ha="center", va="center",
                    fontsize=10, color="white", fontweight="bold")
        else:
            ax.text(i, cum + c + 10, f"{c:.0f}", ha="center", va="bottom",
                    fontsize=10, fontweight="bold")
        cum += c
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Share of the supply cut absorbed (M bu)")
    ax.set_title(f"Where does a {abs(dS):.0f} M bu supply cut go?\n"
                 "Deterministic run at median elasticities — no uncertainty")
    ax.text(0.02, 0.96,
            "Price rises until demand falls by the full cut.\n"
            "Most-elastic demand (exports) absorbs the most;\n"
            "least-elastic (food/seed/other) absorbs the least.",
            transform=ax.transAxes, ha="left", va="top", fontsize=9,
            color="dimgray")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return cuts


def price_vs_shock(shock_grid, med, p10, p90, det_med, path):
    """(c) Price vs shock size (-10 to +5 bu/ac): MC median with P10-P90
    bands, plus the deterministic median-elasticity curve."""
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.fill_between(shock_grid, p10, p90, color="steelblue", alpha=0.25,
                    label="MC P10-P90 band")
    ax.plot(shock_grid, med, color="navy", linewidth=2, label="MC median")
    ax.plot(shock_grid, det_med, color="darkred", linestyle="--",
            linewidth=1.5, label="Deterministic (median elasticities)")
    ax.axvline(0, color="black", linewidth=1)
    ax.axhline(4.80, color="gray", linestyle=":", linewidth=1,
               label="WASDE #675: $4.80")
    ax.set_xlabel("Yield shock (bu/acre)")
    ax.set_ylabel("Season-average price ($/bu)")
    ax.set_title("Structural MC: corn price vs yield shock, -10 to +5 bu/acre\n"
                 "(n=10,000 per shock point)")
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def price_vs_stocks_v2(draws, price_params, path):
    """(d) Diagnostic overlay: v2 structural price cloud against v1's fitted
    inverse curve + history. v1's curve is shown, never used for pricing."""
    fig, ax = plt.subplots(figsize=(8, 5))
    su_grid = np.linspace(0.05, 0.25, 200)
    ax.plot(su_grid * 100, price_params["a"] + price_params["b"] / su_grid,
            color="black", linewidth=1.5,
            label="v1 fitted curve: P = a + b/(s/u)  [diagnostic only]")
    idx = np.random.default_rng(7).choice(len(draws["price"]), 3000,
                                          replace=False)
    ax.scatter(draws["stocks_use"][idx] * 100, draws["price"][idx],
               s=6, alpha=0.25, color="steelblue",
               label="v2 structural draws (3k shown)")
    ax.scatter(price_params["su"] * 100, price_params["px"],
               s=28, color="darkgreen", zorder=5,
               label="History 2010/11-2025/26")
    ax.scatter([9.69], [4.80], s=70, color="red", marker="*", zorder=6,
               label="WASDE #675 2026/27")
    ax.set_xlim(4, 26)
    ax.set_ylim(2, 12)
    ax.text(0.02, 0.98,
            "v2 prices structurally (demand rationing);\n"
            "the v1 curve is overlaid for comparison only.",
            transform=ax.transAxes, ha="left", va="top", fontsize=8,
            color="dimgray")
    ax.set_xlabel("Stocks-to-use (%)")
    ax.set_ylabel("Season-average price ($/bu)")
    ax.set_title("Diagnostic: v2 structural prices vs v1 fitted price curve")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
