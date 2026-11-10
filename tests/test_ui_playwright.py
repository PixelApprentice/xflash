"""Automated end-to-end tests for the Aegis Laptop Diagnostics UI using Playwright."""
import threading
import unittest
from tempfile import NamedTemporaryFile
from pathlib import Path

from playwright.sync_api import sync_playwright

from laptop_inspector.db import Database
from laptop_inspector.web.server import create_server

TEST_HOST = "127.0.0.1"
TEST_PORT = 8923


class UITestsPlaywright(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.temp_db.close()
        cls.db = Database(cls.temp_db.name)

        cls.server = create_server(host=TEST_HOST, port=TEST_PORT, db=cls.db)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        Path(cls.temp_db.name).unlink(missing_ok=True)

    def setUp(self):
        self.page = self.browser.new_page()

    def tearDown(self):
        self.page.close()

    def test_dashboard_loads_and_has_branding(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")
        self.assertIn("Aegis", self.page.title())

        # Check brand and navigation tabs
        self.assertTrue(self.page.locator(".brand-title").is_visible())
        self.assertTrue(self.page.locator("button[data-tab='tab-inspect']").is_visible())
        # New tab structure: tab-tools is hidden alias; check real tabs instead
        self.assertTrue(self.page.locator("button[data-tab='tab-ports']").is_visible())
        self.assertTrue(self.page.locator("button[data-tab='tab-screen']").is_visible())
        self.assertTrue(self.page.locator("button[data-tab='tab-history']").is_visible())
        self.assertTrue(self.page.locator("button[data-tab='tab-about']").is_visible())
        self.assertTrue(self.page.locator(".mode-switch-wrapper").is_visible())

    def test_normal_vs_expert_mode_toggle(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # Initially in Normal mode: config panel hidden
        self.assertFalse(self.page.locator("#expertConfigPanel").is_visible())

        # Toggle Expert Mode on by clicking slider
        self.page.click(".slider")
        self.page.wait_for_selector("#expertConfigPanel", state="visible")
        self.assertTrue(self.page.locator("#expertConfigPanel").is_visible())

        # Check that expert label is active
        self.assertIn("active", self.page.locator(".expert-label").get_attribute("class") or "")

        # Toggle back to Normal Mode
        self.page.click(".slider")
        self.page.wait_for_selector("#expertConfigPanel", state="hidden")
        self.assertFalse(self.page.locator("#expertConfigPanel").is_visible())

    def test_auto_detect_specs_query(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # Click Auto-Detect Specs
        self.page.click("#autoDetectBtn")
        # Wait up to 8 seconds for probe to complete and populate field
        self.page.wait_for_function("document.getElementById('claimRam').value.length > 0", timeout=8000)

        # Confirm RAM input or Model input was populated by local probe
        ram_val = self.page.locator("#claimRam").input_value()
        self.assertTrue(len(ram_val) > 0, "Auto-detect should populate detected host RAM")

    def test_inspection_sample_workflow_and_checklist(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # Fill claims
        self.page.fill("#claimModel", "ThinkPad T14 Gen 2")
        self.page.fill("#claimRam", "16")
        self.page.fill("#claimStorage", "512")
        self.page.fill("#operatorNotes", "Playwright automated test inspection")

        # Click Load Synthetic Sample
        self.page.click("#loadSampleBtn")

        # Wait for results to show
        self.page.wait_for_selector("#sessionResults", state="visible")
        self.assertTrue(self.page.locator("#verdictBanner").is_visible())

        # Check visual gauges
        self.assertTrue(self.page.locator("#batteryCirclePath").is_visible())
        self.assertTrue(self.page.locator("#storageWearFill").is_visible())
        battery_pct = self.page.locator("#batteryHealthDialText").text_content()
        self.assertIn("%", battery_pct)

        # Check findings rendered
        findings = self.page.locator(".finding-card")
        self.assertGreater(findings.count(), 0)

        # Toggle evidence on first card
        first_toggle = self.page.locator(".evidence-toggle").first
        first_toggle.click()
        self.assertTrue(self.page.locator("#ev-0").is_visible())

        # Check claim comparison table
        self.page.click("button[data-subtab='subtab-comparison']")
        self.page.wait_for_selector("#subtab-comparison", state="visible")
        self.assertGreater(self.page.locator("#comparisonTableBody tr").count(), 0)

        # Check coverage table
        self.page.click("button[data-subtab='subtab-coverage']")
        self.page.wait_for_selector("#subtab-coverage", state="visible")
        self.assertGreater(self.page.locator("#coverageTableBody tr").count(), 0)

        # Check manual checklist and click PASS on first item
        self.page.click("button[data-subtab='subtab-manual']")
        self.page.wait_for_selector("#subtab-manual", state="visible")
        pass_btn = self.page.locator(".check-btn[data-val='passed']").first
        pass_btn.click()
        self.page.wait_for_timeout(300)
        self.assertIn("active-pass", pass_btn.get_attribute("class") or "")

    def test_expert_telemetry_mode(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # Enable Expert Mode
        self.page.click(".slider")
        self.page.wait_for_selector("#expertConfigPanel", state="visible")

        # Load reference sample
        self.page.click("#loadSampleBtn")
        self.page.wait_for_selector("#sessionResults", state="visible")

        # Thermal gauge card is visible in Expert Mode
        self.assertTrue(self.page.locator("#thermalDialCard").is_visible())

        # Expert tab button is visible
        self.assertTrue(self.page.locator(".expert-tab-btn").is_visible())
        self.page.click(".expert-tab-btn")
        self.page.wait_for_selector("#subtab-expert", state="visible")

        # Check expert tables are populated
        self.assertGreater(self.page.locator("#expertCpuTable tr").count(), 0)
        self.assertGreater(self.page.locator("#expertBatteryTable tr").count(), 0)
        self.assertGreater(self.page.locator("#expertStorageTable tr").count(), 0)
        self.assertGreater(self.page.locator("#expertSystemTable tr").count(), 0)
        self.assertGreater(self.page.locator("#expertOsRefurbishTable tr").count(), 0)

    def test_interactive_tools_suite(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # 1. Screen Pixel Tester: navigate to Screen Studio tab
        self.page.click("button[data-tab='tab-screen']")
        self.page.wait_for_selector("#tab-screen", state="visible")
        self.page.click("#launchScreenTestBtn")
        self.page.wait_for_selector("#screenTestOverlay", state="visible")
        self.page.click("#screenTestOverlay")
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(200)
        self.assertFalse(self.page.locator("#screenTestOverlay").is_visible())

        # 2. Audio Tester Controls: navigate to Audio & Camera tab
        self.page.click("button[data-tab='tab-media']")
        self.page.wait_for_selector("#tab-media", state="visible")
        freq_val = self.page.locator("#audioFreqVal").inner_text()
        self.assertIn("Hz", freq_val)
        self.page.click("#playToneBtn")
        self.page.wait_for_timeout(100)
        self.assertEqual(self.page.locator("#playToneBtn").inner_text(), "Stop Tone")
        self.page.click("#playToneBtn")
        self.page.wait_for_timeout(100)
        self.assertEqual(self.page.locator("#playToneBtn").inner_text(), "Play Tone")

        # 3. Trackpad Canvas: navigate to Input & Trackpad tab
        self.page.click("button[data-tab='tab-input']")
        self.page.wait_for_selector("#tab-input", state="visible")
        canvas = self.page.locator("#trackpadCanvas")
        self.assertTrue(canvas.is_visible())
        canvas.scroll_into_view_if_needed()
        canvas.click(position={"x": 50, "y": 50})
        self.page.wait_for_timeout(150)
        event_text = self.page.locator("#trackpadLastEvent").inner_text()
        self.assertTrue(any(term in event_text for term in ["at", "Click", "Tracking", "Finger"]))

        # 4. Keyboard Matrix Tester (also on tab-input)
        self.page.keyboard.press("KeyA")
        self.page.keyboard.press("KeyS")
        self.page.keyboard.press("Space")
        self.page.wait_for_timeout(200)

        count_text = self.page.locator("#kbVerifiedCount").inner_text()
        self.assertGreaterEqual(int(count_text), 3)

        a_key = self.page.locator("#kb-KeyA")
        self.assertIn("tested", a_key.get_attribute("class") or "")

        # Reset keyboard
        self.page.click("#kbResetBtn")
        self.page.wait_for_timeout(100)
        self.assertEqual(self.page.locator("#kbVerifiedCount").inner_text(), "0")

    def test_history_and_about_pages(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # Check history view
        self.page.click("button[data-tab='tab-history']")
        self.page.wait_for_selector("#tab-history", state="visible")
        self.assertTrue(self.page.locator("#historyTableBody").is_visible())

        # Check About & Donate view
        self.page.click("button[data-tab='tab-about']")
        self.page.wait_for_selector("#tab-about", state="visible")
        self.assertTrue(self.page.locator(".donate-options").is_visible())
        self.assertTrue(self.page.locator(".crypto-box").is_visible())

    def test_screen_studio_and_contrast_ramp(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # Navigate to Screen Studio tab
        self.page.click("button[data-tab='tab-screen']")
        self.page.wait_for_selector("#tab-screen", state="visible")

        # Contrast steps exist
        self.page.wait_for_selector(".contrast-step", state="visible")
        self.assertEqual(self.page.locator(".contrast-step").count(), 16)

        # Sharpness checkerboard canvas exists
        self.assertTrue(self.page.locator("#checkerboardCanvas").is_visible())

        # UFO animation canvas exists
        self.assertTrue(self.page.locator("#ufoCanvas").is_visible())
        self.assertTrue(self.page.locator("#ufoHzText").is_visible())

    def test_ports_and_cooling_pulse_tabs(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # Navigate to Ports tab
        self.page.click("button[data-tab='tab-ports']")
        self.page.wait_for_selector("#tab-ports", state="visible")
        self.assertTrue(self.page.locator("#usbPortsList").is_visible())
        self.assertTrue(self.page.locator("#refreshPortsBtn").is_visible())

        # Navigate to Cooling Pulse tab
        self.page.click("button[data-tab='tab-benchmark']")
        self.page.wait_for_selector("#tab-benchmark", state="visible")
        self.assertTrue(self.page.locator("#runPulseBtn").is_visible())
        self.assertTrue(self.page.locator("#refreshFansBtn").is_visible())
        self.assertTrue(self.page.locator("#btnFanPerformance").is_visible())

    def test_portable_mode_and_export(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # Check App Mode Badge
        self.assertTrue(self.page.locator("#appModeBadge").is_visible())
        badge_text = self.page.locator("#appModeBadge").inner_text()
        self.assertTrue(any(term in badge_text for term in ["PORTABLE", "SYSTEM"]))

        # Verify /api/health exposes portable fields
        resp = self.page.request.get(f"http://{TEST_HOST}:{TEST_PORT}/api/health")
        self.assertTrue(resp.ok)
        health_data = resp.json()
        self.assertIn("portable_mode", health_data)
        self.assertIn("db_path", health_data)
        self.assertIn("reports_dir", health_data)

        # Load synthetic sample session
        self.page.click("#loadSampleBtn")
        self.page.wait_for_selector("#sessionResults", state="visible")

        # Save report directly to USB / reports directory
        save_btn = self.page.locator("#saveUsbReportBtn")
        self.assertTrue(save_btn.is_visible())
        save_btn.click()

        self.page.wait_for_function(
            "document.getElementById('saveUsbReportStatus').textContent.includes('Saved to USB')",
            timeout=5000,
        )
        status_text = self.page.locator("#saveUsbReportStatus").inner_text()
        self.assertIn("Saved to USB", status_text)

        # Verify report files actually exist on disk
        reports_dir = Path(health_data["reports_dir"])
        html_files = list(reports_dir.glob("inspection-*.html"))
        json_files = list(reports_dir.glob("inspection-*.json"))
        self.assertGreater(len(html_files), 0)
        self.assertGreater(len(json_files), 0)

        # Clean up files created during this test
        for f in html_files + json_files:
            if "SAMPLE-USED-T14-DEMO" in f.name:
                f.unlink(missing_ok=True)

    def test_lite_edition_loads_and_runs(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}/lite")
        self.assertIn("Xflash Lite", self.page.title())

        # Check action buttons
        self.assertTrue(self.page.locator("#liteScanBtn").is_visible())
        self.assertTrue(self.page.locator("#quickSampleBtn").is_visible())
        self.assertTrue(self.page.locator("#quickScreenBtn").is_visible())

        # Click Load Demo Sample
        self.page.click("#quickSampleBtn")
        self.page.wait_for_selector("#liteVerdictCard", state="visible")
        self.assertTrue(self.page.locator("#liteVerdictCard").is_visible())
        self.assertTrue(self.page.locator("#liteMetricsGrid").is_visible())
        self.assertTrue(self.page.locator("#liteComparisonCard").is_visible())

        # Verify metrics rendered
        bat_val = self.page.locator("#liteBatVal").text_content()
        self.assertIn("%", bat_val)

    def test_smart_listing_parser_and_bargaining_in_main_app(self):
        self.page.goto(f"http://{TEST_HOST}:{TEST_PORT}")

        # Test smart listing ad parser
        self.page.fill("#listingPasteInputMain", "ThinkPad T14 Gen 2 i7-1165G7 16GB RAM 512GB SSD")
        self.page.click("#extractSpecsBtnMain")
        self.page.wait_for_function("document.getElementById('claimRam').value === '16'", timeout=5000)

        self.assertEqual(self.page.locator("#claimRam").input_value(), "16")
        self.assertEqual(self.page.locator("#claimStorage").input_value(), "512")
        self.assertIn("ThinkPad T14", self.page.locator("#claimModel").input_value())

        # Load reference sample to check comparison and bargaining
        self.page.click("#loadSampleBtn")
        self.page.wait_for_selector("#sessionResults", state="visible")

        # Check comparison tab
        self.page.click("button[data-subtab='subtab-comparison']")
        self.page.wait_for_selector("#subtab-comparison", state="visible")
        self.assertGreater(self.page.locator("#comparisonTableBody tr").count(), 0)


