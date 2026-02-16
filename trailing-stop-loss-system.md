# Trailing Stop Loss System - Implementation Plan

## Overview

A comprehensive stop loss management system that:
- **Protects winners** - Locks in gains as price rises
- **Limits losses** - Exits losers before catastrophic declines
- **Adapts to volatility** - Wider stops for volatile stocks, tighter for stable ones
- **Respects technicals** - Uses support/resistance levels, not arbitrary percentages
- **Integrates with risk framework** - Adjusts stops based on fundamental risk scores

## Stop Loss Strategy Framework

### 1. Position Classification

Every position gets classified into one of four categories, each with different stop logic:

#### A. **Strong Winners** (Up >50%, Strong Fundamentals)
**Characteristics:**
- Unrealized gain >50%
- Company risk score <30 (strong fundamentals)
- Sector risk score >50 (favorable environment)
- Valuation risk <70 (not extremely overvalued)

**Stop Strategy:** **Trailing Stop** (15-20% from peak)
```python
Example: NATF
- Current price: PKR 408.94
- Peak price: PKR 408.94 (current)
- Trailing stop: PKR 347.60 (-15% from peak)
- As price rises, stop rises too (never falls)

If NATF goes to PKR 450:
- New trailing stop: PKR 382.50 (-15% from PKR 450)
```

**Rationale:** Let winners run, but protect against significant reversal

#### B. **Weak Winners** (Up >20%, Deteriorating Fundamentals)
**Characteristics:**
- Unrealized gain 20-50%
- Company risk score 30-60 (moderate issues)
- Sector risk deteriorating (score falling)
- Valuation risk 70-85 (getting expensive)

**Stop Strategy:** **Tight Trailing Stop** (10-12% from peak)
```python
Example: Hypothetical - BAFL if fundamentals weaken
- Current price: PKR 126
- Peak: PKR 130 (recent high)
- Tight trailing stop: PKR 114.40 (-12% from peak)
```

**Rationale:** Take profits on deteriorating situations before major reversal

#### C. **Quality on Dip** (Down <15%, Strong Fundamentals)
**Characteristics:**
- Unrealized loss 0% to -15%
- Company risk score <30 (strong fundamentals)
- Sector outlook stable/improving
- Reason for decline: Temporary (market selloff, not company-specific)

**Stop Strategy:** **Support-Based Stop** (below key technical level)
```python
Example: Quality stock temporarily down
- Current price: PKR 100 (down from PKR 115 entry)
- Key support: PKR 92 (200-day moving average)
- Stop loss: PKR 90 (-2% below support, -21% from entry)
```

**Rationale:** Give quality companies room to work through temporary weakness

#### D. **Broken Positions** (Down >5%, Weak Fundamentals)
**Characteristics:**
- Unrealized loss >5%
- Company risk score >60 (structural issues)
- Sector risk <35 (unfavorable environment)
- Fundamentals deteriorating (not temporary)

**Stop Strategy:** **Tight Fixed Stop** (8-10% max loss)
```python
Example: GAL
- Entry: PKR 555.33
- Current: PKR 495.99 (-10.68%)
- Stop loss: PKR 499.80 (-10% from entry)
- Status: STOP HIT - SELL IMMEDIATELY
```

**Rationale:** Cut losses quickly on fundamentally broken positions

### 2. Stop Loss Calculation Methods

#### Method A: **Percentage-Based Trailing Stop**

**Formula:**
```python
trailing_stop_price = peak_price × (1 - trailing_percentage)

# Update logic
if current_price > peak_price:
    peak_price = current_price  # Update peak
    trailing_stop = peak_price × (1 - trailing_pct)
else:
    # Stop level stays same or rises, never falls
    trailing_stop = max(previous_stop, peak_price × (1 - trailing_pct))
```

**Example - NATF:**
```
Day 1:  Price PKR 300 → Peak PKR 300 → Stop PKR 255 (-15%)
Day 10: Price PKR 350 → Peak PKR 350 → Stop PKR 297.50 (-15%)
Day 20: Price PKR 408 → Peak PKR 408 → Stop PKR 346.80 (-15%)
Day 25: Price PKR 390 → Peak still PKR 408 → Stop still PKR 346.80
Day 30: Price PKR 420 → Peak PKR 420 → Stop PKR 357 (-15%)
```

**Advantages:**
- Simple to implement
- Automatic, no manual intervention
- Locks in gains as price rises

**Disadvantages:**
- Ignores volatility (same % for all stocks)
- May be too tight for volatile stocks
- May be too wide for stable stocks

