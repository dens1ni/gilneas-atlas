"""Production-only court visuals and actual downloaded device decode."""
import argparse
import base64
import functools
import http.server
import json
import threading
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(); parser.add_argument('--url'); parser.add_argument('--output',required=True); args=parser.parse_args()
OUT=Path(args.output); OUT.mkdir(parents=True,exist_ok=True)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=None
if args.url: url=args.url.rstrip('/')+'/'
else:
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start(); url=f'http://127.0.0.1:{server.server_port}/'
results=[]; errors=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
        context=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=2,reduced_motion='reduce')
        page=context.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None)
        page.on('response',lambda response:errors.append(f'{response.status} {response.url}') if response.status>=400 else None)
        page.goto(url,wait_until='domcontentloaded'); page.wait_for_function('window.gilneasApp?.ready',timeout=60000,polling=50)
        original=page.evaluate('window.gilneasApp.getData()')
        expected=json.loads((ROOT/'assets/data/atlas.json').read_text())
        assert [f['id'] for f in original['factions']]==[f['id'] for f in expected['factions']]
        assert original['factions']==expected['factions']
        for faction in original['factions']:
            row=page.locator('#faction-list .faction-row[data-faction-id="'+faction['id']+'"]')
            shield=row.locator('.faction-shield')
            state=shield.evaluate('e=>({id:e.dataset.factionId,shape:e.querySelector("path").getAttribute("d"),field:e.querySelector("path").getAttribute("fill"),device:e.querySelector("image").getAttribute("href")})')
            assert state['device']==faction['heraldry']['symbol']
            assert state['shape']=='M1 1H59V46.4L30 71 1 46.4Z'
            expected=original['meta']['gilneasHeraldry']['field'] if faction['id']=='gilneas' else faction.get('heraldry',{}).get('field',faction['color'])
            assert state['field']==expected
            decode=page.evaluate('''async source=>{const image=new Image(); image.src=new URL(source,document.baseURI).href;await image.decode();return {width:image.naturalWidth,height:image.naturalHeight};}''',state['device'])
            assert decode['width']>0 and decode['height']>0
            row.screenshot(path=str(OUT/('row-'+faction['id']+'.png')))
            rendered=page.evaluate('''async markup=>{const image=new Image();image.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(markup);await image.decode();const canvas=document.createElement('canvas');canvas.width=120;canvas.height=144;canvas.getContext('2d').drawImage(image,0,0,120,144);return canvas.toDataURL('image/png').split(',')[1];}''',page.evaluate('''async id=>{const original=document.querySelector('#faction-list .faction-row[data-faction-id="'+id+'"] .faction-shield');const copy=original.cloneNode(true);const ref=copy.querySelector('image'),response=await fetch(new URL(ref.getAttribute('href'),document.baseURI));if(!response.ok)throw Error(response.status);const blob=await response.blob();const encoded=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(blob);});ref.setAttribute('href',encoded);copy.setAttribute('xmlns','http://www.w3.org/2000/svg');copy.setAttribute('width','120');copy.setAttribute('height','144');return new XMLSerializer().serializeToString(copy);}''',faction['id']))
            (OUT/('shield-'+faction['id']+'.png')).write_bytes(base64.b64decode(rendered))
            results.append({'id':faction['id'],'state':state,'decoded':decode})
        for width,height in [(1440,1000),(390,844),(844,390)]:
            page.set_viewport_size({'width':width,'height':height})
            page.locator('#council-open').click(); page.screenshot(path=str(OUT/f'council-{width}x{height}.png'))
            assert page.locator('.council-rosters .council-member').count()==sum(member['active'] for member in original['royalCouncil']['members'])
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#council-close').click(); page.locator('#wall-history-open').click()
            page.screenshot(path=str(OUT/f'wall-{width}x{height}.png')); page.locator('[data-close=wall-journal]').click()
        assert page.evaluate('window.gilneasApp.getData()')==original
        assert page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")') is None
        assert not errors,errors
        context.close(); browser.close()
finally:
    if server: server.shutdown(); server.server_close()
contact=Image.new('RGB',(820,((len(results)+4)//5)*210+10),'#171b1e'); draw=ImageDraw.Draw(contact)
for i,result in enumerate(results):
    image=Image.open(OUT/('shield-'+result['id']+'.png')); image.load(); assert image.width==120 and image.height==144
    x=(i%5)*164+22; y=(i//5)*210+10
    contact.paste(image,(x,y),image.getchannel('A')); draw.text((x,y+155),result['id'],fill='#ddd5c2')
contact.save(OUT/'faction-shields.png')
report={'url':url,'factions':results,'count':len(results),'errors':errors,'noWrites':True}
(OUT/'visual-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
