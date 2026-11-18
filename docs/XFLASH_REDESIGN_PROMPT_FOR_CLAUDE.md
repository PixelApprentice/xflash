# MASTER REDESIGN PROMPT & TECHNICAL SPECIFICATION
## Project: Xflash Hardware Diagnostics — Complete UI/UX & Architectural Overhaul

> **Prompt Context for Claude / AI Frontend Architect:**
> You are tasked with executing a comprehensive redesign of **Xflash** (`xflash`), an offline-first, portable laptop hardware testing kit. 
> The current UI is fractured, beginner mode is still too technical and confusing, and expert mode is broken into convoluted multi-step tabs. 
> Follow this master specification to rebuild the frontend into a world-class, human-first diagnostic instrument adhering to Anthropic's brand guidelines.

---

## 1. Executive Vision & Core Philosophy

### 1.1 The Two Fundamental Problems of the Current App
1. **The Fracture Problem (Lite vs. Pro):** Currently, the application is divided into two separate routes (`/` and `/lite`). This creates an artificial wall, duplicate codebases (`index.html` and `lite.html`), and user confusion. **Directive:** Eliminate the separation completely. Xflash must be **one unified application** where the presentation adapts instantly via a single, persistent mode switch.
2. **The "Complexity vs. Fragmentation" Problem:**
   - **For Beginners:** The app still overwhelms with jargon (mWh, SMART attributes, GiB vs GB, bus lanes, thermal throttling registers) and requires clicking through 8 different top-level navigation tabs. Beginners need **human-readable answers**: *"How long will this battery last me in hours?", "Is this SSD about to die?", "Can this laptop handle 40 Chrome tabs and video calls?", "What do I say to negotiate the price down?"*
   - **For Experts:** Telemetry is fractured across too many tabs and multi-step subtabs (`subtab-comparison`, `subtab-coverage`, `subtab-manual`, `subtab-expert`). Technicians and refurbishers need a **dense, unified single-cockpit workbench** where all registers, SMART attributes, DMI tables, and stress curves are visible and filterable at a glance.

---

## 2. Global Architectural Restructuring

### 2.1 Unified Single-Page Architecture
- **Retire `/lite`:** All capabilities from the lite edition (fast paste parser, quick check list) are seamlessly embedded into the main interface.
- **Persistent Header Navigation:**
  - **Left:** Brand Mark (`Xflash`), version, and offline USB security seal badge.
  - **Center:** **Mode Toggle Switch:**
    - `[ 🟢 Buyer (Human) Mode ]` vs `[ ⚙️ Expert (Cockpit) Mode ]`
    - Toggling transforms the view instantly via CSS/JS without reloading the page or losing current scan state.
  - **Right:**
    - Quick Action Button: `[ ⚡ Auto-Scan Hardware ]` (or `[ Load Demo Sample ]` for testing).
    - Theme Switcher Pills: `Porcelain Light` (`#faf9f5`), `Carbon Dark` (`#141413`), `Warm Paper` (`#f6f3eb`).
    - Report Action: `[ 📄 Export PDF Certificate ]`.

---

## 3. Beginner Buyer Mode: The "Human Story" Experience

The mental model of Beginner Mode is a **knowledgeable, trustworthy tech friend standing right beside the buyer at a coffee shop or parking lot meetup**, translating raw electronics into plain everyday human value.

### 3.1 The Verdict & Safety Hero Banner
- Prominent top card with an unmistakable status:
  - 🟢 **SAFE TO BUY (Verified Clean):** All hardware matches claims, battery and SSD have ample lifespan remaining.
  - 🟡 **NEGOTIATE DISCOUNT (Wear Detected):** Hardware works, but component degradation (worn battery, small RAM shortfall) justifies a price cut.
  - 🔴 **WALK AWAY (Critical Hardware Defect):** Storage drive has unrecoverable physical bad sectors, fan failure, or thermal runaway.
- **Estimated Real-World Value & Safety Score:**
  - Overall hardware health translated into a friendly label (e.g., *"Like New / Excellent Condition"* vs *"Heavily Used / Needs Servicing"*).

### 3.2 Human-Readable Subsystem Health Cards (Deep Details in Plain English)
Beginner Mode must replace raw metrics with rich, contextualized real-world explanations:

