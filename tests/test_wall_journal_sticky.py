"""Native scrolling of a long ledger; test-only events never enter production."""
import functools,json,threading,unittest,os
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('WALL_STICKY_OUT','/Users/daniil_si/.hermes/cache/scratch/wall-journal-sticky'))
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,format,*args):pass
class WallJournalSticky(unittest.TestCase):
 def test_native_long_ledger_keeps_title_and_matching_progress_visible_without_writes(self):
  source=json.loads((ROOT/'assets/data/atlas.json').read_text());draft=json.loads(json.dumps(source))
  for i in range(45):draft['meta']['wallConstruction']['events'].append({'id':f'test-only-sticky-{i}','name':f'Проверочная запись {i}','description':'Только тест прокрутки. '+('Длинная запись летописи. '*12),'delta':0,'effects':[]})
  raw=json.dumps(draft,ensure_ascii=False,indent=3)+'\n';OUT.mkdir(parents=True,exist_ok=True)
  server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
    for w,h in [(1440,1000),(390,844),(844,390)]:
     with self.subTest(viewport=(w,h)):
      context=browser.new_context(viewport={'width':w,'height':h},reduced_motion='reduce');page=context.new_page();errors=[]
      page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
      page.add_init_script('localStorage.setItem("gilneas-atlas-draft-v1",'+json.dumps(raw)+');')
      page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='domcontentloaded');page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=60000)
      before=page.evaluate('window.gilneasApp.getData()');page.locator('#wall-history-open').click();dialog=page.locator('#wall-journal');head=page.locator('#wall-journal > .dialog-head');bar=page.locator('#wall-journal-progress')
      self.assertNotIn('Начальная отметка',dialog.inner_text());self.assertEqual(bar.count(),1);self.assertTrue(bar.is_visible())
      for attr in ['value','max','aria-valuenow','aria-valuemax','aria-label']:self.assertEqual(bar.get_attribute(attr),page.locator('#wall-progress').get_attribute(attr))
      self.assertEqual(page.locator('#wall-journal-progress-value').inner_text(),page.locator('#wall-progress-value').inner_text())
      style=page.evaluate('''()=>{const a=getComputedStyle(document.querySelector('#wall-progress')),b=getComputedStyle(document.querySelector('#wall-journal-progress'));return ['height','borderTopColor','backgroundColor'].every(k=>a[k]===b[k]);}''');self.assertTrue(style)
      initial=head.bounding_box();box=dialog.bounding_box();page.mouse.move(box['x']+box['width']/2,box['y']+box['height']-35);page.mouse.wheel(0,1800)
      page.wait_for_function('document.querySelector("#wall-journal").scrollTop>200')
      after=head.bounding_box();self.assertAlmostEqual(initial['y'],after['y'],delta=1)
      self.assertGreaterEqual(bar.bounding_box()['y'],after['y']);self.assertLessEqual(bar.bounding_box()['y']+bar.bounding_box()['height'],after['y']+after['height']+1)
      self.assertTrue(page.locator('#wall-journal-title').is_visible());self.assertLessEqual(dialog.evaluate('e=>e.scrollWidth-e.clientWidth'),1)
      page.screenshot(path=str(OUT/f'sticky-{w}x{h}.png'));self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before);self.assertEqual(page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),raw);self.assertEqual(errors,[])
      page.keyboard.press('Escape');self.assertFalse(dialog.is_visible());context.close()
    browser.close()
  finally:server.shutdown();server.server_close();thread.join(timeout=2)
if __name__=='__main__':unittest.main()
