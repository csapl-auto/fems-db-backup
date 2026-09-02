# 🚒 FEMS Disaster Recovery & Database Restoration Runbook (SOP)

**Standard Operating Procedure (SOP) for Crescent Steel FEMS Database Restoration**  
**Classification**: High-Priority Business Continuity & Disaster Recovery (BCDR)  
**Database Engines**: PostgreSQL 16 (Relational DB) & MongoDB 7 (Audit Logs)  
**Environments Managed**: FEMS Staging & FEMS Production  

---

## 📌 1. Overview & Directory Hierarchy

The FEMS Backup Subsystem saves snapshots outside the application code directory in an external location on the host VM:
`/var/backups/FEMS_Backup/` (or `./FEMS_Backup` fallback).

The structure inside `FEMS_Backup` is organized strictly by Date (`YYYY-MM-DD/`) and isolated Environment folders (`FEMS_Staging` & `FEMS_PROD`):

```text
/var/backups/FEMS_Backup/
└── 2026-09-02/
    ├── FEMS_Staging/
    │   ├── postgres_fems_staging_20260902_070000.dump      # PostgreSQL custom compressed (-Fc)
    │   ├── mongodb_fems_audit_staging_20260902_070000.archive # MongoDB gzip archive
    │   ├── checksums.sha256                               # SHA-256 validation hashes
    │   └── manifest.json                                  # Metadata manifest
    ├── FEMS_PROD/
    │   ├── postgres_fems_production_20260902_070000.dump   # PostgreSQL custom compressed (-Fc)
    │   ├── mongodb_fems_audit_db_20260902_070000.archive    # MongoDB gzip archive
    │   ├── checksums.sha256                               # SHA-256 validation hashes
    │   └── manifest.json                                  # Metadata manifest
    └── summary_manifest.json                              # Day-level summary report
```

---

## 🔒 2. Pre-Restoration Verification (Integrity & Checksum)

Before applying any restoration dump, verify the SHA-256 integrity hash:

```bash
cd /var/backups/FEMS_Backup/2026-09-02/FEMS_PROD/

# Verify checksums
sha256sum -c checksums.sha256
```

Expected Output:
```text
postgres_fems_production_20260902_070000.dump: OK
mongodb_fems_audit_db_20260902_070000.archive: OK
```

---

## 🛠️ 3. Scenario A: Restoring FEMS Production Database

### Step 1: Temporarily Stop Application Container (Optional but Recommended)
To prevent inbound writes during restoration:
```bash
docker stop fems-production
```

### Step 2: Restore PostgreSQL 16 (`fems_production`)
Execute `pg_restore` with `--clean --if-exists` to drop existing objects before rebuilding schemas:

**Via Docker Exec (Recommended):**
```bash
cat /var/backups/FEMS_Backup/YYYY-MM-DD/FEMS_PROD/postgres_fems_production_*.dump | \
docker exec -i fems-production pg_restore -U fems_admin -d fems_production --clean --if-exists --no-owner
```

**Direct Host Execution (Native):**
```bash
PGPASSWORD="SecurePassword123" pg_restore -h 127.0.0.1 -p 5432 -U fems_admin -d fems_production --clean --if-exists \
/var/backups/FEMS_Backup/YYYY-MM-DD/FEMS_PROD/postgres_fems_production_*.dump
```

### Step 3: Restore MongoDB 7 (`fems_audit_db`)
Execute `mongorestore` with `--gzip --drop`:

**Via Host / Docker Exec:**
```bash
mongorestore --uri="mongodb://fems_logger:SecureLogsPwd456@127.0.0.1:27017/fems_audit_db?authSource=admin" \
--archive=/var/backups/FEMS_Backup/YYYY-MM-DD/FEMS_PROD/mongodb_fems_audit_db_*.archive --gzip --drop
```

### Step 4: Restart & Verify Application
```bash
docker start fems-production
curl -I http://10.11.0.41:4000/api/health
```

---

## 🧪 4. Scenario B: Restoring FEMS Staging Database

### Step 1: Restore PostgreSQL 16 (`fems_staging`)
```bash
cat /var/backups/FEMS_Backup/YYYY-MM-DD/FEMS_Staging/postgres_fems_staging_*.dump | \
docker exec -i fems-staging pg_restore -U fems_admin -d fems_staging --clean --if-exists --no-owner
```

### Step 2: Restore MongoDB 7 (`fems_audit_staging_db`)
```bash
mongorestore --uri="mongodb://fems_logger:SecureLogsPwd456@127.0.0.1:27017/fems_audit_staging_db?authSource=admin" \
--archive=/var/backups/FEMS_Backup/YYYY-MM-DD/FEMS_Staging/mongodb_fems_audit_staging_*.archive --gzip --drop
```

---

## ⚡ 5. Scenario C: Cloning Production Data into Staging

To refresh Staging with the latest Production snapshot for testing:

```bash
# 1. Restore Production Postgres dump into Staging database
cat /var/backups/FEMS_Backup/YYYY-MM-DD/FEMS_PROD/postgres_fems_production_*.dump | \
docker exec -i fems-staging pg_restore -U fems_admin -d fems_staging --clean --if-exists --no-owner

# 2. Restore Production Mongo archive into Staging Mongo database
mongorestore --uri="mongodb://fems_logger:SecureLogsPwd456@127.0.0.1:27017/fems_audit_staging_db?authSource=admin" \
--nsFrom="fems_audit_db.*" --nsTo="fems_audit_staging_db.*" \
--archive=/var/backups/FEMS_Backup/YYYY-MM-DD/FEMS_PROD/mongodb_fems_audit_db_*.archive --gzip --drop
```

---

## 🚨 6. Scenario D: Complete Bare-Metal VM Disaster Recovery

If the entire VM server fails and a new VM is provisioned:

1. **Install Prerequisites on New Host**:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose postgresql-client mongodb-database-tools
   ```
2. **Transfer Backup Directory**:
   Copy `/var/backups/FEMS_Backup/` from off-site storage / cold storage to `/var/backups/FEMS_Backup/` on the new VM.
3. **Deploy FEMS Containers**:
   ```bash
   cd /home/dockerhub1/fems
   docker compose up -d
   ```
4. **Deploy FEMS Backup Manager Subsystem**:
   ```bash
   cd /opt/fems_backup_manager
   sudo ./install_service.sh
   ```
5. **Run Restoration Steps** outlined in **Section 3**.

---

## 📞 7. Escalation & Contact Directory

- **Database Administrator**: DBA Team (`itsupport@crescent.com.pk`)
- **System Relay**: `10.1.0.23:25`
- **Dashboard Portal**: `http://10.11.0.41:5050`
