"""Reproducible final assets from the user's two immutable originals."""
import json
import hashlib
from pathlib import Path
from PIL import Image
from prepare_map import inactive_mask, mist_overlay, enhanced_map
from adapt_period import adapted

SOURCE=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-originals')
OUT=Path(__file__).resolve().parents[1]/'assets/maps'
original_path=SOURCE/'Gilneas_Map.png'
correction_path=SOURCE/'Gilneas_Map_Corretion_Area.png'
original=Image.open(original_path).convert('RGB')
correction=Image.open(correction_path).convert('RGB')
mask,metadata=inactive_mask(original,correction)
period,period_mask,period_metadata=adapted(original)
enhanced=enhanced_map(period)
OUT.mkdir(parents=True,exist_ok=True)
enhanced.save(OUT/'gilneas-enhanced.webp',quality=94,method=6)
mask.save(OUT/'inactive-mask.png',optimize=True)
mist=mist_overlay(original,mask)
mist.save(OUT/'inactive-mist.webp',lossless=True,method=6)
preview=enhanced.resize(original.size,Image.Resampling.LANCZOS).convert('RGBA')
preview.alpha_composite(mist)
preview.thumbnail((1000,1500))
preview.convert('RGB').save(OUT/'processing-preview.jpg',quality=93)
metadata.update({'source_sha256':hashlib.sha256(original_path.read_bytes()).hexdigest(),
  'correction_sha256':hashlib.sha256(correction_path.read_bytes()).hexdigest(),
  'enhanced_size':list(enhanced.size),
  'upscale':'1.5x Lanczos + conservative brightness/color/unsharp; no generative details',
  'period_reconstruction':period_metadata,
  'assets_bytes':{n:(OUT/n).stat().st_size for n in ['gilneas-enhanced.webp','inactive-mask.png','inactive-mist.webp']}})
(OUT/'map-processing.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
print(json.dumps(metadata,ensure_ascii=False,indent=2))
