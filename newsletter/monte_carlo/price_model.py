"""Stocks-to-use -> season-average price model (Westcott-Hoffman inverse form).

Fits P = a + b / (stocks-to-use) on HIST_BALANCE finals (2010/11-2025/26).
"""
import numpy as np
import openpyxl

from . import config as C


def load_history():
    """Return (stocks_use_ratio, price) arrays for 2010/11-2025/26 finals."""
    wb = openpyxl.load_workbook(C.WORKBOOK, data_only=False)
    ws = wb["HIST_BALANCE"]
    su, px = [], []
    for r in range(4, 20):  # rows 4-19 = 2010/11..2025/26 finals
        use = ws.cell(r, 13).value      # M: total use
        end = ws.cell(r, 14).value      # N: ending stocks
        price = ws.cell(r, 16).value    # P: season avg price
        assert use and end and price, f"missing history at row {r}"
        su.append(end / use)
        px.append(price)
    return np.array(su), np.array(px)


def fit(su=None, px=None):
    """Fit P = a + b/(s/u). Returns dict with params, R^2, n."""
    if su is None or px is None:
        su, px = load_history()
    X = np.vstack([np.ones_like(su), 1.0 / su]).T
    (a, b), *_ = np.linalg.lstsq(X, px, rcond=None)
    pred = X @ np.array([a, b])
    r2 = 1 - ((px - pred) ** 2).sum() / ((px - px.mean()) ** 2).sum()
    return {"a": float(a), "b": float(b), "r2": float(r2), "n": len(su),
            "su": su, "px": px, "pred": pred}


def predict(su_ratio, params):
    """Apply fitted curve. su_ratio may be scalar or array."""
    return params["a"] + params["b"] / np.asarray(su_ratio)
