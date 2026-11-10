"""Offline parser for used laptop marketplace listings and bargaining advice generator.

Enables buyers to paste or supply raw text from online listings (eBay, Facebook
Marketplace, Swappa, Craigslist, OLX) and compare detected hardware against
seller representations with zero network transmission.
"""
from __future__ import annotations

import re
from typing import Any


def parse_listing_claims(text: str) -> dict[str, Any]:
    """Extract standard hardware claims from free-form listing text using heuristics.

    Returns a dict compatible with snapshot claims:
    - model: str
    - ram_gib: int
    - storage_gb: int
    - cpu_model: str
    - gpu_model: str
    - display_resolution: str
    """
    if not text or not isinstance(text, str):
        return {}

    cleaned = text.strip()
    if not cleaned:
        return {}

    claims: dict[str, Any] = {}

    # 1. RAM detection
    # Examples: 16GB RAM, 16 GB DDR4, 32GB Memory, 8GB LPDDR5, RAM: 16GB
    ram_match = re.search(r"\b(\d{1,3})\s*(?:gb|gib|g)\s*(?:ddr\d*|lpddr\d*|ram|memory)?\b", cleaned, re.IGNORECASE)
    if ram_match:
        val = int(ram_match.group(1))
        # Sensible laptop RAM bounds: 2 to 256 GB
        if 2 <= val <= 256:
            claims["ram_gib"] = val

    # 2. Storage detection
    # First check TB matches: 1TB SSD, 2 TB NVMe
    tb_match = re.search(r"\b(\d{1,2})\s*(?:tb|tib)\s*(?:ssd|nvme|pcie|storage|disk|hdd|solid)?\b", cleaned, re.IGNORECASE)
    if tb_match:
        claims["storage_gb"] = int(tb_match.group(1)) * 1000
    else:
        # Check all GB matches to find storage (e.g. 512GB SSD, 256GB, etc.)
        for m in re.finditer(r"\b(\d{2,4})\s*(?:gb|gib)\b(?:\s*(ssd|nvme|pcie|storage|disk|hdd|solid\s*state))?", cleaned, re.IGNORECASE):
            sval = int(m.group(1))
            is_explicit_storage = bool(m.group(2))
            if is_explicit_storage:
                claims["storage_gb"] = sval
                break
            elif sval >= 120 and "storage_gb" not in claims:
                claims["storage_gb"] = sval
            elif "ram_gib" in claims and sval != claims["ram_gib"] and "storage_gb" not in claims:
                claims["storage_gb"] = sval

    # 3. CPU detection
    # Examples: i7-1165G7, i5-1240P, Core i9-12900HK, Ryzen 7 5800H, Ryzen 5 4500U, M1 Pro, M2
    cpu_match = re.search(
        r"\b(?:intel\s+|core\s+)?(i[3579][- ]\d{4,5}[A-Z0-9]{0,4}|core\s+ultra\s+[579][- ]\d{3}[A-Z0-9]{0,3}|ryzen\s+[3579][- ]\d{4}[A-Z0-9]{0,3}|m[1234](?:\s+(?:pro|max|ultra))?)\b",
        cleaned,
        re.IGNORECASE,
    )
    if cpu_match:
        claims["cpu_model"] = cpu_match.group(0).strip()

    # 4. GPU detection
    # Examples: RTX 3050, RTX 3050Ti, GTX 1650, Radeon 680M, Iris Xe
    gpu_match = re.search(
        r"\b((?:rtx|gtx)\s*\d{3,4}(?:\s*ti)?|radeon\s*[\w\d]+|iris\s*xe)\b",
        cleaned,
        re.IGNORECASE,
    )
    if gpu_match:
        claims["gpu_model"] = gpu_match.group(0).strip()

    # 5. Model detection
    # Examples: ThinkPad T14 Gen 2, XPS 15 9520, MacBook Air 13, EliteBook 840, Latitude 5420, Vivobook 15
    model_match = re.search(
        r"\b(ThinkPad\s+[\w\d]+(?:\s+Gen\s+\d+)?|XPS\s+\d{2}(?:\s+\d{4})?|MacBook\s+(?:Air|Pro)(?:\s+\d{2})?|EliteBook\s+\d{3}(?:\s+G\d+)?|Latitude\s+\d{4}|Vivobook\s+[\w\d]+|ZenBook\s+[\w\d]+|Surface\s+(?:Laptop|Pro)\s*\d?)\b",
        cleaned,
        re.IGNORECASE,
    )
    if model_match:
        claims["model"] = model_match.group(0).strip()

    # 6. Display resolution
    res_match = re.search(r"\b(\d{3,4}\s*[xX*]\s*\d{3,4}|FHD|QHD|4K|3\.5K|OLED)\b", cleaned)
    if res_match:
        claims["display_resolution"] = res_match.group(0).strip()

    return claims