#### Method B: **ATR-Based Trailing Stop** (Volatility-Adjusted)

**Average True Range (ATR):**
Measures stock's volatility - higher ATR = more volatile

**Formula:**
```python
atr = calculate_atr(price_data, period=14)
trailing_stop = peak_price - (atr × atr_multiplier)

# Typical multiplier: 2-3x ATR
# Volatile stocks: 3x ATR (wider stop)
# Stable stocks: 2x ATR (tighter stop)
```

**Example - NATF (assuming ATR = PKR 25):**
```
Current price: PKR 408
ATR: PKR 25
Multiplier: 2.5x
Trailing stop: PKR 408 - (25 × 2.5) = PKR 345.50
```

**Example - Volatile stock (assuming ATR = PKR 45):**
```
Current price: PKR 500
ATR: PKR 45
Multiplier: 3x (wider for volatile stock)
Trailing stop: PKR 500 - (45 × 3) = PKR 365
```

**Advantages:**
- Adapts to stock's natural volatility
- Less likely to get stopped out on normal fluctuations
- More professional approach

**Disadvantages:**
- More complex to calculate
- Requires historical price data
- ATR changes over time

#### Method C: **Support-Based Stop**

Uses technical support levels (moving averages, previous lows, trendlines)

**Formula:**
```python
# Find key support level
support_candidates = [
    sma_200,           # 200-day moving average
    sma_50,            # 50-day moving average
    recent_low,        # Recent swing low
    fibonacci_level,   # Fibonacci retracement
    round_number       # Psychological level (e.g., PKR 100, 150, 200)
]

# Choose nearest support below current price
key_support = max([s for s in support_candidates if s < current_price])

# Set stop 2-3% below support (buffer for false breaks)
stop_loss = key_support × 0.97  # -3% below support
```

**Example - NATF:**
```
Current price: PKR 408
SMA(200): PKR 350
SMA(50): PKR 380
Recent swing low: PKR 365

Key support: PKR 380 (SMA 50)
Stop loss: PKR 380 × 0.97 = PKR 368.60
```

**Advantages:**
- Respects market structure
- Less arbitrary than fixed percentages
- Gives stock room to breathe

**Disadvantages:**
- Requires technical analysis
- Support levels can fail
- More subjective

#### Method D: **Chandelier Stop** (Hybrid)

Combines ATR with highest high (similar to trailing stop but volatility-adjusted)

**Formula:**
```python
chandelier_stop = highest_high_n_periods - (atr × multiplier)

# Typically use:
# - 22 periods (roughly 1 month of trading days)
# - 3x ATR multiplier
```

**Example:**
```
Highest high (last 22 days): PKR 420
ATR (14-day): PKR 25
Multiplier: 3x
Chandelier stop: PKR 420 - (25 × 3) = PKR 345
```

**Advantages:**
- Best of both worlds (trailing + volatility adjustment)
- Professional-grade approach
- Used by many institutional traders

### 3. Position-Specific Stop Configurations

#### For NATF (Strong Winner, Up 209%)

**Position Type:** Strong Winner
**Stop Method:** Chandelier Stop (trailing + ATR)

```python
config = StopLossConfig(
    symbol="NATF",
    method="chandelier",
    parameters={
        "lookback_period": 22,        # 1 month
        "atr_period": 14,
        "atr_multiplier": 3.0,        # Wide stop - let winner run
        "min_stop_distance_pct": 15   # Never closer than 15%
    }
)

# Current calculation:
highest_high_22d = PKR 408.94
atr_14d = PKR 22.50 (estimated)
chandelier_stop = 408.94 - (22.50 × 3) = PKR 341.44

# Alert settings
alert_buffer = 2%  # Alert when price within 2% of stop
alert_level = PKR 348.27
```

**Reasoning:**
- NATF is a strong winner with solid fundamentals
- Wide stop (3x ATR) gives room for normal volatility
- Won't get shaken out on minor pullbacks
- Locks in >200% gain if major reversal occurs

#### For GAL (Broken Position, Down 10.68%)

**Position Type:** Broken Position
**Stop Method:** Fixed Percentage (tight)

```python
config = StopLossConfig(
    symbol="GAL",
    method="fixed_percentage",
    parameters={
        "stop_percentage": 10,        # -10% from entry
        "already_triggered": True     # Currently at -10.68%
    }
)

# Current calculation:
entry_price = PKR 555.33
stop_loss = PKR 499.80 (-10%)
current_price = PKR 495.99
status = "TRIGGERED - SELL IMMEDIATELY"
```

