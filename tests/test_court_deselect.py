"""Clearing a map selection is presentation-only, never a data commit."""
import functools
import http.server
import json
import os
import threading
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
class Deselect(unittest.TestCase):
    def test_clear_selection_preserves_live_snapshot_and_exact_saved_draft(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling'])
                page=browser.new_page(viewport={'width':1440,'height':1000})
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}'+PREFIX)
                page.wait_for_function('window.gilneasApp?.ready')
                page.evaluate("window.gilneasApp.selectId('gilneas-city')")
                before=page.evaluate('window.gilneasApp.getData()')
                raw=json.dumps(before,ensure_ascii=False,indent=3)+'\n'
                page.evaluate("raw=>localStorage.setItem('gilneas-atlas-draft-v1',raw)",raw)
                self.assertTrue(page.locator('#dossier').is_visible())
                self.assertEqual(page.locator('.map-marker.selected').count(),1)
                self.assertEqual(page.evaluate('typeof window.gilneasApp.clearSelection'),'function')
                page.evaluate('window.gilneasApp.clearSelection()')
                self.assertIsNone(page.evaluate('window.gilneasApp.getSelectedId()'))
                self.assertTrue(page.locator('#dossier').is_hidden())
                self.assertEqual(page.locator('.map-marker.selected').count(),0)
                self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before)
                self.assertEqual(page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')"),raw)
                page.evaluate('window.gilneasApp.clearSelection()')
                self.assertEqual(page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')"),raw)
                self.assertEqual(errors,[])
                browser.close()
        finally:server.shutdown();server.server_close()
    def test_native_blank_click_clears_but_camera_drag_preserves_selection(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling'])
                page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                page.goto(f'http://127.0.0.1:{server.server_port}'+PREFIX);page.wait_for_function('window.gilneasApp?.ready')
                page.evaluate("window.gilneasApp.selectId('gilneas-city');window.gilneasApp.ui.setPanel('navigation',false);window.gilneasApp.ui.setPanel('layers',false);window.gilneasApp.ui.focusLocation('gilneas-city',false)")
                before=page.evaluate('window.gilneasApp.getData()');stored=page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')")
                point=page.evaluate("""()=>{const viewport=document.getElementById('viewport'),r=viewport.getBoundingClientRect();for(let y=r.top+180;y<r.bottom-150;y+=70)for(let x=r.left+200;x<r.right-440;x+=70){const e=document.elementFromPoint(x,y);if(e&&viewport.contains(e)&&!e.closest('.map-marker,.map-title,button,input,dialog'))return [x,y];}throw Error('No blank map point found');}""")
                page.mouse.move(*point);page.mouse.down();page.mouse.move(point[0]+45,point[1]+25,steps=6);page.mouse.up()
                self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),'gilneas-city','Camera drag must preserve selection')
                page.mouse.click(*point)
                self.assertIsNone(page.evaluate('window.gilneasApp.getSelectedId()'),'Native empty-map click clears selection')
                self.assertTrue(page.locator('#dossier').is_hidden())
                self.assertEqual(page.locator('.map-marker.selected').count(),0)
                self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before)
                self.assertEqual(page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')"),stored)
                browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
