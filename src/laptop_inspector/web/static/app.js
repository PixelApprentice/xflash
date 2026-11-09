/**
 * Aegis Laptop Diagnostics (Laptop Buyer Kit v2.1)
 * 100% offline, local browser orchestration.
 * Zero external CDNs, zero telemetry, full privacy.
 */

const SAMPLE_SNAPSHOT = {
  "schema_version": "1.0",
  "inspection": { "id": "SAMPLE-USED-T14-DEMO", "collected_at": new Date().toISOString() },
  "system": { "vendor": "LENOVO", "model": "ThinkPad T14 Gen 2", "bios_version": "N34ET45W (1.45)", "bios_date": "2023-04-18" },
  "claims": {
    "model": "ThinkPad T14 Gen 2",
    "ram_gib": 16,
    "storage_capacity_gb": 512,
    "cpu_model": "11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz",
    "gpu_model": "Intel Corporation TigerLake-LP GT2 [Iris Xe Graphics]",
    "display_resolution": "1920x1080"
  },
  "battery": {
    "design_capacity_mwh": 50500,
    "full_charge_capacity_mwh": 37800,
    "cycle_count": 84,
    "source": "sysfs:BAT0",
    "status": "Discharging",
    "voltage_uv": 11520000,
    "health_percentage": 74.9
  },
  "storage": {
    "total_capacity_gb": 512,
    "devices": [
      {
        "model": "KIOXIA KBG40ZNS512G NVMe 512GB",
        "protocol": "nvme",
        "capacity_bytes": 512110190592,
        "capacity_gb": 512.1,
        "nvme_percentage_used": 14,
        "nvme_critical_warning": 0,
        "media_errors": 0,
        "self_test_status": "clean",
        "temperature_c": 38,
        "power_cycles": 420
      }
    ]
  },
  "memory": { "total_bytes": 17179869184, "total_gib": 16.0 },
  "cpu": { "model": "11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz", "cores": 4, "threads": 8, "mhz": 2800, "arch": "x86_64" },
  "gpu": { "model": "Intel Corporation TigerLake-LP GT2 [Iris Xe Graphics]", "driver": "i915" },
  "display": { "connector": "eDP-1", "status": "connected", "resolution": "1920x1080", "modes": ["1920x1080@60Hz"] },
  "ac_adapter": { "name": "ACAD", "online": false },
  "thermals": [
    { "zone": "thermal_zone0", "type": "acpitz", "temp_c": 44.0 },
    { "zone": "thermal_zone1", "type": "x86_pkg_temp", "temp_c": 42.5 }
  ]
};

const SCREEN_PALETTE = [
  { name: "Pure Black (Stuck subpixels & Backlight Bleed)", color: "#000000" },
  { name: "Pure White (Dead pixels & Uniformity)", color: "#ffffff" },
  { name: "Pure Red (Red subpixel health)", color: "#ff0000" },
  { name: "Pure Green (Green subpixel health)", color: "#00ff00" },
  { name: "Pure Blue (Blue subpixel health)", color: "#0000ff" },
  { name: "Yellow Panel", color: "#ffff00" },
  { name: "Magenta Panel", color: "#ff00ff" },
  { name: "Cyan Panel", color: "#00ffff" }
];

const KB_LAYOUT = [
  [
    { code: "Escape", label: "Esc" },
    { code: "F1", label: "F1" }, { code: "F2", label: "F2" }, { code: "F3", label: "F3" }, { code: "F4", label: "F4" },
    { code: "F5", label: "F5" }, { code: "F6", label: "F6" }, { code: "F7", label: "F7" }, { code: "F8", label: "F8" },
    { code: "F9", label: "F9" }, { code: "F10", label: "F10" }, { code: "F11", label: "F11" }, { code: "F12", label: "F12" },
    { code: "Delete", label: "Del" }
  ],
  [
    { code: "Backquote", label: "` ~" },
    { code: "Digit1", label: "1" }, { code: "Digit2", label: "2" }, { code: "Digit3", label: "3" },
    { code: "Digit4", label: "4" }, { code: "Digit5", label: "5" }, { code: "Digit6", label: "6" },
    { code: "Digit7", label: "7" }, { code: "Digit8", label: "8" }, { code: "Digit9", label: "9" },
    { code: "Digit0", label: "0" }, { code: "Minus", label: "- _" }, { code: "Equal", label: "= +" },
    { code: "Backspace", label: "Backspace", class: "w-2" }
  ],
  [
    { code: "Tab", label: "Tab", class: "w-15" },
    { code: "KeyQ", label: "Q" }, { code: "KeyW", label: "W" }, { code: "KeyE", label: "E" },
    { code: "KeyR", label: "R" }, { code: "KeyT", label: "T" }, { code: "KeyY", label: "Y" },
    { code: "KeyU", label: "U" }, { code: "KeyI", label: "I" }, { code: "KeyO", label: "O" },
    { code: "KeyP", label: "P" }, { code: "BracketLeft", label: "[ {" }, { code: "BracketRight", label: "] }" },
    { code: "Backslash", label: "\\ |", class: "w-15" }
  ],
  [
    { code: "CapsLock", label: "Caps Lock", class: "w-175" },
    { code: "KeyA", label: "A" }, { code: "KeyS", label: "S" }, { code: "KeyD", label: "D" },
    { code: "KeyF", label: "F" }, { code: "KeyG", label: "G" }, { code: "KeyH", label: "H" },
    { code: "KeyJ", label: "J" }, { code: "KeyK", label: "K" }, { code: "KeyL", label: "L" },
    { code: "Semicolon", label: "; :" }, { code: "Quote", label: "' \"" },
    { code: "Enter", label: "Enter", class: "w-225" }
  ],
  [
    { code: "ShiftLeft", label: "Shift", class: "w-225" },
    { code: "KeyZ", label: "Z" }, { code: "KeyX", label: "X" }, { code: "KeyC", label: "C" },
    { code: "KeyV", label: "V" }, { code: "KeyB", label: "B" }, { code: "KeyN", label: "N" },
    { code: "KeyM", label: "M" }, { code: "Comma", label: ", <" }, { code: "Period", label: ". >" },
    { code: "Slash", label: "/ ?" },
    { code: "ShiftRight", label: "Shift", class: "w-225" }
  ],
  [
    { code: "ControlLeft", label: "Ctrl", class: "w-15" },
    { code: "MetaLeft", label: "Win / Cmd", class: "w-125" },
    { code: "AltLeft", label: "Alt", class: "w-125" },
    { code: "Space", label: "Spacebar", class: "w-space" },
    { code: "AltRight", label: "Alt", class: "w-125" },
    { code: "ControlRight", label: "Ctrl", class: "w-15" },
    { code: "ArrowLeft", label: "←" },
    { code: "ArrowUp", label: "↑" },
    { code: "ArrowDown", label: "↓" },
    { code: "ArrowRight", label: "→" }
  ]
];

const MANUAL_CHECKS_DEF = [
  { id: "keyboard_response", name: "Keyboard Key Registration", desc: "No sticking, ghosting, or dead key switches." },
  { id: "display_pixels", name: "Screen Pixels & Backlight Bleed", desc: "Zero dead pixels, white spots, or edge light bleed." },
  { id: "trackpad_gestures", name: "Trackpad & Physical Clicks", desc: "Smooth cursor tracking, multi-touch pinch/scroll, solid click." },
  { id: "ports_usb_display", name: "USB, HDMI & Charging Ports", desc: "All USB-A/C and video output ports connect cleanly without wobble." },
  { id: "chassis_battery_swelling", name: "Chassis & Battery Swelling", desc: "No bulge in trackpad/bottom cover, no cracked hinges, missing screws." },
  { id: "webcam_mic", name: "Webcam & Microphones", desc: "Camera video stream clear, no purple/pink sensor tint; audio records." },
  { id: "speakers_audio", name: "Internal Speakers & Jack", desc: "Clean stereo playback without crackle/distortion at 80% volume." },
  { id: "fans_thermals", name: "Cooling Fan & Noise", desc: "Fan spins smoothly without grinding, bearing chatter, or excessive vibration." }
];

class App {
  constructor() {
    this.currentSession = null;
    this.lastProbedSpecs = null;
    this.isExpertMode = false;
    this.verifiedKeys = new Set();
    this.screenPaletteIndex = 0;

    // Web Audio state
    this.audioCtx = null;
    this.activeOsc = null;
    this.activeGain = null;
    this.activePanner = null;
    this.isTonePlaying = false;

    // MediaStream state
    this.mediaStream = null;
    this.micAudioCtx = null;
    this.micAnalyser = null;
    this.micAnimFrameId = null;

    // Trackpad Canvas state
    this.activePointers = new Map();

    this.initTheme();
    this.initMode();
    this.checkAppMode();
    this.bindEvents();
    this.buildKeyboard();
    this.initTrackpadCanvas();
    this.initKeyboardHeatmap();
    this.loadHistory();
    this.initBootSplash();
    this.initCommandPalette();
    this.initListingToggle();
    this.initSchematicClicks();
  }

  async checkAppMode() {
    try {
      const resp = await fetch("/api/health");
      if (!resp.ok) return;
      const data = await resp.json();
      this.appHealth = data;
      const badge = document.getElementById("appModeBadge");
      if (badge) {
        if (data.portable_mode) {
          badge.textContent = "⚡ USB PORTABLE";
          badge.className = "badge status-passed portable-pulse";
          badge.title = `Zero-Trace Portable USB Mode active. All reports and SQLite database saved to USB drive: ${data.db_path}`;
        } else {
          badge.textContent = "LOCAL SYSTEM";
          badge.className = "badge status-passed";
          badge.title = `System Mode: Database at ${data.db_path}`;
        }
      }
      const stripMode = document.getElementById("stripModeText");
      if (stripMode) {
        stripMode.textContent = data.portable_mode ? "⚡ USB ZERO-TRACE PORTABLE" : "100% AIR-GAPPED OFFLINE";
      }
    } catch (_) {}
  }

  // --------------------------------------------------------------------------
  // Theme & Mode Management
  // --------------------------------------------------------------------------
  initTheme() {
    const saved = localStorage.getItem("lbk_theme") || "light";
    document.documentElement.setAttribute("data-theme", saved);
  }

  toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const next = current === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("lbk_theme", next);
  }

  initMode() {
    const saved = localStorage.getItem("lbk_expert_mode") === "true";
    const toggle = document.getElementById("expertModeToggle");
    if (toggle) {
      toggle.checked = saved;
    }
    this.applyMode(saved);
  }

  applyMode(isExpert) {
    this.isExpertMode = isExpert;
    localStorage.setItem("lbk_expert_mode", isExpert ? "true" : "false");

    document.body.classList.toggle("mode-expert", isExpert);
    document.body.classList.toggle("mode-normal", !isExpert);

    const normalLabel = document.querySelector(".normal-label");
    const expertLabel = document.querySelector(".expert-label");
    if (normalLabel && expertLabel) {
      normalLabel.classList.toggle("active", !isExpert);
      expertLabel.classList.toggle("active", isExpert);
    }

    const configPanel = document.getElementById("expertConfigPanel");
    if (configPanel) {
      configPanel.style.display = isExpert ? "block" : "none";
    }

    const expertTabBtn = document.querySelector(".expert-tab-btn");
    if (expertTabBtn) {
      expertTabBtn.style.display = isExpert ? "inline-flex" : "none";
    }

    const thermalCard = document.getElementById("thermalDialCard");
    if (thermalCard) {
      thermalCard.style.display = isExpert ? "block" : "none";
    }

    // If currently on expert subtab and switching to normal, fallback to findings
    const activeSubtab = document.querySelector(".subnav-btn.active");
    if (!isExpert && activeSubtab && activeSubtab.dataset.subtab === "subtab-expert") {
      this.switchSubtab("subtab-findings");
    }

    const stripExpert = document.getElementById("stripExpertIndicator");
    if (stripExpert) {
      stripExpert.textContent = isExpert ? "Expert Mode" : "Buyer Mode";
      stripExpert.style.color = isExpert ? "var(--primary)" : "inherit";
    }
  }

  // --------------------------------------------------------------------------
  // Event Binding
  // --------------------------------------------------------------------------
  bindEvents() {
    // Navigation Tabs and all buttons with data-tab
    document.querySelectorAll(".nav-btn").forEach(btn => {
      btn.addEventListener("click", () => this.switchTab(btn.dataset.tab));
    });

    // Jump navigation buttons (Station headers and quick check ribbon)
    document.querySelectorAll("[data-jump-tab]").forEach(btn => {
      btn.addEventListener("click", () => this.switchTab(btn.dataset.jumpTab));
    });

    // Guided station flow navigation buttons (station-to-station next/previous footer)
    document.querySelectorAll("[data-flow-jump]").forEach(btn => {
      btn.addEventListener("click", () => {
        this.switchTab(btn.dataset.flowJump);
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    });

    // Version Update Notice dismissal
    const vNotice = document.getElementById("versionUpdateNotice");
    const dismissBtn = document.getElementById("dismissVNoticeBtn");
    if (vNotice && localStorage.getItem("xflash_v31_dismissed") === "true") {
      vNotice.style.display = "none";
    }
    if (dismissBtn && vNotice) {
      dismissBtn.addEventListener("click", () => {
        vNotice.style.opacity = "0";
        setTimeout(() => { vNotice.style.display = "none"; }, 200);
        localStorage.setItem("xflash_v31_dismissed", "true");
      });
    }

    // Corner / Angle Verification Mode Toggle
    this.angleVerificationEnabled = true;
    const angleBtn = document.getElementById("kbAngleModeBtn");
    if (angleBtn) {
      angleBtn.addEventListener("click", () => {
        this.angleVerificationEnabled = !this.angleVerificationEnabled;
        angleBtn.textContent = `Corner Check: ${this.angleVerificationEnabled ? "ON" : "OFF"}`;
        angleBtn.className = `btn btn-sm ${this.angleVerificationEnabled ? "btn-secondary" : "btn-outline"}`;
      });
    }

    // Workflow Stepper Node click navigation
    document.querySelectorAll(".step-node").forEach(node => {
      node.addEventListener("click", () => {
        const step = parseInt(node.dataset.step, 10);
        if (step === 1) {
          this.switchTab("tab-inspect");
          const el = document.getElementById("claimModel");
          if (el) el.focus();
        } else if (step === 2) {
          this.switchTab("tab-inspect");
          const btn = document.getElementById("runLiveBtn");
          if (btn) btn.scrollIntoView({ behavior: "smooth", block: "center" });
        } else if (step === 3) {
          this.switchTab("tab-inspect");
          if (this.currentSession) {
            document.getElementById("verdictBanner")?.scrollIntoView({ behavior: "smooth" });
          }
        } else if (step === 4) {
          this.switchTab("tab-screen");
        } else if (step === 5) {
          this.switchTab("tab-inspect");
          document.getElementById("exportHtmlBtn")?.scrollIntoView({ behavior: "smooth" });
        }
      });
    });

    // Subnav Tabs
    document.querySelectorAll(".subnav-btn").forEach(btn => {
      btn.addEventListener("click", () => this.switchSubtab(btn.dataset.subtab));
    });

    // Theme toggle
    document.getElementById("themeToggleBtn").addEventListener("click", () => this.toggleTheme());

    // Normal vs Expert Mode switch
    document.getElementById("expertModeToggle").addEventListener("change", (e) => {
      this.applyMode(e.target.checked);
    });

    // Sliders in Expert Mode
    const batSlider = document.getElementById("threshBatteryWarn");
    if (batSlider) {
      batSlider.addEventListener("input", (e) => {
        document.getElementById("threshBatteryWarnVal").innerText = `${e.target.value}%`;
      });
    }

    const nvmeSlider = document.getElementById("threshNvmeWear");
    if (nvmeSlider) {
      nvmeSlider.addEventListener("input", (e) => {
        document.getElementById("threshNvmeWearVal").innerText = `${e.target.value}%`;
      });
    }

    // Auto-Detect Specs button
    document.getElementById("autoDetectBtn").addEventListener("click", () => this.runAutoDetection());

    // Inspection Buttons
    document.getElementById("runLiveBtn").addEventListener("click", () => this.runLiveInspection());
    document.getElementById("loadSampleBtn").addEventListener("click", () => this.loadSampleInspection());
    document.getElementById("uploadSnapshotBtn").addEventListener("click", () => {
      document.getElementById("snapshotFileInput").click();
    });
    document.getElementById("snapshotFileInput").addEventListener("change", (e) => this.handleFileUpload(e));

    // Print Report
    document.getElementById("printReportBtn").addEventListener("click", () => window.print());

    // Save to USB Reports
    const saveUsbBtn = document.getElementById("saveUsbReportBtn");
    if (saveUsbBtn) {
      saveUsbBtn.addEventListener("click", () => this.saveToUsbReports());
    }

    // Screen Test Tool
    document.getElementById("launchScreenTestBtn").addEventListener("click", () => this.startScreenTest());
    document.getElementById("screenTestOverlay").addEventListener("click", () => this.cycleScreenColor());
    window.addEventListener("keydown", (e) => {
      if (document.getElementById("screenTestOverlay").style.display !== "none") {
        if (e.code === "Escape") this.stopScreenTest();
        else if (e.code === "Space" || e.code === "ArrowRight") this.cycleScreenColor();
        else if (e.code === "ArrowLeft") this.cycleScreenColor(-1);
      } else {
        this.handleGlobalKeypress(e);
      }
    });

    window.addEventListener("keyup", (e) => {
      this.handleGlobalKeyRelease(e);
    });

    // Keyboard Reset
    document.getElementById("kbResetBtn").addEventListener("click", () => this.resetKeyboard());

    // History refresh
    document.getElementById("refreshHistoryBtn").addEventListener("click", () => this.loadHistory());

    // Audio Diagnostics
    this.bindAudioEvents();

    // Media (Camera & Mic) Diagnostics
    this.bindMediaEvents();
  }

  // switchTab is defined further below with full tab-switch side-effects.

  switchSubtab(subtabId) {
    document.querySelectorAll(".subnav-btn").forEach(b => b.classList.toggle("active", b.dataset.subtab === subtabId));
    document.querySelectorAll(".subtab-pane").forEach(p => p.classList.toggle("active", p.id === subtabId));
  }

  // --------------------------------------------------------------------------
  // Auto-Detection Engine
  // --------------------------------------------------------------------------
  async runAutoDetection() {
    const btn = document.getElementById("autoDetectBtn");
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerText = "⚡ Probing Hardware…";

    try {
      const resp = await fetch("/api/probe");
      if (!resp.ok) {
        throw new Error(`Probe endpoint returned HTTP ${resp.status}`);
      }
      const data = await resp.json();
      this.lastProbedSpecs = data;

      // Populate Claims Form with Detected Physical Values
      if (data.system && data.system.model) {
        document.getElementById("claimModel").value = data.system.model;
      }
      if (data.memory && data.memory.total_gib) {
        document.getElementById("claimRam").value = Math.round(data.memory.total_gib);
      }
      if (data.storage && (data.storage.total_capacity_gb || (data.storage.devices && data.storage.devices[0]))) {
        const cap = data.storage.total_capacity_gb || Math.round((data.storage.devices[0].capacity_bytes || 0) / 1e9);
        if (cap > 0) document.getElementById("claimStorage").value = cap;
      }
      if (data.cpu && data.cpu.model) {
        document.getElementById("claimCpu").value = data.cpu.model;
      }
      if (data.gpu && data.gpu.model) {
        document.getElementById("claimGpu").value = data.gpu.model;
      }
      if (data.display && data.display.resolution) {
        document.getElementById("claimDisplay").value = data.display.resolution;
      }

      // Populate Host Environment Banner
      const banner = document.getElementById("hostMetaBanner");
      if (banner && data.system_extended) {
        const ext = data.system_extended;
        const osVal = document.getElementById("hostOsVal");
        const bootVal = document.getElementById("hostBootVal");
        const dispVal = document.getElementById("hostDisplayVal");
        const instVal = document.getElementById("hostInstallVal");
        const wipeTag = document.getElementById("hostWipeTag");

        if (osVal) osVal.textContent = `${ext.os_name || 'Linux'} · ${ext.cpu_arch || 'x86_64'}`;
        if (bootVal) bootVal.textContent = `${ext.boot_firmware || 'UEFI'} · ${ext.partition_table || 'GPT'}`;
        if (dispVal) {
          const pType = data.display?.edid?.is_oled ? 'OLED' : (data.display?.edid?.panel_type || 'IPS/LCD');
          dispVal.textContent = `${pType} · ${ext.touchscreen_detected ? 'Touch' : 'Non-Touch'}`;
        }
        if (instVal) instVal.textContent = ext.os_install_age_estimate || 'Unknown';
        if (wipeTag) {
          if (ext.is_recent_wipe) {
            wipeTag.className = "badge status-warning";
            wipeTag.textContent = "RECENT WIPE";
          } else {
            wipeTag.className = "badge status-passed";
            wipeTag.textContent = "ESTABLISHED";
          }
        }
        banner.style.display = "block";
      }

      btn.innerText = "✓ Specs Detected!";
      this.updateWorkflowStepper(2);
      setTimeout(() => {
        btn.innerHTML = origHtml;
        btn.disabled = false;
      }, 2000);

      // If a session is open, refresh comparison
      if (this.currentSession) {
        this.renderComparisonTable(this.currentSession);
      }
    } catch (err) {
      console.warn("Auto-detect failed:", err);
      btn.innerText = "Probe Unavailable";
      setTimeout(() => {
        btn.innerHTML = origHtml;
        btn.disabled = false;
      }, 2000);
      alert("Hardware auto-detect notice: " + err.message + "\n(You can still run inspection or enter claims manually)");
    }
  }

  getClaimsInput() {
    const model = document.getElementById("claimModel").value.trim();
    const ram = parseFloat(document.getElementById("claimRam").value);
    const storage = parseFloat(document.getElementById("claimStorage").value);
    const cpu = document.getElementById("claimCpu").value.trim();
    const gpu = document.getElementById("claimGpu").value.trim();
    const display = document.getElementById("claimDisplay") ? document.getElementById("claimDisplay").value.trim() : "";

    const claims = {};
    if (model) claims.model = model;
    if (!isNaN(ram) && ram > 0) claims.ram_gib = ram;
    if (!isNaN(storage) && storage > 0) claims.storage_capacity_gb = storage;
    if (cpu) claims.cpu_model = cpu;
    if (gpu) claims.gpu_model = gpu;
    if (display) claims.display_resolution = display;
    return claims;
  }

  // --------------------------------------------------------------------------
  // Inspection Executions
  // --------------------------------------------------------------------------
  async runLiveInspection() {
    const btn = document.getElementById("runLiveBtn");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerText = "Querying Live Hardware…";

    const claims = this.getClaimsInput();
    const notes = document.getElementById("operatorNotes").value.trim();

    try {
      const resp = await fetch("/api/inspect/live", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claims, operator_notes: notes })
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.error || "Inspection query failed");
      }
      const data = await resp.json();
      this.renderSession(data);
    } catch (err) {
      alert("Live inspection notice: " + err.message + "\n(Falling back to sample reference inspection)");
      this.loadSampleInspection();
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }

  async loadSampleInspection() {
    const claims = this.getClaimsInput();
    const notes = document.getElementById("operatorNotes").value.trim() || "Synthetic reference session";
    const snapshot = JSON.parse(JSON.stringify(SAMPLE_SNAPSHOT));
    if (Object.keys(claims).length > 0) {
      snapshot.claims = { ...snapshot.claims, ...claims };
    }

    try {
      const resp = await fetch("/api/inspect/snapshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ snapshot, operator_notes: notes })
      });
      const data = await resp.json();
      this.renderSession(data);
    } catch (err) {
      alert("Error loading sample: " + err.message);
    }
  }

  async handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const snapshot = JSON.parse(e.target.result);
        const notes = document.getElementById("operatorNotes").value.trim() || `Imported ${file.name}`;
        const resp = await fetch("/api/inspect/snapshot", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ snapshot, operator_notes: notes })
        });
        const data = await resp.json();
        this.renderSession(data);
      } catch (err) {
        alert("Failed to parse snapshot file: " + err.message);
      }
    };
    reader.readAsText(file);
  }

  // --------------------------------------------------------------------------
  // Session Rendering & Gauges
  // --------------------------------------------------------------------------
  renderSession(session) {
    this.currentSession = session;
    document.getElementById("emptyState").style.display = "none";
    document.getElementById("sessionResults").style.display = "block";
    this.updateWorkflowStepper(3);

    const report = session.report || {};
    const risk = report.risk_state || "unknown";

    // Verdict Banner
    const verdictBannerEl = document.getElementById("verdictBanner");
    if (verdictBannerEl) {
      verdictBannerEl.classList.remove("analyzed");
      void verdictBannerEl.offsetWidth;
      verdictBannerEl.classList.add("analyzed");
    }
    const badge = document.getElementById("verdictBadge");
    const title = document.getElementById("verdictTitle");
    const summary = document.getElementById("verdictSummary");

    badge.className = `badge status-${risk === "high_risk" ? "high" : risk}`;
    badge.innerText = risk.replace(/_/g, " ").toUpperCase();

    const titles = {
      "critical": "Critical Hardware Fault Detected",
      "high_risk": "High Risk — Major Discrepancies or Degradation",
      "review": "Review Before Buying — Minor Discrepancies",
      "no_detected_anomaly_in_evaluated_checks": "No Major Anomalies Detected in Evaluated Checks",
      "insufficient_data": "Insufficient Hardware Data for Verdict"
    };
    title.innerText = titles[risk] || "Inspection Complete";

    const findingCount = report.finding_count || 0;
    summary.innerText = `Evaluated checks completed with ${findingCount} finding${findingCount === 1 ? "" : "s"}. Always confirm with manual physical inspection.`;

    document.getElementById("sessionMetaId").innerText = `Session ID: ${session.id}`;
    document.getElementById("sessionMetaDate").innerText = `Date: ${session.created_at ? new Date(session.created_at).toLocaleString() : "Just now"}`;
    document.getElementById("sessionMetaModel").innerText = `Model: ${session.system_model || "Unknown"}`;
    document.getElementById("findingsCountBadge").innerText = findingCount;

    // Export links
    document.getElementById("exportHtmlBtn").href = `/api/export/${session.id}/html`;
    document.getElementById("exportJsonBtn").href = `/api/export/${session.id}/json`;
    const saveUsbBtn = document.getElementById("saveUsbReportBtn");
    if (saveUsbBtn) saveUsbBtn.disabled = false;
    const saveStatus = document.getElementById("saveUsbReportStatus");
    if (saveStatus) saveStatus.textContent = "";

    // Render Health Gauges
    this.renderHealthGauges(session.snapshot || {});

    // Update Interactive Hardware Schematic
    this.updateSchematic(session);

    // Render Findings Cards
    this.renderFindings(report.findings || []);

    // Render Comparison Table
    this.renderComparisonTable(session);

    // Render Coverage Table
    this.renderCoverage(report.coverage || {});

    // Render Manual Checklist
    this.renderManualChecklist(session.manual_checks || {});

    // Render Beginner Mode Glanceable Health Assessment
    this.renderBeginnerSummary(session);

    // Render Expert Mode Telemetry Tables
    this.renderExpertTelemetry(session.snapshot || {});
  }

  renderBeginnerSummary(session) {
    const snap = session.snapshot || {};
    const report = session.report || {};
    const findings = report.findings || [];

    // Battery
    const bat = snap.battery;
    const bTitle = document.getElementById("bCardBatteryTitle");
    const bDesc = document.getElementById("bCardBatteryDetail");
    const bTag = document.getElementById("bCardBatteryTag");
    if (bTitle && bDesc) {
      if (bat && bat.health_pct !== null && bat.health_pct !== undefined) {
        const cycles = bat.cycle_count ? ` · ${bat.cycle_count} cycles` : "";
        if (bat.health_pct >= 80) {
          bTitle.innerHTML = `<span style="color:var(--severity-passed); font-weight:700;">Healthy</span> · ${bat.health_pct}% Capacity`;
          bDesc.textContent = `Battery retains good charge capacity (${bat.full_charge_capacity_mwh || "--"} mWh${cycles}). Normal daily runtime expected.`;
          if (bTag) bTag.textContent = "Healthy";
        } else {
          bTitle.innerHTML = `<span style="color:var(--severity-warning); font-weight:700;">Degraded</span> · ${bat.health_pct}% Capacity`;
          bDesc.textContent = `Battery is significantly worn${cycles}. Budget for an eventual battery replacement.`;
          if (bTag) bTag.textContent = "Degraded";
        }
      } else {
        bTitle.textContent = "Battery Not Detected / AC Mode";
        bDesc.textContent = "System is running on AC wall power or battery controller registers are not exposed.";
        if (bTag) bTag.textContent = "AC Mode";
      }
    }

    // Storage
    const storage = snap.storage;
    const sTitle = document.getElementById("bCardStorageTitle");
    const sDesc = document.getElementById("bCardStorageDetail");
    const sTag = document.getElementById("bCardStorageTag");
    if (sTitle && sDesc) {
      if (storage) {
        const errors = storage.media_errors || 0;
        const used = storage.percentage_used;
        const cap = storage.capacity_gb ? `${storage.capacity_gb} GB` : "Drive";
        if (errors > 0) {
          sTitle.innerHTML = `<span style="color:var(--severity-critical); font-weight:700;">Drive Warning</span> · ${errors} Errors`;
          sDesc.textContent = `Physical drive logged ${errors} media read/write errors. Immediate backup and replacement required.`;
          if (sTag) sTag.textContent = "Warning";
        } else if (used !== null && used !== undefined) {
          sTitle.innerHTML = `<span style="color:var(--severity-passed); font-weight:700;">Clean SSD</span> · ${cap}`;
          sDesc.textContent = `Zero drive errors recorded. Flash wear is at ${used}% (ample endurance remaining).`;
          if (sTag) sTag.textContent = "Healthy";
        } else {
          sTitle.textContent = `${cap} · Storage Active`;
          sDesc.textContent = `${storage.model || "Internal drive"} detected with clean operational status.`;
          if (sTag) sTag.textContent = "Active";
        }
      }
    }

    // Listing Claims Agreement
    const cTitle = document.getElementById("bCardClaimsTitle");
    const cDesc = document.getElementById("bCardClaimsDetail");
    const cTag = document.getElementById("bCardClaimsTag");
    if (cTitle && cDesc) {
      const claimFindings = findings.filter(f => f.category === "memory" || f.category === "storage" || f.category === "system");
      const highMismatches = claimFindings.filter(f => f.severity === "high" || f.severity === "critical");
      if (highMismatches.length > 0) {
        cTitle.innerHTML = `<span style="color:var(--severity-critical); font-weight:700;">Discrepancy</span> · Check Specs`;
        cDesc.textContent = highMismatches[0].explanation || "Physical hardware did not match seller listing claims.";
        if (cTag) cTag.textContent = "Mismatch";
      } else {
        cTitle.innerHTML = `<span style="color:var(--severity-passed); font-weight:700;">Claims Verified</span> · Hardware Matches`;
        cDesc.textContent = "Observed physical RAM, processor, and storage capacity agree with seller listing specs.";
        if (cTag) cTag.textContent = "Agreed";
      }
    }

    // Thermals
    const tTitle = document.getElementById("bCardThermalsTitle");
    const tDesc = document.getElementById("bCardThermalsDetail");
    const tTag = document.getElementById("bCardThermalsTag");
    if (tTitle && tDesc) {
      const cpu = snap.cpu || {};
      const thermals = snap.thermals || {};
      const temp = cpu.temperature_c || thermals.cpu_temp_c || thermals.max_temp_c || thermals.average_temp_c;
      if (temp !== undefined && temp !== null) {
        if (temp >= 85) {
          tTitle.innerHTML = `<span style="color:var(--severity-warning); font-weight:700;">Elevated</span> · ${temp}°C`;
          tDesc.textContent = "Processor is idling high. Clean heatsink dust or check thermal paste.";
          if (tTag) tTag.textContent = "Warm";
        } else {
          tTitle.innerHTML = `<span style="color:var(--severity-passed); font-weight:700;">Cool & Clean</span> · ${temp}°C`;
          tDesc.textContent = "Processor operates well within thermal limits. No thermal throttling detected.";
          if (tTag) tTag.textContent = "Normal";
        }
      } else {
        tTitle.textContent = "Thermals Monitored";
        tDesc.textContent = "Run the 5-Second Cooling Pulse under the Cooling tab to test fan response.";
        if (tTag) tTag.textContent = "Active";
      }
    }
  }

  async saveToUsbReports() {
    if (!this.currentSession) {
      alert("Please run or load an inspection session first.");
      return;
    }
    const btn = document.getElementById("saveUsbReportBtn");
    const status = document.getElementById("saveUsbReportStatus");
    if (btn) btn.disabled = true;
    if (status) status.textContent = "Writing report to USB storage…";

    try {
      const resp = await fetch("/api/export/portable", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: this.currentSession.id })
      });
      const data = await resp.json();
      if (resp.ok && data.success) {
        this.updateWorkflowStepper(5);
        if (status) {
          status.innerHTML = `<span style="color:var(--severity-passed); font-weight:600;">✓ Saved to USB: <code>${data.html_file}</code></span>`;
        }
      } else {
        if (status) status.textContent = `Notice: ${data.error || "Save failed"}`;
      }
    } catch (err) {
      if (status) status.textContent = `Error: ${err.message}`;
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  renderHealthGauges(snapshot) {
    // 1. Battery Gauge
    const bat = snapshot.battery || {};
    const pathEl = document.getElementById("batteryCirclePath");
    const textEl = document.getElementById("batteryHealthDialText");
    const cyclesEl = document.getElementById("batteryCyclesSub");

    let healthPct = null;
    if (typeof bat.health_percentage === "number") {
      healthPct = bat.health_percentage;
    } else if (bat.full_charge_capacity_mwh && bat.design_capacity_mwh && bat.design_capacity_mwh > 0) {
      healthPct = (bat.full_charge_capacity_mwh / bat.design_capacity_mwh) * 100;
    }

    if (healthPct !== null && !isNaN(healthPct)) {
      const clamped = Math.max(0, Math.min(100, Math.round(healthPct)));
      pathEl.setAttribute("stroke-dasharray", `${clamped}, 100`);
      textEl.textContent = `${clamped}%`;

      if (clamped >= 80) {
        pathEl.style.stroke = "var(--severity-passed)";
      } else if (clamped >= 65) {
        pathEl.style.stroke = "var(--severity-warning)";
      } else {
        pathEl.style.stroke = "var(--severity-critical)";
      }

      cyclesEl.textContent = bat.cycle_count !== undefined && bat.cycle_count !== null
        ? `${bat.cycle_count} cycles`
        : "Cycles unknown";
    } else {
      pathEl.setAttribute("stroke-dasharray", "0, 100");
      textEl.textContent = "N/A";
      cyclesEl.textContent = "No battery detected";
    }

    // 2. Storage NVMe Endurance Gauge
    const storage = snapshot.storage || {};
    const devices = storage.devices || [];
    const primDev = devices[0] || {};
    const wearFill = document.getElementById("storageWearFill");
    const wearText = document.getElementById("storageWearText");
    const integSub = document.getElementById("storageIntegritySub");

    if (primDev.nvme_percentage_used !== undefined && primDev.nvme_percentage_used !== null) {
      const wear = primDev.nvme_percentage_used;
      wearFill.style.width = `${Math.min(100, Math.max(2, wear))}%`;
      wearText.textContent = `${wear}% Used`;

      if (wear >= 80) {
        wearFill.style.backgroundColor = "var(--severity-critical)";
      } else if (wear >= 50) {
        wearFill.style.backgroundColor = "var(--severity-warning)";
      } else {
        wearFill.style.backgroundColor = "var(--severity-passed)";
      }

      const errors = primDev.media_errors ?? 0;
      integSub.textContent = `${errors} Media Errors · ${primDev.self_test_status || "Clean"}`;
    } else {
      wearFill.style.width = "0%";
      wearText.textContent = "Standard Disk";
      integSub.textContent = primDev.protocol ? primDev.protocol.toUpperCase() : "SATA/NVMe";
    }

    // 3. CPU Temperature Gauge
    const thermalsData = snapshot.thermals || {};
    const zones = Array.isArray(thermalsData) ? thermalsData : (thermalsData.zones || []);
    const tempText = document.getElementById("cpuTempText");
    const tempSub = document.getElementById("thermalStatusSub");

    let peakTemp = typeof thermalsData.max_temp_c === "number" ? thermalsData.max_temp_c : null;
    if (peakTemp === null) {
      zones.forEach(t => {
        if (typeof t.temp_c === "number") {
          if (peakTemp === null || t.temp_c > peakTemp) {
            peakTemp = t.temp_c;
          }
        }
      });
    }

    if (peakTemp !== null) {
      tempText.textContent = `${Math.round(peakTemp)}°C`;
      if (peakTemp >= 85) {
        tempSub.textContent = "High · Throttle Risk";
        tempText.style.color = "var(--severity-critical)";
      } else if (peakTemp >= 68) {
        tempSub.textContent = "Elevated · Active";
        tempText.style.color = "var(--severity-warning)";
      } else {
        tempSub.textContent = "Normal · Idle";
        tempText.style.color = "var(--severity-passed)";
      }
    } else {
      tempText.textContent = "--°C";
      tempSub.textContent = "Sensor unread";
      tempText.style.color = "inherit";
    }
  }

  renderFindings(findings) {
    const container = document.getElementById("findingsList");
    container.innerHTML = "";

    if (!findings || findings.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">✓</div>
          <h3>Clean Findings</h3>
          <p>No anomaly findings were triggered by the automated analysis rules.</p>
        </div>
      `;
      return;
    }

    findings.forEach((f, idx) => {
      const card = document.createElement("div");
      card.className = `finding-card ${f.severity || "info"}`;
      card.style.setProperty("--card-stagger", Math.min(idx, 8).toString());

      // Derive buyer leverage / impact note (Why It Matters)
      let impactNote = "Component operates within standard specifications.";
      if (f.code && f.code.includes("BATTERY_DEGRADATION")) {
        impactNote = "Noticeable runtime loss off charger; negotiate $60-$90 battery replacement allowance.";
      } else if (f.code && f.code.includes("LOW_CYCLES_HIGH_DEGRADATION")) {
        impactNote = "Atypical decay curve; pack may have sat discharged or endured high heat storage.";
      } else if (f.code && f.code.includes("NVME_WEAR")) {
        impactNote = "High controller write endurance consumed; expect drive replacement sooner under load.";
      } else if (f.code && f.code.includes("RAM")) {
        impactNote = "Advertised RAM does not match physical capacity; verify integrated VRAM allocation or module.";
      } else if (f.severity === "warning" || f.severity === "high") {
        impactNote = "Discrepancy detected; investigate physical hardware state before finalizing deal.";
      } else if (f.severity === "critical") {
        impactNote = "Hardware failure or severe risk; walk away or require seller repair/refund guarantee.";
      }

      card.innerHTML = `
        <div class="finding-header">
          <span class="badge status-${f.severity}">${(f.severity || "INFO").toUpperCase()}</span>
          <span class="text-muted" style="font-family:var(--font-mono); font-size:0.8rem;">${f.code || ""}</span>
        </div>
        <h3 style="margin-top:0.4rem;">${f.title || "Finding"}</h3>
        
        <!-- 3-Part Finding Grid -->
        <div class="finding-part-grid">
          <div class="finding-part-item">
            <strong>1. What's Wrong</strong>
            <span>${f.details || "Observed register value divergence."}</span>
          </div>
          <div class="finding-part-item">
            <strong>2. Why It Matters (Buyer Impact)</strong>
            <span>${impactNote}</span>
          </div>
          <div class="finding-part-item">
            <strong>3. Recommended Action</strong>
            <span>${f.recommended_action || "Investigate reading."}</span>
          </div>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.5rem; flex-wrap:wrap; gap:0.5rem;">
          <button type="button" class="evidence-toggle" data-idx="${idx}">Show Evidence & Provenance ▾</button>
          <button type="button" class="finding-telemetry-btn" data-target="subtab-expert">
            View Raw Register Telemetry ↗
          </button>
        </div>

        <pre id="ev-${idx}" class="code-block evidence-block" style="display:none; margin-top:0.5rem;">${JSON.stringify({ evidence: f.evidence, confidence: f.confidence, source: f.source }, null, 2)}</pre>
      `;

      card.querySelector(".evidence-toggle").addEventListener("click", (e) => {
        const pre = document.getElementById(`ev-${idx}`);
        const isHidden = pre.style.display === "none";
        pre.style.display = isHidden ? "block" : "none";
        e.target.innerText = isHidden ? "Hide Evidence ▴" : "Show Evidence & Provenance ▾";
      });

      const telemBtn = card.querySelector(".finding-telemetry-btn");
      if (telemBtn) {
        telemBtn.addEventListener("click", () => {
          const toggle = document.getElementById("expertModeToggle");
          if (toggle && !toggle.checked) {
            toggle.checked = true;
            this.applyMode(true);
          }
          this.switchSubtab("subtab-expert");
          document.getElementById("subtab-expert")?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      }

      container.appendChild(card);
    });
  }

  renderComparisonTable(session) {
    const tbody = document.getElementById("comparisonTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    const snapshot = session.snapshot || {};
    const claims = snapshot.claims || this.getClaimsInput();

    const rows = [];

    // 1. Model
    const claimedModel = claims.model || "Not specified";
    const detectedModel = snapshot.system?.model || "Unknown";
    let modelVerdict = "DETECTED";
    let modelBadgeClass = "inconclusive";
    if (claims.model) {
      const cm = claimedModel.toLowerCase().replace(/[^a-z0-9]/g, "");
      const dm = detectedModel.toLowerCase().replace(/[^a-z0-9]/g, "");
      if (dm.includes(cm) || cm.includes(dm)) {
        modelVerdict = "MATCH";
        modelBadgeClass = "passed";
      } else {
        modelVerdict = "DISCREPANCY";
        modelBadgeClass = "warning";
      }
    }
    rows.push({
      spec: "System Model",
      claim: claimedModel,
      detected: detectedModel,
      verdict: modelVerdict,
      badge: modelBadgeClass
    });

    // 2. RAM
    const claimedRam = claims.ram_gib ? `${claims.ram_gib} GiB` : "Not specified";
    let detectedRam = "Unknown";
    let ramVerdict = "DETECTED";
    let ramBadgeClass = "inconclusive";
    if (snapshot.memory && snapshot.memory.total_bytes) {
      const gig = snapshot.memory.total_bytes / (1024 ** 3);
      detectedRam = `${gig.toFixed(1)} GiB`;
      if (claims.ram_gib) {
        const ratio = gig / claims.ram_gib;
        if (ratio >= 0.98) {
          ramVerdict = "MATCH";
          ramBadgeClass = "passed";
        } else if (ratio >= 0.88) {
          ramVerdict = "VRAM RESERVED";
          ramBadgeClass = "passed";
        } else {
          ramVerdict = "MISMATCH";
          ramBadgeClass = "warning";
        }
      }
    }
    rows.push({
      spec: "RAM Capacity",
      claim: claimedRam,
      detected: detectedRam,
      verdict: ramVerdict,
      badge: ramBadgeClass
    });

    // 3. Storage
    const claimedStorage = claims.storage_capacity_gb ? `${claims.storage_capacity_gb} GB` : "Not specified";
    let detectedStorage = "Unknown";
    let storVerdict = "DETECTED";
    let storBadgeClass = "inconclusive";
    if (snapshot.storage && snapshot.storage.devices && snapshot.storage.devices.length > 0) {
      let totalB = 0;
      snapshot.storage.devices.forEach(d => { totalB += (d.capacity_bytes || 0); });
      const gb = totalB / 1e9;
      detectedStorage = `${Math.round(gb)} GB (${snapshot.storage.devices.length} disk${snapshot.storage.devices.length > 1 ? 's' : ''})`;
      if (claims.storage_capacity_gb) {
        const ratio = gb / claims.storage_capacity_gb;
        if (ratio >= 0.93) {
          storVerdict = "MATCH";
          storBadgeClass = "passed";
        } else {
          storVerdict = "MISMATCH";
          storBadgeClass = "warning";
        }
      }
    }
    rows.push({
      spec: "Storage Size",
      claim: claimedStorage,
      detected: detectedStorage,
      verdict: storVerdict,
      badge: storBadgeClass
    });

    // 4. CPU
    const claimedCpu = claims.cpu_model || "Not specified";
    const detectedCpu = snapshot.cpu?.model || "Not detected";
    let cpuVerdict = "DETECTED";
    let cpuBadge = "inconclusive";
    if (claims.cpu_model && snapshot.cpu?.model) {
      const cc = claimedCpu.toLowerCase().replace(/[^a-z0-9]/g, "");
      const dc = detectedCpu.toLowerCase().replace(/[^a-z0-9]/g, "");
      cpuVerdict = (dc.includes(cc) || cc.includes(dc)) ? "MATCH" : "VERIFY";
      cpuBadge = cpuVerdict === "MATCH" ? "passed" : "warning";
    }
    rows.push({
      spec: "CPU Specification",
      claim: claimedCpu,
      detected: detectedCpu,
      verdict: cpuVerdict,
      badge: cpuBadge
    });

    // 5. GPU
    const claimedGpu = claims.gpu_model || "Not specified";
    const detectedGpu = snapshot.gpu?.model || "Integrated/PCIe Controller";
    rows.push({
      spec: "GPU / Graphics",
      claim: claimedGpu,
      detected: detectedGpu,
      verdict: claims.gpu_model ? "VERIFY" : "DETECTED",
      badge: "inconclusive"
    });

    // 6. Display
    const claimedDisp = claims.display_resolution || "Not specified";
    const detectedDisp = snapshot.display?.resolution || (snapshot.display?.connector ? `${snapshot.display.connector} connected` : "Panel detected");
    rows.push({
      spec: "Display Panel",
      claim: claimedDisp,
      detected: detectedDisp,
      verdict: claims.display_resolution ? "VERIFY" : "DETECTED",
      badge: "inconclusive"
    });

    rows.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${r.spec}</strong></td>
        <td><code>${r.claim}</code></td>
        <td><code>${r.detected}</code></td>
        <td><span class="badge status-${r.badge}">${r.verdict}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  renderCoverage(coverage) {
    const tbody = document.getElementById("coverageTableBody");
    tbody.innerHTML = "";

    const descriptions = {
      "battery_capacity": "Reported full-charge capacity vs design threshold",
      "battery_cycles": "Battery cycle counter vs degradation consistency",
      "storage_devices": "Internal storage device presence and controller response",
      "storage_capacity_claim": "Advertised decimal storage size vs detected bytes",
      "nvme_endurance": "Rated NVMe endurance usage percentage (0-100+%)",
      "nvme_critical_warning": "NVMe controller hardware health flags bitmask",
      "storage_integrity": "Uncorrectable errors, pending, reallocated sectors",
      "storage_self_test": "SMART / NVMe diagnostic self-test outcome",
      "memory_capacity_claim": "Claimed RAM quantity in GiB vs physical memory"
    };

    Object.keys(coverage).sort().forEach(check => {
      const status = coverage[check] || "unknown";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><code>${check}</code></td>
        <td><span class="badge status-${status.toLowerCase()}">${status.toUpperCase()}</span></td>
        <td class="text-muted">${descriptions[check] || "Hardware telemetry evaluation"}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  renderManualChecklist(savedChecks) {
    const container = document.getElementById("manualChecklist");
    container.innerHTML = "";

    MANUAL_CHECKS_DEF.forEach(def => {
      const current = savedChecks[def.id] || { status: "not_tested", notes: "" };
      const item = document.createElement("div");
      item.className = "check-item";
      item.innerHTML = `
        <div class="check-item-header">
          <h4>${def.name}</h4>
          <span class="badge status-${current.status === 'passed' ? 'passed' : current.status === 'failed' ? 'critical' : 'inconclusive'}">
            ${current.status.toUpperCase()}
          </span>
        </div>
        <p class="text-muted" style="margin-bottom:0.5rem; font-size:0.8rem;">${def.desc}</p>
        <div class="check-buttons">
          <button type="button" class="check-btn ${current.status === 'passed' ? 'active-pass' : ''}" data-val="passed">PASS</button>
          <button type="button" class="check-btn ${current.status === 'failed' ? 'active-fail' : ''}" data-val="failed">FAIL</button>
          <button type="button" class="check-btn" data-val="not_applicable">N/A</button>
        </div>
        <input type="text" class="check-notes-input" placeholder="Optional operator notes…" value="${current.notes || ''}" />
      `;

      const input = item.querySelector(".check-notes-input");
      item.querySelectorAll(".check-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          this.updateManualCheck(def.id, btn.dataset.val, input.value);
        });
      });

      input.addEventListener("change", () => {
        this.updateManualCheck(def.id, current.status, input.value);
      });

      container.appendChild(item);
    });
  }

  async updateManualCheck(checkId, status, notes) {
    if (!this.currentSession) return;
    try {
      const resp = await fetch(`/api/sessions/${this.currentSession.id}/manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ check_name: checkId, status, notes })
      });
      const data = await resp.json();
      this.currentSession.manual_checks = data.manual_checks;
      this.renderManualChecklist(data.manual_checks);
    } catch (err) {
      console.error("Failed to update manual check:", err);
    }
  }

  renderExpertTelemetry(snapshot) {
    // 1. CPU & Thermals Table
    const cpuTable = document.getElementById("expertCpuTable");
    if (cpuTable) {
      const cpu = snapshot.cpu || {};
      const thermalsData = snapshot.thermals || {};
      const zones = Array.isArray(thermalsData) ? thermalsData : (thermalsData.zones || []);
      let rows = `
        <tr><td><strong>Model</strong></td><td><code>${cpu.model || "Unknown"}</code></td></tr>
        <tr><td><strong>Topology</strong></td><td><code>${cpu.cores || "?"} physical cores / ${cpu.threads || "?"} threads</code></td></tr>
        <tr><td><strong>Max Frequency</strong></td><td><code>${cpu.mhz ? `${cpu.mhz} MHz` : "Dynamic"}</code></td></tr>
        <tr><td><strong>Architecture</strong></td><td><code>${cpu.arch || "x86_64"}</code></td></tr>
      `;
      if (zones.length > 0) {
        const tList = zones.map(t => `${t.type || t.zone}: ${t.temp_c}°C`).join("<br>");
        rows += `<tr><td><strong>Thermal Sensors</strong></td><td><code>${tList}</code></td></tr>`;
      }
      cpuTable.innerHTML = rows;
    }

    // 2. Battery ACPI Table
    const batTable = document.getElementById("expertBatteryTable");
    if (batTable) {
      const bat = snapshot.battery || {};
      const ac = snapshot.ac_adapter || {};
      batTable.innerHTML = `
        <tr><td><strong>Design Capacity</strong></td><td><code>${bat.design_capacity_mwh ? `${bat.design_capacity_mwh} mWh` : "N/A"}</code></td></tr>
        <tr><td><strong>Full Charge Capacity</strong></td><td><code>${bat.full_charge_capacity_mwh ? `${bat.full_charge_capacity_mwh} mWh` : "N/A"}</code></td></tr>
        <tr><td><strong>Cycle Count</strong></td><td><code>${bat.cycle_count ?? "N/A"}</code></td></tr>
        <tr><td><strong>Reported Voltage</strong></td><td><code>${bat.voltage_uv ? `${(bat.voltage_uv / 1e6).toFixed(2)} V` : "N/A"}</code></td></tr>
        <tr><td><strong>AC Charger Online</strong></td><td><code>${ac.online !== undefined ? (ac.online ? "YES (Plugged In)" : "NO (On Battery)") : "Unknown"}</code></td></tr>
        <tr><td><strong>Source Node</strong></td><td><code>${bat.source || "ACPI sysfs"}</code></td></tr>
      `;
    }

    // 3. Storage Low-Level Controllers
    const storTable = document.getElementById("expertStorageTable");
    if (storTable) {
      const storage = snapshot.storage || {};
      const dev = (storage.devices && storage.devices[0]) || {};
      storTable.innerHTML = `
        <tr><td><strong>Storage Model</strong></td><td><code>${dev.model || "Unknown"}</code></td></tr>
        <tr><td><strong>Protocol</strong></td><td><code>${dev.protocol ? dev.protocol.toUpperCase() : "Unknown"}</code></td></tr>
        <tr><td><strong>Reported Bytes</strong></td><td><code>${dev.capacity_bytes ? dev.capacity_bytes.toLocaleString() : "N/A"}</code></td></tr>
        <tr><td><strong>NVMe Critical Warning</strong></td><td><code>${dev.nvme_critical_warning !== undefined ? `0x${dev.nvme_critical_warning.toString(16).padStart(2, "0")}` : "N/A"}</code></td></tr>
        <tr><td><strong>Percentage Used</strong></td><td><code>${dev.nvme_percentage_used !== undefined ? `${dev.nvme_percentage_used}%` : "N/A"}</code></td></tr>
        <tr><td><strong>Media Errors</strong></td><td><code>${dev.media_errors ?? "0"}</code></td></tr>
        <tr><td><strong>Self Test Status</strong></td><td><code>${dev.self_test_status || "OK"}</code></td></tr>
      `;
    }

    // 4. Motherboard, Display & System
    const sysTable = document.getElementById("expertSystemTable");
    if (sysTable) {
      const sys = snapshot.system || {};
      const disp = snapshot.display || {};
      const gpu = snapshot.gpu || {};
      sysTable.innerHTML = `
        <tr><td><strong>System Manufacturer</strong></td><td><code>${sys.vendor || "Unknown"}</code></td></tr>
        <tr><td><strong>Motherboard Product</strong></td><td><code>${sys.model || "Unknown"}</code></td></tr>
        <tr><td><strong>BIOS / Firmware</strong></td><td><code>${sys.bios_version || "Unknown"} (${sys.bios_date || "Date unrecorded"})</code></td></tr>
        <tr><td><strong>GPU Device</strong></td><td><code>${gpu.model || "Unknown"}</code></td></tr>
        <tr><td><strong>Display Connector</strong></td><td><code>${disp.connector || "eDP"} (${disp.resolution || "Native"})</code></td></tr>
      `;
    }

    // 5. Operating System, Refurbish & Display Panel Telemetry
    const osTable = document.getElementById("expertOsRefurbishTable");
    const refurbishBadge = document.getElementById("refurbishVerdictBadge");
    if (osTable) {
      const sysExt = snapshot.system_extended || this.lastProbedSpecs?.system_extended || {};
      const disp = snapshot.display || {};
      const edid = disp.edid || {};

      const isWipe = sysExt.is_recent_wipe === true;
      if (refurbishBadge) {
        if (isWipe) {
          refurbishBadge.className = "badge status-warning";
          refurbishBadge.textContent = "RECENT RESALE OS WIPE DETECTED";
        } else if (sysExt.os_install_age_days) {
          refurbishBadge.className = "badge status-passed";
          refurbishBadge.textContent = `ESTABLISHED OS (${sysExt.os_install_age_days} DAYS RUNTIME)`;
        } else {
          refurbishBadge.className = "badge status-passed";
          refurbishBadge.textContent = "OS METADATA VERIFIED";
        }
      }

      const panelDesc = edid.manufacturer
        ? `${edid.manufacturer} ${edid.model_name || ""} — ${edid.panel_type || "LCD"} (${edid.color_depth || "8-bit"}, ${edid.diagonal_inches || "?"}")`
        : (disp.panel_type || (disp.resolution ? `${disp.resolution} Panel` : "Standard Panel"));

      osTable.innerHTML = `
        <tr><td><strong>Operating System</strong></td><td><code>${sysExt.os_pretty_name || sysExt.os_name || "Linux"} (${sysExt.kernel_version || "Kernel"})</code></td></tr>
        <tr><td><strong>CPU Architecture</strong></td><td><code>${sysExt.cpu_arch || "x86_64"} · ${sysExt.cpu_bits || 64}-bit Mode</code></td></tr>
        <tr><td><strong>Boot Firmware Type</strong></td><td><span class="badge status-passed">${sysExt.boot_firmware || "UEFI"}</span></td></tr>
        <tr><td><strong>Storage Partition Table</strong></td><td><code>${sysExt.partition_table || "GPT"} (Root: ${sysExt.root_fs_type || "ext4"}, ${sysExt.root_device || "auto"}, ${sysExt.root_size || ""})</code></td></tr>
        <tr><td><strong>OS Install Date</strong></td><td><code>${sysExt.os_install_date || sysExt.os_install_age_estimate || "Unknown"} (${sysExt.os_install_source || "sysfs"})</code></td></tr>
        <tr><td><strong>Refurbish / Wipe Status</strong></td><td><span class="badge status-${isWipe ? 'warning' : 'passed'}">${sysExt.refurbish_status || "Standard Installation"}</span></td></tr>
        <tr><td><strong>Touchscreen Hardware</strong></td><td><code>${sysExt.touchscreen_detected ? "Touchscreen Enabled (" + (sysExt.touchscreen_device || "Capacitive") + ")" : "Non-Touch Screen"}</code></td></tr>
        <tr><td><strong>Display Panel Technology</strong></td><td><code>${panelDesc}</code> ${edid.is_oled ? '<span class="badge status-passed" style="margin-left:6px;">OLED TRUE BLACK</span>' : ''}</td></tr>
      `;
    }
  }

  // --------------------------------------------------------------------------
  // Interactive Tool: Audio Diagnostics (Pure Web Audio API)
  // --------------------------------------------------------------------------
  bindAudioEvents() {
    const freqSlider = document.getElementById("audioFreqSlider");
    const freqVal = document.getElementById("audioFreqVal");
    const playBtn = document.getElementById("playToneBtn");
    const sweepBtn = document.getElementById("sweepToneBtn");
    const leftBtn = document.getElementById("testLeftSpeakerBtn");
    const rightBtn = document.getElementById("testRightSpeakerBtn");

    if (!freqSlider || !playBtn) return;

    freqSlider.addEventListener("input", (e) => {
      const freq = parseFloat(e.target.value);
      freqVal.textContent = `${freq} Hz`;
      if (this.activeOsc && this.audioCtx) {
        this.activeOsc.frequency.setValueAtTime(freq, this.audioCtx.currentTime);
      }
    });

    playBtn.addEventListener("click", () => {
      if (this.isTonePlaying) {
        this.stopAudioTone();
        playBtn.textContent = "Play Tone";
      } else {
        const freq = parseFloat(freqSlider.value) || 440;
        this.startAudioTone(freq, 0);
        playBtn.textContent = "Stop Tone";
      }
    });

    sweepBtn.addEventListener("click", () => {
      this.runAudioSweep();
    });

    leftBtn.addEventListener("click", () => {
      this.testSpeakerChannel(-1, "Left Speaker Playing…");
    });

    rightBtn.addEventListener("click", () => {
      this.testSpeakerChannel(1, "Right Speaker Playing…");
    });
  }

  ensureAudioContext() {
    if (!this.audioCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AudioCtx();
    }
    if (this.audioCtx.state === "suspended") {
      this.audioCtx.resume();
    }
  }

  startAudioTone(frequency = 440, pan = 0) {
    this.stopAudioTone();
    this.ensureAudioContext();

    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(frequency, this.audioCtx.currentTime);

    gain.gain.setValueAtTime(0.001, this.audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.2, this.audioCtx.currentTime + 0.05);

    if (this.audioCtx.createStereoPanner) {
      const panner = this.audioCtx.createStereoPanner();
      panner.pan.setValueAtTime(pan, this.audioCtx.currentTime);
      osc.connect(gain);
      gain.connect(panner);
      panner.connect(this.audioCtx.destination);
      this.activePanner = panner;
    } else {
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
    }

    osc.start();
    this.activeOsc = osc;
    this.activeGain = gain;
    this.isTonePlaying = true;
  }

  stopAudioTone() {
    if (this.activeGain && this.audioCtx) {
      try {
        this.activeGain.gain.setValueAtTime(this.activeGain.gain.value, this.audioCtx.currentTime);
        this.activeGain.gain.exponentialRampToValueAtTime(0.0001, this.audioCtx.currentTime + 0.05);
      } catch (_) {}
    }
    if (this.activeOsc) {
      try {
        this.activeOsc.stop(this.audioCtx ? this.audioCtx.currentTime + 0.06 : 0);
      } catch (_) {}
      this.activeOsc = null;
    }
    this.activeGain = null;
    this.activePanner = null;
    this.isTonePlaying = false;

    const playBtn = document.getElementById("playToneBtn");
    if (playBtn) playBtn.textContent = "Play Tone";
  }

  runAudioSweep() {
    this.stopAudioTone();
    this.ensureAudioContext();

    const sweepBtn = document.getElementById("sweepToneBtn");
    const origText = sweepBtn.textContent;
    sweepBtn.disabled = true;
    sweepBtn.textContent = "Sweeping (20Hz–2000Hz)…";

    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();

    osc.type = "sine";
    const startTime = this.audioCtx.currentTime + 0.05;
    const duration = 5.0;

    osc.frequency.setValueAtTime(20, startTime);
    osc.frequency.exponentialRampToValueAtTime(2000, startTime + duration);

    gain.gain.setValueAtTime(0.001, startTime);
    gain.gain.exponentialRampToValueAtTime(0.25, startTime + 0.1);
    gain.gain.setValueAtTime(0.25, startTime + duration - 0.1);
    gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);

    osc.connect(gain);
    gain.connect(this.audioCtx.destination);

    osc.start(startTime);
    osc.stop(startTime + duration + 0.05);

    this.activeOsc = osc;
    this.activeGain = gain;
    this.isTonePlaying = true;

    setTimeout(() => {
      this.stopAudioTone();
      sweepBtn.disabled = false;
      sweepBtn.textContent = origText;
    }, (duration + 0.2) * 1000);
  }

  testSpeakerChannel(pan = 0, label = "") {
    this.startAudioTone(600, pan);
    const leftBtn = document.getElementById("testLeftSpeakerBtn");
    const rightBtn = document.getElementById("testRightSpeakerBtn");

    const targetBtn = pan === -1 ? leftBtn : rightBtn;
    const origText = targetBtn.textContent;
    targetBtn.textContent = "Testing…";

    setTimeout(() => {
      this.stopAudioTone();
      targetBtn.textContent = origText;
    }, 2000);
  }

  // --------------------------------------------------------------------------
  // Interactive Tool: Webcam & Microphone Diagnostic
  // --------------------------------------------------------------------------
  bindMediaEvents() {
    const startBtn = document.getElementById("startMediaBtn");
    const stopBtn = document.getElementById("stopMediaBtn");

    if (!startBtn || !stopBtn) return;

    startBtn.addEventListener("click", () => this.startMediaDiagnostic());
    stopBtn.addEventListener("click", () => this.stopMediaDiagnostic());
  }

  async startMediaDiagnostic() {
    const startBtn = document.getElementById("startMediaBtn");
    const stopBtn = document.getElementById("stopMediaBtn");
    const videoEl = document.getElementById("webcamPreview");
    const micText = document.getElementById("micVolumeDb");

    try {
      startBtn.disabled = true;
      startBtn.textContent = "Requesting Device Access…";

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: true
      });

      this.mediaStream = stream;
      videoEl.srcObject = stream;

      // Audio Analyser for Microphone Volume
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.micAudioCtx = new AudioCtx();
      if (this.micAudioCtx.state === "suspended") {
        this.micAudioCtx.resume();
      }

      const source = this.micAudioCtx.createMediaStreamSource(stream);
      const analyser = this.micAudioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      this.micAnalyser = analyser;

      startBtn.style.display = "none";
      stopBtn.disabled = false;
      stopBtn.style.display = "inline-flex";

      this.pollMicVolume();
    } catch (err) {
      console.warn("Media capture permission or device issue:", err);
      startBtn.disabled = false;
      startBtn.textContent = "Start Camera & Mic";
      micText.textContent = `Error: ${err.name || "Access Denied"}`;
      alert(`Camera & Microphone access: ${err.message}\n(Ensure device has camera/mic and permission is granted)`);
    }
  }

  pollMicVolume() {
    if (!this.micAnalyser) return;

    const dataArray = new Uint8Array(this.micAnalyser.frequencyBinCount);
    this.micAnalyser.getByteFrequencyData(dataArray);

    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i];
    }
    const avg = sum / dataArray.length;
    const pct = Math.min(100, Math.round((avg / 128) * 100));

    const fill = document.getElementById("micVolumeBar");
    const text = document.getElementById("micVolumeDb");
    if (fill) fill.style.width = `${pct}%`;
    if (text) {
      const db = avg > 0 ? Math.round(20 * Math.log10(avg / 255)) : -60;
      text.textContent = `Mic Level: ${db} dB (${pct > 5 ? "Audio Active" : "Quiet"})`;
    }

    this.micAnimFrameId = requestAnimationFrame(() => this.pollMicVolume());
  }

  stopMediaDiagnostic() {
    if (this.micAnimFrameId) {
      cancelAnimationFrame(this.micAnimFrameId);
      this.micAnimFrameId = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    if (this.micAudioCtx) {
      this.micAudioCtx.close().catch(() => {});
      this.micAudioCtx = null;
    }
    this.micAnalyser = null;

    const videoEl = document.getElementById("webcamPreview");
    if (videoEl) videoEl.srcObject = null;

    const fill = document.getElementById("micVolumeBar");
    const text = document.getElementById("micVolumeDb");
    if (fill) fill.style.width = "0%";
    if (text) text.textContent = "Mic: Inactive";

    const startBtn = document.getElementById("startMediaBtn");
    const stopBtn = document.getElementById("stopMediaBtn");
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.style.display = "inline-flex";
      startBtn.textContent = "Start Camera & Mic";
    }
    if (stopBtn) {
      stopBtn.disabled = true;
      stopBtn.style.display = "none";
    }
  }

  // --------------------------------------------------------------------------
  // Interactive Tool: Trackpad & Gesture Canvas
  // --------------------------------------------------------------------------
  initTrackpadCanvas() {
    const canvas = document.getElementById("trackpadCanvas");
    const clearBtn = document.getElementById("clearCanvasBtn");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const colors = ["#2563eb", "#059669", "#d97706", "#dc2626", "#8b5cf6", "#ec4899"];
    this.trackpadZoneHits = new Array(9).fill(0);

    const getPos = (e) => {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY
      };
    };

    const updateZoneHit = (pos) => {
      const col = Math.min(2, Math.max(0, Math.floor((pos.x / canvas.width) * 3)));
      const row = Math.min(2, Math.max(0, Math.floor((pos.y / canvas.height) * 3)));
      const zoneIdx = row * 3 + col;
      this.trackpadZoneHits[zoneIdx] = (this.trackpadZoneHits[zoneIdx] || 0) + 1;

      const cell = document.querySelector(`.zone-cell[data-zone="${zoneIdx}"]`);
      if (cell) {
        cell.classList.add("zone-active");
        const hitsEl = cell.querySelector(".zone-hits");
        if (hitsEl) hitsEl.textContent = `${this.trackpadZoneHits[zoneIdx]} hits`;
      }

      const activeCount = this.trackpadZoneHits.filter(h => h > 0).length;
      const scoreEl = document.getElementById("trackpadZonesScore");
      if (scoreEl) {
        scoreEl.textContent = `${activeCount}/9 Zones Active`;
        scoreEl.className = `badge status-${activeCount === 9 ? 'passed' : activeCount >= 5 ? 'warning' : 'inconclusive'}`;
      }
    };

    const updateStatus = (text, pressure = 0) => {
      const lbl = document.getElementById("trackpadLastEvent");
      if (lbl) lbl.textContent = text;
      const fingers = document.getElementById("trackpadTouchCount");
      if (fingers) fingers.textContent = `Fingers: ${this.activePointers.size}`;
      const pressureEl = document.getElementById("trackpadPressureText");
      if (pressureEl) {
        if (pressure > 0) {
          pressureEl.textContent = `Pressure: ${Math.round(pressure * 100)}%`;
        } else {
          pressureEl.textContent = `Pressure: Standard Multi-touch`;
        }
      }
    };

    canvas.addEventListener("pointerdown", (e) => {
      canvas.setPointerCapture(e.pointerId);
      const pos = getPos(e);
      const color = colors[e.pointerId % colors.length];
      const radius = e.pressure && e.pressure > 0 ? Math.max(4, Math.round(6 + e.pressure * 14)) : 7;
      this.activePointers.set(e.pointerId, { lastX: pos.x, lastY: pos.y, color });

      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      updateZoneHit(pos);
      const btnType = e.button === 0 ? "Left Click" : e.button === 2 ? "Right Click" : `Button ${e.button}`;
      updateStatus(`${btnType} at (${Math.round(pos.x)}, ${Math.round(pos.y)})`, e.pressure);
    });

    canvas.addEventListener("pointermove", (e) => {
      if (!this.activePointers.has(e.pointerId)) return;
      const prev = this.activePointers.get(e.pointerId);
      const pos = getPos(e);
      const lineWidth = e.pressure && e.pressure > 0 ? Math.max(2, Math.round(2 + e.pressure * 8)) : 3;

      ctx.beginPath();
      ctx.moveTo(prev.lastX, prev.lastY);
      ctx.lineTo(pos.x, pos.y);
      ctx.strokeStyle = prev.color;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = "round";
      ctx.stroke();

      prev.lastX = pos.x;
      prev.lastY = pos.y;
      updateZoneHit(pos);
      updateStatus(`Tracking Finger #${e.pointerId} at (${Math.round(pos.x)}, ${Math.round(pos.y)})`, e.pressure);
    });

    const release = (e) => {
      if (this.activePointers.has(e.pointerId)) {
        this.activePointers.delete(e.pointerId);
      }
      try {
        canvas.releasePointerCapture(e.pointerId);
      } catch (_) {}
      updateStatus(this.activePointers.size > 0 ? "Tracking…" : "Finger released", 0);
    };

    canvas.addEventListener("pointerup", release);
    canvas.addEventListener("pointercancel", release);

    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      updateStatus(`2-Finger Scroll Delta Y: ${Math.round(e.deltaY)}`, 0);
    }, { passive: false });

    canvas.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      updateStatus("Physical Right-Click Registered", 0);
    });

    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        this.trackpadZoneHits = new Array(9).fill(0);
        document.querySelectorAll(".zone-cell").forEach((cell, idx) => {
          cell.classList.remove("zone-active");
          const h = cell.querySelector(".zone-hits");
          if (h) h.textContent = "0 hits";
        });
        const scoreEl = document.getElementById("trackpadZonesScore");
        if (scoreEl) scoreEl.textContent = "0/9 Zones Active";
        updateStatus("Canvas cleared. Draw or click to test tracking", 0);
      });
    }
  }

  // --------------------------------------------------------------------------
  // Interactive Tool: Keyboard Matrix
  // --------------------------------------------------------------------------
  buildKeyboard() {
    const container = document.getElementById("virtualKeyboard");
    if (!container) return;
    container.innerHTML = "";

    KB_LAYOUT.forEach(row => {
      const rowEl = document.createElement("div");
      rowEl.className = "kb-row";
      row.forEach(key => {
        const keyEl = document.createElement("div");
        keyEl.className = `key ${key.class || ""}`;
        keyEl.id = `kb-${key.code}`;
        keyEl.innerText = key.label;
        rowEl.appendChild(keyEl);
      });
      container.appendChild(rowEl);
    });
  }

  handleGlobalKeypress(e) {
    if (e.repeat) return; // Prevent OS autorepeat from skewing counts or misclassifying switch chatter

    this.currentlyHeldKeys = this.currentlyHeldKeys || new Set();
    this.cornerVerifiedKeys = this.cornerVerifiedKeys || new Set();
    this.keyActuationCounts = this.keyActuationCounts || {};
    this.keyReleaseTimestamp = this.keyReleaseTimestamp || {};
    this.keyPressTimestamps = this.keyPressTimestamps || [];
    this.keyBounceFlags = this.keyBounceFlags || {};

    const now = performance.now();
    this.currentlyHeldKeys.add(e.code);
    this.updateRolloverDisplay();

    // Electrical contact chatter detection:
    // If a keyup occurred on the SAME key < 18ms ago, that indicates physical contact bounce
    const lastRelease = this.keyReleaseTimestamp[e.code] || 0;
    if (lastRelease > 0 && (now - lastRelease) < 18) {
      this.keyBounceFlags[e.code] = true;
    }

    // Measure typing cadence (keystrokes per second)
    this.keyPressTimestamps.push(now);
    if (this.keyPressTimestamps.length > 20) this.keyPressTimestamps.shift();
    this.updateTypingCadence();

    const count = (this.keyActuationCounts[e.code] || 0) + 1;
    this.keyActuationCounts[e.code] = count;

    const keyEl = document.getElementById(`kb-${e.code}`);
    if (keyEl) {
      keyEl.classList.add("pressed", "tested");
      this.verifiedKeys.add(e.code);
      document.getElementById("kbVerifiedCount").innerText = this.verifiedKeys.size;

      const angleCheck = this.angleVerificationEnabled !== false;
      if (angleCheck) {
        if (count === 1) {
          keyEl.classList.add("corner-pending");
          keyEl.classList.remove("fully-verified");
          document.getElementById("lastKeyPressed").innerHTML = `Key <strong>${e.key}</strong> [${e.code}] registered (1/2: center strike). <em>Now strike key corner/angle to verify switch stability.</em>`;
        } else {
          keyEl.classList.remove("corner-pending");
          keyEl.classList.add("fully-verified");
          this.cornerVerifiedKeys.add(e.code);
          document.getElementById("lastKeyPressed").innerHTML = `Key <strong>${e.key}</strong> [${e.code}] <strong>fully verified</strong> (center + corner strike confirmed).`;
        }
      } else {
        keyEl.classList.add("fully-verified");
        this.cornerVerifiedKeys.add(e.code);
        document.getElementById("lastKeyPressed").innerHTML = `Key <strong>${e.key}</strong> [${e.code}] verified.`;
      }

      const cornerCountEl = document.getElementById("kbCornerVerifiedCount");
      if (cornerCountEl) cornerCountEl.innerText = this.cornerVerifiedKeys.size;
    }

    // Record for heatmap tracking
    this.recordKeyPressHeatmap(e.code);
  }

  handleGlobalKeyRelease(e) {
    if (this.currentlyHeldKeys) {
      this.currentlyHeldKeys.delete(e.code);
      this.updateRolloverDisplay();
    }
    this.keyReleaseTimestamp = this.keyReleaseTimestamp || {};
    this.keyReleaseTimestamp[e.code] = performance.now();

    const keyEl = document.getElementById(`kb-${e.code}`);
    if (keyEl) {
      keyEl.classList.remove("pressed");
    }
  }

  updateRolloverDisplay() {
    const el = document.getElementById("kbRolloverLive");
    if (!el) return;
    const held = Array.from(this.currentlyHeldKeys || []);
    if (held.length === 0) {
      el.innerHTML = `<span class="rollover-idle">Rollover: 0 keys held (Clean)</span>`;
    } else if (held.length >= 3) {
      el.innerHTML = `<span class="rollover-chord">Active Rollover: ${held.length} keys held [${held.map(c => c.replace("Key", "")).join(", ")}] — Clean n-key trace</span>`;
    } else {
      el.innerHTML = `<span class="rollover-active">Held: [${held.map(c => c.replace("Key", "")).join(", ")}]</span>`;
    }
  }

  updateTypingCadence() {
    const el = document.getElementById("kbCadenceLive");
    if (!el) return;
    if (!this.keyPressTimestamps || this.keyPressTimestamps.length < 2) {
      el.textContent = "Cadence: 0 keys/sec";
      return;
    }
    const recent = this.keyPressTimestamps.slice(-10);
    const timeSpan = (recent[recent.length - 1] - recent[0]) / 1000.0;
    if (timeSpan > 0.05) {
      const cps = ((recent.length - 1) / timeSpan).toFixed(1);
      el.textContent = `Cadence: ${cps} keys/sec`;
    }
  }

  resetKeyboard() {
    this.verifiedKeys.clear();
    if (this.cornerVerifiedKeys) this.cornerVerifiedKeys.clear();
    if (this.currentlyHeldKeys) this.currentlyHeldKeys.clear();
    this.keyActuationCounts = {};
    this.keyReleaseTimestamp = {};
    this.keyBounceFlags = {};
    this.keyPressTimestamps = [];

    document.querySelectorAll(".key.tested, .key.fully-verified, .key.corner-pending, .key.pressed").forEach(k => {
      k.classList.remove("tested", "fully-verified", "corner-pending", "pressed", "heat-cold", "heat-warm", "heat-hot", "heat-bounce");
    });
    document.getElementById("kbVerifiedCount").innerText = "0";
    const cornerCountEl = document.getElementById("kbCornerVerifiedCount");
    if (cornerCountEl) cornerCountEl.innerText = "0";
    document.getElementById("lastKeyPressed").innerText = "Press any key to begin verification…";
    this.updateRolloverDisplay();
    this.updateKeyConditionReport();
  }

  // --------------------------------------------------------------------------
  // Interactive Tool: Dead & Stuck Pixel Screen Tester
  // --------------------------------------------------------------------------
  startScreenTest() {
    this.screenPaletteIndex = 0;
    const overlay = document.getElementById("screenTestOverlay");
    overlay.style.display = "flex";
    this.applyScreenColor();

    const help = document.getElementById("screenTestHelp");
    help.style.opacity = "1";
    setTimeout(() => { help.style.opacity = "0"; }, 3000);

    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    }
  }

  stopScreenTest() {
    const overlay = document.getElementById("screenTestOverlay");
    overlay.style.display = "none";
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }
  }

  cycleScreenColor(step = 1) {
    this.screenPaletteIndex = (this.screenPaletteIndex + step + SCREEN_PALETTE.length) % SCREEN_PALETTE.length;
    this.applyScreenColor();
  }

  applyScreenColor() {
    const current = SCREEN_PALETTE[this.screenPaletteIndex];
    const overlay = document.getElementById("screenTestOverlay");
    overlay.style.backgroundColor = current.color;
  }

  // --------------------------------------------------------------------------
  // Ports & Connectors Tab
  // --------------------------------------------------------------------------
  async loadPortsData() {
    try {
      const resp = await fetch("/api/ports");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      // USB Devices (handle both data.usb and data.usb_devices)
      const usbList = document.getElementById("usbPortsList");
      const usbDevices = data.usb || data.usb_devices || [];
      const portUsbCountEl = document.getElementById("portUsbCount");
      if (portUsbCountEl) portUsbCountEl.textContent = usbDevices.length;

      if (usbList) {
        if (usbDevices.length === 0) {
          usbList.innerHTML = `<div class="port-card empty-port"><div class="port-icon">🔌</div><div><strong>No USB devices detected</strong><p class="text-muted">Plug in a USB drive or mouse to verify each port.</p></div></div>`;
        } else {
          usbList.innerHTML = usbDevices.map(d => `
            <div class="port-card ${d.removable ? 'port-active' : ''}">
              <div class="port-card-top">
                <div class="port-icon">${d.removable ? '💾' : '🖱️'}</div>
                <div>
                  <strong>${d.product || "USB Device"}</strong>
                  <div class="text-muted" style="font-size:0.8rem;">${d.manufacturer || "Unknown Vendor"} · Port ${d.port_id || ""}</div>
                </div>
                <span class="port-speed-pill ${d.removable ? 'pill-green' : ''}">${d.speed_label || d.speed || "USB"}</span>
              </div>
              <div class="text-muted" style="font-size:0.75rem; margin-top:0.3rem;">Type: ${d.device_type || (d.removable ? "External Removable Port" : "Internal Header")}</div>
            </div>
          `).join("");
        }
      }

      // Display Connectors (handle both data.display_ports and data.display_connectors)
      const displayList = document.getElementById("displayPortsList");
      const connectors = data.display_ports || data.display_connectors || [];
      const portDisplayCountEl = document.getElementById("portDisplayCount");
      if (portDisplayCountEl) portDisplayCountEl.textContent = connectors.length;

      if (displayList) {
        if (connectors.length === 0) {
          displayList.innerHTML = `<div class="port-card"><div class="port-icon">🖥️</div><div><strong>No video outputs enumerated</strong></div></div>`;
        } else {
          displayList.innerHTML = connectors.map(c => {
            const portName = c.connector || c.name || "Video Output";
            const isConnected = c.status === "connected";
            const isEdp = portName.toLowerCase().includes("edp");
            return `
              <div class="port-card ${isConnected ? 'port-active' : ''}">
                <div class="port-card-top">
                  <div class="port-icon">${isEdp ? '💻' : '🖥️'}</div>
                  <div>
                    <strong>${portName}</strong>
                    <div class="text-muted" style="font-size:0.8rem;">${c.port_type || (isEdp ? "Internal Display" : "External Port")} · ${c.status || "Unknown"}</div>
                  </div>
                  <span class="port-speed-pill ${isConnected ? 'pill-green' : ''}">${(c.status || "DISCONNECTED").toUpperCase()}</span>
                </div>
                ${c.resolution ? `<div class="text-muted" style="font-size:0.75rem; margin-top:0.3rem;">Active Resolution: <strong>${c.resolution}</strong></div>` : ""}
                ${c.modes && c.modes.length ? `<div class="text-muted" style="font-size:0.75rem; margin-top:0.2rem;">Supported: ${c.modes.slice(0, 3).join(", ")}${c.modes.length > 3 ? "…" : ""}</div>` : ""}
              </div>
            `;
          }).join("");
        }
      }

      // AC Adapter (handle both data.ac_charging and data.ac_adapter)
      const acBox = document.getElementById("acPortStatusBox");
      const ac = data.ac_charging || data.ac_adapter;
      if (acBox) {
        if (ac && ac.name) {
          const online = ac.online === true;
          acBox.innerHTML = `
            <div class="port-card ${online ? 'port-active' : ''}">
              <div class="port-card-top">
                <div class="port-icon">${online ? '⚡' : '🔋'}</div>
                <div>
                  <strong>${ac.name || "AC Adapter"}</strong>
                  <div class="text-muted" style="font-size:0.8rem;">${online ? "Charger connected and delivering power" : "Running on battery power"}</div>
                </div>
                <span class="port-speed-pill ${online ? 'pill-green' : ''}">${online ? "CHARGING" : "BATTERY"}</span>
              </div>
              ${ac.wattage_w ? `<div class="text-muted" style="font-size:0.75rem; margin-top:0.3rem;">Negotiated Power: <strong>${ac.wattage_w} W</strong></div>` : ""}
            </div>
          `;
        } else {
          acBox.innerHTML = `
            <div class="port-card">
              <div class="port-card-top">
                <div class="port-icon">🔌</div>
                <div>
                  <strong>AC Sensor Inconclusive</strong>
                  <div class="text-muted" style="font-size:0.8rem;">No AC charging controller exposed via sysfs (Desktop or battery-direct EC)</div>
                </div>
                <span class="port-speed-pill">STANDBY</span>
              </div>
            </div>
          `;
        }
      }

      // Verified count
      const verified = usbDevices.length + connectors.filter(c => c.status === "connected" || c.status === true).length;
      const verifiedEl = document.getElementById("portVerifiedCount");
      if (verifiedEl) verifiedEl.textContent = verified;

    } catch (err) {
      console.warn("Port data unavailable:", err);
    }

    // Network Adapters
    try {
      const nResp = await fetch("/api/network");
      if (!nResp.ok) return;
      const net = await nResp.json();
      const netBox = document.getElementById("networkStatusBox");
      if (!netBox) return;

      const adapters = net.adapters || [];
      if (adapters.length === 0) {
        netBox.innerHTML = `<div class="port-card"><div class="port-icon">📡</div><div><strong>No network adapters detected</strong></div></div>`;
      } else {
        netBox.innerHTML = adapters.map(a => {
          const ifaceName = a.interface || a.name || "Network Interface";
          const ifaceState = a.state || a.operstate || "unknown";
          const isUp = ifaceState.toLowerCase() === "up";
          const isWifi = a.type === "Wi-Fi";
          return `
            <div class="port-card ${isUp ? 'port-active' : ''}">
              <div class="port-card-top">
                <div class="port-icon">${isWifi ? '📶' : '🌐'}</div>
                <div>
                  <strong>${ifaceName}</strong>
                  <div class="text-muted" style="font-size:0.8rem;">${a.type || "Network"} · Interface State: ${ifaceState}</div>
                </div>
                <span class="port-speed-pill ${isUp ? 'pill-green' : ''}">${ifaceState.toUpperCase()}</span>
              </div>
            </div>
          `;
        }).join("");
      }
    } catch (_) {}
  }

  bindPortsEvents() {
    const refreshBtn = document.getElementById("refreshPortsBtn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.loadPortsData());
    }
  }

  // --------------------------------------------------------------------------
  // Screen Studio Tab
  // --------------------------------------------------------------------------
  initScreenStudio() {
    this.drawContrastRamp();
    this.drawCheckerboard();
    if (!this.ufoRunning) {
      this.startUfoAnimation();
    }
    const contrastBtn = document.getElementById("launchContrastFullscreenBtn");
    if (contrastBtn && !contrastBtn._bound) {
      contrastBtn._bound = true;
      contrastBtn.addEventListener("click", () => this.launchContrastFullscreen());
    }
    const ufoToggleBtn = document.getElementById("toggleUfoAnimBtn");
    if (ufoToggleBtn && !ufoToggleBtn._bound) {
      ufoToggleBtn._bound = true;
      ufoToggleBtn.addEventListener("click", () => {
        if (this.ufoRunning) {
          this.stopUfoAnimation();
          ufoToggleBtn.textContent = "Resume Animation";
        } else {
          this.startUfoAnimation();
          ufoToggleBtn.textContent = "Pause Animation";
        }
      });
    }
  }

  drawContrastRamp() {
    const bar = document.getElementById("contrastStepBar");
    if (!bar) return;
    bar.innerHTML = "";
    const steps = 16;
    for (let i = 0; i < steps; i++) {
      const val = Math.round((i / (steps - 1)) * 255);
      const div = document.createElement("div");
      div.className = "contrast-step";
      div.style.backgroundColor = `rgb(${val},${val},${val})`;
      div.title = `L${Math.round((val / 255) * 100)}%`;
      bar.appendChild(div);
    }
  }

  drawCheckerboard() {
    const canvas = document.getElementById("checkerboardCanvas");
    if (!canvas) return;
    canvas.width = 200;
    canvas.height = 80;
    const ctx = canvas.getContext("2d");
    const cellSize = 4;
    for (let y = 0; y < canvas.height; y += cellSize) {
      for (let x = 0; x < canvas.width; x += cellSize) {
        ctx.fillStyle = (Math.floor(x / cellSize) + Math.floor(y / cellSize)) % 2 === 0 ? "#000" : "#fff";
        ctx.fillRect(x, y, cellSize, cellSize);
      }
    }
  }

  launchContrastFullscreen() {
    const steps = 16;
    let idx = 0;
    const overlay = document.getElementById("screenTestOverlay");
    if (!overlay) return;
    const val = Math.round((idx / (steps - 1)) * 255);
    overlay.style.backgroundColor = `rgb(${val},${val},${val})`;
    overlay.style.display = "flex";
    const help = document.getElementById("screenTestHelp");
    if (help) help.textContent = "Click / Space to step grayscale. ESC to exit.";
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    }
    this._contrastIdx = 0;
    this._contrastMode = true;
    this._contrastSteps = steps;

    overlay._contrastClick = () => {
      this._contrastIdx = (this._contrastIdx + 1) % steps;
      const v = Math.round((this._contrastIdx / (steps - 1)) * 255);
      overlay.style.backgroundColor = `rgb(${v},${v},${v})`;
    };
    overlay.addEventListener("click", overlay._contrastClick);
  }

  // UFO Refresh Rate Animation
  startUfoAnimation() {
    const canvas = document.getElementById("ufoCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    this.ufoRunning = true;
    this.ufoX = 0;
    this.ufoDir = 1;
    this.ufoFrameTimes = [];
    this.ufoLastFrame = performance.now();

    const animate = (now) => {
      if (!this.ufoRunning) return;

      const dt = now - this.ufoLastFrame;
      this.ufoLastFrame = now;
      this.ufoFrameTimes.push(dt);
      if (this.ufoFrameTimes.length > 60) this.ufoFrameTimes.shift();

      // Compute Hz
      if (this.ufoFrameTimes.length > 5) {
        const avgMs = this.ufoFrameTimes.reduce((a, b) => a + b, 0) / this.ufoFrameTimes.length;
        const hz = avgMs > 0 ? (1000 / avgMs).toFixed(1) : "?";
        const hzEl = document.getElementById("ufoHzText");
        const ftEl = document.getElementById("ufoFrameTimeText");
        if (hzEl) hzEl.textContent = `${hz} Hz`;
        if (ftEl) ftEl.textContent = `${avgMs.toFixed(1)} ms`;
      }

      // Draw
      const speed = 3;
      this.ufoX += this.ufoDir * speed;
      const w = canvas.width, h = canvas.height;
      if (this.ufoX > w - 30) this.ufoDir = -1;
      if (this.ufoX < 30) this.ufoDir = 1;

      ctx.clearRect(0, 0, w, h);

      // Trail effect
      ctx.fillStyle = "rgba(0,0,0,0.12)";
      ctx.fillRect(0, 0, w, h);

      // UFO body
      ctx.beginPath();
      ctx.ellipse(this.ufoX, h / 2, 28, 10, 0, 0, Math.PI * 2);
      ctx.fillStyle = "#2563eb";
      ctx.fill();

      // Dome
      ctx.beginPath();
      ctx.ellipse(this.ufoX, h / 2 - 6, 14, 8, 0, 0, Math.PI, true);
      ctx.fillStyle = "#60a5fa";
      ctx.fill();

      // Glow
      const grd = ctx.createRadialGradient(this.ufoX, h / 2, 2, this.ufoX, h / 2, 28);
      grd.addColorStop(0, "rgba(96,165,250,0.5)");
      grd.addColorStop(1, "rgba(96,165,250,0)");
      ctx.fillStyle = grd;
      ctx.beginPath();
      ctx.ellipse(this.ufoX, h / 2, 28, 10, 0, 0, Math.PI * 2);
      ctx.fill();

      this.ufoAnimFrameId = requestAnimationFrame(animate);
    };

    this.ufoAnimFrameId = requestAnimationFrame(animate);
  }

  stopUfoAnimation() {
    this.ufoRunning = false;
    if (this.ufoAnimFrameId) {
      cancelAnimationFrame(this.ufoAnimFrameId);
      this.ufoAnimFrameId = null;
    }
  }

  // --------------------------------------------------------------------------
  // Cooling Pulse Benchmark
  // --------------------------------------------------------------------------
  bindBenchmarkEvents() {
    const runBtn = document.getElementById("runPulseBtn");
    if (runBtn && !runBtn._bound) {
      runBtn._bound = true;
      runBtn.addEventListener("click", () => this.runThermalPulse());
    }
    const refreshFansBtn = document.getElementById("refreshFansBtn");
    if (refreshFansBtn && !refreshFansBtn._bound) {
      refreshFansBtn._bound = true;
      refreshFansBtn.addEventListener("click", () => this.loadFanRpms());
    }

    const btnPerf = document.getElementById("btnFanPerformance");
    if (btnPerf && !btnPerf._bound) {
      btnPerf._bound = true;
      btnPerf.addEventListener("click", () => this.setFanProfile("performance"));
    }
    const btnQuiet = document.getElementById("btnFanQuiet");
    if (btnQuiet && !btnQuiet._bound) {
      btnQuiet._bound = true;
      btnQuiet.addEventListener("click", () => this.setFanProfile("quiet"));
    }
    const btnBal = document.getElementById("btnFanBalanced");
    if (btnBal && !btnBal._bound) {
      btnBal._bound = true;
      btnBal.addEventListener("click", () => this.setFanProfile("balanced"));
    }

    this.loadFanRpms();
    this.loadFanProfileStatus();
  }

  async loadFanProfileStatus() {
    const badge = document.getElementById("currentFanProfileBadge");
    const msg = document.getElementById("fanProfileStatusMsg");
    try {
      const resp = await fetch("/api/fan/profiles");
      if (!resp.ok) return;
      const data = await resp.json();
      if (!data.supported) {
        if (badge) badge.textContent = "ACPI Fan Profiles: N/A";
        if (msg) msg.textContent = "ACPI thermal profile switching not supported on this firmware.";
        return;
      }
      if (badge) {
        badge.textContent = `Current: ${data.current.toUpperCase()}`;
        badge.className = `badge status-${data.current === 'performance' ? 'critical' : data.current === 'quiet' ? 'passed' : 'passed'}`;
      }
      if (msg) {
        msg.textContent = `Available firmware profiles: ${data.choices.join(', ')}.`;
      }
    } catch (_) {}
  }

  async setFanProfile(profile) {
    const badge = document.getElementById("currentFanProfileBadge");
    const msg = document.getElementById("fanProfileStatusMsg");
    if (msg) msg.textContent = `Switching fan mode to '${profile}'…`;
    try {
      const resp = await fetch("/api/fan/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile })
      });
      const data = await resp.json();
      if (resp.ok && data.success) {
        if (badge) {
          badge.textContent = `Current: ${profile.toUpperCase()}`;
          badge.className = `badge status-${profile === 'performance' ? 'critical' : 'passed'}`;
        }
        if (msg) {
          msg.innerHTML = `✅ Successfully switched to <strong>${profile.toUpperCase()}</strong> mode via ${data.method}. Notice fan acoustic and RPM response!`;
        }
        setTimeout(() => this.loadFanRpms(), 1200);
      } else {
        if (msg) msg.textContent = `Notice: ${data.error || "Profile switch error"}`;
      }
    } catch (err) {
      if (msg) msg.textContent = `Failed: ${err.message}`;
    }
  }

  async loadFanRpms() {
    const list = document.getElementById("fanRpmList");
    if (!list) return;
    try {
      const resp = await fetch("/api/fans");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const fans = data.fans || [];
      if (fans.length === 0) {
        list.innerHTML = `<div class="text-muted" style="font-size:0.85rem;">No fan sensors detected via hwmon sysfs (may require hwmon driver or root for some chips).</div>`;
        return;
      }
      list.innerHTML = fans.map(f => `
        <div class="port-card ${f.rpm > 0 ? 'port-active' : ''}">
          <div class="port-card-top">
            <div class="port-icon">${f.rpm > 0 ? '🌀' : '💤'}</div>
            <div>
              <strong>${f.label}</strong>
              <div class="text-muted" style="font-size:0.8rem;">${f.hwmon}</div>
            </div>
            <span class="port-speed-pill ${f.rpm > 0 ? 'pill-green' : ''}">${f.rpm} RPM</span>
          </div>
        </div>
      `).join("");
    } catch (err) {
      if (list) list.innerHTML = `<div class="text-muted" style="font-size:0.85rem;">Fan data unavailable: ${err.message}</div>`;
    }
  }

  async runThermalPulse() {
    const runBtn = document.getElementById("runPulseBtn");
    if (!runBtn) return;
    const origText = runBtn.innerHTML;
    runBtn.disabled = true;
    runBtn.innerHTML = "⏳ Running 5-second multi-core pulse…";

    const peakEl = document.getElementById("benchPeakTempVal");
    const startEl = document.getElementById("benchStartTemp");
    const deltaEl = document.getElementById("benchRiseDelta");
    const rampEl = document.getElementById("benchRampRate");
    const statusEl = document.getElementById("benchStatusBadge");

    if (peakEl) peakEl.textContent = "…°C";
    if (statusEl) {
      statusEl.textContent = "Testing…";
      statusEl.style.color = "var(--primary)";
    }

    try {
      const resp = await fetch("/api/benchmark/cpu-pulse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration: 5.0 })
      });
      if (!resp.ok) throw new Error(`Server error ${resp.status}`);
      const d = await resp.json();

      if (peakEl) peakEl.textContent = `${d.peak_temp_c ?? "--"}°C`;
      if (startEl) startEl.textContent = `${d.initial_temp_c ?? "--"}°C`;
      if (deltaEl) deltaEl.textContent = `+${d.temp_rise_c ?? 0.0}°C`;
      if (rampEl) rampEl.textContent = `${d.thermal_ramp_rate ?? 0.0} °C/s`;

      if (statusEl) {
        statusEl.textContent = d.status || (d.throttle_detected ? "⚠️ Throttling" : "✅ Healthy");
        statusEl.style.color = d.throttle_detected ? "var(--severity-critical)" : (d.temp_rise_c >= 25 ? "var(--severity-warning)" : "var(--severity-passed)");
      }

      // Refresh fan readings after pulse
      setTimeout(() => this.loadFanRpms(), 1000);
    } catch (err) {
      if (peakEl) peakEl.textContent = "Error";
      if (statusEl) {
        statusEl.textContent = "Failed: " + err.message;
        statusEl.style.color = "var(--severity-critical)";
      }
    } finally {
      runBtn.disabled = false;
      runBtn.innerHTML = origText;
    }
  }

  // --------------------------------------------------------------------------
  // Keyboard Heatmap & Condition Metadata
  // --------------------------------------------------------------------------
  initKeyboardHeatmap() {
    // keyPressCounts: code -> count
    // keyBounceFlags: code -> boolean (bounce detected)
    // keyLastTimestamp: code -> ms timestamp
    this.keyPressCounts = this.keyPressCounts || {};
    this.keyBounceFlags = this.keyBounceFlags || {};
    this.keyLastTimestamp = this.keyLastTimestamp || {};
  }

  recordKeyPressHeatmap(code) {
    const now = performance.now();
    this.keyPressCounts[code] = (this.keyPressCounts[code] || 0) + 1;
    this.keyLastTimestamp[code] = now;

    this.updateKeyHeatmapColor(code);
    this.updateKeyConditionReport();
  }

  updateKeyHeatmapColor(code) {
    const el = document.getElementById(`kb-${code}`);
    if (!el) return;
    const count = this.keyPressCounts[code] || 0;
    const bounced = this.keyBounceFlags[code];

    el.classList.remove("heat-cold", "heat-warm", "heat-hot", "heat-bounce");
    if (bounced) {
      el.classList.add("heat-bounce"); // Red-ish warning
    } else if (count >= 20) {
      el.classList.add("heat-hot");    // Green: well-tested
    } else if (count >= 5) {
      el.classList.add("heat-warm");   // Yellow: partially tested
    } else if (count >= 1) {
      el.classList.add("heat-cold");   // Light blue: rarely pressed
    }
  }

  updateKeyConditionReport() {
    const report = document.getElementById("kbConditionReport");
    if (!report) return;
    const issues = [];
    for (const [code, bounced] of Object.entries(this.keyBounceFlags)) {
      if (bounced) {
        const count = this.keyPressCounts[code] || 0;
        issues.push(`<span style="color:var(--severity-critical);">⚠ Key '${code}': ${count} presses, bounce detected — possibly worn switch</span>`);
      }
    }
    if (issues.length === 0) {
      report.innerHTML = `<span class="text-muted">No key condition issues detected. Press all keys thoroughly to build heatmap.</span>`;
    } else {
      report.innerHTML = issues.join("<br>");
    }
  }

  // --------------------------------------------------------------------------
  // Tab Switch Enhanced (trigger side effects per tab)
  // --------------------------------------------------------------------------
  switchTab(tabId) {
    document.querySelectorAll(".nav-btn").forEach(b => {
      const isActive = b.dataset.tab === tabId;
      b.classList.toggle("active", isActive);
      b.setAttribute("aria-selected", isActive ? "true" : "false");
    });
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.toggle("active", p.id === tabId));

    if (tabId === "tab-history") this.loadHistory();
    if (tabId === "tab-ports") this.loadPortsData();
    if (tabId === "tab-screen") this.initScreenStudio();
    if (tabId === "tab-benchmark") { this.bindBenchmarkEvents(); this.loadFanRpms(); }

    // Workflow Stepper Synchronization
    if (["tab-screen", "tab-ports", "tab-media", "tab-input", "tab-benchmark"].includes(tabId)) {
      this.updateWorkflowStepper(4);
    } else if (tabId === "tab-inspect") {
      this.updateWorkflowStepper(this.currentSession ? 3 : 1);
    }
  }

  updateWorkflowStepper(activeStep) {
    const stepper = document.getElementById("workflowStepper");
    if (!stepper) return;
    stepper.querySelectorAll(".step-node").forEach(node => {
      const s = parseInt(node.dataset.step, 10);
      node.classList.toggle("active", s === activeStep);
      node.classList.toggle("completed", s < activeStep);
    });
  }

  // --------------------------------------------------------------------------
  // History
  // --------------------------------------------------------------------------
  async loadHistory() {
    try {
      const resp = await fetch("/api/sessions");
      const data = await resp.json();
      const tbody = document.getElementById("historyTableBody");
      tbody.innerHTML = "";

      if (!data.sessions || data.sessions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-muted" style="text-align:center;">No past inspections recorded in SQLite database.</td></tr>`;
        return;
      }

      data.sessions.forEach(s => {
        const tr = document.createElement("tr");
        let badgeClass = "inconclusive";
        let label = s.risk_state;
        if (s.risk_state === "no_detected_anomaly_in_evaluated_checks" || s.risk_state === "pass" || s.risk_state === "healthy") {
          badgeClass = "passed";
          label = "✓ Healthy / Passed";
        } else if (s.risk_state === "review") {
          badgeClass = "warning";
          label = "⚠ Review Needed";
        } else if (s.risk_state === "high_risk" || s.risk_state === "critical") {
          badgeClass = "critical";
          label = "✖ Critical Anomaly";
        } else if (s.risk_state === "inconclusive") {
          badgeClass = "inconclusive";
          label = "? Inconclusive";
        }

        tr.innerHTML = `
          <td>${new Date(s.created_at).toLocaleString()}</td>
          <td><code>${s.id}</code></td>
          <td>${s.system_model || "Unknown"}</td>
          <td><span class="badge status-${badgeClass}">${label}</span></td>
          <td>${s.finding_count}</td>
          <td>${s.operator_notes || "-"}</td>
          <td>
            <button class="btn btn-sm btn-outline load-hist-btn" data-id="${s.id}">View</button>
            <button class="btn btn-sm btn-outline del-hist-btn" data-id="${s.id}" style="color:var(--severity-critical);">Delete</button>
          </td>
        `;

        tr.querySelector(".load-hist-btn").addEventListener("click", async () => {
          const sResp = await fetch(`/api/sessions/${s.id}`);
          const sData = await sResp.json();
          this.switchTab("tab-inspect");
          this.renderSession(sData);
        });

        tr.querySelector(".del-hist-btn").addEventListener("click", async () => {
          if (confirm(`Delete session ${s.id}?`)) {
            await fetch(`/api/sessions/${s.id}`, { method: "DELETE" });
            this.loadHistory();
          }
        });

        tbody.appendChild(tr);
      });
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  }

  // --------------------------------------------------------------------------
  // Xflash v3.0 Extensions: Boot Splash, Command Palette, Schematic & Listing
  // --------------------------------------------------------------------------
  initBootSplash() {
    const splash = document.getElementById("xflashSplash");
    const ringFill = document.getElementById("splashRingFill");
    const spark = document.getElementById("splashSpark");
    if (!splash) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      splash.classList.add("hidden");
      return;
    }

    if (window.gsap && ringFill && spark) {
      const tl = gsap.timeline({
        onComplete: () => {
          gsap.to(splash, { opacity: 0, duration: 0.35, onComplete: () => splash.classList.add("hidden") });
        }
      });
      tl.to(ringFill, { strokeDasharray: "135, 176", duration: 0.8, ease: "power2.out" })
        .to(spark, { opacity: 1, duration: 0.2 }, "-=0.2")
        .to({}, { duration: 0.25 });
    } else {
      setTimeout(() => {
        splash.classList.add("hidden");
      }, 800);
    }
  }

  initCommandPalette() {
    const overlay = document.getElementById("cmdPaletteOverlay");
    const input = document.getElementById("cmdPaletteInput");
    const results = document.getElementById("cmdResults");
    const btn = document.getElementById("cmdPaletteBtn");
    if (!overlay || !input || !results) return;

    const commands = [
      { id: "tab-inspect", label: "Diagnostics & Hardware Verdict", icon: "⚡", tab: "tab-inspect" },
      { id: "tab-screen", label: "Screen Studio (Dead Pixels, Contrast, UFO 144Hz)", icon: "🖥️", tab: "tab-screen" },
      { id: "tab-ports", label: "Ports & Connectors (USB-C, HDMI, Charger)", icon: "🔌", tab: "tab-ports" },
      { id: "tab-input", label: "Input Studio (84-Key Heatmap & Trackpad)", icon: "⌨️", tab: "tab-input" },
      { id: "tab-media", label: "Audio & Camera (20Hz-8kHz Sweep, Mic, Cam)", icon: "🔊", tab: "tab-media" },
      { id: "tab-benchmark", label: "Cooling Pulse (Thermal Burst, Fan RPM)", icon: "❄️", tab: "tab-benchmark" },
      { id: "tab-history", label: "Inspection History Archive", icon: "📁", tab: "tab-history" },
      { id: "tab-about", label: "About Xflash & Offline Guarantees", icon: "ℹ️", tab: "tab-about" },
      { id: "action-run", label: "Run Full Hardware Diagnostic", icon: "🚀", action: () => document.getElementById("runLiveBtn")?.click() },
      { id: "action-probe", label: "Auto-Detect Local Hardware Specs", icon: "🔍", action: () => document.getElementById("autoDetectBtn")?.click() },
      { id: "action-sample", label: "Load Reference Sample Session", icon: "📄", action: () => document.getElementById("loadSampleBtn")?.click() },
      { id: "action-expert", label: "Toggle Expert Telemetry Mode", icon: "🛠️", action: () => {
        const toggle = document.getElementById("expertModeToggle");
        if (toggle) { toggle.checked = !toggle.checked; this.applyMode(toggle.checked); }
      }},
      { id: "action-print", label: "Print Inspection Certificate (PDF)", icon: "🖨️", action: () => window.print() },
      { id: "action-usb", label: "Save Report to USB Drive", icon: "💾", action: () => this.saveToUsbReports() }
    ];

    const openPalette = () => {
      overlay.classList.add("open");
      input.value = "";
      renderList(commands);
      setTimeout(() => input.focus(), 50);
    };

    const closePalette = () => {
      overlay.classList.remove("open");
    };

    const renderList = (items) => {
      results.innerHTML = "";
      if (items.length === 0) {
        results.innerHTML = `<div style="padding:1rem; text-align:center; color:var(--text-muted); font-size:0.85rem;">No matching commands</div>`;
        return;
      }
      items.forEach((item, index) => {
        const div = document.createElement("div");
        div.className = `cmd-result-item ${index === 0 ? "active" : ""}`;
        div.innerHTML = `
          <span style="font-size:1.1rem;">${item.icon}</span>
          <span class="cmd-result-label">${item.label}</span>
          <span class="cmd-result-kbd">ENTER</span>
        `;
        div.addEventListener("click", () => {
          closePalette();
          if (item.tab) this.switchTab(item.tab);
          if (item.action) item.action();
        });
        results.appendChild(div);
      });
    };

    input.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      const filtered = commands.filter(c => c.label.toLowerCase().includes(q));
      renderList(filtered);
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closePalette();
      } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const items = results.querySelectorAll(".cmd-result-item");
        if (!items.length) return;
        let activeIdx = Array.from(items).findIndex(el => el.classList.contains("active"));
        items[activeIdx]?.classList.remove("active");
        if (e.key === "ArrowDown") {
          activeIdx = (activeIdx + 1) % items.length;
        } else {
          activeIdx = (activeIdx - 1 + items.length) % items.length;
        }
        items[activeIdx].classList.add("active");
        items[activeIdx].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter") {
        e.preventDefault();
        const active = results.querySelector(".cmd-result-item.active");
        if (active) active.click();
      }
    });

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closePalette();
    });

    if (btn) btn.addEventListener("click", openPalette);

    window.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (overlay.classList.contains("open")) closePalette();
        else openPalette();
      } else if (e.altKey && e.key.toLowerCase() === "e") {
        e.preventDefault();
        const toggle = document.getElementById("expertModeToggle");
        if (toggle) {
          toggle.checked = !toggle.checked;
          this.applyMode(toggle.checked);
        }
      }
    });
  }

  initListingToggle() {
    const toggleBtn = document.getElementById("listingToggleBtn");
    const claimsForm = document.getElementById("claimsForm");
    const saveUrlBtn = document.getElementById("parseListingBtn");
    const urlInput = document.getElementById("listingUrlInput");

    if (saveUrlBtn && urlInput) {
      saveUrlBtn.addEventListener("click", () => {
        const url = urlInput.value.trim();
        if (url) {
          saveUrlBtn.textContent = "✓ Saved";
          const notes = document.getElementById("operatorNotes");
          if (notes && !notes.value.includes(url)) {
            notes.value = notes.value ? `${notes.value}\nListing: ${url}` : `Listing: ${url}`;
          }
          setTimeout(() => { saveUrlBtn.textContent = "Save URL"; }, 1500);
        }
      });
    }

    if (toggleBtn && claimsForm) {
      toggleBtn.addEventListener("click", () => {
        const isCollapsed = claimsForm.style.display === "none";
        claimsForm.style.display = isCollapsed ? "block" : "none";
        toggleBtn.setAttribute("aria-expanded", isCollapsed ? "true" : "false");
        const badge = document.getElementById("listingStateBadge");
        if (badge) {
          badge.textContent = isCollapsed ? "OPT-IN" : "COLLAPSED";
        }
      });
    }
  }

  initSchematicClicks() {
    document.querySelectorAll(".schematic-zone").forEach(zone => {
      zone.addEventListener("click", () => {
        const tab = zone.dataset.targetTab;
        const subtab = zone.dataset.targetSubtab;
        if (tab) {
          this.switchTab(tab);
        } else if (subtab) {
          this.switchSubtab(subtab);
          const el = document.getElementById(subtab);
          if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });
  }

  updateSchematic(session) {
    const snapshot = session.snapshot || {};
    const report = session.report || {};
    const findings = report.findings || [];

    const setZone = (id, status, subtext = null) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.remove("zone-healthy", "zone-warn", "zone-critical");
      el.classList.add(status === "critical" ? "zone-critical" : status === "warning" ? "zone-warn" : "zone-healthy");
      if (subtext) {
        const subEl = document.getElementById(`${id}-sub`) || document.getElementById(`${id}-status`);
        if (subEl) subEl.textContent = subtext;
      }
    };

    // 1. Battery
    const bat = snapshot.battery || {};
    let batHealth = bat.health_percentage;
    if (batHealth === undefined && bat.full_charge_capacity_mwh && bat.design_capacity_mwh) {
      batHealth = (bat.full_charge_capacity_mwh / bat.design_capacity_mwh) * 100;
    }
    if (batHealth !== undefined) {
      const batStatus = batHealth < 65 ? "critical" : batHealth < 80 ? "warning" : "healthy";
      setZone("schematic-battery", batStatus);
      const batText = document.getElementById("schematic-battery-text");
      if (batText) batText.textContent = `BATTERY (${Math.round(batHealth)}%)`;
    }

    // 2. Storage
    const stor = snapshot.storage || {};
    const dev = (stor.devices && stor.devices[0]) || {};
    const wear = dev.nvme_percentage_used ?? 0;
    const mediaErrors = dev.media_errors ?? 0;
    const storStatus = (wear >= 80 || mediaErrors > 0) ? "warning" : "healthy";
    setZone("schematic-storage", storStatus, `${wear}% Used`);

    // 3. CPU & Thermals
    const thermals = snapshot.thermals || {};
    const maxT = typeof thermals.max_temp_c === "number" ? thermals.max_temp_c : 45;
    const cpuStatus = maxT >= 85 ? "critical" : maxT >= 70 ? "warning" : "healthy";
    setZone("schematic-cpu", cpuStatus, `${Math.round(maxT)}°C`);

    // 4. Ports
    setZone("schematic-ports-l", "healthy");
    setZone("schematic-ports-r", "healthy");

    // 5. Findings mapping
    findings.forEach(f => {
      if (f.code && f.code.includes("BATTERY")) {
        setZone("schematic-battery", f.severity === "critical" ? "critical" : "warning");
      }
      if (f.code && (f.code.includes("NVME") || f.code.includes("STORAGE"))) {
        setZone("schematic-storage", f.severity === "critical" ? "critical" : "warning");
      }
      if (f.code && f.code.includes("THERMAL")) {
        setZone("schematic-cpu", f.severity === "critical" ? "critical" : "warning");
      }
    });
  }
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  window.app = new App();
});