**Reasoning:**
- GAL has structural issues (high debt, losing market share)
- Tight stop to prevent further losses
- Already triggered - exit now

#### For BAFL (Weak Winner, Up 130%)

**Position Type:** Weak Winner (cyclical peak)
**Stop Method:** Tight Trailing (percentage-based)

```python
config = StopLossConfig(
    symbol="BAFL",
    method="trailing_percentage",
    parameters={
        "trailing_percentage": 12,    # Tighter than strong winners
        "peak_price": 130.00,         # Recent high
        "min_stop_distance_pct": 10   # Can get as tight as 10%
    }
)

# Current calculation:
peak_price = PKR 130.00
trailing_stop = 130.00 × (1 - 0.12) = PKR 114.40
current_price = PKR 126.00
distance_to_stop = -9.05%
```

**Reasoning:**
- Banking cycle peaking, want to protect gains
- Tighter stop than NATF (12% vs 15%)
- Will exit if price breaks below PKR 114

#### For HTL (Near Breakeven, Monitor)

**Position Type:** Near breakeven, uncertain
**Stop Method:** Support-based

```python
config = StopLossConfig(
    symbol="HTL",
    method="support_based",
    parameters={
        "key_support": 52.00,         # SMA(50) or recent low
        "buffer_pct": 3,              # 3% below support
    }
)

# Current calculation:
current_price = PKR 54.25
key_support = PKR 52.00 (50-day MA)
stop_loss = 52.00 × 0.97 = PKR 50.44
distance_to_stop = -7.0%
```

**Reasoning:**
- Near entry price, no clear trend
- Use technical support as guide
- If breaks support, likely going lower

### 4. Database Schema

**Table: `stop_loss_levels`**
```sql
CREATE TABLE stop_loss_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_name TEXT NOT NULL,
    symbol TEXT NOT NULL,

    -- Position info
    quantity REAL NOT NULL,
    entry_price REAL NOT NULL,
    current_price REAL NOT NULL,
    unrealized_pl_pct REAL NOT NULL,

    -- Stop configuration
    stop_method TEXT NOT NULL,  -- 'trailing_pct', 'atr', 'support', 'chandelier', 'fixed'
    stop_price REAL NOT NULL,
    stop_distance_pct REAL NOT NULL,

    -- Trailing stop tracking
    peak_price REAL,
    peak_date TEXT,

    -- ATR-based parameters
    atr_value REAL,
    atr_multiplier REAL,

    -- Support-based parameters
    key_support REAL,

    -- Alert settings
    alert_enabled BOOLEAN DEFAULT 1,
    alert_buffer_pct REAL DEFAULT 2.0,
    alert_level REAL,
    alert_triggered BOOLEAN DEFAULT 0,
    alert_triggered_at TEXT,

    -- Status
    stop_status TEXT,  -- 'active', 'triggered', 'disabled'
    last_updated TEXT NOT NULL,

    UNIQUE(portfolio_name, symbol)
);

CREATE INDEX idx_stop_status ON stop_loss_levels(stop_status);
CREATE INDEX idx_alert_triggered ON stop_loss_levels(alert_enabled, alert_triggered);
```

**Table: `stop_loss_history`**
```sql
CREATE TABLE stop_loss_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_name TEXT NOT NULL,
    symbol TEXT NOT NULL,

    -- Event info
    event_type TEXT NOT NULL,  -- 'stop_triggered', 'stop_updated', 'peak_updated'
    event_date TEXT NOT NULL,

    -- Price at event
    price REAL NOT NULL,
    stop_level REAL NOT NULL,

    -- Action taken
    action_taken TEXT,  -- 'sold', 'alert_sent', 'stop_adjusted'
    notes TEXT
);

CREATE INDEX idx_stop_history_symbol ON stop_loss_history(symbol, event_date DESC);
```

### 5. Implementation

**File:** `psx_stop_loss_manager.py`

