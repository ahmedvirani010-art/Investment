"""
PSX Risk Monitor
Monitoring engine that runs detection and checks on each cycle
"""

import uuid
from datetime import datetime
from typing import List, Optional
from psx_position_manager import PositionManager
from psx_alert_engine import AlertEngine
from psx_risk_limits import RiskLimitEnforcer
from psx_risk_predictor import RiskPredictor
from psx_risk_storage import RiskEvent


class RiskMonitor:
    """
    Risk monitoring engine for EOD analysis

    Orchestrates:
    - Position price updates
    - Anomaly detection
    - Technical signal analysis
    - Predictive signal generation
    - Risk score calculation
    - Limit breach checking
    - Alert generation
    """

    def __init__(self,
                 position_manager: PositionManager,
                 alert_engine: AlertEngine,
                 limit_enforcer: RiskLimitEnforcer,
                 predictor: RiskPredictor,
                 anomaly_agent=None,
                 technical_agent=None):
        """
        Initialize risk monitor

        Args:
            position_manager: PositionManager instance
            alert_engine: AlertEngine instance
            limit_enforcer: RiskLimitEnforcer instance
            predictor: RiskPredictor instance
            anomaly_agent: PSXAnomalyAgent instance (optional)
            technical_agent: PSXTechnicalAgent instance (optional)
        """
        self.position_manager = position_manager
        self.alert_engine = alert_engine
        self.limit_enforcer = limit_enforcer
        self.predictor = predictor
        self.anomaly_agent = anomaly_agent
        self.technical_agent = technical_agent

    def run_eod_monitoring_cycle(self) -> None:
        """
        Execute one complete EOD monitoring cycle

        Steps:
        1. Update position prices
        2. Check risks for each position
        3. Generate alerts
        4. Evaluate position actions
        """
        print(f"\n{'='*80}")
        print(f"EOD MONITORING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*80}\n")

        # 1. Update prices for all positions
        print("📊 Step 1: Updating position prices...")
        self.position_manager.update_position_prices()

        # 2. Get active positions
        positions = self.position_manager.get_active_positions()
        print(f"📈 Step 2: Monitoring {len(positions)} active positions\n")

        if not positions:
            print("No active positions to monitor\n")
            return

        # 3. For each position, check risks
        for position in positions:
            print(f"\n--- Analyzing {position.symbol} ---")

            # Get technical signals if available
            technical_bias = "NEUTRAL"
            if self.technical_agent:
                try:
                    technical = self.technical_agent.analyze_symbol(position.symbol)
                    if technical and hasattr(technical, 'overall_bias'):
                        technical_bias = technical.overall_bias.value
                        print(f"  Technical Bias: {technical_bias}")
                except Exception as e:
                    print(f"  Technical analysis error: {str(e)}")

            # Update position with technical bias
            position.technical_bias = technical_bias

            # Get predictive signals
            predictive_signals = self.predictor.predict_risks(position.symbol)
            if predictive_signals:
                print(f"  ⚠️  Predictive Signals: {len(predictive_signals)}")
                for signal in predictive_signals[:2]:  # Show top 2
                    print(f"    - {signal.signal_type}: {signal.description[:60]}")

            # Calculate risk score
            risk_score = self._calculate_position_risk_score(
                position,
                predictive_signals
            )
            position.risk_score = risk_score
            print(f"  Risk Score: {risk_score:.0f}/100")

            # Check limits
            limit_breaches = self.limit_enforcer.check_position_limits(position)

            if limit_breaches:
                print(f"  🚨 Limit Breaches: {len(limit_breaches)}")
                for breach in limit_breaches:
                    print(f"    - {breach.limit_type}: {breach.description}")

                    # Generate alert for breach
                    alert = self.alert_engine.create_alert(
                        symbol=position.symbol,
                        alert_type=breach.limit_type,
                        severity=breach.severity,
                        description=breach.description,
                        risk_score=risk_score,
                        recommended_action=breach.recommended_action
                    )
                    self.alert_engine.raise_alert(alert)

            # Generate alerts for predictive signals
            for signal in predictive_signals:
                if signal.severity in ["CRITICAL", "HIGH"]:
                    alert = self.alert_engine.create_alert(
                        symbol=position.symbol,
                        alert_type=signal.signal_type,
                        severity=signal.severity,
                        description=signal.description,
                        risk_score=risk_score,
                        recommended_action=signal.recommended_action
                    )
                    self.alert_engine.raise_alert(alert)

            # Evaluate position action
            action = self.position_manager.evaluate_position_action(
                position, limit_breaches
            )

            if action:
                print(f"  📋 Recommended Action: {action.action_type} ({action.urgency})")
                print(f"     Reason: {action.reason}")

                # Execute action (will log to audit)
                self.position_manager.execute_action(position, action)

            # Save updated position
            self.position_manager.storage.save_position(position)

            # Save predictive signals as risk events
            for signal in predictive_signals:
                event = RiskEvent(
                    event_id=signal.signal_id,
                    symbol=signal.symbol,
                    event_type=signal.signal_type,
                    severity=signal.severity,
                    detected_at=signal.detected_at,
                    description=signal.description,
                    risk_score=risk_score,
                    data_json=str(signal.to_dict())
                )
                self.position_manager.storage.save_risk_event(event)

        # 4. Portfolio-level checks
        print(f"\n--- Portfolio Analysis ---")
        self._check_portfolio_risk(positions)

        print(f"\n{'='*80}")
        print("EOD MONITORING CYCLE COMPLETE")
        print(f"{'='*80}\n")

    def _calculate_position_risk_score(self,
                                      position,
                                      predictive_signals: List) -> float:
        """
        Calculate risk score (0-100) for a position

        Factors:
        - Unrealized loss magnitude
        - Distance from stop loss
        - Number and severity of predictive signals
        - Technical bias

        Returns:
            Risk score (0-100, higher = more risky)
        """
        score = 0.0

        # Factor 1: Unrealized loss (0-40 points)
        if position.unrealized_pnl_pct < 0:
            # More loss = higher risk
            loss_points = min(40, abs(position.unrealized_pnl_pct) * 8)  # -5% = 40 points
            score += loss_points

        # Factor 2: Distance from stop loss (0-30 points)
        if position.stop_loss_price and position.current_price > 0:
            distance_from_stop = ((position.current_price - position.stop_loss_price) /
                                 position.stop_loss_price) * 100
            if distance_from_stop < 5:  # Within 5% of stop loss
                score += 30 - (distance_from_stop * 6)  # Closer = higher risk

        # Factor 3: Predictive signals (0-20 points)
        signal_points = 0
        for signal in predictive_signals:
            if signal.severity == "CRITICAL":
                signal_points += 10
            elif signal.severity == "HIGH":
                signal_points += 5
            elif signal.severity == "MEDIUM":
                signal_points += 2
        score += min(20, signal_points)

        # Factor 4: Technical bias (0-10 points)
        if position.technical_bias == "BEARISH":
            score += 10
        elif position.technical_bias == "NEUTRAL":
            score += 5

        return min(100.0, score)

    def _check_portfolio_risk(self, positions: List) -> None:
        """Check portfolio-level risk"""
        if not positions:
            return

        # Calculate total portfolio value
        total_value = sum(p.quantity * p.current_price for p in positions)

        # Check portfolio limits
        breaches = self.limit_enforcer.check_portfolio_limits(
            positions, total_value
        )

        if breaches:
            print(f"  🚨 Portfolio Limit Breaches: {len(breaches)}")
            for breach in breaches:
                print(f"    - {breach.limit_type}: {breach.description}")

                # Generate portfolio-level alert
                alert = self.alert_engine.create_alert(
                    symbol="PORTFOLIO",
                    alert_type=breach.limit_type,
                    severity=breach.severity,
                    description=breach.description,
                    risk_score=0.0,
                    recommended_action=breach.recommended_action
                )
                self.alert_engine.raise_alert(alert)
        else:
            print("  ✓ All portfolio limits OK")

        # Portfolio statistics
        avg_risk = sum(p.risk_score for p in positions) / len(positions) if positions else 0
        max_risk = max((p.risk_score for p in positions), default=0)
        print(f"  Average Position Risk: {avg_risk:.0f}/100")
        print(f"  Max Position Risk: {max_risk:.0f}/100")
