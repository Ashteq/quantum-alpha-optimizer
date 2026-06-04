"""
main.py
-------
FastAPI application for the Quantum-Alpha Portfolio Optimizer.

Endpoints
---------
GET  /          → health check
POST /optimize  → run full quantum optimisation pipeline

CORS is configured to accept requests from the Streamlit frontend on
http://localhost:8501 (and the wildcard for dev convenience).

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Author : Quantum-Alpha Team
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from market_data import fetch_market_data
from quantum_solver import QuantumOptimisationResult, solve_portfolio

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Quantum-Alpha Portfolio Optimizer API",
    version="1.0.0",
    description=(
        "Combines yfinance market data with a QAOA-based "
        "binary portfolio selection solver (Qiskit)."
    ),
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow the Streamlit frontend (8501) and any localhost origin during dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://0.0.0.0:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class OptimiseRequest(BaseModel):
    """Payload accepted by ``POST /optimize``."""

    tickers: list[str]
    budget: Optional[int] = None          # None → auto (ceil(n/2))
    risk_factor: float = 0.5              # 0 = max return, 1 = min risk
    qaoa_reps: int = 1                    # QAOA circuit depth p

    @field_validator("tickers")
    @classmethod
    def at_least_two_tickers(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip().upper() for t in v if t.strip()]
        if len(cleaned) < 2:
            raise ValueError("Please provide at least 2 tickers.")
        if len(cleaned) > 10:
            raise ValueError(
                "Maximum 10 tickers supported (quantum circuit size limit)."
            )
        return cleaned

    @field_validator("risk_factor")
    @classmethod
    def valid_risk_factor(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("risk_factor must be in [0, 1].")
        return v

    @field_validator("qaoa_reps")
    @classmethod
    def valid_reps(cls, v: int) -> int:
        if not (1 <= v <= 3):
            raise ValueError("qaoa_reps must be between 1 and 3.")
        return v


class AssetDetail(BaseModel):
    ticker: str
    expected_return: float
    weight: float                         # equal-weight among selected assets


class OptimiseResponse(BaseModel):
    """JSON payload returned by ``POST /optimize``."""

    selected_tickers: list[str]
    selection_vector: list[int]
    all_tickers: list[str]
    asset_details: list[AssetDetail]
    portfolio_expected_return: float      # annualised
    portfolio_variance: float             # annualised
    sharpe_proxy: float
    objective_value: float
    elapsed_seconds: float
    solver_metadata: dict


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
async def root() -> dict:
    """Health check — confirms the API is running."""
    return {"status": "ok", "service": "quantum-alpha-optimizer"}


@app.post("/optimize", response_model=OptimiseResponse, tags=["portfolio"])
async def optimize(payload: OptimiseRequest) -> OptimiseResponse:
    """
    Run the full QAOA portfolio optimisation pipeline.

    1. Fetch 1-year daily closing prices via yfinance.
    2. Compute expected returns (mu) and covariance matrix (sigma).
    3. Formulate a binary selection QUBO with ``PortfolioOptimization``.
    4. Solve with QAOA + COBYLA via the Qiskit local Sampler.
    5. Return the optimised binary portfolio with statistics.
    """
    t_start = time.perf_counter()

    logger.info(
        "▶ /optimize called | tickers=%s | budget=%s | q=%.2f | p=%d",
        payload.tickers, payload.budget, payload.risk_factor, payload.qaoa_reps,
    )

    # ── Step 1: Market data ───────────────────────────────────────────────────
    try:
        mu, sigma, valid_tickers = fetch_market_data(payload.tickers)
    except ValueError as exc:
        logger.error("Market data error: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected market data error")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market data: {exc}",
        )

    # ── Step 2: Quantum solver ────────────────────────────────────────────────
    try:
        result: QuantumOptimisationResult = solve_portfolio(
            mu=mu,
            sigma=sigma,
            tickers=valid_tickers,
            budget=payload.budget,
            risk_factor=payload.risk_factor,
            qaoa_reps=payload.qaoa_reps,
        )
    except ValueError as exc:
        logger.error("Solver error: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected solver error")
        raise HTTPException(
            status_code=500,
            detail=f"Quantum solver failed: {exc}",
        )

    # ── Step 3: Build response ────────────────────────────────────────────────
    n_selected = len(result.selected_tickers)
    equal_weight = 1.0 / n_selected if n_selected > 0 else 0.0

    asset_details = [
        AssetDetail(
            ticker=t,
            expected_return=float(mu[valid_tickers.index(t)]),
            weight=equal_weight,
        )
        for t in result.selected_tickers
    ]

    elapsed = time.perf_counter() - t_start

    logger.info(
        "✅ Optimisation complete in %.2fs | selected=%s",
        elapsed,
        result.selected_tickers,
    )

    return OptimiseResponse(
        selected_tickers=result.selected_tickers,
        selection_vector=result.selection_vector,
        all_tickers=valid_tickers,
        asset_details=asset_details,
        portfolio_expected_return=result.expected_return,
        portfolio_variance=result.expected_variance,
        sharpe_proxy=result.sharpe_proxy,
        objective_value=result.objective_value,
        elapsed_seconds=round(elapsed, 3),
        solver_metadata=result.solver_metadata,
    )