```python
"""
PSX Stop Loss Manager

Manages trailing stops, alerts, and automatic stop triggers
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np
import pandas as pd
from datetime import datetime


class StopMethod(Enum):
    """Stop loss calculation methods"""
    FIXED_PERCENTAGE = "fixed_percentage"
    TRAILING_PERCENTAGE = "trailing_percentage"
    ATR_BASED = "atr_based"
    SUPPORT_BASED = "support_based"
    CHANDELIER = "chandelier"


class StopStatus(Enum):
    """Stop loss status"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    DISABLED = "disabled"
    ALERT = "alert"


@dataclass
class StopLossConfig:
    """Configuration for stop loss calculation"""
    symbol: str
    method: StopMethod

    # Percentage-based
    stop_percentage: Optional[float] = None
    trailing_percentage: Optional[float] = None

    # ATR-based
    atr_period: Optional[int] = 14
    atr_multiplier: Optional[float] = 3.0

    # Chandelier
    lookback_period: Optional[int] = 22

    # Support-based
    key_support: Optional[float] = None
    buffer_pct: Optional[float] = 3.0

    # Alert settings
    alert_buffer_pct: float = 2.0

    # Constraints
    min_stop_distance_pct: Optional[float] = None
    max_stop_distance_pct: Optional[float] = None


@dataclass
class StopLossLevel:
    """Current stop loss level for a position"""
    symbol: str
    stop_method: str
    stop_price: float
    stop_distance_pct: float

    current_price: float
    entry_price: float
    peak_price: Optional[float]

    alert_level: float
    alert_triggered: bool
    stop_status: StopStatus

    # Calculation details
    atr_value: Optional[float] = None
    key_support: Optional[float] = None

    last_updated: str = ""
    notes: List[str] = None


class PSXStopLossManager:
    """
    Stop Loss Manager for PSX Portfolio

    Calculates, tracks, and monitors stop loss levels for all positions
    """

    def __init__(self, portfolio_store, price_store, db_path="portfolio_data/stop_losses.db"):
        self.portfolio_store = portfolio_store
        self.price_store = price_store
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize stop loss database"""
        # Create tables as shown in schema above
        pass

    def calculate_stop_loss(
        self,
        symbol: str,
        config: StopLossConfig,
        current_price: float,
        entry_price: float,
        quantity: float
    ) -> StopLossLevel:
        """
        Calculate stop loss level based on configuration
        """
        if config.method == StopMethod.FIXED_PERCENTAGE:
            return self._calculate_fixed_stop(symbol, config, current_price, entry_price)

        elif config.method == StopMethod.TRAILING_PERCENTAGE:
            return self._calculate_trailing_stop(symbol, config, current_price, entry_price)

        elif config.method == StopMethod.ATR_BASED:
            return self._calculate_atr_stop(symbol, config, current_price)

        elif config.method == StopMethod.SUPPORT_BASED:
            return self._calculate_support_stop(symbol, config, current_price)

        elif config.method == StopMethod.CHANDELIER:
            return self._calculate_chandelier_stop(symbol, config, current_price)

    def _calculate_fixed_stop(self, symbol, config, current_price, entry_price) -> StopLossLevel:
        """Fixed percentage stop from entry"""
        stop_price = entry_price * (1 - config.stop_percentage / 100)
        stop_distance_pct = ((current_price - stop_price) / current_price) * 100

        status = StopStatus.TRIGGERED if current_price <= stop_price else StopStatus.ACTIVE
        alert_level = stop_price * (1 + config.alert_buffer_pct / 100)
        alert_triggered = current_price <= alert_level

        return StopLossLevel(
            symbol=symbol,
            stop_method="fixed_percentage",
            stop_price=stop_price,
            stop_distance_pct=stop_distance_pct,
            current_price=current_price,
            entry_price=entry_price,
            peak_price=None,
            alert_level=alert_level,
            alert_triggered=alert_triggered,
            stop_status=status,
            notes=[f"Fixed stop at {config.stop_percentage}% below entry"]
        )

    def _calculate_trailing_stop(self, symbol, config, current_price, entry_price) -> StopLossLevel:
        """Trailing percentage stop from peak"""
        # Get historical peak
        peak_price = self._get_peak_price(symbol, current_price)

        # Calculate stop from peak
        stop_price = peak_price * (1 - config.trailing_percentage / 100)

        # Apply minimum distance constraint if specified
        if config.min_stop_distance_pct:
            min_stop = current_price * (1 - config.min_stop_distance_pct / 100)
            stop_price = min(stop_price, min_stop)

        stop_distance_pct = ((current_price - stop_price) / current_price) * 100

        status = StopStatus.TRIGGERED if current_price <= stop_price else StopStatus.ACTIVE
        alert_level = stop_price * (1 + config.alert_buffer_pct / 100)
        alert_triggered = current_price <= alert_level

        return StopLossLevel(
            symbol=symbol,
            stop_method="trailing_percentage",
            stop_price=stop_price,
            stop_distance_pct=stop_distance_pct,
            current_price=current_price,
            entry_price=entry_price,
            peak_price=peak_price,
            alert_level=alert_level,
            alert_triggered=alert_triggered,
            stop_status=status,
            notes=[
                f"Trailing stop {config.trailing_percentage}% from peak",
                f"Peak price: PKR {peak_price:.2f}"
            ]
        )

    def _calculate_atr_stop(self, symbol, config, current_price) -> StopLossLevel:
        """ATR-based stop (volatility adjusted)"""
        # Get price data
        df = self.price_store.get_prices(symbol, days=100)

        # Calculate ATR
        atr = self._calculate_atr(df, period=config.atr_period)

        # Get peak for trailing
        peak_price = self._get_peak_price(symbol, current_price)

        # Stop is peak minus (ATR × multiplier)
        stop_price = peak_price - (atr * config.atr_multiplier)
        stop_distance_pct = ((current_price - stop_price) / current_price) * 100

        status = StopStatus.TRIGGERED if current_price <= stop_price else StopStatus.ACTIVE
        alert_level = stop_price * (1 + config.alert_buffer_pct / 100)
        alert_triggered = current_price <= alert_level

        return StopLossLevel(
            symbol=symbol,
            stop_method="atr_based",
            stop_price=stop_price,
            stop_distance_pct=stop_distance_pct,
            current_price=current_price,
            entry_price=None,
            peak_price=peak_price,
            atr_value=atr,
            alert_level=alert_level,
            alert_triggered=alert_triggered,
            stop_status=status,
            notes=[
                f"ATR-based stop: {config.atr_multiplier}x ATR below peak",
                f"ATR({config.atr_period}): PKR {atr:.2f}",
                f"Peak: PKR {peak_price:.2f}"
            ]
        )

    def _calculate_chandelier_stop(self, symbol, config, current_price) -> StopLossLevel:
        """Chandelier stop (highest high - ATR × multiplier)"""
        # Get price data
        df = self.price_store.get_prices(symbol, days=100)

        # Calculate highest high over lookback period
        highest_high = df['High'].tail(config.lookback_period).max()

        # Calculate ATR
        atr = self._calculate_atr(df, period=config.atr_period)

        # Chandelier stop
        stop_price = highest_high - (atr * config.atr_multiplier)
        stop_distance_pct = ((current_price - stop_price) / current_price) * 100

        status = StopStatus.TRIGGERED if current_price <= stop_price else StopStatus.ACTIVE
        alert_level = stop_price * (1 + config.alert_buffer_pct / 100)
        alert_triggered = current_price <= alert_level

        return StopLossLevel(
            symbol=symbol,
            stop_method="chandelier",
            stop_price=stop_price,
            stop_distance_pct=stop_distance_pct,
            current_price=current_price,
            entry_price=None,
            peak_price=highest_high,
            atr_value=atr,
            alert_level=alert_level,
            alert_triggered=alert_triggered,
            stop_status=status,
            notes=[
                f"Chandelier: Highest({config.lookback_period}) - {config.atr_multiplier}×ATR",
                f"Highest high: PKR {highest_high:.2f}",
                f"ATR: PKR {atr:.2f}"
            ]
        )

    def _calculate_support_stop(self, symbol, config, current_price) -> StopLossLevel:
        """Support-based stop (below key technical level)"""
        # Get price data
        df = self.price_store.get_prices(symbol, days=250)

        # Find key support levels
        sma_200 = df['Close'].tail(200).mean()
        sma_50 = df['Close'].tail(50).mean()
        recent_low = df['Low'].tail(60).min()

        # Choose key support (closest below current price)
        supports = [s for s in [sma_200, sma_50, recent_low] if s < current_price]
        key_support = max(supports) if supports else current_price * 0.90

        # Stop below support with buffer
        stop_price = key_support * (1 - config.buffer_pct / 100)
        stop_distance_pct = ((current_price - stop_price) / current_price) * 100

        status = StopStatus.TRIGGERED if current_price <= stop_price else StopStatus.ACTIVE
        alert_level = key_support  # Alert at support, not stop
        alert_triggered = current_price <= alert_level

        return StopLossLevel(
            symbol=symbol,
            stop_method="support_based",
            stop_price=stop_price,
            stop_distance_pct=stop_distance_pct,
            current_price=current_price,
            entry_price=None,
            peak_price=None,
            key_support=key_support,
            alert_level=alert_level,
            alert_triggered=alert_triggered,
            stop_status=status,
            notes=[
                f"Stop {config.buffer_pct}% below support at PKR {key_support:.2f}",
                f"SMA(200): PKR {sma_200:.2f}",
                f"SMA(50): PKR {sma_50:.2f}"
            ]
        )

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high = df['High']
        low = df['Low']
        close = df['Close'].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.tail(period).mean()

        return float(atr)

    def _get_peak_price(self, symbol: str, current_price: float) -> float:
        """Get peak price for trailing stop (from database or current)"""
        # Query database for stored peak
        # If current > stored peak, update and return current
        # Otherwise return stored peak

        # Simplified version:
        return current_price  # In real implementation, track historical peak

    def update_all_stops(self, portfolio_name: str) -> Dict[str, StopLossLevel]:
        """
        Update stop losses for all positions in portfolio
        """
        positions = self.portfolio_store.get_all_positions(portfolio_name)
        config_map = self._load_stop_configs(portfolio_name)

        stop_levels = {}

        for symbol, position in positions.items():
            # Get current price
            df = self.price_store.get_prices(symbol, days=1)
            if df.empty:
                continue

            current_price = float(df['Close'].iloc[-1])

            # Get stop config for this symbol
            config = config_map.get(symbol)
            if not config:
                # Use default config based on position performance
                config = self._get_default_config(symbol, position)

            # Calculate stop level
            stop_level = self.calculate_stop_loss(
                symbol=symbol,
                config=config,
                current_price=current_price,
                entry_price=position.average_cost,
                quantity=position.quantity
            )

            stop_levels[symbol] = stop_level

            # Save to database
            self._save_stop_level(portfolio_name, stop_level)

            # Check for triggers/alerts
            if stop_level.stop_status == StopStatus.TRIGGERED:
                self._handle_stop_triggered(portfolio_name, symbol, stop_level)
            elif stop_level.alert_triggered:
                self._handle_alert_triggered(portfolio_name, symbol, stop_level)

        return stop_levels

    def _get_default_config(self, symbol: str, position) -> StopLossConfig:
        """
        Get default stop config based on position performance
        and risk assessment
        """
        unrealized_pl_pct = position.unrealized_pl_pct

        # Strong winner (up >50%)
        if unrealized_pl_pct > 50:
            return StopLossConfig(
                symbol=symbol,
                method=StopMethod.CHANDELIER,
                lookback_period=22,
                atr_period=14,
                atr_multiplier=3.0,
                min_stop_distance_pct=15
            )

        # Weak winner (up 20-50%)
        elif unrealized_pl_pct > 20:
            return StopLossConfig(
                symbol=symbol,
                method=StopMethod.TRAILING_PERCENTAGE,
                trailing_percentage=12,
                min_stop_distance_pct=10
            )

        # Near breakeven
        elif abs(unrealized_pl_pct) < 5:
            return StopLossConfig(
                symbol=symbol,
                method=StopMethod.SUPPORT_BASED,
                buffer_pct=3.0
            )

        # Loser (down >5%)
        else:
            return StopLossConfig(
                symbol=symbol,
                method=StopMethod.FIXED_PERCENTAGE,
                stop_percentage=10
            )

    def generate_stop_loss_report(self, portfolio_name: str) -> str:
        """Generate formatted report of all stop levels"""
        stop_levels = self.update_all_stops(portfolio_name)

        report = []
        report.append("="*100)
        report.append("🛡️  STOP LOSS MONITOR")
        report.append("="*100)

        # Group by status
        active = [s for s in stop_levels.values() if s.stop_status == StopStatus.ACTIVE]
        triggered = [s for s in stop_levels.values() if s.stop_status == StopStatus.TRIGGERED]
        alerts = [s for s in stop_levels.values() if s.alert_triggered]

        # Triggered stops (urgent)
        if triggered:
            report.append(f"\n🚨 STOPS TRIGGERED - IMMEDIATE ACTION REQUIRED ({len(triggered)})")
            report.append("-"*100)
            for stop in sorted(triggered, key=lambda x: x.stop_distance_pct):
                report.append(f"\n{stop.symbol} - SELL NOW")
                report.append(f"   Current: PKR {stop.current_price:.2f}")
                report.append(f"   Stop: PKR {stop.stop_price:.2f}")
                report.append(f"   Distance: {stop.stop_distance_pct:+.2f}% (BELOW STOP)")
                report.append(f"   Method: {stop.stop_method}")

        # Alert levels (warning)
        if alerts and not triggered:  # Only show if no triggered stops
            report.append(f"\n⚠️  STOPS ON ALERT - MONITOR CLOSELY ({len(alerts)})")
            report.append("-"*100)
            for stop in sorted(alerts, key=lambda x: x.stop_distance_pct):
                report.append(f"\n{stop.symbol}")
                report.append(f"   Current: PKR {stop.current_price:.2f}")
                report.append(f"   Alert: PKR {stop.alert_level:.2f}")
                report.append(f"   Stop: PKR {stop.stop_price:.2f}")
                report.append(f"   Distance to stop: {stop.stop_distance_pct:.2f}%")

        # Active stops (all positions)
        report.append(f"\n✅ ACTIVE STOPS ({len(active)})")
        report.append("-"*100)
        report.append(f"{'Symbol':<10} {'Current':<12} {'Stop':<12} {'Distance':<12} {'Method':<20}")
        report.append("-"*100)

        for stop in sorted(active, key=lambda x: x.stop_distance_pct):
            report.append(
                f"{stop.symbol:<10} "
                f"PKR {stop.current_price:>8.2f}  "
                f"PKR {stop.stop_price:>8.2f}  "
                f"{stop.stop_distance_pct:>9.2f}%   "
                f"{stop.stop_method:<20}"
            )

        report.append("\n" + "="*100)

        return "\n".join(report)


# Helper function for integration
def apply_stop_loss_recommendations(portfolio_name: str, risk_based_manager):
    """
    Apply stop loss logic to risk-based portfolio decisions
    """
    stop_manager = PSXStopLossManager(
        portfolio_store=risk_based_manager.portfolio_store,
        price_store=risk_based_manager.price_store
    )

    stop_levels = stop_manager.update_all_stops(portfolio_name)

    # Generate report
    report = stop_manager.generate_stop_loss_report(portfolio_name)
    print(report)

    return stop_levels
```

