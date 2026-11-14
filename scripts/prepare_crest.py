"""Put only the old Gilneas emblem on the atlas's plain five-sided shield."""
import base64
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, gaussian_filter, label

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/ui/gilneas-human-banner.png'
BBOX = (89, 71, 211, 165)
GOLD = (225, 201, 148)


def main():
    gray = np.array(Image.open(SOURCE).convert('L').crop(BBOX))
    components, _ = label(gray > 110)
    # Actual source ink: main device and the two detached lower-right marks.
    # The thin cloth highlight at bottom left is deliberately excluded.
    sizes = np.bincount(components.ravel())
    selected = [int(index) for index in range(1, len(sizes)) if sizes[index] >= 90]
    mask = binary_fill_holes(np.isin(components, selected))
    alpha = np.rint(gaussian_filter(mask.astype(float), .4) * 255).astype('uint8')
    pixels = np.zeros((*gray.shape, 4), dtype='uint8')
    pixels[:, :, :3] = GOLD
    pixels[:, :, 3] = alpha
    symbol = ROOT / 'assets/ui/gilneas-symbol.png'
    Image.fromarray(pixels).save(symbol)
    encoded = base64.b64encode(symbol.read_bytes()).decode('ascii')
    shield = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 72" width="60" height="72">
  <title>Гилнеас</title>
  <path d="M1 1H59V46.4L30 71 1 46.4Z" fill="#697c95" stroke="#e1c994" stroke-width="1.2"/>
  <image x="9" y="13" width="42" height="33" href="data:image/png;base64,{encoded}"/>
</svg>
'''
    (ROOT / 'assets/ui/gilneas-shield.svg').write_text(shield)
    metadata = {
        'source': 'assets/ui/gilneas-human-banner.png',
        'sourceUrl': 'https://wowpedia.fandom.com/wiki/File:Gineas.jpg',
        'sourceSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'sourceCrop': list(BBOX),
        'selectedComponentPixels': [int(sizes[index]) for index in selected],
        'treatment': 'UI-only emblem extraction, transparent alpha, brass tint on the existing plain blue-gray shield; not an unaltered manual image.',
        'shield': 'assets/ui/gilneas-shield.svg',
        'symbol': 'assets/ui/gilneas-symbol.png',
    }
    (ROOT / 'docs/crest-treatment.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