def suggest_bargaining_discount(
    findings: list[dict[str, Any]],
    ram_match: bool = True,
    storage_match: bool = True,
    battery_wear_pct: float | None = None,
    thermal_throttling: bool = False,
    media_errors: int = 0,
) -> dict[str, Any]:
    """Calculate buyer bargaining leverage and plain-English discount points.

    Returns:
    - suggested_discount_usd: int
    - verdict_code: "BUY_RECOMMENDED" | "NEGOTIATE_DISCOUNT" | "DO_NOT_BUY"
    - summary: str
    - bargaining_points: list[str]
    """
    discount = 0
    points: list[str] = []
    critical_defect = False

    # Check critical media errors
    if media_errors > 0:
        critical_defect = True
        points.append(
            f"Drive has {media_errors} unrecoverable hardware media errors. Drive failure is imminent; replace immediately."
        )

    # Battery degradation check
    if battery_wear_pct is not None:
        if battery_wear_pct >= 40:
            discount += 75
            points.append(
                f"Battery is degraded by {battery_wear_pct:.0f}% (only {100 - battery_wear_pct:.0f}% health). Replacement battery costs $60–$90."
            )
        elif battery_wear_pct >= 20:
            discount += 45
            points.append(
                f"Battery is degraded by {battery_wear_pct:.0f}%. Expect shortened run-time. Negotiate $40–$50 off."
            )

    # RAM shortfall
    if not ram_match:
        discount += 50
        points.append("RAM capacity is lower than the seller listing promised. Negotiate $40–$60 off.")

    # Storage shortfall
    if not storage_match:
        discount += 50
        points.append("Storage drive capacity is lower than advertised in the listing. Negotiate $40–$60 off.")

    # Thermal throttling
    if thermal_throttling:
        discount += 40
        points.append("CPU thermal throttling detected under brief load. Fans or thermal paste need immediate servicing ($30–$50).")

    # High severity findings
    for finding in findings:
        severity = finding.get("severity", "")
        if severity == "critical":
            critical_defect = True
            points.append(f"Critical Hardware Issue: {finding.get('title', 'Unknown defect')}")
        elif severity == "warning" and not any(p.startswith("Battery") for p in points if "Battery" in finding.get("title", "")):
            if discount < 150:
                discount += 25

    if critical_defect:
        verdict_code = "DO_NOT_BUY"
        summary = "DO NOT BUY: Laptop exhibits severe hardware defects or imminent drive failure."
    elif discount > 0:
        verdict_code = "NEGOTIATE_DISCOUNT"
        summary = f"NEGOTIATE ${discount} OFF: Discrepancies or component wear justify a lower price."
    else:
        verdict_code = "BUY_RECOMMENDED"
        summary = "SAFE TO BUY: Physical hardware matches listing claims with healthy diagnostics."

    return {
        "suggested_discount_usd": discount,
        "verdict_code": verdict_code,
        "summary": summary,
        "bargaining_points": points,
    }
