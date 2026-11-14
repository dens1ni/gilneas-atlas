import unittest
import threading
import functools
import http.server
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class EditorSlice(unittest.TestCase):
    def test_create_building_with_independent_semantic_modifiers_and_reload(self):
        self.assertTrue((ROOT/'assets/js/editor.mjs').exists(), 'the location-object editor is not implemented')
        handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT))
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch()
                page=browser.new_page(viewport={'width':1440,'height':1000})
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.wait_for_function('window.gilneasApp?.ready')
                page.locator('#search').fill('Город Гилнеас')
                page.locator('[data-location-id="gilneas-city"]').first.click()
                page.locator('#dossier-add-object').click()
                page.locator('#object-type').select_option('building')
                page.locator('#object-name').fill('Королевская кузница')
                page.locator('#object-description').fill('Сталь для войска')
                page.locator('#modifier-bonus-add').click()
                page.locator('#modifier-list textarea').first.fill('+2 к снабжению')
                page.locator('#modifier-penalty-add').click()
                page.locator('#modifier-list textarea').nth(1).fill('−1 к казне')
                page.locator('#object-form button[type=submit]').click()
                self.assertFalse(page.locator('#object-editor').is_visible())
                page.locator('#dossier-objects details').last.locator('summary').click()
                self.assertIn('Королевская кузница',page.locator('#dossier-objects').inner_text())
                self.assertEqual(page.locator('#dossier-objects .modifier.bonus').last.inner_text(),'+2 к снабжению')
                self.assertEqual(page.locator('#dossier-objects .modifier.penalty').last.inner_text(),'−1 к казне')
                data=page.evaluate('window.gilneasApp.getData()')
                obj=next(l for l in data['locations'] if l['id']=='gilneas-city')['objects'][-1]
                self.assertEqual([m['kind'] for m in obj['modifiers']],['bonus','penalty'])
                saved_id=obj['id']
                page.reload()
                page.wait_for_function('window.gilneasApp?.ready')
                restored=page.evaluate('window.gilneasApp.getData()')
                self.assertEqual(next(l for l in restored['locations'] if l['id']=='gilneas-city')['objects'][-1]['id'],saved_id)
                browser.close()
        finally:
            server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
