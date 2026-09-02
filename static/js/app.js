// FEMS Backup & Disaster Recovery Dashboard Client Logic

function updateClock() {
    const now = new Date();
    const clockEl = document.getElementById("currentTime");
    if (clockEl) {
        clockEl.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    }
}
setInterval(updateClock, 1000);
updateClock();

function showToast(message, type = "info") {
    const toast = document.getElementById("statusToast");
    const icon = document.getElementById("toastIcon");
    const msg = document.getElementById("toastMsg");

    toast.className = "rounded-xl p-4 border transition-all duration-300 flex items-center justify-between";

    if (type === "success") {
        toast.classList.add("bg-emerald-950/80", "border-emerald-500/30", "text-emerald-300");
        icon.className = "fa-solid fa-circle-check text-emerald-400";
    } else if (type === "error") {
        toast.classList.add("bg-rose-950/80", "border-rose-500/30", "text-rose-300");
        icon.className = "fa-solid fa-circle-exclamation text-rose-400";
    } else if (type === "loading") {
        toast.classList.add("bg-slate-900", "border-indigo-500/30", "text-indigo-300");
        icon.className = "fa-solid fa-circle-notch fa-spin text-indigo-400";
    } else {
        toast.classList.add("bg-slate-900", "border-slate-700", "text-slate-300");
        icon.className = "fa-solid fa-circle-info text-cyan-400";
    }

    msg.textContent = message;
    toast.classList.remove("hidden");
}

function closeToast() {
    const toast = document.getElementById("statusToast");
    toast.classList.add("hidden");
}

function openDrModal() {
    document.getElementById("drModal").classList.remove("hidden");
}

function closeDrModal() {
    document.getElementById("drModal").classList.add("hidden");
}

function toggleWeeklyDaySelector() {
    const freq = document.getElementById("cfgFrequency").value;
    const weeklyContainer = document.getElementById("weeklyDayContainer");
    if (freq === "weekly") {
        weeklyContainer.classList.remove("hidden");
    } else {
        weeklyContainer.classList.add("hidden");
    }
}

async function openSettingsModal() {
    try {
        const res = await fetch("/api/config");
        if (res.ok) {
            const cfg = await res.json();
            const smtp = cfg.smtp || {};
            const sched = cfg.schedule || {};
            const storage = cfg.storage || {};

            document.getElementById("cfgRecipient").value = smtp.recipient || "";
            document.getElementById("cfgCc").value = Array.isArray(smtp.cc) ? smtp.cc.join(", ") : (smtp.cc || "");
            document.getElementById("cfgFrequency").value = sched.frequency || "daily";
            document.getElementById("cfgWeeklyDay").value = sched.weekly_day || "monday";
            document.getElementById("cfgDailyTime").value = sched.daily_time || "07:00";
            document.getElementById("cfgRetentionDays").value = storage.retention_days || 30;

            toggleWeeklyDaySelector();
        }
    } catch (err) {
        console.error("Failed to load settings:", err);
    }
    document.getElementById("settingsModal").classList.remove("hidden");
}

function closeSettingsModal() {
    document.getElementById("settingsModal").classList.add("hidden");
}

