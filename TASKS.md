# Implementation checklist

Use this as the source-of-truth task list when working with Antigravity. Mark items complete only after evidence exists; do not mark hardware work complete from mocked tests.

## Phase 0 — repository hygiene and prior art
- [x] Read `docs/prior-art.md`; compare the current HWCheck code and license before choosing reuse/fork vs clean-room modules.
- [x] Record project decision in `docs/decision-log.md` with evidence and license implications.
- [x] Verify dependency licensing and maintain zero external runtime dependencies.

## Phase 1 — analysis engine (v1.0.0)
- [x] Create snapshot input example and normalized JSON shape.
- [x] Implement battery degradation and low-cycle/high-degradation flags.
- [x] Implement initial SSD/NVMe health flags.
- [x] Implement advertised-vs-detected RAM comparison.
- [x] Generate JSON/HTML report locally.
- [x] Add tests for normal, anomalous, missing, and implausible input cases.
- [x] Add result coverage records for each individual check.

## Phase 2 — read-only collectors (v1.0.0 & v2.0.0)
- [x] Define `Collector` protocol and `safe_exec` command runner.
- [x] Build Linux battery and device inventory collector with sample-output fixtures.
- [x] Integrate `smartctl -x`/JSON output safely; handle nonzero exit codes and partial results.
- [x] Add NVMe data collection; do not assume every disk supports it.
- [x] Add Linux CPU topology collection (`/proc/cpuinfo`, physical cores, threads, MHz, arch).
- [x] Add Linux GPU and DRM display collection (`/sys/class/drm`, connector status, resolution modes).
- [x] Add Linux AC power adapter status collection (`/sys/class/power_supply`).
- [x] Add Linux ACPI thermal zone monitoring (`/sys/class/thermal/thermal_zone*`).
- [x] Preserve raw output only when privacy-safe and useful; redact identifiers in shareable reports.
- [ ] Add Windows CIM/PowerShell collector with version-aware fallback for 10/11 (v2.1 roadmap).
- [ ] Add macOS `system_profiler`/IOKit collector (v2.1 roadmap).

## Phase 3 — testing and interactive tools (v1.0.0 & v2.0.0)
- [x] Design guided quick inspection and thorough diagnostics; label estimated durations.
- [x] Add manual keyboard/trackpad/display/ports checklist and recorded operator outcomes.
- [x] Add battery swelling/physical safety stop condition.
- [x] Add test-state model: pass/fail/warn/inconclusive/skipped/manual/not-supported.
- [x] Add dead/stuck pixel screen tester with fullscreen color cycling.
- [x] Add interactive keyboard matrix tester with real-time switch illumination.
- [x] Add Web Audio API pure tone generator, 5s frequency sweep (20Hz–8000Hz), and L/R channel isolation.
- [x] Add MediaStream webcam preview and microphone real-time dB volume analyzer.
- [x] Add trackpad & multi-touch gesture drawing canvas.
- [x] Ensure offline operation with network disabled and no DNS attempts.
- [x] Add Playwright automated UI tests verifying the complete buyer workflow (7 E2E tests, 52 total tests).

## Phase 4 — risk controls and reference sync
- [x] Introduce explicit read-only / non-destructive capability classifications.
- [x] Add SQLite persistence layer for offline sessions and history.
- [x] Add HTML/JSON report download and print optimization.
- [ ] Add signed reference-manifest cache with age/expiry labels (v2.1 roadmap).
- [ ] Add vendor model reference importer and source provenance (v2.1 roadmap).
- [ ] Add signed report export with a local key the user controls (v2.1 roadmap).

## Phase 5 — release & version 2.0.0 milestones
- [x] Clean-room independent architecture implemented (ADR-0004).
- [x] Version 1.0.0 released with git tag `v1.0.0` and open-sourced on GitHub.
- [x] Version 2.0.0: Local hardware auto-detection engine (`/api/probe`, `probe_host_specs()`).
- [x] Version 2.0.0: Dual-mode UI architecture: Normal mode for casual buyers vs Expert mode with custom threshold tuning.
- [x] Version 2.0.0: Radial SVG battery gauge, NVMe endurance meter, and CPU temperature dial.
- [x] Version 2.0.0: Seller Listing Claim Comparison Matrix.
- [x] Version 2.0.0: Deep Telemetry Grid (CPU topology, battery ACPI registers, storage NVMe bitmasks, motherboard/DRM).
- [x] Version 2.0.0: Interactive testing suite (Dead pixel tester, Audio sweep, Webcam & mic diagnostic, Trackpad canvas, Keyboard visualizer).
- [x] Version 2.0.0: Full Playwright test coverage (52 tests all passing).
- [x] Version 2.0.0: Release tag `v2.0.0` and GitHub issue #5 resolved.

