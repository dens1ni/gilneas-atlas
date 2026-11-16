"""Vertical map-presentation tracer bullets with real HTML/CSS/raster assets.

Only the unfinished parent bootstrap is suppressed. Network holds exercise
actual browser image events; readiness is polled in the DOM, never networkidle.
Run: .../gilneas-venv/bin/python tests/test_court_map_presentation.py -v
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
ARTIFACTS = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-map-presentation-evidence')
NEW_BASE = 'assets/maps/gilneas-origins-enhanced.webp'
NEW_MIST = 'assets/maps/origins-inactive-mist.webp'
OLD_BASE = 'assets/maps/gilneas-enhanced.webp'
OLD_MIST = 'assets/maps/inactive-mist.webp'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class CourtMapPresentation(unittest.TestCase):
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
        self.page.set_default_timeout(8000)
        self.page_errors, self.console_errors, self.http_errors = [], [], []
        self.requests, self.expected_failures = [], set()
        self.page.on('pageerror', lambda error: self.page_errors.append(str(error)))
        self.page.on('console', lambda message: self.console_errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.http_errors.append([response.status, response.url]) if response.status >= 400 else None)
        self.page.on('request', lambda request: self.requests.append(request.url))
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(status=200, content_type='text/javascript', body=''))
        self.snapshot = json.loads((ROOT / 'assets/data/atlas.json').read_text())

    def tearDown(self):
        self.context.close()

    def boot(self, size=None):
        self.assertTrue((ROOT / 'assets/js/map-presentation.mjs').is_file(), 'The real map-presentation module is required')
        self.assertTrue((ROOT / 'assets/css/map-presentation.css').is_file(), 'The map-presentation stylesheet is required')
        if size:
            self.page.set_viewport_size(size)
        self.page.goto(self.url + '/index.html', wait_until='load')
        self.page.evaluate("""async snapshot => {
            if (!document.querySelector('link[href$="map-presentation.css"]')) {
                const link=document.createElement('link'); link.rel='stylesheet';
                link.href='./assets/css/map-presentation.css';
                const loaded=new Promise((resolve,reject)=>{link.onload=resolve;link.onerror=reject;});
                document.head.append(link); await loaded;
            }
            const {decorateIcons}=await import('./assets/js/icons.mjs'); decorateIcons();
            const {initMapPresentation}=await import('./assets/js/map-presentation.mjs');
            window.initMapPresentation=initMapPresentation;
            window.presentation=initMapPresentation();
            window.fixtureSnapshot=snapshot;
            window.renderFixture = next => {
                const world=document.querySelector('#world');
                world.style.width=`${next.meta.width}px`; world.style.height=`${next.meta.height}px`;
                for (const [id,url] of [['base-map',next.meta.image],['mist-map',next.meta.mist || 'assets/maps/inactive-mist.webp']]) {
                    const image=document.getElementById(id); image.src=url;
                    image.width=next.meta.width; image.height=next.meta.height;
                }
            };
        }""", self.snapshot)

    def hold(self, path):
        held = []
        captured = False

        def first_request(route):
            nonlocal captured
            if captured:
                route.continue_()
            else:
                captured = True
                held.append(route)

        self.page.route('**/' + path, first_request)
        return held

    def begin_prepare(self, snapshot=None):
        self.page.evaluate("""snapshot => {
            window.prepared=false; window.prepareError=null;
            window.preparation=window.presentation.prepare(snapshot).then(
                ()=>{window.prepared=true;}, error=>{window.prepareError=String(error.message);});
        }""", snapshot or self.snapshot)

    def wait_prepared(self):
        self.page.wait_for_function('window.prepared || window.prepareError', polling=50)
        self.assertIsNone(self.page.evaluate('window.prepareError'))
        self.assertTrue(self.page.evaluate('window.prepared'))

    def world_visible(self):
        return self.page.locator('#world').evaluate("e=>getComputedStyle(e).visibility==='visible' && getComputedStyle(e).opacity!=='0'")

    def reveal(self, snapshot=None):
        self.page.evaluate("""async snapshot => {
            window.renderFixture(snapshot);
            await window.presentation.reveal();
        }""", snapshot or self.snapshot)

    def assert_clean(self):
        self.assertEqual(self.page_errors, [])
        self.assertEqual([item for item in self.http_errors if item[1] not in self.expected_failures], [])
        if not self.expected_failures:
            self.assertEqual(self.console_errors, [])

    def test_01_held_base_stays_hidden_until_resources_and_explicit_geometry_reveal(self):
        held = self.hold(NEW_BASE)
        self.boot()
        self.begin_prepare()
        self.page.wait_for_function('window.presentation && !window.prepared', polling=50)
        self.assertEqual(len(held), 1, 'A real base-image request must be held, not a synthetic ready flag')
        loader = self.page.locator('#map-loading')
        self.assertTrue(loader.is_visible())
        self.assertEqual(loader.get_attribute('role'), 'status')
        self.assertEqual(loader.get_attribute('aria-live'), 'polite')
        self.assertIn('Разворачиваем королевскую карту', loader.inner_text())
        self.assertFalse(self.world_visible(), 'No world layer may flash while the base raster is held')
        self.page.evaluate("window.presentation.reveal().then(()=>window.earlyRevealed=true,()=>window.earlyRevealed=false)")
        self.page.wait_for_function('window.earlyRevealed !== undefined', polling=50)
        self.assertFalse(self.page.evaluate('window.earlyRevealed'))
        self.assertFalse(self.world_visible())
        self.assertNotRegex(loader.inner_text(), r'\d+\s*%')
        held.pop().fulfill(status=200, content_type='image/webp', path=str(ROOT / NEW_BASE))
        self.wait_prepared()
        self.assertTrue(loader.is_visible(), 'Resource readiness is not geometry readiness')
        self.assertFalse(self.world_visible(), 'Only the parent geometry gate may reveal the loaded map')
        self.reveal()
        self.assertTrue(self.world_visible())
        self.assertTrue(loader.is_hidden())
        self.assertFalse(self.page.evaluate("document.body.classList.contains('map-awaiting')"))
        self.assert_clean()
    def test_02_held_mist_blocks_raster_readiness_and_world_reveal(self):
        held = self.hold(NEW_MIST)
        self.boot()
        self.begin_prepare()
        self.page.wait_for_function("Array.from(document.images).every(image=>image.id!=='base-map' || !image.src) && !window.prepared", polling=50)
        self.assertEqual(len(held), 1)
        self.assertFalse(self.page.evaluate('window.prepared'))
        self.assertFalse(self.world_visible())
        self.assertIn('дымку', self.page.locator('#map-loading-stage').inner_text())
        held.pop().fulfill(status=200, content_type='image/webp', path=str(ROOT / NEW_MIST))
        self.wait_prepared()
        self.assertFalse(self.world_visible())
        self.reveal()
        self.assertTrue(self.world_visible())
        self.assert_clean()

    def test_03_failed_base_is_fail_closed_with_safe_error_and_native_reload_retry(self):
        failure_url = self.url + '/' + NEW_BASE
        self.expected_failures.add(failure_url)
        self.page.route('**/' + NEW_BASE, lambda route: route.fulfill(status=404, body='missing test raster'))
        self.boot()
        self.begin_prepare()
        self.page.wait_for_function('window.prepareError', polling=50)
        self.assertEqual(self.page.evaluate('typeof window.presentation.fail'), 'function', 'Initial load failures need an explicit fail-closed presentation')
        self.page.evaluate("window.presentation.fail(new Error('<img src=x onerror=window.bad=1>'))")
        loader = self.page.locator('#map-loading')
        self.assertTrue(loader.is_visible())
        self.assertFalse(self.world_visible())
        self.assertEqual(loader.get_attribute('data-state'), 'error')
        self.assertIn('Не удалось развернуть карту', loader.inner_text())
        self.assertIn('<img src=x onerror=window.bad=1>', loader.inner_text())
        self.assertIsNone(self.page.evaluate('window.bad'))
        self.assertEqual(loader.locator('img[src=x]').count(), 0)
        self.assertNotRegex(loader.inner_text(), r'\d+\s*%')
        retry = loader.locator('button')
        self.assertEqual(retry.inner_text(), 'Повторить загрузку')
        self.assertEqual(retry.get_attribute('type'), 'button')
        with self.page.expect_navigation(wait_until='domcontentloaded'):
            retry.click()
        self.assertEqual(self.page.url, self.url + '/index.html')
        self.assert_clean()
    def test_04_require_prepared_is_a_synchronous_url_pair_gate_without_io_or_dom_writes(self):
        held = self.hold(NEW_BASE)
        self.boot()
        self.assertEqual(self.page.evaluate('typeof window.presentation.requirePrepared'), 'function', 'Commit eligibility needs a synchronous prepared-resource gate')
        result = self.page.evaluate("""snapshot => {
            try { window.presentation.requirePrepared(snapshot); return 'accepted'; }
            catch (error) { return String(error.message); }
        }""", self.snapshot)
        self.assertNotEqual(result, 'accepted', 'Uncached resources must be rejected before a commit')
        self.begin_prepare()
        self.page.wait_for_function('!window.prepared', polling=50)
        self.assertEqual(len(held), 1)
        self.assertTrue(self.page.evaluate("""snapshot=>{
            try { window.presentation.requirePrepared(snapshot); return false; } catch { return true; }
        }""", self.snapshot), 'An in-flight image pair is not commit-ready')
        held.pop().fulfill(status=200, content_type='image/webp', path=str(ROOT / NEW_BASE))
        self.wait_prepared()
        before = self.page.evaluate("document.querySelector('#world').outerHTML")
        request_count = len(self.requests)
        edited = copy.deepcopy(self.snapshot)
        edited['meta'].update(width=3247, height=4860)
        edited['locations'][0]['description'] = 'Только тестовая правка без ввода-вывода.'
        result = self.page.evaluate("""snapshot => {
            const result=window.presentation.requirePrepared(snapshot);
            return {promise:Boolean(result && typeof result.then==='function')};
        }""", edited)
        self.assertFalse(result['promise'], 'Normal commits stay synchronous and perform no network work')
        resolved = copy.deepcopy(edited)
        resolved['meta'].update(image=self.url + '/' + NEW_BASE, mist=self.url + '/' + NEW_MIST)
        self.page.evaluate('snapshot=>window.presentation.requirePrepared(snapshot)', resolved)
        self.assertEqual(self.page.evaluate("document.querySelector('#world').outerHTML"), before)
        self.assertEqual(len(self.requests), request_count)
        for field, value in [('image', OLD_BASE), ('mist', OLD_MIST)]:
            uncached = copy.deepcopy(self.snapshot)
            uncached['meta'][field] = value
            self.assertTrue(self.page.evaluate("""snapshot=>{
                try { window.presentation.requirePrepared(snapshot); return false; } catch { return true; }
            }""", uncached), f'Changing {field} cannot borrow the other URL pair readiness')
        self.assert_clean()
    def test_05_failed_mist_evicts_pending_pair_and_allows_a_real_retry(self):
        failure_url = self.url + '/' + NEW_MIST
        self.expected_failures.add(failure_url)
        requests = []

        def failing_once(route):
            requests.append(route.request.url)
            if len(requests) == 1:
                route.fulfill(status=404, body='missing test mist')
            else:
                route.continue_()

        self.page.route('**/' + NEW_MIST, failing_once)
        self.boot()
        self.begin_prepare()
        self.page.wait_for_function('window.prepareError', polling=50)
        self.page.evaluate('window.presentation.fail(new Error(window.prepareError))')
        self.assertTrue(self.page.locator('#map-loading').is_visible())
        self.assertFalse(self.world_visible())
        self.assertTrue(self.page.evaluate("""snapshot=>{
            try { window.presentation.requirePrepared(snapshot); return false; } catch { return true; }
        }""", self.snapshot))
        self.begin_prepare()
        self.wait_prepared()
        self.assertGreaterEqual(len(requests), 2, 'A rejected cache entry must not poison a later retry')
        self.assertTrue(self.page.locator('#map-loading button').is_hidden())
        self.assertNotEqual(self.page.locator('#map-loading').get_attribute('data-state'), 'error')
        self.reveal()
        self.assertTrue(self.world_visible())
        self.assert_clean()
    def test_06_frame_uses_committed_old_and_new_map_dimensions_without_moving_coordinates(self):
        self.boot()
        self.assertEqual(self.page.evaluate('typeof window.presentation.renderFrame'), 'function', 'Frame updates must be explicit after snapshot commit, not during preload')
        old = copy.deepcopy(self.snapshot)
        old['meta'].update(width=3247, height=4860, image=OLD_BASE, mist=OLD_MIST)
        self.page.evaluate("""snapshot=>{
            window.renderFixture(snapshot);
            document.querySelector('#world').style.transform='translate(73px, 41px) scale(0.2)';
            window.presentation.renderFrame(snapshot);
        }""", old)
        frame = self.page.locator('#map-frame')
        self.assertEqual(frame.count(), 1)
        self.assertEqual(frame.evaluate("e=>e.parentElement.id"), 'world')
        self.assertEqual(frame.get_attribute('viewBox'), '0 0 3247 4860')
        self.assertEqual(frame.evaluate("e=>[e.style.width,e.style.height]"), ['3247px', '4860px'])
        self.assertEqual(frame.get_attribute('aria-hidden'), 'true')
        self.assertEqual(frame.evaluate("e=>[getComputedStyle(e).position,getComputedStyle(e).pointerEvents,getComputedStyle(e).userSelect]"), ['absolute', 'none', 'none'])
        self.assertTrue(frame.evaluate("e=>Array.from(e.querySelectorAll('*')).every(node=>getComputedStyle(node).pointerEvents==='none')"))
        before = self.page.evaluate("""()=>{
            const world=document.querySelector('#world');
            return {size:[world.style.width,world.style.height],transform:world.style.transform,
                base:document.querySelector('#base-map').getAttribute('src'),
                mist:document.querySelector('#mist-map').getAttribute('src'),frame:document.querySelector('#map-frame').outerHTML};
        }""")
        self.begin_prepare()
        self.wait_prepared()
        after = self.page.evaluate("""()=>{
            const world=document.querySelector('#world');
            return {size:[world.style.width,world.style.height],transform:world.style.transform,
                base:document.querySelector('#base-map').getAttribute('src'),
                mist:document.querySelector('#mist-map').getAttribute('src'),frame:document.querySelector('#map-frame').outerHTML};
        }""")
        self.assertEqual(after, before, 'An incoming preload cannot touch the active frame, images, dimensions or camera')
        self.page.evaluate('snapshot=>window.presentation.renderFrame(snapshot)', self.snapshot)
        self.assertEqual(frame.get_attribute('viewBox'), '0 0 3526 4548')
        self.assertEqual(frame.evaluate("e=>[e.style.width,e.style.height]"), ['3526px', '4548px'])
        self.assertEqual(self.page.locator('#map-frame').count(), 1)
        self.assertEqual(self.page.locator('#world').evaluate('e=>[e.style.width,e.style.height,e.style.transform]'),
                         [before['size'][0], before['size'][1], before['transform']], 'Decorative framing never owns map coordinate registration')
        self.assertLess(frame.evaluate('e=>e.outerHTML.length'), 15000, 'The edge must remain a compact vector overlay, not another raster')
        self.assertEqual(frame.locator('foreignObject,canvas').count(), 0)
        self.assert_clean()
    def test_07_failed_incoming_map_keeps_the_complete_active_view_and_saved_snapshot_atomic(self):
        self.boot()
        self.begin_prepare()
        self.wait_prepared()
        self.page.evaluate('snapshot=>window.presentation.renderFrame(snapshot)', self.snapshot)
        self.reveal()
        before = self.page.evaluate("""snapshot=>{
            window.liveSnapshot=structuredClone(snapshot);
            localStorage.setItem('court-map-test-draft', JSON.stringify(snapshot));
            return {world:document.querySelector('#world').outerHTML, loader:document.querySelector('#map-loading').outerHTML,
                body:document.body.className, saved:localStorage.getItem('court-map-test-draft'), snapshot:window.liveSnapshot};
        }""", self.snapshot)
        incoming = copy.deepcopy(self.snapshot)
        incoming['meta'].update(width=3247, height=4860, image=OLD_BASE + '?test-missing=1', mist=OLD_MIST)
        failure_url = self.url + '/' + incoming['meta']['image']
        self.expected_failures.add(failure_url)
        self.page.route('**/' + incoming['meta']['image'], lambda route: route.fulfill(status=404, body='missing incoming test map'))
        self.begin_prepare(incoming)
        self.page.wait_for_function('window.prepareError', polling=50)
        self.assertTrue(self.world_visible(), 'A failed import cannot hide the already complete publication')
        self.assertTrue(self.page.locator('#map-loading').is_hidden())
        self.page.evaluate('window.presentation.fail(new Error(window.prepareError))')
        after = self.page.evaluate("""()=>({world:document.querySelector('#world').outerHTML,
            loader:document.querySelector('#map-loading').outerHTML,body:document.body.className,
            saved:localStorage.getItem('court-map-test-draft'),snapshot:window.liveSnapshot})""")
        self.assertEqual(after, before, 'Both prepare rejection and fail() are DOM/persistence-atomic once an active map is complete')
        self.assertTrue(self.page.evaluate("""snapshot=>{
            try { window.presentation.requirePrepared(snapshot); return false; } catch { return true; }
        }""", incoming))
        self.page.evaluate('snapshot=>window.presentation.requirePrepared(snapshot)', self.snapshot)
        self.assert_clean()
    def test_08_unsafe_image_tokens_and_invalid_dimensions_are_rejected_before_any_request(self):
        self.boot()
        # initMapPresentation assigns these loader images after navigation load.
        # Settle their real requests before measuring forbidden image requests.
        self.page.wait_for_function("Array.from(document.querySelectorAll('#map-loading img')).every(i=>i.complete&&i.naturalWidth>0)", polling=50)
        unsafe = [None, 9, '', ' assets/maps/gilneas-enhanced.webp', 'assets/maps/gilneas-enhanced.webp ',
                  'javascript:alert(1)', 'data:image/svg+xml,<svg onload="window.bad=1"/>',
                  'https://name:password@example.invalid/map.png', 'https://example.invalid/not-an-image.html']
        for value in unsafe:
            invalid = copy.deepcopy(self.snapshot)
            invalid['meta']['image'] = value
            before = len(self.requests)
            result = self.page.evaluate("""async snapshot=>{
                try { await window.presentation.prepare(snapshot); return null; }
                catch(error) { return String(error.message); }
            }""", invalid)
            self.assertIsNotNone(result)
            self.assertEqual(len(self.requests), before, f'Unsafe source token must fail validation, not initiate an image fetch: {value!r}')
        for dimensions in [(0, 4548), (3526, -1), ('3526', 4548), (3526, None)]:
            invalid = copy.deepcopy(self.snapshot)
            invalid['meta'].update(width=dimensions[0], height=dimensions[1])
            before = len(self.requests)
            result = self.page.evaluate("""async snapshot=>{
                try { await window.presentation.prepare(snapshot); return null; }
                catch(error) { return String(error.message); }
            }""", invalid)
            self.assertIsNotNone(result)
            self.assertEqual(len(self.requests), before)
        self.assertIsNone(self.page.evaluate('window.bad'))
        self.assertFalse(self.world_visible())
        self.assert_clean()
    def test_09_a_resource_pair_prepared_before_an_initial_geometry_failure_can_recover_without_reload(self):
        self.boot()
        self.begin_prepare()
        self.wait_prepared()
        self.page.evaluate("window.presentation.fail(new Error('Тестовый отказ геометрии'))")
        self.assertFalse(self.world_visible())
        self.assertTrue(self.page.locator('#map-loading button').is_visible())
        request_count = len(self.requests)
        self.begin_prepare()
        self.wait_prepared()
        self.assertEqual(len(self.requests), request_count, 'Geometry retry should reuse already decoded raster resources')
        self.reveal()
        self.assertTrue(self.world_visible())
        self.assert_clean()

    def test_10_repeated_initializer_returns_the_same_controller_without_rehiding_a_complete_view(self):
        self.boot()
        self.begin_prepare()
        self.wait_prepared()
        self.page.evaluate('snapshot=>window.presentation.renderFrame(snapshot)', self.snapshot)
        self.reveal()
        before = self.page.locator('#world').evaluate('e=>e.outerHTML')
        self.assertTrue(self.page.evaluate('window.initMapPresentation()===window.presentation'), 'Repeated integration hooks must share the active controller/cache')
        self.assertEqual(self.page.locator('#map-loading').count(), 1)
        self.assertEqual(self.page.locator('#map-frame').count(), 1)
        self.assertTrue(self.world_visible())
        self.assertEqual(self.page.locator('#world').evaluate('e=>e.outerHTML'), before)
        self.assert_clean()
    def test_11_raster_pair_is_verified_by_readable_canvas_when_detached_decode_rejects(self):
        self.boot()
        self.page.evaluate("""()=>{
            window.decodeAttempts=[]; window.canvasSamples=0;
            HTMLImageElement.prototype.decode=function(){
                window.decodeAttempts.push(this.src);
                return Promise.reject(new DOMException('Test detached-image scheduling failure', 'EncodingError'));
            };
            const sample=CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData=function(...args){
                window.canvasSamples++; return sample.apply(this,args);
            };
        }""")
        self.begin_prepare()
        self.wait_prepared()
        self.assertEqual(self.page.evaluate('window.decodeAttempts.length'), 2)
        self.assertEqual(self.page.evaluate('window.canvasSamples'), 2, 'Decode rejection needs real readable-pixel evidence, not an unconditional success catch')
        self.reveal()
        self.assertTrue(self.world_visible())
        self.assert_clean()

    def test_12_unreadable_canvas_after_decode_failure_is_not_declared_ready(self):
        self.boot()
        self.page.evaluate("""()=>{
            HTMLImageElement.prototype.decode=()=>Promise.reject(new DOMException('Test decode failure','EncodingError'));
            CanvasRenderingContext2D.prototype.getImageData=()=>{throw new DOMException('Test unreadable raster','SecurityError');};
        }""")
        self.begin_prepare()
        self.page.wait_for_function('window.prepareError', polling=50)
        self.assertFalse(self.world_visible())
        self.assertTrue(self.page.evaluate("""snapshot=>{
            try{window.presentation.requirePrepared(snapshot);return false;}catch{return true;}
        }""", self.snapshot))
        self.page.evaluate('window.presentation.fail(new Error(window.prepareError))')
        self.assertEqual(self.page.locator('#map-loading').get_attribute('data-state'), 'error')
        self.assert_clean()

    def test_13_native_marker_drag_and_wheel_survive_the_frame_and_follow_world_transform(self):
        self.boot()
        self.begin_prepare()
        self.wait_prepared()
        fixture = copy.deepcopy(self.snapshot)
        fixture['territories'] = []
        fixture['nobles'] = []
        # No Council panel participates; its references target excluded nobles.
        fixture.pop('royalCouncil', None)
        marker = copy.deepcopy(fixture['locations'][0])
        # Keep the location classification at fit scale, but no excluded children.
        marker.update(isLocation=True, linkedLocationIds=[])
        marker.update(id='test-map-frame-marker', name='Тестовая метка у края карты', x=12, y=12, objects=[])
        fixture['locations'] = [marker]
        # This one-marker geometry fixture deliberately excludes all ferry docks.
        # Remove only their inherited network; production keeps every real route.
        fixture['meta'].pop('ferryNetwork', None)
        self.page.evaluate("""async snapshot=>{
            const {validateLocationLinks}=await import('./assets/js/location-links.mjs');
            validateLocationLinks(snapshot);
            const {normalizeData}=await import('./assets/js/model.mjs');
            normalizeData(snapshot);
            window.fixtureSnapshot=snapshot; window.nativeSelections=[];
            const {initUI}=await import('./assets/js/ui.mjs');
            window.ui=initUI({getData:()=>window.fixtureSnapshot,getSelectedId:()=>null,
                onSelect:id=>window.nativeSelections.push(id)});
            window.ui.setPanel('navigation',false);window.ui.setPanel('layers',false);
            window.ui.fit(false);
            window.presentation.renderFrame(snapshot);
            await window.presentation.reveal();
        }""", fixture)
        self.page.locator('.map-marker[data-location-id="test-map-frame-marker"]').click()
        self.assertEqual(self.page.evaluate('window.nativeSelections'), ['test-map-frame-marker'])
        viewport = self.page.locator('#viewport').bounding_box()
        self.page.evaluate('window.ui.zoom(1.6)')
        camera_before = self.page.evaluate('window.ui.getCamera()')
        x, y = viewport['x'] + viewport['width'] / 2, viewport['y'] + viewport['height'] / 2
        self.page.mouse.move(x, y)
        self.page.mouse.down()
        self.page.mouse.move(x + 72, y + 38, steps=8)
        self.page.mouse.up()
        camera_after = self.page.evaluate('window.ui.getCamera()')
        self.assertGreater(abs(camera_after['x'] - camera_before['x']), 10)
        self.assertGreater(abs(camera_after['y'] - camera_before['y']), 10)
        self.page.mouse.wheel(0, -160)
        self.page.wait_for_function('scale=>window.ui.getCamera().scale!==scale', arg=camera_after['scale'], polling=50)
        result = self.page.evaluate("""()=>{
            const w=document.querySelector('#world').getBoundingClientRect(), f=document.querySelector('#map-frame').getBoundingClientRect();
            return {world:[w.x,w.y,w.width,w.height],frame:[f.x,f.y,f.width,f.height],
                inert:getComputedStyle(document.querySelector('#map-frame')).pointerEvents};
        }""")
        self.assertEqual(result['world'], result['frame'], 'Frame must pan/zoom with map coordinates, never the viewport')
        self.assertEqual(result['inert'], 'none')
        self.assert_clean()
    def test_14_loading_surface_respects_reduced_motion_and_desktop_mobile_bounds(self):
        self.boot()
        self.page.wait_for_function("Array.from(document.querySelectorAll('#map-loading img')).every(i=>i.complete&&i.naturalWidth>0)", polling=50)
        loader = self.page.locator('#map-loading')
        self.assertEqual(loader.locator('.map-loading-rain').evaluate('e=>getComputedStyle(e).animationName'), 'none')
        self.assertEqual(loader.locator('.map-loading-crest').evaluate('e=>new URL(e.src).pathname'), '/assets/ui/gilneas-royal-shield.svg')
        self.assertEqual(loader.locator('.map-loading-rose').evaluate('e=>new URL(e.src).pathname'), '/assets/ui/rose.svg')
        self.assertNotRegex(loader.inner_text(), r'\d+\s*%')
        for width, height in [(1440, 1000), (390, 844)]:
            self.page.set_viewport_size({'width': width, 'height': height})
            bounds = loader.locator('.map-loading-plate').bounding_box()
            self.assertGreaterEqual(bounds['x'], 0)
            self.assertGreaterEqual(bounds['y'], 0)
            self.assertLessEqual(bounds['x'] + bounds['width'], width)
            self.assertLessEqual(bounds['y'] + bounds['height'], height)
            screenshot = ARTIFACTS / f'loading-{width}x{height}.png'
            self.page.screenshot(path=str(screenshot))
            print('Loading screenshot:', screenshot)
        self.page.emulate_media(reduced_motion='no-preference')
        self.assertEqual(loader.locator('.map-loading-rain').evaluate('e=>getComputedStyle(e).animationName'), 'map-rain-drift')
        self.assertFalse(self.world_visible())
        self.assert_clean()

    def test_15_static_awaiting_class_hides_all_world_descendants_before_initializer(self):
        self.boot()
        self.page.evaluate("""()=>{
            document.querySelector('#map-loading').remove();
            const marker=document.createElement('button'); marker.textContent='Тестовая скрытая метка';
            marker.style.visibility='visible'; document.querySelector('#markers').append(marker);
            window.visibleOverrideMarker=marker;
            window.renderFixture(window.fixtureSnapshot);
        }""")
        self.assertFalse(self.world_visible())
        self.assertEqual(self.page.evaluate('getComputedStyle(window.visibleOverrideMarker).visibility'), 'hidden', 'Static class must suppress explicit child visibility, not just inherited #world state')
        self.assert_clean()

    def test_16_frame_screenshot_is_an_inert_fine_vector_edge_over_the_actual_raster(self):
        self.boot()
        self.begin_prepare()
        self.wait_prepared()
        self.page.evaluate('snapshot=>window.presentation.renderFrame(snapshot)', self.snapshot)
        self.reveal()
        self.page.evaluate("""()=>{
            document.querySelector('#world').style.transform='translate(0px,0px) scale(0.55)';
            for (const id of ['navigation','layers']) document.getElementById(id).hidden=true;
            document.querySelector('.map-title').style.display='none';
        }""")
        self.page.wait_for_function("document.querySelector('#base-map').complete&&document.querySelector('#base-map').naturalWidth>0", polling=50)
        screenshot = ARTIFACTS / 'map-frame-native-corner.png'
        self.page.screenshot(path=str(screenshot))
        print('Frame screenshot:', screenshot)
        self.assertEqual(self.page.locator('#map-frame').evaluate('e=>getComputedStyle(e).pointerEvents'), 'none')
        self.assert_clean()


if __name__ == '__main__':
    unittest.main()
