"""
Production Scheduler

Automated scheduling system for running daily analysis at specified times.
Uses APScheduler for reliable job scheduling.
"""

from datetime import datetime, time
import logging
from pathlib import Path
from typing import Optional

from production.config import ProductionConfig
from production.daily_analyzer import DailyAnalyzer


class ProductionScheduler:
    """
    Automated scheduler for daily analysis

    Features:
    - Configurable run time
    - Weekday-only execution (optional)
    - Automatic retry on failure
    - Logging and error tracking
    """

    def __init__(self, config: Optional[ProductionConfig] = None):
        """
        Args:
            config: Production configuration
        """
        self.config = config or ProductionConfig.load_from_file()
        self.analyzer = DailyAnalyzer(self.config)

        # Setup logging
        self._setup_logging()

        # Track last run
        self.last_run = None
        self.last_status = None

    def _setup_logging(self):
        """Setup logging to file and console"""

        log_dir = Path(self.config.storage.base_dir) / self.config.storage.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"scheduler_{datetime.now().strftime('%Y%m')}.log"

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger('ProductionScheduler')

    def run_scheduled_job(self):
        """
        Run the scheduled daily analysis job

        This is the main job that gets executed by the scheduler.
        """
        self.logger.info("="*80)
        self.logger.info("Starting scheduled daily analysis")
        self.logger.info("="*80)

        try:
            # Run analysis
            snapshots = self.analyzer.run_daily_analysis()

            # Update status
            self.last_run = datetime.now()
            self.last_status = 'success'

            self.logger.info(f"✅ Analysis completed successfully - {len(snapshots)} symbols analyzed")

        except Exception as e:
            self.logger.error(f"❌ Analysis failed: {str(e)}", exc_info=True)
            self.last_status = 'failed'
            self.last_run = datetime.now()

            # Retry logic
            if self.config.schedule.max_retries > 0:
                self._retry_with_backoff(e)

    def _retry_with_backoff(self, error: Exception):
        """Retry analysis with exponential backoff"""

        import time

        for attempt in range(self.config.schedule.max_retries):
            delay = self.config.schedule.retry_delay_seconds * (2 ** attempt)

            self.logger.info(f"Retry attempt {attempt + 1}/{self.config.schedule.max_retries} "
                           f"in {delay} seconds...")

            time.sleep(delay)

            try:
                snapshots = self.analyzer.run_daily_analysis()
                self.last_status = 'success_after_retry'
                self.logger.info(f"✅ Retry successful - {len(snapshots)} symbols analyzed")
                return

            except Exception as e:
                self.logger.error(f"Retry {attempt + 1} failed: {str(e)}")

        self.logger.error(f"❌ All retry attempts failed")

    def start_scheduler(self):
        """
        Start the scheduler

        Requires APScheduler library: pip install apscheduler
        """
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            self.logger.error("APScheduler not installed. Run: pip install apscheduler")
            print("\n⚠️  APScheduler not installed")
            print("Install with: pip install apscheduler")
            print("\nAlternatively, use manual scheduling with cron or Task Scheduler")
            return

        scheduler = BlockingScheduler()

        # Create cron trigger
        trigger = CronTrigger(
            day_of_week=','.join(str(d) for d in self.config.schedule.run_days),
            hour=self.config.schedule.run_hour,
            minute=self.config.schedule.run_minute
        )

        # Add job
        scheduler.add_job(
            self.run_scheduled_job,
            trigger=trigger,
            id='daily_analysis',
            name='Daily Technical Analysis',
            replace_existing=True
        )

        self.logger.info("="*80)
        self.logger.info("PRODUCTION SCHEDULER STARTED")
        self.logger.info("="*80)
        self.logger.info(f"Schedule: {self.config.schedule.run_hour:02d}:{self.config.schedule.run_minute:02d}")
        self.logger.info(f"Days: {self.config.schedule.run_days} (0=Monday, 6=Sunday)")
        self.logger.info(f"Next run: {scheduler.get_job('daily_analysis').next_run_time}")
        self.logger.info("="*80)

        print("\n📅 Scheduler running. Press Ctrl+C to exit.\n")

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Scheduler stopped by user")

    def run_once(self):
        """
        Run analysis once (for testing or manual execution)
        """
        self.logger.info("Running analysis once (manual execution)")
        self.run_scheduled_job()


def create_systemd_service():
    """
    Create a systemd service file for Linux

    Returns:
        String containing systemd service configuration
    """
    service_content = """[Unit]
Description=PSX Technical Analysis Scheduler
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Investment
ExecStart=/usr/bin/python3 -m production.scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    return service_content


def create_cron_entry():
    """
    Create a cron entry for scheduling

    Returns:
        String containing cron configuration
    """
    # Example: Run Monday-Friday at 6:00 PM
    cron_content = """# PSX Technical Analysis - Daily Run
0 18 * * 1-5 cd /path/to/Investment && /usr/bin/python3 -m production.run_daily_analysis
"""

    return cron_content


def create_windows_task():
    """
    Instructions for creating Windows Task Scheduler entry

    Returns:
        String with instructions
    """
    instructions = """
Windows Task Scheduler Setup:

1. Open Task Scheduler (taskschd.msc)

2. Create New Task:
   - Name: PSX Technical Analysis
   - Description: Automated daily technical analysis
   - Run whether user is logged on or not

3. Triggers:
   - New Trigger
   - Daily at 6:00 PM
   - Days: Monday through Friday

4. Actions:
   - New Action
   - Program: C:\\Python39\\python.exe
   - Arguments: -m production.run_daily_analysis
   - Start in: C:\\path\\to\\Investment

5. Conditions:
   - Start only if computer is on AC power: Unchecked
   - Wake computer to run: Checked (optional)

6. Settings:
   - Allow task to be run on demand: Checked
   - If task fails, restart every: 1 minute, 3 times
"""

    return instructions


if __name__ == "__main__":
    """Run scheduler or analysis"""

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run once (for testing)
        print("Running analysis once...")
        scheduler = ProductionScheduler()
        scheduler.run_once()

    elif len(sys.argv) > 1 and sys.argv[1] == '--systemd':
        # Print systemd service
        print("Copy this to /etc/systemd/system/psx-analysis.service:\n")
        print(create_systemd_service())
        print("\nThen run:")
        print("  sudo systemctl daemon-reload")
        print("  sudo systemctl enable psx-analysis")
        print("  sudo systemctl start psx-analysis")

    elif len(sys.argv) > 1 and sys.argv[1] == '--cron':
        # Print cron entry
        print("Add this to your crontab (crontab -e):\n")
        print(create_cron_entry())

    elif len(sys.argv) > 1 and sys.argv[1] == '--windows':
        # Print Windows instructions
        print(create_windows_task())

    else:
        # Start scheduler
        scheduler = ProductionScheduler()
        scheduler.start_scheduler()
