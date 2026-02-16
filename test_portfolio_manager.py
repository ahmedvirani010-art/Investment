#!/usr/bin/env python3
"""
Unit Tests for PSX Portfolio Manager

Tests core functionality of portfolio manager components.
"""

import unittest
from datetime import datetime

from psx_portfolio_models import (
    PortfolioConfig, Position, PortfolioSnapshot, TradingSignal,
    TradeDecision, ActionType, CONSERVATIVE_MODEL, BALANCED_MODEL,
    AGGRESSIVE_MODEL
)
from psx_portfolio_utils import (
    convert_technical_to_score,
    convert_fundamental_to_score,
    calculate_signal_confidence
)
from psx_technical_agent import TechnicalSnapshot, SignalType
from psx_fundamental_agent import FundamentalScore, Recommendation, Confidence, ValuationMetrics, FinancialHealthMetrics, GrowthMetrics, MomentumMetrics


class TestPortfolioModels(unittest.TestCase):
    """Test portfolio models and data structures"""

    def test_portfolio_config_creation(self):
        """Test creating portfolio config"""
        config = PortfolioConfig(name="test", initial_cash=500_000.0)
        self.assertEqual(config.name, "test")
        self.assertEqual(config.initial_cash, 500_000.0)
        self.assertEqual(config.max_position_pct, 15.0)

    def test_position_market_value_update(self):
        """Test position market value calculation"""
        position = Position(
            symbol="HBL",
            quantity=1000,
            average_cost=150.0,
            current_price=150.0
        )
        position.update_market_value(160.0)

        self.assertEqual(position.current_price, 160.0)
        self.assertEqual(position.market_value, 160_000.0)
        self.assertEqual(position.unrealized_pl, 10_000.0)
        self.assertAlmostEqual(position.unrealized_pl_pct, 6.67, places=1)

    def test_portfolio_snapshot_totals(self):
        """Test portfolio snapshot calculations"""
        pos1 = Position("HBL", 1000, 150.0, 160.0)
        pos1.update_market_value(160.0)

        pos2 = Position("LUCK", 200, 700.0, 720.0)
        pos2.update_market_value(720.0)

        snapshot = PortfolioSnapshot(
            portfolio_name="test",
            cash=500_000.0,
            positions={"HBL": pos1, "LUCK": pos2}
        )
        snapshot.calculate_totals()

        self.assertEqual(snapshot.position_count, 2)
        self.assertEqual(snapshot.total_market_value, 304_000.0)  # 160k + 144k
        self.assertEqual(snapshot.total_unrealized_pl, 14_000.0)  # 10k + 4k
        self.assertEqual(snapshot.total_equity, 804_000.0)  # 500k + 304k

    def test_model_weights_sum_to_one(self):
        """Test that model weights sum to 1.0"""
        for model in [CONSERVATIVE_MODEL, BALANCED_MODEL, AGGRESSIVE_MODEL]:
            total = (model.technical_weight + model.fundamental_weight +
                    model.anomaly_weight + model.news_weight)
            self.assertAlmostEqual(total, 1.0, places=2)

    def test_model_characteristics(self):
        """Test model-specific characteristics"""
        # Conservative should favor fundamentals
        self.assertGreater(CONSERVATIVE_MODEL.fundamental_weight,
                          CONSERVATIVE_MODEL.technical_weight)

        # Aggressive should favor technicals
        self.assertGreater(AGGRESSIVE_MODEL.technical_weight,
                          AGGRESSIVE_MODEL.fundamental_weight)

        # Conservative should have higher thresholds
        self.assertGreater(CONSERVATIVE_MODEL.buy_threshold,
                          AGGRESSIVE_MODEL.buy_threshold)
        self.assertGreater(CONSERVATIVE_MODEL.min_confidence,
                          AGGRESSIVE_MODEL.min_confidence)


