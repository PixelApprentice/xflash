"""Unit tests for the offline seller listing claim parser."""
import unittest

from xflash.listing_parser import parse_listing_claims, suggest_bargaining_discount


class ListingParserTests(unittest.TestCase):
    def test_parse_standard_thinkpad_listing(self):
        text = "Lenovo ThinkPad T14 Gen 2 14\" FHD (Intel i7-1165G7, 16GB RAM, 512GB SSD NVMe, Win 11 Pro)"
        claims = parse_listing_claims(text)
        self.assertEqual(claims.get("ram_gib"), 16)
        self.assertEqual(claims.get("storage_gb"), 512)
        self.assertIn("1165G7", claims.get("cpu_model", ""))
        self.assertIn("ThinkPad T14", claims.get("model", ""))

    def test_parse_dell_xps_with_terabyte_storage(self):
        text = "Dell XPS 15 9520 OLED 3.5K - Core i9-12900HK - 32 GB RAM - 1 TB SSD - RTX 3050Ti"
        claims = parse_listing_claims(text)
        self.assertEqual(claims.get("ram_gib"), 32)
        self.assertEqual(claims.get("storage_gb"), 1000)
        self.assertIn("12900HK", claims.get("cpu_model", ""))
        self.assertIn("XPS 15", claims.get("model", ""))
        self.assertIn("RTX 3050", claims.get("gpu_model", ""))

    def test_parse_macbook_listing(self):
        text = "Apple MacBook Air 13 M2 8-core CPU 8GB Memory 256GB SSD Space Gray"
        claims = parse_listing_claims(text)
        self.assertEqual(claims.get("ram_gib"), 8)
        self.assertEqual(claims.get("storage_gb"), 256)
        self.assertIn("M2", claims.get("cpu_model", ""))
        self.assertIn("MacBook Air", claims.get("model", ""))

    def test_parse_empty_or_gibberish_returns_empty_dict(self):
        self.assertEqual(parse_listing_claims(""), {})
        self.assertEqual(parse_listing_claims("hello world no specs here"), {})

    def test_suggest_bargaining_discount_clean_laptop(self):
        # When specs match and health is great, no discount suggested
        discount = suggest_bargaining_discount(
            findings=[],
            ram_match=True,
            storage_match=True,
            battery_wear_pct=8,
            thermal_throttling=False,
        )
        self.assertEqual(discount["suggested_discount_usd"], 0)
        self.assertEqual(discount["verdict_code"], "BUY_RECOMMENDED")

    def test_suggest_bargaining_discount_with_discrepancies(self):
        # Battery worn down to 60% health (40% wear) and 8GB RAM shortfall
        discount = suggest_bargaining_discount(
            findings=[{"title": "RAM shortfall", "severity": "warning"}],
            ram_match=False,
            storage_match=True,
            battery_wear_pct=40,
            thermal_throttling=True,
        )
        self.assertGreater(discount["suggested_discount_usd"], 80)
        self.assertEqual(discount["verdict_code"], "NEGOTIATE_DISCOUNT")
        self.assertTrue(len(discount["bargaining_points"]) >= 2)


    def test_parse_listing_with_price(self):
        text = "Lenovo ThinkPad T14 Gen 2 16GB RAM 512GB SSD - Asking $450 cash"
        claims = parse_listing_claims(text)
        self.assertEqual(claims.get("ram_gib"), 16)
        self.assertEqual(claims.get("storage_gb"), 512)
        self.assertEqual(claims.get("asking_price"), 450)

    def test_suggest_bargaining_discount_with_asking_price_and_script(self):
        # Asking $500, with battery wear and RAM shortfall
        discount = suggest_bargaining_discount(
            findings=[{"title": "RAM shortfall", "severity": "warning"}],
            ram_match=False,
            storage_match=True,
            battery_wear_pct=40,
            thermal_throttling=False,
            asking_price=500,
        )
        self.assertEqual(discount["asking_price_usd"], 500)
        self.assertGreater(discount["suggested_discount_usd"], 0)
        self.assertEqual(discount["fair_offer_usd"], 500 - discount["suggested_discount_usd"])
        self.assertIn("negotiation_script", discount)
        self.assertTrue(len(discount["negotiation_script"]) > 20)
        self.assertIn("$", discount["negotiation_script"])


if __name__ == "__main__":
    unittest.main()
