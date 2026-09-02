# FEMS Database Backup & Disaster Recovery Subsystem

Enterprise-grade, automated database backup and disaster recovery management system for the **FEMS (Fire Extinguisher Management System)** across both **Staging** and **Production** environments.

![Port](https://img.shields.io/badge/port-5050-rose)
![Databases](https://img.shields.io/badge/database-PostgreSQL%2016%20%2B%20MongoDB%207-blue)
![Retention](https://img.shields.io/badge/retention-30%20Days-orange)
![Schedule](https://img.shields.io/badge/schedule-07%3A00%20AM%20Daily-indigo)

---

## 🌟 Key Features

- **Decoupled & Isolated**: Runs completely outside the main FEMS application directory (Port `5050`).
- **Dual-Environment Architecture**: Captures isolated snapshots for both **FEMS Staging** and **FEMS Production**.
- **Multi-Database Support**:
  - **PostgreSQL 16**: High-speed custom format snapshots (`pg_dump -Fc -Z 6`).
  - **MongoDB 7**: Compressed binary collections archives (`mongodump --archive --gzip`).
- **Date-Organized Folders**: Saves snapshots in separate folders per date (`/var/backups/FEMS_Backup/YYYY-MM-DD/`) containing subfolders `FEMS_Staging` and `FEMS_PROD`.
- **SHA-256 Checksum Validation**: Computes and stores cryptographic hashes for every dump file.
- **30-Day Retention Policy**: Automatically prunes backup archives older than 1 month.
- **HTML Email Notifications**: Sends dual-environment status reports and failure alerts to `itsupport@crescent.com.pk` via SMTP relay `10.1.0.23:25`.
- **Interactive Web Dashboard**: Monitor database connectivity, disk space usage, trigger on-demand backups (All / Staging / Prod), download archives, and view restoration commands.

---

## 📁 Storage & Directory Structure

```text
/var/backups/FEMS_Backup/
├── 2026-09-02/
│   ├── FEMS_Staging/
│   │   ├── postgres_fems_staging_20260902_070000.dump
│   │   ├── mongodb_fems_audit_staging_20260902_070000.archive
│   │   ├── checksums.sha256
│   │   └── manifest.json
│   ├── FEMS_PROD/
│   │   ├── postgres_fems_production_20260902_070000.dump
│   │   ├── mongodb_fems_audit_db_20260902_070000.archive
│   │   ├── checksums.sha256
│   │   └── manifest.json
│   └── summary_manifest.json
└── ... (Automated 30-Day Retention Horizon)
```

---

## 🛠️ Quick Installation on Server / VM

### 1. Clone & Run Service Installer
```bash
cd /opt/fems_backup_manager
sudo chmod +x install_service.sh
sudo ./install_service.sh
```

### 2. Allow Dashboard Port
```bash
sudo ufw allow 5050/tcp
```

### 3. Open Web Dashboard
Navigate to:
```text
http://<YOUR_SERVER_IP>:5050
```

---

## 🐳 Docker Deployment

```bash
docker compose -f docker-compose.backup.yml up -d
```

---

## 📧 SMTP Configuration

Default relay parameters configured in `config.json`:
- **Server**: `10.1.0.23`
- **Port**: `25`
- **Sender**: `alerts@crescent.com.pk`
- **Recipient**: `itsupport@crescent.com.pk`

---

## 📖 Disaster Recovery Runbook

For step-by-step instructions on restoring a corrupted database or deploying onto a fresh server, refer to [DR_RUNBOOK.md](DR_RUNBOOK.md).
