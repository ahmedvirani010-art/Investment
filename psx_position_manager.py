"""
PSX Position Manager
Position tracking and automated action execution with approval workflow
"""

import uuid
import json
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
from psx_risk_storage import RiskStorage, Position, AuditEntry
from psx_risk_limits import RiskLimitEnforcer, LimitBreach
from psx_alert_engine import AlertEngine


@dataclass
class PositionAction:
    """Position action to be taken"""
    action_type: str  # EXIT, REDUCE, TIGHTEN_STOP
    urgency: str      # IMMEDIATE, HIGH, MEDIUM
    reason: str
    quantity: Optional[int] = None
    new_stop_loss: Optional[float] = None

    def to_dict(self):
        return {
            'action_type': self.action_type,
            'urgency': self.urgency,
            'reason': self.reason,
            'quantity': self.quantity,
            'new_stop_loss': self.new_stop_loss
        }


class PositionManager:
    """
    Position tracking and automated action execution

    Features:
    - Position tracking with P&L calculation
    - Action evaluation based on risk limits
    - Approval workflow (manual or auto-execute)
    - Audit trail for all decisions
    """

    def __init__(self,
                 storage: RiskStorage,
                 alert_engine: AlertEngine,
                 limit_enforcer: RiskLimitEnforcer,
                 price_store=None,
                 auto_execute: bool = False):
        """
        Initialize position manager

        Args:
            storage: RiskStorage instance
            alert_engine: AlertEngine instance
            limit_enforcer: RiskLimitEnforcer instance
            price_store: PSXPriceStore instance (for price updates)
            auto_execute: Enable auto-execution (default False for safety)
        """
        self.storage = storage
        self.alert_engine = alert_engine
        self.limit_enforcer = limit_enforcer
        self.price_store = price_store
        self.auto_execute = auto_execute

    def get_active_positions(self) -> List[Position]:
        """Get all active positions"""
        return self.storage.get_active_positions()

    def add_position(self,
                     symbol: str,
                     entry_price: float,
                     quantity: int,
                     stop_loss_pct: Optional[float] = None) -> Position:
        """
        Add a new position

        Args:
            symbol: Stock symbol
            entry_price: Entry price
            quantity: Number of shares
            stop_loss_pct: Stop loss percentage (uses default if None)

        Returns:
            Created Position
        """
        # Calculate stop loss
        stop_loss_price = self.limit_enforcer.get_stop_loss_price(
            entry_price, stop_loss_pct
        )

        position = Position(
            position_id=str(uuid.uuid4()),
            symbol=symbol,
            entry_date=datetime.now().isoformat(),
            entry_price=entry_price,
            quantity=quantity,
            current_price=entry_price,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            risk_score=0.0,
            stop_loss_price=stop_loss_price,
            status="ACTIVE"
        )

        self.storage.save_position(position)
        return position

    def update_position_prices(self) -> None:
        """Update current prices for all active positions"""
        if not self.price_store:
            return

        positions = self.get_active_positions()

        for position in positions:
            try:
                # Fetch latest price
                df = self.price_store.get_prices(position.symbol, days=1)
                if not df.empty:
                    close_col = 'close' if 'close' in df.columns else 'Close'
                    current_price = df[close_col].iloc[-1]

                    # Update P&L
                    position.current_price = current_price
                    position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
                    position.unrealized_pnl_pct = ((current_price / position.entry_price) - 1) * 100

                    # Save updated position
                    self.storage.save_position(position)

            except Exception as e:
                print(f"Error updating price for {position.symbol}: {str(e)}")

    def evaluate_position_action(self,
                                position: Position,
                                limit_breaches: List[LimitBreach]) -> Optional[PositionAction]:
        """
        Determine what action to take on a position

        Args:
            position: Position to evaluate
            limit_breaches: List of limit breaches

        Returns:
            PositionAction if action needed, None otherwise
        """
        # CRITICAL: Stop loss breached
        if any(b.limit_type in ["STOP_LOSS", "STOP_LOSS_PCT"] for b in limit_breaches):
            return PositionAction(
                action_type="EXIT",
                urgency="IMMEDIATE",
                reason="Stop loss breached",
                quantity=position.quantity
            )

        # HIGH: Risk score too high
        if position.risk_score > 80:
            return PositionAction(
                action_type="REDUCE",
                urgency="HIGH",
                reason=f"Risk score {position.risk_score:.0f}",
                quantity=position.quantity // 2  # Reduce by 50%
            )

        # HIGH: Approaching stop loss
        if any(b.limit_type == "APPROACHING_STOP_LOSS" for b in limit_breaches):
            return PositionAction(
                action_type="MONITOR",
                urgency="HIGH",
                reason="Approaching stop loss",
                quantity=None
            )

        # MEDIUM: Technical reversal while in profit
        if position.technical_bias == "BEARISH" and position.unrealized_pnl_pct > 0:
            trailing_stop = self.limit_enforcer.get_trailing_stop_price(position.current_price)
            return PositionAction(
                action_type="TIGHTEN_STOP",
                urgency="MEDIUM",
                reason="Technical reversal while in profit",
                new_stop_loss=trailing_stop
            )

        return None

    def execute_action(self, position: Position, action: PositionAction) -> bool:
        """
        Execute position action (with safety checks)

        Args:
            position: Position to act on
            action: Action to execute

        Returns:
            True if executed, False otherwise
        """
        if not self.auto_execute:
            # Manual approval mode
            print(f"\n{'='*60}")
            print(f"POSITION ACTION REQUIRED - {action.urgency}")
            print(f"{'='*60}")
            print(f"Symbol: {position.symbol}")
            print(f"Action: {action.action_type}")
            print(f"Reason: {action.reason}")
            if action.quantity:
                print(f"Quantity: {action.quantity}")
            if action.new_stop_loss:
                print(f"New Stop Loss: {action.new_stop_loss:.2f}")
            print(f"\nManual approval required (auto_execute=False)")

            # Log to audit
            self._log_action_to_audit(position, action, approved=False, executed=False)
            return False

        # Auto-execute (with validation)
        try:
            if action.action_type == "EXIT":
                result = self._exit_position(position)
            elif action.action_type == "REDUCE":
                result = self._reduce_position(position, action.quantity)
            elif action.action_type == "TIGHTEN_STOP":
                result = self._update_stop_loss(position, action.new_stop_loss)
            elif action.action_type == "MONITOR":
                result = True  # No action needed, just log
            else:
                result = False

            # Log to audit
            self._log_action_to_audit(position, action, approved=True, executed=result)

            # Send confirmation alert
            if result:
                self._send_action_confirmation(position, action)

            return result

        except Exception as e:
            print(f"ERROR executing action: {str(e)}")
            self._log_action_to_audit(
                position, action,
                approved=True, executed=False,
                error=str(e)
            )
            return False

    def _exit_position(self, position: Position) -> bool:
        """Exit position completely"""
        position.status = "CLOSED"
        position.quantity = 0
        self.storage.save_position(position)
        print(f"✓ Exited position {position.symbol}")
        return True

    def _reduce_position(self, position: Position, reduce_quantity: int) -> bool:
        """Reduce position size"""
        new_quantity = max(0, position.quantity - reduce_quantity)
        position.quantity = new_quantity
        if new_quantity == 0:
            position.status = "CLOSED"
        self.storage.save_position(position)
        print(f"✓ Reduced {position.symbol} to {new_quantity} shares")
        return True

    def _update_stop_loss(self, position: Position, new_stop_loss: float) -> bool:
        """Update stop loss price"""
        position.stop_loss_price = new_stop_loss
        self.storage.save_position(position)
        print(f"✓ Updated {position.symbol} stop loss to {new_stop_loss:.2f}")
        return True

    def _log_action_to_audit(self,
                             position: Position,
                             action: PositionAction,
                             approved: bool,
                             executed: bool,
                             error: str = "") -> None:
        """Log action to audit trail"""
        audit = AuditEntry(
            audit_id=str(uuid.uuid4()),
            symbol=position.symbol,
            action_type=action.action_type,
            reason=action.reason,
            urgency=action.urgency,
            approved=approved,
            executed=executed,
            timestamp=datetime.now().isoformat(),
            position_data_json=json.dumps(position.to_dict()),
            result="Success" if executed else "Pending" if not approved else "Failed",
            error=error
        )
        self.storage.save_audit_entry(audit)

    def _send_action_confirmation(self, position: Position, action: PositionAction) -> None:
        """Send alert confirming action taken"""
        alert = self.alert_engine.create_alert(
            symbol=position.symbol,
            alert_type="ACTION_EXECUTED",
            severity="HIGH",
            description=f"Action executed: {action.action_type} - {action.reason}",
            risk_score=position.risk_score,
            recommended_action="Review execution"
        )
        self.alert_engine.raise_alert(alert)

    def close_position(self, symbol: str) -> bool:
        """Manually close a position"""
        position = self.storage.get_position(symbol)
        if not position:
            print(f"Position not found: {symbol}")
            return False

        return self._exit_position(position)
