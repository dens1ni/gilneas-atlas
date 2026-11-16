"""Author v6 acceptance: real markers, canonical links, safe drafts and exports."""
import copy
import functools
import json
import os
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',Path(__file__).resolve().parents[1]))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/native-evidence')
DRAFT='gilneas-atlas-draft-v1'
EVERMONT='location-76bf7c1a-fcd2-4dfc-9013-26b909b4732f'
KENNEL='location-d62d4e06-bb2d-48dc-8f59-fcbe0641f652'
DISTILLERY='location-18f52fa5-7ee8-467f-81a1-d8d8ec11929f'
TEMPLE='location-ff52d2ed-f36b-4aba-8eac-7de87c8c76d7'
LIGHTHOUSES=['galewatch-lighthouse','location-3325cfda-47a7-4e3d-9cac-3797f4dbaa9d','location-e8c8f59c-83ac-49ff-819f-9708a9734ff1']

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class AuthoredEstates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT.parent if PREFIX!='/' else ROOT)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'+PREFIX
        cls.p=sync_playwright().start()
        cls.browser=cls.p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
        OUT.mkdir(parents=True,exist_ok=True)
        cls.source=json.loads((ROOT/'assets/data/atlas.json').read_text())
        cls.author=json.loads((ROOT/'assets/data/publication-author-v5.json').read_text())
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.p.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        self.page=self.context.new_page();self.page.set_default_timeout(15000);self.errors=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('console',lambda message:self.errors.append(message.text) if message.type=='error' else None)
        self.page.on('response',lambda response:self.errors.append(f'{response.status}: {response.url}') if response.status>=400 else None)
    def tearDown(self):self.context.close()
    def boot(self,raw=None):
        if raw is not None:
            self.page.add_init_script('''raw=>{if(localStorage.getItem('gilneas-atlas-draft-v1')===null)localStorage.setItem('gilneas-atlas-draft-v1',raw)}'''.replace('raw=>{','(() => {const raw='+json.dumps(raw)+';',1)+')();')
        self.page.goto(self.url,wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=50000)
        self.page.wait_for_function('document.querySelector("#base-map").complete&&document.querySelector("#base-map").naturalWidth>0',polling=50)
    def data(self):return self.page.evaluate('window.gilneasApp.getData()')
    def draft(self):return self.page.evaluate(f'localStorage.getItem("{DRAFT}")')
    def select(self,identifier):
        record=next(location for location in self.source['locations'] if location['id']==identifier)
        self.page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
        self.page.locator('#filter-all').click();self.page.locator('#search').fill(record['name'])
        row=self.page.locator(f'#location-list button.location-row[data-location-id="{identifier}"]')
        row.scroll_into_view_if_needed();row.click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),identifier)
    def enable(self):
        self.page.locator('#editor-open').click();self.page.locator('label:has(#editing-enabled)').click();self.page.locator('[data-close="editor"]').click()
    def test_01_full_author_snapshot_and_every_marked_icon_and_object_are_in_the_readonly_app(self):
        self.boot();before=self.data()
        self.assertEqual(before['meta']['publicationRevision'],'authored-estates-v6')
        self.assertEqual(before,self.source)
        self.assertEqual(len(before['locations']),86);self.assertEqual(len(before['factions']),16)
        self.assertEqual(before['territoryGrid'],self.source['territoryGrid'])
        self.assertEqual(before['meta']['wallConstruction'],self.source['meta']['wallConstruction'])
        self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertIsNone(self.draft())
        markers=self.page.locator('#markers .map-marker').evaluate_all('''nodes=>nodes.map(node=>({id:node.dataset.locationId,x:node.style.left,y:node.style.top,path:node.querySelector('svg path').getAttribute('d')}))''')
        expected_paths=self.page.evaluate('''async()=>{const types=await import('./assets/js/object-types.mjs');return Object.fromEntries(types.TYPE_DEFINITIONS.map(t=>[t.id,t.path]));}''')
        self.assertEqual(len(markers),86)
        for marker in markers:
            record=next(location for location in before['locations'] if location['id']==marker['id'])
            expected=("M3 7 7 11 12 4 17 11 21 7 19 18H5Z M6 21H18" if record.get('capital') else expected_paths[record['type']])
            self.assertEqual(marker['path'],expected,record['id'])
            self.assertEqual(marker['x'],str(record['x'])+'px');self.assertEqual(marker['y'],str(record['y'])+'px')
            self.assertTrue(marker['path'])
            self.assertGreaterEqual(len(record['objects']),1)
            self.assertTrue(any(obj.get('rules',{}).get('edition')=='dnd5e' for obj in record['objects']))
            self.assertNotRegex(record['description'],r'реконструкц|сценарн|в поздних|выбранн.*эпох|Катаклизм|ворген')
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
    def test_02_native_harbor_estate_annex_links_keep_child_ownership_and_do_not_copy_effects(self):
        self.boot();before=self.data();self.select('duskhaven')
        self.page.locator(f'#dossier-location-links button[data-location-link="{EVERMONT}"]').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),EVERMONT)
        self.assertEqual(self.page.locator('#dossier-faction').text_content(),'Дом Эвермонт')
        self.page.locator(f'#dossier-location-links button[data-location-link="{KENNEL}"]').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),KENNEL)
        self.assertEqual(self.page.locator('#dossier-faction').text_content(),'Дом Эвермонт')
        kennel=next(l for l in before['locations'] if l['id']==KENNEL)
        self.assertEqual(self.page.locator('#dossier-objects .object-card').count(),len(kennel['objects']))
        self.page.locator(f'#dossier-parent-locations button[data-location-link="{EVERMONT}"]').click()
        self.page.locator(f'#dossier-location-links button[data-location-link="{DISTILLERY}"]').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),DISTILLERY)
        self.assertEqual(self.page.locator('#dossier-faction').text_content(),'Дом Эвермонт')
        for modifier in self.page.locator('#dossier-objects .modifier').all_text_contents():self.assertNotIn('спасброскам Воли',modifier)
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
    def test_03_lighthouses_new_factions_and_walden_use_actual_canonical_ids(self):
        self.boot();before=self.data()
        for identifier in LIGHTHOUSES:
            self.select(identifier)
            self.assertEqual(self.page.locator('#dossier-type').text_content(),'Маяк')
            self.assertEqual(self.page.locator(f'.map-marker[data-location-id="{identifier}"] svg').get_attribute('data-type'),'lighthouse')
            self.assertGreater(self.page.locator('#dossier-objects .modifier.bonus').count(),0)
        self.select(TEMPLE);self.assertEqual(self.page.locator('#dossier-faction').text_content(),'Жрецы Моря')
        self.select('taldoren');self.assertEqual(self.page.locator('#dossier-faction').text_content(),'Ведьмы Урожая')
        self.select('tempests-reach');self.assertEqual(self.page.locator('#dossier-faction').text_content(),'Дом Вальден')
        self.assertEqual(self.page.locator('#dossier-location-links button.location-link-row').count(),3)
        self.page.locator('#filter-nobles').click()
        self.page.locator('#search').fill('Вальден')
        self.assertEqual(self.page.locator('#location-list .noble-row').count(),1)
        self.page.locator('#location-list .noble-row[data-noble-id="noble-walden"]').click()
        self.assertEqual(self.page.locator('#noble-name').inner_text(),'Лорд Вальден')
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
    def test_04_author_v5_draft_enriches_without_rewriting_saved_raw_json_coordinates_grid_or_custom_text(self):
        draft=copy.deepcopy(self.author)
        draft['authorExtension']={'literal':[None,False,0,'0','  Не менять  ']}
        draft['territoryGrid']['authorGridNote']='  Ручная сетка  '
        original=next(l for l in draft['locations'] if l['id']==EVERMONT)
        original['description']='  Мой собственный текст Эвермонтов.  '
        raw=json.dumps(draft,ensure_ascii=False,indent=3)+'\n'
        self.boot(raw);actual=self.data()
        self.assertEqual(actual['meta']['publicationRevision'],'authored-estates-v6')
        self.assertEqual(actual['territoryGrid'],draft['territoryGrid'])
        self.assertEqual(actual['authorExtension'],draft['authorExtension'])
        self.assertEqual(actual['meta']['wallConstruction'],self.source['meta']['wallConstruction'],'Untouched Wall adopts only the explicitly requested zero-start correction')
        self.assertEqual(next(l for l in actual['locations'] if l['id']==EVERMONT)['description'],original['description'])
        self.assertEqual(len(actual['locations']),86)
        for location in draft['locations']:
            current=next(l for l in actual['locations'] if l['id']==location['id'])
            if location['id']!='ambermill':self.assertEqual([current['x'],current['y']],[location['x'],location['y']],location['id'])
            for obj in location['objects']:self.assertTrue(any(o['id']==obj['id'] for o in current['objects']))
        self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded');self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=50000)
        self.assertEqual(self.data(),actual);self.assertEqual(self.draft(),raw)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertEqual(self.errors,[])
    def test_05_readonly_json_zip_exports_and_native_creation_preserve_the_full_current_snapshot(self):
        self.boot();before=self.data();self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        path=OUT/'authored-readonly.json';download.value.save_as(str(path));self.assertEqual(json.loads(path.read_text()),before)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'authored-readonly.zip';download.value.save_as(str(path))
        manifest=json.loads((ROOT/'assets/runtime-manifest.json').read_text())
        with zipfile.ZipFile(path) as archive:
            self.assertIsNone(archive.testzip());self.assertEqual(set(archive.namelist()),set(manifest))
            self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),before)
            for resource in ['assets/data/publication-v6.json','assets/data/publication-author-v5.json','assets/js/scenario-publication.mjs','assets/js/object-types.mjs']:
                self.assertEqual(archive.read(resource),(ROOT/resource).read_bytes())
        self.assertIsNone(self.draft());self.assertEqual(self.data(),before)
        self.page.locator('label:has(#editing-enabled)').click();self.page.locator('[data-close="editor"]').click()
        self.select('ambermill-town-hall');self.page.locator('#dossier-add-object').click()
        self.page.locator('#object-type').select_option('lighthouse')
        self.page.locator('#object-name').fill('  Авторский сигнальный фонарь  ')
        self.page.locator('#object-form button[type=submit]').click()
        after=self.data()
        for field in ['factions','nobles','sources','territories','territoryGrid','royalCouncil','meta']:self.assertEqual(after[field],before[field],field)
        self.assertEqual(sum(len(l['objects']) for l in after['locations']),sum(len(l['objects']) for l in before['locations'])+1)
        self.page.reload(wait_until='domcontentloaded');self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=50000)
        self.assertEqual(self.data(),after);self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.assertEqual(self.errors,[])

    def test_06_author_building_uses_its_functional_glyph_not_the_fallback_shield(self):
        # Exact author snapshot is a labelled regression fixture, not production.
        self.page.route('**/assets/data/atlas.json',lambda route:route.fulfill(path=str(ROOT/'assets/data/publication-author-v5.json'),content_type='application/json'))
        self.boot()
        identifier='location-8288bc4e-bb08-45d9-ace3-bc878fe7e8ba'
        expected=self.page.evaluate('''async()=>{const {TYPE_DEFINITIONS}=await import('./assets/js/object-types.mjs');return TYPE_DEFINITIONS.find(t=>t.id==='building').path;}''')
        self.assertEqual(self.page.locator(f'.map-marker[data-location-id="{identifier}"] svg path').get_attribute('d'),expected)
        self.assertIsNone(self.draft());self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
