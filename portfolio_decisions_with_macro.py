#!/usr/bin/env python3
"""
Portfolio Decision Engine with Macro Context

Generates specific BUY/HOLD/REDUCE/EXIT recommendations by combining:
- Economic risk scores (macro environment)
- Sector alignment analysis
- Position performance
- Risk management rules
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
from analyze_with_macro_context import (
    PortfolioPosition,
    PortfolioMacroAnalyzer
)
from psx_economic_data import PSXEconomicData


class Decision(Enum):
    """Investment decision types"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"


@dataclass
class PositionDecision:
    """Investment decision for a position"""
    symbol: str
    decision: Decision
    confidence: str  # "high", "moderate", "low"
    target_allocation_pct: float  # % of portfolio
    action_size_pct: float  # % of current position to adjust
    reasoning: List[str]
    risk_factors: List[str]
    opportunity_factors: List[str]
    macro_context: str

    @property
    def decision_emoji(self) -> str:
        """Get emoji for decision"""
        return {
            Decision.STRONG_BUY: "🚀",
            Decision.BUY: "✅",
            Decision.HOLD: "🤝",
            Decision.REDUCE: "⚠️",
            Decision.EXIT: "🚪"
        }[self.decision]


class PortfolioDecisionEngine:
    """
    Makes portfolio decisions by combining macro analysis with position data
    """

    def __init__(self, db_path: str = "portfolio_data/economic_data.db"):
        self.economic_data = PSXEconomicData(db_path)
        self.macro_analyzer = PortfolioMacroAnalyzer(db_path)

    def make_decision(
        self,
        position: PortfolioPosition,
        macro_alignment: Dict,
        risk_score: float
    ) -> PositionDecision:
        """
        Generate investment decision for a position

        Decision logic:
        1. Evaluate macro environment favorability
        2. Assess position P&L and risk exposure
        3. Check sector alignment with macro
        4. Apply risk management rules
        5. Generate action recommendation
        """

        alignment_score = macro_alignment["alignment_score"]
        gain_loss_pct = position.gain_loss_pct

        reasoning = []
        risk_factors = []
        opportunity_factors = []

        # --- Macro Environment Assessment ---

        if risk_score >= 70:
            macro_context = f"FAVORABLE macro environment ({risk_score:.1f}/100) - Risk-on"
            favorable_macro = True
        elif risk_score >= 50:
            macro_context = f"NEUTRAL macro environment ({risk_score:.1f}/100) - Balanced"
            favorable_macro = False
        else:
            macro_context = f"UNFAVORABLE macro environment ({risk_score:.1f}/100) - Risk-off"
            favorable_macro = False

        # --- Sector Alignment Assessment ---

        if alignment_score >= 60:
            reasoning.append(f"✓ Well-aligned with macro (score {alignment_score:.1f})")
            sector_aligned = True
        elif alignment_score >= 40:
            reasoning.append(f"~ Neutral alignment with macro (score {alignment_score:.1f})")
            sector_aligned = False
        else:
            reasoning.append(f"✗ Misaligned with macro (score {alignment_score:.1f})")
            sector_aligned = False
            risk_factors.append(f"Sector vulnerable in current environment")

        # --- Position Performance Assessment ---

        if gain_loss_pct > 100:
            reasoning.append(f"Large gain +{gain_loss_pct:.1f}% - consider taking profits")
            risk_factors.append("Outsized gain increases downside risk")
        elif gain_loss_pct > 50:
            reasoning.append(f"Strong gain +{gain_loss_pct:.1f}% - partial profit taking prudent")
        elif gain_loss_pct > 20:
            reasoning.append(f"Solid gain +{gain_loss_pct:.1f}%")
        elif gain_loss_pct > 0:
            reasoning.append(f"Modest gain +{gain_loss_pct:.1f}%")
        elif gain_loss_pct > -10:
            reasoning.append(f"Small loss {gain_loss_pct:.1f}%")
        else:
            reasoning.append(f"Significant loss {gain_loss_pct:.1f}%")
            risk_factors.append("Large unrealized loss")

        # --- Decision Logic ---

        # STRONG_BUY: Favorable macro + well-aligned sector + position down/flat
        if favorable_macro and sector_aligned and gain_loss_pct < 20:
            decision = Decision.STRONG_BUY
            confidence = "high"
            target_allocation_pct = 8.0  # Increase to 8% of portfolio
            action_size_pct = 50.0  # Add 50% to position
            opportunity_factors.append("Buy opportunity: Strong macro + aligned sector + attractive entry")

        # BUY: Favorable macro + aligned sector OR strong macro with modest position
        elif (favorable_macro and alignment_score >= 50) or (risk_score >= 75 and gain_loss_pct < 30):
            decision = Decision.BUY
            confidence = "moderate" if alignment_score < 60 else "high"
            target_allocation_pct = 6.0
            action_size_pct = 25.0  # Add 25% to position
            opportunity_factors.append("Macro environment supportive for adding")

        # HOLD: Neutral macro with reasonable alignment OR favorable macro with large gains
        elif (50 <= risk_score < 70 and alignment_score >= 40) or (favorable_macro and 50 < gain_loss_pct < 100):
            decision = Decision.HOLD
            confidence = "moderate"
            target_allocation_pct = position.current_value / 1000000 * 100  # Maintain current
            action_size_pct = 0.0
            reasoning.append("Hold current position - monitor for changes")

        # REDUCE: Unfavorable macro OR misaligned + large gains OR very large gains regardless
        elif (not favorable_macro and alignment_score < 40) or \
             (not sector_aligned and gain_loss_pct > 50) or \
             (gain_loss_pct > 150):
            decision = Decision.REDUCE

            if gain_loss_pct > 150:
                confidence = "high"
                action_size_pct = 50.0  # Sell 50% of position
                reasoning.append("Take substantial profits - risk/reward unfavorable")
            elif not favorable_macro and alignment_score < 40:
                confidence = "high"
                action_size_pct = 40.0
                reasoning.append("Reduce exposure - macro unfavorable + sector vulnerable")
            else:
                confidence = "moderate"
                action_size_pct = 30.0
                reasoning.append("Trim position - lock in partial gains")

            target_allocation_pct = 3.0  # Reduce to 3% max
            risk_factors.append("Unfavorable risk/reward at current levels")

        # EXIT: Significant loss + unfavorable macro + misaligned OR extreme losses
        elif (gain_loss_pct < -8 and not favorable_macro and alignment_score < 40) or \
             (gain_loss_pct < -15):
            decision = Decision.EXIT

            if gain_loss_pct < -15:
                confidence = "high"
                reasoning.append("Cut losses - position broken")
            else:
                confidence = "moderate"
                reasoning.append("Exit - fundamentals + macro both negative")

            action_size_pct = 100.0  # Exit full position
            target_allocation_pct = 0.0
            risk_factors.append("High probability of further deterioration")

        # Default REDUCE if nothing else matches
        else:
            decision = Decision.REDUCE
            confidence = "moderate"
            action_size_pct = 25.0
            target_allocation_pct = 4.0
            reasoning.append("Reduce as precaution - mixed signals")

        # --- Add macro alignment reasoning ---
        if macro_alignment.get("reasoning"):
            reasoning.append(f"Sector context: {macro_alignment['reasoning']}")

        return PositionDecision(
            symbol=position.symbol,
            decision=decision,
            confidence=confidence,
            target_allocation_pct=target_allocation_pct,
            action_size_pct=action_size_pct,
            reasoning=reasoning,
            risk_factors=risk_factors,
            opportunity_factors=opportunity_factors,
            macro_context=macro_context
        )

    def analyze_portfolio_decisions(
        self,
        positions: List[PortfolioPosition]
    ) -> Dict:
        """Generate decisions for entire portfolio"""

        # Get macro analysis
        macro_analysis = self.macro_analyzer.analyze_portfolio(positions)

        if "error" in macro_analysis:
            return macro_analysis

        risk_score = macro_analysis["risk_score"].overall_score

        # Generate decisions for each position
        decisions = []
        for pa in macro_analysis["position_analyses"]:
            position = pa["position"]
            macro_alignment = pa["macro_alignment"]

            decision = self.make_decision(position, macro_alignment, risk_score)
            decisions.append(decision)

        # Categorize decisions
        strong_buys = [d for d in decisions if d.decision == Decision.STRONG_BUY]
        buys = [d for d in decisions if d.decision == Decision.BUY]
        holds = [d for d in decisions if d.decision == Decision.HOLD]
        reduces = [d for d in decisions if d.decision == Decision.REDUCE]
        exits = [d for d in decisions if d.decision == Decision.EXIT]

        return {
            "macro_analysis": macro_analysis,
            "decisions": decisions,
            "by_decision": {
                "strong_buy": strong_buys,
                "buy": buys,
                "hold": holds,
                "reduce": reduces,
                "exit": exits
            }
        }