### 6. Integration with Risk-Based Portfolio Manager

**File:** `psx_risk_based_portfolio_manager.py` (enhancement)

```python
class RiskBasedPortfolioManager(PSXPortfolioManager):
    """Enhanced with stop loss management"""

    def __init__(self, portfolio_store, config, stop_loss_manager):
        super().__init__(portfolio_store, config)
        self.stop_manager = stop_loss_manager

    def _generate_decision_with_stops(self, signal, position, ...):
        """Override to include stop loss logic"""

        # Calculate stop loss level
        stop_level = self.stop_manager.calculate_stop_loss(...)

        # If stop triggered, override other logic
        if stop_level.stop_status == StopStatus.TRIGGERED:
            return TradeDecision(
                action=ActionType.SELL,
                quantity=position.quantity,
                reasoning=[
                    f"🚨 STOP LOSS TRIGGERED",
                    f"Stop method: {stop_level.stop_method}",
                    f"Stop price: PKR {stop_level.stop_price:.2f}",
                    f"Current price: PKR {stop_level.current_price:.2f}",
                    "Exit immediately to limit losses"
                ]
            )

        # Otherwise, use risk-based logic but include stop info
        decision = self._generate_decision(signal, position, ...)

        # Add stop loss info to reasoning
        decision.reasoning.append(
            f"Stop loss: PKR {stop_level.stop_price:.2f} "
            f"({stop_level.stop_distance_pct:.1f}% below current)"
        )

        return decision
```

