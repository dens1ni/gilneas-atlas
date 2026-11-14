"""Real Chromium tests of the territory port; parent bootstrap is isolated.

Fixtures are test-only. Use the real Gilneas DOM, raster, UI camera, model,
Blob geometry worker, native pointer capture and local JSON storage.
"""
import functools
import json
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-territory-evidence')


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class TerritoryRevision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT)))
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
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000}, has_touch=True)
        self.page = self.context.new_page()
        self.errors = []
        self.console_errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.console_errors.append(message.text) if message.type == 'error' else None)
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
            status=200, content_type='application/javascript', body='// Territory fixture: isolate parent bootstrap.'))

    def tearDown(self):
        self.context.close()

    def boot(self, reload=False):
        if reload:
            self.page.reload(wait_until='networkidle')
        else:
            self.page.goto(self.url + '/index.html', wait_until='networkidle')
        self.page.evaluate("""async () => {
            window.territoryBootError = null;
            try {
                const M = await import('./assets/js/model.mjs');
                const T = await import('./assets/js/territories.mjs');
                const {initUI} = await import('./assets/js/ui.mjs');
                const baseline = M.normalizeData({version: 1, meta: {width: 3247, height: 4860,
                    image: 'assets/maps/gilneas-enhanced.webp', mist: 'assets/maps/inactive-mist.webp'},
                    factions: [{id: 'test-root', name: 'Тестовая держава', parent: null, color: '#ad4255'},
                        {id: '  test-house  ', name: 'Тестовый вассал', parent: 'test-root', color: '#559080'}],
                    locations: [{id: 'test-place', name: 'Тестовая точка', x: 2100, y: 3400, faction: 'test-root', objects: []}],
                    territories: [], nobles: [], sources: [{id: 0}, {id: '0'}],
                    territoryGrid: {version: 1, width: 203, height: 304, step: 16, mapWidth: 3247, mapHeight: 4860,
                        keys: ['test-root', '  test-house  '], cells: new Array(61712).fill(0), radius: 260,
                        provenance: {sources: [0, '0'], note: '  TEST ONLY  '}, future: {preserved: true}}});
                window.state = M.loadDraft(localStorage, baseline, 'territory-test-draft').data;
                window.commits = 0;
                window.toasts = [];
                window.canPlaceTest = ([x,y]) => x >= 0 && y >= 0 && x <= 3247 && y <= 4860 && !(x >= 1744 && x < 1776);
                window.ui = initUI({getData: () => state, getSelectedId: () => null,
                    onSelect: () => {}, onRenderTerritories: () => window.boundaries?.render()});
                const replaceData = next => {
                    const normalized = M.normalizeData(next);
                    M.saveDraft(localStorage, normalized, 'territory-test-draft');
                    window.state = normalized;
                    window.commits++;
                    ui.render();
                    window.boundaries?.render();
                    return state;
                };
                window.replaceTestData = replaceData;
                window.boundaries = T.initTerritories({getData: () => state, replaceData, ui,
                    canPlace: canPlaceTest, toast: message => toasts.push(message)});
                await window.boundaries.whenReady();
                ui.setPanel('navigation', false);
                ui.setPanel('layers', false);
                ui.home(false);
            } catch (error) { window.territoryBootError = String(error); }
        }""")
        self.assertIsNone(self.page.evaluate('window.territoryBootError'), 'initTerritories must boot the real port')
        self.page.wait_for_function("document.getElementById('base-map').naturalWidth > 0", polling=50)

    def map_screen(self, point):
        return self.page.evaluate("""point => {
            const camera = ui.getCamera(), rect = document.getElementById('viewport').getBoundingClientRect();
            return [rect.left + camera.x + point[0] * camera.scale, rect.top + camera.y + point[1] * camera.scale];
        }""", point)

    def native_stroke(self, start, end, steps=8):
        self.page.mouse.move(*self.map_screen(start))
        self.page.mouse.down()
        self.page.mouse.move(*self.map_screen(end), steps=steps)
        self.page.mouse.up()

    def test_01_native_interpolated_brush_commits_once_without_camera_drag(self):
        self.boot()
        self.page.evaluate('boundaries.open()')
        self.assertTrue(self.page.locator('#boundary-tools').is_visible())
        ids = ['boundary-tools', 'boundary-faction', 'boundary-mode', 'boundary-brush', 'boundary-radius',
               'boundary-generate', 'boundary-undo', 'boundary-redo', 'boundary-clear', 'boundary-save',
               'boundary-close', 'boundary-status']
        self.assertEqual(self.page.evaluate('(ids) => ids.filter(id => !document.getElementById(id))', ids), [])
        self.page.locator('#boundary-faction').select_option('  test-house  ')
        self.page.locator('#boundary-brush').fill('24')
        camera = self.page.evaluate('ui.getCamera()')
        before = self.page.evaluate('JSON.stringify(state)')
        self.page.mouse.move(*self.map_screen([1640, 3720]))
        self.page.mouse.down()
        self.page.mouse.move(*self.map_screen([1848, 3720]), steps=2)
        self.assertEqual(self.page.evaluate('JSON.stringify(state)'), before, 'live immutable data stays unchanged during a stroke')
        self.assertEqual(self.page.evaluate('commits'), 0)
        self.assertGreater(self.page.locator('#boundary-brush-preview rect').count(), 0)
        self.page.mouse.up()
        self.page.evaluate('boundaries.whenReady()')
        self.assertEqual(self.page.evaluate('commits'), 1)
        self.assertEqual(self.page.evaluate('ui.getCamera()'), camera)
        cells = self.page.evaluate('state.territoryGrid.cells')
        width = 203
        for x in range(102, 116):
            index = 232 * width + x
            self.assertEqual(cells[index], 0 if x in [109, 110] else 2, f'interpolated brush cell {x}')
        self.assertGreater(self.page.locator('#boundary-vector path[data-faction-id="  test-house  "]').count(), 0)
        self.assertEqual(self.page.locator('#boundary-vector').get_attribute('viewBox'), '0 0 3247 4860')
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_02_native_erase_undo_redo_reload_preserve_full_grid_extensions(self):
        self.boot()
        self.page.evaluate('boundaries.open()')
        self.page.locator('#boundary-faction').select_option('  test-house  ')
        self.page.locator('#boundary-brush').fill('24')
        self.native_stroke([1640, 3720], [1848, 3720], steps=4)
        painted = self.page.evaluate('state.territoryGrid')
        self.page.locator('#boundary-mode').select_option('erase')
        self.native_stroke([1672, 3720], [1704, 3720])
        erased = self.page.evaluate('state.territoryGrid')
        self.assertNotEqual(erased['cells'], painted['cells'])
        self.assertFalse(self.page.locator('#boundary-undo').is_disabled())
        self.page.locator('#boundary-undo').click()
        self.assertEqual(self.page.evaluate('state.territoryGrid'), painted)
        self.page.locator('#boundary-redo').click()
        self.assertEqual(self.page.evaluate('state.territoryGrid'), erased)
        self.assertEqual(self.page.evaluate('commits'), 4, 'each history action commits one immutable snapshot')
        self.assertEqual(erased['provenance'], {'sources': [0, '0'], 'note': '  TEST ONLY  '})
        self.assertTrue(erased['future']['preserved'])
        snapshot = self.page.evaluate('state')
        self.boot(reload=True)
        self.assertEqual(self.page.evaluate('state'), snapshot)
        self.assertEqual(self.page.evaluate('commits'), 0, 'reload must not write a draft')
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_03_clear_generate_radius_validation_and_save_use_atomic_grid_history(self):
        self.boot()
        self.page.evaluate('boundaries.open()')
        self.page.locator('#boundary-brush').fill('24')
        self.native_stroke([1640, 3720], [1672, 3720])
        painted = self.page.evaluate('state.territoryGrid')
        self.page.on('dialog', lambda dialog: dialog.accept())
        self.page.locator('#boundary-clear').click()
        self.assertTrue(self.page.evaluate('state.territoryGrid.cells.every(v => v === 0)'))
        self.page.locator('#boundary-undo').click()
        self.assertEqual(self.page.evaluate('state.territoryGrid'), painted)
        self.page.locator('#boundary-radius').fill('80')
        self.page.locator('#boundary-generate').click()
        generated = self.page.evaluate('state.territoryGrid')
        self.assertEqual(generated['radius'], 80)
        self.assertNotEqual(generated['cells'], painted['cells'])
        expected = self.page.evaluate("""async () => {
            const {generate} = await import('./assets/js/territory-engine.mjs');
            return generate(state.locations, state.factions, 80, state.meta, canPlaceTest).cells;
        }""")
        self.assertEqual(generated['cells'], expected)
        self.assertEqual(generated['provenance'], painted['provenance'])
        self.assertEqual(generated['future'], painted['future'])
        before = self.page.evaluate('JSON.stringify(state)')
        commits = self.page.evaluate('commits')
        self.page.locator('#boundary-radius').fill('601')
        self.page.locator('#boundary-generate').click()
        self.assertEqual(self.page.evaluate('JSON.stringify(state)'), before)
        self.assertEqual(self.page.evaluate('commits'), commits)
        self.assertIn('40', self.page.locator('#boundary-status').inner_text())
        self.page.locator('#boundary-save').click()
        self.assertEqual(self.page.evaluate('commits'), commits + 1)
        self.assertEqual(self.page.evaluate('JSON.parse(localStorage.getItem("territory-test-draft"))'), self.page.evaluate('state'))
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_04_camera_mode_and_modifiers_pan_without_changing_cells(self):
        self.boot()
        self.page.evaluate('boundaries.open()')
        original = self.page.evaluate('state.territoryGrid.cells')
        self.page.locator('#boundary-mode').select_option('camera')
        camera = self.page.evaluate('ui.getCamera()')
        self.native_stroke([1600, 3700], [1720, 3760])
        after = self.page.evaluate('ui.getCamera()')
        self.assertNotEqual(after, camera, 'camera mode must hand the pointer back to real UI pan')
        self.page.locator('#boundary-mode').select_option('paint')
        for key in ['Alt', 'Meta']:
            camera = self.page.evaluate('ui.getCamera()')
            self.page.keyboard.down(key)
            self.native_stroke([1600, 3700], [1680, 3740])
            self.page.keyboard.up(key)
            self.assertNotEqual(self.page.evaluate('ui.getCamera()'), camera)
        self.assertEqual(self.page.evaluate('state.territoryGrid.cells'), original)
        self.assertEqual(self.page.evaluate('commits'), 0)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_05_native_two_finger_pinch_in_paint_mode_cancels_preview_not_owned_cells(self):
        self.boot()
        self.page.evaluate('boundaries.open()')
        start = self.map_screen([1640, 3720])
        camera = self.page.evaluate('ui.getCamera()')
        original = self.page.evaluate('state.territoryGrid')
        cdp = self.context.new_cdp_session(self.page)
        first = {'x': start[0], 'y': start[1], 'id': 1}
        second = {'x': start[0] + 80, 'y': start[1] - 40, 'id': 2}
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [first]})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [first, second]})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [
            {**first, 'x': first['x'] - 45, 'y': first['y'] + 10},
            {**second, 'x': second['x'] + 55, 'y': second['y'] - 15}]})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        self.page.wait_for_timeout(70)
        self.assertGreater(self.page.evaluate('ui.getCamera().scale'), camera['scale'])
        self.assertEqual(self.page.evaluate('state.territoryGrid'), original)
        self.assertEqual(self.page.evaluate('commits'), 0, 'pinch must never persist its interrupted brush')
        self.assertEqual(self.page.locator('#boundary-brush-preview rect').count(), 0)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_06_actual_path2d_fills_have_shared_reverse_seams_holes_and_sovereign_union(self):
        self.boot()
        result = self.page.evaluate("""async () => {
            const S = await import('./assets/js/smooth-territories.mjs');
            const w = 12, h = 10, cells = [];
            for (let y=0; y<h; y++) for (let x=0; x<w; x++) cells.push(x<6 ? 1 : 2);
            cells[4*w+3] = 0; cells[5*w+3] = 0;
            const layer = {version:1,width:w,height:h,step:16,mapWidth:192,mapHeight:160,
                keys:['test-root','test-vassal'],cells,radius:260};
            const chains = S.geometry(layer), p = S.paths(layer,chains), u = S.paths(layer,chains,[0,1,1]);
            const ctx = document.createElement('canvas').getContext('2d');
            let centreFailures=[], overlaps=0, unionFailures=0, svgDisagreements=0;
            const svg = p.map(region => new Path2D(region.d));
            for(let y=0;y<h;y++) for(let x=0;x<w;x++) {
                const value=cells[y*w+x], point=[x*16+8,y*16+8];
                const hits=p.map(region=>ctx.isPointInPath(region.path,...point,'evenodd'));
                if(hits.filter(Boolean).length !== (value ? 1 : 0) || (value && !hits[value-1])) centreFailures.push([x,y,value,hits]);
            }
            // True Canvas coverage, not a polyline approximation or mock Path2D.
            for(let y=1.35;y<160;y+=2.37) for(let x=1.13;x<192;x+=2.51) {
                const hits=p.map(region=>ctx.isPointInPath(region.path,x,y,'evenodd'));
                if(hits.every(Boolean)) overlaps++;
                if(ctx.isPointInPath(u[0].path,x,y,'evenodd') !== hits.some(Boolean)) unionFailures++;
                p.forEach((region,i)=>{if(ctx.isPointInPath(svg[i],x,y,'evenodd')!==hits[i]) svgDisagreements++;});
            }
            const shared=chains.find(c=>c.right && c.left);
            const segment=shared.segments[0];
            const forward='C'+[...segment.c1,...segment.c2,...segment.b].join(' ');
            const reverse='C'+[...segment.c2,...segment.c1,...segment.a].join(' ');
            const reverseExact=p[shared.right-1].d.includes(forward)&&p[shared.left-1].d.includes(reverse);
            const checker={...layer,width:2,height:2,mapWidth:32,mapHeight:32,cells:[1,2,2,1]};
            const checkerPaths=S.paths(checker);
            const checkerHits=checker.cells.map((v,i)=>checkerPaths.map(r=>ctx.isPointInPath(r.path,(i%2)*16+8,Math.floor(i/2)*16+8,'evenodd')));
            return {centreFailures,overlaps,unionFailures,svgDisagreements,reverseExact,checkerHits,
                unionVassalEmpty:u[1].d==='',hole:ctx.isPointInPath(u[0].path,56,72,'evenodd')};
        }""")
        self.assertEqual(result['centreFailures'], [])
        self.assertEqual(result['overlaps'], 0)
        self.assertEqual(result['unionFailures'], 0)
        self.assertEqual(result['svgDisagreements'], 0)
        self.assertTrue(result['reverseExact'])
        self.assertTrue(result['unionVassalEmpty'])
        self.assertFalse(result['hole'])
        self.assertEqual(result['checkerHits'], [[True,False],[False,True],[False,True],[True,False]])
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_07_cached_selection_visibility_and_location_crud_never_recompute_or_regenerate_cells(self):
        self.boot()
        self.page.evaluate('boundaries.open()')
        self.page.locator('#boundary-brush').fill('24')
        self.native_stroke([1640, 3720], [1848, 3720])
        self.page.evaluate('boundaries.whenReady()')
        original = self.page.evaluate('state.territoryGrid')
        self.page.evaluate("window.pathBefore = document.querySelector('#boundary-vector > path'); window.callsBefore = boundaries.getPerformance().geometryCalls")
        self.page.locator('#faction-list [data-faction-id="  test-house  "]').evaluate('node => node.click()')
        self.page.evaluate('boundaries.render()')
        self.assertTrue(self.page.evaluate('window.pathBefore === document.querySelector("#boundary-vector > path")'))
        self.assertEqual(self.page.evaluate('boundaries.getPerformance().geometryCalls'), self.page.evaluate('callsBefore'))
        self.page.evaluate('boundaries.close(); document.getElementById("show-territories").checked=false; boundaries.render()')
        self.assertIsNotNone(self.page.locator('#boundary-vector').get_attribute('hidden'))
        self.page.evaluate('document.getElementById("show-territories").checked=true; boundaries.render()')
        self.assertIsNone(self.page.locator('#boundary-vector').get_attribute('hidden'))
        self.page.evaluate("""async () => {
            const M=await import('./assets/js/model.mjs');
            replaceTestData(M.updateLocation(state,'test-place',{x:2340,y:3580,description:'  AUTHOR TEXT  '}));
            ui.zoom(1.2); boundaries.render();
        }""")
        self.page.evaluate('boundaries.whenReady()')
        self.assertEqual(self.page.evaluate('state.territoryGrid'), original)
        self.assertEqual(self.page.evaluate('boundaries.getPerformance().geometryCalls'), self.page.evaluate('callsBefore'))
        self.assertTrue(self.page.evaluate('window.pathBefore === document.querySelector("#boundary-vector > path")'))
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_08_incoming_snapshot_interrupts_stroke_without_overwriting_import_or_retaining_old_history(self):
        self.boot()
        self.page.evaluate('boundaries.open()')
        self.page.locator('#boundary-brush').fill('24')
        self.native_stroke([1640, 3720], [1680, 3720])
        self.page.mouse.move(*self.map_screen([1800, 3780]))
        self.page.mouse.down()
        self.page.mouse.move(*self.map_screen([1870, 3780]), steps=4)
        imported = self.page.evaluate("""() => {
            const next=structuredClone(state);
            next.territoryGrid.cells.fill(0);
            next.territoryGrid.cells[0]=2;
            replaceTestData(next);
            return state;
        }""")
        commits = self.page.evaluate('commits')
        self.page.mouse.up()
        self.page.evaluate('boundaries.whenReady()')
        self.assertEqual(self.page.evaluate('state'), imported)
        self.assertEqual(self.page.evaluate('commits'), commits)
        self.assertTrue(self.page.locator('#boundary-undo').is_disabled())
        self.assertEqual(self.page.locator('#boundary-brush-preview rect').count(), 0)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_09_unused_new_faction_key_can_be_added_deleted_and_readded_without_repainting(self):
        self.boot()
        self.page.evaluate('boundaries.open()')
        original = self.page.evaluate('state.territoryGrid.cells')
        self.page.evaluate("""async () => {
            const M=await import('./assets/js/model.mjs');
            replaceTestData(M.upsertFaction(state,{id:'test-new',name:'Тестовый новый дом',color:'#778899',parent:'test-root'}));
        }""")
        self.assertIn('test-new', self.page.evaluate('boundaries.getGrid().keys'))
        self.page.evaluate("""async () => {
            const M=await import('./assets/js/model.mjs');
            replaceTestData(M.deleteFaction(state,'test-new'));
        }""")
        self.assertNotIn('test-new', self.page.evaluate('boundaries.getGrid().keys'))
        self.assertEqual(self.page.evaluate('state.territoryGrid.cells'), original)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_10_native_stroke_defers_worker_and_ignores_stale_geometry_revision(self):
        self.boot()
        self.page.evaluate('boundaries.open(); window.geometryCallsBefore=boundaries.getPerformance().geometryCalls')
        self.page.locator('#boundary-brush').fill('48')
        self.page.mouse.move(*self.map_screen([1600, 3680]))
        self.page.mouse.down()
        self.page.mouse.move(*self.map_screen([1940, 3680]), steps=24)
        during = self.page.evaluate('boundaries.getPerformance()')
        self.assertEqual(during['geometryCalls'], self.page.evaluate('geometryCallsBefore'), 'no graph construction during a live stroke')
        self.page.mouse.up()
        self.page.evaluate('boundaries.whenReady()')
        sample = self.page.evaluate('boundaries.getPerformance()')
        self.assertGreater(sample['changedCells'], 30)
        self.assertLess(sample['brushHandlerMaxMs'], 100)
        self.assertEqual(sample['geometryCalls'], self.page.evaluate('geometryCallsBefore') + 1)
        self.assertEqual(sample['revision'], self.page.evaluate('boundaries.getPerformance().revision'))
        (ARTIFACTS / 'native-brush-performance.json').write_text(json.dumps(sample, indent=2))
        self.page.evaluate("""async () => {
            const S=await import('./assets/js/smooth-territories.mjs');
            const original=S.SmoothTerritories.geometryAsync;
            window.slowJob = true;
            S.SmoothTerritories.geometryAsync = layer => {
                const compute=original(layer);
                return window.slowJob ? new Promise(resolve => {window.slowJob=false; window.releaseGeometry=async()=>resolve(await compute);}) : compute;
            };
        }""")
        self.native_stroke([1640, 3760], [1740, 3760], steps=5)
        self.page.wait_for_function('typeof window.releaseGeometry === "function"')
        self.native_stroke([1840, 3790], [1940, 3790], steps=5)
        self.page.evaluate('window.releaseGeometry()')
        self.page.evaluate('boundaries.whenReady()')
        self.assertGreater(self.page.evaluate('boundaries.getPerformance().staleResults'), 0)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])

    def test_11_camera_mode_survives_close_reopen_and_canceled_stroke_keeps_snapshot(self):
        self.boot()
        self.page.evaluate('boundaries.open()')
        self.page.locator('#boundary-mode').select_option('camera')
        self.page.locator('#boundary-close').click()
        self.page.evaluate('boundaries.open()')
        camera = self.page.evaluate('ui.getCamera()')
        self.native_stroke([1600, 3700], [1680, 3740])
        self.assertNotEqual(self.page.evaluate('ui.getCamera()'), camera)
        self.page.locator('#boundary-mode').select_option('paint')
        before = self.page.evaluate('JSON.stringify(state)')
        self.page.mouse.move(*self.map_screen([1660, 3720]))
        self.page.mouse.down()
        self.page.mouse.move(*self.map_screen([1740, 3720]), steps=4)
        self.page.evaluate('window.dispatchEvent(new Event("blur"))')
        self.page.mouse.up()
        self.page.evaluate('boundaries.whenReady()')
        self.assertEqual(self.page.evaluate('JSON.stringify(state)'), before)
        self.assertEqual(self.page.evaluate('commits'), 0)
        self.assertEqual(self.page.locator('#boundary-brush-preview rect').count(), 0)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])


if __name__ == '__main__':
    unittest.main()
