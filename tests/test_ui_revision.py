"""UI revision tracer bullets; real DOM/CSS, only app bootstrap is isolated.

Fixtures are test-only and never saved to the atlas. Run with:
/Users/daniil_si/.hermes/cache/scratch/gilneas-venv/bin/python tests/test_ui_revision.py -v
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
ARTIFACTS = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-ui-revision-evidence')
ATLAS = json.loads((ROOT / 'assets/data/atlas.json').read_text())
FIXTURE = {
    'version': 1,
    'meta': {'width': 3247, 'height': 4860,
             'image': 'assets/maps/gilneas-enhanced.webp',
             'mist': 'assets/maps/inactive-mist.webp', 'labels': []},
    'factions': [
        {'id': 'gilneas', 'name': 'Тестовое королевство Гилнеас', 'color': '#a74657', 'parent': None},
        {'id': 'test-house', 'name': 'Тестовый старший дом', 'color': '#639096', 'parent': 'gilneas'},
        {'id': 'test-vassal', 'name': 'Тестовый младший дом', 'color': '#93a798', 'parent': 'test-house'},
        {'id': 'test-other', 'name': 'Тестовая иная держава', 'color': '#aa85c4', 'parent': None},
        {'id': 'test-empty', 'name': 'Тестовый пустой дом', 'color': '#7592b2', 'parent': 'gilneas'},
    ],
    'locations': [
        {'id': 'test-crown-place', 'name': 'Тестовая столица', 'type': 'city', 'faction': 'gilneas',
         'x': 1800, 'y': 3400, 'capital': True, 'owner': '',
         'description': 'Тестовое первое предложение. Тестовое второе предложение.', 'objects': []},
        {'id': 'test-house-place', 'name': 'Тестовое поместье', 'type': 'estate', 'faction': 'test-house',
         'x': 1950, 'y': 3200, 'owner': 'Тестовый владелец',
         'description': 'Тестовая земля.', 'provenance': {'confidence': 'reconstruction'}, 'objects': []},
        {'id': 'test-vassal-place', 'name': 'Тестовый младший удел', 'type': 'fortress', 'faction': 'test-vassal',
         'x': 1550, 'y': 3600, 'owner': '', 'description': 'Тестовый удел.', 'objects': []},
        {'id': 'test-other-place', 'name': 'Тестовый другой город', 'type': 'city', 'faction': 'test-other',
         'x': 2300, 'y': 2200, 'owner': '', 'description': '', 'objects': []},
    ],
    'territories': [{'id': 'test-territory', 'faction': 'test-house',
                     'points': [[1700, 3000], [2100, 3000], [2100, 3300], [1700, 3300]]}],
    'nobles': [{'id': 'test-noble', 'name': 'Тестовый дворянин', 'title': 'Тестовый титул', 'house': 'test-house'}],
    'sources': [],
}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class UIRevisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
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
        self.page.set_default_timeout(3000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
            status=200, content_type='application/javascript', body='// Test-only bootstrap seam.'))

    def tearDown(self):
        self.context.close()

    def boot(self, fixture=None, remove_reconstruction_control=False, delegate_territories=False):
        self.page.goto(self.url + '/index.html', wait_until='networkidle')
        self.page.evaluate("""async options => {
            if (options.removeControl) {
                const control = document.querySelector('#show-reconstructions');
                (control?.closest('label') || control)?.remove();
            }
            window.fixtureData = options.data;
            window.fixtureSelected = null;
            window.calls = [];
            window.territoryCalls = [];
            const context = {
                getData: () => window.fixtureData,
                getSelectedId: () => window.fixtureSelected,
                onSelect: id => { window.fixtureSelected = id; window.calls.push(['select', id]); window.ui.render(); },
                onShowNoble: id => window.calls.push(['noble', id]),
                onEditLocation: id => window.calls.push(['edit', id]),
                onAddObject: id => window.calls.push(['add', id]),
                onEditObject: (id, objectId) => window.calls.push(['edit-object', id, objectId]),
                onDeleteObject: (id, objectId) => window.calls.push(['delete-object', id, objectId]),
            };
            if (options.delegateTerritories) {
                const sentinel = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                sentinel.dataset.boundarySentinel = 'parent';
                document.querySelector('#territory-layer').append(sentinel);
                context.onRenderTerritories = state => window.territoryCalls.push(state);
            }
            const { initUI } = await import('./assets/js/ui.mjs');
            window.ui = initUI(context);
        }""", {'data': copy.deepcopy(fixture if fixture is not None else FIXTURE),
                 'removeControl': remove_reconstruction_control, 'delegateTerritories': delegate_territories})
        self.page.wait_for_function("document.querySelector('#base-map').complete && document.querySelector('#base-map').naturalWidth > 0", polling=50)
        self.page.mouse.move(2, 2)

    def select(self, location_id):
        self.page.evaluate("id => { window.fixtureSelected = id; window.ui.render(); window.ui.focusLocation(id, false); }", location_id)

    def center_marker(self, location_id):
        self.page.evaluate("id => { window.ui.setPanel('navigation', false); window.ui.setPanel('layers', false); window.ui.setPanel('dossier', false); window.ui.focusLocation(id, false); }", location_id)
        return self.page.locator(f'.map-marker[data-location-id="{location_id}"]')

    def location_ids(self):
        return self.page.locator('#location-list .location-row').evaluate_all('(rows) => rows.map(row => row.dataset.locationId)')

    def assert_clean(self):
        self.assertEqual(self.errors, [])

    def test_01_native_hover_is_literal_safe_and_shows_immediate_faction_and_sovereign(self):
        fixture = copy.deepcopy(FIXTURE)
        unsafe = '<img src=x onerror="window.uiXss=1"> & <script>window.uiXss=2</script>'
        location = fixture['locations'][2]
        location['name'] = unsafe
        location['shortDescription'] = 'Тестовая краткая строка ' + unsafe
        self.boot(fixture)
        marker = self.center_marker(location['id'])
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        marker.hover()
        tooltip = self.page.locator('#marker-tooltip')
        self.assertEqual(tooltip.count(), 1, 'native hover must create/use the viewport tooltip')
        self.assertTrue(tooltip.is_visible())
        self.assertEqual(tooltip.get_attribute('role'), 'tooltip')
        self.assertEqual(tooltip.locator('.tooltip-title').text_content(), unsafe)
        self.assertEqual(tooltip.locator('.tooltip-description').text_content(), location['shortDescription'])
        self.assertIn('Тестовый младший дом', tooltip.locator('.tooltip-faction').text_content())
        self.assertEqual(tooltip.locator('.tooltip-sovereign').count(), 1, 'sovereign needs its own styled tooltip line')
        self.assertIn('Тестовое королевство Гилнеас', tooltip.locator('.tooltip-sovereign').text_content())
        self.assertEqual(tooltip.evaluate('node => node.style.getPropertyValue("--tooltip-color")'), '#93a798')
        self.assertIsNone(marker.get_attribute('title'), 'native title must not compete with the custom tooltip')
        self.assertEqual(marker.get_attribute('aria-describedby'), 'marker-tooltip')
        self.assertEqual(tooltip.locator('img,script').count(), 0)
        self.assertIsNone(self.page.evaluate('window.uiXss'))
        self.assertEqual(tooltip.evaluate("node => node.parentElement.id"), 'viewport')
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before)
        self.assert_clean()

    def test_02_native_focus_and_leave_manage_the_shared_tooltip(self):
        self.boot()
        marker = self.center_marker('test-crown-place')
        tooltip = self.page.locator('#marker-tooltip')
        marker.focus()
        self.assertTrue(tooltip.is_visible(), 'keyboard focus must show the same tooltip as hover')
        self.assertEqual(tooltip.locator('.tooltip-description').text_content(), 'Тестовое первое предложение.')
        self.page.locator('#viewport').focus()
        self.assertTrue(tooltip.is_hidden(), 'blur must clear the tooltip')
        self.assertIsNone(marker.get_attribute('aria-describedby'))
        marker.hover()
        self.assertTrue(tooltip.is_visible())
        self.page.mouse.move(2, 2)
        self.assertTrue(tooltip.is_hidden(), 'mouseleave must not leave a stale tooltip')
        self.assertIsNone(marker.get_attribute('aria-describedby'))
        marker.hover()
        self.assertEqual(tooltip.count(), 1, 'reuse one viewport tooltip')
        self.assert_clean()

    def test_03_camera_selection_and_editing_hide_stale_tooltips(self):
        self.boot()
        marker = self.center_marker('test-crown-place')
        tooltip = self.page.locator('#marker-tooltip')
        marker.hover()
        self.assertTrue(tooltip.is_visible())
        self.page.mouse.wheel(0, -80)
        self.page.wait_for_timeout(50)
        self.assertTrue(tooltip.is_hidden(), 'native wheel must hide the old screen-space tooltip')
        marker = self.center_marker('test-crown-place')
        marker.hover()
        self.page.mouse.down()
        self.assertTrue(tooltip.is_hidden(), 'pan initiation must clear the tooltip')
        self.page.mouse.move(800, 500, steps=4)
        self.page.mouse.up()
        marker = self.center_marker('test-crown-place')
        marker.focus()
        self.page.evaluate('window.ui.setMapInteraction(() => {})')
        self.assertTrue(tooltip.is_hidden(), 'editing mode must hide the tooltip')
        marker.focus()
        self.assertTrue(tooltip.is_hidden(), 'editing must not reopen hover/focus tooltips')
        self.page.evaluate('window.ui.setMapInteraction(null)')
        self.page.locator('#viewport').focus()
        marker.focus()
        self.page.evaluate('window.ui.render()')
        self.assertTrue(tooltip.is_hidden(), 'data rerenders must clear removed marker references')
        marker = self.center_marker('test-crown-place')
        marker.focus()
        self.page.keyboard.press('Enter')
        self.assertEqual(self.page.evaluate('window.fixtureSelected'), 'test-crown-place')
        self.assertTrue(tooltip.is_hidden(), 'selecting a location must not leave a tooltip over its dossier')
        self.assert_clean()

    def test_04_hover_tooltip_is_clamped_in_unscaled_viewport_coordinates(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['name'] = 'Тестовая_' + 'длинная_метка_' * 35
        fixture['locations'][0]['shortDescription'] = 'Тестовое описание. ' * 35
        self.boot(fixture)
        marker = self.center_marker('test-crown-place')
        tooltip = self.page.locator('#marker-tooltip')
        for width, height in [(1440, 1000), (390, 844)]:
            self.page.set_viewport_size({'width': width, 'height': height})
            self.page.wait_for_function('height => parseFloat(document.documentElement.style.getPropertyValue("--app-height")) === height', arg=height, polling=25)
            self.center_marker('test-crown-place')
            viewport = self.page.locator('#viewport').bounding_box()
            for x, y in [(24, viewport['height'] / 2), (width - 24, viewport['height'] / 2), (width / 2, viewport['height'] - 110)]:
                point = [viewport['x'] + x, viewport['y'] + y]
                self.page.evaluate("point => { const p = window.ui.toMap(...point); const l = window.fixtureData.locations[0]; l.x = p[0]; l.y = p[1]; window.ui.render(); }", point)
                marker.hover()
                box = tooltip.bounding_box()
                self.assertGreaterEqual(box['x'], viewport['x'] + 7, 'left edge must be clamped')
                self.assertGreaterEqual(box['y'], viewport['y'] + 7, 'top edge must be clamped')
                self.assertLessEqual(box['x'] + box['width'], viewport['x'] + viewport['width'] - 7, 'right edge must be clamped')
                self.assertLessEqual(box['y'] + box['height'], viewport['y'] + viewport['height'] - 7, 'bottom edge must be clamped')
                self.assertEqual(tooltip.evaluate('node => getComputedStyle(node).position'), 'absolute')
                self.assertEqual(tooltip.evaluate('node => getComputedStyle(node).pointerEvents'), 'none')
                self.assertEqual(tooltip.evaluate('node => getComputedStyle(node).transform'), 'none')
                self.page.mouse.move(2, 2)
        self.assert_clean()

    def test_05_tooltip_distinguishes_unknown_affiliation_from_explicit_independence(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['faction'] = None
        fixture['locations'][0]['provenance'] = {'confidence': 'reconstruction', 'affiliationStatus': 'unknown'}
        fixture['locations'][1]['faction'] = None
        fixture['locations'][1]['provenance'] = {'confidence': 'reconstruction', 'affiliationStatus': 'independent'}
        self.boot(fixture)
        self.center_marker('test-crown-place').hover()
        self.assertIn('Принадлежность не установлена', self.page.locator('.tooltip-faction').text_content())
        self.assertIn('Подданство: Не установлено', self.page.locator('.tooltip-sovereign').text_content())
        self.center_marker('test-house-place').hover()
        self.assertIn('Независимое владение', self.page.locator('.tooltip-sovereign').text_content())
        self.assertNotIn('не установлена', self.page.locator('.tooltip-faction').text_content())
        self.assert_clean()

    def test_06_dossier_uses_immediate_faction_color_and_keeps_full_owner_text(self):
        fixture = copy.deepcopy(FIXTURE)
        owner = 'Тестовый полный владелец с очень длинным именем, титулом и наследственным домом'
        fixture['locations'][2]['owner'] = owner
        self.boot(fixture)
        self.select('test-vassal-place')
        self.assertEqual(self.page.locator('#dossier').evaluate('node => node.style.getPropertyValue("--dossier-faction-color")'), '#93a798')
        self.assertEqual(self.page.locator('#dossier-faction').evaluate('node => node.style.color'), 'var(--dossier-faction-color)')
        self.assertEqual(self.page.locator('#dossier-faction').text_content(), 'Тестовый младший дом')
        self.assertEqual(self.page.locator('#dossier-sovereign').text_content(), 'Тестовое королевство Гилнеас')
        self.assertEqual(self.page.locator('#dossier-owner').text_content(), owner)
        self.select('test-other-place')
        self.assertEqual(self.page.locator('#dossier').evaluate('node => node.style.getPropertyValue("--dossier-faction-color")'), '#aa85c4')
        self.assertEqual(self.page.locator('#dossier-owner').text_content(), 'Не установлен')
        self.assert_clean()

    def test_07_collapsed_object_badges_use_effective_affiliation_and_keep_modifier_semantics(self):
        fixture = copy.deepcopy(FIXTURE)
        owner = 'Тестовый полный хозяин объекта, наследственный хранитель и глава длинного имени'
        fixture['locations'][1]['objects'] = [
            {'id': 'test-inherited-object', 'type': 'building', 'name': 'Тестовый наследуемый объект', 'owner': owner,
             'modifiers': [{'id': 'test-bonus', 'kind': 'bonus', 'text': '+2 тестовых единицы'},
                           {'id': 'test-penalty', 'kind': 'penalty', 'text': '−1 тестовая единица'}]},
            {'id': 'test-neutral-object', 'type': 'resource', 'name': 'Тестовый независимый объект', 'faction': None, 'modifiers': []},
            {'id': 'test-own-object', 'type': 'landmark', 'name': 'Тестовый чужой объект', 'faction': 'test-other', 'modifiers': []},
        ]
        self.boot(fixture)
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        self.select('test-house-place')
        for object_id, color, label in [('test-inherited-object', '#639096', 'Тестовый старший дом'),
                                        ('test-neutral-object', '#b39467', 'Независимый объект'),
                                        ('test-own-object', '#aa85c4', 'Тестовая иная держава')]:
            card = self.page.locator(f'.object-card[data-object-id="{object_id}"]')
            self.assertFalse(card.evaluate('node => node.open'))
            badge = card.locator('summary .object-faction-badge')
            self.assertEqual(badge.count(), 1, 'affiliation belongs INSIDE the collapsed summary')
            self.assertTrue(badge.is_visible())
            self.assertEqual(badge.text_content(), label)
            self.assertEqual(card.evaluate('node => node.style.getPropertyValue("--object-color")'), color)
            self.assertEqual(badge.evaluate('node => node.style.color'), 'var(--object-color)')
        inherited = self.page.locator('.object-card[data-object-id="test-inherited-object"]')
        inherited.locator('summary').click()
        self.assertIn(owner, inherited.locator('.object-ownership').text_content())
        self.assertEqual(inherited.locator('.modifier.bonus').text_content(), '+2 тестовых единицы')
        self.assertEqual(inherited.locator('.modifier.penalty').text_content(), '−1 тестовая единица')
        self.assertNotEqual(inherited.locator('.modifier.bonus').evaluate('node => getComputedStyle(node).color'),
                            inherited.locator('.modifier.penalty').evaluate('node => getComputedStyle(node).color'))
        inherited.locator('[data-object-edit]').click()
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['edit-object', 'test-house-place', 'test-inherited-object'])
        inherited.locator('[data-object-delete]').click()
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['delete-object', 'test-house-place', 'test-inherited-object'])
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before)
        self.assert_clean()

    def test_08_dossier_hides_bookkeeping_but_preserves_citations_and_direct_wowpedia(self):
        fixture = copy.deepcopy(FIXTURE)
        note = 'Тестовая редакторская инструкция: не назначать владельцев и не добавлять догадки.'
        fixture['sources'] = [{'id': 'test-source', 'title': 'Тестовый источник', 'url': 'https://example.org/test-source'},
                              {'id': 'test-unsafe-source', 'title': '<img src=x onerror="window.uiXss=1">', 'url': 'javascript:window.uiXss=1'}]
        location = fixture['locations'][0]
        location['provenance'] = {'confidence': 'reconstruction', 'note': note, 'sources': ['test-source', 'test-unsafe-source']}
        location['wowpediaUrl'] = 'https://wowpedia.fandom.com/wiki/Test_location'
        self.boot(fixture)
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        self.select('test-crown-place')
        provenance = self.page.locator('#dossier-provenance')
        self.assertEqual(provenance.locator('.confidence').count(), 0, 'no visible confirmed/reconstruction/custom bookkeeping')
        self.assertNotIn(note, self.page.locator('#dossier').text_content())
        citation = provenance.locator('.source-citation[data-source-id="test-source"]')
        self.assertEqual(citation.get_attribute('href'), 'https://example.org/test-source')
        self.assertEqual(citation.get_attribute('rel'), 'noopener noreferrer')
        wowpedia = provenance.locator('.wowpedia-link')
        self.assertEqual(wowpedia.count(), 1)
        self.assertEqual(wowpedia.get_attribute('href'), location['wowpediaUrl'])
        self.assertEqual(wowpedia.get_attribute('target'), '_blank')
        self.assertEqual(wowpedia.get_attribute('rel'), 'noopener noreferrer')
        self.assertNotIn('source-citation', wowpedia.get_attribute('class'))
        self.assertIsNone(wowpedia.get_attribute('data-source-id'))
        self.assertEqual(self.page.locator('#dossier-owner').text_content(), 'Не установлен')
        self.assertEqual(provenance.locator('a[href^="javascript:"]').count(), 0)
        self.assertIsNone(self.page.evaluate('window.uiXss'))
        self.page.evaluate("window.fixtureData.locations[0].wowpediaUrl = 'javascript:window.uiXss=2'; window.ui.renderDossier()")
        self.assertEqual(provenance.locator('.wowpedia-link').count(), 0, 'reject non-HTTP direct links')
        self.page.evaluate("window.fixtureData.locations[0].wowpediaUrl = 'https://wowpedia.fandom.com/wiki/Test_location'")
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before, 'rendering never rewrites provenance')
        self.assert_clean()

    def test_09_reconstruction_checkbox_is_optional_and_never_filters_or_dashes_markers(self):
        self.boot()
        self.page.evaluate("const control = document.querySelector('#show-reconstructions'); if (control) { control.checked = false; control.dispatchEvent(new Event('change', { bubbles: true })); }")
        marker = self.center_marker('test-house-place')
        self.assertFalse(marker.evaluate('node => node.hidden'), 'reconstruction is not a visibility category')
        self.assertNotIn('reconstruction', marker.get_attribute('class'))
        self.assertEqual(marker.evaluate('node => getComputedStyle(node, ":before").borderTopStyle'), 'solid')
        self.boot(remove_reconstruction_control=True)
        self.assertEqual(self.page.locator('.map-marker').count(), len(FIXTURE['locations']))
        self.page.evaluate('window.ui.render()')
        self.assertEqual(self.page.locator('.map-marker.reconstruction').count(), 0)
        self.assert_clean()

    def test_10_dossier_independence_is_explicit_and_does_not_reuse_unknown_labels(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['faction'] = None
        fixture['locations'][0]['provenance'] = {'confidence': 'reconstruction', 'affiliationStatus': 'unknown'}
        fixture['locations'][1]['faction'] = None
        fixture['locations'][1]['provenance'] = {'confidence': 'reconstruction', 'affiliationStatus': 'independent'}
        self.boot(fixture)
        self.select('test-crown-place')
        self.assertEqual(self.page.locator('#dossier-faction').text_content(), 'Принадлежность не установлена')
        self.select('test-house-place')
        self.assertEqual(self.page.locator('#dossier-faction').text_content(), 'Без державы')
        self.assertEqual(self.page.locator('#dossier-sovereign').text_content(), 'Независимое владение')
        self.assertEqual(self.page.locator('#dossier').evaluate('node => node.style.getPropertyValue("--dossier-faction-color")'), '#b39467')
        self.assert_clean()

    def test_11_gilneas_subject_dossiers_use_faction_shields_with_the_supplied_device(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['meta']['gilneasHeraldry'] = {'symbol':'assets/ui/gilneas-royal-symbol.png','field':'#131516','edge':'#65707b','device':'#9aa8b6'}
        self.boot(fixture)
        self.select('test-vassal-place')
        shield = self.page.locator('#dossier-seal .faction-shield')
        self.assertEqual(shield.count(), 1, 'dossier uses the simple shield, not a full banner image')
        faction = next(row for row in fixture['factions'] if row['id']==fixture['locations'][2]['faction'])
        self.assertEqual(shield.locator('.shield-field').get_attribute('fill'), faction['color'])
        self.assertEqual(shield.locator('.shield-device').get_attribute('href'), fixture['meta']['gilneasHeraldry']['symbol'])
        self.assertEqual(self.page.locator('#dossier-seal img').count(), 0)
        self.select('test-other-place')
        self.assertEqual(self.page.locator('#dossier-seal .faction-shield').count(), 1)
        self.assertEqual(self.page.locator('#dossier-seal .shield-device').count(), 0)
        self.assert_clean()

    def test_12_real_atlas_navigation_is_nested_and_every_canonical_location_occurs_once(self):
        self.boot(ATLAS)
        source_ids = sorted(location['id'] for location in ATLAS['locations'])
        self.assertEqual(len(source_ids), 39)
        self.assertEqual(sorted(self.location_ids()), source_ids)
        self.assertEqual(len(set(self.location_ids())), len(source_ids))
        hierarchy = self.page.evaluate("""() => {
            const root = document.querySelector('#location-list details.faction-tree[data-faction-id="gilneas"]');
            const house = root?.querySelector('.faction-children > details.faction-tree[data-faction-id="crowley"]');
            const junior = house?.querySelector('.faction-children > details.faction-tree[data-faction-id="silverlaine"]');
            return { root: !!root, house: !!house, junior: !!junior,
                rootCount: root?.querySelector(':scope > summary .group-count')?.textContent,
                houseCount: house?.querySelector(':scope > summary .group-count')?.textContent,
                juniorCount: junior?.querySelector(':scope > summary .group-count')?.textContent };
        }""")
        self.assertTrue(hierarchy['root'], 'kingdom is a real recursive group')
        self.assertTrue(hierarchy['house'], 'Crowley must be a child of Gilneas, not a sibling')
        self.assertTrue(hierarchy['junior'], 'Silverlaine must be a child of Crowley, not a sibling')
        factions = {faction['id']: faction for faction in ATLAS['factions']}
        def within(faction_id, parent):
            while faction_id is not None:
                if faction_id == parent:
                    return True
                faction_id = factions[faction_id].get('parent')
            return False
        for group, faction_id in [('rootCount', 'gilneas'), ('houseCount', 'crowley'), ('juniorCount', 'silverlaine')]:
            self.assertEqual(hierarchy[group], str(sum(within(location.get('faction'), faction_id) for location in ATLAS['locations'])))
        self.assertEqual(self.page.locator('.registry-category[data-category-id="objects"]').count(), 0, 'exclude empty categories')
        self.assertEqual(self.page.locator('#location-list details.faction-tree[data-faction-id="walden"]').count(), 0, 'exclude empty groups')
        self.assert_clean()

    def test_13_explicit_object_affiliations_get_separate_rows_counts_and_canonical_selection(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['objects'] = [
            {'id': 'test-inherited', 'name': 'Тестовый наследуемый объект', 'type': 'building', 'modifiers': []},
            {'id': 'test-house-object', 'name': 'Тестовый объект старшего дома', 'type': 'building', 'faction': 'test-house', 'modifiers': []},
            {'id': 'test-vassal-object', 'name': 'Тестовый объект младшего дома', 'type': 'landmark', 'faction': 'test-vassal', 'modifiers': []},
            {'id': 'test-independent-object', 'name': 'Тестовый независимый запас', 'type': 'resource', 'faction': None, 'modifiers': []},
        ]
        self.boot(fixture)
        self.assertEqual(self.page.locator('#location-list .object-row').count(), 3, 'index explicit object affiliation only, including null')
        self.assertEqual(sorted(self.location_ids()), sorted(location['id'] for location in fixture['locations']))
        root = self.page.locator('details.faction-tree[data-faction-id="gilneas"]')
        self.assertEqual(root.locator(':scope > summary .group-count').text_content(), '3', 'object rows do not inflate location totals')
        self.assertEqual(root.locator(':scope > summary .group-object-count').text_content(), '2')
        junior = self.page.locator('details.faction-tree[data-faction-id="test-vassal"]')
        self.assertEqual(junior.locator(':scope > summary .group-count').text_content(), '1')
        self.assertEqual(junior.locator(':scope > .registry-category[data-category-id="objects"] .category-count').text_content(), '1')
        self.assertEqual(self.page.locator('.object-row[data-object-id="test-inherited"]').count(), 0)
        independent = self.page.locator('.object-row[data-object-id="test-independent-object"]')
        self.assertEqual(independent.get_attribute('data-location-id'), 'test-crown-place')
        self.assertIn('Тестовая столица', independent.locator('small').text_content())
        self.assertEqual(independent.evaluate('node => node.closest(".faction-tree").dataset.affiliation'), 'independent')
        row = self.page.locator('.object-row[data-object-id="test-vassal-object"]')
        row.click()
        self.assertEqual(self.page.evaluate('window.fixtureSelected'), 'test-crown-place')
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['select', 'test-crown-place'])
        self.assertTrue(self.page.locator('.object-card[data-object-id="test-vassal-object"]').evaluate('node => node.open'))
        self.assertIn('active', self.page.locator('.location-row[data-location-id="test-crown-place"]').get_attribute('class'))
        self.page.evaluate("window.ui.setPanel('dossier', false); window.ui.setPanel('layers', true)")
        self.page.locator('.faction-row[data-faction-id="test-house"]').click()
        self.assertEqual(sorted(self.location_ids()), ['test-house-place', 'test-vassal-place'])
        self.assertEqual(sorted(self.page.locator('#location-list .object-row').evaluate_all('(rows) => rows.map(row => row.dataset.objectId)')), ['test-house-object', 'test-vassal-object'])
        self.assert_clean()

    def test_14_search_autoexpands_ancestors_without_overwriting_normal_group_and_category_state(self):
        self.boot()
        category = self.page.locator('.faction-tree[data-faction-id="test-vassal"] > .registry-category[data-category-id="locations"]')
        category.locator('summary').click()
        self.assertFalse(category.evaluate('node => node.open'))
        self.page.evaluate('window.ui.render()')
        self.assertFalse(category.evaluate('node => node.open'), 'ordinary category collapse must survive rerender')
        root = self.page.locator('.faction-tree[data-faction-id="gilneas"]')
        root.locator(':scope > summary').click()
        self.page.locator('#search').fill('младший удел')
        self.assertEqual(self.location_ids(), ['test-vassal-place'])
        self.assertEqual(self.page.locator('#location-list .faction-tree[open]').count(), 3)
        self.assertTrue(category.evaluate('node => node.open'))
        self.page.evaluate('window.ui.render(); document.querySelector("#search").value = ""; document.querySelector("#search").dispatchEvent(new Event("input"))')
        self.assertFalse(root.evaluate('node => node.open'), 'search autoexpand must not overwrite ordinary kingdom collapse')
        self.assertFalse(category.evaluate('node => node.open'), 'search autoexpand must not overwrite ordinary category collapse')
        root.locator(':scope > summary').click()
        self.page.locator('#fold-groups').click()
        self.assertEqual(self.page.locator('#location-list details[open]').count(), 0)
        self.page.locator('#search').fill('младший удел')
        self.assertGreater(self.page.locator('#location-list details[open]').count(), 0)
        self.page.locator('#search').fill('')
        self.assertEqual(self.page.locator('#location-list details[open]').count(), 0)
        self.page.locator('#fold-groups').click()
        self.assertEqual(self.page.locator('#location-list details:not([open])').count(), 0)
        self.assert_clean()

    def test_15_noble_rows_resolve_house_names_and_keep_the_parent_noble_callback(self):
        self.boot()
        self.page.locator('#filter-nobles').click()
        row = self.page.locator('.noble-row[data-noble-id="test-noble"]')
        self.assertIn('Тестовый старший дом', row.locator('small').text_content())
        self.assertNotIn('test-house', row.text_content())
        self.page.locator('#search').fill('старший дом')
        self.assertEqual(self.page.locator('.noble-row').count(), 1, 'search matches the resolved house name')
        row.click()
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['noble', 'test-noble'])
        self.assertIsNone(self.page.evaluate('window.fixtureSelected'), 'opening noble remains the parent callback, not location selection')
        self.assert_clean()

    def test_16_unknown_navigation_is_not_mislabeled_as_independent(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['faction'] = None
        fixture['locations'][0]['provenance'] = {'affiliationStatus': 'unknown'}
        fixture['locations'][1]['faction'] = None
        fixture['locations'][1]['provenance'] = {'affiliationStatus': 'independent'}
        self.boot(fixture)
        unknown = self.page.locator('.faction-tree[data-affiliation="unknown"]')
        self.assertEqual(unknown.count(), 1, 'unknown locations need an honest unknown group')
        self.assertEqual(unknown.locator(':scope > summary .group-name').text_content(), 'Принадлежность не установлена')
        self.assertEqual(unknown.locator('.location-row').get_attribute('data-location-id'), 'test-crown-place')
        independent = self.page.locator('.faction-tree[data-affiliation="independent"]')
        self.assertEqual(independent.locator('.location-row').get_attribute('data-location-id'), 'test-house-place')
        self.assertNotIn('не установлена', independent.locator(':scope > summary .group-name').text_content())
        self.assertEqual(sorted(self.location_ids()), sorted(location['id'] for location in fixture['locations']))
        self.assert_clean()

    def test_17_junior_vassal_header_prioritizes_its_ruler_without_changing_canonical_house(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['factions'][2]['ruler'] = 'Тестовый барон младшего дома'
        self.boot(fixture)
        summary = self.page.locator('.faction-tree[data-faction-id="test-vassal"] > summary')
        self.assertEqual(summary.locator('.group-name').text_content(), 'Тестовый барон младшего дома')
        self.assertEqual(summary.locator('.group-house-name').text_content(), 'Тестовый младший дом')
        self.assertEqual(self.page.locator('.faction-tree[data-faction-id="test-house"] > summary .group-name').text_content(), 'Тестовый старший дом')
        self.assertEqual(self.page.evaluate('window.fixtureData.factions[2].name'), 'Тестовый младший дом')
        self.page.locator('#search').fill('Тестовый барон младшего дома')
        self.assertEqual(self.location_ids(), ['test-vassal-place'])
        self.assertEqual(self.page.locator('.faction-tree').count(), 3, 'ruler search keeps the two real ancestors')
        self.assert_clean()

    def test_18_territory_callback_owns_the_layer_and_receives_visibility_and_descendant_filter(self):
        self.boot(delegate_territories=True)
        self.assertEqual(self.page.locator('#territory-layer [data-boundary-sentinel="parent"]').count(), 1, 'UI must not replace the parent-owned boundary layer')
        self.assertEqual(self.page.locator('#territory-layer polygon').count(), 0)
        state = self.page.evaluate('window.territoryCalls.at(-1)')
        self.assertEqual(state['visible'], True)
        self.assertIsNone(state['selectedFaction'])
        self.assertIsNone(state['includedFactions'])
        self.page.locator('.faction-row[data-faction-id="test-house"]').click()
        state = self.page.evaluate('window.territoryCalls.at(-1)')
        self.assertEqual(state['selectedFaction'], 'test-house')
        self.assertEqual(sorted(state['includedFactions']), ['test-house', 'test-vassal'])
        self.page.locator('label:has(#show-territories)').click()
        self.assertEqual(self.page.evaluate('window.territoryCalls.at(-1).visible'), False)
        self.assertEqual(self.page.locator('#territory-layer [data-boundary-sentinel="parent"]').count(), 1)
        self.boot()
        polygon = self.page.locator('#territory-layer polygon[data-territory-id="test-territory"]')
        self.assertEqual(polygon.count(), 1, 'legacy standalone fixtures keep polygon fallback')
        self.assertEqual(polygon.get_attribute('points'), '1700,3000 2100,3000 2100,3300 1700,3300')
        self.assertEqual(polygon.get_attribute('fill'), '#639096')
        self.page.locator('label:has(#show-territories)').click()
        self.assertTrue(self.page.locator('#territory-layer').evaluate('node => node.hasAttribute("hidden")'))
        self.assert_clean()

    def test_19_collapsed_object_heading_stacks_badge_below_title_before_the_chevron(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['objects'] = [{'id': 'test-heading', 'name': 'Тестовый объект', 'type': 'building', 'modifiers': []}]
        self.boot(fixture)
        self.select('test-crown-place')
        summary = self.page.locator('.object-card[data-object-id="test-heading"] > summary')
        self.assertEqual(summary.locator(':scope > .object-heading').count(), 1, 'title and badge share the middle summary column')
        self.assertEqual(summary.locator('.object-heading .object-title').text_content(), 'Тестовый объект')
        self.assertEqual(summary.locator('.object-heading .object-faction-badge').count(), 1)
        self.assertEqual(summary.locator(':scope > .chevron').count(), 1)
        self.assertTrue(summary.locator('.object-faction-badge').is_visible())
        self.assert_clean()

    def test_20_unknown_inherited_objects_are_not_presented_as_explicit_independent_objects(self):
        fixture = copy.deepcopy(FIXTURE)
        location = fixture['locations'][0]
        location['faction'] = None
        location['provenance'] = {'affiliationStatus': 'unknown'}
        location['objects'] = [
            {'id': 'test-unknown-inherited', 'name': 'Тестовый объект неизвестной земли', 'type': 'building', 'modifiers': []},
            {'id': 'test-explicit-independent', 'name': 'Тестовый явно независимый объект', 'type': 'resource', 'faction': None, 'modifiers': []},
        ]
        self.boot(fixture)
        self.select('test-crown-place')
        unknown = self.page.locator('.object-card[data-object-id="test-unknown-inherited"]')
        self.assertEqual(unknown.locator('.object-faction-badge').text_content(), 'Принадлежность не установлена')
        self.assertIn('Принадлежность не установлена', unknown.locator('.object-ownership').text_content())
        independent = self.page.locator('.object-card[data-object-id="test-explicit-independent"]')
        self.assertEqual(independent.locator('.object-faction-badge').text_content(), 'Независимый объект')
        self.assertEqual(unknown.evaluate('node => node.style.getPropertyValue("--object-color")'), '#b39467')
        self.assert_clean()

    def test_21_selected_label_is_not_clipped_and_keeps_real_map_anchor_at_multiple_scales(self):
        # Integration gate for the parent-owned scoped CSS, not a CSS fixture.
        self.boot(ATLAS)
        self.select('northern-headlands')
        marker = self.page.locator('.map-marker[data-location-id="northern-headlands"]')
        label = marker.locator('.marker-label')
        self.assertEqual(label.text_content(), 'Северный каменистый мыс')
        initial_width = marker.bounding_box()['width']
        for factor in [1, 1.25, 0.8]:
            self.page.evaluate('factor => window.ui.zoom(factor)', factor)
            self.page.evaluate("window.ui.focusLocation('northern-headlands', false)")
            geometry = marker.evaluate("""node => {
                const marker = node.getBoundingClientRect(), label = node.querySelector('.marker-label'), box = label.getBoundingClientRect();
                const range = document.createRange(); range.selectNodeContents(label);
                const text = range.getBoundingClientRect();
                return {center: [marker.x + marker.width / 2, marker.y + marker.height / 2], width: marker.width,
                    labelCenter: box.x + box.width / 2, textLeft: text.left, textRight: text.right,
                    left: box.left, right: box.right, overflow: getComputedStyle(node).overflow};
            }""")
            self.assertEqual(geometry['overflow'], 'visible', 'global button clipping must be reset for map markers')
            self.assertGreaterEqual(geometry['textLeft'], geometry['left'] + 4)
            self.assertLessEqual(geometry['textRight'], geometry['right'] - 4)
            self.assertAlmostEqual(geometry['labelCenter'], geometry['center'][0], delta=1)
            self.assertAlmostEqual(geometry['width'], initial_width, delta=0.2)
            point = self.page.evaluate('point => window.ui.toMap(...point)', geometry['center'])
            location = next(item for item in ATLAS['locations'] if item['id'] == 'northern-headlands')
            self.assertAlmostEqual(point[0], location['x'], delta=0.02)
            self.assertAlmostEqual(point[1], location['y'], delta=0.02)
        self.assert_clean()

    def test_22_gilneas_root_badges_use_the_supplied_crest_but_subject_houses_keep_their_identity(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['meta']['gilneasCrest'] = 'assets/ui/rose.svg'
        self.boot(fixture)
        root_crest = self.page.locator('.faction-tree[data-faction-id="gilneas"] > summary .faction-crest')
        self.assertEqual(root_crest.count(), 1)
        self.assertEqual(root_crest.get_attribute('src'), fixture['meta']['gilneasCrest'])
        self.assertEqual(self.page.locator('.faction-row[data-faction-id="gilneas"] .faction-crest').count(), 1)
        self.assertEqual(self.page.locator('.faction-tree[data-faction-id="test-house"] > summary .faction-crest').count(), 0)
        self.assertEqual(self.page.locator('.faction-row[data-faction-id="test-house"] .faction-crest').count(), 0)
        self.assert_clean()


if __name__ == '__main__':
    unittest.main()
