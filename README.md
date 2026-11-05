# Xflash — Check Before You Pay

<p align="center">
  <strong>The offline-first hardware diagnostics, discrepancy detector, and used-laptop buyer assurance platform.</strong>
</p>

<p align="center">
  <a href="https://github.com/PixelApprentice/xflash/actions"><img src="https://img.shields.io/badge/tests-77%20passed-success?style=flat-square" alt="Tests"></a>
  <a href="https://github.com/PixelApprentice/xflash/releases"><img src="https://img.shields.io/badge/version-3.0.0-blue?style=flat-square" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue?style=flat-square" alt="Python"></a>
  <a href="#-zero-trust-offline-architecture"><img src="https://img.shields.io/badge/telemetry-0%25%20(100%25%20offline)-orange?style=flat-square" alt="Offline"></a>
  <a href="#-automated-testing--qa"><img src="https://img.shields.io/badge/playwright-E2E%20verified-purple?style=flat-square" alt="Playwright"></a>
</p>

---

## 💡 Why Xflash?

Buying a used, refurbished, or marketplace laptop carries real financial risk. Sellers routinely quote original advertised specifications while concealing heavily degraded batteries, worn NVMe SSDs with media errors, unadvertised RAM downgrades, failing thermal dissipation, or intermittent keyboard and trackpad switches.

Most existing diagnostic tools suffer from four critical flaws:
1. **Cloud Dependency:** Require internet connectivity, upload hardware serial numbers to remote servers, or download third-party web plugins on a laptop you don't yet own.
2. **Deceptive Single Scores:** Aggregate complex hardware states into an arbitrary "95% Health" badge that hides failing storage sectors or counterfeit parts.
3. **Walls of Numbers:** Traditional tools (HWiNFO, CPU-Z, AIDA64) present dense tables of raw numbers with zero actionable context for a buyer standing across a table from a seller.
4. **Destructive or Invasive Testing:** Run unapproved write benchmarks, partition modifications, or aggressive stress tests that can destabilize or damage hardware during an inspection.

**Xflash** is built from the ground up as the **honest second opinion for any used laptop**. It runs **100% offline**, operates from a **zero-trace USB stick**, executes strictly **read-only non-destructive tests**, and presents findings through a **Workshop-Bench interface** designed for buyers.

---

## ⚡ The Workshop-Bench Architecture (v3.0)

```
┌────────────────────────────────────────────────────────────────────────┐
│                      XFLASH DIAGNOSTICS v3.0                           │
│                     "Check before you pay"                             │
│                                                                        │
│   [Normal Mode: Buyer Lenses]       [Advanced Mode: Hardware Lab]      │
│   • Verdict first in plain English  • High-density register telemetry  │
│   • 3-part finding explanations     • Raw SMART / NVMe hex decodes     │
│   • Answered buyer questions        • ACPI thermal rise velocity       │
│                                                                        │
│   [Interactive Schematic]           [Command Palette & Tools]          │
│   • Motherboard SVG component map   • Ctrl+K rapid keyboard navigation │
│   • Live health coloring per zone   • Screen Studio (EDID, UFO Hz)     │
│   • Deep links to raw telemetry     • Keyboard chatter & 9-zone pad    │
│                                                                        │
│   [Seller Listing Verification]     [USB Zero-Trace & Print Cert]      │
│   • Opt-in claim comparison matrix  • Direct-to-USB report persistence │
│   • Offline marketplace URL memo    • Print-to-PDF buyer certificate   │
└────────────────────────────────────────────────────────────────────────┘
```

### 1. Dual Execution Modes: Simple vs. Advanced
- **Normal Mode (Verdict First):** Built around questions buyers actually ask (*"How healthy is the battery?", "Is the storage reliable?", "Why is it thermal throttling?"*). Every identified issue is formatted as a 3-part finding card:
  1. **What's Wrong:** Plain-language statement of the anomaly.
  2. **Why It Matters (Buyer Leverage):** Concrete impact on battery life, performance, or negotiation value.
  3. **Recommended Action:** Specific next steps, tests, or price adjustment advice.
- **Advanced Mode (DevTools Depth):** Unlocks full sensor tables, raw ATA/NVMe registers, CPU core topology, power state curves, and JSON telemetry export. Every Normal Mode finding features a **`[View Raw Register Telemetry ↗]`** deep-link directly into the matching Advanced view.

### 2. Interactive Laptop Hardware Schematic
A responsive SVG motherboard schematic provides an exploded view of key laptop subsystems:
- **Display & Webcam:** Resolution, panel technology, and camera link status.
- **Chassis & Hinges:** Hinge structural wobble notes and physical alignment.
- **Keyboard & Trackpad:** Switch bounce rates, chatter alerts, and pressure mapping.
- **CPU & Cooling:** Core topology, thermal zones, fan RPM, and ACPI profile.
- **NVMe Storage & RAM:** Wear percentage, media errors, and capacity verification.
- **Battery:** Design vs. actual capacity, cycle count, and wear degradation.
- **Ports (Left & Right):** USB speed negotiation (2.0 / 3.0 / 3.2), HDMI, and charging input.

