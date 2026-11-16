"""Real atlas hierarchy, pixel-clipped coasts and redraw controls in Chrome."""
import copy,functools,json,threading,unittest
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/realm-redraw-20261115/native-realm-layout')
DRAFT='gilneas-atlas-draft-v1'
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class RealmBoundaries(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=json.loads((ROOT/'assets/data/atlas.json').read_text());cls.seed=json.loads((ROOT/'assets/data/publication-author-v5.json').read_text())
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url=f'http://127.0.0.1:{cls.server.server_port}/'
  cls.p=sync_playwright().start();cls.browser=cls.p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows']);OUT.mkdir(parents=True,exist_ok=True)
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.p.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
 def setUp(self):
  self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True);self.page=self.context.new_page();self.page.set_default_timeout(20000);self.errors=[]
  self.page.on('pageerror',lambda e:self.errors.append(str(e)));self.page.on('console',lambda m:self.errors.append(m.text) if m.type=='error' else None);self.page.on('response',lambda r:self.errors.append(f'{r.status} {r.url}') if r.status>=400 else None)
 def tearDown(self):self.context.close()
 def boot(self,raw=None):
  if raw is not None:self.page.add_init_script('if(localStorage.getItem("'+DRAFT+'")===null)localStorage.setItem("'+DRAFT+'",'+json.dumps(raw)+');')
  self.page.goto(self.url,wait_until='domcontentloaded');self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=60000)
  self.page.wait_for_function('document.querySelector("#base-map").complete&&document.querySelector("#base-map").naturalWidth>0',polling=50)
 def data(self):return self.page.evaluate('window.gilneasApp.getData()')
 def stored(self):return self.page.evaluate('localStorage.getItem("'+DRAFT+'")')
 def enable(self):self.page.locator('#editor-open').click();self.page.locator('label:has(#editing-enabled)').click();self.page.locator('[data-close="editor"]').click()
 def test_01_current_map_has_full_sovereign_outline_pixel_land_clip_and_nested_Crowley_union(self):
  self.boot();before=self.data();self.assertEqual(before,self.source);self.assertEqual(before['territories'],[]);self.assertEqual(before['territoryGrid']['migration']['method'],'author-full-realm-layout')
  mask=self.page.locator('#boundary-vector defs mask#boundary-terrain-mask');self.assertEqual(mask.count(),0);self.assertEqual(before['territoryGrid']['realmLayout']['waterPolicy'],'continuous-political-regions')
  painted=self.page.locator('#boundary-vector > path');self.assertGreater(painted.count(),0)
  self.assertTrue(all(v is None for v in painted.evaluate_all('nodes=>nodes.map(n=>n.getAttribute("mask"))')))
  roots=self.page.locator('#boundary-vector > path[data-bloc="true"]').evaluate_all('nodes=>[...new Set(nodes.map(n=>n.dataset.factionId))]');self.assertEqual(set(roots),{'gilneas','lordaeron','dalaran'})
  parent=self.page.locator('#boundary-vector > path[data-faction-id="crowley"][data-region="vassal-union"]');self.assertEqual(parent.count(),1)
  children=self.page.locator('#boundary-vector > path[data-region="vassal-union"]').evaluate_all('nodes=>nodes.map(n=>n.dataset.factionId)');self.assertIn('harford',children);self.assertIn('candren',children);self.assertIn('silverlaine',children)
  result=self.page.evaluate('''()=>{const root=new Path2D(document.querySelector('#boundary-vector > path[data-faction-id="gilneas"][data-bloc="true"]').getAttribute('d'));const parent=new Path2D(document.querySelector('#boundary-vector > path[data-faction-id="crowley"][data-region="vassal-union"]').getAttribute('d'));const ctx=document.createElement('canvas').getContext('2d');return {shadowfangInRealm:ctx.isPointInPath(root,1675,1725,'evenodd'),shadowfangInCrowley:ctx.isPointInPath(parent,1675,1725,'evenodd'),ambermillInCrowley:ctx.isPointInPath(parent,2440,1648,'evenodd'),capitalInRealm:ctx.isPointInPath(root,1825,3160,'evenodd'),dalaranOutsideRealm:!ctx.isPointInPath(root,3020,1428,'evenodd'),lakeOutsideRealm:!ctx.isPointInPath(root,2864,875,'evenodd')};}''')
  self.assertTrue(all(result.values()),result)
  self.page.evaluate('window.gilneasApp.ui.setPanel("navigation",false);window.gilneasApp.ui.setPanel("layers",false);window.gilneasApp.ui.home(false)');self.page.screenshot(path=str(OUT/'realm-overview-desktop.png'))
  self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertIsNone(self.stored());self.assertEqual(self.data(),before);self.assertEqual(self.errors,[])
 def test_02_native_rebuild_keeps_every_land_domain_and_undo_reloads_exact_snapshot(self):
  self.boot();before=self.data();self.enable();self.page.locator('#territory-editor-open').click() if self.page.locator('#territory-editor-open').count() else self.page.evaluate('window.gilneasApp.boundaries.open()')
  self.page.on('dialog',lambda d:d.accept());self.page.locator('#boundary-radius').fill('220');self.page.locator('#boundary-generate').click();self.page.evaluate('window.gilneasApp.boundaries.whenReady()')
  after=self.data();self.assertEqual(after['territoryGrid']['radius'],220);self.assertEqual(after['territoryGrid']['realmLayout']['domainCells'],before['territoryGrid']['realmLayout']['domainCells'])
  self.assertEqual([bool(v) for v in after['territoryGrid']['cells']],[bool(v) for v in before['territoryGrid']['cells']]);self.assertEqual(after['locations'],before['locations']);self.assertEqual(after['meta'],before['meta'])
  self.page.locator('#boundary-undo').click();self.page.evaluate('window.gilneasApp.boundaries.whenReady()');self.assertEqual(self.data(),before)
  self.page.locator('#boundary-close').click();raw=self.stored();self.page.reload(wait_until='domcontentloaded');self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=60000);self.assertEqual(self.data(),before);self.assertEqual(self.stored(),raw);self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertEqual(self.errors,[])
 def test_03_unchanged_author_grid_adopts_redraw_but_custom_cells_remain_exact_without_writes(self):
  raw=json.dumps(self.seed,ensure_ascii=False,indent=3)+'\n';self.boot(raw);self.assertEqual(self.data(),self.source);self.assertEqual(self.stored(),raw)
  self.page.reload(wait_until='domcontentloaded');self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=60000);self.assertEqual(self.data(),self.source);self.assertEqual(self.stored(),raw);self.assertEqual(self.errors,[])
  custom=copy.deepcopy(self.seed);custom['territoryGrid']['cells'][1000]=1 if custom['territoryGrid']['cells'][1000]==0 else 0;custom['territoryGrid']['authorNotes']={'sources':['  авторская заметка  ']};raw2=json.dumps(custom,ensure_ascii=False,indent=3)+'\n'
  self.page.evaluate('(raw)=>localStorage.setItem("'+DRAFT+'",raw)',raw2);self.page.reload(wait_until='domcontentloaded');self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=60000);self.assertEqual(self.data()['territoryGrid'],custom['territoryGrid']);self.assertEqual(self.stored(),raw2);self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertEqual(self.errors,[])
if __name__=='__main__':unittest.main()
