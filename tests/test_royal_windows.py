"""Vertical UI revision tests: real modules/DOM/CSS, only app.mjs is isolated.

All extra records/palette overrides are test-only; production data is never
written. Parent integrates the last-loaded stylesheet and measured emblem.
Run: /Users/daniil_si/.hermes/cache/scratch/gilneas-venv/bin/python tests/test_royal_windows.py -v
"""
import copy
import functools
import json
import os
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get('TMPDIR', '/Users/daniil_si/.hermes/cache/scratch')) / 'gilneas-royal-window-evidence'
SHAPE = 'M1 1H59V46.4L30 71 1 46.4Z'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def test_snapshot():
    data = json.loads((ROOT / 'assets/data/atlas.json').read_text())
    # Measured parent asset/palette. The override is test-only until metadata
    # integration lands; production UI deliberately has no guessed device.
    data['meta'].setdefault('gilneasHeraldry', {
        'symbol': 'assets/ui/gilneas-royal-symbol.png',
        'field': '#131516', 'edge': '#65707b', 'device': '#9aa8b6',
    })
    return data


class RoyalWindows(unittest.TestCase):
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
        ARTIFACTS.mkdir(parents=True, exist_ok=True)

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
        self.page.set_default_timeout(4000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
            status=200, content_type='application/javascript', body='// Royal-window test bootstrap seam.'))

    def tearDown(self):
        self.context.close()

    def boot(self, data=None, size=None):
        if size:
            self.page.set_viewport_size(size)
        self.data = copy.deepcopy(data if data is not None else test_snapshot())
        self.page.goto(self.url + '/index.html', wait_until='networkidle')
        self.page.evaluate("""async data => {
            // Parent owns index.html. Add the actual CSS, never a CSS mock.
            if (!document.querySelector('link[href$="royal-windows.css"]') && data.loadRoyalCSS) {
                const sheet = document.createElement('link'); sheet.rel = 'stylesheet';
                sheet.href = './assets/css/royal-windows.css'; document.head.append(sheet);
                await new Promise((resolve, reject) => { sheet.onload = resolve; sheet.onerror = reject; });
            }
            window.fixtureData = data.snapshot; window.fixtureSelected = null; window.calls = [];
            const { decorateIcons } = await import('./assets/js/icons.mjs');
            decorateIcons();
            const { initUI } = await import('./assets/js/ui.mjs');
            window.ui = initUI({
                getData: () => window.fixtureData, getSelectedId: () => window.fixtureSelected,
                onSelect: id => { window.fixtureSelected = id; window.ui.render(); },
                onShowNoble: id => window.nobleUI.open(id),
                onEditLocation: id => window.calls.push(['edit', id]),
                onAddObject: id => window.calls.push(['add', id]),
                onEditObject: (id, objectId) => window.calls.push(['edit-object', id, objectId]),
                onDeleteObject: (id, objectId) => window.calls.push(['delete-object', id, objectId]),
            });
            const { initNobleDossier } = await import('./assets/js/noble-dossier.mjs');
            window.nobleUI = initNobleDossier({
                getData: () => window.fixtureData,
                onSelect: id => { window.fixtureSelected = id; window.ui.render(); },
            });
        }""", {'snapshot': self.data, 'loadRoyalCSS': (ROOT / 'assets/css/royal-windows.css').exists()})
        self.page.wait_for_function("document.querySelector('#base-map').complete && document.querySelector('#base-map').naturalWidth > 0", polling=50)
        self.page.wait_for_timeout(100)
        self.page.mouse.move(2, 2)

    def select(self, location_id):
        self.page.evaluate("id => { window.fixtureSelected = id; window.ui.render(); }", location_id)
        self.page.wait_for_timeout(220)

    def evidence(self, label):
        self.page.screenshot(path=str(ARTIFACTS / f'{label}.png'), full_page=True)

    def assert_clean(self):
        self.assertEqual(self.errors, [])

    def test_01_root_location_uses_five_sided_black_shield_with_metadata_device(self):
        data = test_snapshot()
        location = data['locations'][0]
        location['faction'] = 'gilneas'  # Test-only root-field contrast case.
        self.boot(data)
        self.select(location['id'])
        self.evidence('01-root-shield')
        shield = self.page.locator('#dossier-seal svg.faction-shield')
        self.assertEqual(shield.count(), 1, 'Every dossier needs the existing five-sided SVG, not a crest image or map glyph')
        self.assertEqual(shield.get_attribute('viewBox'), '0 0 60 72')
        self.assertEqual(shield.get_attribute('data-faction-id'), 'gilneas', 'Expose the immediate affiliation, never its ancestor')
        self.assertEqual(shield.get_attribute('data-color'), data['meta']['gilneasHeraldry']['field'])
        self.assertEqual(shield.locator('.shield-field').get_attribute('d'), SHAPE)
        self.assertEqual(shield.locator('.shield-field').get_attribute('fill'), data['meta']['gilneasHeraldry']['field'])
        self.assertEqual(shield.locator('.shield-field').get_attribute('stroke'), data['meta']['gilneasHeraldry']['edge'])
        self.assertEqual(shield.locator('image.shield-device').get_attribute('href'), data['meta']['gilneasHeraldry']['symbol'])
        self.assertEqual(shield.locator('.shield-device').count(), 1)
        self.assertEqual(self.page.locator('#dossier-seal img').count(), 0)
        self.assert_clean()
    def test_02_every_location_uses_its_immediate_faction_without_changing_map_glyphs(self):
        data = test_snapshot()
        template = copy.deepcopy(data['locations'][0])
        for suffix, affiliation in [('independent', 'independent'), ('unknown', 'unknown')]:
            item = copy.deepcopy(template)
            item.update(id='test-shield-' + suffix, faction=None, objects=[], name='Тестовый ' + suffix)
            item['provenance'] = {'affiliationStatus': affiliation}
            data['locations'].append(item)
        self.boot(data)
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        glyphs = self.page.locator('#markers .map-marker').evaluate_all("""nodes => nodes.map(node => ({
            id: node.dataset.locationId, path: node.querySelector('svg path').getAttribute('d'),
            viewBox: node.querySelector('svg').getAttribute('viewBox'), left: node.style.left, top: node.style.top,
            color: node.style.getPropertyValue('--marker-color'), width: getComputedStyle(node.querySelector('svg')).width,
            height: getComputedStyle(node.querySelector('svg')).height,
        }))""")
        factions = {f['id']: f for f in data['factions']}
        observed = []
        for location in data['locations']:
            self.page.evaluate("id => { window.fixtureSelected = id; window.ui.render(); }", location['id'])
            shield = self.page.locator('#dossier-seal .faction-shield')
            self.assertEqual(shield.count(), 1, location['id'])
            faction = factions.get(location.get('faction'))
            expected = data['meta']['gilneasHeraldry']['field'] if location.get('faction') == 'gilneas' else faction['color'] if faction else '#87918d'
            self.assertEqual(shield.get_attribute('data-color'), expected, location['id'])
            self.assertEqual(shield.locator('.shield-field').get_attribute('fill'), expected)
            parent = faction
            chain = set()
            while parent and parent['id'] not in chain:
                chain.add(parent['id'])
                parent = factions.get(parent.get('parent'))
            is_gilneas = 'gilneas' in chain
            self.assertEqual(shield.locator('image.shield-device').count(), int(is_gilneas), location['id'])
            if is_gilneas:
                self.assertEqual(shield.locator('.shield-field').get_attribute('stroke'), data['meta']['gilneasHeraldry']['edge'])
                self.assertEqual(shield.locator('image').get_attribute('href'), data['meta']['gilneasHeraldry']['symbol'])
            self.assertEqual(shield.locator('.shield-field').get_attribute('d'), SHAPE)
            observed.append({'id': location['id'], 'faction': location.get('faction'), 'field': expected, 'device': is_gilneas})
        after_glyphs = self.page.locator('#markers .map-marker').evaluate_all("""nodes => nodes.map(node => ({
            id: node.dataset.locationId, path: node.querySelector('svg path').getAttribute('d'),
            viewBox: node.querySelector('svg').getAttribute('viewBox'), left: node.style.left, top: node.style.top,
            color: node.style.getPropertyValue('--marker-color'), width: getComputedStyle(node.querySelector('svg')).width,
            height: getComputedStyle(node.querySelector('svg')).height,
        }))""")
        self.assertEqual(glyphs, after_glyphs)
        self.assertEqual(len(observed), len(data['locations']))
        self.assertEqual(before, self.page.evaluate('JSON.stringify(window.fixtureData)'))
        (ARTIFACTS / 'all-location-shields.json').write_text(json.dumps(observed, ensure_ascii=False, indent=2))
        self.assert_clean()
    def test_03_nested_cards_show_effective_faction_shields_and_keep_native_actions(self):
        data = test_snapshot()
        location = data['locations'][0]
        location['faction'] = 'crowley'
        location['objects'] = [
            {'id': 'test-inherit', 'name': 'Тест наследования', 'type': 'building', 'description': 'Тестовый объект', 'modifiers': [
                {'id': 'test-plus', 'kind': 'bonus', 'text': 'Тестовый бонус +3'},
                {'id': 'test-minus', 'kind': 'penalty', 'text': 'Тестовый штраф −2'}]},
            {'id': 'test-none', 'name': 'Тест независимости', 'type': 'resource', 'faction': None},
            {'id': 'test-junior', 'name': 'Тест младшего дома', 'type': 'landmark', 'faction': 'silverlaine'},
            {'id': 'test-root', 'name': 'Тест короны', 'type': 'building', 'faction': 'gilneas'},
            {'id': 'test-other', 'name': 'Тест другой державы', 'type': 'resource', 'faction': 'lordaeron'},
        ]
        self.boot(data)
        self.select(location['id'])
        expected = ['crowley', None, 'silverlaine', 'gilneas', 'lordaeron']
        factions = {f['id']: f for f in data['factions']}
        for item, faction_id in zip(location['objects'], expected):
            card = self.page.locator(f'#dossier-objects [data-object-id="{item["id"]}"]')
            shield = card.locator('.object-icon .faction-shield')
            self.assertEqual(shield.count(), 1, 'Nested cards must replace the building/resource glyph with the same shield')
            field = data['meta']['gilneasHeraldry']['field'] if faction_id == 'gilneas' else factions[faction_id]['color'] if faction_id else '#87918d'
            self.assertEqual(shield.get_attribute('data-color'), field)
            self.assertEqual(shield.locator('.shield-field').get_attribute('d'), SHAPE)
            self.assertEqual(shield.locator('.shield-device').count(), int(faction_id in ['crowley', 'silverlaine', 'gilneas']))
        card = self.page.locator('#dossier-objects [data-object-id="test-inherit"]')
        card.locator('summary').click()
        self.assertTrue(card.evaluate('e => e.open'))
        self.assertEqual(card.locator('.modifier.bonus').inner_text(), 'Тестовый бонус +3')
        self.assertEqual(card.locator('.modifier.penalty').inner_text(), 'Тестовый штраф −2')
        self.page.locator('#dossier-favorite').click()
        self.assertTrue(card.evaluate('e => e.open'), 'Rerendering favorites must retain open cards')
        card.locator('[data-object-edit]').click()
        card.locator('[data-object-delete]').click()
        self.assertEqual(self.page.evaluate('window.calls'), [
            ['edit-object', location['id'], 'test-inherit'], ['delete-object', location['id'], 'test-inherit']])
        self.evidence('03-nested-shields')
        self.assert_clean()
    def test_04_every_noble_uses_house_shield_instead_of_the_old_img(self):
        data = test_snapshot()
        data['nobles'].append({'id': 'test-no-house', 'name': 'Тест без дома', 'house': None, 'description': 'Только тест.'})
        self.boot(data)
        factions = {f['id']: f for f in data['factions']}
        for noble in data['nobles']:
            self.page.evaluate('id => window.nobleUI.open(id)', noble['id'])
            identity = self.page.locator('#noble-crest')
            self.assertTrue(identity.is_visible(), 'Every person, including an unaffiliated one, needs the plain shield')
            self.assertNotEqual(identity.evaluate('e => e.tagName'), 'IMG', 'The identity container must accept the shared SVG safely')
            self.assertEqual(identity.get_attribute('aria-hidden'), 'true')
            shield = identity.locator('.faction-shield')
            self.assertEqual(shield.count(), 1)
            house = factions.get(noble.get('house'))
            field = data['meta']['gilneasHeraldry']['field'] if noble.get('house') == 'gilneas' else house['color'] if house else '#87918d'
            self.assertEqual(shield.get_attribute('data-color'), field)
            self.assertEqual(shield.locator('.shield-field').get_attribute('d'), SHAPE)
            self.assertEqual(self.page.locator('#noble-name').text_content(), noble['name'])
        self.evidence('04-noble-shield')
        self.assert_clean()
    def test_05_shared_shield_api_keeps_options_safe_and_rejects_non_image_urls(self):
        self.boot()
        result = self.page.evaluate("""async () => {
            const { createFactionShield } = await import('./assets/js/heraldry.mjs');
            const shield = createFactionShield(window.fixtureData, 'crowley', { className: 'test-extra', id: 'test-shield-id' });
            document.body.append(shield);
            const unsafe = ['javascript:window.shieldXss=1', 'data:image/svg+xml,<svg onload="window.shieldXss=2"/>',
                '//example.org/crest.png', 'https://example.org/crest.html', 'file:///etc/passwd.png',
                'https://name:password@example.org/crest.png', 'assets/ui/crest.png\\\\evil', ' assets/ui/crest.png'];
            const rejected = unsafe.map(symbol => {
                const snapshot = structuredClone(window.fixtureData); snapshot.meta.gilneasHeraldry.symbol = symbol;
                return createFactionShield(snapshot, 'crowley').querySelectorAll('image').length;
            });
            const snapshot = structuredClone(window.fixtureData);
            snapshot.factions.push({ id: 'test-bad-color', color: 'url(javascript:window.shieldXss=3)', parent: null });
            const neutral = createFactionShield(snapshot, 'test-bad-color');
            return { id: shield.id, classes: [...shield.classList], rejected,
                field: neutral.dataset.color, children: [...shield.children].map(node => node.tagName),
                script: !!document.querySelector('.faction-shield script'), xss: window.shieldXss || null };
        }""")
        self.assertEqual(result['id'], 'test-shield-id', 'Optional stable identity must be set without HTML interpolation')
        self.assertIn('test-extra', result['classes'])
        self.assertIn('faction-shield', result['classes'])
        self.assertEqual(result['rejected'], [0] * 8)
        self.assertEqual(result['field'], '#87918d')
        self.assertEqual(result['children'], ['path', 'image'])
        self.assertFalse(result['script'])
        self.assertIsNone(result['xss'])
        self.assert_clean()
    def test_06_windows_share_registry_surfaces_headers_and_square_controls_at_all_viewports(self):
        geometries = []
        for size in [{'width': 1440, 'height': 1000}, {'width': 390, 'height': 844}, {'width': 844, 'height': 390}]:
            self.boot(size=size)
            self.select(self.data['locations'][0]['id'])
            # Native top-layer dialogs retain their original scroll layout.
            noble = self.data['nobles'][0]
            self.page.evaluate('id => window.nobleUI.open(id)', noble['id'])
            self.evidence(f'06-windows-{size["width"]}x{size["height"]}')
            palette = self.page.evaluate("""() => {
                const style = selector => { const c=getComputedStyle(document.querySelector(selector));
                    return {background:c.backgroundColor, image:c.backgroundImage, font:c.fontFamily, border:c.borderBottomColor}; };
                return {navigation:style('#navigation'), dossier:style('#dossier'), noble:style('#noble-dossier'),
                    editor:style('#editor'), help:style('#help'), registryHeader:style('#navigation .panel-head'),
                    dossierHeader:style('#dossier .dossier-head'), nobleHeader:style('#noble-dossier .dialog-head'),
                    editorHeader:style('#editor .dialog-head'), boundary:document.querySelector('#boundary-tools') ? style('#boundary-tools') : null};
            }""")
            for key in ['navigation', 'dossier', 'noble', 'editor', 'help']:
                self.assertEqual(palette[key]['background'], 'rgb(26, 29, 31)', f'{size}: {key} must share the registry background')
                self.assertEqual(palette[key]['image'], 'none', f'{size}: remove parchment and gradients')
                self.assertEqual(palette[key]['font'], palette['navigation']['font'])
            for key in ['registryHeader', 'dossierHeader', 'nobleHeader', 'editorHeader']:
                self.assertEqual(palette[key]['background'], 'rgb(32, 38, 41)', f'{size}: {key}')
                self.assertEqual(palette[key]['image'], 'none')
                self.assertEqual(palette[key]['border'], palette['registryHeader']['border'])
            buttons = self.page.locator('#noble-dossier .dialog-head button').evaluate_all("""nodes => nodes.map(e => {
                const r=e.getBoundingClientRect(),c=getComputedStyle(e); return {width:r.width,height:r.height,
                    background:c.backgroundColor,image:c.backgroundImage,border:c.borderColor,color:c.color,radius:c.borderRadius}; })""")
            self.assertEqual(buttons[0]['width'], 44)
            self.assertEqual(buttons[0]['height'], 44)
            self.page.evaluate('window.nobleUI.close()')
            self.page.locator('#dossier-fold').click()
            self.assertEqual(self.page.locator('#dossier-fold').get_attribute('aria-expanded'), 'false')
            self.page.locator('#dossier-fold').click()
            self.assertTrue(self.page.locator('#dossier-body').is_visible())
            self.page.mouse.move(2, 2)
            self.page.wait_for_timeout(220)
            dossier_buttons = self.page.locator('#dossier .dossier-head button').evaluate_all("""nodes => nodes.map(e => {
                const r=e.getBoundingClientRect(),c=getComputedStyle(e); return {width:r.width,height:r.height,
                    background:c.backgroundColor,image:c.backgroundImage,border:c.borderColor,color:c.color,radius:c.borderRadius}; })""")
            self.assertEqual(dossier_buttons, [buttons[0], buttons[0]], 'Close/fold controls must have identical winning geometry and styles')
            self.page.locator('#dossier-close').click()
            self.assertTrue(self.page.locator('#dossier').is_hidden())
            self.page.evaluate("window.ui.setPanel('navigation',true)")
            nav_button = self.page.locator('#nav-close').bounding_box()
            self.assertEqual([nav_button['width'], nav_button['height']], [44, 44])
            self.page.locator('#nav-close').click()
            self.assertTrue(self.page.locator('#navigation').is_hidden())
            self.page.evaluate("window.ui.setPanel('layers',true)")
            layer_button = self.page.locator('#layers-fold').bounding_box()
            self.assertEqual([layer_button['width'], layer_button['height']], [44, 44])
            self.page.locator('#layers-fold').click()
            self.assertTrue(self.page.locator('#layer-body').is_hidden())
            self.page.locator('#layers-fold').click()
            self.assertTrue(self.page.locator('#layer-body').is_visible())
            geometries.append({'viewport':size,'palette':palette,'close':buttons[0]})
            self.assert_clean()
        (ARTIFACTS / 'window-palettes-and-controls.json').write_text(json.dumps(geometries, ensure_ascii=False, indent=2))
    def test_07_inner_dossiers_are_dark_readable_and_keep_semantic_colors_and_shield_sizes(self):
        data = test_snapshot()
        location = data['locations'][0]
        location['faction'] = 'crowley'
        location['objects'] = [{'id': 'test-colors', 'name': 'Тест цвета', 'type': 'building', 'description': 'Тестовая запись.',
            'faction': 'silverlaine', 'modifiers': [{'id': 'test-b', 'kind': 'bonus', 'text': 'Бонус'}, {'id': 'test-p', 'kind': 'penalty', 'text': 'Штраф'}]}]
        self.boot(data)
        self.select(location['id'])
        card = self.page.locator('#dossier-objects [data-object-id="test-colors"]')
        card.locator('summary').click()
        styles = self.page.evaluate("""() => {
            const style=s=>{const e=document.querySelector(s),c=getComputedStyle(e),r=e.getBoundingClientRect();
                return {bg:c.backgroundColor,image:c.backgroundImage,color:c.color,width:r.width,height:r.height,
                    clip:c.clipPath,border:c.borderBottomColor,font:c.fontFamily};};
            return {card:style('.object-card'),description:style('#dossier-description'),title:style('#dossier-title'),
                owner:style('#dossier-owner'),label:style('#dossier-faction'),badge:style('.object-faction-badge'),
                bonus:style('.modifier.bonus'),penalty:style('.modifier.penalty'),seal:style('#dossier-seal'),
                shield:style('#dossier-seal .faction-shield'),objectShield:style('.object-icon .faction-shield'),
                pseudo:getComputedStyle(document.querySelector('#dossier-seal'),'::after').content};
        }""")
        self.evidence('07-dossier-colors')
        self.assertEqual(styles['card']['bg'], 'rgb(26, 29, 31)', 'Object cards must not retain their beige paper surfaces')
        for key in ['description', 'title', 'owner']:
            self.assertEqual(styles[key]['color'], 'rgb(221, 213, 194)', key + ' must use registry cream, never parchment ink')
        self.assertEqual(styles['label']['color'], 'rgb(99, 144, 150)')
        self.assertEqual(styles['badge']['color'], 'rgb(147, 167, 152)')
        self.assertEqual(styles['bonus']['color'], 'rgb(94, 170, 120)')
        self.assertEqual(styles['penalty']['color'], 'rgb(211, 121, 120)')
        self.assertEqual(styles['seal']['clip'], 'none', 'The wax rosette clip must not cut the five-sided shield')
        self.assertIn(styles['pseudo'], ['none', 'normal'], 'Remove the wax-seal circular ornament')
        self.assertEqual([styles['shield']['width'], styles['shield']['height']], [58, 65])
        self.assertEqual([styles['objectShield']['width'], styles['objectShield']['height']], [25, 30])
        self.page.evaluate("window.nobleUI.open('noble-darius')")
        noble_styles = self.page.evaluate("""() => {
            const style=s=>{const c=getComputedStyle(document.querySelector(s));return {color:c.color,bg:c.backgroundColor,image:c.backgroundImage};};
            return {description:style('#noble-description'),title:style('#noble-title'),tenure:style('#noble-social-status'),
                holding:style('.noble-holding'),holdingName:style('.holding-name'),body:style('.noble-body')};
        }""")
        for key in ['description', 'title', 'tenure', 'holdingName']:
            self.assertEqual(noble_styles[key]['color'], 'rgb(221, 213, 194)', key)
        self.assertEqual(noble_styles['holding']['bg'], 'rgb(26, 29, 31)')
        self.assertEqual(noble_styles['body']['image'], 'none')
        self.evidence('07-noble-colors')
        self.assert_clean()
    def test_08_action_buttons_fields_and_wrapped_peers_have_uniform_geometry(self):
        measurements = []
        for size in [{'width': 1440, 'height': 1000}, {'width': 390, 'height': 844}, {'width': 844, 'height': 390}]:
            self.boot(size=size)
            # Actual editor module; no stubs for dynamically generated controls.
            self.page.evaluate("""async () => {
                const { initEditor } = await import('./assets/js/editor.mjs');
                window.editorUI=initEditor({getData:()=>window.fixtureData,getSelectedId:()=>window.fixtureSelected,
                    getUI:()=>window.ui,replaceData:data=>{window.fixtureData=data;window.ui.render();}});
                document.querySelector('#editor-open').addEventListener('click',()=>window.editorUI.open());
            }""")
            self.select(self.data['locations'][0]['id'])
            self.page.locator('#editor-open').click()
            actions = self.page.locator('#editor .editor-actions button, #editor .export-actions button, #editor .export-actions label, #editor .destructive-actions button').evaluate_all("""nodes => nodes.map(e=>{
                const r=e.getBoundingClientRect(),c=getComputedStyle(e);return {id:e.id||'import-label',height:r.height,width:r.width,
                    radius:c.borderRadius,top:r.top,bg:c.backgroundColor,border:c.borderColor,padding:c.padding};})""")
            for action in actions:
                self.assertGreaterEqual(action['height'], 44, action['id'])
                self.assertEqual(action['radius'], '2px')
            peers = [a for a in actions if a['id'] in ['location-create','location-edit','location-move','object-create','houses-open','territories-open']]
            for peer in peers:
                self.assertEqual(peer['bg'], 'rgb(38, 40, 42)')
                self.assertEqual(peer['border'], 'rgb(96, 91, 76)')
                for other in peers:
                    if abs(other['top']-peer['top']) < 1:
                        self.assertEqual(peer['height'],other['height'],'Wrapped peer actions must share the available row height')
            self.page.locator('[data-close="editor"]').click()
            self.page.evaluate('window.editorUI.editLocation(window.fixtureSelected)')
            fields = self.page.locator('#location-editor input:not([type=checkbox]):not([type=hidden]), #location-editor select').evaluate_all("""nodes=>nodes.map(e=>{
                const r=e.getBoundingClientRect(),p=e.parentElement.getBoundingClientRect();return {id:e.id,height:r.height,left:r.left,
                    right:r.right,parentLeft:p.left,parentRight:p.right};})""")
            for field in fields:
                self.assertEqual(field['height'],44, field['id'])
                self.assertGreaterEqual(field['left'],field['parentLeft'])
                self.assertLessEqual(field['right'],field['parentRight']+.1)
            self.page.locator('[data-close="location-editor"]').click()
            self.page.evaluate('window.editorUI.addObject(window.fixtureSelected)')
            self.page.locator('#modifier-bonus-add').click()
            self.page.locator('#modifier-penalty-add').click()
            remove = self.page.locator('[data-modifier-remove]').evaluate_all('nodes=>nodes.map(e=>{const r=e.getBoundingClientRect();return [r.width,r.height]})')
            self.assertEqual(remove, [[44,44],[44,44]])
            self.page.evaluate("document.querySelector('#object-editor').close()")
            self.page.locator('#dossier-add-object').click()
            dossier_actions = self.page.locator('#dossier-add-object,#dossier-edit,#dossier-favorite,#dossier-focus').evaluate_all("""nodes=>nodes.map(e=>{
                const r=e.getBoundingClientRect(),c=getComputedStyle(e);return {id:e.id,height:r.height,bg:c.backgroundColor,border:c.borderColor};})""")
            self.page.mouse.move(2,2)
            self.page.wait_for_timeout(220)
            for action in dossier_actions:
                self.assertGreaterEqual(action['height'],44, action['id']+' must match window controls')
            measurements.append({'viewport':size,'actions':actions,'fields':fields,'dossierActions':dossier_actions})
            self.assert_clean()
        (ARTIFACTS/'action-and-field-boxes.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2))
    def test_09_action_palette_preserves_branded_destructive_bonus_and_penalty_identity(self):
        self.boot()
        colors = self.page.evaluate("""() => {
            document.querySelector('#editor').showModal();
            const style=id=>{const c=getComputedStyle(document.getElementById(id));return {bg:c.backgroundColor,color:c.color,border:c.borderColor};};
            return Object.fromEntries(['export-site','export-json','draft-reset','location-delete','modifier-bonus-add','modifier-penalty-add'].map(id=>[id,style(id)]));
        }""")
        self.assertEqual(colors['export-site'], {'bg':'rgb(48, 46, 39)','color':'rgb(225, 199, 148)','border':'rgb(140, 116, 80)'})
        self.assertEqual(colors['export-json'], {'bg':'rgb(38, 40, 42)','color':'rgb(221, 213, 194)','border':'rgb(96, 91, 76)'})
        self.assertEqual(colors['draft-reset'], colors['location-delete'])
        self.assertEqual(colors['draft-reset']['bg'],'rgb(54, 35, 40)')
        self.assertEqual(colors['modifier-bonus-add']['color'],'rgb(171, 208, 169)')
        self.assertEqual(colors['modifier-penalty-add']['color'],'rgb(215, 148, 148)')
        self.page.locator('#draft-reset').hover()
        self.page.wait_for_timeout(220)
        hover = self.page.locator('#draft-reset').evaluate('e=>{const c=getComputedStyle(e);return {bg:c.backgroundColor,color:c.color,border:c.borderColor}}')
        self.assertEqual(hover,{'bg':'rgb(77, 41, 50)','color':'rgb(233, 179, 174)','border':'rgb(182, 101, 112)'})
        self.assert_clean()
    def test_10_home_reads_current_map_metadata_bounds_without_other_camera_changes(self):
        data = test_snapshot()
        bounds = {'x': 400, 'y': 600, 'width': 800, 'height': 900}
        data['meta']['homeBounds'] = bounds
        self.boot(data)
        self.page.evaluate("window.ui.setPanel('navigation',false);window.ui.setPanel('layers',false);window.ui.setPanel('dossier',false);window.ui.home(false)")
        result = self.page.evaluate("""bounds => {
            const rect=document.querySelector('#viewport').getBoundingClientRect(), c=window.ui.getCamera();
            const scale=Math.min((rect.width-48)/bounds.width,(rect.height-48)/bounds.height)*.94;
            return {camera:c, expected:{x:rect.width/2-(bounds.x+bounds.width/2)*scale,
                y:rect.height/2-(bounds.y+bounds.height/2)*scale,scale}};
        }""", bounds)
        for key in ['x','y','scale']:
            self.assertAlmostEqual(result['camera'][key],result['expected'][key],delta=.01,msg='home() must use meta.homeBounds')
        self.assert_clean()

    def test_11_headers_share_registry_typography_and_icon_geometry(self):
        self.boot()
        self.select(self.data['locations'][0]['id'])
        self.page.evaluate('id=>window.nobleUI.open(id)',self.data['nobles'][0]['id'])
        styles=self.page.evaluate("""() => {
            const style=s=>{const c=getComputedStyle(document.querySelector(s));return {size:c.fontSize,font:c.fontFamily,
                weight:c.fontWeight,line:c.lineHeight,color:c.color};};
            return {nav:style('#navigation h2'),layer:style('#layers h2'),noble:style('#noble-name'),
                editor:style('#editor .dialog-head h2'),navEyebrow:style('#navigation .panel-head .eyebrow'),
                nobleEyebrow:style('#noble-dossier .dialog-head .eyebrow'),dossierEyebrow:style('#dossier-type')};
        }""")
        self.assertEqual(styles['layer'],styles['nav'],'All window headings must use the actual registry font treatment')
        self.assertEqual(styles['noble'],styles['nav'])
        self.assertEqual(styles['editor'],styles['nav'])
        self.assertEqual(styles['nobleEyebrow'],styles['navEyebrow'])
        self.assertEqual(styles['dossierEyebrow'],styles['navEyebrow'])
        icon_boxes=self.page.locator('#nav-close svg,#noble-dossier .dialog-head button svg,#dossier-fold svg').evaluate_all('nodes=>nodes.map(e=>{const c=getComputedStyle(e);return [c.width,c.height]})')
        self.assertEqual(icon_boxes,[['19px','19px']]*3)
        self.evidence('11-header-typography')
        self.assert_clean()
    def test_12_native_scroll_cards_and_camera_rail_remain_reachable_without_overlap(self):
        evidence = []
        for size in [{'width':1440,'height':1000},{'width':390,'height':844},{'width':844,'height':390}]:
            data=test_snapshot()
            location=data['locations'][0]
            location['objects']=[{'id':'test-scroll-card','type':'building','name':'Тестовая карточка',
                'description':'Тестовый текст.\n'*12,'modifiers':[{'id':'b','kind':'bonus','text':'Бонус +3'},{'id':'p','kind':'penalty','text':'Штраф −2'}]}]
            self.boot(data,size)
            self.select(location['id'])
            self.page.locator('.object-card summary').click()
            self.assertTrue(self.page.locator('.object-card').evaluate('e=>e.open'))
            panel=self.page.locator('#dossier').bounding_box()
            rail=self.page.locator('.zoom-tools').bounding_box()
            overlaps=lambda a,b: a['x']<b['x']+b['width'] and a['x']+a['width']>b['x'] and a['y']<b['y']+b['height'] and a['y']+a['height']>b['y']
            self.assertFalse(overlaps(panel,rail),'Keep the camera rail outside the original dossier box')
            header=self.page.locator('#dossier .dossier-head').bounding_box()
            self.page.mouse.move(panel['x']+panel['width']/2,panel['y']+panel['height']/2)
            self.page.mouse.wheel(0,2500)
            self.page.wait_for_timeout(220)
            self.assertAlmostEqual(self.page.locator('#dossier .dossier-head').bounding_box()['y'],header['y'],delta=1)
            self.page.locator('#dossier-focus').scroll_into_view_if_needed()
            self.assertTrue(self.page.locator('#dossier-focus').is_visible())
            self.page.locator('#dossier-fold').click()
            self.assertTrue(self.page.locator('#dossier-body').is_hidden())
            self.page.locator('#dossier-fold').click()
            self.assertTrue(self.page.locator('#dossier-body').is_visible())
            self.page.locator('#dossier-close').click()
            self.page.evaluate("window.ui.setPanel('navigation',true)")
            registry=self.page.locator('#location-list').bounding_box()
            self.assertGreater(registry['height'],50,'Do not flatten or clip the native navigation scroll track')
            self.page.locator('#location-list .location-row').last.scroll_into_view_if_needed()
            self.assertTrue(self.page.locator('#location-list .location-row').last.is_visible())
            self.page.locator('#nav-close').click()
            self.page.evaluate('id=>window.nobleUI.open(id)',data['nobles'][0]['id'])
            self.page.evaluate("document.querySelector('#noble-dossier').scrollTop=document.querySelector('#noble-dossier').scrollHeight")
            self.page.locator('#noble-sources').scroll_into_view_if_needed()
            self.assertTrue(self.page.locator('#noble-sources').is_visible())
            self.evidence(f'12-scroll-{size["width"]}x{size["height"]}')
            evidence.append({'viewport':size,'dossier':panel,'cameraRail':rail,'registry':registry})
            self.assert_clean()
        (ARTIFACTS/'nonoverlap-and-scroll.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    unittest.main()
