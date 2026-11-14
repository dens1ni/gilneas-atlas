"""Extract the user's precise silver device; keep the established shield."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, label

ROOT=Path(__file__).resolve().parents[1]
BBOX=(148,240,305,420)
SHAPE='M1 1H59V46.4L30 71 1 46.4Z'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True,type=Path)
    args=parser.parse_args()
    with Image.open(args.source) as source:
        rgb=np.array(source.convert('RGB').crop(BBOX))
    gray=rgb.mean(axis=2)
    components,_=label(gray>85)
    sizes=np.bincount(components.ravel())
    selected=[int(i) for i in range(1,len(sizes)) if sizes[i]>=50]
    mask=binary_dilation(np.isin(components,selected),iterations=1)
    # Preserve the real dark openings and detached strokes; never fill the
    # rune's interior or take the banner cloth, poles, brackets or rim.
    alpha=np.rint(np.clip((gray-50)/35,0,1)*255).astype('uint8')
    alpha[~mask]=0
    image=np.dstack([rgb,alpha])
    symbol=ROOT/'assets/ui/gilneas-royal-symbol.png'
    Image.fromarray(image).save(symbol)
    encoded=base64.b64encode(symbol.read_bytes()).decode('ascii')
    field,edge,device='#131516','#65707b','#9aa8b6'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 72" width="60" height="72">
  <title>Королевство Гилнеас</title>
  <path d="{SHAPE}" fill="{field}" stroke="{edge}" stroke-width="1.2"/>
  <image x="9" y="8" width="42" height="49" href="data:image/png;base64,{encoded}"/>
</svg>
'''
    (ROOT/'assets/ui/gilneas-royal-shield.svg').write_text(svg)
    metadata={
        'sourceSha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'source':'user-supplied Gilneas royal banner',
        'sourceCrop':list(BBOX),'shape':SHAPE,
        'field':field,'edge':edge,'device':device,
        'samples':{'field':{'box':[138,300,152,355],'medianRgb':[19,21,22]},
                   'edge':{'box':[116,300,132,350],'approximateRgb':[101,112,123]}},
        'selectedComponents':[{'index':i,'pixels':int(sizes[i])} for i in selected],
        'symbol':'assets/ui/gilneas-royal-symbol.png',
        'shield':'assets/ui/gilneas-royal-shield.svg',
        'treatment':'Keep supplied silver RGB, derive alpha from local luminance only, retain open spaces and all three components. Existing shield shape unchanged; graphite field and silver edge replace the old blue and gold.',
    }
    (ROOT/'docs/royal-crest-treatment.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(metadata,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