class TestPortfolioUtils(unittest.TestCase):
    """Test portfolio utility functions"""

    def test_convert_technical_bullish(self):
        """Test converting bullish technical snapshot"""
        snapshot = TechnicalSnapshot(
            symbol="HBL",
            date="2024-01-01",
            overall_bias=SignalType.BULLISH,
            confidence=0.8
        )
        score = convert_technical_to_score(snapshot)
        self.assertGreater(score, 50.0)
        self.assertLessEqual(score, 100.0)

    def test_convert_technical_bearish(self):
        """Test converting bearish technical snapshot"""
        snapshot = TechnicalSnapshot(
            symbol="HBL",
            date="2024-01-01",
            overall_bias=SignalType.BEARISH,
            confidence=0.8
        )
        score = convert_technical_to_score(snapshot)
        self.assertLess(score, 50.0)
        self.assertGreaterEqual(score, 0.0)

    def test_convert_technical_neutral(self):
        """Test converting neutral technical snapshot"""
        snapshot = TechnicalSnapshot(
            symbol="HBL",
            date="2024-01-01",
            overall_bias=SignalType.NEUTRAL,
            confidence=0.5
        )
        score = convert_technical_to_score(snapshot)
        self.assertEqual(score, 50.0)

    def test_convert_fundamental_score(self):
        """Test converting fundamental score"""
        fundamental = FundamentalScore(
            symbol="HBL",
            fundamental_score=75.0,
            recommendation=Recommendation.BUY,
            confidence=Confidence.HIGH,
            valuation=ValuationMetrics(),
            financial_health=FinancialHealthMetrics(),
            growth_metrics=GrowthMetrics(),
            momentum_metrics=MomentumMetrics()
        )
        score = convert_fundamental_to_score(fundamental)
        self.assertEqual(score, 75.0)

    def test_calculate_signal_confidence_high_agreement(self):
        """Test confidence calculation with high agreement"""
        # All scores high (bullish agreement)
        confidence = calculate_signal_confidence(80.0, 85.0, 75.0, 82.0)
        self.assertGreater(confidence, 0.7)

    def test_calculate_signal_confidence_low_agreement(self):
        """Test confidence calculation with low agreement"""
        # Conflicting scores
        confidence = calculate_signal_confidence(80.0, 30.0, 50.0, 70.0)
        self.assertLess(confidence, 0.7)


class TestActionTypes(unittest.TestCase):
    """Test action type enums"""

    def test_action_types(self):
        """Test all action types are defined"""
        actions = [ActionType.BUY, ActionType.SELL, ActionType.REDUCE, ActionType.HOLD]
        self.assertEqual(len(actions), 4)

    def test_action_values(self):
        """Test action type values"""
        self.assertEqual(ActionType.BUY.value, "BUY")
        self.assertEqual(ActionType.SELL.value, "SELL")
        self.assertEqual(ActionType.REDUCE.value, "REDUCE")
        self.assertEqual(ActionType.HOLD.value, "HOLD")


class TestTradeDecision(unittest.TestCase):
    """Test trade decision creation and validation"""

    def test_buy_decision_creation(self):
        """Test creating BUY decision"""
        decision = TradeDecision(
            symbol="HBL",
            action=ActionType.BUY,
            quantity=1000,
            target_price=150.0,
            composite_score=75.0,
            confidence=0.8
        )
        self.assertEqual(decision.action, ActionType.BUY)
        self.assertEqual(decision.quantity, 1000)
        self.assertFalse(decision.violates_constraints)

    def test_decision_to_dict(self):
        """Test converting decision to dictionary"""
        decision = TradeDecision(
            symbol="HBL",
            action=ActionType.BUY,
            quantity=1000,
            composite_score=75.0
        )
        data = decision.to_dict()
        self.assertIn('symbol', data)
        self.assertIn('action', data)
        self.assertEqual(data['action'], 'BUY')


def run_tests():
    """Run all tests"""
    print("="*100)
    print("🧪 PSX PORTFOLIO MANAGER - UNIT TESTS")
    print("="*100)

    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestPortfolioModels))
    suite.addTests(loader.loadTestsFromTestCase(TestPortfolioUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestActionTypes))
    suite.addTests(loader.loadTestsFromTestCase(TestTradeDecision))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*100)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
    print("="*100)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
