"""
PSX Risk Storage
Persistent storage for risk events, alerts, positions, and audit trail
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class RiskAlert:
    """Risk alert dataclass"""
    alert_id: str
    symbol: str
    alert_type: str
    severity: str
    triggered_at: str
    description: str
    risk_score: float
    recommended_action: str
    acknowledged: bool = False
    resolved: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Position:
    """Position dataclass"""
    position_id: str
    symbol: str
    entry_date: str
    entry_price: float
    quantity: int
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    risk_score: float = 0.0
    stop_loss_price: Optional[float] = None
    target_price: Optional[float] = None
    technical_bias: str = "NEUTRAL"
    status: str = "ACTIVE"
    notes: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RiskEvent:
    """Risk event dataclass (predictive signals, anomalies, etc.)"""
    event_id: str
    symbol: str
    event_type: str
    severity: str
    detected_at: str
    description: str
    risk_score: float
    data_json: str = "{}"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AuditEntry:
    """Audit log entry"""
    audit_id: str
    symbol: str
    action_type: str
    reason: str
    urgency: str
    approved: bool
    executed: bool
    timestamp: str
    position_data_json: str = "{}"
    result: str = ""
    error: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class RiskStorage:
    """
    Database layer for risk management system

    Stores:
    - Risk alerts
    - Positions
    - Risk events (predictive signals, anomalies)
    - Audit log (all actions taken)
    """

    def __init__(self, db_path: str = "risk_data/risk.db"):
        """
        Initialize risk storage

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

        # Create directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Risk alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_alerts (
                    alert_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    triggered_at TEXT NOT NULL,
                    description TEXT,
                    risk_score REAL,
                    recommended_action TEXT,
                    acknowledged BOOLEAN DEFAULT 0,
                    resolved BOOLEAN DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_symbol
                ON risk_alerts(symbol)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_triggered
                ON risk_alerts(triggered_at DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_severity
                ON risk_alerts(severity)
            ''')

            # Positions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    position_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    entry_date TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    current_price REAL DEFAULT 0.0,
                    unrealized_pnl REAL DEFAULT 0.0,
                    unrealized_pnl_pct REAL DEFAULT 0.0,
                    risk_score REAL DEFAULT 0.0,
                    stop_loss_price REAL,
                    target_price REAL,
                    technical_bias TEXT DEFAULT 'NEUTRAL',
                    status TEXT DEFAULT 'ACTIVE',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_positions_symbol
                ON positions(symbol)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_positions_status
                ON positions(status)
            ''')

            # Risk events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_events (
                    event_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    description TEXT,
                    risk_score REAL,
                    data_json TEXT,
                    created_at TEXT NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_symbol
                ON risk_events(symbol)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_detected
                ON risk_events(detected_at DESC)
            ''')

            # Audit log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_actions_audit (
                    audit_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    reason TEXT,
                    urgency TEXT,
                    approved BOOLEAN,
                    executed BOOLEAN,
                    timestamp TEXT NOT NULL,
                    position_data_json TEXT,
                    result TEXT,
                    error TEXT
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_symbol
                ON risk_actions_audit(symbol)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON risk_actions_audit(timestamp DESC)
            ''')

            conn.commit()

    def save_alert(self, alert: RiskAlert) -> None:
        """Save risk alert to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO risk_alerts
                (alert_id, symbol, alert_type, severity, triggered_at, description,
                 risk_score, recommended_action, acknowledged, resolved, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id,
                alert.symbol,
                alert.alert_type,
                alert.severity,
                alert.triggered_at,
                alert.description,
                alert.risk_score,
                alert.recommended_action,
                alert.acknowledged,
                alert.resolved,
                datetime.now().isoformat()
            ))
            conn.commit()

    def save_position(self, position: Position) -> None:
        """Save or update position"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if position exists
            cursor.execute('SELECT position_id FROM positions WHERE position_id = ?',
                          (position.position_id,))
            exists = cursor.fetchone() is not None

            if exists:
                # Update existing position
                cursor.execute('''
                    UPDATE positions SET
                    current_price = ?,
                    unrealized_pnl = ?,
                    unrealized_pnl_pct = ?,
                    risk_score = ?,
                    stop_loss_price = ?,
                    target_price = ?,
                    technical_bias = ?,
                    status = ?,
                    notes = ?,
                    updated_at = ?
                    WHERE position_id = ?
                ''', (
                    position.current_price,
                    position.unrealized_pnl,
                    position.unrealized_pnl_pct,
                    position.risk_score,
                    position.stop_loss_price,
                    position.target_price,
                    position.technical_bias,
                    position.status,
                    position.notes,
                    datetime.now().isoformat(),
                    position.position_id
                ))
            else:
                # Insert new position
                cursor.execute('''
                    INSERT INTO positions
                    (position_id, symbol, entry_date, entry_price, quantity,
                     current_price, unrealized_pnl, unrealized_pnl_pct, risk_score,
                     stop_loss_price, target_price, technical_bias, status, notes,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    position.position_id,
                    position.symbol,
                    position.entry_date,
                    position.entry_price,
                    position.quantity,
                    position.current_price,
                    position.unrealized_pnl,
                    position.unrealized_pnl_pct,
                    position.risk_score,
                    position.stop_loss_price,
                    position.target_price,
                    position.technical_bias,
                    position.status,
                    position.notes,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            conn.commit()

    def save_risk_event(self, event: RiskEvent) -> None:
        """Save risk event (predictive signal, anomaly, etc.)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO risk_events
                (event_id, symbol, event_type, severity, detected_at, description,
                 risk_score, data_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id,
                event.symbol,
                event.event_type,
                event.severity,
                event.detected_at,
                event.description,
                event.risk_score,
                event.data_json,
                datetime.now().isoformat()
            ))
            conn.commit()

    def save_audit_entry(self, audit: AuditEntry) -> None:
        """Save audit log entry"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO risk_actions_audit
                (audit_id, symbol, action_type, reason, urgency, approved, executed,
                 timestamp, position_data_json, result, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                audit.audit_id,
                audit.symbol,
                audit.action_type,
                audit.reason,
                audit.urgency,
                audit.approved,
                audit.executed,
                audit.timestamp,
                audit.position_data_json,
                audit.result,
                audit.error
            ))
            conn.commit()

    def get_active_alerts(self, limit: int = 100) -> List[RiskAlert]:
        """Get active (unresolved) alerts"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT alert_id, symbol, alert_type, severity, triggered_at,
                       description, risk_score, recommended_action, acknowledged, resolved
                FROM risk_alerts
                WHERE resolved = 0
                ORDER BY triggered_at DESC
                LIMIT ?
            ''', (limit,))

            alerts = []
            for row in cursor.fetchall():
                alerts.append(RiskAlert(
                    alert_id=row[0],
                    symbol=row[1],
                    alert_type=row[2],
                    severity=row[3],
                    triggered_at=row[4],
                    description=row[5],
                    risk_score=row[6],
                    recommended_action=row[7],
                    acknowledged=bool(row[8]),
                    resolved=bool(row[9])
                ))
            return alerts

    def get_active_positions(self) -> List[Position]:
        """Get all active positions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT position_id, symbol, entry_date, entry_price, quantity,
                       current_price, unrealized_pnl, unrealized_pnl_pct, risk_score,
                       stop_loss_price, target_price, technical_bias, status, notes
                FROM positions
                WHERE status = 'ACTIVE'
                ORDER BY symbol
            ''')

            positions = []
            for row in cursor.fetchall():
                positions.append(Position(
                    position_id=row[0],
                    symbol=row[1],
                    entry_date=row[2],
                    entry_price=row[3],
                    quantity=row[4],
                    current_price=row[5],
                    unrealized_pnl=row[6],
                    unrealized_pnl_pct=row[7],
                    risk_score=row[8],
                    stop_loss_price=row[9],
                    target_price=row[10],
                    technical_bias=row[11],
                    status=row[12],
                    notes=row[13]
                ))
            return positions

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT position_id, symbol, entry_date, entry_price, quantity,
                       current_price, unrealized_pnl, unrealized_pnl_pct, risk_score,
                       stop_loss_price, target_price, technical_bias, status, notes
                FROM positions
                WHERE symbol = ? AND status = 'ACTIVE'
                LIMIT 1
            ''', (symbol,))

            row = cursor.fetchone()
            if row:
                return Position(
                    position_id=row[0],
                    symbol=row[1],
                    entry_date=row[2],
                    entry_price=row[3],
                    quantity=row[4],
                    current_price=row[5],
                    unrealized_pnl=row[6],
                    unrealized_pnl_pct=row[7],
                    risk_score=row[8],
                    stop_loss_price=row[9],
                    target_price=row[10],
                    technical_bias=row[11],
                    status=row[12],
                    notes=row[13]
                )
            return None

    def acknowledge_alert(self, alert_id: str) -> None:
        """Mark alert as acknowledged"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE risk_alerts SET acknowledged = 1
                WHERE alert_id = ?
            ''', (alert_id,))
            conn.commit()

    def resolve_alert(self, alert_id: str) -> None:
        """Mark alert as resolved"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE risk_alerts SET resolved = 1
                WHERE alert_id = ?
            ''', (alert_id,))
            conn.commit()

    def get_recent_events(self, symbol: Optional[str] = None, limit: int = 50) -> List[RiskEvent]:
        """Get recent risk events"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if symbol:
                cursor.execute('''
                    SELECT event_id, symbol, event_type, severity, detected_at,
                           description, risk_score, data_json
                    FROM risk_events
                    WHERE symbol = ?
                    ORDER BY detected_at DESC
                    LIMIT ?
                ''', (symbol, limit))
            else:
                cursor.execute('''
                    SELECT event_id, symbol, event_type, severity, detected_at,
                           description, risk_score, data_json
                    FROM risk_events
                    ORDER BY detected_at DESC
                    LIMIT ?
                ''', (limit,))

            events = []
            for row in cursor.fetchall():
                events.append(RiskEvent(
                    event_id=row[0],
                    symbol=row[1],
                    event_type=row[2],
                    severity=row[3],
                    detected_at=row[4],
                    description=row[5],
                    risk_score=row[6],
                    data_json=row[7]
                ))
            return events

    def get_audit_log(self, symbol: Optional[str] = None, limit: int = 100) -> List[AuditEntry]:
        """Get audit log entries"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if symbol:
                cursor.execute('''
                    SELECT audit_id, symbol, action_type, reason, urgency, approved,
                           executed, timestamp, position_data_json, result, error
                    FROM risk_actions_audit
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (symbol, limit))
            else:
                cursor.execute('''
                    SELECT audit_id, symbol, action_type, reason, urgency, approved,
                           executed, timestamp, position_data_json, result, error
                    FROM risk_actions_audit
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

            entries = []
            for row in cursor.fetchall():
                entries.append(AuditEntry(
                    audit_id=row[0],
                    symbol=row[1],
                    action_type=row[2],
                    reason=row[3],
                    urgency=row[4],
                    approved=bool(row[5]),
                    executed=bool(row[6]),
                    timestamp=row[7],
                    position_data_json=row[8],
                    result=row[9],
                    error=row[10]
                ))
            return entries

    def get_stats(self) -> Dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM risk_alerts WHERE resolved = 0')
            active_alerts = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM positions WHERE status = "ACTIVE"')
            active_positions = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM risk_events')
            total_events = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM risk_actions_audit')
            total_audit_entries = cursor.fetchone()[0]

            return {
                'active_alerts': active_alerts,
                'active_positions': active_positions,
                'total_events': total_events,
                'total_audit_entries': total_audit_entries
            }