## Phase 6 — v2.1.0 extended hardware suite

- [x] OS/Boot detection: UEFI vs BIOS/MBR, CPU arch (x86_64/ARM/32/64-bit), root filesystem type, OS pretty name, kernel version.
- [x] OS install age estimate: based on /etc/machine-id mtime (best-effort, no PII).
- [x] Touchscreen detection: sysfs input device name scan.
- [x] Backlight type detection: "raw" (OLED hint) vs "firmware" (LCD).
- [x] Fan RPM monitoring: non-destructive hwmon sysfs read; `/api/fans` endpoint.
- [x] Fan RPM display in Cooling Pulse tab with live refresh.
- [x] Ports & Connectors tab: USB device list, HDMI/DP connectors, AC charging status, network adapters.
- [x] Screen Studio tab: Contrast ramp (16-step grayscale), 1px checkerboard sharpness, UFO refresh-rate animation.
- [x] Keyboard heatmap: press-count color coding, 30ms bounce detection, condition report per key.
- [x] Keyboard condition report div with real-time bounce warning.
- [x] USB portable mode: autorun.inf, start-aegis.bat, start-aegis.manifest (UAC elevation request).
- [x] /api/system/extended endpoint for OS/boot metadata.
- [x] 58 tests all passing (19 collector, 32 unit analysis, 7 Playwright E2E).
- [ ] Code signing for Windows (requires EV certificate — future work).
- [ ] EDID panel type lookup (OLED/IPS/TN/VA) from binary EDID — future work.
- [ ] Fan speed control (max/whisper mode) — requires root + fancontrol; advisory-only for now.

## Phase 7 — v2.2.0 USB portable zero-trace & Rufus-tier performance

- [x] Dual-mode architecture: Automatic portable detection (`.portable` marker, `AEGIS_PORTABLE` env, `--portable` flag) vs standard system install.
- [x] Zero-trace USB storage: SQLite database routed to `<usb_root>/aegis_data/inspections.sqlite3` and reports to `<usb_root>/aegis_reports/`, leaving zero host traces.
- [x] Rufus-tier performance: Refactored `LinuxCollector.probe_host_specs()` and `collect_snapshot()` to use `ThreadPoolExecutor(max_workers=8)` for concurrent subsystem queries (67% speedup: latency dropped from ~3.7s to ~1.1s).
- [x] Direct-to-USB report persistence: Added `POST /api/export/portable` endpoint and dedicated "⚡ Save Report to USB" UI action.
- [x] UI Mode indicator: Added persistent `#appModeBadge` in navigation header displaying `⚡ USB PORTABLE` (pulsing emerald glow) or `LOCAL SYSTEM`.
- [x] Cross-platform portable launchers: Updated `start-aegis.bat` with local `PYTHONPATH` injection (no `pip install` required, zero host pollution) and added executable `run-portable.sh` for Linux USB boot.
- [x] Comprehensive test coverage: Added `PortableModeTests` in `tests/test_db.py` and `test_portable_mode_and_export` in `tests/test_ui_playwright.py` (71 total tests all passing cleanly).

## Phase 8 — v3.0.0 Xflash rebrand & Workshop-Bench UI/UX suite

- [x] Full product brand evolution: Renamed to Xflash ("Check before you pay") with signature open-ring-and-spark mark.
- [x] Zero-slop visual system: PCB token vocabulary (`--solder-mask`, `--silkscreen`, `--trace`, `--via-pad`), solid carbon OLED background, high-contrast monospace tabular numerals, and zero fake gradients.
- [x] Interactive Laptop Schematic: Responsive SVG hardware topology diagram mapping Screen, Webcam, Hinges, Keyboard, Trackpad, Ports, CPU/Thermals, NVMe Storage, and Battery with real-time health coloration and studio deep-links.
- [x] 3-Part Findings structure: Upgraded from generic text to explicit Lighthouse/iFixit tiers (1. What's wrong, 2. Why it matters / Buyer negotiation leverage, 3. Recommended action).
- [x] Intentional opt-in seller listing workflow: Collapsible listing claims accordion with offline marketplace URL storage, preventing false discrepancy accusations when claims are absent.
- [x] Fast command palette: Keyboard-driven quick jumper (`Ctrl+K` / `Cmd+K` / `Alt+E`) for rapid studio access and action execution.
- [x] Bundled offline GSAP animation: Boot splash ring fill animation and fluid studio tab switching with complete air-gap compliance.
- [x] Print-to-PDF certificate optimization: Clean, high-contrast `@media print` layout formatting reports for buyer-seller marketplace negotiations.
- [x] Persistent mode and offline status bar: Footer status strip displaying air-gapped status, zero-trace confirmation, and active lens.
- [x] 100% test verification: All 61 unit tests and 10 Playwright E2E browser tests pass cleanly.
