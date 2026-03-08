"""
Investment simulation via Monte Carlo method.

Projects portfolio value over the investment horizon using
randomised annual returns drawn from historical asset-class distributions.
"""

import random
import statistics


# Historical mean annual returns and std deviations (approximate, annualised)
ASSET_STATS = {
    "equity": {"mean": 0.12, "std": 0.18},   # ~12% mean, high volatility
    "bonds":  {"mean": 0.07, "std": 0.05},   # ~7% mean, low volatility
    "gold":   {"mean": 0.08, "std": 0.10},   # ~8% mean, moderate volatility
    "cash":   {"mean": 0.04, "std": 0.01},   # ~4% (savings/liquid fund)
}


def _simulate_single_path(
    initial_value: float,
    annual_contribution: float,
    allocation: dict,
    years: int,
    seed: int,
) -> float:
    """Run one Monte Carlo path and return the terminal portfolio value."""
    rng = random.Random(seed)
    portfolio = initial_value

    for _ in range(years):
        blended_return = 0.0
        for asset, weight in allocation.items():
            stats = ASSET_STATS.get(asset, {"mean": 0.06, "std": 0.08})
            # Box-Muller approximation using rng.gauss
            annual_return = rng.gauss(stats["mean"], stats["std"])
            blended_return += weight * annual_return

        portfolio = portfolio * (1 + blended_return) + annual_contribution

    return max(portfolio, 0.0)


def run_simulation(
    features: dict,
    allocation: dict,
    n_simulations: int = 1000,
) -> dict:
    """
    Run Monte Carlo simulation for the given portfolio allocation.

    Args:
        features:      Extracted financial features dict.
        allocation:    Portfolio weights, e.g. {"equity": 0.60, "bonds": 0.25, "gold": 0.15}
        n_simulations: Number of Monte Carlo paths to run.

    Returns:
        Dict with projected portfolio statistics.
    """
    initial_value = features["total_investments"]
    annual_contribution = features["annual_savings"]
    years = features["years_to_retirement"]

    if years <= 0:
        years = 10  # default horizon if already at/past retirement age

    results = []
    for i in range(n_simulations):
        terminal = _simulate_single_path(
            initial_value=initial_value,
            annual_contribution=annual_contribution,
            allocation=allocation,
            years=years,
            seed=i,
        )
        results.append(terminal)

    results.sort()

    p10 = results[int(0.10 * n_simulations)]
    p50 = results[int(0.50 * n_simulations)]
    p90 = results[int(0.90 * n_simulations)]
    mean_val = statistics.mean(results)

    # Probability of meeting total goal amount
    total_goal = features["total_goal_amount"]
    prob_meeting_goal = (
        sum(1 for r in results if r >= total_goal) / n_simulations
        if total_goal > 0
        else None
    )

    return {
        "horizon_years": years,
        "n_simulations": n_simulations,
        "projected_p10": round(p10, 2),
        "projected_median": round(p50, 2),
        "projected_p90": round(p90, 2),
        "projected_mean": round(mean_val, 2),
        "prob_meeting_goal": (
            round(prob_meeting_goal * 100, 1) if prob_meeting_goal is not None else "N/A"
        ),
        "total_goal_amount": total_goal,
    }
