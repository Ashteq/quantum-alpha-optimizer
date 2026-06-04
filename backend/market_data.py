"""
market_data.py
--------------
Fetches historical daily closing prices for a list of stock tickers using yfinance,
then computes the expected return vector (mu) and the annualised covariance matrix
(sigma) needed by the portfolio optimiser.

Author : Quantum-Alpha Team
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
import requests # <-- 1. Add this import at the top

def fetch_market_data(tickers: list[str]):
    # 2. Create a custom session with a human browser header
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    })
    
    # 3. Pass the session into the download function
    # (Adjust the period or interval if your Claude code had different parameters)
    data = yf.download(tickers, period="1y", session=session)
    
    if data.empty:
        raise ValueError(f"Yahoo Finance returned no data for tickers: {tickers}. They might be invalid or delisted.")

# ── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ── Constants ─────────────────────────────────────────────────────────────────
TRADING_DAYS_PER_YEAR: int = 252          # standard annualisation factor
LOOKBACK_PERIOD: str = "1y"               # yfinance period string → 1 calendar year


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_market_data(
    tickers: list[str],
    period: str = LOOKBACK_PERIOD,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Download closing prices and compute mu / sigma.

    Parameters
    ----------
    tickers : list[str]
        Upper-case stock ticker symbols, e.g. ["AAPL", "MSFT", "GOOGL"].
    period  : str
        yfinance period string (default ``"1y"``).

    Returns
    -------
    mu     : np.ndarray, shape (n,)
        Annualised expected return for each valid ticker.
    sigma  : np.ndarray, shape (n, n)
        Annualised covariance matrix.
    valid_tickers : list[str]
        Tickers that survived the data-quality filters (subset of *tickers*).

    Raises
    ------
    ValueError
        If fewer than 2 valid tickers remain after cleaning.
    """
    tickers = _sanitise_tickers(tickers)
    logger.info("Fetching %d tickers: %s", len(tickers), tickers)

    # ── 1. Download ──────────────────────────────────────────────────────────
    raw: pd.DataFrame = yf.download(
        tickers,
        period=period,
        auto_adjust=True,          # adjusted for splits / dividends
        progress=False,
        threads=True,
    )["Close"]

    # yfinance returns a Series when only one ticker is requested;
    # normalise to a DataFrame in every case.
    if isinstance(raw, pd.Series):
        raw = raw.to_frame(name=tickers[0])

    # ── 2. Clean ─────────────────────────────────────────────────────────────
    prices = _clean_prices(raw, tickers)

    # ── 3. Compute returns ───────────────────────────────────────────────────
    daily_returns: pd.DataFrame = prices.pct_change().dropna()

    if daily_returns.empty or len(daily_returns) < 30:
        raise ValueError(
            "Insufficient price history. "
            "Check that the tickers are valid and traded on a major exchange."
        )

    # ── 4. Annualised statistics ──────────────────────────────────────────────
    mu: np.ndarray = (
        daily_returns.mean().values * TRADING_DAYS_PER_YEAR
    )                                             # shape (n,)

    sigma: np.ndarray = (
        daily_returns.cov().values * TRADING_DAYS_PER_YEAR
    )                                             # shape (n, n)

    valid_tickers: list[str] = daily_returns.columns.tolist()

    logger.info(
        "Market data ready — %d assets, mu range [%.4f, %.4f]",
        len(valid_tickers),
        mu.min(),
        mu.max(),
    )

    return mu, sigma, valid_tickers


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sanitise_tickers(tickers: list[str]) -> list[str]:
    """Strip whitespace, convert to upper-case, de-duplicate."""
    seen: set[str] = set()
    clean: list[str] = []
    for t in tickers:
        t = t.strip().upper()
        if t and t not in seen:
            clean.append(t)
            seen.add(t)
    if not clean:
        raise ValueError("No valid tickers provided.")
    return clean


def _clean_prices(
    prices: pd.DataFrame,
    requested: list[str],
) -> pd.DataFrame:
    """Drop tickers with excessive missing data and forward-fill minor gaps."""

    # Drop columns that are entirely NaN (ticker not found / delisted)
    prices = prices.dropna(axis=1, how="all")

    # Warn about any tickers that disappeared
    missing = set(requested) - set(prices.columns)
    if missing:
        logger.warning("Tickers not found / no data: %s", sorted(missing))

    # Forward-fill up to 5 consecutive missing days (holidays, etc.)
    prices = prices.ffill(limit=5)

    # Drop columns that still have > 5 % NaN after filling
    threshold = 0.95
    prices = prices.dropna(thresh=int(len(prices) * threshold), axis=1)

    # Drop remaining rows with any NaN (aligns all series to common dates)
    prices = prices.dropna()

    remaining = prices.columns.tolist()
    if len(remaining) < 2:
        raise ValueError(
            f"Only {len(remaining)} valid ticker(s) remain after cleaning: "
            f"{remaining}. Please provide at least 2 tradeable tickers."
        )

    logger.info("Clean price matrix: %d rows × %d tickers", *prices.shape)
    return prices
