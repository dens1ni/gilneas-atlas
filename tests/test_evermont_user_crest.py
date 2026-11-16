"""Supplied Evermont needle, snake and apple, red affiliation and full exports."""
import copy
import functools
import json
import threading
import unittest
import zipfile
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/evermont-user-crest/native-evidence')
DRAFT='gilneas-atlas-draft-v1'
SHAPE='M1 1H59V46.4L30 71 1 46.4Z'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class EvermontUserCrest(unittest.TestCase):
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
        self.page=self.context.new_page();self.page.set_default_timeout(15000);self.errors=[];self.watch(self.page,self.errors)
    def tearDown(self):self.context.close()
    def watch(self,page,errors):
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.on('response',lambda r:errors.append(f'{r.status} {r.url}') if r.status>=400 else None)
    def ready(self,page):
        page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=50000)
        page.wait_for_function('document.querySelector("#base-map").complete&&document.querySelector("#base-map").naturalWidth>0',polling=50)
    def boot(self,raw=None):
        if raw is not None:self.page.add_init_script('localStorage.setItem("'+DRAFT+'",'+json.dumps(raw)+');')
        self.page.goto(self.url,wait_until='domcontentloaded');self.ready(self.page)
    def data(self,page=None):return (page or self.page).evaluate('window.gilneasApp.getData()')
    def draft(self,page=None):return (page or self.page).evaluate('localStorage.getItem("'+DRAFT+'")')
    def select(self,page,identifier):
        record=next(l for l in self.source['locations'] if l['id']==identifier)
        page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)');page.locator('#filter-all').click();page.locator('#search').fill(record['name'])
        row=page.locator(f'#location-list button.location-row[data-location-id="{identifier}"]');row.scroll_into_view_if_needed();row.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),identifier)
    def shield(self,page,selector):
        svg=page.locator(selector);self.assertEqual(svg.count(),1)
        self.assertEqual(svg.get_attribute('viewBox'),'0 0 60 72');self.assertEqual(svg.get_attribute('data-faction-id'),'evermont')
        field=svg.locator('.shield-field');self.assertEqual(field.get_attribute('d'),SHAPE)
        self.assertEqual(field.get_attribute('fill'),'#350a13');self.assertEqual(field.get_attribute('stroke'),'#cda24f')
        image=svg.locator('.shield-device');self.assertEqual(image.get_attribute('href'),'assets/ui/factions/evermont-device.svg')
        self.assertEqual([image.get_attribute(key) for key in ['x','y','width','height']],['10','8','40','44'])
    def test_01_gold_needle_snake_apple_shield_in_registry_layers_and_all_evermont_dossiers_keeps_functional_markers(self):
        self.boot();before=self.data();self.assertEqual(before,self.source);self.assertIsNone(self.draft())
        self.assertEqual(next(f for f in before['factions'] if f['id']=='evermont')['color'],'#cc6666')
        self.assertEqual(self.page.locator('#faction-list .faction-row[data-faction-id=evermont]').evaluate('n=>n.style.getPropertyValue("--faction-color")'),'#cc6666')
        for location in before['locations']:
            if location['faction']!='evermont':continue
            marker=self.page.locator(f'#markers .map-marker[data-location-id="{location["id"]}"]')
            self.assertEqual(marker.evaluate('n=>n.style.getPropertyValue("--marker-color")'),'#cc6666')
        self.shield(self.page,'#faction-list .faction-row[data-faction-id="evermont"] > .faction-shield')
        self.shield(self.page,'#location-list details.faction-tree[data-faction-id="evermont"] > summary .faction-shield')
        markers=self.page.locator('#markers .map-marker').evaluate_all('nodes=>nodes.map(n=>({id:n.dataset.locationId,left:n.style.left,top:n.style.top,path:n.querySelector("svg path").getAttribute("d"),color:n.style.getPropertyValue("--marker-color")}))')
        for record in before['locations']:
            if record['faction']!='evermont':continue
            self.select(self.page,record['id']);self.shield(self.page,'#dossier-seal .faction-shield')
            self.assertEqual(self.page.locator('#dossier-faction').text_content(),'Дом Эвермонт')
            self.assertEqual(self.page.locator('#dossier-faction').evaluate('n=>getComputedStyle(n).color'),'rgb(204, 102, 102)')
            self.assertEqual(self.page.locator('#dossier-objects .object-card').count(),len(record['objects']))
            for obj in record['objects']:
                card=self.page.locator(f'#dossier-objects .object-card[data-object-id="{obj["id"]}"]')
                self.assertEqual(card.locator('.object-icon svg').get_attribute('data-type'),obj['type'],'Nested property keeps its functional icon, not Evermont arms')
            self.assertEqual(self.data(),before)
        self.select(self.page,'location-76bf7c1a-fcd2-4dfc-9013-26b909b4732f');self.page.screenshot(path=str(OUT/'evermont-symbol-dossier-desktop.png'))
        self.page.locator('#dossier-seal').screenshot(path=str(OUT/'evermont-symbol-shield-ui.png'))
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.assertEqual(self.page.locator('#markers .map-marker').evaluate_all('nodes=>nodes.map(n=>({id:n.dataset.locationId,left:n.style.left,top:n.style.top,path:n.querySelector("svg path").getAttribute("d"),color:n.style.getPropertyValue("--marker-color")}))'),markers)
        self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
    def test_02_old_author_raw_draft_receives_new_crest_and_clean_exports_preserve_every_byte(self):
        raw=json.dumps(self.author,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw)
        self.select(self.page,'location-76bf7c1a-fcd2-4dfc-9013-26b909b4732f');self.shield(self.page,'#dossier-seal .faction-shield')
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'evermont-user-crest.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),self.source)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'evermont-user-crest.zip';download.value.save_as(str(path))
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist();self.assertIsNone(archive.testzip());self.assertEqual(len(names),len(set(names)));self.assertEqual(set(names),set(self.manifest));self.assertEqual(len(names),len(self.manifest))
            self.assertTrue(all(not n.startswith('/') and '..' not in Path(n).parts for n in names))
            self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),self.source)
            for name in names:
                if name!='assets/data/atlas.json':self.assertEqual(archive.read(name),(ROOT/name).read_bytes(),name)
            for mode in ['root','subpath']:
                host=OUT/('clean-'+mode);host.mkdir();target=host if mode=='root' else host/'gilneas-atlas';target.mkdir(exist_ok=True);archive.extractall(target)
                server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(host)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=context.new_page();errors=[];self.watch(page,errors)
                try:
                    prefix='/' if mode=='root' else '/gilneas-atlas/'
                    page.goto(f'http://127.0.0.1:{server.server_port}'+prefix,wait_until='domcontentloaded');self.ready(page);self.assertEqual(self.data(page),self.source)
                    self.shield(page,'#faction-list .faction-row[data-faction-id="evermont"] > .faction-shield');self.select(page,'location-76bf7c1a-fcd2-4dfc-9013-26b909b4732f');self.shield(page,'#dossier-seal .faction-shield')
                    self.assertFalse(page.locator('#editing-enabled').is_checked());self.assertIsNone(self.draft(page));self.assertEqual(errors,[])
                finally:context.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.select(self.page,'location-76bf7c1a-fcd2-4dfc-9013-26b909b4732f');self.shield(self.page,'#dossier-seal .faction-shield')
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw);self.assertEqual(self.errors,[])
    def test_03_other_heraldry_and_author_custom_field_survive_readonly_mobile_and_reload(self):
        self.boot();before=self.data()
        for faction in before['factions']:
            if faction['id']=='evermont':continue
            field=self.page.locator(f'#faction-list .faction-row[data-faction-id="{faction["id"]}"] .shield-field')
            expected=before['meta']['gilneasHeraldry']['field'] if faction['id']=='gilneas' else faction.get('heraldry',{}).get('field',faction['color'])
            self.assertEqual(field.get_attribute('fill'),expected,faction['id'])
        self.page.set_viewport_size({'width':390,'height':844});self.select(self.page,'location-76bf7c1a-fcd2-4dfc-9013-26b909b4732f');self.shield(self.page,'#dossier-seal .faction-shield')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
        self.page.screenshot(path=str(OUT/'evermont-symbol-dossier-phone.png'))
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
        for value in [None,'#263844']:
            custom=copy.deepcopy(self.source);house=next(f for f in custom['factions'] if f['id']=='evermont')
            if value is None:del house['heraldry']['field']
            else:house['heraldry']['field']=value
            house['heraldry']['authorExtension']={'note':'  Свой герб  ','literal':[False,None,0,'0']}
            raw=json.dumps(custom,ensure_ascii=False,indent=3)+'\n'
            context=self.browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce');page=context.new_page();errors=[];self.watch(page,errors)
            page.add_init_script('localStorage.setItem("'+DRAFT+'",'+json.dumps(raw)+');')
            try:
                page.goto(self.url,wait_until='domcontentloaded');self.ready(page)
                expected=value if value is not None else house['color']
                field=page.locator('#faction-list .faction-row[data-faction-id="evermont"] .shield-field')
                self.assertEqual(field.get_attribute('fill'),expected);self.assertEqual(self.data(page),custom);self.assertEqual(self.draft(page),raw)
                page.reload(wait_until='domcontentloaded');self.ready(page)
                self.assertEqual(self.data(page),custom);self.assertEqual(self.draft(page),raw)
                self.assertEqual(field.get_attribute('fill'),expected);self.assertEqual(errors,[])
            finally:context.close()

if __name__=='__main__':unittest.main()
