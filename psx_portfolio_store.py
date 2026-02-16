"""
PSX Portfolio Store
Persistent storage layer for portfolio state, positions, and transactions
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

from psx_portfolio_models import (
    PortfolioConfig, Position, PortfolioSnapshot, TradeDecision
)


class PSXPortfolioStore:
    """
    Persistent storage for portfolio data

    Stores:
    - Portfolio configuration
    - Current positions
    - Transaction history
    - Portfolio snapshots (for performance tracking)
    - Trade decisions (for audit trail)
    """

    def __init__(self, db_path: str = "portfolio_data/portfolio.db"):
        """
        Initialize portfolio store

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

            # Portfolio configuration table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_config (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    initial_cash REAL NOT NULL,
                    max_position_pct REAL NOT NULL,
                    max_positions INTEGER NOT NULL,
                    min_cash_reserve_pct REAL NOT NULL,
                    max_single_order_value REAL NOT NULL,
                    lot_size INTEGER NOT NULL,
                    transaction_fee_pct REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # Current positions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    average_cost REAL NOT NULL,
                    current_price REAL NOT NULL,
                    market_value REAL NOT NULL,
                    unrealized_pl REAL NOT NULL,
                    unrealized_pl_pct REAL NOT NULL,
                    opened_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    UNIQUE(portfolio_name, symbol)
                )
            ''')

            # Transaction history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    fees REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    notes TEXT
                )
            ''')

            # Portfolio snapshots table (for performance tracking)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    cash REAL NOT NULL,
                    total_equity REAL NOT NULL,
                    total_market_value REAL NOT NULL,
                    unrealized_pl REAL NOT NULL,
                    position_count INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
            ''')

            # Trade decisions table (audit trail)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_name TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    decision_date TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    target_price REAL,
                    confidence REAL NOT NULL,
                    composite_score REAL NOT NULL,
                    reasoning_json TEXT NOT NULL,
                    executed BOOLEAN DEFAULT 0,
                    execution_price REAL,
                    execution_timestamp TEXT
                )
            ''')

            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_positions_portfolio
                ON positions(portfolio_name)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_transactions_portfolio
                ON transactions(portfolio_name, timestamp DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio
                ON portfolio_snapshots(portfolio_name, timestamp DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_decisions_portfolio
                ON trade_decisions(portfolio_name, decision_date DESC)
            ''')

            conn.commit()

    # ===== Portfolio Configuration =====

    def save_config(self, config: PortfolioConfig):
        """
        Save or update portfolio configuration

        Args:
            config: PortfolioConfig instance
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO portfolio_config (
                    name, initial_cash, max_position_pct, max_positions,
                    min_cash_reserve_pct, max_single_order_value, lot_size,
                    transaction_fee_pct, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config.name, config.initial_cash, config.max_position_pct,
                config.max_positions, config.min_cash_reserve_pct,
                config.max_single_order_value, config.lot_size,
                config.transaction_fee_pct, config.created_at,
                datetime.now().isoformat()
            ))

            conn.commit()

    def get_config(self, portfolio_name: str) -> Optional[PortfolioConfig]:
        """
        Get portfolio configuration

        Args:
            portfolio_name: Portfolio name

        Returns:
            PortfolioConfig or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT name, initial_cash, max_position_pct, max_positions,
                       min_cash_reserve_pct, max_single_order_value, lot_size,
                       transaction_fee_pct, created_at, updated_at
                FROM portfolio_config
                WHERE name = ?
            ''', (portfolio_name,))

            row = cursor.fetchone()
            if not row:
                return None

            return PortfolioConfig(
                name=row[0],
                initial_cash=row[1],
                max_position_pct=row[2],
                max_positions=row[3],
                min_cash_reserve_pct=row[4],
                max_single_order_value=row[5],
                lot_size=row[6],
                transaction_fee_pct=row[7],
                created_at=row[8],
                updated_at=row[9]
            )

    # ===== Position Management =====

    def get_position(self, portfolio_name: str, symbol: str) -> Optional[Position]:
        """
        Get current position for a symbol

        Args:
            portfolio_name: Portfolio name
            symbol: Stock symbol

        Returns:
            Position or None if no position
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT symbol, quantity, average_cost, current_price,
                       market_value, unrealized_pl, unrealized_pl_pct,
                       opened_date, last_updated
                FROM positions
                WHERE portfolio_name = ? AND symbol = ?
            ''', (portfolio_name, symbol))

            row = cursor.fetchone()
            if not row:
                return None

            return Position(
                symbol=row[0],
                quantity=row[1],
                average_cost=row[2],
                current_price=row[3],
                market_value=row[4],
                unrealized_pl=row[5],
                unrealized_pl_pct=row[6],
                opened_date=row[7],
                last_updated=row[8]
            )

    def get_all_positions(self, portfolio_name: str) -> Dict[str, Position]:
        """
        Get all positions for a portfolio

        Args:
            portfolio_name: Portfolio name

        Returns:
            Dictionary of symbol -> Position
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT symbol, quantity, average_cost, current_price,
                       market_value, unrealized_pl, unrealized_pl_pct,
                       opened_date, last_updated
                FROM positions
                WHERE portfolio_name = ?
            ''', (portfolio_name,))

            positions = {}
            for row in cursor.fetchall():
                position = Position(
                    symbol=row[0],
                    quantity=row[1],
                    average_cost=row[2],
                    current_price=row[3],
                    market_value=row[4],
                    unrealized_pl=row[5],
                    unrealized_pl_pct=row[6],
                    opened_date=row[7],
                    last_updated=row[8]
                )
                positions[position.symbol] = position

            return positions

    def update_position(self, portfolio_name: str, position: Position):
        """
        Update or insert a position

        Args:
            portfolio_name: Portfolio name
            position: Position instance
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO positions (
                    portfolio_name, symbol, quantity, average_cost,
                    current_price, market_value, unrealized_pl, unrealized_pl_pct,
                    opened_date, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                portfolio_name, position.symbol, position.quantity,
                position.average_cost, position.current_price,
                position.market_value, position.unrealized_pl,
                position.unrealized_pl_pct, position.opened_date,
                position.last_updated
            ))

            conn.commit()

    def delete_position(self, portfolio_name: str, symbol: str):
        """
        Delete a position (when fully sold)

        Args:
            portfolio_name: Portfolio name
            symbol: Stock symbol
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM positions
                WHERE portfolio_name = ? AND symbol = ?
            ''', (portfolio_name, symbol))

            conn.commit()

    # ===== Transaction Management =====

    def record_transaction(
        self,
        portfolio_name: str,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        fees: float,
        notes: str = ""
    ):
        """
        Record a transaction

        Args:
            portfolio_name: Portfolio name
            symbol: Stock symbol
            action: "BUY" or "SELL"
            quantity: Number of shares
            price: Price per share
            fees: Transaction fees
            notes: Optional notes
        """
        total_amount = quantity * price + fees

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO transactions (
                    portfolio_name, symbol, action, quantity, price,
                    fees, total_amount, timestamp, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                portfolio_name, symbol, action, quantity, price,
                fees, total_amount, datetime.now().isoformat(), notes
            ))

            conn.commit()

    def get_transactions(
        self,
        portfolio_name: str,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get transaction history

        Args:
            portfolio_name: Portfolio name
            symbol: Optional symbol filter
            limit: Maximum number of transactions to return

        Returns:
            List of transaction dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if symbol:
                cursor.execute('''
                    SELECT id, symbol, action, quantity, price, fees,
                           total_amount, timestamp, notes
                    FROM transactions
                    WHERE portfolio_name = ? AND symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (portfolio_name, symbol, limit))
            else:
                cursor.execute('''
                    SELECT id, symbol, action, quantity, price, fees,
                           total_amount, timestamp, notes
                    FROM transactions
                    WHERE portfolio_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (portfolio_name, limit))

            transactions = []
            for row in cursor.fetchall():
                transactions.append({
                    'id': row[0],
                    'symbol': row[1],
                    'action': row[2],
                    'quantity': row[3],
                    'price': row[4],
                    'fees': row[5],
                    'total_amount': row[6],
                    'timestamp': row[7],
                    'notes': row[8]
                })

            return transactions

    # ===== Portfolio Snapshot Management =====

    def save_snapshot(self, snapshot: PortfolioSnapshot):
        """
        Save a portfolio snapshot

        Args:
            snapshot: PortfolioSnapshot instance
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO portfolio_snapshots (
                    portfolio_name, timestamp, cash, total_equity,
                    total_market_value, unrealized_pl, position_count,
                    snapshot_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot.portfolio_name,
                snapshot.timestamp,
                snapshot.cash,
                snapshot.total_equity,
                snapshot.total_market_value,
                snapshot.total_unrealized_pl,
                snapshot.position_count,
                json.dumps(snapshot.to_dict())
            ))

            conn.commit()

    def get_latest_snapshot(self, portfolio_name: str) -> Optional[PortfolioSnapshot]:
        """
        Get the most recent portfolio snapshot

        Args:
            portfolio_name: Portfolio name

        Returns:
            PortfolioSnapshot or None if no snapshots
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT snapshot_json
                FROM portfolio_snapshots
                WHERE portfolio_name = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (portfolio_name,))

            row = cursor.fetchone()
            if not row:
                return None

            data = json.loads(row[0])

            # Reconstruct PortfolioSnapshot from dict
            positions = {}
            for symbol, pos_dict in data.get('positions', {}).items():
                positions[symbol] = Position(**pos_dict)

            snapshot = PortfolioSnapshot(
                portfolio_name=data['portfolio_name'],
                timestamp=data['timestamp'],
                cash=data['cash'],
                total_equity=data['total_equity'],
                total_market_value=data['total_market_value'],
                total_unrealized_pl=data['total_unrealized_pl'],
                position_count=data['position_count'],
                cash_pct=data['cash_pct'],
                invested_pct=data['invested_pct'],
                positions=positions
            )

            return snapshot

    # ===== Trade Decision Management =====

    def save_decision(
        self,
        portfolio_name: str,
        model_name: str,
        decision: TradeDecision
    ):
        """
        Save a trade decision

        Args:
            portfolio_name: Portfolio name
            model_name: Model name (conservative/balanced/aggressive)
            decision: TradeDecision instance
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO trade_decisions (
                    portfolio_name, model_name, symbol, decision_date,
                    action, quantity, target_price, confidence,
                    composite_score, reasoning_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                portfolio_name,
                model_name,
                decision.symbol,
                decision.date,
                decision.action.value,
                decision.quantity,
                decision.target_price,
                decision.confidence,
                decision.composite_score,
                json.dumps(decision.to_dict())
            ))

            conn.commit()

    def get_recent_decisions(
        self,
        portfolio_name: str,
        model_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent trade decisions

        Args:
            portfolio_name: Portfolio name
            model_name: Optional model filter
            limit: Maximum number of decisions to return

        Returns:
            List of decision dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if model_name:
                cursor.execute('''
                    SELECT id, model_name, symbol, decision_date, action,
                           quantity, confidence, composite_score
                    FROM trade_decisions
                    WHERE portfolio_name = ? AND model_name = ?
                    ORDER BY decision_date DESC
                    LIMIT ?
                ''', (portfolio_name, model_name, limit))
            else:
                cursor.execute('''
                    SELECT id, model_name, symbol, decision_date, action,
                           quantity, confidence, composite_score
                    FROM trade_decisions
                    WHERE portfolio_name = ?
                    ORDER BY decision_date DESC
                    LIMIT ?
                ''', (portfolio_name, limit))

            decisions = []
            for row in cursor.fetchall():
                decisions.append({
                    'id': row[0],
                    'model_name': row[1],
                    'symbol': row[2],
                    'decision_date': row[3],
                    'action': row[4],
                    'quantity': row[5],
                    'confidence': row[6],
                    'composite_score': row[7]
                })

            return decisions

    # ===== Cash Management =====

    def get_cash_balance(self, portfolio_name: str) -> float:
        """
        Get current cash balance from latest snapshot

        Args:
            portfolio_name: Portfolio name

        Returns:
            Cash balance (PKR)
        """
        snapshot = self.get_latest_snapshot(portfolio_name)
        if snapshot:
            return snapshot.cash

        # If no snapshot, get initial cash from config
        config = self.get_config(portfolio_name)
        return config.initial_cash if config else 0.0

    def update_cash(self, portfolio_name: str, new_cash: float):
        """
        Update cash balance by saving a new snapshot

        Args:
            portfolio_name: Portfolio name
            new_cash: New cash balance
        """
        # Get current positions
        positions = self.get_all_positions(portfolio_name)

        # Create new snapshot
        snapshot = PortfolioSnapshot(
            portfolio_name=portfolio_name,
            cash=new_cash,
            positions=positions
        )
        snapshot.calculate_totals()

        # Save snapshot
        self.save_snapshot(snapshot)

    # ===== Helper Methods =====

    def get_portfolio_snapshot(self, portfolio_name: str, current_prices: Dict[str, float]) -> PortfolioSnapshot:
        """
        Get current portfolio snapshot with updated prices

        Args:
            portfolio_name: Portfolio name
            current_prices: Dictionary of symbol -> current price

        Returns:
            PortfolioSnapshot with updated market values
        """
        # Get cash balance
        cash = self.get_cash_balance(portfolio_name)

        # Get all positions
        positions = self.get_all_positions(portfolio_name)

        # Update positions with current prices
        for symbol, position in positions.items():
            if symbol in current_prices:
                position.update_market_value(current_prices[symbol])

        # Create snapshot
        snapshot = PortfolioSnapshot(
            portfolio_name=portfolio_name,
            cash=cash,
            positions=positions
        )
        snapshot.calculate_totals()

        return snapshot

    def initialize_portfolio(self, config: PortfolioConfig):
        """
        Initialize a new portfolio with starting cash

        Args:
            config: PortfolioConfig instance
        """
        # Save configuration
        self.save_config(config)

        # Create initial snapshot
        snapshot = PortfolioSnapshot(
            portfolio_name=config.name,
            cash=config.initial_cash
        )
        snapshot.calculate_totals()
        self.save_snapshot(snapshot)

        print(f"Initialized portfolio '{config.name}' with PKR {config.initial_cash:,.0f}")
