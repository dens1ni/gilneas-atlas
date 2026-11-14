"""Browser acceptance tests for ui.mjs only; never boot the parent app.

All records below are TEST FIXTURES, not additions to atlas lore. Gilneas uses
its confirmed atlas test anchor (1800, 3400); other records say «Тест».
Run: /Users/daniil_si/.hermes/cache/scratch/gilneas-venv/bin/python tests/test_ui.py -v
"""
import copy
import functools
import json
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-ui-evidence')
DATA = {
    'version': 1,
    'meta': {
        'width': 3247, 'height': 4860,
        'image': 'assets/maps/gilneas-enhanced.webp',
        'mist': 'assets/maps/inactive-mist.webp',
        'labels': [{'x': 1930, 'y': 2950, 'text': 'ГИЛНЕАС', 'size': 16}],
    },
    'factions': [
        {'id': 'gilneas', 'name': 'Гилнеас', 'color': '#ad4255', 'parent': None},
        {'id': 'test-house', 'name': 'Тестовый дом', 'color': '#bd8d59', 'parent': 'gilneas'},
        {'id': 'test-vassal', 'name': 'Тестовый младший дом', 'color': '#748e62', 'parent': 'test-house'},
        {'id': 'test-other', 'name': 'Тестовая держава', 'color': '#9072ab', 'parent': None},
    ],
    'locations': [
        {'id': 'gilneas-city', 'name': 'Гилнеас', 'type': 'city', 'faction': 'gilneas',
         'x': 1800, 'y': 3400, 'capital': True, 'owner': '',
         'description': 'Тестовое описание.\nВторая строка.',
         'provenance': {'confidence': 'confirmed', 'note': 'Тестовая ссылка на источник.', 'sources': ['test-source']},
         'objects': []},
        {'id': 'test-estate', 'name': 'Тестовое поместье', 'type': 'estate', 'faction': 'test-house',
         'house': 'Тестовый дом', 'x': 1950, 'y': 3200, 'owner': 'Тестовый владелец',
         'description': '', 'provenance': {'confidence': 'reconstruction'}, 'objects': []},
        {'id': 'test-forest', 'name': 'Тестовый лес', 'type': 'forest', 'faction': 'test-vassal',
         'x': 1550, 'y': 3600, 'owner': '', 'description': '', 'objects': []},
        {'id': 'test-other-city', 'name': 'Тестовый иной город', 'type': 'city', 'faction': 'test-other',
         'x': 2300, 'y': 2200, 'owner': '', 'description': '', 'objects': []},
    ],
    'territories': [
        {'id': 'test-area', 'faction': 'gilneas', 'points': [[1100, 2450], [2500, 2450], [2500, 4300], [1100, 4300]]},
        {'id': 'test-house-area', 'faction': 'test-house', 'points': [[1700, 3000], [2100, 3000], [2100, 3300], [1700, 3300]]},
    ],
    'nobles': [{'id': 'test-noble', 'name': 'Тестовый дворянин', 'title': 'Тестовый титул',
                'description': 'Только тестовая запись.', 'house': 'Тестовый дом'}],
    'sources': [{'id': 'test-source', 'url': 'https://example.org/test-source',
                 'title': 'Тестовый источник', 'quote': 'Тестовая цитата.'}],
}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class UITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=[
            '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
        ])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.page = self.context.new_page()
        self.errors = []
        self.console_errors = []
        self.http_errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.console_errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.http_errors.append([response.status, response.url]) if response.status >= 400 else None)
        # Parent bootstrap is intentionally absent/disabled in this fixture.
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
            status=200, content_type='application/javascript', body='// UI fixture: no parent bootstrap.'))
        # Parent owns decoration. An absent background is not a UI-module error.
        if not (ROOT / 'assets/ui/parchment.webp').exists():
            self.page.route('**/assets/ui/parchment.webp', lambda route: route.fulfill(status=204))

    def tearDown(self):
        self.context.close()

    def boot(self, data=None, storage=None, size=None):
        if size:
            self.page.set_viewport_size(size)
        if storage:
            self.page.add_init_script(f"if (localStorage.getItem('gilneas-atlas-favorites-v1') === null) localStorage.setItem('gilneas-atlas-favorites-v1', {json.dumps(storage)});")
        self.page.goto(self.url + '/index.html', wait_until='networkidle')
        self.page.evaluate("""async data => {
            window.fixtureData = data;
            window.fixtureSelected = null;
            window.calls = [];
            window.uiLoadError = null;
            try {
                const module = await import('./assets/js/ui.mjs');
                window.ui = module.initUI({
                    getData: () => window.fixtureData,
                    getSelectedId: () => window.fixtureSelected,
                    onSelect: id => { window.fixtureSelected = id; window.calls.push(['select', id]); window.ui.render(); },
                    onEditLocation: id => window.calls.push(['edit', id]),
                    onAddObject: id => window.calls.push(['add', id]),
                    onEditObject: (id, objectId) => window.calls.push(['edit-object', id, objectId]),
                    onDeleteObject: (id, objectId) => window.calls.push(['delete-object', id, objectId]),
                    onShowNoble: id => window.calls.push(['noble', id]),
                    onFavoriteChange: (...args) => window.calls.push(['favorite', ...args]),
                });
            } catch (error) { window.uiLoadError = String(error); }
        }""", copy.deepcopy(data or DATA))
        self.assertIsNone(self.page.evaluate('window.uiLoadError'), 'ui.mjs must provide a working initUI(context)')
        self.page.wait_for_function("document.querySelector('#base-map').complete && document.querySelector('#base-map').naturalWidth > 0", polling=50)
        self.page.wait_for_timeout(40)

    def camera(self):
        return self.page.evaluate('window.ui.getCamera()')

    def visible_location_ids(self, scope='#location-list'):
        return self.page.locator(scope + ' [data-location-id]').evaluate_all(
            '(nodes) => nodes.filter(node => !node.hidden).map(node => node.dataset.locationId)')

    def assert_clean(self):
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])
        self.assertEqual(self.http_errors, [])

    def test_01_initial_render_api_real_map_navigation_and_home(self):
        self.boot()
        expected = ['render', 'renderDossier', 'focusLocation', 'home', 'fit', 'zoom',
                    'setPanel', 'toMap', 'getCamera', 'setMapInteraction', 'refreshViewport']
        self.assertEqual(self.page.evaluate('(keys) => keys.filter(key => typeof window.ui[key] !== "function")', expected), [])
        self.assertEqual(self.page.locator('#world').evaluate('node => [node.style.width, node.style.height]'), ['3247px', '4860px'])
        self.assertEqual(self.page.locator('#territory-layer').get_attribute('viewBox'), '0 0 3247 4860')
        self.assertTrue(self.page.locator('#base-map').get_attribute('src').endswith('gilneas-enhanced.webp'))
        self.assertTrue(self.page.locator('#mist-map').get_attribute('src').endswith('inactive-mist.webp'))
        self.assertEqual(self.page.locator('.map-marker').count(), 4)
        marker = self.page.locator('.map-marker[data-location-id="gilneas-city"]')
        self.assertIsNone(marker.get_attribute('title'), 'Custom hover replaces the competing native title')
        self.assertEqual(marker.get_attribute('aria-label'), 'Гилнеас')
        self.assertEqual(marker.evaluate('node => [node.style.left, node.style.top]'), ['1800px', '3400px'])
        self.assertGreater(marker.locator('svg path, svg use').count(), 0)
        self.assertEqual(self.page.locator('#region-labels').inner_text(), 'ГИЛНЕАС')
        self.assertEqual(self.page.locator('details.group').count(), 4)
        self.assertEqual(self.page.locator('details.group .group-count').all_text_contents(), ['3', '2', '1', '1'])
        self.assertEqual(set(self.visible_location_ids()), {record['id'] for record in DATA['locations']})
        self.assertEqual(self.page.locator('#result-count').inner_text(), '4 владения')
        self.assertTrue(self.page.locator('#dossier').is_hidden())
        self.assertTrue(self.page.locator('#navigation').is_visible())
        self.assertTrue(self.page.locator('#layers').is_visible())
        self.assertEqual(self.page.evaluate("(() => { const ids = [...document.querySelectorAll('[id]')].map(node => node.id); return ids.length === new Set(ids).size; })()"), True)
        camera = self.camera()
        self.assertGreater(camera['scale'], 0)
        self.assertTrue(self.page.locator('#world').evaluate('node => Number(node.style.getPropertyValue("--inverse-scale")) > 0'))
        self.assert_clean()
    def test_02_registry_search_favorites_nobles_and_group_folding(self):
        self.boot(storage=json.dumps(['test-estate']))
        self.page.locator('#search').fill('ТЕСТОВЫЙ ВЛАДЕЛЕЦ')
        self.assertEqual(self.visible_location_ids(), ['test-estate'])
        self.page.locator('#search').fill('ТЕСТОВЫЙ ДОМ')
        self.assertEqual(self.visible_location_ids(), ['test-estate'])
        self.page.locator('#search').fill('')
        self.page.locator('#filter-favorites').click()
        self.assertEqual(self.visible_location_ids(), ['test-estate'])
        self.assertEqual(self.page.locator('#filter-favorites').get_attribute('aria-pressed'), 'true')
        self.page.locator('#filter-nobles').click()
        self.assertEqual(self.page.locator('button.noble-row').count(), 1)
        self.assertIn('Тестовый дворянин', self.page.locator('button.noble-row').inner_text())
        self.page.locator('button.noble-row').click()
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['noble', 'test-noble'])
        self.page.locator('#search').fill('НЕСУЩЕСТВУЮЩИЙ')
        self.assertEqual(self.page.locator('button.noble-row').count(), 0)
        self.page.locator('#search').fill('')
        self.page.locator('#filter-all').click()
        self.page.locator('#fold-groups').click()
        self.assertEqual(self.page.locator('details.group[open]').count(), 0)
        self.page.evaluate('window.ui.render()')
        self.assertEqual(self.page.locator('details.group[open]').count(), 0)
        self.page.locator('#fold-groups').click()
        self.assertEqual(self.page.locator('details.group[open]').count(), 4)
        row = self.page.locator('button.location-row[data-location-id="gilneas-city"]')
        self.assertEqual(row.locator('.location-type').inner_text(), 'Город')
        self.assertEqual(self.page.locator('#filter-all').get_attribute('aria-pressed'), 'true')
        self.assert_clean()
    def test_03_sovereign_filter_keeps_descendants_and_layer_controls(self):
        self.boot()
        self.assertEqual(self.page.locator('button.faction-row').count(), 4)
        vassal = self.page.locator('button.faction-row[data-faction-id="test-house"]')
        self.assertIn('vassal', vassal.get_attribute('class'))
        self.assertIn('Гилнеас', vassal.locator('.faction-parent').inner_text())
        self.assertEqual(vassal.evaluate('node => node.style.getPropertyValue("--faction-color")'), '#bd8d59')
        polygon = self.page.locator('polygon[data-territory-id="test-house-area"]')
        self.assertEqual(polygon.get_attribute('points'), '1700,3000 2100,3000 2100,3300 1700,3300')
        self.assertEqual(polygon.get_attribute('fill'), '#bd8d59')
        self.assertEqual(polygon.get_attribute('fill-opacity'), '0.15')
        self.assertEqual(polygon.get_attribute('stroke-opacity'), '0.55')
        self.page.locator('button.faction-row[data-faction-id="gilneas"]').click()
        self.assertEqual(set(self.visible_location_ids()), {'gilneas-city', 'test-estate', 'test-forest'})
        self.assertNotIn('dimmed', self.page.locator('.map-marker[data-location-id="test-forest"]').get_attribute('class'))
        self.assertIn('dimmed', self.page.locator('.map-marker[data-location-id="test-other-city"]').get_attribute('class'))
        vassal.click()
        self.assertEqual(set(self.visible_location_ids()), {'test-estate', 'test-forest'})
        self.page.locator('#faction-clear').click()
        self.assertEqual(len(self.visible_location_ids()), 4)
        self.page.locator('label:has(#show-territories)').click()
        self.assertFalse(self.page.locator('#show-territories').is_checked())
        self.assertTrue(self.page.locator('#territory-layer').is_hidden())
        self.page.locator('label:has(#show-labels)').click()
        self.assertIn('show-labels', self.page.locator('#world').get_attribute('class'))
        self.assertTrue(self.page.locator('#show-reconstructions').is_hidden())
        self.page.evaluate("document.querySelector('#show-reconstructions').checked=false;window.ui.render()")
        self.assertTrue(self.page.locator('.map-marker[data-location-id="test-estate"]').is_visible(), 'Historical bookkeeping no longer hides locations')
        self.page.evaluate("window.fixtureSelected = 'test-estate'; window.ui.render()")
        self.assertTrue(self.page.locator('.map-marker[data-location-id="test-estate"]').is_visible())
        self.page.evaluate("window.fixtureSelected = null; window.ui.render(); window.ui.setPanel('layers', true)")
        self.page.locator('#layers-fold').click()
        self.assertTrue(self.page.locator('#layer-body').is_hidden())
        self.assertEqual(self.page.locator('#layers-fold').get_attribute('aria-expanded'), 'false')
        self.page.locator('#layers-fold').click()
        self.assertTrue(self.page.locator('#layer-body').is_visible())
        self.assertEqual(self.page.evaluate('window.fixtureData.territories[1].points'), DATA['territories'][1]['points'])
        self.assert_clean()
    def test_04_selected_parchment_dossier_objects_citations_and_safe_text(self):
        fixture = copy.deepcopy(DATA)
        unsafe = '<img src=x onerror="window.uiXss=1"> & <script>window.uiXss=2</script>'
        fixture['locations'][0]['description'] = unsafe + '\nВторая строка.'
        fixture['locations'][0]['objects'] = [
            {'id': 'test-building', 'type': 'building', 'name': 'Тестовое здание',
             'description': unsafe, 'owner': '',
             'modifiers': [{'id': 'test-bonus', 'kind': 'bonus', 'text': unsafe},
                           {'id': 'test-bonus-two', 'kind': 'bonus', 'text': 'Тестовый второй бонус'},
                           {'id': 'test-penalty', 'kind': 'penalty', 'text': 'Тестовый штраф'}],
             'provenance': {'sources': ['test-source']}},
            {'id': 'test-resource', 'type': 'resource', 'name': 'Тестовый ресурс',
             'description': 'Тестовый запас.', 'amount': '20 тестовых единиц', 'faction': None, 'owner': '', 'modifiers': []},
            {'id': 'test-landmark', 'type': 'landmark', 'name': 'Тестовое особое место',
             'description': '', 'faction': 'test-house', 'owner': 'Тестовый хранитель', 'modifiers': []},
        ]
        fixture['sources'].append({'id': 'unsafe-source', 'url': 'javascript:window.uiXss=3', 'title': unsafe})
        fixture['locations'][0]['provenance']['sources'].append('unsafe-source')
        self.boot(fixture)
        self.page.locator('button.location-row[data-location-id="gilneas-city"]').click()
        self.assertTrue(self.page.locator('#dossier').is_visible())
        self.assertTrue(self.page.locator('#layers').is_hidden())
        self.assertIn('dossier-open', self.page.locator('body').get_attribute('class'))
        self.assertEqual(self.page.locator('#dossier-title').inner_text(), 'Гилнеас')
        self.assertEqual(self.page.locator('#dossier-owner').inner_text(), 'Не установлен')
        self.assertEqual(self.page.locator('#dossier-sovereign').inner_text(), 'Гилнеас')
        self.assertEqual(self.page.locator('#dossier-description').text_content(), unsafe + '\nВторая строка.')
        self.assertEqual(self.page.locator('#dossier-provenance .confidence').count(),0,'Keep historical bookkeeping out of the dossier')
        self.assertEqual(self.page.locator('#dossier-provenance a').first.inner_text(), '[1]')
        self.assertEqual(self.page.locator('#dossier-provenance a').first.get_attribute('href'), 'https://example.org/test-source')
        self.assertEqual(self.page.locator('#dossier-provenance a').first.get_attribute('rel'), 'noopener noreferrer')
        self.assertEqual(self.page.locator('details.object-card').count(), 3)
        building = self.page.locator('details.object-card[data-object-id="test-building"]')
        building.locator('summary').click()
        self.assertEqual(building.locator('.object-title').inner_text(), 'Тестовое здание')
        self.assertEqual(building.locator('li.modifier.bonus').count(), 2)
        self.assertEqual(building.locator('li.modifier.penalty').count(), 1)
        self.assertEqual(building.locator('li.modifier.bonus').first.text_content(), unsafe)
        self.assertIn('Гилнеас', building.locator('.object-ownership').inner_text())
        resource = self.page.locator('details.object-card[data-object-id="test-resource"]')
        resource.locator('summary').click()
        self.assertIn('Независим', resource.locator('.object-ownership').inner_text())
        self.assertIn('20 тестовых единиц', resource.locator('.amount').inner_text())
        landmark = self.page.locator('details.object-card[data-object-id="test-landmark"]')
        landmark.locator('summary').click()
        self.assertIn('Тестовый дом', landmark.locator('.object-ownership').inner_text())
        self.assertIn('Тестовый хранитель', landmark.locator('.object-ownership').inner_text())
        for selector, call in [('[data-object-edit="test-building"]', ['edit-object', 'gilneas-city', 'test-building']),
                               ('[data-object-delete="test-building"]', ['delete-object', 'gilneas-city', 'test-building'])]:
            button = self.page.locator(selector)
            self.assertTrue(button.get_attribute('title'))
            button.click()
            self.assertEqual(self.page.evaluate('window.calls.at(-1)'), call)
        self.page.locator('#dossier-sources > summary').click()
        self.assertEqual(self.page.locator('#dossier-source-list a').count(), 1)
        self.assertIn(unsafe, self.page.locator('#dossier-source-list').text_content())
        self.assertEqual(self.page.locator('#dossier script, #dossier img').count(), 0)
        self.assertIsNone(self.page.evaluate('window.uiXss'))
        self.page.locator('#dossier-edit').click()
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['edit', 'gilneas-city'])
        self.page.locator('#dossier-add-object').click()
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['add', 'gilneas-city'])
        self.page.locator('#dossier-fold').click()
        self.assertTrue(self.page.locator('#dossier-body').is_hidden())
        self.assertIn('folded', self.page.locator('#dossier').get_attribute('class'))
        self.assertEqual(self.page.locator('#dossier-fold').get_attribute('aria-expanded'), 'false')
        self.page.locator('#dossier-fold').click()
        self.assertTrue(self.page.locator('#dossier-body').is_visible())
        self.page.locator('#dossier-close').click()
        self.assertTrue(self.page.locator('#dossier').is_hidden())
        self.assertTrue(self.page.locator('#layers').is_visible())
        self.page.evaluate('window.ui.render()')
        self.assertTrue(self.page.locator('#dossier').is_hidden())
        self.assertEqual(self.page.evaluate('window.fixtureSelected'), 'gilneas-city')
        self.page.locator('button.location-row[data-location-id="gilneas-city"]').click()
        self.assertTrue(self.page.locator('#dossier').is_visible(), 'reselecting the same location must reopen its closed dossier')
        self.assert_clean()
    def test_05_favorites_are_view_only_and_survive_reload(self):
        self.boot(storage='not valid json')
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        self.page.locator('button.location-row[data-location-id="gilneas-city"]').click()
        favorite = self.page.locator('#dossier-favorite')
        self.assertEqual(favorite.get_attribute('aria-pressed'), 'false')
        favorite.click()
        self.assertEqual(favorite.get_attribute('aria-pressed'), 'true')
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('gilneas-atlas-favorites-v1'))"), ['gilneas-city'])
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['favorite', 'gilneas-city', True])
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before)
        self.boot()
        self.page.locator('#filter-favorites').click()
        self.assertEqual(self.visible_location_ids(), ['gilneas-city'])
        self.page.locator('button.location-row[data-location-id="gilneas-city"]').click()
        self.assertEqual(favorite.get_attribute('aria-pressed'), 'true')
        favorite.click()
        self.assertEqual(favorite.get_attribute('aria-pressed'), 'false')
        self.assertEqual(self.visible_location_ids(), [])
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('gilneas-atlas-favorites-v1'))"), [])
        self.assert_clean()
    def test_06_camera_controls_center_markers_between_panels(self):
        self.boot()
        home_scale = self.camera()['scale']
        marker = self.page.locator('.map-marker[data-location-id="gilneas-city"]')
        initial_box = marker.bounding_box()
        self.page.locator('#zoom-in').click()
        self.page.wait_for_timeout(600)
        self.assertGreater(self.camera()['scale'], home_scale)
        self.assertAlmostEqual(marker.bounding_box()['width'], initial_box['width'], delta=0.1)
        self.page.locator('#map-fit').click()
        self.page.wait_for_timeout(600)
        fit_camera = self.camera()
        self.assertLess(fit_camera['scale'], home_scale)
        viewport_box = self.page.locator('#viewport').bounding_box()
        world_box = self.page.locator('#world').bounding_box()
        self.assertGreaterEqual(world_box['x'], viewport_box['x'] - 0.1)
        self.assertGreaterEqual(world_box['y'], viewport_box['y'] - 0.1)
        self.assertLessEqual(world_box['x'] + world_box['width'], viewport_box['x'] + viewport_box['width'] + 0.1)
        self.assertLessEqual(world_box['y'] + world_box['height'], viewport_box['y'] + viewport_box['height'] + 0.1)
        self.page.locator('#map-home').click()
        self.page.wait_for_timeout(600)
        self.assertAlmostEqual(self.camera()['scale'], home_scale, delta=0.001)
        self.page.locator('button.location-row[data-location-id="gilneas-city"]').click()
        self.page.wait_for_timeout(600)
        self.assertIn('selected', marker.get_attribute('class'))
        self.assertIn('active', self.page.locator('button.location-row[data-location-id="gilneas-city"]').get_attribute('class'))
        box = marker.bounding_box()
        center = [box['x'] + box['width'] / 2, box['y'] + box['height'] / 2]
        nav = self.page.locator('#navigation').bounding_box()
        dossier = self.page.locator('#dossier').bounding_box()
        expected_x = (nav['x'] + nav['width'] + dossier['x']) / 2
        self.assertAlmostEqual(center[0], expected_x, delta=1)
        point = self.page.evaluate('(p) => window.ui.toMap(...p)', center)
        self.assertAlmostEqual(point[0], 1800, delta=0.01)
        self.assertAlmostEqual(point[1], 3400, delta=0.01)
        self.page.evaluate("window.ui.setPanel('navigation', false); window.ui.focusLocation('gilneas-city', false)")
        box_without_nav = marker.bounding_box()
        self.assertLess(box_without_nav['x'], box['x'])
        self.page.evaluate('const copied = window.ui.getCamera(); copied.x = 100000; copied.scale = 999')
        self.assertLess(self.camera()['scale'], 5)
        self.page.locator('#dossier-focus').click()
        self.page.wait_for_timeout(600)
        zoomed = self.camera()['scale']
        self.page.locator('#zoom-out').click()
        self.page.wait_for_timeout(600)
        self.assertLess(self.camera()['scale'], zoomed)
        self.assert_clean()
    def test_07_real_wheel_anchor_drag_and_native_map_guards(self):
        self.boot()
        self.page.evaluate("window.ui.setPanel('navigation', false); window.ui.setPanel('layers', false); window.ui.home(false)")
        point = [620, 470]
        before_point = self.page.evaluate('(p) => window.ui.toMap(...p)', point)
        before = self.camera()
        marker = self.page.locator('.map-marker[data-location-id="gilneas-city"]')
        before_width = marker.bounding_box()['width']
        self.page.mouse.move(*point)
        self.page.mouse.wheel(0, -240)
        self.page.wait_for_timeout(80)
        self.assertGreater(self.camera()['scale'], before['scale'])
        after_point = self.page.evaluate('(p) => window.ui.toMap(...p)', point)
        self.assertAlmostEqual(before_point[0], after_point[0], delta=0.01)
        self.assertAlmostEqual(before_point[1], after_point[1], delta=0.01)
        self.assertAlmostEqual(marker.bounding_box()['width'], before_width, delta=0.1)
        before_drag = self.camera()
        self.page.mouse.move(600, 500)
        self.page.mouse.down()
        self.page.mouse.move(690, 545, steps=8)
        self.assertIn('dragging', self.page.locator('#viewport').get_attribute('class'))
        self.page.mouse.up()
        self.assertNotIn('dragging', self.page.locator('#viewport').get_attribute('class'))
        after_drag = self.camera()
        self.assertAlmostEqual(after_drag['x'] - before_drag['x'], 90, delta=0.5)
        self.assertAlmostEqual(after_drag['y'] - before_drag['y'], 45, delta=0.5)
        self.page.mouse.click(800, 570)
        self.assertEqual(self.page.evaluate('window.calls'), [])
        self.assertEqual(self.page.locator('#viewport').evaluate('node => getComputedStyle(node).touchAction'), 'none')
        prevented = self.page.locator('#viewport').evaluate("""node => ['dragstart', 'selectstart'].map(type => {
            const event = new Event(type, {bubbles: true, cancelable: true});
            node.dispatchEvent(event); return event.defaultPrevented;
        })""")
        self.assertEqual(prevented, [True, True])
        self.assert_clean()
    def test_08_map_task_clicks_doubleclick_and_alt_meta_pan(self):
        self.boot()
        self.page.evaluate("""window.ui.setPanel('navigation', false); window.ui.setPanel('layers', false); window.ui.home(false);
            window.taskClicks = [];
            window.ui.setMapInteraction((point, event) => window.taskClicks.push({point, type: event.type, detail: event.detail}));""")
        point = [700, 450]
        expected = self.page.evaluate('(p) => window.ui.toMap(...p)', point)
        self.page.mouse.click(*point)
        click = self.page.evaluate('window.taskClicks.at(-1)')
        self.assertIsNotNone(click, 'active map task must receive click events')
        self.assertEqual(click['type'], 'click')
        self.assertAlmostEqual(click['point'][0], expected[0], delta=0.01)
        self.assertAlmostEqual(click['point'][1], expected[1], delta=0.01)
        before = self.camera()
        self.page.mouse.move(700, 450)
        self.page.mouse.down()
        self.page.mouse.move(800, 500, steps=5)
        self.page.mouse.up()
        self.assertEqual(self.camera(), before, 'task mode plain drag must not pan')
        self.assertEqual(self.page.evaluate('window.taskClicks.length'), 1)
        for key in ['Alt', 'Meta']:
            before = self.camera()
            self.page.keyboard.down(key)
            self.page.mouse.move(700, 450)
            self.page.mouse.down()
            self.page.mouse.move(750, 475, steps=5)
            self.page.mouse.up()
            self.page.keyboard.up(key)
            self.assertAlmostEqual(self.camera()['x'] - before['x'], 50, delta=0.5)
        self.assertEqual(self.page.evaluate('window.taskClicks.length'), 1)
        self.page.mouse.dblclick(800, 500)
        self.assertEqual(self.page.evaluate('window.taskClicks.at(-1).type'), 'dblclick')
        self.assertEqual(self.page.evaluate('window.taskClicks.at(-1).detail'), 2)
        self.assertEqual(self.page.evaluate('window.calls'), [])
        self.assertIn('map-editing', self.page.locator('body').get_attribute('class'))
        self.page.evaluate('window.ui.setMapInteraction(null)')
        self.assertNotIn('map-editing', self.page.locator('body').get_attribute('class'))
        count = self.page.evaluate('window.taskClicks.length')
        self.page.mouse.click(800, 500)
        self.assertEqual(self.page.evaluate('window.taskClicks.length'), count)
        marker = self.page.locator('.map-marker[data-location-id="gilneas-city"]')
        marker.click()
        self.assertEqual(self.page.evaluate('window.fixtureSelected'), 'gilneas-city')
        self.assert_clean()
    def test_09_trusted_two_finger_pinch_then_single_finger_pan(self):
        self.boot(size={'width': 390, 'height': 844})
        self.page.evaluate("window.ui.setPanel('navigation', false); window.ui.setPanel('layers', false); window.ui.home(false)")
        session = self.context.new_cdp_session(self.page)
        session.send('Emulation.setTouchEmulationEnabled', {'enabled': True, 'maxTouchPoints': 5})
        point = [195, 250]
        map_point = self.page.evaluate('(p) => window.ui.toMap(...p)', point)
        before = self.camera()
        marker = self.page.locator('.map-marker[data-location-id="gilneas-city"]')
        width = marker.bounding_box()['width']

        def touches(kind, positions, ids=None):
            session.send('Input.dispatchTouchEvent', {
                'type': kind,
                'touchPoints': [{'x': x, 'y': y, 'id': ids[i] if ids else i + 1, 'radiusX': 3, 'radiusY': 3, 'force': 1}
                                for i, (x, y) in enumerate(positions)],
            })
            self.page.wait_for_timeout(25)

        touches('touchStart', [(155, 250), (235, 250)])
        touches('touchMove', [(125, 250), (265, 250)])
        self.assertGreater(self.camera()['scale'], before['scale'] * 1.5)
        anchored = self.page.evaluate('(p) => window.ui.toMap(...p)', point)
        self.assertAlmostEqual(anchored[0], map_point[0], delta=0.2)
        self.assertAlmostEqual(anchored[1], map_point[1], delta=0.2)
        self.assertAlmostEqual(marker.bounding_box()['width'], width, delta=0.15)
        after_pinch = self.camera()
        # CDP touchEnd names the finger being lifted, not the remaining set.
        touches('touchEnd', [(265, 250)], ids=[2])
        self.assertEqual(self.camera(), after_pinch, 'lifting one pinch finger must not jump')
        touches('touchMove', [(145, 270)])
        self.assertAlmostEqual(self.camera()['x'] - after_pinch['x'], 20, delta=0.5)
        self.assertAlmostEqual(self.camera()['y'] - after_pinch['y'], 20, delta=0.5)
        touches('touchEnd', [])
        self.assertNotIn('dragging', self.page.locator('#viewport').get_attribute('class'))
        self.assertEqual(self.page.evaluate('window.calls'), [])
        session.detach()
        self.assert_clean()
    def test_10_cancellable_raf_flights_manual_input_never_snaps_back(self):
        self.boot()
        self.page.evaluate("window.ui.setPanel('navigation', false); window.ui.setPanel('layers', false); window.ui.home(false)")
        before, immediate = self.page.evaluate('(() => { const before = window.ui.getCamera(); window.ui.fit(true); return [before, window.ui.getCamera()]; })()')
        self.assertEqual(immediate, before, 'animated flight must not immediately teleport')
        self.page.wait_for_function('(scale) => window.ui.getCamera().scale < scale', arg=before['scale'], timeout=2500)
        during = self.camera()
        self.assertLess(during['scale'], before['scale'])
        self.page.mouse.move(700, 450)
        self.page.mouse.wheel(0, -60)
        self.page.wait_for_timeout(60)
        interrupted = self.camera()
        self.page.wait_for_timeout(650)
        self.assertEqual(self.camera(), interrupted, 'wheel must cancel the pending flyTo RAF')
        self.page.evaluate("window.ui.focusLocation('gilneas-city', true)")
        self.page.wait_for_timeout(80)
        self.page.mouse.move(600, 450)
        self.page.mouse.down()
        self.page.mouse.move(630, 460, steps=4)
        self.page.mouse.up()
        dragged = self.camera()
        self.page.wait_for_timeout(650)
        self.assertEqual(self.camera(), dragged, 'drag must cancel a flight without a later snap')
        self.page.evaluate('window.ui.home(true)')
        self.page.wait_for_timeout(70)
        self.page.evaluate('window.ui.fit(false)')
        fitted = self.camera()
        self.page.wait_for_timeout(650)
        self.assertEqual(self.camera(), fitted, 'new camera command must cancel old RAF')
        self.page.emulate_media(reduced_motion='reduce')
        self.page.evaluate('window.ui.home(true)')
        self.assertNotEqual(self.camera(), fitted, 'reduced motion uses the immediate final camera')
        self.assert_clean()
    def test_11_mobile_portrait_and_short_landscape_exclusive_panels(self):
        self.boot(size={'width': 390, 'height': 844})
        for selector in ['#navigation', '#layers', '#dossier']:
            self.assertTrue(self.page.locator(selector).is_hidden())
            self.assertEqual(self.page.locator(selector).get_attribute('aria-hidden'), 'true')
        self.assertTrue(self.page.locator('#mobile-dossier').is_disabled())
        self.page.locator('#mobile-nav').click()
        self.assertTrue(self.page.locator('#navigation').is_visible())
        self.assertIn('mobile-panel-navigation', self.page.locator('body').get_attribute('class'))
        self.assertEqual(self.page.locator('#mobile-nav').get_attribute('aria-pressed'), 'true')
        self.page.locator('#mobile-layers').click()
        self.assertTrue(self.page.locator('#navigation').is_hidden())
        self.assertTrue(self.page.locator('#layers').is_visible())
        self.assertEqual(self.page.locator('#layers').get_attribute('aria-hidden'), 'false')
        self.page.locator('#layers-close').click()
        self.assertTrue(self.page.locator('#layers').is_hidden())
        self.page.locator('#mobile-nav').click()
        self.page.locator('button.location-row[data-location-id="gilneas-city"]').click()
        self.page.wait_for_timeout(650)
        self.assertTrue(self.page.locator('#navigation').is_hidden())
        self.assertTrue(self.page.locator('#dossier').is_visible())
        self.assertIn('mobile-panel-dossier', self.page.locator('body').get_attribute('class'))
        self.assertFalse(self.page.locator('#mobile-dossier').is_disabled())
        marker = self.page.locator('.map-marker[data-location-id="gilneas-city"]').bounding_box()
        dossier = self.page.locator('#dossier').bounding_box()
        self.assertLess(marker['y'] + marker['height'], dossier['y'])
        self.page.locator('#mobile-dossier').click()
        self.assertTrue(self.page.locator('#dossier').is_hidden())
        self.page.locator('#mobile-nav').click()
        self.page.set_viewport_size({'width': 844, 'height': 390})
        self.page.wait_for_timeout(100)
        self.assertTrue(self.page.locator('#navigation').is_visible())
        self.assertTrue(self.page.locator('#layers').is_hidden())
        self.assertIn('mobile-panel-navigation', self.page.locator('body').get_attribute('class'))
        self.page.locator('#mobile-layers').click()
        self.assertTrue(self.page.locator('#layers').is_visible())
        self.assertTrue(self.page.locator('#navigation').is_hidden())
        self.assertAlmostEqual(self.page.locator('html').evaluate('node => parseFloat(node.style.getPropertyValue("--app-height"))'), 390, delta=1)
        self.page.set_viewport_size({'width': 1440, 'height': 1000})
        self.page.wait_for_timeout(100)
        self.assertTrue(self.page.locator('#navigation').is_visible())
        self.assertNotIn('mobile-panel-', self.page.locator('body').get_attribute('class'))
        self.page.locator('#nav-close').click()
        self.assertTrue(self.page.locator('#navigation').is_hidden())
        self.assertTrue(self.page.locator('#nav-open').is_visible())
        self.assertIn('nav-hidden', self.page.locator('body').get_attribute('class'))
        self.page.locator('#nav-open').click()
        self.assertTrue(self.page.locator('#navigation').is_visible())
        self.assertTrue(self.page.locator('#nav-open').is_hidden())
        self.assertAlmostEqual(self.page.locator('html').evaluate('node => parseFloat(node.style.getPropertyValue("--app-height"))'), 1000, delta=1)
        self.assert_clean()


    def test_12_keyboard_shortcuts_skip_inputs_and_open_dialogs(self):
        self.boot()
        self.page.locator('#viewport').focus()
        self.page.keyboard.press('n')
        self.assertTrue(self.page.locator('#navigation').is_hidden())
        self.page.locator('#viewport').dispatch_event('keydown', {'key': 'т', 'code': 'KeyN', 'bubbles': True})
        self.assertTrue(self.page.locator('#navigation').is_visible())
        self.page.keyboard.press('/')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'search')
        before = self.camera()
        self.page.keyboard.type('g+n0')
        self.assertEqual(self.camera(), before)
        self.page.locator('#search').fill('')
        self.page.locator('#viewport').focus()
        self.page.keyboard.press('0')
        self.page.wait_for_timeout(650)
        self.assertLess(self.camera()['scale'], before['scale'])
        self.page.locator('#viewport').dispatch_event('keydown', {'key': 'п', 'code': 'KeyG', 'bubbles': True})
        self.page.wait_for_timeout(650)
        self.assertAlmostEqual(self.camera()['scale'], before['scale'], delta=0.001)
        self.page.keyboard.press('+')
        self.assertGreater(self.camera()['scale'], before['scale'])
        self.page.keyboard.press('-')
        self.assertAlmostEqual(self.camera()['scale'], before['scale'], delta=0.001)
        self.page.evaluate("document.querySelector('#help').showModal(); document.querySelector('#help').focus()")
        before_dialog = self.camera()
        self.page.keyboard.press('n')
        self.page.keyboard.press('0')
        self.page.keyboard.press('/')
        self.assertTrue(self.page.locator('#navigation').is_visible())
        self.assertEqual(self.camera(), before_dialog)
        self.assertNotEqual(self.page.evaluate('document.activeElement.id'), 'search')
        self.page.evaluate("document.querySelector('#help').close()")
        self.page.locator('#viewport').focus()
        self.page.keyboard.press('g')
        self.page.wait_for_timeout(650)
        self.assert_clean()


    def test_13_parent_css_row_classes_and_real_screenshot_evidence(self):
        self.boot(storage=json.dumps(['gilneas-city']))
        row = self.page.locator('button.location-row[data-location-id="gilneas-city"]')
        self.assertEqual(row.locator('.row-name').count(), 1)
        self.assertEqual(row.locator('.row-capital svg').count(), 1)
        self.assertEqual(row.locator('.row-favorite').count(), 1)
        self.assertEqual(row.locator('.location-type').inner_text(), 'Город')
        badge = self.page.locator('.faction-row[data-faction-id="test-house"] .faction-parent')
        self.assertTrue(badge.is_visible(), 'the vassal parent label must be visible with parent CSS')
        framed = self.page.evaluate("""(() => {
            const camera = window.ui.getCamera(), viewport = document.querySelector('#viewport').getBoundingClientRect();
            const left = document.querySelector('#navigation').getBoundingClientRect().right + 20;
            const right = document.querySelector('#layers').getBoundingClientRect().left - 20;
            return 800 * camera.scale + camera.x + viewport.left >= left &&
                   2800 * camera.scale + camera.x + viewport.left <= right;
        })()""")
        self.assertTrue(framed, 'home must expose western Gilneas outside the left register')
        self.page.evaluate("import('./assets/js/icons.mjs').then(module => module.decorateIcons(document))")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(ARTIFACTS / 'desktop-home.png'))
        row.click()
        self.page.wait_for_timeout(650)
        self.page.screenshot(path=str(ARTIFACTS / 'desktop-dossier.png'))
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.wait_for_timeout(120)
        self.page.locator('#mobile-dossier').click()
        self.page.locator('#mobile-dossier').click()
        self.page.evaluate("window.ui.focusLocation('gilneas-city', false)")
        self.page.screenshot(path=str(ARTIFACTS / 'mobile-dossier.png'))
        self.page.set_viewport_size({'width': 844, 'height': 390})
        self.page.wait_for_timeout(120)
        self.page.screenshot(path=str(ARTIFACTS / 'landscape-dossier.png'))
        self.assert_clean()


if __name__ == '__main__':
    unittest.main()
