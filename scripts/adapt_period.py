"""A cartographic pre-wall reconstruction; not recovered canon terrain."""
import json
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def period_mask(original):
    mask=Image.new('L',original.size)
    d=ImageDraw.Draw(mask)
    # Follow the visible wall with a local strip, never a regional rectangle.
    wall=[(1410,2468),(1460,2490),(1540,2513),(1620,2536),(1705,2562),
          (1755,2570),(1800,2581),(1845,2629),(1908,2680),(1975,2699),
          (2048,2703),(2110,2687),(2175,2663),(2205,2635),(2256,2628),
          (2300,2646),(2335,2692),(2408,2774),(2470,2848),(2518,2890)]
    d.line(wall,fill=255,width=82,joint='curve')
    for x,y in wall:d.ellipse((x-41,y-41,x+41,y+41),fill=255)
    d.ellipse((1360,2407,1461,2525),fill=255)
    d.ellipse((2472,2841,2573,2940),fill=255)
    d.polygon([(1676,2508),(1743,2480),(1829,2546),(1813,2629),(1745,2654),(1675,2582)],fill=255)
    # Include the whole arch's artificial pier and shadow footprint.
    d.polygon([(2169,2644),(2196,2593),(2254,2588),(2318,2622),
               (2372,2680),(2343,2734),(2284,2712),(2240,2705),(2196,2694)],fill=255)
    # Dalaran's modern crater is absent from this period.
    d.ellipse((2670,1310,3095,1745),fill=255)
    # Glowing Forsaken elements at the surface city are late-period details.
    d.ellipse((2960,175,3060,330),fill=255)
    metadata={'status':'cartographic reconstruction','wall_path':wall,
      'removed':['visible Greymane wall strip','modern Dalaran crater','visible green Forsaken glow'],
      'not_claimed':'No canon pre-wall terrain scan exists in the supplied files; local terrain is reconstructed.',
      'sources':['https://wowpedia.fandom.com/wiki/Greymane_Wall','https://wowpedia.fandom.com/wiki/Dalaran_Crater']}
    return mask,metadata


def adapted(original):
    mask,metadata=period_mask(original)
    # Work at source-pixel resolution; change only the explicit mask.
    a=np.asarray(original.convert('RGB'))
    m=np.asarray(mask)
    # Telea is deliberately avoided: broad masked regions produced radial smears.
    # Sample displaced neighboring texture on both sides of the former line and
    # blend inside the mask. Outside pixels remain exactly the supplied map.
    h,w=a.shape[:2]
    yy,xx=np.mgrid[:h,:w]
    shift=110
    upper=a[np.clip(yy-shift,0,h-1),xx]
    lower=a[np.clip(yy+shift,0,h-1),xx]
    wall_poly=np.array(metadata['wall_path'],dtype=float)
    center=np.interp(np.arange(w),wall_poly[:,0],wall_poly[:,1])
    t=np.clip((yy-center[None,:]+38)/76,0,1)[...,None]
    local=(upper*(1-t)+lower*t).astype(np.uint8)
    # Dalaran's surrounding grassy plain uses adjacent intact terrain.
    crater=((xx-2890)/228)**2+((yy-1526)/236)**2<1.15
    local[crater]=a[np.clip(yy[crater]+450,0,h-1),np.clip(xx[crater]-420,0,w-1)]
    alpha=np.asarray(mask.filter(ImageFilter.GaussianBlur(7))).astype(float)[...,None]/255
    alpha[np.asarray(mask)==0]=0
    crop=(a*(1-alpha)+local*alpha).astype(np.uint8)
    result=Image.fromarray(crop)
    # On the former crater, use an explicitly cartographic city vignette.
    # It represents a city, not recovered architectural placement.
    layer=Image.new('RGBA',original.size)
    d=ImageDraw.Draw(layer)
    x,y=2890,1526
    d.ellipse((x-132,y-114,x+132,y+114),fill=(89,80,91,175),outline=(181,151,184,220),width=4)
    d.ellipse((x-116,y-100,x+116,y+100),outline=(169,141,173,200),width=2)
    for dx,dy,w,h in [(-77,12,26,82),(-33,-18,31,102),(12,-35,35,136),(64,8,27,91),(96,40,21,55),(-101,43,19,54),(35,54,30,69),(-20,60,27,56)]:
        tx,base=x+dx,y+dy
        d.rectangle((tx-w//2,base-h//2,tx+w//2,base+h//2),fill=(124,117,135,255),outline=(216,198,183,255),width=2)
        d.polygon([(tx-w//2-5,base-h//2),(tx,base-h//2-27),(tx+w//2+5,base-h//2)],fill=(100,67,118,255),outline=(189,147,190,255))
        d.line((tx,base-h//2-27,tx,base-h//2-41),fill=(200,183,143,255),width=2)
        for wy in range(int(base-h//2+12),int(base+h//2-6),16):
            d.rectangle((tx-4,wy,tx+4,wy+8),fill=(218,204,140,230))
    d.arc((x-145,y-132,x+143,y+133),12,160,fill=(184,143,186,170),width=2)
    out=Image.alpha_composite(result.convert('RGBA'),layer).convert('RGB')
    metadata['dalaran_representation']='stylized ground-city cartographic vignette; not a literal recovered city image'
    return out,mask,metadata


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--original',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    im,mask,metadata=adapted(Image.open(args.original).convert('RGB'))
    im.save(args.output/'gilneas-period.png',optimize=True)
    mask.save(args.output/'period-reconstruction-mask.png',optimize=True)
    preview=im.copy();preview.thumbnail((1000,1500));preview.save(args.output/'period-preview.jpg',quality=93)
    (args.output/'period-reconstruction.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    print(json.dumps(metadata,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
