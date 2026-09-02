"""
scheduler.py - Pure Python Background Daemon Scheduler for FEMS Database Backups.
Triggers daily automated backup snapshots at scheduled time (e.g., 07:00 AM PKT) with zero external cron dependencies.
"""

import os
import json
import time
import threading
from datetime import datetime
import logging

from backup_engine import BackupEngine
from mailer import Mailer

logger = logging.getLogger("FEMSScheduler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class BackupScheduler:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.running = False
        self.thread = None
        self.last_run_date = None
        self.next_run_time_str = "Calculating..."
        self.engine = BackupEngine(config_path=self.config_path)

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading {self.config_path}: {e}")
        return {}

    def get_status(self):
        cfg = self._load_config()
        sched_cfg = cfg.get("schedule", {})
        return {
            "enabled": sched_cfg.get("enabled", True),
            "daily_time": sched_cfg.get("daily_time", "07:00"),
            "timezone": sched_cfg.get("timezone", "Asia/Karachi"),
            "running": self.running,
            "last_run_date": self.last_run_date,
            "next_run_time": self.next_run_time_str
        }

    def _run_scheduled_job(self):
        """Execute scheduled backup and send email notification."""
        logger.info("⏰ Starting scheduled automated backup job...")
        try:
            summary = self.engine.run_backup(trigger_source="SCHEDULED_DAEMON", scope="all")
            cfg = self._load_config()
            smtp_cfg = cfg.get("smtp", {})
            mailer = Mailer(smtp_cfg)
            mailer.send_backup_report(summary)
            logger.info("Scheduled backup job and notification dispatch completed successfully.")
        except Exception as e:
            logger.error(f"Error during scheduled backup job execution: {e}")

    def _loop(self):
        """Scheduler main loop: checks time every 30 seconds."""
        logger.info("Backup Scheduler background thread started.")
        while self.running:
            try:
                cfg = self._load_config()
                sched_cfg = cfg.get("schedule", {})
                if not sched_cfg.get("enabled", True):
                    time.sleep(30)
                    continue

                daily_time = sched_cfg.get("daily_time", "07:00")
                now = datetime.now()
                current_hm = now.strftime("%H:%M")
                today_str = now.strftime("%Y-%m-%d")

                # Format human readable next run time
                target_hour, target_min = map(int, daily_time.split(":"))
                self.next_run_time_str = f"Today at {daily_time}" if (now.hour < target_hour or (now.hour == target_hour and now.minute < target_min)) else f"Tomorrow at {daily_time}"

                # If current HH:MM matches scheduled daily_time and hasn't run today
                if current_hm == daily_time and self.last_run_date != today_str:
                    self.last_run_date = today_str
                    # Run in separate worker thread to avoid blocking scheduler tick
                    worker = threading.Thread(target=self._run_scheduled_job, daemon=True)
                    worker.start()

            except Exception as e:
                logger.error(f"Scheduler loop exception: {e}")

            time.sleep(30)

    def start(self):
        """Start scheduler in background thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            logger.info("FEMS Backup Scheduler started successfully.")

    def stop(self):
        """Stop scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            logger.info("FEMS Backup Scheduler stopped.")
