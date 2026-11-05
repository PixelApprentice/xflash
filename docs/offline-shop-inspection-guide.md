# In-Store & Clean-OS Laptop Inspection Guide

This guide explains how to use **Xflash** to inspect used or refurbished laptops in computer shops, marketplaces, or private meetups where the target machine has been **freshly wiped or clean-reinstalled** and has **no Python, compilers, or third-party tools installed**.

---

## 🏬 The Clean-OS Shop Reality

When buying used laptops in retail shops or from classified sellers:
1. **The laptop was recently reset:** Sellers usually perform a fresh Windows or Linux installation before putting it in the display case.
2. **Zero development tools:** Python, Git, and diagnostic utilities are almost never installed on shop machines.
3. **No internet access guarantee:** You might not have the store's Wi-Fi password, or the laptop might not be connected to the internet.
4. **No persistent modifications allowed:** Sellers will not allow you to install large software packages, run invasive write tests, or modify system files.

---

## 💽 The 100% Standalone USB Solution

Xflash operates in **USB Portable Mode**, which carries its own lightweight runtime directly on the flash drive:

```
USB_FLASH_DRIVE/
├── python/                     # Optional self-contained Windows Python runtime (~10MB)
│   ├── python.exe              # Official embeddable interpreter
│   └── python311._pth          # Configured to load Xflash without host installation
├── src/                        # Xflash core inspection engine
├── start-xflash.bat            # One-click Windows launcher (Windows 8, 10, 11)
├── run-portable.sh             # Executable Linux launcher (Ubuntu, Arch, Debian, Fedora)
├── xflash.desktop              # Desktop application shortcut for Linux file managers
├── autorun.inf                 # Windows Explorer drive branding & AutoPlay prompt
├── autorun.sh                  # GNOME/XFCE removable media auto-prompt
├── aegis_data/                 # Local SQLite database (written strictly to USB)
└── aegis_reports/              # Generated HTML & PDF certificates (written strictly to USB)
```

---

## 🛠 Step 1: Pre-Configuring Your USB Drive (Before Visiting the Shop)

Before going to the store, prepare your USB drive using your home computer:

### On Linux or macOS:
```bash
# Clone Xflash to your USB drive
git clone https://github.com/PixelApprentice/xflash.git /media/your-usb/xflash
cd /media/your-usb/xflash

# Download and bundle the Windows embeddable runtime (~10 MB)
./prepare-usb.sh
```

### On Windows:
```cmd
git clone https://github.com/PixelApprentice/xflash.git D:\xflash
cd D:\xflash
prepare-usb.bat
```

> **What `./prepare-usb.sh` does:** Downloads the official, signed Python Embeddable package from python.org and extracts it into `./python/`. It configures the search path so Windows laptops can run Xflash without installing Python on the shop machine!

---

## 🖥 Step 2: Testing Laptops in the Shop

### Testing a Windows Laptop (Windows 8, 10, or 11)

1. **Plug in your USB drive.**
2. Open **File Explorer** and open the USB drive.
3. Double-click **`start-xflash.bat`**.
   - If `./python/` is present on the USB, Xflash launches immediately using the self-contained interpreter.
   - If not, it checks standard Windows paths (Microsoft Store Python, Python.org, system PATH).
4. The local browser opens automatically to **`http://127.0.0.1:8080`**.
5. Click **⚡ Auto-Detect Specs** to probe the hardware, or enter the seller's price and advertised specs.
6. Click **Print / PDF Certificate** before closing to save the report to the USB drive.

### Testing a Linux Laptop (Ubuntu, Arch, Debian, Fedora, Mint)

Almost all modern Linux desktop distributions include Python 3 by default:

#### Option A: Interactive Web Workshop
1. Plug in the USB drive.
2. Double-click **`xflash.desktop`** (or open a terminal on the USB and run `./run-portable.sh`).
3. View the workshop dashboard in the browser.

#### Option B: Terminal CLI (Super Fast)
If you prefer testing directly in the terminal without opening a browser:
```bash
# 1. Instant live hardware scan:
./xflash scan

# 2. Reconcile against seller listing claims:
./xflash scan --claim-ram 16 --claim-storage 512 --claim-model "ThinkPad T14"

# 3. Export an offline HTML report to the USB drive:
./xflash scan --claim-ram 16 --export-html aegis_reports/shop-inspection.html
```

---

## 🔍 In-Store Inspection Checklist

1. **Check Battery Health:** Look at full charge capacity vs design capacity. A battery with <75% health is a prime candidate for a $50–$100 price discount.
2. **Check Cycle Count Discrepancy:** If cycles are low (<30) but capacity loss is high (>20%), the battery was likely stored flat or swapped.
3. **Verify Storage (NVMe/SSD):**
   - Check **Media Errors** (must be `0`). Nonzero errors indicate bad NAND flash blocks.
   - Check **Percentage Used** (wear leveling).
   - Check **Power-On Hours** to see how long the drive was really used.
4. **Detect Resale Clean-Wipes:** Xflash compares the OS install timestamp against SSD runtime. If the OS was installed 2 days ago but the SSD has 8,000 power-on hours, you know the laptop was wiped right before being placed in the shop.
5. **Screen Studio:** Run the 16-step grayscale contrast ramp and the live UFO refresh rate benchmark to verify genuine panel specs (e.g. 10-bit OLED vs budget 6-bit TN).
6. **Keyboard Switch Chatter:** Tap every key in the Input Studio; verify no switch bounce warnings (<35ms).
