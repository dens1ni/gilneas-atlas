"""Enhance the supplied custom map; carry the author's old work mask forward."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from prepare_map import mist_overlay

ROOT = Path(__file__).resolve().parents[1]
# Include the enlarged ground city and its north/east bridges. This is an
# activity override, not a claim of a canon cadastral or coastline polygon.
DALARAN_ACTIVE = [(2650,1300),(2760,1230),(2870,1130),(2950,1140),
                  (3005,1210),(3110,1190),(3270,1090),(3410,1150),
                  (3430,1330),(3370,1450),(3365,1570),(3250,1730),
                  (3100,1795),(2940,1775),(2780,1690),(2680,1540)]


def enhance(original):
    image = ImageEnhance.Brightness(original).enhance(1.14)
    image = ImageEnhance.Color(image).enhance(1.055)
    image = ImageEnhance.Contrast(image).enhance(1.025)
    image = image.filter(ImageFilter.UnsharpMask(radius=1.15, percent=100, threshold=3))
    size = (round(original.width * 1.5), round(original.height * 1.5))
    return image.resize(size, Image.Resampling.LANCZOS).filter(
        ImageFilter.UnsharpMask(radius=.8, percent=60, threshold=3))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--registration', required=True, type=Path)
    parser.add_argument('--old-mask', default=ROOT/'assets/maps/inactive-mask.png', type=Path)
    parser.add_argument('--output', default=ROOT/'assets/maps', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    original = Image.open(args.source).convert('RGB')
    registration = json.loads(args.registration.read_text())
    old_mask = np.array(Image.open(args.old_mask).convert('L'))
    mask_array = cv2.warpPerspective(old_mask, np.array(registration['homography']),
                                    original.size, flags=cv2.INTER_NEAREST,
                                    borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    mask = Image.fromarray(mask_array)
    ImageDraw.Draw(mask).polygon(DALARAN_ACTIVE, fill=0)
    mask.save(args.output/'origins-inactive-mask.png', optimize=True)
    mist = mist_overlay(original, mask)
    mist.save(args.output/'origins-inactive-mist.webp', lossless=True, method=6)
    image = enhance(original)
    image.save(args.output/'gilneas-origins-enhanced.webp', quality=95, method=6)
    preview = image.resize(original.size, Image.Resampling.LANCZOS).convert('RGBA')
    preview.alpha_composite(mist)
    preview.thumbnail((1163,1500))
    preview.convert('RGB').save(args.output/'origins-processing-preview.jpg', quality=95)
    metadata = {
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'source_size': list(original.size), 'enhanced_size': list(image.size),
        'upscale': '1.5x Lanczos; brightness 1.14, color 1.055, contrast 1.025; conservative unsharp',
        'terrain_edits': [],
        'custom_features_preserved': ['enlarged Dalaran', 'intact Duskhaven'],
        'activity_method': 'registered original author-correction mask with enlarged-Dalaran active override',
        'registration': registration,
        'dalaran_active_override': DALARAN_ACTIVE,
        'old_mask_sha256': hashlib.sha256(args.old_mask.read_bytes()).hexdigest(),
        'inactive_pixels': int((np.array(mask)>127).sum()),
        'notes': 'No synthetic towers, crater replacement, coastline or wall retouching applied to the new source. Source coordinates stay in the original 3526 x 4548 space.',
        'assets_bytes': {name:(args.output/name).stat().st_size for name in
                         ['gilneas-origins-enhanced.webp','origins-inactive-mask.png','origins-inactive-mist.webp']},
    }
    (args.output/'origins-processing.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(metadata,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
