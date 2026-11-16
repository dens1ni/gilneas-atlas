"""Real ferry markers, inert routes, author drafts and clean exports."""
import functools
import json
import threading
import unittest
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/ferry-network/native-evidence')
IDS=['ferry-duskhaven','ferry-keel-harbor','ferry-stormglen']
DRAFT='gilneas-atlas-draft-v1'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class FerryNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads((ROOT/'assets/data/atlas.json').read_text())
        cls.author=json.loads((ROOT/'assets/data/publication-author-v5.json').read_text())
        cls.manifest=json.loads((ROOT/'assets/runtime-manifest.json').read_text())
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}/'
        cls.p=sync_playwright().start()
        cls.browser=cls.p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
        OUT.mkdir(parents=True,exist_ok=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.p.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True)
        self.page=self.context.new_page();self.page.set_default_timeout(15000);self.errors=[]
        self.watch(self.page,self.errors)
    def tearDown(self):self.context.close()
    def watch(self,page,errors):
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.on('response',lambda r:errors.append(f'{r.status}: {r.url}') if r.status>=400 else None)
    def ready(self,page):
        page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=50000)
        page.wait_for_function('document.querySelector("#base-map").complete&&document.querySelector("#base-map").naturalWidth>0',polling=50)
    def boot(self,raw=None):
        if raw is not None:self.page.add_init_script('localStorage.setItem("'+DRAFT+'",'+json.dumps(raw)+');')
        self.page.goto(self.url,wait_until='domcontentloaded');self.ready(self.page)
    def data(self,page=None):return (page or self.page).evaluate('window.gilneasApp.getData()')
    def draft(self,page=None):return (page or self.page).evaluate('localStorage.getItem("'+DRAFT+'")')
    def select(self,page,identifier):
        location=next(record for record in self.source['locations'] if record['id']==identifier)
        page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
        page.locator('#filter-all').click();page.locator('#search').fill(location['name'])
        row=page.locator(f'#location-list button.location-row[data-location-id="{identifier}"]');row.scroll_into_view_if_needed();row.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),identifier)
        self.assertEqual(page.locator('#dossier-title').text_content(),location['name'])
    def assert_routes(self,page):
        network=self.source['meta']['ferryNetwork'];layer=page.locator('#ferry-routes')
        self.assertEqual(layer.count(),1,'One detached ferry SVG must be rendered')
        self.assertEqual(layer.get_attribute('aria-hidden'),'true')
        self.assertEqual(layer.get_attribute('focusable'),'false')
        self.assertEqual(layer.get_attribute('viewBox'),f"0 0 {self.source['meta']['width']} {self.source['meta']['height']}")
        self.assertEqual(layer.evaluate('node=>getComputedStyle(node).pointerEvents'),'none')
        main=layer.locator('.ferry-route-line');halo=layer.locator('.ferry-route-halo')
        self.assertEqual(main.count(),2);self.assertEqual(halo.count(),2)
        for route in network['routes']:
            line=layer.locator(f'.ferry-route-line[data-ferry-route="{route["id"]}"]')
            self.assertEqual(line.get_attribute('points'),' '.join(','.join(str(v) for v in point) for point in route['points']))
            self.assertEqual(line.evaluate('node=>getComputedStyle(node).vectorEffect'),'non-scaling-stroke')
            self.assertNotEqual(line.evaluate('node=>getComputedStyle(node).strokeDasharray'),'none')
            self.assertEqual(line.evaluate('node=>getComputedStyle(node).pointerEvents'),'none')
        self.assertEqual(self.data(page),self.source)
    def test_01_native_dashed_overlay_is_inert_and_connects_the_three_real_docks(self):
        self.boot()
        self.assertEqual(self.page.locator('#ferry-routes').count(),1,'Render the requested dashed ferry overlay in the real app')
        self.assert_routes(self.page)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertIsNone(self.draft())
        for identifier in IDS:
            self.select(self.page,identifier)
            record=next(location for location in self.source['locations'] if location['id']==identifier)
            marker=self.page.locator(f'#markers .map-marker[data-location-id="{identifier}"]')
            self.assertEqual(marker.locator('svg').get_attribute('data-type'),'ferry')
            self.assertEqual(marker.evaluate('node=>node.classList.contains("ferry-marker")'),True)
            self.assertEqual(marker.evaluate('node=>getComputedStyle(node,"::before").borderRadius'),'50%')
            self.assertEqual(self.page.locator('#dossier-type').text_content(),'Паромная пристань')
            self.assertEqual(self.page.locator('#dossier-objects .object-card').count(),1)
            self.assertEqual(self.page.locator('#dossier-objects .object-icon svg').get_attribute('data-type'),'ferry')
            self.assertEqual(self.data(),self.source);self.assertIsNone(self.draft())
        self.assertEqual(self.errors,[])
    def test_02_phone_wheel_pan_fade_and_canonical_parent_navigation_never_write_data(self):
        self.context.close();self.context=self.browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,reduced_motion='reduce')
        self.page=self.context.new_page();self.errors=[];self.watch(self.page,self.errors);self.boot()
        before=self.data();self.assert_routes(self.page)
        for dock_id,parent_id in [('ferry-duskhaven','duskhaven'),('ferry-keel-harbor','keel-harbor'),('ferry-stormglen','stormglen')]:
            self.select(self.page,parent_id)
            self.page.locator(f'#dossier-location-links button[data-location-link="{dock_id}"]').click()
            self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),dock_id)
            self.page.locator(f'#dossier-parent-locations button[data-location-link="{parent_id}"]').click()
            self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),parent_id)
        self.page.evaluate('''()=>{const ui=window.gilneasApp.ui;for(const name of ['dossier','navigation','layers'])ui.setPanel(name,false);ui.focusLocation('ferry-keel-harbor',false);ui.zoom(.6/ui.getCamera().scale);}''')
        self.page.mouse.move(150,240);self.page.mouse.wheel(0,180)
        self.page.wait_for_function('window.gilneasApp.ui.getCamera().scale<.6',polling=50)
        self.page.evaluate('window.gilneasApp.ui.zoom(.45/window.gilneasApp.ui.getCamera().scale)')
        self.page.wait_for_function('Math.abs(window.gilneasApp.ui.getCamera().scale-.45)<1e-9',polling=50)
        for identifier in IDS:
            marker=self.page.locator(f'#markers .map-marker[data-location-id="{identifier}"]')
            self.assertAlmostEqual(float(marker.evaluate('node=>getComputedStyle(node).opacity')),.5,places=6)
        self.page.evaluate('window.gilneasApp.ui.zoom(.4/window.gilneasApp.ui.getCamera().scale)')
        self.page.wait_for_function('Math.abs(window.gilneasApp.ui.getCamera().scale-.4)<1e-9',polling=50)
        for identifier in IDS:
            marker=self.page.locator(f'#markers .map-marker[data-location-id="{identifier}"]')
            self.assertEqual(marker.evaluate('node=>getComputedStyle(node).visibility'),'hidden');self.assertTrue(marker.is_disabled())
        self.assert_routes(self.page)
        self.page.mouse.move(140,240);camera=self.page.evaluate('window.gilneasApp.ui.getCamera()');self.page.mouse.down();self.page.mouse.move(180,270,steps=4);self.page.mouse.up()
        self.assertNotEqual(self.page.evaluate('window.gilneasApp.ui.getCamera()'),camera)
        self.select(self.page,'ferry-stormglen')
        self.assertGreater(self.page.evaluate('window.gilneasApp.ui.getCamera().scale'),.4)
        self.page.screenshot(path=str(OUT/'ferry-stormglen-phone.png'))
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
    def test_03_author_draft_reload_json_zip_and_clean_root_subpath_keep_routes_exact(self):
        import zipfile
        raw=json.dumps(self.author,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw);self.assert_routes(self.page)
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'ferry-network.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),self.source)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'ferry-network.zip';download.value.save_as(str(path))
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist();self.assertIsNone(archive.testzip());self.assertEqual(len(names),len(set(names)));self.assertEqual(set(names),set(self.manifest))
            self.assertTrue(all(not n.startswith('/') and '..' not in Path(n).parts for n in names))
            self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),self.source)
            for name in names:
                if name!='assets/data/atlas.json':self.assertEqual(archive.read(name),(ROOT/name).read_bytes(),name)
            for mode in ['root','subpath']:
                host=OUT/('clean-'+mode);host.mkdir();target=host if mode=='root' else host/'gilneas-atlas';target.mkdir(exist_ok=True);archive.extractall(target)
                server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(host)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True);page=context.new_page();errors=[];self.watch(page,errors)
                try:
                    prefix='/' if mode=='root' else '/gilneas-atlas/'
                    page.goto(f'http://127.0.0.1:{server.server_port}'+prefix,wait_until='domcontentloaded');self.ready(page);self.assert_routes(page)
                    self.assertFalse(page.locator('#editing-enabled').is_checked());self.assertIsNone(self.draft(page))
                    for identifier in IDS:self.select(page,identifier)
                    page.locator('#editor-open').click()
                    with page.expect_download(timeout=60000) as download:page.locator('#export-json').click()
                    reexport=OUT/f'ferry-{mode}-reexport.json';download.value.save_as(str(reexport));self.assertEqual(json.loads(reexport.read_text()),self.source)
                    self.assertEqual(errors,[])
                finally:context.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.assert_routes(self.page)
        self.assertEqual(self.draft(),raw);self.assertEqual(self.errors,[])
    def test_04_rejected_imports_preserve_live_snapshot_and_saved_raw_draft(self):
        import copy
        self.boot();self.page.locator('#editor-open').click();self.page.locator('label:has(#editing-enabled)').click();self.page.locator('[data-close="editor"]').click()
        before=self.data();stored=self.draft()
        for kind in ['malformed','missing','collision']:
            invalid=copy.deepcopy(before)
            if kind=='malformed':invalid['meta']['ferryNetwork']['routes'][0]['points'][1][0]='not-a-number'
            if kind=='missing':invalid['meta']['ferryNetwork']['routes'][0]['toLocationId']='absent-ferry'
            if kind=='collision':invalid['meta']['ferryNetwork']['routes'][0]['id']=invalid['locations'][0]['objects'][0]['id']
            error=self.page.evaluate('''async raw=>{try{await window.gilneasApp.importSnapshot(new File([raw],'invalid-ferry.json',{type:'application/json'}));return null;}catch(error){return error.message;}}''',json.dumps(invalid,ensure_ascii=False))
            self.assertIsInstance(error,str);self.assertRegex(error,r'паром|маршрут|координат|переправ|Повтор ID')
            self.assertEqual(self.data(),before);self.assertEqual(self.draft(),stored);self.assert_routes(self.page)
        self.assertEqual(self.errors,[])
    def test_05_moved_deleted_empty_and_other_map_routes_do_not_reappear_after_native_save_reload(self):
        import copy
        self.boot();self.page.locator('#editor-open').click();self.page.locator('label:has(#editing-enabled)').click();self.page.locator('[data-close="editor"]').click()
        original=self.data()
        moved=copy.deepcopy(original);next(l for l in moved['locations'] if l['id']=='ferry-keel-harbor')['x']+=2
        self.page.evaluate('snapshot=>window.gilneasApp.replaceData(snapshot)',moved)
        self.assertEqual(self.data(),moved);self.assertEqual(json.loads(self.draft()),moved)
        self.assertEqual(self.page.locator('#ferry-routes .ferry-route-line').count(),1)
        self.assertEqual(self.page.locator('#ferry-routes .ferry-route-line').get_attribute('data-ferry-route'),'ferry-route-duskhaven-stormglen')
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page)
        self.assertEqual(self.data(),moved);self.assertEqual(self.page.locator('#ferry-routes .ferry-route-line').count(),1)
        self.page.locator('#editor-open').click();self.page.locator('label:has(#editing-enabled)').click();self.page.locator('[data-close="editor"]').click()
        empty=copy.deepcopy(original);empty['meta']['ferryNetwork']['routes']=[]
        self.page.evaluate('snapshot=>window.gilneasApp.replaceData(snapshot)',empty)
        self.assertEqual(self.page.locator('#ferry-routes .ferry-route-line').count(),0);self.assertEqual(self.data(),empty)
        absent=copy.deepcopy(original);del absent['meta']['ferryNetwork']
        self.page.evaluate('snapshot=>window.gilneasApp.replaceData(snapshot)',absent)
        self.assertEqual(self.page.locator('#ferry-routes .ferry-route-line').count(),0);self.assertEqual(self.data(),absent)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page)
        self.assertEqual(self.data(),absent);self.assertEqual(json.loads(self.draft()),absent)
        self.page.locator('#editor-open').click();self.page.locator('label:has(#editing-enabled)').click();self.page.locator('[data-close="editor"]').click()
        other=copy.deepcopy(original);other['meta']['ferryNetwork']['mapRevision']='author-another-revision'
        self.page.evaluate('snapshot=>window.gilneasApp.replaceData(snapshot)',other)
        self.assertEqual(self.page.locator('#ferry-routes .ferry-route-line').count(),0);self.assertEqual(self.data(),other)
        self.page.evaluate('snapshot=>window.gilneasApp.replaceData(snapshot)',original);self.assert_routes(self.page)
        self.assertEqual(self.errors,[])
    def test_06_screen_path_registration_and_mouse_clicks_do_not_hit_the_inert_overlay(self):
        self.boot();self.page.evaluate('''()=>{for(const name of ['dossier','navigation','layers'])window.gilneasApp.ui.setPanel(name,false);window.gilneasApp.ui.focusLocation('ferry-stormglen',false);}''')
        route=self.source['meta']['ferryNetwork']['routes'][1]
        for target_scale in [.65,1.1]:
            self.page.evaluate('scale=>window.gilneasApp.ui.zoom(scale/window.gilneasApp.ui.getCamera().scale)',target_scale)
            line=self.page.locator(f'#ferry-routes .ferry-route-line[data-ferry-route="{route["id"]}"]')
            measured=line.evaluate('''(node,point)=>{const matrix=node.getScreenCTM(),p=new DOMPoint(...point).matrixTransform(matrix),camera=window.gilneasApp.ui.getCamera(),box=document.querySelector('#viewport').getBoundingClientRect();return {projected:[p.x,p.y],expected:[box.left+camera.x+point[0]*camera.scale,box.top+camera.y+point[1]*camera.scale],stroke:getComputedStyle(node).strokeWidth,events:getComputedStyle(node).pointerEvents};}''',route['points'][-2])
            self.assertAlmostEqual(measured['projected'][0],measured['expected'][0],places=3);self.assertAlmostEqual(measured['projected'][1],measured['expected'][1],places=3)
            self.assertEqual(measured['stroke'],'1.8px');self.assertEqual(measured['events'],'none')
        self.page.evaluate('window.gilneasApp.clearSelection()');self.select(self.page,'ferry-stormglen')
        self.page.locator('#dossier-close').click();self.page.evaluate('window.gilneasApp.ui.setPanel("navigation",false)')
        marker=self.page.locator('#markers .map-marker[data-location-id="ferry-stormglen"]')
        marker.click();self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'ferry-stormglen')
        self.page.locator('#dossier-close').click();self.assert_routes(self.page)
        self.page.screenshot(path=str(OUT/'ferry-stormglen-desktop.png'))
        self.assertEqual(self.data(),self.source);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