#### Card 1: Battery & Daily Run-Time
- **Human Metric:** `Battery Health: 72% · Estimated 3.5 to 4.5 Hours of Use`
- **Plain-English Story:**
  - *"The factory battery originally held 60,000 mWh. Due to normal usage over ~300 charge cycles, it now holds 43,200 mWh."*
  - *"What this means for you: Expect around 3.5 to 4 hours of web browsing, YouTube streaming, or document editing on a full charge. For gaming or video rendering, expect 1 to 1.5 hours."*
- **Actionable Financial Advice:**
  - *"Budget $45–$65 for an eventual replacement battery on Amazon/eBay if you need all-day battery life."*
- **1-Click Test:** `[ ⚡ Test Battery Drain Speed ]` (monitors discharge rate under quick simulated load).

#### Card 2: SSD Lifespan & Data Safety
- **Human Metric:** `SSD Health: 92% Life Remaining · Estimated 5+ Years Left`
- **Plain-English Story:**
  - *"This laptop uses a modern, high-speed NVMe Solid State Drive (SSD). It has only used 8% of its rated lifetime write cycles."*
  - *"Zero read/write media errors: The drive is physically healthy with no corrupted storage sectors. Your files and photos are safe."*
  - *"Storage Capacity: 512 GB (Roughly 476 GB usable) — Enough space for ~120,000 photos, 60 hours of HD video, or 10 modern large games."*
- **Speed Rating:** *"Lightning Fast (Loads Windows in ~10 seconds)."*

#### Card 3: Memory (RAM) & Real-World Capability
- **Human Metric:** `RAM: 16 GB · Excellent Multitasking Power`
- **Plain-English Story:**
  - *"16 Gigabytes of high-speed memory detected. Matches the seller's advertised specification."*
  - *"What you can run simultaneously:*
    - *30–50 open browser tabs with video playback*
    - *Office / Google Docs / Zoom video meetings*
    - *Light photo editing (Photoshop, Lightroom) and programming.*
  - *(If 8GB detected):* *"Adequate for everyday web and schoolwork, but may slow down with many open tabs."*

#### Card 4: Processor (CPU) & Cooling Noise
- **Human Metric:** `Processor: Intel Core i7-1165G7 · Cool & Quiet (44°C)`
- **Plain-English Story:**
  - *"The processor is operating at a comfortable 44°C (111°F). Normal laptop idling temperature is 40°C–55°C."*
  - *"Cooling fan is running smoothly with no grinding bearing noise or dust choke."*
- **1-Click Test:** `[ 🌪 5-Second Fan Pulse ]` (spins the fan briefly so the buyer can hear if it grinds, clicks, or rattles).

#### Card 5: Display Panel & Visual Check
- **Human Metric:** `Screen: 14-Inch Full HD (1920 × 1080) · Panel Ready`
- **Plain-English Story:**
  - *"Sharp 1080p resolution. No fuzzy text or weird scaling."*
- **1-Click Test:** `[ 📺 Open Fullscreen Color Check ]`
  - Turns screen solid White, Black, Red, Green, Blue.
  - Plain prompt: *"Look closely at the screen: Do you see any tiny black/colored dots that won't change (dead pixels), white pressure blotches, or bright light leaking from the corners?"*
  - Two big buttons: `[ ✅ Screen Looks Clean ]` or `[ ❌ Found Screen Defects ]`.

#### Card 6: Keyboard & Trackpad Touch Test
- **Human Metric:** `Keyboards & Touchpad: 42 Keys Tested · Smooth Click`
- **Plain-English Story:**
  - *"Laptop keyboards often fail from spilled liquids or worn switches. Type every key to verify they don't double-type or fail to respond."*
- **Visual Switch Grid:**
  - A friendly laptop keyboard graphic where keys turn bright green as you press them.
  - Trackpad area where you can draw with your finger to verify touch tracking and multi-finger scroll.

---

