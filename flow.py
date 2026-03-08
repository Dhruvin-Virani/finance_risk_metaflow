"""
Personal Finance Risk Analyzer — Metaflow Pipeline
====================================================

Pipeline steps
--------------
  start
    ↓
  extract_features      — derive financial ratios from raw inputs
    ↓
  score_risk            — compute 0-100 risk score + label
    ↓
  simulate_investments  — Monte Carlo projection of portfolio growth
    ↓
  recommend_portfolio   — map risk score to asset allocation + advice
    ↓
  end                   — print final report

Usage
-----
  # Run with default sample inputs:
  python flow.py run

  # Run with custom inputs:
  python flow.py run \
    --salary 1500000 \
    --expenses 900000 \
    --age 35 \
    --investments '{"equity":400000,"bonds":100000,"gold":50000,"cash":80000}' \
    --goals '[{"name":"Retirement","target_amount":25000000,"years_to_achieve":25}]'

  # Show run history:
  python flow.py card view <run-id>
"""

import json

from metaflow import FlowSpec, Parameter, step, card, current
from metaflow.cards import Markdown, Table

from modules.feature_extraction import extract_features
from modules.risk_scoring import compute_risk_score
from modules.simulation import run_simulation
from modules.portfolio import recommend_portfolio


class FinanceRiskFlow(FlowSpec):
    """Personal Finance Risk Analyzer pipeline."""

    # ------------------------------------------------------------------ #
    #  Parameters                                                          #
    # ------------------------------------------------------------------ #

    salary = Parameter(
        "salary",
        help="Annual gross income (same currency throughout)",
        default=1_200_000,
        type=float,
    )
    expenses = Parameter(
        "expenses",
        help="Annual total expenses",
        default=720_000,
        type=float,
    )
    age = Parameter(
        "age",
        help="Current age",
        default=32,
        type=int,
    )
    investments = Parameter(
        "investments",
        help='JSON string: {"equity":n,"bonds":n,"gold":n,"cash":n}',
        default='{"equity":300000,"bonds":100000,"gold":80000,"cash":60000}',
        type=str,
    )
    goals = Parameter(
        "goals",
        help='JSON list of goals: [{"name":"...","target_amount":n,"years_to_achieve":n}]',
        default=(
            '[{"name":"Home purchase","target_amount":3000000,"years_to_achieve":7},'
            '{"name":"Child education","target_amount":1500000,"years_to_achieve":15},'
            '{"name":"Retirement corpus","target_amount":20000000,"years_to_achieve":28}]'
        ),
        type=str,
    )
    n_simulations = Parameter(
        "n_simulations",
        help="Number of Monte Carlo simulation paths",
        default=1000,
        type=int,
    )

    # ------------------------------------------------------------------ #
    #  Steps                                                               #
    # ------------------------------------------------------------------ #

    @step
    def start(self):
        """Validate and parse all inputs."""
        self.investments_dict = json.loads(self.investments)
        self.goals_list = json.loads(self.goals)

        print(f"\n{'='*55}")
        print("  Personal Finance Risk Analyzer")
        print(f"{'='*55}")
        print(f"  Salary      : {self.salary:>15,.0f}")
        print(f"  Expenses    : {self.expenses:>15,.0f}")
        print(f"  Age         : {self.age:>15}")
        print(f"  Investments : {sum(self.investments_dict.values()):>15,.0f}")
        print(f"  Goals       : {len(self.goals_list):>15}")
        print(f"{'='*55}\n")

        self.next(self.extract_features)

    @card(type="blank")
    @step
    def extract_features(self):
        """
        Step 1 — Financial Feature Extraction.

        Derives savings rate, investment ratio, emergency fund coverage,
        goal urgency score, and other financial KPIs from raw inputs.
        """
        self.features = extract_features(
            salary=self.salary,
            expenses=self.expenses,
            investments=self.investments_dict,
            age=self.age,
            goals=self.goals_list,
        )

        print("[Step 1] Financial Feature Extraction")
        print(f"  Savings Rate     : {self.features['savings_rate']*100:.1f}%")
        print(f"  Annual Savings   : {self.features['annual_savings']:,.0f}")
        print(f"  Emergency Fund   : {self.features['emergency_months']:.1f} months")
        print(f"  Investment Ratio : {self.features['investment_ratio']:.2f}x salary")
        print(f"  Urgency Score    : {self.features['urgency_score']:.4f}")
        print()

        current.card.append(
            Markdown("## Step 1: Financial Feature Extraction")
        )
        current.card.append(
            Table(
                data=[
                    ["Savings Rate", f"{self.features['savings_rate']*100:.1f}%"],
                    ["Annual Savings", f"{self.features['annual_savings']:,.0f}"],
                    ["Emergency Fund Coverage", f"{self.features['emergency_months']:.1f} months"],
                    ["Investment Ratio", f"{self.features['investment_ratio']:.2f}x salary"],
                    ["Total Investments", f"{self.features['total_investments']:,.0f}"],
                    ["Years to Retirement", str(self.features['years_to_retirement'])],
                    ["Goal Urgency Score", f"{self.features['urgency_score']:.4f}"],
                ],
                headers=["Feature", "Value"],
            )
        )

        self.next(self.score_risk)

    @card(type="blank")
    @step
    def score_risk(self):
        """
        Step 2 — Risk Scoring.

        Computes a composite 0-100 risk score from financial features.
        Factors: age, savings rate, emergency fund, investment ratio,
        goal urgency, and liquidity ratio.
        """
        self.risk_result = compute_risk_score(self.features)

        print("[Step 2] Risk Scoring")
        print(f"  Risk Score : {self.risk_result['risk_score']:.1f} / 100")
        print(f"  Risk Label : {self.risk_result['risk_label']}")
        print("  Score Breakdown:")
        for component, pts in self.risk_result["score_breakdown"].items():
            print(f"    {component:<20}: {pts:.2f} pts")
        print()

        current.card.append(
            Markdown("## Step 2: Risk Scoring")
        )
        current.card.append(
            Markdown(
                f"**Risk Score: {self.risk_result['risk_score']:.1f} / 100 "
                f"— {self.risk_result['risk_label']}**"
            )
        )
        breakdown_rows = [
            [comp.replace("_", " ").title(), f"{pts:.2f} pts"]
            for comp, pts in self.risk_result["score_breakdown"].items()
        ]
        current.card.append(
            Table(data=breakdown_rows, headers=["Component", "Points"])
        )

        self.next(self.simulate_investments)

    @card(type="blank")
    @step
    def simulate_investments(self):
        """
        Step 3 — Investment Simulation (Monte Carlo).

        Projects portfolio value over the retirement horizon using
        randomised annual returns sampled from historical asset-class
        distributions. Reports P10/P50/P90 outcomes and goal-meeting
        probability.
        """
        # Use recommended allocation from risk score for simulation
        from modules.portfolio import ALLOCATION_TABLE
        score = self.risk_result["risk_score"]
        allocation = {"equity": 0.60, "bonds": 0.25, "gold": 0.15}
        for (lo, hi, eq, bd, gd) in ALLOCATION_TABLE:
            if lo <= score < hi:
                allocation = {"equity": eq, "bonds": bd, "gold": gd}
                break

        self.sim_allocation = allocation
        self.sim_result = run_simulation(
            features=self.features,
            allocation=allocation,
            n_simulations=self.n_simulations,
        )

        print("[Step 3] Investment Simulation (Monte Carlo)")
        print(f"  Horizon        : {self.sim_result['horizon_years']} years")
        print(f"  Paths run      : {self.sim_result['n_simulations']:,}")
        print(f"  Median outcome : {self.sim_result['projected_median']:>15,.0f}")
        print(f"  Pessimistic P10: {self.sim_result['projected_p10']:>15,.0f}")
        print(f"  Optimistic  P90: {self.sim_result['projected_p90']:>15,.0f}")
        print(f"  Goal target    : {self.sim_result['total_goal_amount']:>15,.0f}")
        print(f"  Prob. of goal  : {self.sim_result['prob_meeting_goal']}%")
        print()

        current.card.append(
            Markdown("## Step 3: Monte Carlo Investment Simulation")
        )
        current.card.append(
            Table(
                data=[
                    ["Horizon", f"{self.sim_result['horizon_years']} years"],
                    ["Simulation Paths", f"{self.sim_result['n_simulations']:,}"],
                    ["Median Portfolio (P50)", f"{self.sim_result['projected_median']:,.0f}"],
                    ["Pessimistic (P10)", f"{self.sim_result['projected_p10']:,.0f}"],
                    ["Optimistic (P90)", f"{self.sim_result['projected_p90']:,.0f}"],
                    ["Mean Portfolio", f"{self.sim_result['projected_mean']:,.0f}"],
                    ["Total Goal Amount", f"{self.sim_result['total_goal_amount']:,.0f}"],
                    ["Probability of Meeting Goal", f"{self.sim_result['prob_meeting_goal']}%"],
                ],
                headers=["Metric", "Value"],
            )
        )

        self.next(self.recommend_portfolio)

    @card(type="blank")
    @step
    def recommend_portfolio(self):
        """
        Step 4 — Portfolio Recommendation.

        Maps the risk score to an optimal asset allocation across equity,
        bonds, and gold. Produces concrete action items and a narrative
        advisory summary.
        """
        self.recommendation = recommend_portfolio(
            risk_result=self.risk_result,
            features=self.features,
        )

        print("[Step 4] Portfolio Recommendation")
        print(self.recommendation["narrative"])
        print()
        if self.recommendation["action_items"]:
            print("  Action Items:")
            for item in self.recommendation["action_items"]:
                print(f"    - {item}")
        print()

        current.card.append(
            Markdown("## Step 4: Portfolio Recommendation")
        )
        alloc_rows = [
            [asset.title(), pct, f"{self.recommendation['monetary_allocation'][asset]:,.0f}"]
            for asset, pct in self.recommendation["allocation_pct"].items()
        ]
        current.card.append(
            Table(
                data=alloc_rows,
                headers=["Asset Class", "Allocation %", "Target Amount"],
            )
        )
        actions_md = "\n".join(
            f"- {item}" for item in self.recommendation["action_items"]
        )
        current.card.append(Markdown(f"### Action Items\n{actions_md}"))

        self.next(self.end)

    @step
    def end(self):
        """Print the final consolidated report."""
        r = self.recommendation
        s = self.sim_result

        print(f"\n{'='*55}")
        print("  FINAL REPORT — Personal Finance Risk Analyzer")
        print(f"{'='*55}")
        print(f"  Risk Score   : {r['risk_score']:.1f} / 100")
        print(f"  Risk Profile : {r['risk_label']}")
        print()
        print("  Suggested Allocation")
        print(f"    Equity : {r['allocation_pct']['equity']}")
        print(f"    Bonds  : {r['allocation_pct']['bonds']}")
        print(f"    Gold   : {r['allocation_pct']['gold']}")
        print()
        print("  Portfolio Projection (Monte Carlo)")
        print(f"    Median (P50) : {s['projected_median']:>15,.0f}")
        print(f"    Best   (P90) : {s['projected_p90']:>15,.0f}")
        print(f"    Worst  (P10) : {s['projected_p10']:>15,.0f}")
        print(f"    Goal success : {s['prob_meeting_goal']}%")
        print()
        print("  Action Items:")
        for item in r["action_items"]:
            print(f"    - {item}")
        print(f"{'='*55}\n")


if __name__ == "__main__":
    FinanceRiskFlow()
