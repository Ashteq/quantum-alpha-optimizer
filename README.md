# Quantum-Alpha Portfolio Optimizer

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.25+-FF4B4B.svg)
![Qiskit](https://img.shields.io/badge/Qiskit-Quantum-6929C4.svg)

A full-stack, quantum-inspired web application designed to translate raw market data into precision asset allocation. The system utilizes Quadratic Unconstrained Binary Optimization (QUBO) and the Quantum Approximate Optimization Algorithm (QAOA) to solve complex financial selection problems.

### Video Demonstration
https://github.com/Ashteq/quantum-alpha-optimizer/blob/main/demo%201.mp4
## System Architecture

The project is built on a decoupled microservice architecture to ensure high scalability and a strict separation of concerns.

* **Frontend (Streamlit):** A responsive interface featuring interactive Plotly data visualizations. The user interface is engineered with a high-contrast retro aesthetic and includes dynamic fault tolerance mechanisms.
* **Backend (FastAPI):** A high-performance REST API handling asynchronous client requests and coordinating the quantum mathematical pipeline.
* **Data Ingestion (yfinance):** Automatically fetches live historical asset pricing and calculates expected returns and covariance matrices.
* **Quantum Engine (Qiskit):** Formulates the portfolio optimization problem as a QUBO and executes a local QAOA simulator to determine the optimal binary asset selection.

## Key Features

* **Algorithmic Asset Selection:** Bypasses traditional continuous-weight models in favor of a discrete, binary selection model optimized for quantum simulators.
* **Fault-Tolerant UI (Fallback Demo Mode):** The frontend includes a self-healing interface. If the FastAPI backend is unreachable due to network latency or server suspension, the frontend intercepts the HTTP error and automatically initializes a local mock data generation sequence. This guarantees the dashboard remains interactive for demonstration purposes under varying network conditions.
* **Data Visualization:** Translates complex quantum state outputs into accessible, interactive financial charts.

## Local Environment Setup

The following instructions assume a Linux or WSL (Windows Subsystem for Linux) environment.

**1. Clone the repository:**
```bash
git clone [https://github.com/YOUR-USERNAME/quantum-alpha-optimizer.git](https://github.com/YOUR-USERNAME/quantum-alpha-optimizer.git)
cd quantum-alpha-optimizer
