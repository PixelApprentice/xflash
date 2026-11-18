"""Demo backend: fixed sample data, used for development, screenshots and tests.

It is also the reference implementation of the Backend contract. The UI marks it
DEMO DATA everywhere, so it can never be mistaken for a real inspection.
"""
from __future__ import annotations

import math
import random
import threading
from typing import Callable, Optional

from .backend import (Backend, CheckUpdate, PulseSample, ScanFailed, ScanFinished, ScanOptions,
                      ScanStarted)
from .model import (Bars, Bay, Chart, Finding, Grid, Hist, Keycaps, KV, Lines, Page, Session,
                    SessionRef, Status)

P, W, F, C, O = Status.PASS, Status.WARN, Status.FAIL, Status.CLAIM, Status.OPEN

# name, final status, seconds, text, bay index
CHECKS = [
    ("profile", P, 0.4, "standard keyboard · touchpad · webcam", None),
    ("drive", P, 0.3, "SSD · NVMe 1.4 · PCIe Gen4 x4 · M.2 2280", 1),
    ("battery", W, 0.2, "full 43,200 / design 60,000 mWh", 0),
    ("smart", P, 0.3, "spare 100 % · used 8 % · media errors 0", 1),
    ("memory", P, 0.1, "16 GiB · 2×8 · dual · 3,200 MT/s", 2),
    ("processor", C, 0.1, "i7-1165G7 · claimed i7-1185G7", 3),
    ("display", P, 0.6, "BOE · IPS · 10-bit · 59.98 Hz", 5),
    ("os", W, 0.2, "installed 14 d ago · drive 142 d", None),
    ("cooling", P, 0.5, "pkg 51 °C · fan 2,380 rpm", 4),
    ("usb", W, 0.3, "right port negotiated 480 Mb/s", None),
    ("audio", W, 0.4, "headphone output no signal", None),
    ("keys", P, 0.2, "31 of 40 keys read", None),
]


def _curve(a, b, n=30, k=3.0):
    return [round(a + (b - a) * (1 - math.exp(-k * i / (n - 1))) / (1 - math.exp(-k)), 1) for i in range(n)]


