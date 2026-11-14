"""The new supplied Origins map replaces terrain without synthetic edits."""
import hashlib
import json
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-origins/Gilneas_Origins_Map.png')

class OriginsMap(unittest.TestCase):
    def test_new_supplied_map_is_the_actual_enhanced_base(self):
        metadata = json.loads((ROOT/'assets/maps/origins-processing.json').read_text()) if (ROOT/'assets/maps/origins-processing.json').exists() else {}
        self.assertEqual(metadata.get('source_sha256'), hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'New user map must replace the earlier reconstructed terrain')
        self.assertEqual(metadata['source_size'], [3526, 4548])
        self.assertEqual(metadata['enhanced_size'], [5289, 6822])
        self.assertEqual(metadata['terrain_edits'], [])
        for name,size in [('gilneas-origins-enhanced.webp',(5289,6822)),('origins-inactive-mask.png',(3526,4548)),('origins-inactive-mist.webp',(3526,4548))]:
            with Image.open(ROOT/'assets/maps'/name) as image:
                self.assertEqual(image.size,size)
        self.assertEqual(metadata['custom_features_preserved'], ['enlarged Dalaran', 'intact Duskhaven'])

if __name__ == '__main__':
    unittest.main()
