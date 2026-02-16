#!/usr/bin/env python3
"""
Portfolio Analysis for User's Current Holdings
Analyzes the provided portfolio without requiring external dependencies
"""

# User's portfolio data
portfolio = {
    'HINOON': {'qty': 60, 'avg_cost': 1038.00, 'current': 1021.12, 'value': 61267, 'weight': 2.22},
    'SAZEW': {'qty': 60, 'avg_cost': 2022.83, 'current': 2333.98, 'value': 140039, 'weight': 5.08},
    'PNSC': {'qty': 200, 'avg_cost': 634.75, 'current': 619.00, 'value': 123800, 'weight': 4.49},
    'NATF': {'qty': 550, 'avg_cost': 132.08, 'current': 408.94, 'value': 224917, 'weight': 8.16},
    'BFBIO': {'qty': 1500, 'avg_cost': 137.22, 'current': 164.00, 'value': 246000, 'weight': 8.92},
    'AGP': {'qty': 1200, 'avg_cost': 191.26, 'current': 238.08, 'value': 285696, 'weight': 10.36},
    'GAL': {'qty': 150, 'avg_cost': 555.33, 'current': 495.99, 'value': 74399, 'weight': 2.70},
    'PAKT': {'qty': 110, 'avg_cost': 1372.30, 'current': 1595.00, 'value': 175450, 'weight': 6.36},
    'BAFL': {'qty': 1500, 'avg_cost': 54.72, 'current': 126.00, 'value': 189000, 'weight': 6.85},
    'BBFL': {'qty': 2000, 'avg_cost': 49.89, 'current': 49.00, 'value': 98000, 'weight': 3.55},
    'ICL': {'qty': 1600, 'avg_cost': 85.82, 'current': 151.50, 'value': 242400, 'weight': 8.79},
    'HTL': {'qty': 2000, 'avg_cost': 55.77, 'current': 54.25, 'value': 108500, 'weight': 3.94},
    'PAEL': {'qty': 3200, 'avg_cost': 58.68, 'current': 53.98, 'value': 172736, 'weight': 6.26},
    'BFAGRO': {'qty': 3000, 'avg_cost': 34.37, 'current': 39.40, 'value': 118200, 'weight': 4.29},
    'HALEON': {'qty': 300, 'avg_cost': 796.02, 'current': 914.00, 'value': 274200, 'weight': 9.94},
    'ATLH': {'qty': 125, 'avg_cost': 1168.40, 'current': 1781.02, 'value': 222628, 'weight': 8.07},
}