def build_demo_session() -> Session:
    rnd = random.Random(7)
    drive_temp = [38 + rnd.choice([0, 0, 1, -1, 2, 5, 8, 6, 3, 0, -2]) for _ in range(30)]
    bays = [
        Bay("BAT", "72.0 %", W, bar=0.72, plain="72.0 % retention", target="rules", rule="BAT-01"),
        Bay("SSD", "NVMe · 8 % used", P, bar=0.93, plain="NVMe · 8 % used", target="storage"),
        Bay("MEM", "16.0 GiB", P, sub="2×8 · 3200 MT/s", plain="16.0 GiB", target="memory"),
        Bay("CPU", "44 °C", C, sub="i7-1165G7", plain="i7-1165G7 · 44 °C", target="thermal"),
        Bay("FAN", "2,100 rpm", P, spark=[2100, 2200, 2300, 2400, 2500, 2600, 2700, 2880],
            plain="2,100 rpm", target="thermal"),
        Bay("DSP", "60 Hz · 10-bit", O, sub="BOE IPS", plain="60 Hz · 10-bit", target="display"),
    ]
    findings = [
        Finding("BAT-01", "Capacity retention", W, "72.0 %", "threshold 80 %", "Battery capacity retention", [
            KV("Evaluation", [("Metric", "full / design capacity"), ("Observed", "72.0 %  43,200 / 60,000 mWh"),
                              ("Threshold", "at least 80 %"), ("Result", "@warn"),
                              ("Cycle count", "300"), ("Chemistry", "LiP · SMP")]),
            Bars("Retention across sessions", [("Nov 02", 0.91, "91 %", "p"), ("Nov 09", 0.88, "88 %", "p"),
                                               ("Nov 13", 0.72, "72 %", "w")]),
            Lines("sysfs power_supply/BAT0", ["energy_full_design  60000000 µWh", "energy_full         43200000 µWh",
                                              "voltage_now         11400000 µV"]),
        ]),
        Finding("CLM-02", "Processor model", F, "differs", "listing i7-1185G7", "Processor model vs listing", [
            KV("Evaluation", [("Metric", "cpuid brand string"), ("Observed", "i7-1165G7"),
                              ("Listing", "i7-1185G7"), ("Result", "@fail")])]),
        Finding("PRT-04", "Headphone output", W, "no signal", "", "Headphone output", [
            KV("Evaluation", [("Metric", "loopback level"), ("Observed", "no signal"), ("Result", "@warn")])]),
        Finding("USB-03", "USB-A right link speed", W, "480 Mb/s", "expected 5,000", "USB-A right link speed", [
            KV("Evaluation", [("Metric", "negotiated link"), ("Observed", "480 Mb/s"),
                              ("Expected", "5,000 Mb/s"), ("Result", "@warn")])]),
        Finding("OS-01", "Install vs drive age", W, "128 d", "limit 30 d", "OS install age vs drive age", [
            KV("Evaluation", [("Metric", "days between install and drive first use"), ("Observed", "128 d"),
                              ("Limit", "30 d"), ("Result", "@warn")])]),
        Finding("SCR-01", "Dead pixel test", O, "not run", "", "Dead pixel test", [
            KV("Evaluation", [("Metric", "manual, 4 fills"), ("Observed", "not run"), ("Result", "@open")])]),
        Finding("STO-01", "Drive percentage used", P, "8 %", "limit 80 %", "Drive percentage used", [
            KV("Evaluation", [("Metric", "NVMe percentage used"), ("Observed", "8 %"),
                              ("Limit", "80 %"), ("Result", "@pass")])]),
    ]
    pages = {
        "storage": Page("storage", "Storage", "STORAGE", "drive 0 · nvme0n1", "2 of 6 bays", [
            [KV("Drive identification", [("Media type", "SSD (0 RPM)"), ("Protocol", "NVMe 1.4"),
                                         ("Transport", "PCIe Gen4 x4"), ("Form factor", "M.2 2280"),
                                         ("Model", "Samsung PM9A1 512 GB")]),
             KV("NVMe health log", [("Critical warning", "0x00"), ("Temperature", "38 °C"),
                                    ("Available spare", "100 %"), ("Percentage used", "8 %"),
                                    ("Data written", "27,730,118 units"), ("Power on hours", "3,412"),
                                    ("Unsafe shutdowns", "12"), ("Media errors", "0")])],
            [Chart("TEMP", drive_temp, 30, 50, "drive temperature, °C", "last 30 s · limit 70", height=4),
             Bars("WEAR", [("used", 0.08, "8 %", "p"), ("written", 14.2 / 300, "14.2 of 300 TB", "p"),
                           ("spare", 1.0, "100 %", "p")]),
             Lines("Attributes read by drive type", ["NVMe  health log", "SATA  5 9 177 179 194 241",
                                                     "HDD   5 9 10 188 193 197 198"])]]),
        "thermal": Page("thermal", "Thermal", "THERMAL", "bay 4 and 5 · pulse 5 s",
                        "rise 1.8 °C/s · median 44 °C", [
            [Chart("PKG", _curve(44, 58), 40, 60, "package °C during the 5 s pulse", "0 s", "5 s"),
             Chart("FAN", [round(x) for x in _curve(2100, 2880)], 2000, 3000, "rpm during the pulse", "0 s", "5 s",
                   role="p")],
            [KV("Platform profiles", [("Performance", "3,400 rpm · peak 61 °C"),
                                      ("Balanced  ◂", "2,880 rpm · peak 58 °C"),
                                      ("Whisper", "1,900 rpm · peak 66 °C")]),
             KV("Sensors", [("coretemp pkg", "44 °C"), ("core 0 to 3", "41 / 43 / 42 / 44 °C"), ("acpitz", "40 °C"),
                            ("nvme", "38 °C"), ("fan1", "2,140 rpm"), ("PROCHOT#", "clear"),
                            ("throttle events", "0")])]]),
        "memory": Page("memory", "Memory", "MEM", "LPDDR4X · dual channel", "", [
            [KV("Memory", [("Capacity", "16.0 GiB"), ("Layout", "2 × 8 GiB · dual channel"),
                           ("Speed", "3,200 MT/s"), ("Type", "LPDDR4X")])]]),
        "display": Page("display", "Display", "DSP", "BOE · IPS · 10-bit", "", [
            [KV("Display", [("Panel", "BOE · IPS"), ("Depth", "10-bit"), ("Refresh", "59.98 Hz"),
                            ("Dead pixel test", "@open")]),
             Lines("", ["Run :screen for the dead pixel, grayscale and refresh checks."])]]),
        "keys": Page("keys", "Keyboard", "INPUT", "keyboard and touchpad", "read only", [
            [Keycaps("KEYS", ["1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"], "5T",
                     {"J": "3 bounces · worst 22 ms", "Space": "1 bounce · 9 ms"}, 31, 40,
                     "ANSI · 83 keys · no number pad · touchpad",
                     "Absent, skipped  TrackPoint · touchscreen · number pad"),
             KV("Flagged keys", [("J", "3 bounces · worst 22 ms"), ("Space", "1 bounce · 9 ms")])],
            [Hist("BOUNCE", [("0 to 5", 210), ("5 to 10", 14), ("10 to 20", 6), ("20 to 35", 2),
                             ("35 and up", 3)], "interval, ms", "threshold 35 ms"),
             Grid("PAD", [[98, 97, 99], [96, 100, 95], [0, 93, 94]], "touchpad zones, % response",
                  "one dead zone, bottom left")]]),
    }
    return Session("xps13-2026-11-15", "Dell XPS 13 9310", bays, findings, DEMO_MACHINE, pages,
                   "xflash_reports/xps13-2026-11-15.html")


