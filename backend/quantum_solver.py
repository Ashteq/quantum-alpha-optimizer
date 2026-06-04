"""
quantum_solver.py
-----------------
Formulates a Markowitz-style binary portfolio selection problem and solves it
using the Quantum Approximate Optimisation Algorithm (QAOA) via Qiskit.

The optimisation objective is:

    minimise   q * xᵀ Σ x  -  (1 - q) * μᵀ x

subject to  x ∈ {0, 1}ⁿ  (binary asset inclusion)
            Σ xᵢ = B       (budget constraint: pick exactly B assets)

where
  x  – binary selection vector
  Σ  – annualised covariance matrix (risk)
  μ  – annualised expected return vector
  q  – risk appetite ∈ [0, 1]  (0 = pure return, 1 = pure risk minimisation)
  B  – budget (number of assets to select)

Author : Quantum-Alpha Team
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# ── Qiskit imports ────────────────────────────────────────────────────────────
from qiskit.primitives import Sampler
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_finance.applications.optimization import PortfolioOptimization
from qiskit_optimization.algorithms import MinimumEigenOptimizer

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class QuantumOptimisationResult:
    """Typed container returned by :func:`solve_portfolio`."""

    selected_tickers: list[str]             # assets chosen (x_i = 1)
    selection_vector: list[int]             # raw binary vector
    objective_value: float                  # QUBO objective at solution
    expected_return: float                  # annualised expected return
    expected_variance: float                # annualised portfolio variance
    sharpe_proxy: float                     # return / sqrt(variance) proxy
    solver_metadata: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def solve_portfolio(
    mu: np.ndarray,
    sigma: np.ndarray,
    tickers: list[str],
    budget: Optional[int] = None,
    risk_factor: float = 0.5,
    qaoa_reps: int = 1,
    max_iter: int = 150,
) -> QuantumOptimisationResult:
    """Run QAOA-based portfolio optimisation.

    Parameters
    ----------
    mu         : np.ndarray, shape (n,)
        Annualised expected return vector.
    sigma      : np.ndarray, shape (n, n)
        Annualised covariance matrix.
    tickers    : list[str]
        Asset names corresponding to the rows/columns of *sigma*.
    budget     : int, optional
        Number of assets to select.  Defaults to ``ceil(n / 2)``.
    risk_factor: float
        Risk-aversion coefficient *q* ∈ [0, 1].  Higher → more risk-averse.
    qaoa_reps  : int
        Number of QAOA layers *p*.  More layers → better approximation,
        but longer runtime.  Keep at 1 for an MVP demo.
    max_iter   : int
        Maximum COBYLA iterations for the variational optimiser.

    Returns
    -------
    QuantumOptimisationResult
    """
    n = len(tickers)
    if n < 2:
        raise ValueError("Need at least 2 assets to optimise a portfolio.")

    # ── Clamp budget ──────────────────────────────────────────────────────────
    if budget is None:
        budget = max(1, int(np.ceil(n / 2)))
    budget = int(np.clip(budget, 1, n))

    logger.info(
        "Quantum solver | n=%d assets | budget=%d | q=%.2f | p=%d",
        n, budget, risk_factor, qaoa_reps,
    )

    # ── 1. Build QUBO via PortfolioOptimization ───────────────────────────────
    portfolio_problem = PortfolioOptimization(
        expected_returns=mu,
        covariances=sigma,
        risk_factor=risk_factor,
        budget=budget,
    )
    qubo = portfolio_problem.to_quadratic_program()
    logger.info("QUBO formulated:\n%s", qubo.export_as_lp_string())

    # ── 2. Construct QAOA with local Sampler ──────────────────────────────────
    sampler = Sampler()                       # statevector-based local sampler

    optimizer = COBYLA(maxiter=max_iter)      # gradient-free classical optimiser

    qaoa = QAOA(
        sampler=sampler,
        optimizer=optimizer,
        reps=qaoa_reps,
    )

    # ── 3. Wrap in MinimumEigenOptimizer and solve ────────────────────────────
    meo = MinimumEigenOptimizer(qaoa)

    logger.info("Starting QAOA optimisation …")
    result = meo.solve(qubo)
    logger.info("QAOA finished — raw result: %s", result)

    # ── 4. Parse result ───────────────────────────────────────────────────────
    x: np.ndarray = np.array(result.x, dtype=int)   # binary selection vector

    # Fallback: if all zeros (degenerate solution), pick top-B by return
    if x.sum() == 0:
        logger.warning(
            "QAOA returned all-zero selection; falling back to greedy heuristic."
        )
        x = _greedy_fallback(mu, budget)

    selected_indices = np.where(x == 1)[0]
    selected_tickers = [tickers[i] for i in selected_indices]

    # Portfolio statistics
    port_return = float(mu @ x)
    port_variance = float(x @ sigma @ x)
    sharpe_proxy = (
        port_return / np.sqrt(port_variance) if port_variance > 1e-12 else 0.0
    )

    return QuantumOptimisationResult(
        selected_tickers=selected_tickers,
        selection_vector=x.tolist(),
        objective_value=float(result.fval),
        expected_return=port_return,
        expected_variance=port_variance,
        sharpe_proxy=sharpe_proxy,
        solver_metadata={
            "n_assets": n,
            "budget": budget,
            "risk_factor": risk_factor,
            "qaoa_reps": qaoa_reps,
            "max_iter": max_iter,
            "status": str(result.status),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _greedy_fallback(mu: np.ndarray, budget: int) -> np.ndarray:
    """Return a binary vector selecting the *budget* highest-return assets."""
    x = np.zeros(len(mu), dtype=int)
    top_k = np.argsort(mu)[::-1][:budget]
    x[top_k] = 1
    return x