### 3.3 The Deal Evaluator & "What to Say to the Seller"
A dedicated negotiation box that calculates exact price discounts and equips the non-technical buyer with confidence:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 💬 BUYER BARGAINING LEVERAGE & TALKING POINTS                          │
├────────────────────────────────────────────────────────────────────────┤
│  Asking Price: $450   │  Fair Counter-Offer: $385  │  Discount: -$65   │
├────────────────────────────────────────────────────────────────────────┤
│  Why the discount is justified:                                        │
│  • Battery capacity is down to 72% (replacement pack costs ~$50-$70).   │
│  • Cooling fan showed mild thermal spike (dust cleaning needed).       │
├────────────────────────────────────────────────────────────────────────┤
│  🗣 Suggested Script (Read or paraphrase to seller):                   │
│  "I just ran a quick hardware check on the machine. Everything powers  │
│   on nicely, but the battery has lost roughly 28% of its original      │
│   charge capacity, which means I'll need to budget for a replacement   │
│   battery soon. Factoring in that cost, would you be open to $385      │
│   cash today?"                                                         │
│                                                                        │
│  [ 📋 Copy Script ]   [ 📱 Show Seller Certificate ]                  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Expert Mode: The "Cockpit Workbench" Experience

The mental model of Expert Mode is a **high-density diagnostic workbench** (inspired by Bloomberg Terminal, Logic Pro, and Apple Developer Instruments) for technicians, engineers, and refurbishers.

### 4.1 Elimination of Multi-Step Tab Mazes
- In the old UI, experts had to click across 6 tabs and 4 subtabs to see complete telemetry.
- **The New Cockpit Layout (3-Column Dense Grid):**
  - **Left Column (System Architecture & Bus Topology):**
    - Motherboard & DMI / SMBIOS table (Board vendor, UUID, serial, BIOS version, release date).
    - Memory channel configuration (Dual-channel vs Single-channel, SODIMM slot occupancy, frequency, CAS latency).
    - PCIe bus lanes and generation (e.g. Gen 4 x4 NVMe link).
  - **Center Column (Live Sensors & Real-Time Curves):**
    - CPU Core topology and thread frequencies.
    - Live thermal graph with TjMax delta and thermal throttle flag indicators (`PROCHOT#`).
    - CPU 5-second pulse benchmark with before/after thermal rise velocity (°C/sec).
    - Fan profile override and tachometer RPM readout.
  - **Right Column (Raw Controller Dumps & NVMe SMART):**
    - Full NVMe SMART attribute table: Critical warning byte flags, temperature sensors 1 & 2, available spare %, power cycles, unsafe shutdowns, media error counts.
    - Battery Gas Gauge registers: Manufacturer, chemistry (LiP/LION), design voltage vs current voltage, full charge capacity vs design capacity, cycle counter, degradation ratio.
    - Discrepancy Reconciliation Engine: Claimed vs detected comparison matrix with byte-accurate tolerances.
- **Quick Controls at Top of Cockpit:**
  - `[ 🔍 Filter Registers ]` search bar.
  - `[ Dec / Hex Toggle ]` for raw counters.
  - `[ 💾 Export Raw JSON Snapshot ]`
  - `[ 📋 Copy DMI / SMART to Clipboard ]`

---

## 5. Visual Design System: Anthropic Brand Guidelines

The entire redesign must follow Anthropic's refined design tokens and typography:

### 5.1 Color Tokens
```css
:root {
  /* Anthropic Light (Porcelain Clean - Default) */
  --bg-app: #faf9f5;
  --bg-surface: #ffffff;
  --bg-subtle: #f0ede6;
  --border-color: #e8e6dc;
  --border-hover: #b0aea5;
  --text-main: #141413;
  --text-muted: #6b6963;
  --text-subtle: #96938a;
  
  /* Anthropic Brand Accents */
  --primary: #d97757;          /* Anthropic Terracotta Orange */
  --primary-subtle: #fbf0ec;
  --primary-border: #f2cbbe;
  --accent-blue: #6a9bcc;      /* Secondary Soft Blue */
  --accent-green: #788c5d;     /* Tertiary Olive Green */

  /* Semantic Hardware Status */
  --status-pass: #788c5d;       /* Clean / Passed */
  --status-pass-subtle: #f2f5ed;
  --status-warn: #d97757;       /* Degraded / Review */
  --status-warn-subtle: #fbf0ec;
  --status-crit: #c53b27;       /* Defect / Dangerous */
  --status-crit-subtle: #faebe8;
  --status-neutral: #6a9bcc;    /* Inconclusive / Unsupported */
}

[data-theme="dark"] {
  /* Anthropic Carbon Dark */
  --bg-app: #141413;
  --bg-surface: #1f1f1d;
  --bg-subtle: #292927;
  --border-color: #353532;
  --border-hover: #4e4e4a;
  --text-main: #faf9f5;
  --text-muted: #b0aea5;
  --text-subtle: #7a7974;
  
  --primary: #d97757;
  --primary-subtle: #33201b;
  --primary-border: #5e362a;
}

[data-theme="warm"] {
  /* Anthropic Warm Paper */
  --bg-app: #f6f3eb;
  --bg-surface: #ffffff;
  --bg-subtle: #ede8dc;
  --border-color: #ded9cd;
  --border-hover: #b8b2a5;
  --text-main: #1e1e1c;
  --text-muted: #6e6a62;
  --text-subtle: #8c887b;
}
```

