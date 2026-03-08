"""
Risk scoring engine.

Produces a numeric risk score (0–100) and a categorical label.
Higher score = higher risk tolerance / capacity.
"""

RISK_LABELS = {
    (0,  40): "Conservative",
    (40, 60): "Moderate",
    (60, 80): "Moderately Aggressive",
    (80, 101): "Aggressive",
}


def compute_risk_score(features: dict) -> dict:
    """
    Compute a composite risk score from extracted financial features.

    Scoring components:
    - Age component          (0–25):  younger → higher score
    - Savings rate           (0–20):  higher savings → higher score
    - Emergency fund         (0–15):  6+ months buffer → full score
    - Investment ratio       (0–20):  already investing more → higher score
    - Goal urgency           (0–10):  high urgency → lower score (penalty)
    - Liquidity ratio        (0–10):  moderate liquidity is good

    Returns dict with score, label, and component breakdown.
    """
    score = 0.0
    breakdown = {}

    # --- Age component (25 pts) ---
    # 20–30 → 25, 30–40 → 20, 40–50 → 12, 50–60 → 5, 60+ → 0
    age = features["age"]
    age_score = max(0, 25 - max(0, (age - 20)) * 0.5)
    age_score = round(min(age_score, 25), 2)
    score += age_score
    breakdown["age"] = age_score

    # --- Savings rate (20 pts) ---
    sr = features["savings_rate"]
    # 0% → 0 pts, 30%+ → 20 pts
    sr_score = round(min(sr / 0.30, 1.0) * 20, 2)
    score += sr_score
    breakdown["savings_rate"] = sr_score

    # --- Emergency fund (15 pts) ---
    em = features["emergency_months"]
    # 0 months → 0, 6+ months → 15
    em_score = round(min(em / 6.0, 1.0) * 15, 2)
    score += em_score
    breakdown["emergency_fund"] = em_score

    # --- Investment ratio (20 pts) ---
    ir = features["investment_ratio"]
    # 0 → 0 pts, 2x salary → 20 pts
    ir_score = round(min(ir / 2.0, 1.0) * 20, 2)
    score += ir_score
    breakdown["investment_ratio"] = ir_score

    # --- Goal urgency penalty (10 pts) ---
    # High urgency reduces risk score
    urg = features["urgency_score"]
    # urgency_score of 1.0+ = maximum penalty
    urgency_penalty = round(min(urg, 1.0) * 10, 2)
    urgency_contribution = round(10 - urgency_penalty, 2)
    score += urgency_contribution
    breakdown["goal_urgency"] = urgency_contribution

    # --- Liquidity ratio (10 pts) ---
    # Target ~10–20% in cash/liquid; too little or too much is suboptimal
    liq = features["liquidity_ratio"]
    if liq <= 0.20:
        liq_score = round((liq / 0.20) * 10, 2)
    else:
        # Penalty for holding too much cash (opportunity cost)
        liq_score = round(max(0, 10 - (liq - 0.20) * 20), 2)
    score += liq_score
    breakdown["liquidity"] = liq_score

    total_score = round(min(max(score, 0), 100), 1)

    # Determine label
    label = "Conservative"
    for (low, high), lbl in RISK_LABELS.items():
        if low <= total_score < high:
            label = lbl
            break

    return {
        "risk_score": total_score,
        "risk_label": label,
        "score_breakdown": breakdown,
    }