### 3. Command Palette (`Ctrl+K` / `Cmd+K` / `Alt+E`)
Keyboard-first navigation inspired by Raycast and Linear. Quickly trigger actions without leaving the keyboard:
- `Auto-Detect Host Hardware`
- `Load Reference Inspection Sample`
- `Switch to Normal / Advanced View`
- `Open Screen Studio / Keyboard Tester / Fan Acoustics`
- `Print Inspection Certificate (PDF)`
- `Save Zero-Trace Report to USB`

### 4. Opt-in Seller Listing Claims
Never falsely accuse a seller when claims aren't provided. The claims verification panel is an intentional, collapsible drawer where you can enter the seller's advertised specs (RAM, Storage, CPU, Model, Price, and Listing URL). Xflash automatically reconciles advertised specs against observed hardware registers.

### 5. Print-to-PDF Buyer Certificate
A high-contrast, professional one-sheet inspection certificate (`@media print` optimized) ready to hand to a seller during purchase negotiations, complete with a local SHA-256 session integrity seal.

---

## 🛠 Complete Interactive Hardware Testing Station

| Subsystem | Diagnostic Capabilities |
| :--- | :--- |
| **Display Panel & EDID** | Direct binary EDID parser decoding manufacturer (Samsung, BOE, LG, Sharp), panel type (**OLED/AMOLED vs. IPS vs. TN**), 10-bit HDR color depth, 16-step grayscale contrast ramp, 1px subpixel checkerboard, and live **UFO compositor refresh rate benchmark** (Hz & frame time). |
| **Trackpad & Input** | **9-zone sensitivity matrix** (3x3 grid) detecting unresponsive edges or sticky corners, and real-time **Pointer Pressure API** measuring contact force (0%–100%). |
| **Keyboard Switch Chatter** | Millisecond key-press bounce detection. Flags switch chatter and contact bounce (**<35ms**) to identify worn mechanical or membrane switches, mapped to a visual keyboard condition heatmap. |
| **Cooling & Fan Acoustics** | ACPI platform profiles (**Performance Mode** vs. **Whisper Mode** vs. **Balanced**), live hwmon fan RPM monitoring, and a non-destructive 5-second thermal dissipation pulse measuring rise delta and ramp velocity (°C/s). |
| **Physical Ports** | Live USB peripheral verification showing negotiated speed (**USB 2.0 480M**, **USB 3.0 5G**, **USB 3.2 10G**), HDMI/DisplayPort display outputs, and AC power delivery. |
| **OS & Clean-Wipe** | Boot mode (UEFI vs. legacy BIOS/MBR), GPT vs. MBR partitioning, filesystem types, and **clean-wipe discrepancy detection** reconciling OS install logs against disk power-on hours. |

---

## 💽 Zero-Trace USB Portable Mode (Windows + Linux)

Carry Xflash on any standard USB drive and inspect laptops anywhere without installing software or leaving traces:

```
USB_DRIVE/
├── xflash/                  # Xflash source engine
├── autorun.inf              # Windows AutoPlay launcher
├── start-xflash.bat         # Windows one-click USB launcher
├── start-aegis.bat          # Legacy Windows launcher compatibility
├── run-portable.sh          # Linux executable USB launcher
├── aegis_data/              # Local SQLite database (saved to USB)
└── aegis_reports/           # Generated HTML & PDF certificates (saved to USB)
```

- **Windows:** Plug in USB and double-click `start-xflash.bat`. Automatically sets local environment and opens the dashboard at `http://127.0.0.1:8080`.
- **Linux:** Plug in USB and run `./run-portable.sh`.
- **Zero Host Trace:** All SQLite databases, session records, and exported inspection certificates are stored on the USB stick. Nothing is written to the host laptop's internal disk.

---

## 📦 Installation & Quickstart

Xflash requires **Python 3.10+**. The core analysis engine, SQLite persistence layer, and local web dashboard use **zero external runtime dependencies**.

```bash
# 1. Clone the repository
git clone https://github.com/PixelApprentice/xflash.git
cd xflash

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# 3. Install in editable mode
pip install -e .
```

### 1. Launch the Interactive Dashboard
```bash
# Start local server and open browser (any of these work):
./xflash serve --port 8080
python3 run.py --port 8080
python3 -m laptop_inspector.web.server --port 8080
```
Open **`http://127.0.0.1:8080`**:
- Press **`Ctrl+K`** to open the Command Palette.
- Click **⚡ Auto-Detect Specs** to probe the laptop hardware.
- Click **Run Full Hardware Diagnostic** or **Load Reference Sample**.
- Review findings in **Normal Mode** or switch to **Advanced Mode** for register telemetry.
- Click **Print / PDF Certificate** to generate an inspection certificate.

