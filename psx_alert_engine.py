"""
PSX Alert Engine
Alert generation, routing, deduplication, and persistence for position/swing trading
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from psx_risk_storage import RiskStorage, RiskAlert, AlertSeverity


class AlertEngine:
    """
    Alert generation and routing engine

    Features:
    - Multi-channel routing (console, file, email)
    - Deduplication with cooldown periods
    - Severity-based routing
    - EOD digest compilation
    - Morning news brief
    """

    def __init__(self,
                 storage: RiskStorage,
                 config: Optional[Dict] = None):
        """
        Initialize alert engine

        Args:
            storage: RiskStorage instance
            config: Alert configuration dict
        """
        self.storage = storage
        self.config = config or {}

        # Alert tracking for deduplication
        self.active_alerts: Dict[str, datetime] = {}

        # Cooldown periods (in days for position/swing trading)
        self.cooldown_days = {
            AlertSeverity.CRITICAL.value: 1,
            AlertSeverity.HIGH.value: 1,
            AlertSeverity.MEDIUM.value: 2,
            AlertSeverity.LOW.value: 3
        }

        # Alert file path
        self.alert_file_path = Path(self.config.get('file_path', 'alerts/risk_alerts.log'))
        self.alert_file_path.parent.mkdir(parents=True, exist_ok=True)

        # EOD digest buffer
        self.eod_digest_buffer: List[RiskAlert] = []

    def raise_alert(self, alert: RiskAlert) -> bool:
        """
        Raise a risk alert

        Args:
            alert: RiskAlert to raise

        Returns:
            True if alert was triggered, False if suppressed by deduplication
        """
        # Check deduplication
        if not self.should_trigger_alert(alert.symbol, alert.alert_type, alert.severity):
            return False

        # Save to database
        self.storage.save_alert(alert)

        # Route based on severity
        if self.config.get('eod_digest_mode', True):
            # Buffer for EOD digest
            self.eod_digest_buffer.append(alert)

            # Only send immediate for CRITICAL
            if alert.severity == AlertSeverity.CRITICAL.value:
                self._send_console(alert)
                self._send_file(alert)
        else:
            # Immediate routing
            if alert.severity == AlertSeverity.CRITICAL.value:
                self._send_console(alert)
                self._send_file(alert)
            elif alert.severity == AlertSeverity.HIGH.value:
                self._send_console(alert)
                self._send_file(alert)
            else:
                self._send_file(alert)

        # Mark as triggered
        key = f"{alert.symbol}_{alert.alert_type}"
        self.active_alerts[key] = datetime.now()

        return True

    def should_trigger_alert(self, symbol: str, alert_type: str, severity: str) -> bool:
        """
        Check if alert should fire (deduplication)

        Args:
            symbol: Stock symbol
            alert_type: Type of alert
            severity: Alert severity

        Returns:
            True if should trigger, False if in cooldown period
        """
        key = f"{symbol}_{alert_type}"

        if key not in self.active_alerts:
            return True

        last_triggered = self.active_alerts[key]
        cooldown_days = self.cooldown_days.get(severity, 1)

        if datetime.now() - last_triggered > timedelta(days=cooldown_days):
            return True

        return False

    def _send_console(self, alert: RiskAlert) -> None:
        """Send alert to console"""
        severity_icon = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }.get(alert.severity, "⚪")

        print(f"\n{severity_icon} [{alert.severity}] {alert.symbol} - {alert.alert_type}")
        print(f"   {alert.description}")
        print(f"   Risk Score: {alert.risk_score:.0f}/100")
        print(f"   Recommended: {alert.recommended_action}")
        print(f"   Time: {alert.triggered_at}")

    def _send_file(self, alert: RiskAlert) -> None:
        """Append alert to log file"""
        try:
            with open(self.alert_file_path, 'a') as f:
                f.write(f"{alert.triggered_at} | {alert.severity} | {alert.symbol} | "
                       f"{alert.alert_type} | {alert.description} | "
                       f"Risk: {alert.risk_score:.0f} | Action: {alert.recommended_action}\n")
        except Exception as e:
            print(f"Error writing alert to file: {str(e)}")

    def send_eod_digest(self) -> str:
        """
        Compile and send EOD digest email

        Returns:
            Email content as string
        """
        if not self.eod_digest_buffer:
            return "No alerts today"

        # Group by severity
        critical = [a for a in self.eod_digest_buffer if a.severity == AlertSeverity.CRITICAL.value]
        high = [a for a in self.eod_digest_buffer if a.severity == AlertSeverity.HIGH.value]
        medium = [a for a in self.eod_digest_buffer if a.severity == AlertSeverity.MEDIUM.value]
        low = [a for a in self.eod_digest_buffer if a.severity == AlertSeverity.LOW.value]

        # Build email
        email_content = f"""
