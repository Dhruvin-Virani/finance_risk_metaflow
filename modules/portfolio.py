"""
Portfolio recommendation engine.

Maps a risk score to a suggested asset allocation and
produces a human-readable recommendation summary.
"""


# Allocation table keyed by risk score bucket
ALLOCATION_TABLE = [
    # (min_score, max_score, equity, bonds, gold)
    (0,  40,  0.20, 0.55, 0.25),   # Conservative
    (40, 55,  0.40, 0.40, 0.20),   # Moderate-Conservative
    (55, 65,  0.60, 0.25, 0.15),   # Moderate
    (65, 80,  0.70, 0.20, 0.10),   # Moderately Aggressive
    (80, 101, 0.85, 0.10, 0.05),   # Aggressive
]


def recommend_portfolio(risk_result: dict, features: dict) -> dict:
    """
    Build a portfolio recommendation from the risk score.

    Args:
        risk_result: Output of compute_risk_score()
        features:    Extracted financial features

    Returns:
        Dict containing allocation percentages, narrative advice,
        and action items.
    """
    score = risk_result["risk_score"]
    label = risk_result["risk_label"]

    # Find allocation
    allocation = {"equity": 0.60, "bonds": 0.25, "gold": 0.15}  # default
    for (lo, hi, eq, bd, gd) in ALLOCATION_TABLE:
        if lo <= score < hi:
            allocation = {"equity": eq, "bonds": bd, "gold": gd}
            break

    # Build advice narrative
    advice_lines = [
        f"Based on your risk profile ({label}, score {score}/100), "
        f"the suggested portfolio allocation is:"
    ]
    advice_lines.append(
        f"  Equity : {int(allocation['equity']*100)}%"
    )
    advice_lines.append(
        f"  Bonds  : {int(allocation['bonds']*100)}%"
    )
    advice_lines.append(
        f"  Gold   : {int(allocation['gold']*100)}%"
    )

    # Action items
    actions = []
    if features["emergency_months"] < 6:
        needed = 6 * (features["expenses"] / 12) - features["investment_breakdown"].get("cash", 0)
        actions.append(
            f"Build emergency fund: add ~{needed:,.0f} to liquid savings "
            f"(currently {features['emergency_months']:.1f} months covered, target 6)."
        )
    if features["savings_rate"] < 0.20:
        actions.append(
            f"Increase savings rate from {features['savings_rate']*100:.1f}% to at least 20%."
        )
    if features["years_to_retirement"] < 10 and allocation["equity"] > 0.50:
        actions.append(
            "Consider de-risking: shift more to bonds/gold as retirement approaches."
        )
    if not actions:
        actions.append("You are on a solid financial track. Review allocation annually.")

    # Compute monetary target allocations
    investable = features["annual_savings"] * features["years_to_retirement"]
    monetary = {
        asset: round(weight * investable, 2)
        for asset, weight in allocation.items()
    }

    return {
        "risk_label": label,
        "risk_score": score,
        "allocation": allocation,
        "allocation_pct": {k: f"{int(v*100)}%" for k, v in allocation.items()},
        "investable_amount": round(investable, 2),
        "monetary_allocation": monetary,
        "narrative": "\n".join(advice_lines),
        "action_items": actions,
    }