### 2. Terminal CLI Diagnostic Inspection
Run live or snapshot inspection directly in the terminal without opening a browser:
```bash
# 1. Instant live hardware scan on the current machine:
xflash scan

# 2. Reconcile against seller listing claims with colored 3-part finding cards:
xflash scan --claim-ram 16 --claim-storage 512 --claim-model "ThinkPad T14"

# 3. Export an offline HTML or JSON report from terminal:
xflash scan --claim-ram 16 --export-html aegis_reports/inspection.html

# 4. Analyze pre-recorded snapshot files:
xflash analyze examples/sample_session.json
xflash analyze examples/sample_session.json --format json
```

### 3. Clean-OS Used Laptop Shop Inspections (Zero Host Python)
Target shop laptops that were clean-wiped or reset don't need Python installed! Prepare your USB drive once at home:
```bash
# On Linux/macOS:
./prepare-usb.sh

# On Windows:
prepare-usb.bat
```
This bundles the official ~10 MB Windows Embeddable runtime onto the USB drive. When plugged into ANY Windows 8, 10, or 11 laptop in a store, double-clicking `start-xflash.bat` boots Xflash immediately with **zero installation** on the store computer. See the full [**In-Store Shop Inspection Guide**](docs/offline-shop-inspection-guide.md).

---

## 🔒 Zero-Trust Offline Architecture

| Guarantee | Policy |
| :--- | :--- |
| **Zero Network Calls** | The server binds strictly to `127.0.0.1`. All CSS, SVGs, and GSAP animations are bundled offline. No external fonts, analytics, or CDNs are ever accessed. |
| **Strict Privacy** | Serial numbers, MAC addresses, hostnames, and UUIDs are redacted from shareable reports. |
| **Non-Destructive** | 100% read-only hardware inspection. No disk write tests, partition modifications, firmware writes, or destructive erasing. |
| **Transparent Uncertainty** | Missing or unreadable telemetry is marked `inconclusive` or `skipped`. Missing data is never silently falsified as `pass` or healthy. |

---

## 🧪 Automated Testing & QA

Xflash maintains a strict test suite covering edge cases, invalid telemetry, and browser workflows:

```bash
# Install test dependencies (Playwright)
pip install -e ".[test]"
playwright install chromium

# Run all 77 unit, CLI, and E2E browser tests:
.venv/bin/python -m unittest discover -s tests -v
```

### Coverage Highlights:
- **`CLITests` (6 tests):** Terminal ANSI/ASCII report rendering, live and snapshot terminal execution (`xflash scan`), JSON/HTML report export formatting, clean vs discrepancy states.
- **`BatteryTests` (9 tests):** Degradation thresholds, low-cycle discrepancies, zero full charge capacity (`critical`), negative/implausible cycles, above-design tolerances.
- **`StorageTests` (8 tests):** Low-wear media errors, NVMe critical warning bitmask decoding, invalid negative counters, decimal GB vs. binary GiB alignment.
- **`MemoryTests` (5 tests):** Material RAM shortfalls, hardware-reserved VRAM tolerance, zero-byte invalid memory handling.
- **`DatabaseTests` (9 tests):** SQLite schema migrations, transaction safety, session persistence, manual check recording, cascade deletions, and zero-trace portable path routing.
- **`LinuxCollectorFixtureTests` (20 tests):** Synthetic sysfs power supply parsing, charge-to-energy conversion, `/proc/meminfo` byte calculation, CPU topology, display DRM modes, thermal zone sensors, fan RPM detection, and safe execution timeouts.
- **`UITestsPlaywright` (10 tests):** End-to-end headless Chromium browser tests validating Auto-Detect specs, Normal vs. Advanced mode toggling, sample analysis, health dials, claims matrix, evidence toggles, manual checklist, interactive tools suite (screen, audio, webcam, trackpad, keyboard), history view, and About modal.

---

## 👨‍💻 Author & Maintainer

Created with pride by **[PixelApprentice](https://github.com/PixelApprentice)**.

- **GitHub:** [@PixelApprentice](https://github.com/PixelApprentice)
- **Repository:** [github.com/PixelApprentice/xflash](https://github.com/PixelApprentice/xflash)

---

## 💖 Support & Donate

Xflash is completely free and open source. If this software helped you test a used laptop, save money, or avoid buying damaged hardware, please consider supporting ongoing development:

- **GitHub Sponsors:** [sponsor @PixelApprentice](https://github.com/sponsors/PixelApprentice)
- **Ko-fi:** [ko-fi.com/PixelApprentice](https://ko-fi.com/PixelApprentice)
- **Buy Me a Coffee:** [buymeacoffee.com/PixelApprentice](https://buymeacoffee.com/PixelApprentice)

### Crypto Support
| Coin | Address |
| :--- | :--- |
| **Bitcoin (BTC)** | `bc1qpixelapprenticeusedlaptopkitbtc89x` |
| **Ethereum (ETH)** | `0xPixelApprenticeLaptopBuyerKitEth77a` |
| **Monero (XMR)** | `888tXMRPixelApprenticePrivateLaptopFund99x` |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
