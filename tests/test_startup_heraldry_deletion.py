"""Real saved-draft bootstrap never resurrects deliberately deleted heraldry."""
import copy
import functools
import json
import os
from pathlib import Path
import threading
import unittest
import uuid
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('GILNEAS_HERALDRY_EVIDENCE', '/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/release-finish-20261115')) / ('native-heraldry-' + uuid.uuid4().hex)
DRAFT = 'gilneas-atlas-draft-v1'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

class StartupHeraldryDeletion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = json.loads((ROOT / 'assets/data/publication-author-v5.json').read_text())
        cls.previous = json.loads((ROOT / 'assets/data/publication-v5.json').read_text())
        cls.published = json.loads((ROOT / 'assets/data/atlas.json').read_text())
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/'
        cls.p = sync_playwright().start()
        cls.browser = cls.p.chromium.launch()
        OUT.mkdir(parents=True, exist_ok=False)
        print('HERALDRY_EVIDENCE', OUT, flush=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.p.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def ready(self, page):
        page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=50000)

    def test_author_seed_and_immutable_v5_deletion_survive_view_downloads_and_reload(self):
        for label, initial in [('author-seed', self.seed), ('immutable-v5', self.previous), ('seed-only-prior', self.previous)]:
            with self.subTest(label=label):
                draft = copy.deepcopy(initial)
                del draft['meta']['gilneasHeraldry']
                raw = json.dumps(draft, ensure_ascii=False, indent=3) + '\n'
                (OUT / (label + '-raw.json')).write_text(raw)
                context = self.browser.new_context(accept_downloads=True, reduced_motion='reduce')
                errors = []
                try:
                    context.add_init_script('if(localStorage.getItem(' + json.dumps(DRAFT) + ')===null)localStorage.setItem(' + json.dumps(DRAFT) + ',' + json.dumps(raw) + ');')
                    page = context.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    if label == 'seed-only-prior':
                        previous = copy.deepcopy(self.previous)
                        del previous['meta']['gilneasHeraldry']
                        self.assertIn('gilneasHeraldry', self.seed['meta'])
                        page.route('**/assets/data/publication-v5.json', lambda route: route.fulfill(content_type='application/json', body=json.dumps(previous)))
                    page.goto(self.url, wait_until='domcontentloaded')
                    self.ready(page)
                    actual = page.evaluate('window.gilneasApp.getData()')
                    expected = copy.deepcopy(self.published)
                    del expected['meta']['gilneasHeraldry']
                    if label != 'author-seed':
                        prior = copy.deepcopy(self.previous)
                        if label == 'seed-only-prior': del prior['meta']['gilneasHeraldry']
                        expected = page.evaluate('''async ({draft,published,prior,seed})=>{const {reconcileDraftPublication}=await import('./assets/js/draft-publication.mjs');const {prepareTerritoryGrid}=await import('./assets/js/territory-data.mjs');return prepareTerritoryGrid(reconcileDraftPublication(draft,published,prior,seed),gilneasApp.canPlace);}''', {'draft':draft,'published':self.published,'prior':prior,'seed':self.seed})
                        self.assertNotIn('gilneasHeraldry', expected['meta'])
                    self.assertTrue(actual == expected, 'complete in-memory migration, with author deletion; bounded diagnostic')
                    self.assertEqual(page.evaluate('localStorage.getItem(' + json.dumps(DRAFT) + ')'), raw)
                    self.assertFalse(page.locator('#editing-enabled').is_checked())
                    shield = page.evaluate('''async()=>{const {createFactionShield}=await import('./assets/js/heraldry.mjs');const shield=createFactionShield(window.gilneasApp.getData(),'gilneas');document.body.append(shield);return {symbol:shield.querySelector('image')?.getAttribute('href'),field:shield.querySelector('.shield-field').getAttribute('fill')};}''')
                    royal = next(record for record in expected['factions'] if record['id'] == 'gilneas')['heraldry']
                    self.assertEqual(shield['symbol'], royal['symbol'], 'current faction crest is a view-only fallback')
                    self.assertEqual(shield['field'], royal['field'])
                    self.assertEqual(page.evaluate('window.gilneasApp.getData()'), expected)
                    self.assertEqual(page.evaluate('localStorage.getItem(' + json.dumps(DRAFT) + ')'), raw)
                    with page.expect_download(timeout=60000) as download:
                        page.evaluate('window.gilneasApp.exportJson()')
                    snapshot = OUT / (label + '-export.json')
                    download.value.save_as(str(snapshot))
                    self.assertEqual(json.loads(snapshot.read_text()), expected)
                    with page.expect_download(timeout=60000) as download:
                        page.evaluate('window.gilneasApp.exportSite()')
                    archive_path = OUT / (label + '-export.zip')
                    download.value.save_as(str(archive_path))
                    with zipfile.ZipFile(archive_path) as archive:
                        self.assertIsNone(archive.testzip())
                        self.assertEqual(json.loads(archive.read('assets/data/atlas.json')), expected)
                    page.reload(wait_until='domcontentloaded')
                    self.ready(page)
                    self.assertEqual(page.evaluate('window.gilneasApp.getData()'), expected)
                    self.assertEqual(page.evaluate('localStorage.getItem(' + json.dumps(DRAFT) + ')'), raw)
                    self.assertFalse(page.locator('#editing-enabled').is_checked())
                    self.assertEqual(errors, [])
                finally:
                    (OUT / (label + '-pageerrors.json')).write_text(json.dumps(errors))
                    context.close()

    def test_legacy_first_adoption_requires_absence_in_draft_and_previous(self):
        previous = copy.deepcopy(self.previous)
        del previous['meta']['gilneasHeraldry']
        draft = copy.deepcopy(previous)
        draft['meta']['publicationRevision'] = 'royal-council-v5'
        incoming = copy.deepcopy(self.previous)
        incoming['meta']['publicationRevision'] = 'royal-council-v5-first-adoption-test'
        raw = json.dumps(draft, ensure_ascii=False, indent=3) + '\n'
        context = self.browser.new_context(reduced_motion='reduce')
        try:
            context.add_init_script('if(localStorage.getItem(' + json.dumps(DRAFT) + ')===null)localStorage.setItem(' + json.dumps(DRAFT) + ',' + json.dumps(raw) + ');')
            page = context.new_page()
            page.route('**/assets/data/atlas.json', lambda route: route.fulfill(content_type='application/json', body=json.dumps(incoming)))
            page.route('**/assets/data/publication-v5.json', lambda route: route.fulfill(content_type='application/json', body=json.dumps(previous)))
            page.goto(self.url, wait_until='domcontentloaded')
            self.ready(page)
            self.assertEqual(page.evaluate('window.gilneasApp.getData().meta.gilneasHeraldry'), incoming['meta']['gilneasHeraldry'])
            self.assertEqual(page.evaluate('localStorage.getItem(' + json.dumps(DRAFT) + ')'), raw)
        finally:
            context.close()

if __name__ == '__main__':
    unittest.main()
