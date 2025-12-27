import sys
from pathlib import Path
import unittest

# Add repo root to path to import parse_court_docs.py
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from parse_court_docs import map_desc_to_code, parse_events_table  # type: ignore


class TestParserLogic(unittest.TestCase):
    def test_map_desc_to_code_keywords(self):
        """Verify description keyword mappings."""
        cases = [
            ("Petition for Guardianship", "PGII"),
        ("Notice of Hearing", "NOH"),
        ("Proof of Service", "POS"),
        ("Order Appointing Guardian", "OAF"),
        ("Letters of Authority", "LET"),
        ("Objection to Petition", "PGII"),  # contains "PETITION" so maps to PGII with current order
        ("Random Unknown Document", ""),
        ]
        for desc, expected in cases:
            self.assertEqual(map_desc_to_code(desc), expected, f"Failed to map '{desc}'")

    def test_parse_events_table_basic_rows(self):
        """Row regex should capture standard MiCOURT table lines."""
        sample = """
        Event Date  Description             Event No
        01/06/2025  PETITION GUARDIANSHIP   1
        01/08/2025  NOTICE OF HEARING       2
        02/10/2025  ORDER APPOINTING        3
        """
        events = parse_events_table(sample, "2025-TEST", {}, {}, "MiCourt_Events.txt")
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].filed_date, "01/06/2025")
        self.assertEqual(events[0].event_type_code, "PGII")
        self.assertEqual(events[1].event_type_code, "NOH")

    def test_parse_events_table_irregular_spacing(self):
        """Regex should handle irregular spacing from OCR."""
        sample = """
        01/06/2025    PETITION      1
        01/08/2025 NOTICE OF HEARING 2
        """
        events = parse_events_table(sample, "2025-TEST", {}, {}, "MiCourt_Events.txt")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1].event_type_code, "NOH")


if __name__ == "__main__":
    unittest.main()
