"""Real camera projection: ordinary markers fade at 50–40%, never snapshot data."""
import functools
import json
import math
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/marker-zoom-fade-50-40/native-evidence')
DRAFT='gilneas-atlas-draft-v1'
DETAIL='galewatch-lighthouse'
CONTAINER='northern-headlands'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class MarkerZoomFade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads((ROOT/'assets/data/atlas.json').read_text())
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}/'
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
        OUT.mkdir(parents=True,exist_ok=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.playwright.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True)
        self.page=self.context.new_page();self.page.set_default_timeout(15000);self.errors=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.on('console',lambda m:self.errors.append(m.text) if m.type=='error' else None)
        self.page.on('response',lambda r:self.errors.append(f'{r.status} {r.url}') if r.status>=400 else None)
    def tearDown(self):self.context.close()
    def boot(self,raw=None):
        if raw is not None:self.page.add_init_script('localStorage.setItem("'+DRAFT+'",'+json.dumps(raw)+');')
        self.page.goto(self.url,wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=50000)
        self.page.wait_for_function('document.querySelector("#base-map").complete&&document.querySelector("#base-map").naturalWidth>0',polling=50)
    def data(self):return self.page.evaluate('window.gilneasApp.getData()')
    def draft(self):return self.page.evaluate('localStorage.getItem("'+DRAFT+'")')
    def scale(self,value):
        self.page.evaluate('scale=>{const ui=window.gilneasApp.ui;ui.zoom(scale/ui.getCamera().scale);}',value)
        self.assertAlmostEqual(self.page.evaluate('window.gilneasApp.ui.getCamera().scale'),value,places=10)
    def projections(self):
        return self.page.locator('#markers .map-marker').evaluate_all('''nodes=>nodes.map(node=>{const s=getComputedStyle(node);return {id:node.dataset.locationId,opacity:Number(s.opacity),visibility:s.visibility,pointer:s.pointerEvents,x:node.style.left,y:node.style.top,path:node.querySelector('svg path').getAttribute('d'),labelVisibility:getComputedStyle(node.querySelector('.marker-label')).visibility};})''')
    def test_01_all_nonlocations_fade_linearly_from_fifty_to_forty_and_all_containers_remain_visible(self):
        self.boot();before=self.data();self.assertEqual(before,self.source);self.assertIsNone(self.draft())
        self.page.evaluate('window.gilneasApp.selectId("'+DETAIL+'");window.gilneasApp.ui.setPanel("navigation",false);window.gilneasApp.ui.setPanel("layers",false);window.gilneasApp.ui.setPanel("dossier",false);window.gilneasApp.ui.focusLocation("'+DETAIL+'",false)')
        self.scale(.6);original=self.projections();original_by_id={row['id']:row for row in original};records={row['id']:row for row in before['locations']}
        self.assertEqual(set(original_by_id),set(records));results=[]
        for scale,opacity in [(.6,1),(.5,1),(.49,.9),(.475,.75),(.45,.5),(.425,.25),(.41,.1),(.4001,.001),(.4,0),(.39,0),(.25,0),(.45,.5),(.5,1)]:
            self.scale(scale);rows=self.projections();self.assertEqual(len(rows),len(records))
            for row in rows:
                is_location=records[row['id']].get('isLocation') is True
                expected=1 if is_location else opacity
                self.assertAlmostEqual(row['opacity'],expected,places=6,msg=f"{row['id']} at {scale*100}% must have opacity {expected}")
                self.assertEqual([row['x'],row['y'],row['path']],[original_by_id[row['id']]['x'],original_by_id[row['id']]['y'],original_by_id[row['id']]['path']],'Fade must not replace type glyphs or map anchors')
                if not is_location and opacity==0:
                    self.assertEqual(row['visibility'],'hidden');self.assertEqual(row['labelVisibility'],'hidden');self.assertEqual(row['pointer'],'none')
                else:self.assertEqual(row['visibility'],'visible')
            results.append({'scale':scale,'expectedNonlocationOpacity':opacity,'markers':rows})
            self.assertEqual(self.data(),before);self.assertIsNone(self.draft())
        self.assertEqual(self.errors,[])
        (OUT/'all-marker-scales.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')

    def test_02_hidden_markers_and_labels_cannot_intercept_map_clicks_focus_or_tooltips(self):
        raw=json.dumps(self.source,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        before=self.data();self.assertEqual(self.draft(),raw)
        self.page.evaluate('window.gilneasApp.selectId("'+CONTAINER+'");window.gilneasApp.ui.setPanel("navigation",false);window.gilneasApp.ui.setPanel("layers",false);window.gilneasApp.ui.setPanel("dossier",false);window.gilneasApp.ui.focusLocation("'+DETAIL+'",false)')
        self.scale(.5)
        marker=self.page.locator(f'#markers .map-marker[data-location-id="{DETAIL}"]')
        marker.hover();self.assertTrue(self.page.locator('#marker-tooltip').is_visible())
        self.scale(.4);self.assertTrue(self.page.locator('#marker-tooltip').is_hidden())
        self.assertTrue(marker.is_disabled())
        point=marker.evaluate('node=>{const r=node.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}')
        self.assertEqual(self.page.evaluate('point=>document.elementFromPoint(...point)?.closest(".map-marker")?.dataset.locationId||null',point),None)
        self.page.mouse.click(*point)
        self.assertIsNone(self.page.evaluate('window.gilneasApp.getSelectedId()'),'Click through a vanished marker must act on the blank map')
        for method in ['click','focus']:
            marker.evaluate('''(node,method)=>{node[method]();}''',method)
            self.assertIsNone(self.page.evaluate('window.gilneasApp.getSelectedId()'))
            self.assertNotEqual(self.page.evaluate('document.activeElement?.dataset.locationId'),DETAIL)
        self.assertTrue(self.page.locator('#marker-tooltip').is_hidden())
        self.page.evaluate('window.gilneasApp.selectId("'+CONTAINER+'");window.gilneasApp.ui.setPanel("dossier",false);window.gilneasApp.ui.focusLocation("'+CONTAINER+'",false)')
        self.scale(.39)
        container=self.page.locator(f'#markers .map-marker[data-location-id="{CONTAINER}"]')
        self.assertFalse(container.is_disabled());self.assertTrue(container.is_visible())
        container.click();self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),CONTAINER)
        self.assertEqual(self.data(),before);self.assertEqual(self.draft(),raw);self.assertEqual(self.errors,[])

    def test_03_faction_dimming_and_redraws_preserve_the_camera_fade_and_registry_can_reveal_a_hidden_marker(self):
        self.boot();before=self.data()
        self.page.evaluate('window.gilneasApp.ui.setPanel("layers",true)')
        self.page.locator('#faction-list button.faction-row[data-faction-id="raft"]').click()
        self.scale(.45)
        dimmed=self.page.locator(f'#markers .map-marker[data-location-id="{DETAIL}"]')
        self.assertIn('dimmed',dimmed.get_attribute('class'))
        self.assertAlmostEqual(dimmed.evaluate('node=>Number(getComputedStyle(node).opacity)'),.075,places=6)
        ordinary=self.page.locator('#markers .map-marker[data-location-id="location-raft-estate"]')
        self.assertAlmostEqual(ordinary.evaluate('node=>Number(getComputedStyle(node).opacity)'),.5,places=6)
        self.scale(.39)
        self.page.locator('label:has(#show-labels)').click()
        for row in self.projections():
            record=next(l for l in before['locations'] if l['id']==row['id'])
            if record.get('isLocation') is not True:
                self.assertEqual(row['visibility'],'hidden');self.assertEqual(row['labelVisibility'],'hidden')
        self.page.locator('#faction-clear').click()
        self.assertAlmostEqual(dimmed.evaluate('node=>Number(getComputedStyle(node).opacity)'),0,places=6)
        self.page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
        self.page.locator('#search').fill('Штормовой маяк')
        self.page.locator(f'#location-list button.location-row[data-location-id="{DETAIL}"]').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),DETAIL)
        self.assertGreaterEqual(self.page.evaluate('window.gilneasApp.ui.getCamera().scale'),.65)
        self.assertTrue(dimmed.is_visible());self.assertFalse(dimmed.is_disabled())
        self.assertAlmostEqual(dimmed.evaluate('node=>Number(getComputedStyle(node).opacity)'),1,places=6)
        self.assertEqual(self.page.locator('#dossier-title').text_content(),'Штормовой маяк')
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])

    def test_04_native_wheel_and_phone_pinch_drive_the_same_fade_without_changing_map_data(self):
        self.boot();before=self.data()
        self.page.evaluate('window.gilneasApp.ui.setPanel("navigation",false);window.gilneasApp.ui.setPanel("layers",false);window.gilneasApp.ui.focusLocation("'+DETAIL+'",false)')
        self.scale(.5)
        box=self.page.locator('#viewport').bounding_box()
        self.page.mouse.move(box['x']+box['width']*.6,box['y']+box['height']*.55)
        self.page.mouse.wheel(0,-math.log(.45/.5)/.002)
        self.page.wait_for_function('Math.abs(window.gilneasApp.ui.getCamera().scale-.45)<1e-8',polling=50)
        marker=self.page.locator(f'#markers .map-marker[data-location-id="{DETAIL}"]')
        self.assertAlmostEqual(marker.evaluate('node=>Number(getComputedStyle(node).opacity)'),.5,places=6)
        self.page.mouse.wheel(0,-math.log(.39/.45)/.002)
        self.page.wait_for_function('Math.abs(window.gilneasApp.ui.getCamera().scale-.39)<1e-8',polling=50)
        self.assertTrue(marker.is_hidden());self.assertTrue(marker.is_disabled())
        self.page.set_viewport_size({'width':390,'height':844})
        self.page.wait_for_function('Math.abs(parseFloat(document.documentElement.style.getPropertyValue("--app-height"))-844)<1',polling=50)
        self.page.evaluate('window.gilneasApp.ui.setPanel("navigation",false);window.gilneasApp.ui.setPanel("layers",false);window.gilneasApp.ui.setPanel("dossier",false)')
        self.scale(.6)
        session=self.context.new_cdp_session(self.page)
        session.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':5})
        rect=self.page.locator('#viewport').bounding_box();x=rect['x']+rect['width']/2;y=rect['y']+rect['height']*.32
        def touch(kind,distance=None):
            points=[] if distance is None else [{'x':x-distance/2,'y':y,'id':1,'radiusX':3,'radiusY':3,'force':1},{'x':x+distance/2,'y':y,'id':2,'radiusX':3,'radiusY':3,'force':1}]
            session.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':points})
        touch('touchStart',160)
        touch('touchMove',120)
        self.page.wait_for_function('Math.abs(window.gilneasApp.ui.getCamera().scale-.45)<1e-8',polling=50)
        self.assertAlmostEqual(marker.evaluate('node=>Number(getComputedStyle(node).opacity)'),.5,places=6)
        touch('touchMove',100)  # Integer finger coordinates keep the native scale exact.
        self.page.wait_for_function('Math.abs(window.gilneasApp.ui.getCamera().scale-.375)<1e-8',polling=50)
        self.assertTrue(marker.is_hidden());self.assertTrue(marker.is_disabled())
        touch('touchMove',160)
        self.page.wait_for_function('Math.abs(window.gilneasApp.ui.getCamera().scale-.6)<1e-8',polling=50)
        touch('touchEnd');session.detach()
        self.assertTrue(marker.is_visible());self.assertFalse(marker.is_disabled())
        self.assertAlmostEqual(marker.evaluate('node=>Number(getComputedStyle(node).opacity)'),1,places=6)
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])

    def test_05_current_json_and_zip_preserve_data_and_the_clean_export_keeps_fade_at_both_publish_paths(self):
        self.boot();before=self.data()
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'marker-fade.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),before)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'marker-fade.zip';download.value.save_as(str(path))
        manifest=json.loads((ROOT/'assets/runtime-manifest.json').read_text())
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist();self.assertIsNone(archive.testzip())
            self.assertEqual(len(names),len(set(names)));self.assertEqual(set(names),set(manifest))
            self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),before)
            for name in names:
                if name!='assets/data/atlas.json':self.assertEqual(archive.read(name),(ROOT/name).read_bytes(),name)
            for mode in ['root','subpath']:
                host=OUT/('clean-'+mode);host.mkdir()
                target=host if mode=='root' else host/'gilneas-atlas';target.mkdir(exist_ok=True);archive.extractall(target)
                server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(host)))
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                page=context.new_page();errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('response',lambda r:errors.append(f'{r.status} {r.url}') if r.status>=400 else None)
                try:
                    prefix='/' if mode=='root' else '/gilneas-atlas/'
                    page.goto(f'http://127.0.0.1:{server.server_port}'+prefix,wait_until='domcontentloaded')
                    page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=50000)
                    self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before)
                    self.assertFalse(page.locator('#editing-enabled').is_checked())
                    for scale,opacity in [(.5,1),(.45,.5),(.4,0),(.3,0),(.5,1)]:
                        page.evaluate('scale=>{const ui=window.gilneasApp.ui;ui.zoom(scale/ui.getCamera().scale);}',scale)
                        detail=page.locator(f'#markers .map-marker[data-location-id="{DETAIL}"]')
                        container=page.locator(f'#markers .map-marker[data-location-id="{CONTAINER}"]')
                        self.assertAlmostEqual(detail.evaluate('node=>Number(getComputedStyle(node).opacity)'),opacity,places=6)
                        self.assertEqual(detail.is_disabled(),opacity==0)
                        self.assertAlmostEqual(container.evaluate('node=>Number(getComputedStyle(node).opacity)'),1,places=6)
                        self.assertTrue(container.is_visible());self.assertFalse(container.is_disabled())
                    self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before)
                    self.assertIsNone(page.evaluate('localStorage.getItem("'+DRAFT+'")'));self.assertEqual(errors,[])
                finally:context.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
