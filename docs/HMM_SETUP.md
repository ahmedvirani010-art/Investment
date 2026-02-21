# HMM Regime Analysis — Recommended Setup

To run **true Hidden Markov Model (HMM)** regime detection (transition dynamics, Baum–Welch), use the following setup in order.

**Pipeline (7 assets):** The HMM applies to Bitcoin (BTC-USD), Gold (GC=F), Crude Oil (CL=F), Silver (SI=F), NASDAQ (^IXIC), NIKKEI (^N225), and S&P 500 (^GSPC). It uses **7 states**, **full covariance**, **5 engineered features** (log returns, realized vol 20d, normalized RSI 14, volume ratio 20d, momentum 20d), **10 random restarts**, **200 EM iterations**, and best model by log-likelihood. Regime labeling is by mean return. Run integrated HMM + spread analysis with: `py run_integrated_analysis.py` (writes to `price_data/hmm_regimes.db` and `price_data/spread_analysis.db`).

## 1. Python version

Use **Python 3.11 or 3.12**.  
`hmmlearn` has prebuilt wheels for these versions on Windows, so no C++ compiler is needed.

- **Python 3.14**: pip will try to build `hmmlearn` from source and will fail unless you install [Microsoft Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
- **Python 3.11 / 3.12**: `pip install hmmlearn` usually installs a wheel and works without Build Tools.

## 2. Create a virtual environment (recommended)

From the project root:

```powershell
# Windows: use py launcher for 3.11 or 3.12 if you have it
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies (in order)

With the venv activated:

```powershell
pip install --upgrade pip
pip install hmmlearn scikit-learn yfinance pandas numpy
```

Or install from the project’s requirements:

```powershell
pip install -r requirements.txt
```

If `hmmlearn` fails to install (e.g. on Python 3.14), the app will fall back to **Gaussian Mixture Model (GMM)** regime clustering; the dashboard will still work but without HMM transition dynamics.

## 4. Point the dashboard at this Python (optional)

If you run the app (e.g. `npm run dev`) and use **Run HMM** from the dashboard, the API spawns Python via `PYTHON_PATH` or the default `py` / `python3`. To use the venv:

**Windows (PowerShell):**

```powershell
$env:PYTHON_PATH = ".\.venv\Scripts\python.exe"
npm run dev
```

Or add to `.env` in the project root:

```
PYTHON_PATH=.venv/Scripts/python.exe
```

**macOS/Linux:** use `PYTHON_PATH=.venv/bin/python` (or the full path).

## 5. Verify

From the project root, with the same Python that the app will use:

```powershell
py scripts/api_hmm_regime.py BTC-USD --period 90d
```

You should see JSON with `"backend": "hmmlearn"`. If you see `"backend": "gmm"`, the fallback is in use (install `hmmlearn` with Python 3.11/3.12 as above).

## Summary order

1. Install **Python 3.11 or 3.12**.
2. Create and activate a **venv** with that Python.
3. **pip install** `hmmlearn scikit-learn yfinance` (and the rest of `requirements.txt` if you like).
4. Set **PYTHON_PATH** to the venv’s Python if the dashboard uses a different Python by default.
5. Run the app and use **HMM Regimes** in the dashboard; the result will show whether **hmmlearn** or **gmm** was used.
