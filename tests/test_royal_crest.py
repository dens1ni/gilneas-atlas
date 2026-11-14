"""The supplied silver emblem replaces the old sign, not the shield shape."""
import hashlib
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-origins/Gilneas_Royal_Banner.png')

class RoyalCrest(unittest.TestCase):
    def test_user_emblem_and_palette_keep_the_existing_shield_outline(self):
        metadata=json.loads((ROOT/'docs/royal-crest-treatment.json').read_text()) if (ROOT/'docs/royal-crest-treatment.json').exists() else {}
        self.assertEqual(metadata.get('sourceSha256'),hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'Use the precise new emblem supplied by the user')
        self.assertEqual(metadata['field'],'#131516')
        self.assertEqual(metadata['edge'],'#65707b')
        self.assertEqual(metadata['shape'],'M1 1H59V46.4L30 71 1 46.4Z')
        svg=ET.parse(ROOT/'assets/ui/gilneas-royal-shield.svg').getroot()
        self.assertEqual(svg.attrib['viewBox'],'0 0 60 72')
        path=svg.find('{http://www.w3.org/2000/svg}path')
        self.assertEqual(path.attrib['d'],metadata['shape'])
        self.assertEqual(path.attrib['fill'],metadata['field'])
        self.assertEqual(path.attrib['stroke'],metadata['edge'])
        with Image.open(ROOT/'assets/ui/gilneas-royal-symbol.png') as image:
            self.assertEqual(image.mode,'RGBA')
            self.assertEqual(image.getchannel('A').getextrema(),(0,255))
            self.assertEqual(image.getchannel('A').getpixel((0,0)),0)
        self.assertEqual(len(metadata['selectedComponents']),3,'Include both detached silver strokes')

if __name__=='__main__':unittest.main()