async function saveSettings(event) {
    if (event) event.preventDefault();
    const btn = document.getElementById("btnSaveSettings");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...`;

    try {
        const recipient = document.getElementById("cfgRecipient").value.trim();
        const ccRaw = document.getElementById("cfgCc").value.trim();
        const frequency = document.getElementById("cfgFrequency").value;
        const weeklyDay = document.getElementById("cfgWeeklyDay").value;
        const dailyTime = document.getElementById("cfgDailyTime").value.trim() || "07:00";
        const retentionDays = parseInt(document.getElementById("cfgRetentionDays").value.trim()) || 30;

        const ccList = ccRaw ? ccRaw.split(",").map(s => s.trim()).filter(Boolean) : [];

        const payload = {
            smtp: {
                recipient: recipient,
                cc: ccList
            },
            schedule: {
                enabled: true,
                frequency: frequency,
                weekly_day: weeklyDay,
                daily_time: dailyTime,
                timezone: "Asia/Karachi"
            },
            storage: {
                retention_days: retentionDays
            }
        };

        const res = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            showToast("Settings successfully saved! Schedule & email preferences updated.", "success");
            closeSettingsModal();
            await loadStatus();
        } else {
            showToast(`Failed to save settings: ${data.message}`, "error");
        }
    } catch (err) {
        showToast(`Save settings error: ${err.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Save Settings`;
    }
}

function copyToClipboard(text, label = "Checksum") {
    navigator.clipboard.writeText(text).then(() => {
        showToast(`${label} copied to clipboard!`, "success");
        setTimeout(closeToast, 3000);
    }).catch(() => {
        prompt("Copy manually:", text);
    });
}

// --------------------------------------------------------------------------
// API Client Functions
// --------------------------------------------------------------------------

async function loadStatus() {
    try {
        const res = await fetch("/api/status");
        if (!res.ok) throw new Error("Failed to fetch status");
        const data = await res.json();

        // Disk space
        if (data.storage) {
            document.getElementById("diskFreeVal").textContent = data.storage.free_gb || "0";
            document.getElementById("backupRootText").textContent = data.storage.path || "/var/backups/FEMS_Backup";
        }

        // Retention
        document.getElementById("retentionDaysVal").textContent = data.retention_days || "30";
        document.getElementById("totalFoldersCount").textContent = data.total_date_folders || "0";

        // Schedule
        if (data.schedule) {
            document.getElementById("schedTimeVal").textContent = `${data.schedule.daily_time || "07:00"} PKT`;
            document.getElementById("nextSchedVal").textContent = `Next: ${data.schedule.next_run_time || "Scheduled"}`;
        }

        // Staging DB
        const staging = data.environments?.staging;
        if (staging) {
            document.getElementById("stagingDbInfo").textContent = `${staging.postgres?.name || "fems_staging"}`;
        }

        // Production DB
        const prod = data.environments?.production;
        if (prod) {
            document.getElementById("prodDbInfo").textContent = `${prod.postgres?.name || "fems_production"}`;
        }

    } catch (err) {
        console.error("Status error:", err);
    }
}

async function loadBackups() {
    const container = document.getElementById("backupListContainer");
    try {
        const res = await fetch("/api/backups");
        if (!res.ok) throw new Error("Failed to fetch backups");
        const data = await res.json();

        if (!data.backups || data.backups.length === 0) {
            container.innerHTML = `
                <div class="p-12 text-center text-slate-500">
                    <i class="fa-solid fa-folder-open text-3xl mb-3 text-slate-600"></i>
                    <p class="text-sm font-medium text-slate-400">No backup date folders found in repository.</p>
                    <p class="text-xs text-slate-500 mt-1">Click "Run All Backups" to generate initial snapshots.</p>
                </div>
            `;
            return;
        }

        let html = "";
        data.backups.forEach((b) => {
            const isSuccess = b.summary?.status === "SUCCESS";
            const statusBadge = isSuccess
                ? `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">SUCCESS</span>`
                : `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">${b.summary?.status || 'RECORDED'}</span>`;

            // Build Subfolders (FEMS_Staging and FEMS_PROD)
            let subfoldersHtml = "";
            b.subfolders.forEach(sub => {
                const isStaging = sub.folder_name.toLowerCase().includes("staging");
                const envIcon = isStaging ? "fa-vial text-amber-400" : "fa-shield-halved text-rose-400";
                const envLabel = isStaging ? "FEMS Staging" : "FEMS Production";

                let filesHtml = "";
                sub.files.forEach(f => {
                    const isPg = f.name.includes("postgres");
                    const isMongo = f.name.includes("mongo");
                    const isSum = f.name.includes("checksum") || f.name.includes("manifest");

                    let icon = "fa-file text-slate-400";
                    if (isPg) icon = "fa-database text-blue-400";
                    else if (isMongo) icon = "fa-leaf text-emerald-400";
                    else if (isSum) icon = "fa-file-shield text-slate-400";

                    filesHtml += `
                        <div class="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition text-xs">
                            <div class="flex items-center space-x-2.5 truncate mr-3">
                                <i class="fa-solid ${icon}"></i>
                                <span class="font-mono text-slate-200 truncate" title="${f.name}">${f.name}</span>
                            </div>
                            <div class="flex items-center space-x-3 shrink-0">
                                <span class="text-slate-400 font-mono">${f.size_mb} MB</span>
                                <a href="/api/backup/download?path=${encodeURIComponent(f.relative_path)}" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition flex items-center gap-1.5" title="Download">
                                    <i class="fa-solid fa-download text-emerald-400"></i>
                                    <span>Download</span>
                                </a>
                            </div>
                        </div>
                    `;
                });

                subfoldersHtml += `
                    <div class="bg-slate-900/90 rounded-xl border border-slate-800 p-4 space-y-3">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-2">
                                <i class="fa-solid ${envIcon}"></i>
                                <strong class="text-sm text-white font-semibold">${sub.folder_name}</strong>
                                <span class="text-xs text-slate-400">(${envLabel})</span>
                            </div>
                            <span class="text-xs font-mono text-slate-400">${sub.size_mb} MB total</span>
                        </div>
                        <div class="space-y-2">
                            ${filesHtml}
                        </div>
                    </div>
                `;
            });

            html += `
                <div class="p-5 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4 hover:border-slate-700 transition">
                    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
                        <div class="flex items-center space-x-3">
                            <div class="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-rose-400 font-bold text-xs font-mono">
                                <i class="fa-regular fa-calendar-days"></i>
                            </div>
                            <div>
                                <h3 class="text-base font-bold text-white font-mono flex items-center gap-2">
                                    ${b.date}
                                    ${statusBadge}
                                </h3>
                                <p class="text-xs text-slate-400">Total Archive Volume: <strong class="text-slate-200">${b.total_size_mb} MB</strong> &bull; ${b.subfolders.length} Environments</p>
                            </div>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        ${subfoldersHtml}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;

    } catch (err) {
        console.error("Backups list error:", err);
        container.innerHTML = `<div class="p-8 text-center text-rose-400 text-sm">Failed to load backups list.</div>`;
    }
}

async function triggerBackup(scope = "all") {
    const scopeLabel = scope === "all" ? "Both Environments (Staging & Production)" : scope.toUpperCase();
    showToast(`Executing snapshot for ${scopeLabel}... Please wait.`, "loading");

    try {
        const res = await fetch("/api/backup/trigger", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scope: scope, send_email: true })
        });
        const data = await res.json();
        if (data.status === "SUCCESS") {
            showToast(`Backup completed successfully in ${data.duration_sec}s! Email report sent.`, "success");
        } else {
            showToast(`Backup finished with warnings: ${data.status}`, "error");
        }
        await loadBackups();
        await loadStatus();
    } catch (err) {
        showToast(`Backup execution failed: ${err.message}`, "error");
    }
}

async function testSmtp() {
    showToast("Connecting to SMTP Relay (10.1.0.23:25) & sending test report...", "loading");
    try {
        const res = await fetch("/api/smtp/test", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Test email successfully delivered to itsupport@crescent.com.pk!", "success");
        } else {
            showToast(`SMTP test failed: ${data.message}`, "error");
        }
    } catch (err) {
        showToast(`SMTP Request error: ${err.message}`, "error");
    }
}

// Initial Load
document.addEventListener("DOMContentLoaded", () => {
    loadStatus();
    loadBackups();
    // Auto-refresh every 60 seconds
    setInterval(() => {
        loadStatus();
    }, 60000);
});