### 7. Configuration for Your Portfolio

**`stop_loss_config.json`**

```json
{
  "portfolio_name": "default",
  "positions": {
    "NATF": {
      "method": "chandelier",
      "lookback_period": 22,
      "atr_period": 14,
      "atr_multiplier": 3.0,
      "min_stop_distance_pct": 15,
      "notes": "Strong winner - let run with wide stop"
    },
    "BAFL": {
      "method": "trailing_percentage",
      "trailing_percentage": 12,
      "min_stop_distance_pct": 10,
      "notes": "Weak winner - tighter stop, cycle peaking"
    },
    "ICL": {
      "method": "trailing_percentage",
      "trailing_percentage": 15,
      "notes": "Strong winner - standard trailing stop"
    },
    "ATLH": {
      "method": "chandelier",
      "atr_multiplier": 2.5,
      "notes": "Strong winner - slightly tighter than NATF"
    },
    "GAL": {
      "method": "fixed_percentage",
      "stop_percentage": 10,
      "notes": "Broken position - tight fixed stop (ALREADY TRIGGERED)"
    },
    "PAEL": {
      "method": "fixed_percentage",
      "stop_percentage": 10,
      "notes": "Weak position - tight stop to prevent further loss"
    },
    "HTL": {
      "method": "support_based",
      "buffer_pct": 3,
      "notes": "Near breakeven - use technical support"
    },
    "PNSC": {
      "method": "support_based",
      "buffer_pct": 3,
      "notes": "Near breakeven - use technical support"
    }
  },
  "defaults": {
    "strong_winner": {
      "method": "chandelier",
      "atr_multiplier": 3.0,
      "min_stop_distance_pct": 15
    },
    "weak_winner": {
      "method": "trailing_percentage",
      "trailing_percentage": 12
    },
    "loser": {
      "method": "fixed_percentage",
      "stop_percentage": 10
    },
    "breakeven": {
      "method": "support_based",
      "buffer_pct": 3
    }
  }
}
```