PSX Risk Management - EOD Digest
{datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*60}

SUMMARY:
- Critical Alerts: {len(critical)}
- High Priority: {len(high)}
- Medium Priority: {len(medium)}
- Low Priority: {len(low)}

{'='*60}
"""

        if critical:
            email_content += "\n🔴 CRITICAL ALERTS (Immediate Action Required):\n" + "-"*60 + "\n"
            for alert in critical:
                email_content += f"\n{alert.symbol} - {alert.alert_type}\n"
                email_content += f"  {alert.description}\n"
                email_content += f"  Risk Score: {alert.risk_score:.0f}/100\n"
                email_content += f"  Action: {alert.recommended_action}\n"

        if high:
            email_content += "\n🟠 HIGH PRIORITY ALERTS:\n" + "-"*60 + "\n"
            for alert in high:
                email_content += f"\n{alert.symbol} - {alert.alert_type}\n"
                email_content += f"  {alert.description}\n"
                email_content += f"  Action: {alert.recommended_action}\n"

        if medium:
            email_content += "\n🟡 MEDIUM PRIORITY ALERTS:\n" + "-"*60 + "\n"
            for alert in medium[:5]:  # Top 5 only
                email_content += f"  {alert.symbol}: {alert.description}\n"
            if len(medium) > 5:
                email_content += f"  ... and {len(medium)-5} more\n"

        # Clear buffer
        self.eod_digest_buffer = []

        return email_content

    def send_morning_news_brief(self, overnight_news: List[Dict], watchlist: List[str]) -> str:
        """
        Compile morning news brief

        Args:
            overnight_news: List of news items from overnight
            watchlist: List of symbols on watchlist

        Returns:
            Email content as string
        """
        if not overnight_news:
            return ""  # Skip if no news

        # Filter for watchlist symbols
        relevant_news = [n for n in overnight_news if n.get('symbol') in watchlist]

        if not relevant_news:
            return ""  # Skip if no relevant news

        # Build brief
        brief = f"""
PSX Risk Management - Morning News Brief
{datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*60}

OVERNIGHT NEWS for Watchlist:
"""

        # Group by symbol
        by_symbol = {}
        for news in relevant_news:
            symbol = news.get('symbol')
            if symbol not in by_symbol:
                by_symbol[symbol] = []
            by_symbol[symbol].append(news)

        for symbol, news_items in sorted(by_symbol.items()):
            brief += f"\n{symbol}:\n"
            for news in news_items[:3]:  # Top 3 per symbol
                brief += f"  • {news.get('headline', 'No headline')}\n"
                if news.get('sentiment'):
                    brief += f"    Sentiment: {news.get('sentiment')}\n"

        brief += "\n" + "="*60 + "\n"
        brief += "Note: Review positions and consider gap risk at market open.\n"

        return brief

    def get_active_alerts(self) -> List[RiskAlert]:
        """Get all active (unresolved) alerts from storage"""
        return self.storage.get_active_alerts()

    def acknowledge_alert(self, alert_id: str) -> None:
        """Mark alert as acknowledged"""
        self.storage.acknowledge_alert(alert_id)

    def resolve_alert(self, alert_id: str) -> None:
        """Mark alert as resolved"""
        self.storage.resolve_alert(alert_id)

    def create_alert(self,
                     symbol: str,
                     alert_type: str,
                     severity: str,
                     description: str,
                     risk_score: float,
                     recommended_action: str) -> RiskAlert:
        """
        Helper to create a RiskAlert

        Args:
            symbol: Stock symbol
            alert_type: Type of alert
            severity: Alert severity
            description: Alert description
            risk_score: Risk score (0-100)
            recommended_action: Recommended action

        Returns:
            RiskAlert object
        """
        return RiskAlert(
            alert_id=str(uuid.uuid4()),
            symbol=symbol,
            alert_type=alert_type,
            severity=severity,
            triggered_at=datetime.now().isoformat(),
            description=description,
            risk_score=risk_score,
            recommended_action=recommended_action
        )
