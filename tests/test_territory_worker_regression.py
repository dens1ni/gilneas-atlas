"""Controlled worker failures against the real territory DOM/UI/model.

Only the parent bootstrap is routed out. Successful jobs use the actual Blob
geometry worker and source paths; fixtures and failure messages are test-only.
"""
import functools
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 5000


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class TerritoryWorkerRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT)))
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
        self.page.set_default_timeout(TIMEOUT)
        self.page.set_default_navigation_timeout(TIMEOUT)
        self.errors = []
        self.console_errors = []
        self.http_errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.console_errors.append(message.text)
                     if message.type == 'error' else None)
        self.page.on('response', lambda response: self.http_errors.append(
            (response.status, response.url)) if response.status >= 400 else None)
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
            status=200, content_type='application/javascript',
            body='// Worker regression fixture: isolate parent bootstrap.'))

    def tearDown(self):
        self.context.close()

    def boot(self):
        self.page.goto(self.url + '/index.html', wait_until='networkidle')
        self.page.evaluate("""async () => {
            document.body.classList.add('edit-mode');
            const M = await import('./assets/js/model.mjs');
            const S = await import('./assets/js/smooth-territories.mjs');
            const T = await import('./assets/js/territories.mjs');
            const {initUI} = await import('./assets/js/ui.mjs');
            const baseline = M.normalizeData({version: 1,
                meta: {width: 3247, height: 4860, image: 'assets/maps/gilneas-enhanced.webp',
                    mist: 'assets/maps/inactive-mist.webp'},
                factions: [{id: 'test-root', name: 'Тестовая держава', parent: null, color: '#ad4255'},
                    {id: 'test-house', name: 'Тестовый вассал', parent: 'test-root', color: '#559080'}],
                locations: [], territories: [], nobles: [], sources: [],
                territoryGrid: {version: 1, width: 203, height: 304, step: 16,
                    mapWidth: 3247, mapHeight: 4860, keys: ['test-root', 'test-house'],
                    cells: new Array(61712).fill(0), radius: 260}});
            window.state = baseline;
            window.workerJobs = [];
            window.readiness = {};
            const actualGeometryAsync = S.SmoothTerritories.geometryAsync;
            S.SmoothTerritories.geometryAsync = snapshot => new Promise((resolve, reject) => {
                workerJobs.push({snapshot: structuredClone(snapshot),
                    resolve: () => resolve(actualGeometryAsync(snapshot)),
                    reject: message => reject(Error(message))});
            });
            window.ui = initUI({getData: () => state, getSelectedId: () => null,
                onSelect: () => {}, onRenderTerritories: () => window.boundaries?.render()});
            const replaceData = next => {
                window.state = M.normalizeData(next);
                ui.render();
                window.boundaries?.render();
                return state;
            };
            window.boundaries = T.initTerritories({getData: () => state, replaceData, ui});
            window.adoptWorkerGrid = value => {
                const next = structuredClone(state);
                next.territoryGrid.cells.fill(0);
                next.territoryGrid.cells[232 * 203 + 104] = value;
                replaceData(next);
            };
            window.watchReady = name => {
                readiness[name] = {state: 'pending'};
                boundaries.whenReady().then(value => {
                    readiness[name] = {state: 'resolved', value};
                }, error => {
                    readiness[name] = {state: 'rejected', message: error.message};
                });
            };
        }""")
        self.page.wait_for_function('workerJobs.length === 1', polling=20)

    def ready_result(self, name):
        try:
            self.page.wait_for_function(
                'name => readiness[name].state !== "pending"', arg=name, polling=20)
        except PlaywrightTimeoutError:
            self.fail(f'whenReady({name}) stayed pending after the worker settled')
        return self.page.evaluate('name => readiness[name]', name)

    def assert_clean_browser(self):
        self.assertEqual(self.errors, [])
        self.assertEqual(self.console_errors, [])
        self.assertEqual(self.http_errors, [])

    def test_obsolete_worker_rejection_keeps_latest_readiness_and_status(self):
        self.boot()
        self.page.evaluate("adoptWorkerGrid(1); adoptWorkerGrid(2); watchReady('latest')")
        self.assertEqual(self.page.evaluate('workerJobs.length'), 1,
                         'the initial job must still be held while two newer grids are adopted')
        self.assertEqual(self.page.evaluate('boundaries.getGrid()'),
                         self.page.evaluate('state.territoryGrid'))
        self.page.evaluate("workerJobs[0].reject('STALE_WORKER_FAILURE')")
        self.page.wait_for_function('workerJobs.length === 2', polling=20)
        self.assertEqual(self.page.evaluate("""() => ({
            readiness: readiness.latest.state,
            status: document.getElementById('boundary-status').textContent
        })"""), {'readiness': 'pending', 'status': ''},
            'an obsolete rejection must neither reject current waiters nor overwrite status')
        self.assertEqual(self.page.evaluate('workerJobs[1].snapshot.cells'),
                         self.page.evaluate('state.territoryGrid.cells'))
        self.page.evaluate('workerJobs[1].resolve()')
        current = self.ready_result('latest')
        self.assertEqual(current['state'], 'resolved')
        self.assertEqual(current['value']['revision'], 3)
        self.assertEqual(current['value']['geometryCalls'], 2)
        self.assertEqual(self.page.locator('#boundary-status').text_content(), '')
        self.assertEqual(self.page.locator(
            '#boundary-vector > path[fill-rule="evenodd"]').get_attribute('data-faction-id'),
            'test-house', 'the visible fill must come from the newest grid')

        # Disposal also makes a held job obsolete, without a replacement DOM.
        self.page.evaluate("""adoptWorkerGrid(1); watchReady('disposed');
            window.detachedStatus = document.getElementById('boundary-status');
            boundaries.destroy(); workerJobs[2].reject('DISPOSED_WORKER_FAILURE');""")
        self.assertEqual(self.ready_result('disposed'),
                         {'state': 'rejected', 'message': 'Редактор закрыт.'})
        self.assertEqual(self.page.evaluate('detachedStatus.textContent'), '')
        self.assertEqual(self.page.locator('#boundary-tools').count(), 0)
        self.assertEqual(self.page.evaluate('workerJobs.length'), 3)
        self.assert_clean_browser()

    def test_current_worker_failure_rejects_readiness_then_later_grid_recovers(self):
        self.boot()
        self.page.evaluate("watchReady('failed'); workerJobs[0].reject('CURRENT_WORKER_FAILURE')")
        failure = {'state': 'rejected', 'message': 'CURRENT_WORKER_FAILURE'}
        self.assertEqual(self.ready_result('failed'), failure)
        self.assertEqual(self.page.locator('#boundary-status').text_content(),
                         'Не удалось обновить контуры: CURRENT_WORKER_FAILURE')
        self.assertEqual(self.page.evaluate('workerJobs.length'), 1,
                         'a failed revision must not spin/retry geometry')
        self.page.evaluate("watchReady('alreadyFailed')")
        self.assertEqual(self.ready_result('alreadyFailed'), failure,
                         'readiness requested after the current failure must reject, not hang')

        self.page.evaluate("adoptWorkerGrid(2); watchReady('recovered')")
        self.page.wait_for_function('workerJobs.length === 2', polling=20)
        self.assertEqual(self.page.evaluate('workerJobs[1].snapshot.cells'),
                         self.page.evaluate('state.territoryGrid.cells'))
        self.assertEqual(self.page.evaluate('readiness.recovered.state'), 'pending')
        self.page.evaluate('workerJobs[1].resolve()')
        recovered = self.ready_result('recovered')
        self.assertEqual(recovered['state'], 'resolved')
        self.assertEqual(recovered['value']['revision'], 2)
        self.assertEqual(recovered['value']['geometryCalls'], 2)
        self.assertEqual(self.page.locator('#boundary-status').text_content(), '',
                         'successful later geometry must clear its old worker failure message')
        self.assertEqual(self.page.locator(
            '#boundary-vector > path[fill-rule="evenodd"]').get_attribute('data-faction-id'),
            'test-house')
        self.page.evaluate("watchReady('currentReady')")
        self.assertEqual(self.ready_result('currentReady')['state'], 'resolved')
        self.assertEqual(self.page.evaluate('workerJobs.length'), 2)
        self.assert_clean_browser()


if __name__ == '__main__':
    unittest.main()
