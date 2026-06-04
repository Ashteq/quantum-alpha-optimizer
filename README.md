# ⚛️ Quantum-Alpha Portfolio Optimizer

A full-stack MVP that uses **QAOA (Quantum Approximate Optimisation Algorithm)** via
Qiskit to select an optimal binary subset of stocks from real market data.

```
FastAPI backend (port 8000)  ←→  Streamlit frontend (port 8501)
         ↑                                  ↑
    yfinance + Qiskit                  Plotly charts
```

---

## Architecture

```
quantum-alpha-optimizer/
├── backend/
│   ├── main.py            # FastAPI app — POST /optimize endpoint
│   ├── market_data.py     # yfinance → mu (returns) + sigma (cov matrix)
│   ├── quantum_solver.py  # QAOA via Qiskit → binary selection vector
│   └── requirements.txt
└── frontend/
    ├── app.py             # Streamlit UI + Plotly charts
    └── requirements.txt
```

---

## Quick Start (WSL / Ubuntu)

### 1. Prerequisites

```bash
sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip -y
```

### 2. Backend setup

```bash
cd quantum-alpha-optimizer/backend

python3.11 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Start the API server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

✅ Backend is ready at `http://localhost:8000`
📄 Auto-docs at `http://localhost:8000/docs`

### 3. Frontend setup (new terminal)

```bash
cd quantum-alpha-optimizer/frontend

python3.11 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Start Streamlit
streamlit run app.py --server.port 8501
```

✅ Frontend is ready at `http://localhost:8501`

---

## API Reference

### `POST /optimize`

**Request body (JSON)**

| Field         | Type    | Default | Description                                |
|---------------|---------|---------|--------------------------------------------|
| `tickers`     | list    | —       | 2–10 stock ticker symbols                  |
| `budget`      | int     | auto    | Number of assets to select                 |
| `risk_factor` | float   | 0.5     | Risk aversion q ∈ [0, 1]                  |
| `qaoa_reps`   | int     | 1       | QAOA circuit depth p ∈ {1, 2, 3}          |

**Example**

```bash
curl -s -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL","MSFT","GOOGL","AMZN"], "budget": 2, "risk_factor": 0.5}' \
  | python3 -m json.tool
```

**Response fields**

- `selected_tickers` — assets chosen by QAOA
- `selection_vector` — raw binary vector (length = n)
- `portfolio_expected_return` — annualised return of selected portfolio
- `portfolio_variance` — annualised variance
- `sharpe_proxy` — return / sqrt(variance)
- `elapsed_seconds` — server-side wall time

---

## Optimisation Formulation

The problem is a **Quadratic Unconstrained Binary Optimisation (QUBO)**:

```
minimise   q · xᵀ Σ x  −  (1−q) · μᵀ x
subject to Σ xᵢ = B,   xᵢ ∈ {0, 1}
```

- `x`  — binary selection vector  
- `Σ`  — annualised covariance matrix (risk)  
- `μ`  — annualised expected return vector  
- `q`  — risk-aversion coefficient  
- `B`  — budget (number of assets)

Solved by `PortfolioOptimization` → `MinimumEigenOptimizer(QAOA)` from Qiskit.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ConnectionError` in frontend | Ensure backend is running on port 8000 |
| `ValueError: Only 1 valid ticker` | One of your tickers may be delisted or misspelled |
| QAOA timeout | Reduce tickers to ≤ 6 or set `qaoa_reps=1` |
| `ModuleNotFoundError: qiskit_finance` | Re-run `pip install qiskit-finance==0.4.0` |
| Port already in use | `lsof -i :8000` then `kill <PID>` |

---

## Notes for WSL Users

- Use `0.0.0.0` (not `127.0.0.1`) when starting uvicorn so Windows browsers can reach it.
- If using WSL2, the Windows IP is reachable via `$(hostname -I | awk '{print $1}')`.
- Streamlit and FastAPI can each run in their own WSL terminal pane.
