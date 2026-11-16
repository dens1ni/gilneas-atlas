"""Preserve full snapshots through real court JSON/ZIP exports and reload."""
import functools
import json
import os
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-court-export-evidence')
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
class CourtExport(unittest.TestCase):
    def test_author_council_and_wall_events_roundtrip_through_downloaded_json_and_site_zip(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        threading.Thread(target=server.serve_forever,daemon=True).start(); OUT.mkdir(parents=True,exist_ok=True)
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling'])
                ctx=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                page=ctx.new_page(); page.set_default_timeout(15000); errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('response',lambda response:errors.append(f'{response.status} {response.url}') if response.status>=400 else None)
                page.goto(f'http://127.0.0.1:{server.server_port}'+PREFIX)
                page.wait_for_function('window.gilneasApp?.ready',polling=50)
                published=json.loads((ROOT/'assets/data/atlas.json').read_text())
                track=published['meta']['wallConstruction']
                original_events=track.get('events',[])
                original_ids={event['id'] for event in original_events}
                after_supply=max(0,min(track['max'],track['value']+15))
                after_delay=max(0,min(track['max'],after_supply-20))
                baseline=page.evaluate('window.gilneasApp.getData()')
                self.assertEqual(baseline['meta']['wallConstruction'],track)
                page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click()
                page.locator('#council-open').click()
                page.locator('[data-council-edit="council-noble-silverlaine"]').click()
                page.locator('#council-party').select_option('internationalists')
                page.locator('#council-note').fill('  Авторское назначение барона  ')
                page.locator('#council-save').click(); page.locator('#council-close').click()
                page.locator('#wall-history-open').click()
                page.locator('#wall-event-name').fill('Проверка поставок')
                page.locator('#wall-event-delta').fill('15')
                page.locator('#wall-effect-bonus-add').click()
                page.locator('#wall-effect-list textarea').fill('  Бонус автора +1  ')
                page.locator('#wall-event-form button[type=submit]').click()
                self.assertEqual(page.locator('#wall-progress-value').text_content(),f"{after_supply} / {track['max']}")
                page.locator('#wall-event-name').fill('Проверка задержки')
                page.locator('#wall-event-delta').fill('-20')
                page.locator('#wall-effect-penalty-add').click()
                page.locator('#wall-effect-list textarea').fill('  Штраф автора −1  ')
                page.locator('#wall-event-form button[type=submit]').click()
                self.assertEqual(page.locator('#wall-progress-value').text_content(),f"{after_delay} / {track['max']}")
                snapshot=page.evaluate('window.gilneasApp.getData()')
                events=snapshot['meta']['wallConstruction']['events']
                self.assertEqual(snapshot['meta']['wallConstruction']['value'],after_delay)
                self.assertEqual(len(events),len(original_events)+2)
                self.assertEqual([event for event in events if event['id'] in original_ids],original_events)
                for field in ['locations','nobles','factions','territories','territoryGrid','sources']:
                    self.assertEqual(snapshot[field],baseline[field],field)
                page.locator('[data-close=wall-journal]').click(); page.locator('#editor-open').click()
                with page.expect_download() as download: page.locator('#export-json').click()
                json_path=OUT/'court-snapshot.json'; download.value.save_as(str(json_path))
                self.assertEqual(json.loads(json_path.read_text()),snapshot)
                with page.expect_download(timeout=60000) as download: page.locator('#export-site').click()
                zip_path=OUT/'court-snapshot.zip'; download.value.save_as(str(zip_path))
                manifest=json.loads((ROOT/'assets/runtime-manifest.json').read_text())
                with zipfile.ZipFile(zip_path) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertEqual(set(archive.namelist()),set(manifest))
                    self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),snapshot)
                    for name in manifest:
                        if name!='assets/data/atlas.json': self.assertEqual(archive.read(name),(ROOT/name).read_bytes(),name)
                page.reload(); page.wait_for_function('window.gilneasApp?.ready',polling=50)
                self.assertEqual(page.evaluate('window.gilneasApp.getData()'),snapshot)
                self.assertFalse(page.locator('#editing-enabled').is_checked())
                page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click()
                page.locator('#editor-open').click(); page.locator('#draft-reset').click(); page.locator('#confirm-yes').click()
                page.wait_for_function('localStorage.getItem("gilneas-atlas-draft-v1")===null',polling=50)
                self.assertEqual(page.evaluate('window.gilneasApp.getData()'),baseline)
                if not page.locator('#editor').is_visible(): page.locator('#editor-open').click()
                page.locator('#import-json').set_input_files(str(json_path))
                page.wait_for_function('(count)=>window.gilneasApp.getData().meta.wallConstruction.events?.length===count',arg=len(original_events)+2,polling=50)
                self.assertEqual(page.evaluate('window.gilneasApp.getData()'),snapshot)
                self.assertEqual(json.loads(page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')),snapshot)
                self.assertEqual(errors,[]); ctx.close(); browser.close()
        finally: server.shutdown(); server.server_close()
if __name__=='__main__': unittest.main()
