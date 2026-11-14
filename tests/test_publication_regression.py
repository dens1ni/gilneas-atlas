import unittest,functools,http.server,threading,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class PublicationRegression(unittest.TestCase):
 def test_citation_numbers_match_global_archive_and_unknown_is_not_independence(self):
  handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT));server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    b=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows']);page=b.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready')
    page.evaluate("window.gilneasApp.selectId('gilneas-city')")
    links=page.locator('#dossier-provenance .source-citation').evaluate_all('(nodes)=>nodes.map(n=>({id:n.dataset.sourceId,text:n.textContent}))')
    self.assertTrue(links)
    for link in links:self.assertEqual(link['text'],f"[{link['id']}]",'Dossier and archive must use the same source number')
    page.evaluate("window.gilneasApp.selectId('northgate-river')")
    self.assertEqual(page.locator('#dossier-sovereign').inner_text(),'Не установлено','Unknown political tenure must not become confirmed independence')
    page.evaluate("window.gilneasApp.selectId('gilneas-city')")
    self.assertEqual(page.locator('#dossier-provenance .confidence').count(),0,'Historical bookkeeping stays in data, not the visible card')
    b.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
