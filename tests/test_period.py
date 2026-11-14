import unittest
import importlib.util
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class PeriodMapTest(unittest.TestCase):
    def test_does_not_present_a_wall_or_dalaran_crater_as_pre_wall_terrain(self):
        script=ROOT/'scripts/adapt_period.py'
        self.assertTrue(script.exists(),'the supplied postwar render is not adapted to the requested period')
        spec=importlib.util.spec_from_file_location('adapt',script)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        original=Image.open('/Users/daniil_si/.hermes/cache/scratch/gilneas-originals/Gilneas_Map.png').convert('RGB')
        mask,metadata=m.period_mask(original)
        self.assertEqual(mask.size,original.size)
        self.assertGreater(mask.getpixel((2270,2690)),0,'wall crossing must be removed')
        self.assertGreater(mask.getpixel((2900,1550)),0,'modern crater must be replaced')
        self.assertEqual(mask.getpixel((1800,3370)),0,'Gilneas city geometry is preserved')
        self.assertEqual(mask.getpixel((150,2000)),0,'western sea is not invented')
        self.assertIn('reconstruction',metadata['status'])
if __name__=='__main__':unittest.main()