def print_decision_report(analysis: Dict):
    """Print comprehensive decision report"""

    if "error" in analysis:
        print(f"\n❌ Error: {analysis['error']}")
        return

    macro_analysis = analysis["macro_analysis"]
    risk_score = macro_analysis["risk_score"]
    summary = macro_analysis["portfolio_summary"]
    decisions = analysis["decisions"]
    by_decision = analysis["by_decision"]

    print("=" * 120)
    print("🎯 PORTFOLIO DECISIONS WITH MACRO-ECONOMIC CONTEXT")
    print("=" * 120)

    # Executive Summary
    print(f"\n📊 EXECUTIVE SUMMARY")
    print("-" * 120)
    print(f"Economic Environment: {risk_score.overall_score:.1f}/100 ({risk_score.risk_level.upper()}) - "
          f"Trend: {risk_score.trend.upper()}")
    print(f"Portfolio Value: PKR {summary['total_current']:,.0f} | "
          f"P&L: PKR {summary['total_gain']:,.0f} ({summary['total_gain_pct']:+.2f}%)")
    print(f"\nDecision Summary:")
    print(f"  🚀 STRONG BUY: {len(by_decision['strong_buy'])} positions")
    print(f"  ✅ BUY:        {len(by_decision['buy'])} positions")
    print(f"  🤝 HOLD:       {len(by_decision['hold'])} positions")
    print(f"  ⚠️  REDUCE:     {len(by_decision['reduce'])} positions")
    print(f"  🚪 EXIT:       {len(by_decision['exit'])} positions")

    # Action Priority List
    print(f"\n🚨 ACTION PRIORITY (Immediate Attention Required)")
    print("=" * 120)

    # Priority 1: Exits
    if by_decision['exit']:
        print(f"\n1️⃣  EXITS - Execute First")
        print("-" * 120)
        for dec in by_decision['exit']:
            pos = next(p for p in macro_analysis["position_analyses"] if p["position"].symbol == dec.symbol)
            position = pos["position"]
            print(f"\n{dec.decision_emoji} {dec.symbol} → EXIT (Confidence: {dec.confidence.upper()})")
            print(f"   Current: {position.shares} shares @ PKR {position.current_price:.2f} = PKR {position.current_value:,.0f}")
            print(f"   P&L: PKR {position.gain_loss:,.0f} ({position.gain_loss_pct:+.2f}%)")
            print(f"   Action: SELL 100% of position")
            print(f"   Reasoning:")
            for reason in dec.reasoning:
                print(f"     • {reason}")
            if dec.risk_factors:
                print(f"   ⚠️  Risks:")
                for risk in dec.risk_factors:
                    print(f"     • {risk}")

    # Priority 2: Reduces
    if by_decision['reduce']:
        print(f"\n2️⃣  REDUCE POSITIONS - Take Profits / Cut Risk")
        print("-" * 120)
        for dec in by_decision['reduce']:
            pos = next(p for p in macro_analysis["position_analyses"] if p["position"].symbol == dec.symbol)
            position = pos["position"]
            shares_to_sell = int(position.shares * (dec.action_size_pct / 100))
            proceeds = shares_to_sell * position.current_price

            print(f"\n{dec.decision_emoji} {dec.symbol} → REDUCE by {dec.action_size_pct:.0f}% (Confidence: {dec.confidence.upper()})")
            print(f"   Current: {position.shares} shares @ PKR {position.current_price:.2f}")
            print(f"   P&L: PKR {position.gain_loss:,.0f} ({position.gain_loss_pct:+.2f}%)")
            print(f"   Action: SELL {shares_to_sell} shares → Receive PKR {proceeds:,.0f}")
            print(f"   After: {position.shares - shares_to_sell} shares remaining")
            print(f"   Reasoning:")
            for reason in dec.reasoning:
                print(f"     • {reason}")

    # Priority 3: Strong Buys
    if by_decision['strong_buy']:
        print(f"\n3️⃣  STRONG BUY - High Conviction Opportunities")
        print("-" * 120)
        for dec in by_decision['strong_buy']:
            pos = next(p for p in macro_analysis["position_analyses"] if p["position"].symbol == dec.symbol)
            position = pos["position"]
            shares_to_buy = int(position.shares * (dec.action_size_pct / 100))
            cost = shares_to_buy * position.current_price

            print(f"\n{dec.decision_emoji} {dec.symbol} → STRONG BUY (Confidence: {dec.confidence.upper()})")
            print(f"   Current: {position.shares} shares @ PKR {position.current_price:.2f}")
            print(f"   P&L: PKR {position.gain_loss:,.0f} ({position.gain_loss_pct:+.2f}%)")
            print(f"   Action: BUY {shares_to_buy} shares @ ~PKR {position.current_price:.2f} = PKR {cost:,.0f}")
            print(f"   After: {position.shares + shares_to_buy} shares total")
            print(f"   Opportunities:")
            for opp in dec.opportunity_factors:
                print(f"     ✓ {opp}")
            print(f"   Reasoning:")
            for reason in dec.reasoning:
                print(f"     • {reason}")

    # Priority 4: Buys
    if by_decision['buy']:
        print(f"\n4️⃣  BUY - Add to Positions")
        print("-" * 120)
        for dec in by_decision['buy']:
            pos = next(p for p in macro_analysis["position_analyses"] if p["position"].symbol == dec.symbol)
            position = pos["position"]
            shares_to_buy = int(position.shares * (dec.action_size_pct / 100))
            cost = shares_to_buy * position.current_price

            print(f"\n{dec.decision_emoji} {dec.symbol} → BUY (Confidence: {dec.confidence.upper()})")
            print(f"   Current: {position.shares} shares @ PKR {position.current_price:.2f}")
            print(f"   Action: BUY {shares_to_buy} shares = PKR {cost:,.0f}")
            print(f"   Reasoning:")
            for reason in dec.reasoning:
                print(f"     • {reason}")

    # Holds
    if by_decision['hold']:
        print(f"\n5️⃣  HOLD - Monitor These Positions")
        print("-" * 120)
        for dec in by_decision['hold']:
            pos = next(p for p in macro_analysis["position_analyses"] if p["position"].symbol == dec.symbol)
            position = pos["position"]

            print(f"\n{dec.decision_emoji} {dec.symbol} → HOLD")
            print(f"   Current: {position.shares} shares @ PKR {position.current_price:.2f} | "
                  f"P&L: {position.gain_loss_pct:+.2f}%")
            print(f"   Reasoning: {dec.reasoning[0] if dec.reasoning else 'Maintain position'}")

    # Summary of cash flows
    print(f"\n" + "=" * 120)
    print("💰 CASH FLOW SUMMARY")
    print("=" * 120)

    total_proceeds = sum(
        next(p["position"] for p in macro_analysis["position_analyses"] if p["position"].symbol == dec.symbol).shares *
        next(p["position"] for p in macro_analysis["position_analyses"] if p["position"].symbol == dec.symbol).current_price *
        (dec.action_size_pct / 100)
        for dec in by_decision['exit'] + by_decision['reduce']
    )

    total_investments = sum(
        next(p["position"] for p in macro_analysis["position_analyses"] if p["position"].symbol == dec.symbol).shares *
        next(p["position"] for p in macro_analysis["position_analyses"] if p["position"].symbol == dec.symbol).current_price *
        (dec.action_size_pct / 100)
        for dec in by_decision['strong_buy'] + by_decision['buy']
    )

    net_cash_flow = total_proceeds - total_investments

    print(f"\nCash from Exits/Reduces: PKR {total_proceeds:,.0f}")
    print(f"Cash for Buys:           PKR {total_investments:,.0f}")
    print(f"Net Cash Flow:           PKR {net_cash_flow:,.0f}")

    if net_cash_flow > 0:
        print(f"\n✅ Net cash generated: PKR {net_cash_flow:,.0f}")
        print("   Consider: Keep as reserves or deploy to new opportunities")
    else:
        print(f"\n⚠️  Additional cash needed: PKR {abs(net_cash_flow):,.0f}")
        print("   Consider: Reduce buy sizes or increase sales")

    print(f"\n" + "=" * 120)
    print("📝 NEXT STEPS")
    print("=" * 120)
    print("\n1. Review and validate all recommended actions")
    print("2. Execute EXITS first (clear capital, reduce risk)")
    print("3. Execute REDUCES second (harvest profits)")
    print("4. Execute BUYS with proceeds from sales")
    print("5. Update economic data monthly: python update_economic_data.py")
    print("6. Re-run this analysis after significant market moves")
    print("\n⚠️  Important: These are recommendations based on macro analysis.")
    print("   Always validate with your own research and risk tolerance.")
    print("=" * 120)


