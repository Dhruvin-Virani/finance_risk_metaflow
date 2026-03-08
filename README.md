# Personal Finance Risk Analyzer

A Metaflow pipeline that takes your raw financial inputs — salary, expenses,
investments, age, and goals — and produces a risk-scored portfolio recommendation
backed by a Monte Carlo simulation.

<img width="1902" height="1055" alt="image" src="https://github.com/user-attachments/assets/642f3845-7802-4deb-b382-473eaae513ef" />


---

## Pipeline Overview

```
start
  └─ extract_features     derive financial ratios from raw inputs
       └─ score_risk       compute 0–100 composite risk score
            └─ simulate_investments   Monte Carlo projection (1000 paths)
                 └─ recommend_portfolio   map score → allocation + advice
                      └─ end            print final report
```

---

## Project Structure

```
finance_risk_metaflow/
├── flow.py                    # Metaflow FlowSpec — pipeline entry point
├── modules/
│   ├── feature_extraction.py  # Step 1: financial KPI derivation
│   ├── risk_scoring.py        # Step 2: composite risk scoring
│   ├── simulation.py          # Step 3: Monte Carlo simulation
│   └── portfolio.py           # Step 4: allocation table + advice
├── data/
│   └── sample_input.json      # Example inputs to try
└── requirements.txt
```

---

## Inputs

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `--salary` | float | Annual gross income | 1,200,000 |
| `--expenses` | float | Annual total expenses | 720,000 |
| `--age` | int | Current age | 32 |
| `--investments` | JSON string | Current holdings by asset class | see below |
| `--goals` | JSON string | List of financial goals | see below |
| `--n_simulations` | int | Monte Carlo paths to run | 1000 |

**investments format:**
```json
{"equity": 300000, "bonds": 100000, "gold": 80000, "cash": 60000}
```

**goals format:**
```json
[
  {"name": "Home purchase",    "target_amount": 3000000,  "years_to_achieve": 7},
  {"name": "Child education",  "target_amount": 1500000,  "years_to_achieve": 15},
  {"name": "Retirement corpus","target_amount": 20000000, "years_to_achieve": 28}
]
```

All amounts are in the same currency unit (INR in samples, but the math is currency-agnostic).

---

## Quick Start

### Option A — CLI only (no Docker needed)

```bash
pip install -r requirements.txt

# Run with built-in defaults
python3 flow.py run

# Run with custom inputs
python3 flow.py run \
  --salary 1500000 \
  --expenses 900000 \
  --age 35 \
  --investments '{"equity":400000,"bonds":100000,"gold":50000,"cash":80000}' \
  --goals '[{"name":"Retirement","target_amount":25000000,"years_to_achieve":25}]'

# View per-step HTML cards in browser
python3 flow.py card view extract_features
python3 flow.py card view score_risk
python3 flow.py card view simulate_investments
python3 flow.py card view recommend_portfolio
```

### Option B — With Metaflow UI (Docker required)

The UI shows a full DAG, run history, step timings, and artifacts at `http://localhost:8083`.

**1. Build the metadata service image** (once, takes ~3 min):
```bash
# Install docker buildx if not already present
mkdir -p ~/.docker/cli-plugins
curl -SL https://github.com/docker/buildx/releases/download/v0.13.1/buildx-v0.13.1.linux-amd64 \
  -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx

# Clone and build
git clone --depth=1 https://github.com/Netflix/metaflow-service /tmp/metaflow-service
DOCKER_BUILDKIT=1 docker build \
  --build-arg TARGETARCH=amd64 \
  -t metadata_service:latest \
  /tmp/metaflow-service
```

**2. Start the stack:**
```bash
docker-compose up -d
```

**3. Run the flow pointing at the local metadata service:**
```bash
METAFLOW_DEFAULT_METADATA=service \
METAFLOW_SERVICE_URL=http://localhost:8080/ \
python3 flow.py run
```

**4. Open the UI:**
```
http://localhost:8083
```

Every subsequent run (with those env vars) appears in the UI automatically.

To stop the stack:
```bash
docker-compose down
```

---

## How It Works — Step by Step

### Step 1 — Financial Feature Extraction (`modules/feature_extraction.py`)

Converts the five raw inputs into a set of normalised financial ratios that
the rest of the pipeline operates on.

| Feature | Formula | What it captures |
|---------|---------|-----------------|
| `savings_rate` | `(salary - expenses) / salary` | What fraction of income is kept |
| `expense_ratio` | `expenses / salary` | Cost-of-living burden |
| `investment_ratio` | `total_investments / salary` | Accumulated wealth relative to income |
| `liquidity_ratio` | `cash / total_investments` | Share of portfolio that is immediately accessible |
| `emergency_months` | `cash / (expenses / 12)` | How many months of expenses cash covers |
| `years_to_retirement` | `max(0, 60 - age)` | Remaining investment horizon (retirement age fixed at 60) |
| `urgency_score` | `Σ(target_amount / years_to_achieve) / salary` | Weighted pressure from near-term, high-value goals; normalised to salary |

The urgency score formula means a goal of 3,000,000 due in 7 years contributes
`3,000,000 / 7 ≈ 428,571` to the numerator. Dividing by salary normalises it so
the score is comparable across different income levels.

---

### Step 2 — Risk Scoring (`modules/risk_scoring.py`)

Produces a single score from **0 to 100** by summing six weighted components.
Higher score = higher risk capacity / tolerance.

