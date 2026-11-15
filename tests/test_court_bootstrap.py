"""Real parent bootstrap mounts the council and wall journal without saving."""
import functools,http.server,json,os,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
class CourtBootstrap(unittest.TestCase):
    def test_council_and_wall_controls_use_real_parent_snapshot(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling'])
                page=b.new_page(viewport={'width':1440,'height':1000});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}'+PREFIX)
                page.wait_for_function('window.gilneasApp?.ready')
                before=page.evaluate('window.gilneasApp.getData()');stored=page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')")
                page.locator('#council-open').click()
                self.assertTrue(page.locator('#royal-council').is_visible())
                self.assertEqual(page.locator('#council-title').inner_text(),'Королевский Совет')
                page.locator('#council-close').click()
                page.locator('#wall-history-open').click()
                self.assertTrue(page.locator('#wall-journal').is_visible())
                self.assertEqual(page.locator('#wall-progress-value').text_content(),'10 / 100')
                page.locator('[data-close=wall-journal]').click()
                self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before)
                self.assertEqual(page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')"),stored)
                self.assertEqual(errors,[]);b.close()
        finally:server.shutdown();server.server_close()
    def test_wall_event_after_commit_recalculates_header_and_reset_restores_published_track(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling'])
                page=b.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{server.server_port}'+PREFIX)
                page.wait_for_function('window.gilneasApp?.ready');before=page.evaluate('window.gilneasApp.getData()')
                page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click()
                page.locator('#wall-history-open').click();page.locator('#wall-event-name').fill('Проверка поставки')
                page.locator('#wall-event-description').fill('  Авторский журнал  ');page.locator('#wall-event-delta').fill('15')
                page.locator('#wall-event-form button[type=submit]').click()
                self.assertEqual(page.locator('#wall-progress-value').text_content(),'25 / 100')
                snapshot=page.evaluate('window.gilneasApp.getData()');self.assertEqual(snapshot['locations'],before['locations'])
                self.assertEqual(snapshot['territoryGrid'],before['territoryGrid'])
                self.assertEqual(snapshot['meta']['wallConstruction']['events'][0]['description'],'  Авторский журнал  ')
                page.locator('[data-close=wall-journal]').click();page.locator('#editor-open').click()
                page.locator('#draft-reset').click();page.locator('#confirm-yes').click()
                page.wait_for_function("localStorage.getItem('gilneas-atlas-draft-v1')===null")
                self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before)
                self.assertEqual(page.locator('#wall-progress-value').text_content(),'10 / 100')
                b.close()
        finally:server.shutdown();server.server_close()
    def test_programmatic_council_and_wall_dialogs_close_on_true_backdrop(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling'])
                page=b.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{server.server_port}'+PREFIX)
                page.wait_for_function('window.gilneasApp?.ready')
                for opener,dialog in [('#council-open','#royal-council'),('#wall-history-open','#wall-journal')]:
                    page.locator(opener).click();self.assertTrue(page.locator(dialog).is_visible())
                    page.mouse.click(2,2)
                    self.assertTrue(page.locator(dialog).is_hidden(),dialog+' should close on true backdrop click')
                b.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