### 8. Example Output

```
====================================================================================================
🛡️  STOP LOSS MONITOR
====================================================================================================

🚨 STOPS TRIGGERED - IMMEDIATE ACTION REQUIRED (2)
----------------------------------------------------------------------------------------------------

GAL - SELL NOW
   Current: PKR 495.99
   Stop: PKR 499.80
   Distance: -0.76% (BELOW STOP)
   Method: fixed_percentage
   Notes: Broken position - exit to prevent further loss

PAEL - SELL NOW
   Current: PKR 53.98
   Stop: PKR 52.81
   Distance: -2.17% (BELOW STOP)
   Method: fixed_percentage
   Notes: High debt, fundamentals weakening

⚠️  STOPS ON ALERT - MONITOR CLOSELY (1)
----------------------------------------------------------------------------------------------------

HTL
   Current: PKR 54.25
   Alert: PKR 52.00 (Support level)
   Stop: PKR 50.44
   Distance to stop: 7.02%
   Notes: Watching support at PKR 52 (50-day MA)

✅ ACTIVE STOPS (13)
----------------------------------------------------------------------------------------------------
Symbol     Current      Stop         Distance     Method
----------------------------------------------------------------------------------------------------
NATF       PKR 408.94  PKR 341.44      16.52%   chandelier
ICL        PKR 151.50  PKR 128.78      15.00%   trailing_percentage
ATLH       PKR 1781.02 PKR 1514.87     14.94%   chandelier
BAFL       PKR 126.00  PKR 114.40       9.21%   trailing_percentage
AGP        PKR 238.08  PKR 214.27       10.00%  trailing_percentage
HALEON     PKR 914.00  PKR 776.90       15.00%  trailing_percentage
BFBIO      PKR 164.00  PKR 139.40       15.00%  trailing_percentage
SAZEW      PKR 2333.98 PKR 2043.48      12.44%  trailing_percentage
PAKT       PKR 1595.00 PKR 1435.50      10.00%  trailing_percentage
BFAGRO     PKR 39.40   PKR 33.49        15.00%  trailing_percentage
BBFL       PKR 49.00   PKR 44.81         8.55%  support_based
HINOON     PKR 1021.12 PKR 932.70        8.66%  support_based
PNSC       PKR 619.00  PKR 571.25        7.71%  support_based

====================================================================================================
```