### 5.2 Typography System
```css
/* Typography Scale */
--font-heading: "Poppins", "Arial", sans-serif;
--font-body: "Lora", "Georgia", serif;
--font-mono: "JetBrains Mono", "SF Mono", monospace;
```
- **Headings & Badges:** Use `var(--font-heading)` with tight letter spacing for crisp, modern hardware titles.
- **Human Explanations, Stories & Scripts:** Use `var(--font-body)` for high-comfort editorial reading of diagnostic advice and negotiation points.
- **Numbers, Registers & Capacities:** Use `var(--font-mono)` with `font-feature-settings: "tnum" 1` so columns of numbers never wobble or jitter.

---

## 6. Implementation Checklist & Step-by-Step Execution Plan

When implementing this redesign, proceed in this exact order:

### Step 1: Consolidate Markup (`src/xflash/web/static/index.html`)
- Remove duplicate files or dependencies on `lite.html`.
- Build the unified top navbar with the Mode Switcher (`Buyer` vs `Expert`).
- Structure the main container with two adaptive modes:
  - Container `.buyer-view`: The 6 human-readable cards + Deal Evaluator & Negotiation Box + Fullscreen testing modal launchers.
  - Container `.expert-view`: The dense 3-column diagnostic workbench + live SVG bus topology + raw register search tables.

### Step 2: Enrich Controller Logic (`src/xflash/web/static/app.js`)
- **Human Metric Translation Engine:** Add helper functions that convert raw numbers to real-world language:
  - `formatBatteryRuntimeHours(full_mwh, current_rate)` -> Returns e.g. `"3.5 to 4.5 hours of everyday use"`.
  - `formatSsdLifespanYears(used_pct)` -> Returns e.g. `"Estimated 5+ years remaining"`.
  - `formatRamCapability(gib)` -> Returns bullet points of what everyday software can run smoothly.
- **Dynamic Mode Switcher:**
  - Persist user preference (`localStorage.getItem("xflash_mode") || "buyer"`).
  - Toggling smoothly switches between `.buyer-view` and `.expert-view`.
- **Integrated Listing Auto-Fill:**
  - Keep the paste input box right at the top of the Buyer view with instant spec detection and asking price extraction.

### Step 3: Polish Stylesheet (`src/xflash/web/static/app.css`)
- Implement the Anthropic tokens, typography stacks, and elevation shadows.
- Ensure responsive fluidity on both small laptop screens (1366x768) and high-DPI retina displays.
- Style the keyboard switch tester and full-screen color check overlays with smooth transitions.

### Step 4: Verification & Standalone Packaging
- Run test suite: `.venv/bin/python -m unittest discover -s tests -v`.
- Build binaries: `.venv/bin/python tools/build_standalone.py --all`.
- Verify runtime behavior on sample sessions: `./dist/xflash analyze examples/sample_session.json`.

---

## 7. Expected Deliverables from Claude
When asked to execute this redesign:
1. Provide the complete updated `src/xflash/web/static/index.html`.
2. Provide the complete updated `src/xflash/web/static/app.js`.
3. Provide the complete updated `src/xflash/web/static/app.css`.
4. Ensure zero regressions in `tests/test_ui_playwright.py` and unit tests.
5. Compile and output updated `dist/xflash` and `dist/xflash.pyz`.
