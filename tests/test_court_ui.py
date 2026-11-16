"""Court interaction tracer bullets against real DOM/CSS and native input.

Only the parent app bootstrap is routed away in isolated tests; all UI,
chronicle, icons and raster assets are real. Extra records never leave fixtures.
Run: .../gilneas-venv/bin/python tests/test_court_ui.py -v
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
ARTIFACTS = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-court-ui-evidence')


def snapshot():
    data = json.loads((ROOT / 'assets/data/atlas.json').read_text())
    original = data['locations'][0]
    location = copy.deepcopy(original)
    # The isolated two-point fixture must not inherit links to removed real IDs.
    location.pop('isLocation', None)
    location.pop('linkedLocationIds', None)
    location.update(id='test-court-location', name='Тестовое поместье автора', type='estate',
                    faction='crowley', owner='Владелец локации', capital=False, x=1800, y=3400,
                    description='Тестовое описание владения.', objects=[])
    peer = copy.deepcopy(location)
    peer.update(id='test-court-peer', name='Тестовая соседняя локация', type='city', x=2050, y=3400)
    data['locations'] = [location, peer]
    # This labelled isolated fixture excludes every canonical ferry endpoint.
    data['meta'].pop('ferryNetwork', None)
    data['territories'] = []
    data['nobles'] = [{'id': 'test-court-noble', 'name': 'Тестовый авторский дворянин',
                       'title': 'Тестовый титул', 'description': 'Только тестовая запись.',
                       'house': 'crowley', 'sources': [data['sources'][0]['id']]}]
    return data


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class CourtUI(unittest.TestCase):
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
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        self.page = self.context.new_page()
        self.page.set_default_timeout(5000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)

    def tearDown(self):
        self.context.close()

    def boot(self, data=None, size=None, real=False):
        if size:
            self.page.set_viewport_size(size)
        self.data = copy.deepcopy(data if data is not None else snapshot())
        if not real:
            self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
                status=200, content_type='application/javascript', body='// Court test: isolated parent bootstrap.'))
        self.page.goto(self.url + '/index.html', wait_until='networkidle')
        # The parent owns static markup and stylesheet ordering. Its real
        # layer return control and Council entry are both actual static markup.
        self.page.evaluate("""async options => {
            if (options.loadCSS && !document.querySelector('link[href$="court-ui.css"]')) {
                const link=document.createElement('link'); link.rel='stylesheet';
                link.href='./assets/css/court-ui.css'; document.head.append(link);
                await new Promise((resolve,reject)=>{link.onload=resolve;link.onerror=reject;});
            }

            const {decorateIcons}=await import('./assets/js/icons.mjs'); decorateIcons();
            if (!options.real) {
                document.body.classList.add('edit-mode');
                window.fixtureData=options.snapshot; window.fixtureSelected=null; window.calls=[];
                const {initUI}=await import('./assets/js/ui.mjs');
                window.ui=initUI({getData:()=>window.fixtureData,getSelectedId:()=>window.fixtureSelected,
                    onSelect:id=>{window.fixtureSelected=id;window.calls.push(['select',id]);window.ui.render();},
                    onClearSelection:()=>{window.fixtureSelected=null;window.calls.push(['clear']);window.ui.render();},
                    onShowNoble:id=>window.calls.push(['noble',id]),
                    onEditObject:(id,objectId)=>window.calls.push(['edit-object',id,objectId]),
                    onDeleteObject:(id,objectId)=>window.calls.push(['delete-object',id,objectId])});
                const {initChronicle}=await import('./assets/js/chronicle.mjs');
                window.chronicleUI=initChronicle(()=>window.fixtureData,{onOpenCouncil:()=>window.calls.push(['council'])});
            }
        }""", {'snapshot': self.data, 'loadCSS': (ROOT / 'assets/css/court-ui.css').exists(), 'real': real})
        if real:
            self.page.wait_for_function('window.gilneasApp?.ready', polling=50)
            self.page.evaluate('window.ui=window.gilneasApp.ui')
        self.page.wait_for_function("document.querySelector('#base-map').complete && document.querySelector('#base-map').naturalWidth>0", polling=50)
        self.page.mouse.move(2, 2)

    def select(self, location_id='test-court-location'):
        self.page.evaluate('id=>{window.fixtureSelected=id;window.ui.render();window.ui.focusLocation(id,false);}', location_id)

    def clean(self):
        self.assertEqual(self.errors, [])

    def test_01_native_fold_is_compact_with_named_sticky_44px_header(self):
        self.boot()
        self.select()
        self.page.locator('#dossier-fold').click()
        state = self.page.locator('#dossier').evaluate("""e=>{
            const header=e.querySelector('.dossier-head'),body=e.querySelector('#dossier-body');
            const c=getComputedStyle(header),r=e.getBoundingClientRect();
            return {height:r.height,headerHeight:header.getBoundingClientRect().height,
                hidden:body.hidden,display:getComputedStyle(body).display,position:c.position,top:c.top,
                headerText:header.innerText,title:header.title,expanded:e.querySelector('#dossier-fold').getAttribute('aria-expanded')};
        }""")
        print('Native folded cascade:', state)
        self.page.screenshot(path=str(ARTIFACTS / '01-native-fold.png'))
        self.assertTrue(state['hidden'])
        self.assertEqual(state['display'], 'none', 'The winning cascade must truly hide dossier content')
        self.assertLessEqual(state['height'], 48, 'Folded dossier must shrink to its header, not an empty tall panel')
        self.assertEqual(state['headerHeight'], 44)
        self.assertEqual([state['position'], state['top']], ['sticky', '0px'])
        self.assertIn('Тестовое поместье автора', state['headerText'])
        self.assertIn('ПОМЕСТЬЕ', state['headerText'])
        self.assertIn('Тестовое поместье автора', state['title'])
        self.assertEqual(state['expanded'], 'false')
        buttons=self.page.locator('#dossier .dossier-head button').evaluate_all('nodes=>nodes.map(e=>{const r=e.getBoundingClientRect();return [r.width,r.height];})')
        self.assertEqual(buttons, [[32, 32], [32, 32]], 'The compact dossier actions leave room within the unchanged 44px header')
        self.page.locator('#dossier-fold').click()
        self.assertTrue(self.page.locator('#dossier-body').is_visible())
        self.clean()

    def test_02_selected_native_hover_never_shows_tooltip_even_folded_or_closed(self):
        self.boot()
        self.select()
        peer = self.page.locator('.map-marker[data-location-id="test-court-peer"]')
        marker = self.page.locator('.map-marker[data-location-id="test-court-location"]')
        peer.hover()
        self.assertTrue(self.page.locator('#marker-tooltip').is_visible())
        self.assertIn('Тестовая соседняя локация', self.page.locator('#marker-tooltip').inner_text())
        marker.hover()
        self.assertTrue(self.page.locator('#marker-tooltip').is_hidden(), 'Only the selected location suppresses its tooltip')
        self.assertIsNone(marker.get_attribute('aria-describedby'))
        self.assertIn('selected', marker.get_attribute('class'))
        self.assertTrue(marker.evaluate("e=>e.matches(':hover')"), 'Selected hover/rings still receive native hover')
        self.page.locator('#dossier-fold').click()
        marker.hover()
        self.assertTrue(self.page.locator('#marker-tooltip').is_hidden())
        self.page.locator('#dossier-close').click()
        marker.hover()
        self.assertTrue(self.page.locator('#marker-tooltip').is_hidden())
        self.assertIn('selected', marker.get_attribute('class'))
        peer.hover()
        self.assertTrue(self.page.locator('#marker-tooltip').is_visible(), 'Unselected hover is not globally disabled')
        self.clean()
    def test_03_same_native_marker_click_reopens_and_unfolds_dossier(self):
        self.boot()
        self.select()
        marker=self.page.locator('.map-marker[data-location-id="test-court-location"]')
        self.page.locator('#dossier-fold').click()
        marker.click()
        self.assertTrue(self.page.locator('#dossier-body').is_visible(), 'Reselecting the same marker must unfold its content')
        self.assertEqual(self.page.locator('#dossier-fold').get_attribute('aria-expanded'), 'true')
        self.assertNotIn('folded', self.page.locator('#dossier').get_attribute('class'))
        self.page.locator('#dossier-fold').click()
        self.page.locator('#dossier-close').click()
        marker.click()
        self.assertTrue(self.page.locator('#dossier').is_visible())
        self.assertTrue(self.page.locator('#dossier-body').is_visible())
        self.assertEqual(self.page.evaluate('window.fixtureSelected'), 'test-court-location')
        self.assertEqual(self.page.evaluate('typeof window.ui.unfoldDossier'), 'function', 'Parent selection API needs an explicit unfold seam')
        self.page.locator('#dossier-fold').click()
        self.page.evaluate('window.ui.unfoldDossier()')
        self.assertTrue(self.page.locator('#dossier-body').is_visible())
        self.clean()
    def test_04_desktop_layers_reopen_without_overlapping_or_clearing_selection(self):
        self.boot()
        self.select()
        self.assertTrue(self.page.locator('#layers').is_hidden())
        opener=self.page.locator('#layers-open')
        self.assertTrue(opener.is_visible(), 'Auto-hidden desktop layers need the same return affordance as the registry')
        opener.click()
        self.assertTrue(self.page.locator('#layers').is_visible())
        self.assertTrue(self.page.locator('#dossier').is_hidden(), 'Right-side panels are mutually exclusive')
        self.assertTrue(opener.is_hidden())
        self.assertEqual(self.page.evaluate('window.fixtureSelected'), 'test-court-location')
        self.assertIn('selected', self.page.locator('.map-marker[data-location-id="test-court-location"]').get_attribute('class'))
        self.page.locator('#layers-close').click()
        self.assertTrue(self.page.locator('#layers').is_hidden())
        self.assertTrue(opener.is_visible())
        self.page.locator('#nav-close').click()
        self.assertTrue(self.page.locator('#nav-open').is_visible())
        self.page.locator('#nav-open').click()
        self.assertTrue(self.page.locator('#navigation').is_visible())
        opener.click()
        self.page.locator('.map-marker[data-location-id="test-court-location"]').click()
        self.assertTrue(self.page.locator('#dossier').is_visible())
        self.assertTrue(self.page.locator('#layers').is_hidden())
        self.assertTrue(opener.is_visible())
        box=opener.bounding_box()
        dossier=self.page.locator('#dossier').bounding_box()
        self.assertGreaterEqual(box['height'], 44)
        self.assertGreaterEqual(dossier['y'], box['y']+box['height']+8, 'The corrected top-right return control occupies its own row above the dossier')
        self.clean()
    def test_05_dossier_border_matches_registry_neutral_metal_not_affiliation(self):
        self.boot()
        self.select()
        styles=self.page.evaluate("""()=>{
            const c=s=>getComputedStyle(document.querySelector(s));
            return {navigation:c('#navigation').borderTopColor,dossier:c('#dossier').borderTopColor,
                faction:c('#dossier-faction').color,factionBorder:c('#dossier-faction').borderColor,
                factionVariable:document.querySelector('#dossier').style.getPropertyValue('--dossier-faction-color')};
        }""")
        print('Neutral panel / exact affiliation:', styles)
        self.assertEqual(styles['dossier'], styles['navigation'], 'Only the outer panel border loses faction coloring')
        self.assertEqual(styles['faction'], 'rgb(99, 144, 150)')
        self.assertEqual(styles['factionBorder'], styles['faction'])
        self.assertEqual(styles['factionVariable'], '#639096')
        self.clean()
    def test_06_chronicle_noble_sources_start_on_next_line_after_open_dossier(self):
        self.boot()
        self.page.evaluate("window.chronicleUI.open('nobles')")
        button=self.page.locator('.noble-card button[data-noble-id="test-court-noble"]')
        source=self.page.locator('.noble-card a').first
        button_box=button.bounding_box()
        source_box=source.bounding_box()
        self.assertGreaterEqual(source_box['y'], button_box['y']+button_box['height'], 'Source links must begin on the next line, not beside Open dossier')
        wrapper=source.locator('..')
        self.assertIn('chronicle-source-links', wrapper.get_attribute('class') or '')
        self.assertEqual(wrapper.evaluate('e=>getComputedStyle(e).display'), 'block')
        self.assertEqual(source.get_attribute('rel'), 'noopener noreferrer')
        self.page.screenshot(path=str(ARTIFACTS/'06-chronicle-sources.png'))
        self.clean()
    def test_07_chronicle_council_button_uses_optional_parent_callback(self):
        self.boot()
        self.page.evaluate('window.chronicleUI.open()')
        self.page.locator('#chronicle-council').click()
        self.assertEqual(self.page.evaluate('window.calls'), [['council']], 'Council is owned by the parent; Chronicle only routes the callback')
        # The old one-argument signature remains safe even with static Council.
        self.page.evaluate("async()=>{const {initChronicle}=await import('./assets/js/chronicle.mjs');window.chronicleUI=initChronicle(()=>window.fixtureData);}")
        self.page.locator('#chronicle-council').click()
        self.clean()
    def test_08_collapsed_object_summary_preserves_author_title_with_explicit_owner_only(self):
        data=snapshot()
        data['locations'][0]['objects']=[
            {'id':'test-owner-unset','type':'building','name':'Авторское название без владельца'},
            {'id':'test-owner-empty','type':'building','name':'Авторское название пустое','owner':'  \t '},
            {'id':'test-owner-assigned','type':'building','name':'Авторское название с владельцем','owner':'  Авторский хранитель  ',
             'faction':'silverlaine','description':'Авторское описание.\nВторая строка.',
             'modifiers':[{'id':'test-plus','kind':'bonus','text':'Бонус автора +3'},
                          {'id':'test-minus','kind':'penalty','text':'Штраф автора −2'}]},
        ]
        self.boot(data)
        before=self.page.evaluate('JSON.stringify(window.fixtureData)')
        self.select()
        for item in data['locations'][0]['objects']:
            card=self.page.locator(f'.object-card[data-object-id="{item["id"]}"]')
            self.assertFalse(card.evaluate('e=>e.open'))
            self.assertEqual(card.locator('.object-icon svg').get_attribute('viewBox'), '0 0 24 24', 'Object summary uses its type, not a faction shield')
            self.assertEqual(card.locator('.object-icon .faction-shield').count(), 0)
            self.assertEqual(card.locator('.object-title').text_content(), item['name'])
            self.assertEqual(card.locator('.object-faction-badge').count(), 1)
            self.assertEqual(card.locator('.object-ownership').count(), 0, 'Do not repeat faction and owner in an expanded ownership line')
            owner=card.locator('.object-owner-badge')
            expected=item.get('owner','').strip()
            self.assertEqual(owner.count(), int(bool(expected)), 'Unset/whitespace object owner never inherits the location owner')
            if expected:
                self.assertEqual(owner.text_content(), expected)
                self.assertTrue(owner.is_visible(), 'Explicit owner is visible while collapsed')
        assigned=self.page.locator('.object-card[data-object-id="test-owner-assigned"]')
        self.assertEqual(assigned.locator('.object-faction-badge').text_content(), next(f['name'] for f in data['factions'] if f['id']=='silverlaine'))
        assigned.locator('summary').click()
        self.assertEqual(assigned.locator('.object-description').text_content(), 'Авторское описание.\nВторая строка.')
        self.assertEqual(assigned.locator('.modifier.bonus').evaluate('e=>getComputedStyle(e).color'), 'rgb(94, 170, 120)')
        self.assertEqual(assigned.locator('.modifier.penalty').evaluate('e=>getComputedStyle(e).color'), 'rgb(211, 121, 120)')
        self.assertEqual(assigned.locator('.object-faction-badge').evaluate('e=>getComputedStyle(e).color'), 'rgb(147, 167, 152)')
        assigned.locator('[data-object-edit]').click()
        assigned.locator('[data-object-delete]').click()
        self.assertEqual(self.page.evaluate('window.calls'), [['edit-object','test-court-location','test-owner-assigned'],['delete-object','test-court-location','test-owner-assigned']])
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before)
        self.page.screenshot(path=str(ARTIFACTS/'08-object-summary.png'))
        self.clean()
    def test_09_registry_and_layer_rows_use_immediate_shields_for_every_actual_faction(self):
        data=snapshot()
        template=copy.deepcopy(data['locations'][0])
        data['locations']=[]
        for faction in data['factions']:
            location=copy.deepcopy(template)
            location.update(id='test-row-'+faction['id'],name='Тестовый реестр '+faction['id'],faction=faction['id'])
            data['locations'].append(location)
        unknown=copy.deepcopy(template)
        unknown.update(id='test-unknown-row',name='Тест неизвестной принадлежности',faction=None,provenance={'affiliationStatus':'unknown'})
        data['locations'].append(unknown)
        data['nobles'].append({'id':'test-no-house','name':'Тест без дома','house':None})
        self.boot(data)
        for faction in data['factions']:
            for selector in [f'.faction-tree[data-faction-id="{faction["id"]}"] > summary .group-heading',f'.faction-row[data-faction-id="{faction["id"]}"]']:
                row=self.page.locator(selector)
                shield=row.locator('svg.faction-shield')
                self.assertEqual(shield.count(),1,'Every actual faction row gets the shared heraldry, not a generic crest or color swatch')
                self.assertEqual(shield.get_attribute('data-faction-id'), faction['id'])
                self.assertEqual(shield.get_attribute('viewBox'),'0 0 60 72')
                box=shield.bounding_box()
                self.assertGreater(box['width'],0)
                self.assertLessEqual(box['width'],24,'Registry shields stay in the existing row icon track')
                self.assertEqual(row.locator('img.faction-crest').count(),0)
                if faction['parent'] is None and faction['id']!='gilneas':
                    self.assertFalse(any('gilneas-royal-symbol' in (s or '') for s in shield.locator('image').evaluate_all('nodes=>nodes.map(e=>e.getAttribute("href"))')))
        self.assertEqual(self.page.locator('.faction-tree[data-affiliation="unknown"] > summary .group-heading .faction-shield').count(),0,'Unknown registry groups stay plain')
        self.page.locator('#filter-nobles').click()
        house=self.page.locator('.noble-row[data-noble-id="test-court-noble"] .faction-shield')
        self.assertEqual(house.get_attribute('data-faction-id'),'crowley')
        self.assertEqual(self.page.locator('.noble-row[data-noble-id="test-no-house"] svg').count(),0,'No house does not borrow a crest')
        self.clean()
    def test_10_mobile_dock_keeps_mutual_panels_and_compact_named_fold(self):
        for size in [{'width':390,'height':844},{'width':844,'height':390}]:
            self.boot(size=size)
            self.assertTrue(self.page.locator('#layers-open').is_hidden())
            self.assertTrue(self.page.locator('#mobile-dock').is_visible())
            self.page.locator('#mobile-layers').click()
            self.assertTrue(self.page.locator('#layers').is_visible())
            self.page.locator('#mobile-nav').click()
            self.assertTrue(self.page.locator('#navigation').is_visible())
            self.assertTrue(self.page.locator('#layers').is_hidden())
            self.select()
            self.assertTrue(self.page.locator('#dossier').is_visible())
            self.assertTrue(self.page.locator('#navigation').is_hidden())
            self.page.locator('#dossier-fold').click()
            self.assertTrue(self.page.locator('#dossier-body').is_hidden())
            box=self.page.locator('#dossier').bounding_box()
            self.assertLessEqual(box['height'],48,str(size))
            self.assertEqual(self.page.locator('#dossier .dossier-head').bounding_box()['height'],44)
            self.assertTrue(self.page.locator('.dossier-header-name').is_visible())
            self.page.locator('#mobile-layers').click()
            self.assertTrue(self.page.locator('#dossier').is_hidden())
            self.assertEqual(self.page.evaluate('window.fixtureSelected'),'test-court-location')
            self.page.locator('#mobile-dossier').click()
            self.assertTrue(self.page.locator('#dossier').is_visible())
            self.assertTrue(self.page.locator('#layers').is_hidden())
            self.page.locator('.map-marker[data-location-id="test-court-location"]').click()
            self.assertTrue(self.page.locator('#dossier-body').is_visible())
            self.page.screenshot(path=str(ARTIFACTS/f'10-mobile-{size["width"]}x{size["height"]}.png'))
            self.clean()

    def test_11_real_bootstrap_native_selection_fold_reopen_and_layers(self):
        self.boot(real=True)
        location_id=self.page.evaluate("window.gilneasApp.getData().locations.find(l=>l.id==='gilneas-city')?.id||window.gilneasApp.getData().locations[0].id")
        before=self.page.evaluate('JSON.stringify(window.gilneasApp.getData())')
        self.page.evaluate('id=>window.gilneasApp.selectId(id)',location_id)
        marker=self.page.locator(f'.map-marker[data-location-id="{location_id}"]')
        marker.hover()
        self.assertTrue(self.page.locator('#marker-tooltip').is_hidden())
        self.page.locator('#dossier-fold').click()
        self.assertTrue(self.page.locator('#dossier-body').is_hidden())
        self.assertLessEqual(self.page.locator('#dossier').bounding_box()['height'],48)
        self.page.locator('#dossier-close').click()
        marker.click()
        self.assertTrue(self.page.locator('#dossier').is_visible())
        self.assertTrue(self.page.locator('#dossier-body').is_visible())
        self.page.locator('#layers-open').click()
        self.assertTrue(self.page.locator('#layers').is_visible())
        self.assertTrue(self.page.locator('#dossier').is_hidden())
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),location_id)
        marker.click()
        self.assertTrue(self.page.locator('#dossier-body').is_visible())
        self.assertEqual(self.page.evaluate('JSON.stringify(window.gilneasApp.getData())'),before)
        self.page.screenshot(path=str(ARTIFACTS/'11-real-native.png'))
        self.clean()
    def test_12_native_dossier_scroll_keeps_44px_header_above_content(self):
        self.boot()
        self.select()
        dossier=self.page.locator('#dossier')
        before=self.page.locator('#dossier .dossier-head').bounding_box()
        self.page.mouse.move(before['x']+80,before['y']+100)
        self.page.mouse.wheel(0,900)
        self.page.wait_for_function("document.querySelector('#dossier').scrollTop>0",polling=50)
        header=self.page.locator('#dossier .dossier-head').bounding_box()
        self.assertAlmostEqual(header['y'],before['y'],delta=1)
        self.assertEqual(header['height'],44)
        self.page.locator('#dossier-fold').click()
        self.assertTrue(self.page.locator('#dossier-body').is_hidden())
        self.assertLessEqual(dossier.bounding_box()['height'],48)
        self.clean()
    def test_13_shared_type_catalog_drives_all_object_icons_and_new_map_types_without_changing_legacy_glyphs(self):
        self.boot()
        definitions=self.page.evaluate("""async()=>{
            const {TYPE_DEFINITIONS}=await import('./assets/js/object-types.mjs');
            const template=structuredClone(window.fixtureData.locations[0]);
            window.fixtureData.locations=TYPE_DEFINITIONS.map((d,i)=>({...structuredClone(template),
                id:'test-type-'+d.id,name:'Авторское название '+d.id,type:d.id,capital:false,
                x:1400+i*12,y:3300,objects:[]}));
            window.fixtureData.locations[0].objects=TYPE_DEFINITIONS.map(d=>({id:'test-object-'+d.id,
                type:d.id,name:'Авторский объект '+d.id,owner:''}));
            window.ui.render();
            return TYPE_DEFINITIONS;
        }""")
        self.assertGreaterEqual(len(definitions),30)
        self.select('test-type-city')
        before=self.page.evaluate('JSON.stringify(window.fixtureData)')
        legacy={'city','settlement','estate','fortress','district','harbor','forest','mine','landmark','building','resource'}
        shield='M4 3H20V12C20 17 16 20 12 22 8 20 4 17 4 12Z M8 8H16 M12 5V17'
        for definition in definitions:
            kind=definition['id']
            card=self.page.locator(f'.object-card[data-object-id="test-object-{kind}"]')
            symbol=card.locator('.object-icon svg')
            self.assertEqual(symbol.get_attribute('data-type'),kind,'Object icon must come from the shared catalog')
            self.assertEqual(symbol.locator('path').get_attribute('d'),definition['path'])
            self.assertEqual(card.locator('.object-title').text_content(),'Авторский объект '+kind)
            marker=self.page.locator(f'.map-marker[data-location-id="test-type-{kind}"]')
            # Buildings now use their approved functional house glyph.
            # Landmark/resource legacy map fallback geometry stays unchanged.
            expected=shield if kind in {'landmark','resource'} else definition['path']
            self.assertEqual(marker.locator('svg path').get_attribute('d'),expected,'Legacy location geometry must remain exact; new kinds use catalog geometry')
            if kind not in legacy:
                self.assertEqual(marker.locator('svg').get_attribute('data-type'),kind)
            self.assertEqual(self.page.locator(f'.location-row[data-location-id="test-type-{kind}"] .location-type').text_content(),definition['label'])
        # New location types also use the shared name in both dossier identities.
        self.select('test-type-farm')
        self.assertEqual(self.page.locator('#dossier-type').text_content(),'Ферма')
        self.assertIn('Ферма',self.page.locator('#dossier-subtitle').text_content())
        self.assertEqual(self.page.locator('#dossier-title').text_content(),'Авторское название farm')
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'),before)
        self.clean()
    def test_14_map_region_names_are_never_visible_without_changing_author_metadata(self):
        self.boot(real=True)
        labels=self.page.evaluate('JSON.stringify(window.gilneasApp.getData().meta.labels)')
        self.assertNotEqual(labels,'[]')
        self.assertTrue(self.page.locator('#region-labels').is_hidden(), 'Regional map captions must disappear, not author metadata')
        self.page.locator('label:has(#show-labels)').click()
        self.assertTrue(self.page.locator('#region-labels').is_hidden())
        self.assertIn('show-labels',self.page.locator('#world').get_attribute('class'))
        self.assertEqual(self.page.evaluate('JSON.stringify(window.gilneasApp.getData().meta.labels)'),labels)
        self.clean()
    def test_15_map_caption_never_overlaps_registry_return_control_or_mobile_dock(self):
        for size in [{'width':1440,'height':1000},{'width':390,'height':844}]:
            self.boot(size=size)
            if size['width']==390:
                self.page.locator('#mobile-nav').click()
            self.page.locator('#nav-close').click()
            title=self.page.locator('.map-title').bounding_box()
            for selector in ['#nav-open','#mobile-dock']:
                control=self.page.locator(selector)
                if not control.is_visible():
                    continue
                box=control.bounding_box()
                overlap=min(title['x']+title['width'],box['x']+box['width'])>max(title['x'],box['x']) and min(title['y']+title['height'],box['y']+box['height'])>max(title['y'],box['y'])
                self.assertFalse(overlap,f'Map caption must not go behind {selector}: {size}')
            viewport=self.page.locator('#viewport').bounding_box()
            self.assertGreaterEqual(title['x'],viewport['x'])
            self.assertLessEqual(title['x']+title['width'],viewport['x']+viewport['width'])
            self.assertIn('ИСТОРИЯ КОРОЛЕВСТВА ДОЖДЕЙ',self.page.locator('.map-title').inner_text())
            self.assertIn('Глава I. Стена Седогрива',self.page.locator('.map-title').inner_text())
            self.page.screenshot(path=str(ARTIFACTS/f'15-map-caption-{size["width"]}.png'))
            self.clean()
    def label_metrics(self):
        return self.page.locator('.map-marker.selected .marker-label').evaluate("""e=>{
            const box=e.getBoundingClientRect(),viewport=document.querySelector('#viewport').getBoundingClientRect();
            const text=e.firstChild,characters=[];
            for(let i=0;i<text.length;i++){
                const range=document.createRange();range.setStart(text,i);range.setEnd(text,i+1);
                characters.push({text:text.data[i],rect:range.getBoundingClientRect().toJSON()});
            }
            const c=getComputedStyle(e);
            return {text:e.textContent,box:box.toJSON(),viewport:viewport.toJSON(),characters,
                overflow:c.overflow,mask:c.mask,clip:c.clip,clipPath:c.clipPath};
        }""")

    def assert_full_selected_label(self, expected):
        metrics=self.label_metrics()
        self.assertEqual(metrics['text'],expected)
        self.assertEqual(''.join(char['text'] for char in metrics['characters']),expected)
        box=metrics['box']
        view=metrics['viewport']
        self.assertGreaterEqual(box['left'],view['left']+7,'Selected label must not be clipped by the viewport left edge')
        self.assertLessEqual(box['right'],view['right']-7,'Selected label must not be clipped by the viewport right edge')
        self.assertGreaterEqual(box['top'],view['top']+7)
        self.assertLessEqual(box['bottom'],view['bottom']-7)
        for char in metrics['characters']:
            if not char['text'].strip():
                continue
            rect=char['rect']
            self.assertGreaterEqual(rect['left'],box['left']+9,char['text']+' is clipped inside its pill')
            self.assertLessEqual(rect['right'],box['right']-9,char['text']+' is clipped inside its pill')
            self.assertGreaterEqual(rect['top'],box['top']+1)
            self.assertLessEqual(rect['bottom'],box['bottom']-1)
        self.assertEqual([metrics['overflow'],metrics['mask'],metrics['clip'],metrics['clipPath']],['visible','none','auto','none'])

    def pan_selected_to(self,x,y):
        marker=self.page.locator('.map-marker.selected').bounding_box()
        self.page.mouse.move(marker['x']+marker['width']/2,marker['y']+marker['height']/2)
        self.page.mouse.down()
        self.page.mouse.move(x,y,steps=10)
        self.page.mouse.up()

    def test_16_all_selected_name_characters_fit_pill_and_viewport_after_native_pan_zoom(self):
        self.boot(real=True)
        self.page.evaluate("window.gilneasApp.selectId('northern-headlands');window.ui.setPanel('navigation',false);window.ui.setPanel('layers',false);window.ui.setPanel('dossier',false);window.ui.focusLocation('northern-headlands',false)")
        self.assert_full_selected_label('Северный каменистый мыс')
        view=self.page.locator('#viewport').bounding_box()
        self.pan_selected_to(view['x']+30,view['y']+view['height']/2)
        self.assert_full_selected_label('Северный каменистый мыс')
        self.page.screenshot(path=str(ARTIFACTS/'16-selected-left-edge.png'))
        self.pan_selected_to(view['x']+5,view['y']+view['height']/2)
        self.assert_full_selected_label('Северный каменистый мыс')
        self.pan_selected_to(view['x']+view['width']-30,view['y']+view['height']/2)
        self.assert_full_selected_label('Северный каменистый мыс')
        self.pan_selected_to(view['x']+view['width']-5,view['y']+view['height']/2)
        self.assert_full_selected_label('Северный каменистый мыс')
        self.page.mouse.move(view['x']+view['width']*.8,view['y']+view['height']*.5)
        self.page.mouse.wheel(0,-180)
        self.assert_full_selected_label('Северный каменистый мыс')
        self.page.evaluate("window.ui.focusLocation('northern-headlands',false)")
        self.assert_full_selected_label('Северный каменистый мыс')
        self.page.evaluate("window.ui.setPanel('navigation',true);window.ui.setPanel('dossier',true)")
        self.assert_full_selected_label('Северный каменистый мыс')
        # Maximum author name is a fixture only; no production data/ID mutation.
        data=snapshot()
        prefix='Тестовое название автора — '
        maximum=prefix+'Ж'*(160-len(prefix))
        self.assertEqual(len(maximum),160)
        data['locations'][0]['name']=maximum
        self.boot(data,size={'width':390,'height':844})
        self.select()
        self.page.evaluate("window.ui.setPanel('dossier',false);window.ui.focusLocation('test-court-location',false)")
        self.assert_full_selected_label(maximum)
        view=self.page.locator('#viewport').bounding_box()
        self.pan_selected_to(30,view['y']+view['height']*.35)
        self.assert_full_selected_label(maximum)
        self.page.screenshot(path=str(ARTIFACTS/'16-selected-maximum-mobile.png'))
        self.clean()
    def test_17_native_empty_map_click_clears_selection_but_drag_zoom_and_paint_do_not(self):
        self.boot(real=True)
        self.page.evaluate("window.gilneasApp.selectId('northern-headlands')")
        before=self.page.evaluate("({data:JSON.stringify(window.gilneasApp.getData()),storage:JSON.stringify(Object.entries(localStorage))})")
        view=self.page.locator('#viewport').bounding_box()
        point={'x':view['x']+view['width']*.5,'y':view['y']+view['height']*.8}
        self.page.mouse.move(point['x'],point['y'])
        self.page.mouse.wheel(0,-80)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'northern-headlands')
        self.page.mouse.down()
        self.page.mouse.move(point['x']+30,point['y']+20,steps=5)
        self.page.mouse.up()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'northern-headlands')
        self.page.evaluate('window.paintCalls=[];window.ui.setMapInteraction((point,event)=>window.paintCalls.push([point,event.type]))')
        self.page.mouse.click(point['x'],point['y'])
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'northern-headlands')
        self.assertEqual(self.page.evaluate('window.paintCalls.length'),1)
        self.page.mouse.move(point['x'],point['y'])
        self.page.keyboard.down('Alt')
        self.page.mouse.down()
        self.page.mouse.move(point['x']+40,point['y']+20,steps=4)
        self.page.mouse.up()
        self.page.keyboard.up('Alt')
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'northern-headlands')
        self.page.evaluate('window.ui.setMapInteraction(null)')
        self.page.locator('#dossier-fold').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'northern-headlands')
        self.page.mouse.click(point['x'],point['y'])
        self.assertIsNone(self.page.evaluate('window.gilneasApp.getSelectedId()'),'Native empty-space click clears parent view selection')
        self.assertEqual(self.page.locator('.map-marker.selected').count(),0)
        self.assertTrue(self.page.locator('#dossier').is_hidden())
        marker=self.page.locator('.map-marker[data-location-id="northern-headlands"]')
        marker.hover()
        self.assertTrue(self.page.locator('#marker-tooltip').is_visible(),'The newly unselected location keeps its tooltip')
        after=self.page.evaluate("({data:JSON.stringify(window.gilneasApp.getData()),storage:JSON.stringify(Object.entries(localStorage))})")
        self.assertEqual(before,after,'Deselection must not persist or rewrite source data')
        self.clean()

    def test_18_trusted_pinch_preserves_selection_and_next_empty_tap_clears(self):
        self.boot(size={'width':390,'height':844})
        self.select()
        self.page.evaluate("window.ui.setPanel('dossier',false)")
        session=self.context.new_cdp_session(self.page)
        session.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':5})
        def touches(kind,positions,ids=None):
            session.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':[
                {'x':x,'y':y,'id':ids[i] if ids else i+1,'radiusX':3,'radiusY':3,'force':1}
                for i,(x,y) in enumerate(positions)]})
            self.page.wait_for_timeout(25)
        touches('touchStart',[(155,290),(235,290)])
        touches('touchMove',[(125,290),(265,290)])
        touches('touchEnd',[(265,290)],ids=[2])
        touches('touchMove',[(145,310)])
        touches('touchEnd',[])
        self.assertEqual(self.page.evaluate('window.fixtureSelected'),'test-court-location')
        self.assertEqual(self.page.evaluate('window.calls'),[],'Pinch and remaining-finger pan never clear selection')
        touches('touchStart',[(195,560)])
        touches('touchEnd',[])
        self.page.wait_for_function('window.fixtureSelected===null',polling=50)
        self.assertEqual(self.page.evaluate('window.calls'),[['clear']])
        self.assertTrue(self.page.locator('#dossier').is_hidden())
        session.detach()
        self.clean()
    def test_19_each_real_selected_name_character_is_painted_above_neighbor_markers(self):
        self.boot(real=True)
        locations=self.page.evaluate('window.gilneasApp.getData().locations.map(l=>({id:l.id,name:l.name}))')
        observed=[]
        for location in locations:
            self.page.evaluate('id=>{window.gilneasApp.selectId(id);window.ui.focusLocation(id,false);}',location['id'])
            self.assert_full_selected_label(location['name'])
            covered=self.page.locator('.map-marker.selected .marker-label').evaluate("""e=>{
                const text=e.firstChild,covered=[]; e.style.pointerEvents='auto';
                for(let i=0;i<text.length;i++){
                    if(!text.data[i].trim())continue;
                    const range=document.createRange();range.setStart(text,i);range.setEnd(text,i+1);
                    const r=range.getBoundingClientRect(),at=document.elementFromPoint((r.left+r.right)/2,(r.top+r.bottom)/2);
                    if(at!==e)covered.push({character:text.data[i],index:i,by:at?.id||String(at?.className)});
                }
                e.style.pointerEvents='';return covered;
            }""")
            self.assertEqual(covered,[],location['id']+' label is internally covered by another map element')
            observed.append(location)
        self.assertEqual(len(observed),len(locations))
        (ARTIFACTS/'19-all-real-selected-labels.json').write_text(json.dumps(observed,ensure_ascii=False,indent=2))
        self.clean()


if __name__ == '__main__':
    unittest.main()
