import unittest
import importlib.util
from pathlib import Path
import tempfile
import os

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'prepare_map.py'
SOURCE = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-originals')

class CorrectedMapTest(unittest.TestCase):
    def test_marks_annotated_regions_not_natural_sea_or_cities(self):
        self.assertTrue(SCRIPT.exists(), 'map processor has not been implemented')
        spec = importlib.util.spec_from_file_location('prepare_map', SCRIPT)
        processor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(processor)
        from PIL import Image
        original = Image.open(SOURCE / 'Gilneas_Map.png').convert('RGB')
        correction = Image.open(SOURCE / 'Gilneas_Map_Corretion_Area.png').convert('RGB')
        mask, metadata = processor.inactive_mask(original, correction)
        self.assertEqual(mask.size, original.size)
        self.assertGreater(mask.getpixel((1800, 150)), 240, 'north annotations must become an inactive region')
        self.assertGreater(mask.getpixel((3120, 2200)), 240, 'east annotations must become an inactive region')
        self.assertEqual(mask.getpixel((3000, 250)), 0, 'Lordaeron outside annotations remains active')
        self.assertEqual(mask.getpixel((2900, 1550)), 0, 'Dalaran outside annotations remains active')
        self.assertEqual(mask.getpixel((150, 2000)), 0, 'dark natural sea is not an annotation')
        self.assertEqual(mask.getpixel((1850, 3500)), 0, 'Gilneas remains active')
        self.assertEqual(metadata['source_size'], [3247,4860])
        self.assertGreater(metadata['marked_pixels'], 100000)

if __name__ == '__main__':
    unittest.main()