| Component | Max pts | Formula |
|-----------|---------|---------|
| **Age** | 25 | `max(0, 25 − (age − 20) × 0.5)` — linear decay from age 20 onward |
| **Savings rate** | 20 | `min(savings_rate / 0.30, 1.0) × 20` — full pts at 30%+ savings |
| **Emergency fund** | 15 | `min(emergency_months / 6.0, 1.0) × 15` — full pts at 6+ months |
| **Investment ratio** | 20 | `min(investment_ratio / 2.0, 1.0) × 20` — full pts when invested ≥ 2× salary |
| **Goal urgency** | 10 | `10 − min(urgency_score, 1.0) × 10` — high urgency penalises score |
| **Liquidity** | 10 | Linear up to 20% cash; penalised above 20% (opportunity cost) |

**Score → Risk Label mapping:**

| Score range | Label |
|-------------|-------|
| 0 – 39 | Conservative |
| 40 – 59 | Moderate |
| 60 – 79 | Moderately Aggressive |
| 80 – 100 | Aggressive |

**Sample calculation (defaults — age 32, 40% savings rate, 1 month emergency fund):**
```
Age (32):          25 − (32−20)×0.5  = 19.00 pts
Savings rate (0.4): min(0.4/0.3,1)×20 = 20.00 pts
Emergency (1 mo):  min(1/6,1)×15     =  2.50 pts
Investment ratio:  min(0.45/2,1)×20  =  4.50 pts
Goal urgency:      10 − min(1.04,1)×10 = 0.00 pts  ← near-term goals
Liquidity (0.11):  (0.11/0.20)×10   =  5.55 pts
─────────────────────────────────────────────────
Total                                = 51.55 → 51.5  →  Moderate
```

---

### Step 3 — Investment Simulation (`modules/simulation.py`)

Runs a **Monte Carlo simulation** to project what the portfolio could be worth
at retirement across 1,000 independent random paths.

**Asset class return assumptions (annualised):**

| Asset | Mean return | Std deviation |
|-------|------------|---------------|
| Equity | 12% | 18% |
| Bonds | 7% | 5% |
| Gold | 8% | 10% |
| Cash | 4% | 1% |

These are approximate long-run historical figures for a diversified Indian/emerging-market portfolio.

**Each simulation path works like this:**

```
portfolio = initial_investments   # starting corpus
for each year in horizon:
    blended_return = Σ (weight_i × gauss(mean_i, std_i))
    portfolio = portfolio × (1 + blended_return) + annual_savings
```

- Returns for each asset class are drawn independently from a **Gaussian distribution** using `random.gauss(mean, std)` with a unique seed per path.
- `annual_savings` (salary − expenses) is added at the end of every year, simulating ongoing contributions.
- The terminal value is clamped to zero — portfolios cannot go negative.

After all paths complete, results are sorted and the following statistics are reported:

| Metric | Meaning |
|--------|---------|
| P10 (pessimistic) | 10% of paths end below this value |
| P50 / Median | The "most likely" outcome |
| P90 (optimistic) | Only 10% of paths exceed this value |
| Mean | Average across all paths |
| Goal success % | Fraction of paths that reach the total goal amount |

---

### Step 4 — Portfolio Recommendation (`modules/portfolio.py`)

Maps the risk score to a **static allocation table** then generates concrete
action items.

**Allocation table:**

| Score range | Label | Equity | Bonds | Gold |
|-------------|-------|--------|-------|------|
| 0 – 39 | Conservative | 20% | 55% | 25% |
| 40 – 54 | Moderate-Conservative | 40% | 40% | 20% |
| 55 – 64 | Moderate | 60% | 25% | 15% |
| 65 – 79 | Moderately Aggressive | 70% | 20% | 10% |
| 80 – 100 | Aggressive | 85% | 10% | 5% |

The rationale: younger investors with high savings and a long horizon can absorb
equity volatility. As the score drops (older, less savings, urgent goals), the
mix shifts toward capital-preserving bonds and inflation-hedging gold.

**Monetary allocation** is computed as:
```
investable_amount = annual_savings × years_to_retirement
monetary[asset]   = allocation_weight × investable_amount
```

**Action items are triggered by rule:**
- Emergency fund < 6 months → calculate shortfall and flag it
- Savings rate < 20% → prompt to save more
- Years to retirement < 10 and equity > 50% → flag de-risking needed

---

## Output Example

```
=======================================================
  FINAL REPORT — Personal Finance Risk Analyzer
=======================================================
  Risk Score   : 51.5 / 100
  Risk Profile : Moderate

  Suggested Allocation
    Equity : 40%
    Bonds  : 40%
    Gold   : 20%

  Portfolio Projection (Monte Carlo)
    Median (P50) : 5,98,93,179
    Best   (P90) : 8,45,79,698
    Worst  (P10) : 4,20,40,899
    Goal success : 99.9%

  Action Items:
    - Build emergency fund: add ~3,00,000 to liquid savings
      (currently 1.0 months covered, target 6).
=======================================================
```

---

## Viewing Step Cards

Each pipeline step decorated with `@card` stores an HTML report locally
under `.metaflow/mf.cards/`. Open any step's card in a browser:

```bash
python3 flow.py card view extract_features
python3 flow.py card view score_risk
python3 flow.py card view simulate_investments
python3 flow.py card view recommend_portfolio
```

For a full DAG visualisation with run history, see the
[Metaflow UI setup guide](https://github.com/Netflix/metaflow-ui).
