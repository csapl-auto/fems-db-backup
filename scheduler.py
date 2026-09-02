"""
scheduler.py - Pure Python Background Daemon Scheduler for FEMS Database Backups.
Features:
- Automatic VM Boot / Restart Recovery.
- Smart Date Check: Never duplicates if backup already exists for today.
- Flexible Scheduling: Supports Daily (every day) OR Weekly (selected day of week e.g. Monday, Friday, Sunday).
- Zero external cron dependencies.
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
import logging

from backup_engine import BackupEngine
from mailer import Mailer

logger = logging.getLogger("FEMSScheduler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DAYS_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6
}

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

    def has_backup_today(self):
        """Check if today's date folder already contains completed backup manifests."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        backup_root = self.engine.get_backup_dir()
        today_dir = os.path.join(backup_root, today_str)

        if os.path.exists(today_dir) and os.path.isdir(today_dir):
            summary_path = os.path.join(today_dir, "summary_manifest.json")
            if os.path.exists(summary_path):
                return True
            # Check if subfolders have dumps
            for sub in ("FEMS_Staging", "FEMS_PROD"):
                sub_path = os.path.join(today_dir, sub)
                if os.path.exists(sub_path) and len(os.listdir(sub_path)) > 0:
                    return True
        return False

    def is_scheduled_for_today(self, sched_cfg):
        """Check if today matches the configured frequency (Daily vs Weekly day)."""
        freq = sched_cfg.get("frequency", "daily").lower()
        if freq == "daily":
            return True

        if freq == "weekly":
            weekly_day = sched_cfg.get("weekly_day", "monday").lower()
            target_weekday = DAYS_MAP.get(weekly_day, 0)
            current_weekday = datetime.now().weekday()
            return current_weekday == target_weekday

        return True

    def calculate_next_run(self, sched_cfg):
        """Calculate human-readable next execution timestamp."""
        daily_time = sched_cfg.get("daily_time", "07:00")
        freq = sched_cfg.get("frequency", "daily").lower()
        weekly_day = sched_cfg.get("weekly_day", "monday").lower()

        now = datetime.now()
        try:
            target_hour, target_min = map(int, daily_time.split(":"))
        except Exception:
            target_hour, target_min = 7, 0

        target_time_today = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)

        if freq == "daily":
            if now < target_time_today:
                return f"Today at {daily_time}"
            else:
                return f"Tomorrow at {daily_time}"
        elif freq == "weekly":
            target_weekday = DAYS_MAP.get(weekly_day, 0)
            current_weekday = now.weekday()

            if current_weekday == target_weekday and now < target_time_today:
                return f"Today ({weekly_day.title()}) at {daily_time}"
            else:
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7
                next_date = now + timedelta(days=days_ahead)
                return f"Next {weekly_day.title()} ({next_date.strftime('%Y-%m-%d')}) at {daily_time}"

        return f"Daily at {daily_time}"

    def get_status(self):
        cfg = self._load_config()
        sched_cfg = cfg.get("schedule", {})
        next_run = self.calculate_next_run(sched_cfg)
        return {
            "enabled": sched_cfg.get("enabled", True),
            "frequency": sched_cfg.get("frequency", "daily"),
            "weekly_day": sched_cfg.get("weekly_day", "monday"),
            "daily_time": sched_cfg.get("daily_time", "07:00"),
            "timezone": sched_cfg.get("timezone", "Asia/Karachi"),
            "running": self.running,
            "has_backup_today": self.has_backup_today(),
            "last_run_date": self.last_run_date,
            "next_run_time": next_run
        }

    def _run_scheduled_job(self):
        """Execute scheduled backup and send email notification."""
        logger.info("⏰ Triggering scheduled automated backup snapshot...")
        try:
            summary = self.engine.run_backup(trigger_source="SCHEDULED_DAEMON", scope="all")
            cfg = self._load_config()
            smtp_cfg = cfg.get("smtp", {})
            mailer = Mailer(smtp_cfg)
            mailer.send_backup_report(summary)
            logger.info("Scheduled backup snapshot and report delivery completed.")
        except Exception as e:
            logger.error(f"Error during scheduled backup job execution: {e}")

    def _loop(self):
        """Scheduler main loop: checks state every 30 seconds."""
        logger.info("FEMS Background Backup Daemon loop active.")

        # On VM boot/daemon startup: sync last_run_date if today already has a backup
        if self.has_backup_today():
            self.last_run_date = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"Existing backup detected for today ({self.last_run_date}). No duplicate run needed.")

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

                # Update next run calculation
                self.next_run_time_str = self.calculate_next_run(sched_cfg)

                # Check if today is a scheduled day (daily or matching weekly_day)
                is_due_today = self.is_scheduled_for_today(sched_cfg)

                # Check if time matches and hasn't run today and doesn't already exist on disk
                if is_due_today and current_hm == daily_time and self.last_run_date != today_str:
                    if not self.has_backup_today():
                        self.last_run_date = today_str
                        logger.info(f"Scheduled time reached ({daily_time}). Triggering backup...")
                        worker = threading.Thread(target=self._run_scheduled_job, daemon=True)
                        worker.start()
                    else:
                        self.last_run_date = today_str
                        logger.info(f"Backup for today ({today_str}) is already present on disk. Skipping redundant run.")

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