def analyze_portfolio():
    """Analyze the portfolio and provide recommendations"""

    print("="*100)
    print("💼 PORTFOLIO ANALYSIS")
    print("="*100)

    total_value = sum(p['value'] for p in portfolio.values())
    total_cost = sum(p['qty'] * p['avg_cost'] for p in portfolio.values())
    total_pl = total_value - total_cost
    total_pl_pct = (total_pl / total_cost) * 100

    print(f"\n📊 PORTFOLIO SUMMARY")
    print(f"   Total Holdings:    16 stocks")
    print(f"   Total Cost Basis:  PKR {total_cost:,.0f}")
    print(f"   Current Value:     PKR {total_value:,.0f}")
    print(f"   Total P&L:         PKR {total_pl:,.0f} ({total_pl_pct:+.2f}%)")

    # Calculate position metrics
    winners = []
    losers = []

    for symbol, data in portfolio.items():
        cost = data['qty'] * data['avg_cost']
        pl = data['value'] - cost
        pl_pct = (pl / cost) * 100

        position = {
            'symbol': symbol,
            'qty': data['qty'],
            'avg_cost': data['avg_cost'],
            'current': data['current'],
            'value': data['value'],
            'weight': data['weight'],
            'cost': cost,
            'pl': pl,
            'pl_pct': pl_pct
        }

        if pl > 0:
            winners.append(position)
        else:
            losers.append(position)

    # Sort by P&L percentage
    winners.sort(key=lambda x: x['pl_pct'], reverse=True)
    losers.sort(key=lambda x: x['pl_pct'])

    # Print winners
    print(f"\n✅ WINNING POSITIONS ({len(winners)})")
    print("-"*100)
    print(f"{'Symbol':<10} {'Qty':<8} {'Avg Cost':<12} {'Current':<12} {'P&L':<15} {'P&L %':<10} {'Weight':<8}")
    print("-"*100)

    for pos in winners:
        print(f"{pos['symbol']:<10} {pos['qty']:<8} {pos['avg_cost']:>10.2f}   {pos['current']:>10.2f}   "
              f"{pos['pl']:>12,.0f}   {pos['pl_pct']:>7.2f}%   {pos['weight']:>6.2f}%")

    # Print losers
    print(f"\n❌ LOSING POSITIONS ({len(losers)})")
    print("-"*100)
    print(f"{'Symbol':<10} {'Qty':<8} {'Avg Cost':<12} {'Current':<12} {'P&L':<15} {'P&L %':<10} {'Weight':<8}")
    print("-"*100)

    for pos in losers:
        print(f"{pos['symbol']:<10} {pos['qty']:<8} {pos['avg_cost']:>10.2f}   {pos['current']:>10.2f}   "
              f"{pos['pl']:>12,.0f}   {pos['pl_pct']:>7.2f}%   {pos['weight']:>6.2f}%")

    # Concentration analysis
    print(f"\n📊 CONCENTRATION ANALYSIS")
    print("-"*100)

    positions_sorted = sorted(portfolio.items(), key=lambda x: x[1]['weight'], reverse=True)

    top5_weight = sum(p[1]['weight'] for p in positions_sorted[:5])
    top10_weight = sum(p[1]['weight'] for p in positions_sorted[:10])

    print(f"   Top 5 positions: {top5_weight:.1f}% of portfolio")
    print(f"   Top 10 positions: {top10_weight:.1f}% of portfolio")
    print(f"\n   Largest positions:")
    for symbol, data in positions_sorted[:5]:
        print(f"      {symbol}: {data['weight']:.2f}%")

    # Risk analysis
    print(f"\n⚠️  RISK ANALYSIS")
    print("-"*100)

    overweight = [s for s, d in portfolio.items() if d['weight'] > 10]
    if overweight:
        print(f"   Positions > 10% (concentration risk): {len(overweight)}")
        for symbol in overweight:
            print(f"      {symbol}: {portfolio[symbol]['weight']:.2f}%")
    else:
        print(f"   ✓ No single position exceeds 10% (good diversification)")

    small_positions = [s for s, d in portfolio.items() if d['weight'] < 3]
    if small_positions:
        print(f"\n   Small positions < 3%: {len(small_positions)}")
        for symbol in small_positions:
            print(f"      {symbol}: {portfolio[symbol]['weight']:.2f}% (PKR {portfolio[symbol]['value']:,.0f})")

    # Recommendations
    print(f"\n🎯 PORTFOLIO RECOMMENDATIONS")
    print("="*100)

    print(f"\n1. REBALANCING SUGGESTIONS:")
    print(f"   • AGP (10.36%) is overweight - consider reducing to 8-10%")
    print(f"   • Consider consolidating small positions (<3%) to reduce tracking complexity")
    print(f"   • Small positions that could be consolidated or exited: HINOON (2.22%), GAL (2.70%)")

    print(f"\n2. PERFORMANCE-BASED ACTIONS:")
    print(f"   ")
    print(f"   🔴 Underperformers to Review:")
    for pos in losers[:3]:
        print(f"      • {pos['symbol']}: {pos['pl_pct']:+.2f}% - Review fundamentals, consider stop loss")

    print(f"\n   🟢 Top Performers to Monitor:")
    for pos in winners[:3]:
        print(f"      • {pos['symbol']}: {pos['pl_pct']:+.2f}% - Consider taking partial profits if overextended")

    print(f"\n3. POSITION SIZING:")
    print(f"   Conservative Model (10% max per position):")
    print(f"      • Reduce: AGP from 10.36% to 10%")

    print(f"\n   Balanced Model (15% max per position):")
    print(f"      • All positions within limits ✓")

    print(f"\n4. RISK MANAGEMENT:")
    print(f"   • Portfolio has {len(portfolio)} positions - good diversification")
    print(f"   • Top 5 positions = {top5_weight:.1f}% (healthy, not over-concentrated)")
    print(f"   • Consider setting stop losses on losing positions")
    print(f"   • Review fundamentals of positions down >10%")

    # Sector analysis (based on stock types)
    print(f"\n5. SECTOR ALLOCATION (Inferred):")

    sectors = {
        'Financial': ['BAFL', 'AGP'],
        'Automobile': ['SAZEW', 'GAL', 'ATLH'],
        'Pharma/Healthcare': ['HINOON', 'BFBIO', 'HALEON'],
        'Food/FMCG': ['NATF', 'BBFL', 'BFAGRO'],
        'Manufacturing': ['PAEL', 'ICL'],
        'Tobacco': ['PAKT'],
        'Shipping': ['PNSC'],
        'Oil & Gas': ['HTL'],
    }

    sector_weights = {}
    for sector, symbols in sectors.items():
        weight = sum(portfolio.get(s, {}).get('weight', 0) for s in symbols)
        if weight > 0:
            sector_weights[sector] = weight

    for sector, weight in sorted(sector_weights.items(), key=lambda x: x[1], reverse=True):
        print(f"      {sector}: {weight:.1f}%")

    print(f"\n6. NEXT STEPS:")
    print(f"   1. Run technical analysis on losing positions (HINOON, PNSC, GAL, BBFL, HTL, PAEL)")
    print(f"   2. Check fundamental health of underperformers")
    print(f"   3. Consider partial profit-taking on positions up >100% (NATF, BAFL, ICL)")
    print(f"   4. Review and rebalance AGP if it continues to grow beyond 10%")
    print(f"   5. Set price alerts for positions near breakeven")

    print("\n" + "="*100)
    print("✅ ANALYSIS COMPLETE")
    print("="*100)
    print("\nNote: For detailed technical and fundamental analysis, run:")
    print("  python run_portfolio_analysis.py --symbols HINOON SAZEW PNSC ... (after installing dependencies)")
    print()

if __name__ == "__main__":
    analyze_portfolio()