DEMO_MACHINE = {"Vendor": "Dell Inc.", "Product": "XPS 13 9310", "BIOS": "3.2.1 · 2022-03-14",
                "Chassis": "10 · Notebook", "OS": "Windows 11 Home", "Boot": "UEFI · GPT · Secure Boot on",
                "Serial": "redacted"}


class DemoBackend(Backend):
    name = "demo"
    is_demo = True

    def __init__(self, delay: float = 0.4):
        self.delay = delay
        self._session = build_demo_session()

    def machine(self):
        return dict(DEMO_MACHINE)

    def history(self):
        return [SessionRef("9f2c4e7a", "Nov 13", 1, 4), SessionRef("3b81d0c2", "Nov 09", 0, 0),
                SessionRef("c4a7e911", "Nov 02", 2, 3)]

    def events(self):
        """Scan events in order; the CLI's --once scan snapshot reuses this without sleeping."""
        s, pulse = self._session, _curve(40, 60)
        yield ScanStarted([c[0] for c in CHECKS])
        for i, (_, status, secs, text, bay) in enumerate(CHECKS):
            yield CheckUpdate(i, Status.RUNNING, bay=bay)
            yield CheckUpdate(i, status, secs, text, bay, s.bays[bay] if bay is not None else None)
            for v in pulse[i * 30 // len(CHECKS):(i + 1) * 30 // len(CHECKS)]:
                yield PulseSample(v)
        yield ScanFinished(s)

    def scan(self, opts: ScanOptions, emit: Callable, cancel: threading.Event):
        for ev in self.events():
            if cancel.is_set():
                return
            emit(ev)
            if isinstance(ev, CheckUpdate) and ev.status is Status.RUNNING:
                cancel.wait(self.delay)

    def load(self, ref: str) -> Session:
        return self._session

    def export(self, session, fmt, path):
        raise RuntimeError("demo backend does not write files")

    def tool(self, name: str):
        return f"demo: the {name} tool is not available"
