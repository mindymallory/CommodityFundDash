"""Static PNG charts for Monte Carlo v3-world (global) — newsletter-ready."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import world_config as WC
from . import world as W

SCENARIO_STYLE = {
    "base_global":   {"color": "steelblue", "label": "Base (global model)"},
    "brazil_bumper": {"color": "forestgreen", "label": "Brazil bumper (+500 M bu)"},
    "brazil_drought": {"color": "darkred",   "label": "Brazil drought (-500 M bu)"},
    "china_surge":   {"color": "darkorange", "label": "China surge (+200 M bu)"},
}


def price_scenarios(results, path):
    """(a) U.S. price distributions: base vs bumper/drought/china_surge."""
    names = ["base_global", "brazil_bumper", "brazil_drought", "china_surge"]
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    lo = min(np.percentile(results[n]["draws"]["price"], 1) for n in names)
    hi = max(np.percentile(results[n]["draws"]["price"], 99) for n in names)
    lo, hi = math_floor(lo), math_ceil(hi)
    for n in names:
        st = SCENARIO_STYLE[n]
        p = results[n]["draws"]["price"]
        ax.hist(p, bins=60, range=(lo, hi), color=st["color"], alpha=0.55,
                edgecolor="white", linewidth=0.4, label=st["label"])
        p50 = np.percentile(p, 50)
        ax.axvline(p50, color=st["color"], linestyle="--", linewidth=1.6)
        ax.text(p50, ax.get_ylim()[1] * 0.96, f" P50 ${p50:.2f}",
                color=st["color"], fontsize=9, va="top", fontweight="bold")
    ax.axvline(WC.P0, color="black", linewidth=1.4,
               label=f"WASDE #675: ${WC.P0:.2f}")
    ax.set_xlim(lo, hi)
    ax.set_xlabel("Season-average U.S. corn price ($/bu)")
    ax.set_ylabel("Draws")
    ax.set_title("Global MC: 2026/27 U.S. corn price by scenario (n=10,000 each)")
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def math_floor(x):
    import math
    return math.floor(x * 2) / 2


def math_ceil(x):
    import math
    return math.ceil(x * 2) / 2


def china_capture(capture, level_shares, path):
    """(b) Stacked bar: who supplies the marginal bushels of the +200 M bu
    China surge (structural marginal capture, not the logit level split)."""
    origins = ["US", "BR", "AR", "UP"]
    colors = {"US": "#1f77b4", "BR": "#2ca02c", "AR": "#ff7f0e",
              "UP": "#9467bd"}
    vals = np.array([capture[o] for o in origins])  # fractions of the +200
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    left = 0.0
    for o in origins:
        v = vals[origins.index(o)]
        ax.barh(0, v, left=left, color=colors[o], edgecolor="white",
                height=0.45, label=o)
        if v > 0.03:
            ax.text(left + v / 2, 0, f"{o}\n{v*100:.0f}%",
                    ha="center", va="center", fontsize=10, color="white",
                    fontweight="bold")
        left += v
    ax.set_xlim(0, max(1.0, left * 1.02))
    ax.set_ylim(-0.6, 0.6)
    ax.set_yticks([])
    ax.set_xlabel("Share of the +200 M bu China import surge")
    ax.set_title("China +200 M bu surge: marginal capture by origin "
                 "(equilibrium exports, surge vs base)")
    ax.legend(fontsize=9, loc="upper right", title="Origin")
    lvl = ", ".join(f"{o} {level_shares[o]*100:.0f}%"
                    for o in origins)
    ax.text(0.01, -0.52,
            "Level split of China's total buys (logit on landed cost): " + lvl
            + "\nCapture sums to ~68%, not 100%: the higher clearing price "
            "rations ~60 M bu of rest-of-world import demand, so only ~140 M bu "
            "of extra exports are needed.",
            transform=ax.transAxes, fontsize=8, va="top", color="dimgray")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def export_curve(path):
    """(c) U.S. export demand curve: v2 constant-elasticity vs the global
    residual curve at median parameters, plus the residual curve shifted by
    the Brazil bumper (+500 M bu)."""
    P = np.linspace(3.0, 7.0, 200)
    v2 = W.v2_export_curve(P)
    base = W.residual_export_curve(P)
    bumper = W.residual_export_curve(P, dProd_BR=500.0)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(P, v2, color="gray", linestyle="--", linewidth=1.8,
            label="v2: constant-elasticity (eps=-1.0)")
    ax.plot(P, base, color="steelblue", linewidth=2.2,
            label="Global residual (base, median params)")
    ax.plot(P, bumper, color="forestgreen", linewidth=2.2,
            label="Global residual (Brazil +500 M bu)")
    ax.scatter([WC.P0], [3275.0], color="black", s=60, zorder=5,
               label="WASDE #675 point ($4.80, 3,275 M bu)")
    ax.annotate("", xy=(4.8, float(W.residual_export_curve(
        np.array([4.8]), dProd_BR=500.0)[0])), xytext=(4.8, 3275.0),
                arrowprops=dict(arrowstyle="<->", color="forestgreen",
                                linewidth=1.4))
    ax.text(4.85, 3050, "bumper shifts\nthe curve down\n~500 M bu",
            fontsize=9, color="forestgreen", va="top")
    ax.set_xlim(3.0, 7.0)
    ax.set_xlabel("U.S. corn price ($/bu)")
    ax.set_ylabel("U.S. export demand (M bu)")
    ax.set_title("U.S. export demand: v2 fixed curve vs global residual curve")
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
