"""Final authored additions and reusable destroyed tags through real bootstrap."""
import copy
import functools
import json
from pathlib import Path
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/release-finish-20261115/native-finish-evidence')
DRAFT='gilneas-atlas-draft-v1'
GRAY='location-df0aa1e2-31ba-43fa-b6b0-84c7733f625a'
MOSSY='location-fb88bb30-c639-4f75-a142-92445555a772'
BURNED='location-gray-ford-north-burned-house'
NEW_IDS=['location-gray-ford-godfrey-estate',BURNED,'location-gray-ford-east-burned-house','location-merchant-cloth-shop','location-merchant-herbal-shop','location-merchant-ironware-shop','location-military-forge','location-military-barracks','location-greymane-record-office','location-greymane-post-office','location-cathedral-rose-park']

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class ReleaseFinishing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads((ROOT/'assets/data/atlas.json').read_text())
        cls.seed=json.loads((ROOT/'assets/data/publication-author-v5.json').read_text())
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
        if raw is not None:self.page.add_init_script('if(localStorage.getItem("'+DRAFT+'")===null)localStorage.setItem("'+DRAFT+'",'+json.dumps(raw)+');')
        self.page.goto(self.url,wait_until='domcontentloaded');self.ready(self.page)
    def data(self,page=None):return (page or self.page).evaluate('window.gilneasApp.getData()')
    def stored(self,page=None):return (page or self.page).evaluate('localStorage.getItem("'+DRAFT+'")')
    def select(self,id,page=None):
        page=page or self.page;loc=next(l for l in self.source['locations'] if l['id']==id)
        page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)');page.locator('#filter-all').click();page.locator('#search').fill(loc['name'])
        row=page.locator(f'#location-list button.location-row[data-location-id="{id}"]');row.scroll_into_view_if_needed();row.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),id)
    def enable(self):
        self.page.locator('#editor-open').click();self.page.locator('label:has(#editing-enabled)').click();self.page.locator('[data-close="editor"]').click()
    def test_01_new_map_pins_have_native_dossiers_type_icons_and_destroyed_labels_without_writes(self):
        self.boot();before=self.data();self.assertEqual(before,self.source);self.assertEqual(len(before['locations']),86)
        self.assertEqual(sum(len(l['objects']) for l in before['locations']),98);self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertIsNone(self.stored())
        for id in NEW_IDS:
            self.select(id);loc=next(l for l in before['locations'] if l['id']==id)
            self.assertEqual(self.page.locator('#dossier-title').text_content(),loc['name'])
            self.assertEqual(self.page.locator('#dossier-description').text_content(),loc['description'])
            expected=self.page.evaluate('''async type=>{const {TYPE_DEFINITIONS}=await import('./assets/js/object-types.mjs');return TYPE_DEFINITIONS.find(t=>t.id===type).path;}''',loc['type'])
            self.assertEqual(self.page.locator(f'#markers .map-marker[data-location-id="{id}"] svg path').get_attribute('d'),expected)
            self.assertEqual(self.page.locator('#dossier-subtitle .object-condition-tag').count(),int(loc.get('destroyed') is True))
            self.assertEqual(self.page.locator('#dossier-objects .object-condition-tag').count(),int(loc.get('destroyed') is True))
            self.assertFalse(self.page.locator('#dossier-edit').is_visible())
        self.select(GRAY)
        self.assertEqual(self.page.locator('#dossier-location-links button.location-link-row').evaluate_all('nodes=>nodes.map(n=>n.dataset.locationLink)'),NEW_IDS[:3])
        self.page.locator(f'#dossier-location-links [data-location-link="{BURNED}"]').click()
        self.assertEqual(self.page.locator('#dossier-subtitle .object-condition-tag').text_content(),'Разрушено')
        self.page.screenshot(path=str(OUT/'gray-ford-destroyed-desktop.png'))
        for id,name,owner in [('emberstone-village','Дом Марли','Лорд Марли'),('emberstone-mine','Дом Марли','Лорд Марли'),(MOSSY,'Дом Харфорд','Лорд Харфорд'),('stormglen','Дом Эшбери','Барон Эшбери'),('ferry-stormglen','Дом Эшбери','Барон Эшбери')]:
            self.select(id);self.assertEqual(self.page.locator('#dossier-faction').text_content(),name);self.assertEqual(self.page.locator('#dossier-owner').text_content(),owner)
            self.assertTrue(all(text==name for text in self.page.locator('#dossier-objects .object-faction-badge').all_text_contents()))
        self.assertEqual(self.data(),before);self.assertIsNone(self.stored());self.assertEqual(self.errors,[])
    def test_02_native_condition_edits_preserve_absence_false_and_complete_unrelated_data(self):
        self.boot();before=self.data();self.enable();self.select(BURNED)
        self.page.locator('#dossier-edit').click();self.assertTrue(self.page.locator('#location-destroyed').is_checked())
        self.page.locator('label:has(#location-destroyed)').click();self.page.locator('#location-form button[type=submit]').click()
        expected=copy.deepcopy(before);next(l for l in expected['locations'] if l['id']==BURNED)['destroyed']=False
        self.assertEqual(self.data(),expected)
        oid=next(l for l in expected['locations'] if l['id']==BURNED)['objects'][0]['id']
        card=self.page.locator(f'#dossier-objects .object-card[data-object-id="{oid}"]');card.locator('summary').click();card.locator('[data-object-edit]').click()
        self.assertTrue(self.page.locator('#object-destroyed').is_checked());self.page.locator('label:has(#object-destroyed)').click();self.page.locator('#object-form button[type=submit]').click()
        next(l for l in expected['locations'] if l['id']==BURNED)['objects'][0]['destroyed']=False;self.assertEqual(self.data(),expected)
        self.select('gilneas-city');self.page.locator('#dossier-edit').click();self.assertFalse(self.page.locator('#location-destroyed').is_checked());self.page.locator('#location-form button[type=submit]').click()
        self.assertEqual(self.data(),expected);self.assertNotIn('destroyed',next(l for l in self.data()['locations'] if l['id']=='gilneas-city'))
        raw=self.stored();self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.assertEqual(self.data(),expected);self.assertEqual(self.stored(),raw)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.enable()
        invalid=copy.deepcopy(expected);invalid['locations'][0]['destroyed']='true'
        error=self.page.evaluate('''async raw=>{try{await window.gilneasApp.importSnapshot(new File([raw],'invalid-condition.json',{type:'application/json'}));return null;}catch(e){return e.message;}}''',json.dumps(invalid))
        self.assertRegex(error,r'destroyed|Разрушено|разруш');self.assertEqual(self.data(),expected);self.assertEqual(self.stored(),raw);self.assertEqual(self.errors,[])
    def test_03_author_seed_json_zip_and_clean_subpath_preserve_all_new_records_and_condition_bytes(self):
        raw=json.dumps(self.seed,ensure_ascii=False,indent=3)+'\n';self.boot(raw);self.assertEqual(self.data(),self.source);self.assertEqual(self.stored(),raw)
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'finished-author-v6.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),self.source)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        zip_path=OUT/'finished-author-v6.zip';download.value.save_as(str(zip_path))
        with zipfile.ZipFile(zip_path) as archive:
            names=archive.namelist();self.assertEqual(len(names),len(self.manifest));self.assertEqual(len(names),len(set(names)));self.assertEqual(set(names),set(self.manifest));self.assertIsNone(archive.testzip())
            self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),self.source)
            self.assertEqual(archive.read('assets/data/atlas.json'),snapshot.read_bytes()+b'\n','ZIP appends exactly one LF to the identical JSON serializer body')
            for name in names:
                if name!='assets/data/atlas.json':self.assertEqual(archive.read(name),(ROOT/name).read_bytes(),name)
            host=OUT/'clean-subpath';target=host/'gilneas-atlas';target.mkdir(parents=True);archive.extractall(target)
            server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(host)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            context=self.browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce');page=context.new_page();errors=[];self.watch(page,errors)
            try:
                page.goto(f'http://127.0.0.1:{server.server_port}/gilneas-atlas/',wait_until='domcontentloaded');self.ready(page);self.assertEqual(self.data(page),self.source);self.assertFalse(page.locator('#editing-enabled').is_checked());self.assertIsNone(self.stored(page))
                self.select(BURNED,page);self.assertEqual(page.locator('#dossier-subtitle .object-condition-tag').text_content(),'Разрушено');page.screenshot(path=str(OUT/'gray-ford-destroyed-mobile.png'))
                self.select('location-military-forge',page);self.assertEqual(page.locator('#dossier-objects .modifier.bonus').text_content(),'+1 к броскам атаки ближним оружием всей фракции.')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),390);self.assertEqual(errors,[])
            finally:context.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.assertEqual(self.data(),self.source);self.assertEqual(self.stored(),raw);self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
