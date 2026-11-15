"""Real-bootstrap raster-mask lifecycle regressions; no production fixtures changed."""
import functools
import http.server
import json
import os
import threading
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(os.environ.get('GILNEAS_TEST_ROOT', str(Path(__file__).resolve().parents[1])))
PREFIX = os.environ.get('GILNEAS_TEST_PREFIX', '/')
REMOTE_URL = os.environ.get('GILNEAS_TEST_URL')
DRAFT_KEY = 'gilneas-atlas-draft-v1'


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class MaskRevision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = None
        if REMOTE_URL:
            cls.url = REMOTE_URL
        else:
            cls.server = http.server.ThreadingHTTPServer(
                ('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT))
            )
            threading.Thread(target=cls.server.serve_forever, daemon=True).start()
            cls.url = f'http://127.0.0.1:{cls.server.server_port}' + PREFIX
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=[
            '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
        ])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()

    def setUp(self):
        self.contexts = []
        self.errors = []
        self.failed_mask_requests = []

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], 'Unexpected browser errors')
        finally:
            for context in self.contexts:
                context.close()

    def boot(self, raw=None, unavailable_masks=()):
        context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.contexts.append(context)
        context.add_init_script("""(() => {
            const raw = %s, key = %s;
            const set = Storage.prototype.setItem, remove = Storage.prototype.removeItem;
            if (raw !== null) set.call(localStorage, key, raw);
            window.maskRevisionStorageWrites = [];
            Storage.prototype.setItem = function(k, value) {
                if (this === localStorage && k === key) window.maskRevisionStorageWrites.push(['set', value]);
                return set.call(this, k, value);
            };
            Storage.prototype.removeItem = function(k) {
                if (this === localStorage && k === key) window.maskRevisionStorageWrites.push(['remove']);
                return remove.call(this, k);
            };
        })();""" % (json.dumps(raw), json.dumps(DRAFT_KEY)))
        page = context.new_page()
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.on('console', lambda message: self.errors.append(message.text)
                if message.type == 'error' else None)
        page.on('response', lambda response: self.errors.append(f'{response.status}: {response.url}')
                if response.status >= 400 else None)
        for pattern in unavailable_masks:
            self.unavailable_mask(page, pattern)
        page.goto(self.url)
        try:
            page.wait_for_function('window.gilneasApp?.ready', polling=100, timeout=15000)
        except Exception:
            self.fail('Valid active snapshot must boot independently of an unavailable baseline mask: '
                      + page.locator('#toast').text_content())
        page.wait_for_function("document.getElementById('base-map').complete && document.getElementById('base-map').naturalWidth > 0", polling=100)
        return page

    def fixture(self, page, name):
        return page.evaluate("""async name => {
            const response = await fetch(new URL('assets/data/' + name, document.baseURI), {cache: 'no-store'});
            if (!response.ok) throw Error('Real publication fixture unavailable: ' + response.status);
            return response.json();
        }""", name)

    def snapshot(self, page):
        return page.evaluate('window.gilneasApp.getData()')

    def stored(self, page):
        return page.evaluate('key => localStorage.getItem(key)', DRAFT_KEY)

    def unavailable_mask(self, page, pattern):
        def fail_decode(route):
            self.failed_mask_requests.append(route.request.url)
            # A successful HTTP response with unreadable image bytes exercises
            # real Image.decode failure without replacing any raster success.
            route.fulfill(status=200, content_type='image/png', body=b'')
        page.route(pattern, fail_decode)

    def exact_live_draft(self, page):
        snapshot = self.snapshot(page)
        raw = json.dumps(snapshot, ensure_ascii=False, indent=3) + '\n'
        page.evaluate("raw => {localStorage.setItem('gilneas-atlas-draft-v1', raw); window.maskRevisionStorageWrites = [];}", raw)
        self.assertEqual(self.stored(page), raw)
        return snapshot, raw, self.eligibility(page, snapshot)

    def enable_editing(self, page):
        if not page.locator('#editing-enabled').is_checked():
            if not page.locator('#editor').evaluate('element => element.open'):
                page.locator('#editor-open').click()
            page.locator('label:has(#editing-enabled)').click()
            page.locator('[data-close=editor]').click()

    def native_import(self, page, snapshot, name='mask-revision.json'):
        self.enable_editing(page)
        if not page.locator('#editor').evaluate('element => element.open'):
            page.locator('#editor-open').click()
        page.locator('#import-json').set_input_files({
            'name': name, 'mimeType': 'application/json',
            'buffer': json.dumps(snapshot, ensure_ascii=False).encode('utf-8'),
        })
        page.wait_for_function("!document.getElementById('import-json').disabled && document.getElementById('import-json').value === ''", polling=100)
        return page.locator('#editor-error').text_content()

    def eligibility(self, page, snapshot):
        grid = snapshot['territoryGrid']
        shape = {key: grid[key] for key in ('width', 'height', 'step', 'mapWidth', 'mapHeight')}
        return page.evaluate("""async shape => {
            const {cellPoint} = await import(new URL('assets/js/territory-engine.mjs', document.baseURI));
            const values = [[8, 8], [100, 10], [0, 0], [shape.mapWidth, shape.mapHeight],
                [-1, 0], [0, -1], [shape.mapWidth + 1, 0], [0, shape.mapHeight + 1]]
                .map(point => window.gilneasApp.canPlace(point));
            for (let y = 0; y < shape.height; y++) for (let x = 0; x < shape.width; x++) {
                values.push(window.gilneasApp.canPlace(cellPoint(shape, x, y)));
            }
            return values;
        }""", shape)

    def real_grid(self, page, snapshot):
        return page.evaluate("""async snapshot => {
            const {prepareTerritoryGrid} = await import(new URL('assets/js/territory-data.mjs', document.baseURI));
            const image = new Image();
            await new Promise((resolve, reject) => {
                image.onload = resolve; image.onerror = reject;
                image.src = new URL(snapshot.meta.inactiveMask || 'assets/maps/inactive-mask.png', document.baseURI);
            });
            const canvas = document.createElement('canvas');
            canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
            const ctx = canvas.getContext('2d', {willReadFrequently: true});
            ctx.drawImage(image, 0, 0);
            const canPlace = ([x, y]) => {
                if (x < 0 || y < 0 || x > snapshot.meta.width || y > snapshot.meta.height) return false;
                const px = Math.min(canvas.width - 1, Math.floor(x * canvas.width / snapshot.meta.width));
                const py = Math.min(canvas.height - 1, Math.floor(y * canvas.height / snapshot.meta.height));
                return ctx.getImageData(px, py, 1, 1).data[0] < 128;
            };
            return prepareTerritoryGrid(snapshot, canPlace).territoryGrid;
        }""", snapshot)

    def assert_values(self, actual, expected, label):
        self.assertEqual(len(actual), len(expected), label + ': sample count')
        differences = [index for index, (left, right) in enumerate(zip(actual, expected)) if left != right]
        self.assertEqual(len(differences), 0,
                         f'{label}: {len(differences)} mismatches; first indices {differences[:8]}')

    def assert_grid(self, actual, expected, label):
        self.assertEqual({key: value for key, value in actual.items() if key != 'cells'},
                         {key: value for key, value in expected.items() if key != 'cells'},
                         label + ': exact grid metadata/keys')
        self.assert_values(actual['cells'], expected['cells'], label + ': generated grid cells')

    def test_01_reset_restores_origins_mask_after_cropped_legacy_fallback(self):
        fresh = self.boot()
        origins = self.snapshot(fresh)
        expected_eligibility = self.eligibility(fresh, origins)
        self.assertFalse(expected_eligibility[0], 'Real Origins raster rejects [8,8]')
        old = self.fixture(fresh, 'publication-v2.json')
        city = next(location for location in old['locations'] if location['id'] == 'gilneas-city')
        city['x'], city['y'] = 100, 10
        raw = json.dumps(old, ensure_ascii=False, indent=3) + '\n'
        fallback = self.boot(raw)
        active = self.snapshot(fallback)
        self.assertEqual([active['meta']['width'], active['meta']['height']], [3247, 4860])
        self.assertEqual(next(location for location in active['locations'] if location['id'] == city['id'])['x'], 100)
        self.assertTrue(fallback.evaluate('window.gilneasApp.canPlace([8,8])'))
        self.assert_grid(active['territoryGrid'], self.real_grid(fresh, old), 'Fallback old raster')
        self.assertEqual(self.stored(fallback), raw, 'Startup preserves exact original draft string')
        self.assertEqual(fallback.evaluate('window.maskRevisionStorageWrites'), [], 'No startup migration writes')
        self.enable_editing(fallback)
        fallback.locator('#editor-open').click()
        fallback.locator('#draft-reset').click()
        fallback.locator('#confirm-yes').click()
        fallback.wait_for_function("localStorage.getItem('gilneas-atlas-draft-v1') === null", polling=100)
        fallback.evaluate('window.gilneasApp.boundaries.whenReady()')
        reset = self.snapshot(fallback)
        actual_eligibility = self.eligibility(fallback, origins)
        eligibility_mismatches = sum(left != right for left, right in zip(actual_eligibility, expected_eligibility))
        grid_mismatches = sum(left != right for left, right in zip(reset['territoryGrid']['cells'], origins['territoryGrid']['cells']))
        print(f'Reset comparison: {eligibility_mismatches}/{len(expected_eligibility)} eligibility mismatches; '
              f'{grid_mismatches}/{len(origins["territoryGrid"]["cells"])} grid differences')
        self.assert_values(actual_eligibility, expected_eligibility, 'Reset Origins eligibility')
        self.assert_grid(reset['territoryGrid'], origins['territoryGrid'], 'Reset Origins baseline')
        self.assertEqual({key: value for key, value in reset.items() if key != 'territoryGrid'},
                         {key: value for key, value in origins.items() if key != 'territoryGrid'})
        print(f'Reset Origins: 0/{len(expected_eligibility)} eligibility mismatches; '
              f'0/{len(origins["territoryGrid"]["cells"])} grid differences; no startup writes')

    def test_02_old_map_import_samples_target_raster_for_missing_grid(self):
        current = self.boot()
        origins = self.snapshot(current)
        self.assertFalse(current.evaluate('window.gilneasApp.canPlace([8,8])'))
        old = self.fixture(current, 'publication-v2.json')
        city = next(location for location in old['locations'] if location['id'] == 'gilneas-city')
        city['x'], city['y'] = 100, 10
        independent_old = self.boot(json.dumps(old, ensure_ascii=False))
        expected_old = self.snapshot(independent_old)
        expected_eligibility = self.eligibility(independent_old, expected_old)
        self.assertTrue(expected_eligibility[0], 'Real old raster accepts [8,8]')
        self.assert_grid(expected_old['territoryGrid'], self.real_grid(current, old), 'Independent old bootstrap')
        self.assertEqual(self.native_import(current, old), '', 'Incoming old mask must be ready before commit')
        current.evaluate('window.gilneasApp.boundaries.whenReady()')
        imported = self.snapshot(current)
        self.assertEqual([imported['meta']['width'], imported['meta']['height']], [3247, 4860])
        self.assertTrue(current.evaluate('window.gilneasApp.canPlace([8,8])'))
        self.assert_values(self.eligibility(current, imported), expected_eligibility, 'Imported old-map eligibility')
        self.assert_grid(imported['territoryGrid'], expected_old['territoryGrid'], 'Imported old-map missing grid')
        self.assertEqual(json.loads(self.stored(current)), imported, 'Only correctly prepared snapshot is stored')
        self.assertEqual(current.evaluate('window.maskRevisionStorageWrites.length'), 1)
        self.assertNotEqual(origins['territoryGrid']['mapHeight'], imported['territoryGrid']['mapHeight'])
        print(f'Old-map import: [8,8]=true; 0/{len(expected_eligibility)} eligibility mismatches; '
              f'0/{len(imported["territoryGrid"]["cells"])} grid differences')

    def test_03_unavailable_import_keeps_exact_live_storage_and_active_mask(self):
        page = self.boot()
        before, raw, expected_eligibility = self.exact_live_draft(page)
        pattern = '**/assets/maps/origins-inactive-mask.png?mask-revision=unavailable'
        self.unavailable_mask(page, pattern)
        for with_grid in (False, True):
            with self.subTest(manual_grid=with_grid):
                incoming = json.loads(json.dumps(before))
                incoming['meta']['inactiveMask'] += '?mask-revision=unavailable'
                if not with_grid:
                    del incoming['territoryGrid']
                error = self.native_import(page, incoming, 'unavailable-mask.json')
                self.assertRegex(error, 'маск', 'Failed incoming mask must reject the import')
                self.assertEqual(self.snapshot(page), before)
                self.assertEqual(self.stored(page), raw, 'Failed import preserves exact whitespace in storage')
                self.assert_values(self.eligibility(page, before), expected_eligibility, 'Active mask after failed import')
                self.assertEqual(page.evaluate('window.maskRevisionStorageWrites'), [])
        self.assertEqual(len(self.failed_mask_requests), 2, 'Failed target is retried, never borrowed from active cache')
        result = page.evaluate("""snapshot => {
            const result = window.gilneasApp.replaceData(snapshot);
            return {thenable: typeof result?.then === 'function', snapshot: result};
        }""", before)
        self.assertFalse(result['thenable'], 'Same-map edits stay synchronous after mask IO failure')
        self.assertEqual(result['snapshot'], before)
        self.assertEqual(self.snapshot(page), before)
        self.assert_values(self.eligibility(page, before), expected_eligibility, 'Cached active mask still usable')
        print('Unavailable import: 2 real decode failures; exact live/string/eligibility preserved; active sync commit usable')

    def test_04_reset_mask_failure_preserves_old_live_snapshot_and_exact_storage(self):
        fresh = self.boot()
        origins = self.snapshot(fresh)
        expected_origins = self.eligibility(fresh, origins)
        old = self.fixture(fresh, 'publication-v2.json')
        city = next(location for location in old['locations'] if location['id'] == 'gilneas-city')
        city['x'], city['y'] = 100, 10
        pattern = '**/assets/maps/origins-inactive-mask.png'
        page = self.boot(json.dumps(old, ensure_ascii=False, indent=3) + '\n', unavailable_masks=[pattern])
        before, raw, expected_old = self.exact_live_draft(page)
        self.assertTrue(expected_old[0], 'Old active mask is ready despite failed baseline preload')
        self.assertEqual([before['meta']['width'], before['meta']['height']], [3247, 4860])
        self.assertEqual(page.evaluate('window.maskRevisionStorageWrites'), [])
        self.enable_editing(page)
        page.locator('#editor-open').click()
        page.locator('#draft-reset').click()
        page.locator('#confirm-yes').click()
        page.wait_for_function("!document.getElementById('draft-reset').disabled", polling=100)
        self.assertRegex(page.locator('#editor-error').text_content(), 'маск')
        self.assertEqual(self.snapshot(page), before, 'Failed reset preserves exact live snapshot')
        self.assertEqual(self.stored(page), raw, 'Failed reset must not remove or rewrite the stored draft')
        self.assert_values(self.eligibility(page, before), expected_old, 'Old active raster after failed reset')
        self.assertEqual(page.evaluate('window.maskRevisionStorageWrites'), [])
        self.assertEqual(len(self.failed_mask_requests), 2, 'Reset retries failed baseline preload')
        page.unroute(pattern)
        page.locator('#draft-reset').click()
        page.locator('#confirm-yes').click()
        page.wait_for_function("localStorage.getItem('gilneas-atlas-draft-v1') === null", polling=100)
        page.evaluate('window.gilneasApp.boundaries.whenReady()')
        self.assert_values(self.eligibility(page, origins), expected_origins, 'Reset recovery Origins raster')
        self.assert_grid(self.snapshot(page)['territoryGrid'], origins['territoryGrid'], 'Reset recovery baseline')
        self.assertEqual(page.evaluate('window.maskRevisionStorageWrites'), [['remove']])
        print('Unavailable reset: failed preload + reset leave exact live/string/old mask; retry restores exact Origins grid')

    def test_05_uncached_synchronous_commit_rejects_before_state_or_storage(self):
        page = self.boot()
        before, raw, expected_eligibility = self.exact_live_draft(page)
        self.enable_editing(page)
        for with_grid in (True, False):
            with self.subTest(author_grid=with_grid):
                incoming = json.loads(json.dumps(before))
                incoming['meta']['inactiveMask'] += '?mask-revision=uncached'
                if with_grid:
                    incoming['territoryGrid']['cells'][0] = 1
                    incoming['territoryGrid']['authorNote'] = 'Manual owner even in inactive cell; do not repaint'
                else:
                    del incoming['territoryGrid']
                result = page.evaluate("""snapshot => {
                    try {
                        const result = window.gilneasApp.replaceData(snapshot);
                        return {error: null, thenable: typeof result?.then === 'function'};
                    } catch (error) {return {error: error.message, thenable: false};}
                }""", incoming)
                self.assertIsNotNone(result['error'], 'Uncached map-changing commit must throw, including author grids')
                self.assertRegex(result['error'], 'маск|Маск')
                self.assertFalse(result['thenable'], 'replaceData remains a synchronous API')
                self.assertEqual(self.snapshot(page), before, 'Rejected commit must not change live state')
                self.assertEqual(self.stored(page), raw, 'Rejected commit must not rewrite exact stored string')
                self.assert_values(self.eligibility(page, before), expected_eligibility, 'Active raster after uncached commit')
                self.assertEqual(page.evaluate('window.maskRevisionStorageWrites'), [])
        print('Uncached synchronous commit: author-grid and missing-grid attempts rejected before live/storage changes')

    def test_06_cached_map_switches_keep_manual_keys_owners_and_erasures(self):
        page = self.boot()
        origins = self.snapshot(page)
        expected_origins = self.eligibility(page, origins)
        old = self.fixture(page, 'publication-v2.json')
        city = next(location for location in old['locations'] if location['id'] == 'gilneas-city')
        city['x'], city['y'] = 100, 10
        independent_old = self.boot(json.dumps(old, ensure_ascii=False))
        old_snapshot = self.snapshot(independent_old)
        expected_old = self.eligibility(independent_old, old_snapshot)
        self.assertEqual(self.native_import(page, old), '')
        self.assert_grid(self.snapshot(page)['territoryGrid'], old_snapshot['territoryGrid'], 'First old-map preparation')
        manual_snapshots = []
        for source, eligibility in ((old_snapshot, expected_old), (origins, expected_origins)):
            manual = json.loads(json.dumps(source))
            grid = manual['territoryGrid']
            old_keys = grid['keys'][:]
            grid['keys'].reverse()
            grid['cells'] = [grid['keys'].index(old_keys[value - 1]) + 1 if value else 0 for value in grid['cells']]
            erased = next(index for index, value in enumerate(grid['cells']) if value)
            blocked = next(index for index, allowed in enumerate(eligibility[8:]) if not allowed)
            grid['cells'][erased] = 0
            grid['cells'][blocked] = len(grid['keys'])
            grid['authorMaskRevision'] = {'erase': erased, 'inactiveOwner': blocked, 'literal': '  manual grid  '}
            manual_snapshots.append((manual, eligibility))
        for pattern in ('**/assets/maps/inactive-mask.png', '**/assets/maps/origins-inactive-mask.png'):
            self.unavailable_mask(page, pattern)
        for round_number in range(2):
            for manual, eligibility in manual_snapshots:
                self.assertEqual(self.native_import(page, manual), '', 'Known masks must reuse successful readiness')
                result = page.evaluate("""snapshot => {
                    const result = window.gilneasApp.replaceData(snapshot);
                    return {thenable: typeof result?.then === 'function', snapshot: result};
                }""", manual)
                self.assertFalse(result['thenable'], 'Editor/territory replaceData stays synchronous')
                self.assertEqual(result['snapshot'], manual)
                self.assertEqual(self.snapshot(page), manual)
                self.assertEqual(json.loads(self.stored(page)), manual)
                self.assert_values(self.eligibility(page, manual), eligibility, f'Cached switch {round_number + 1}')
                self.assert_grid(self.snapshot(page)['territoryGrid'], manual['territoryGrid'], 'Manual grid never regenerated')
                page.evaluate('window.gilneasApp.boundaries.whenReady()')
        self.assertEqual(self.failed_mask_requests, [], 'Ready masks require no replacement IO for repeated switches')
        # Cached cross-map commits, not just same-map edits, also keep the API synchronous.
        for manual, eligibility in manual_snapshots:
            result = page.evaluate("""snapshot => {
                const result = window.gilneasApp.replaceData(snapshot);
                return {thenable: typeof result?.then === 'function', snapshot: result};
            }""", manual)
            self.assertFalse(result['thenable'])
            self.assertEqual(result['snapshot'], manual)
            self.assertEqual(self.snapshot(page), manual)
            self.assertEqual(json.loads(self.stored(page)), manual)
            self.assert_values(self.eligibility(page, manual), eligibility, 'Cached synchronous cross-map switch')
        print('Known maps switched old/current twice: no extra mask IO; exact manual keys/owners/0 erasures retained; sync commits')


if __name__ == '__main__':
    unittest.main()
