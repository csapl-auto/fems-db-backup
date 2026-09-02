"""
mailer.py - High-Reliability SMTP Notification Engine for FEMS Database Backups.
Supports dual-environment summary reports (Staging & Production), Outlook-compatible HTML templating, and instant failure alerts.
"""

import smtplib
import os
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from datetime import datetime
import logging

logger = logging.getLogger("FEMSBackupMailer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class Mailer:
    def __init__(self, smtp_config):
        self.config = smtp_config
        self.server = smtp_config.get("server", "10.1.0.23")
        self.port = int(smtp_config.get("port", 25))
        self.use_tls = smtp_config.get("use_tls", False)
        self.use_ssl = smtp_config.get("use_ssl", False)
        self.username = smtp_config.get("username", "")
        self.password = smtp_config.get("password", "")
        self.sender = smtp_config.get("sender", "alerts@crescent.com.pk")
        self.sender_name = smtp_config.get("sender_name", "FEMS Database Backup System")
        self.recipient = smtp_config.get("recipient", "itsupport@crescent.com.pk")
        self.cc = smtp_config.get("cc", [])

    def _create_connection(self):
        """Create and connect to SMTP server with proper timeout."""
        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.server, self.port, timeout=30)
        else:
            server = smtplib.SMTP(self.server, self.port, timeout=30)
            if self.use_tls:
                server.starttls()

        if self.username and self.password:
            server.login(self.username, self.password)

        return server

    def test_connection(self):
        """Test SMTP server connectivity."""
        try:
            with self._create_connection() as s:
                s.noop()
            return True, f"Successfully connected to SMTP server {self.server}:{self.port}"
        except Exception as e:
            return False, f"SMTP Connection Failed: {str(e)}"

    def send_backup_report(self, backup_summary):
        """
        Send formatted, Outlook-friendly HTML dual-environment backup report.
        """
        if not self.config.get("enabled", True):
            logger.info("SMTP is disabled in configuration. Skipping email delivery.")
            return True, "Email skipped (disabled)"

        is_success = backup_summary.get("status") == "SUCCESS"
        date_folder = backup_summary.get("date_folder", "/var/backups/FEMS_Backup")
        duration_sec = backup_summary.get("duration_sec", 1.25)
        folder_size_mb = backup_summary.get("date_folder_size_mb", 0.0)
        retention_days = backup_summary.get("retention_days", 30)
        free_space_gb = backup_summary.get("storage_free_gb", 0)
        hostname = backup_summary.get("hostname", socket.gethostname())
        envs = backup_summary.get("environments", {})

        subject = f"{'✅ [SUCCESS]' if is_success else '🚨 [ALERT]'} FEMS Database Backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        to_addrs = [r.strip() for r in self.recipient.split(",") if r.strip()]
        cc_addrs = self.cc if isinstance(self.cc, list) else [r.strip() for r in self.cc.split(",") if r.strip()]
        all_recipients = to_addrs + cc_addrs

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.sender}>"
        msg["To"] = ", ".join(to_addrs)
        if cc_addrs:
            msg["Cc"] = ", ".join(cc_addrs)
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        header_bg = "#0f172a"
        badge_bg = "#059669" if is_success else "#DC2626"
        badge_text = "BACKUPS COMPLETED" if is_success else "BACKUP FAILED"

        # Build Environment Sections
        env_sections_html = ""
        for env_key, env_data in envs.items():
            env_name = env_data.get("environment_name", env_key.title())
            env_folder = env_data.get("folder_name", f"FEMS_{env_key.title()}")
            env_status = env_data.get("status", "SUCCESS")
            env_badge_color = "#059669" if env_status == "SUCCESS" else "#DC2626"

            pg = env_data.get("postgres", {})
            mongo = env_data.get("mongodb", {})

            pg_sha = pg.get("sha256", "")
            pg_sha_short = f"{pg_sha[:20]}..." if len(pg_sha) > 20 else pg_sha

            mongo_sha = mongo.get("sha256", "")
            mongo_sha_short = f"{mongo_sha[:20]}..." if len(mongo_sha) > 20 else mongo_sha

            env_sections_html += f"""
            <div style="margin-top: 14px; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; background-color: #ffffff;">
                <div style="background-color: #f8fafc; padding: 8px 12px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #0f172a; font-size: 13px; font-weight: bold;">🗂️ {env_name} ({env_folder})</span>
                    <span style="background-color: {env_badge_color}; color: #ffffff; padding: 2px 7px; border-radius: 10px; font-size: 10px; font-weight: bold;">{env_status}</span>
                </div>
                <table width="100%" cellpadding="6" cellspacing="0" style="font-size: 12px; color: #334155; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td width="30%" style="padding: 7px 12px; font-weight: bold; background-color: #fcfcfc;">PostgreSQL (16):</td>
                        <td style="padding: 7px 12px;">
                            <strong>{pg.get('database', 'fems_staging')}</strong> &bull; {pg.get('size_mb', 0)} MB<br>
                            <span style="font-size: 10px; color: #64748b; font-family: monospace;">SHA256: {pg_sha_short}</span>
                        </td>
                    </tr>
                    <tr>
                        <td width="30%" style="padding: 7px 12px; font-weight: bold; background-color: #fcfcfc;">MongoDB (7 Audit):</td>
                        <td style="padding: 7px 12px;">
                            <strong>{mongo.get('database', 'fems_audit_db')}</strong> &bull; {mongo.get('size_mb', 0)} MB<br>
                            <span style="font-size: 10px; color: #64748b; font-family: monospace;">SHA256: {mongo_sha_short}</span>
                        </td>
                    </tr>
                </table>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>FEMS Database Backup</title>
        </head>
        <body style="font-family: Arial, Helvetica, sans-serif; background-color: #f1f5f9; margin: 0; padding: 12px; color: #1e293b;">
            <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 540px; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #cbd5e1; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <!-- Header -->
                <tr>
                    <td style="background-color: {header_bg}; padding: 16px 20px;">
                        <table width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr>
                                <td>
                                    <h1 style="color: #ffffff; margin: 0; font-size: 17px; font-weight: bold; letter-spacing: -0.5px;">
                                        FEMS Database Backup
                                    </h1>
                                </td>
                                <td align="right" style="vertical-align: middle;">
                                    <span style="background-color: {badge_bg}; color: #ffffff; padding: 4px 10px; border-radius: 20px; font-size: 10px; font-weight: bold; text-transform: uppercase;">
                                        {badge_text}
                                    </span>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>

                <!-- Content -->
                <tr>
                    <td style="padding: 16px 20px;">
                        <!-- Metric Summary Table -->
                        <table width="100%" cellpadding="6" cellspacing="0" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 12px; margin-bottom: 8px;">
                            <tr>
                                <td width="38%" style="color: #64748b; padding: 5px 12px;">Execution Time:</td>
                                <td style="color: #0f172a; font-weight: bold; padding: 5px 12px;">{duration_sec} seconds</td>
                            </tr>
                            <tr>
                                <td width="38%" style="color: #64748b; padding: 5px 12px;">Backup Folder Size:</td>
                                <td style="color: #0f172a; font-weight: bold; padding: 5px 12px;">{folder_size_mb} MB</td>
                            </tr>
                            <tr>
                                <td style="color: #64748b; padding: 5px 12px;">Retention Horizon:</td>
                                <td style="color: #0f172a; font-weight: bold; padding: 5px 12px;">{retention_days} Days</td>
                            </tr>
                            <tr>
                                <td style="color: #64748b; padding: 5px 12px;">Storage Remaining:</td>
                                <td style="color: #0f172a; font-weight: bold; padding: 5px 12px;">{free_space_gb} GB Free</td>
                            </tr>
                            <tr>
                                <td style="color: #64748b; padding: 5px 12px;">Storage Path:</td>
                                <td style="color: #0f172a; font-family: monospace; font-size: 11px; padding: 5px 12px;">{date_folder}</td>
                            </tr>
                        </table>

                        <!-- Environments Breakdown -->
                        {env_sections_html}
                    </td>
                </tr>

                <!-- Footer -->
                <tr>
                    <td style="background-color: #f8fafc; padding: 12px 20px; border-top: 1px solid #e2e8f0; text-align: center;">
                        <p style="margin: 0; font-size: 11px; color: #64748b;">
                            FEMS Backup System, {hostname}
                        </p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        try:
            with self._create_connection() as server:
                server.sendmail(self.sender, all_recipients, msg.as_string())
            logger.info(f"Backup report email successfully sent to {all_recipients}")
            return True, "Email sent successfully"
        except Exception as e:
            logger.error(f"Failed to send backup report email: {e}")
            return False, str(e)
