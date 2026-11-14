"""Preserve the supplied terrain; derive inactivity from its correction."""
from pathlib import Path
import json
import hashlib
import argparse
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
from scipy.ndimage import label, binary_dilation, binary_fill_holes


def inactive_mask(original, correction):
    if original.size != correction.size:
        raise ValueError('Correction and original must use the same pixel space')
    a = np.asarray(original.convert('RGB')).astype(np.int16)
    b = np.asarray(correction.convert('RGB')).astype(np.int16)
    # Difference is the annotation: do not select natural black water/terrain.
    strokes = (np.max(a - b, axis=2) > 12) & (np.sum(b, axis=2) < np.sum(a, axis=2) * .9)
    barrier = binary_dilation(strokes, iterations=3)
    regions, count = label(~barrier)
    active = int(regions[original.height // 2, original.width // 10])
    if not active:
        raise ValueError('Active sea sample is occluded')
    mask = regions != active
    mask = binary_fill_holes(mask)
    raw = Image.fromarray(mask.astype(np.uint8) * 255)
    metadata = {
        'source_size': list(original.size), 'method': 'difference strokes + boundary-connected flood fill',
        'marked_pixels': int(strokes.sum()), 'inactive_pixels': int(mask.sum()),
        'free_regions': int(count), 'edge_feather_px': 18,
        'notes': 'Annotation is a work-scope mask, not a canonical political boundary.'
    }
    return raw, metadata


def enhanced_map(original):
    # Recover legibility without generating or inventing land details.
    im = original.convert('RGB')
    im = ImageEnhance.Brightness(im).enhance(1.19)
    im = ImageEnhance.Color(im).enhance(1.08)
    im = ImageEnhance.Contrast(im).enhance(1.035)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.3, percent=115, threshold=3))
    target = (int(round(im.width * 1.5)), int(round(im.height * 1.5)))
    return im.resize(target, Image.Resampling.LANCZOS).filter(ImageFilter.UnsharpMask(radius=.85, percent=65, threshold=3))


def mist_overlay(original, mask):
    # Keep silhouettes visible; fog changes opacity, never the coastline.
    w, h = original.size
    soft = mask.filter(ImageFilter.GaussianBlur(18))
    rng = np.random.default_rng(73)
    small = (rng.random((96, 64)) * 255).astype(np.uint8)
    clouds = Image.fromarray(small).resize((w, h), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(45))
    cloud = np.asarray(clouds).astype(float) / 255
    alpha = np.asarray(soft).astype(float) * (.64 + .12 * cloud)
    result = np.zeros((h,w,4), dtype=np.uint8)
    result[:,:,:3] = np.dstack([15 + 11 * cloud, 20 + 13 * cloud, 23 + 16 * cloud]).astype(np.uint8)
    result[:,:,3] = alpha.astype(np.uint8)
    return Image.fromarray(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', required=True, type=Path)
    parser.add_argument('--correction', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    original = Image.open(args.original).convert('RGB')
    correction = Image.open(args.correction).convert('RGB')
    mask, metadata = inactive_mask(original, correction)
    mask.save(args.output/'inactive-mask.png', optimize=True)
    mist = mist_overlay(original, mask)
    mist.save(args.output/'inactive-mist.webp', lossless=True, method=6)
    enhanced = enhanced_map(original)
    enhanced.save(args.output/'gilneas-enhanced.webp', quality=94, method=6)
    # Work preview only; not a replacement for the full resolution map.
    preview = enhanced.resize(original.size, Image.Resampling.LANCZOS).convert('RGBA')
    preview.alpha_composite(mist)
    preview.thumbnail((1000,1500))
    preview.convert('RGB').save(args.output/'processing-preview.jpg', quality=93)
    metadata.update({
        'source_sha256': hashlib.sha256(args.original.read_bytes()).hexdigest(),
        'correction_sha256': hashlib.sha256(args.correction.read_bytes()).hexdigest(),
        'enhanced_size': list(enhanced.size),
        'upscale': '1.5x Lanczos + conservative contrast/color/unsharp; no generative details',
        'output_bytes': {p.name:p.stat().st_size for p in args.output.iterdir() if p.is_file()}
    })
    (args.output/'map-processing.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(json.dumps(metadata, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