### 9. Daily Monitoring Workflow

**Morning Check (Before Market Open):**
```bash
python monitor_stops.py --portfolio default --send-alerts
```

Output:
```
Good morning! Stop loss status:
- 2 TRIGGERED: GAL, PAEL → SELL AT MARKET OPEN
- 1 ON ALERT: HTL → Watch closely, may trigger today
- 13 ACTIVE: All within normal range
```

**End of Day Update:**
```bash
python update_stops.py --portfolio default
```

Updates all stop levels based on:
- New peak prices (update trailing stops)
- Latest ATR values (update volatility stops)
- New support levels (update technical stops)

### 10. Implementation Timeline

**Week 1:** Core stop loss calculation methods
**Week 2:** Database schema and tracking
**Week 3:** Integration with portfolio manager
**Week 4:** Alerting and monitoring system
**Week 5:** Backtesting and calibration
**Week 6:** Production deployment

## Summary

This trailing stop loss system:

✅ **Protects winners** - NATF locked at minimum +183% even if reverses
✅ **Limits losses** - GAL auto-exits at -10%, not -30%
✅ **Adapts to volatility** - Wide stops for volatile stocks, tight for stable
✅ **Uses technical levels** - Respects support/resistance, not arbitrary
✅ **Integrates with risk** - Tighter stops for risky positions
✅ **Automates monitoring** - Daily alerts, no manual checking

Combined with the risk-based framework, you now have a comprehensive system that:
1. Evaluates economic/sector/company/valuation risks
2. Makes hold/sell decisions based on fundamentals
3. Sets appropriate stop losses to protect capital
4. Monitors positions automatically
5. Alerts you when action needed

Would you like me to start implementing any specific component?
