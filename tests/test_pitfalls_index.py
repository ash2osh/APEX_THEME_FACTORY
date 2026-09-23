from pathlib import Path
import re
import unittest

KNOWLEDGE = Path(__file__).resolve().parent.parent / ".agents/knowledge"
INDEX = KNOWLEDGE / "pitfalls.md"
LAYERS = KNOWLEDGE / "pitfalls"
ENTRY = re.compile(r"^### (\S+) ", re.MULTILINE)


class PitfallsIndexTests(unittest.TestCase):
    def entries(self):
        return [(layer, entry) for layer in sorted(LAYERS.glob("*.md"))
                for entry in ENTRY.findall(layer.read_text(encoding="utf-8"))]

    def test_every_layer_entry_is_listed_in_the_index(self):
        index = INDEX.read_text(encoding="utf-8")
        entries = self.entries()
        self.assertGreaterEqual(len(entries), 51)
        for layer, entry in entries:
            self.assertIn(f"**§{entry}**", index, f"{layer.name}: §{entry} missing from the index")

    def test_entry_numbers_are_unique(self):
        numbers = [entry for _layer, entry in self.entries()]
        self.assertEqual(len(numbers), len(set(numbers)))

    def test_index_links_resolve(self):
        for target in re.findall(r"\]\((pitfalls/[^)]+)\)", INDEX.read_text(encoding="utf-8")):
            self.assertTrue((KNOWLEDGE / target).is_file(), target)

    def test_index_is_short_enough_to_skim(self):
        self.assertLess(len(INDEX.read_text(encoding="utf-8")), 12000)
