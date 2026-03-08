"""
Financial feature extraction from raw user inputs.
"""


def extract_features(salary: float, expenses: float, investments: dict, age: int, goals: list) -> dict:
    """
    Derive meaningful financial ratios and features from raw inputs.

    Args:
        salary:      Annual gross income (INR or any currency)
        expenses:    Annual total expenses
        investments: Dict of asset -> current value
                     e.g. {"equity": 200000, "bonds": 50000, "gold": 30000, "cash": 20000}
        age:         Current age of the person
        goals:       List of goal dicts, each with keys: name, target_amount, years_to_achieve

    Returns:
        Feature dict consumed by subsequent pipeline steps.
    """
    if salary <= 0:
        raise ValueError("Salary must be positive.")

    monthly_salary = salary / 12
    annual_savings = salary - expenses
    savings_rate = annual_savings / salary                      # 0–1
    expense_ratio = expenses / salary                           # 0–1

    total_investments = sum(investments.values())
    investment_ratio = total_investments / salary if salary else 0

    # Liquidity: cash as fraction of total investments
    cash = investments.get("cash", 0)
    liquidity_ratio = cash / total_investments if total_investments else 0

    # Emergency fund: months of expenses covered by cash
    monthly_expenses = expenses / 12
    emergency_months = cash / monthly_expenses if monthly_expenses else 0

    # Retirement horizon
    retirement_age = 60
    years_to_retirement = max(0, retirement_age - age)

    # Total target amount across all goals
    total_goal_amount = sum(g.get("target_amount", 0) for g in goals)

    # Weighted urgency: goals due sooner are more urgent
    urgency_score = 0.0
    for g in goals:
        years = g.get("years_to_achieve", 10)
        target = g.get("target_amount", 0)
        # Closer deadlines + bigger targets = higher urgency
        urgency_score += target / max(years, 1)
    # Normalise to salary
    urgency_score = urgency_score / salary if salary else 0

    return {
        "salary": salary,
        "expenses": expenses,
        "annual_savings": annual_savings,
        "savings_rate": round(savings_rate, 4),
        "expense_ratio": round(expense_ratio, 4),
        "total_investments": total_investments,
        "investment_ratio": round(investment_ratio, 4),
        "liquidity_ratio": round(liquidity_ratio, 4),
        "emergency_months": round(emergency_months, 2),
        "age": age,
        "years_to_retirement": years_to_retirement,
        "monthly_salary": round(monthly_salary, 2),
        "total_goal_amount": total_goal_amount,
        "urgency_score": round(urgency_score, 4),
        "num_goals": len(goals),
        "investment_breakdown": investments,
    }