def main():
    """Main execution"""

    # User's actual portfolio
    portfolio_positions = [
        PortfolioPosition("NATF", 400, 137.95, 426.50, "Food"),
        PortfolioPosition("BAFL", 200, 118.50, 272.80, "Banking"),
        PortfolioPosition("ICL", 500, 95.00, 195.50, "Chemicals"),
        PortfolioPosition("ATLH", 300, 130.00, 198.00, "Auto"),
        PortfolioPosition("FFBL", 250, 75.00, 110.00, "Fertilizer"),
        PortfolioPosition("PSO", 150, 180.00, 247.00, "Oil & Gas"),
        PortfolioPosition("ENGRO", 200, 250.00, 325.00, "Fertilizer"),
        PortfolioPosition("LUCK", 100, 650.00, 950.00, "Cement"),
        PortfolioPosition("MEBL", 400, 95.00, 150.00, "Banking"),
        PortfolioPosition("DGKC", 600, 60.00, 85.00, "Cement"),
        PortfolioPosition("SNGP", 300, 40.00, 55.00, "Oil & Gas"),
        PortfolioPosition("PPL", 250, 85.00, 105.00, "Oil & Gas"),
        PortfolioPosition("EFERT", 200, 70.00, 95.00, "Fertilizer"),
        PortfolioPosition("GAL", 150, 185.00, 165.25, "Auto"),
        PortfolioPosition("PAEL", 300, 65.00, 59.80, "Auto"),
        PortfolioPosition("MTL", 400, 45.00, 48.50, "Textiles"),
    ]

    print("\n🔍 Analyzing portfolio with macro-economic context...")
    print(f"Portfolio: {len(portfolio_positions)} positions\n")

    # Generate decisions
    engine = PortfolioDecisionEngine()
    analysis = engine.analyze_portfolio_decisions(portfolio_positions)

    # Print report
    print_decision_report(analysis)


if __name__ == "__main__":
    main()
