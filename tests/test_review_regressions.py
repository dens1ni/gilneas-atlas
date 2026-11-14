"""Review regressions: invalid imports, removed faction filters, native dblclick."""
import unittest,threading,functools,http.server,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class ReviewRegression(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=cls.server.serve_forever,daemon=True).start();cls.p=sync_playwright().start();cls.browser=cls.p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.p.stop();cls.server.shutdown();cls.server.server_close()
 def setUp(self):
  self.context=self.browser.new_context(viewport={'width':1440,'height':1000});self.page=self.context.new_page();self.errors=[];self.page.on('pageerror',lambda e:self.errors.append(str(e)));self.page.goto(f'http://127.0.0.1:{self.server.server_port}/');self.page.wait_for_function('window.gilneasApp?.ready')
 def tearDown(self):self.context.close()
 def test_malformed_import_leaves_live_and_saved_snapshot_untouched(self):
  page=self.page
  page.evaluate("window.gilneasApp.replaceData(window.gilneasApp.getData())")
  before=page.evaluate('window.gilneasApp.getData()');stored=page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')")
  cases=[lambda d,f=field,v=value:d['meta'].__setitem__(f,v) for field,value in [('labels',{}),('chronicle',{}),('labels',[None]),('chronicle',[None])]]
  cases.extend([
   lambda d:d['meta'].__setitem__('labels',[{'x':0,'y':0,'text':{}}]),
   lambda d:d['meta']['chronicle'][0].__setitem__('text',{}),
   lambda d:d['meta']['chronicle'][0].__setitem__('sources',{}),
   lambda d:d['meta']['chronicle'][0].__setitem__('sources',['review-missing-source']),
   lambda d:d['locations'][0].__setitem__('sources',{}),
   lambda d:d['locations'][0]['objects'].append({'id':'review-object','type':'building','name':'Проверочный объект','sources':{}}),
   lambda d:d['nobles'][0].__setitem__('sources',{}),
   lambda d:d['locations'][0].__setitem__('aliases',{}),
   lambda d:d['locations'][0].__setitem__('aliases',[None]),
   lambda d:d['sources'][0].__setitem__('title',{}),
   lambda d:d['sources'][0].__setitem__('url',[]),
  ])
  for change in cases:
   bad=json.loads(json.dumps(before));change(bad)
   result=page.evaluate('''async value=>{try{await window.gilneasApp.importSnapshot(new File([JSON.stringify(value)],'bad.json',{type:'application/json'}));return null}catch(e){return e.message}}''',bad)
   self.assertIsNotNone(result,'Invalid renderer data must be rejected')
   self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before,'Import failure must not change live data')
   self.assertEqual(page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')"),stored,'Import failure must not change persisted data')
  page.reload();page.wait_for_function('window.gilneasApp?.ready');self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before);self.assertFalse(self.errors,self.errors)
 def test_valid_import_clears_deleted_selected_faction(self):
  page=self.page
  page.evaluate("const d=window.gilneasApp.getData();d.factions.push({id:'review-house',name:'Проверочный дом',parent:'gilneas',color:'#927454'});window.gilneasApp.replaceData(d)")
  page.locator('button.faction-row[data-faction-id=review-house]').click()
  result=page.evaluate('''async()=>{const d=window.gilneasApp.getData();d.factions=d.factions.filter(f=>f.id!=='review-house');try{await window.gilneasApp.importSnapshot(new File([JSON.stringify(d)],'valid.json',{type:'application/json'}));return null}catch(e){return e.message}}''')
  self.assertIsNone(result,'A valid replacement must not retain an invalid faction filter')
  self.assertEqual(page.locator('button.faction-row[data-faction-id=review-house]').count(),0)
  self.assertEqual(page.locator('button.location-row').count(),len(page.evaluate('window.gilneasApp.getData().locations')))
  page.evaluate('window.gilneasApp.ui.render()');self.assertFalse(self.errors,self.errors)
 def test_deleting_selected_unused_house_clears_filter(self):
  page=self.page
  page.evaluate("const d=window.gilneasApp.getData();d.factions.push({id:'review-house',name:'Проверочный дом',parent:'gilneas',color:'#927454'});window.gilneasApp.replaceData(d)")
  page.locator('button.faction-row[data-faction-id=review-house]').click()
  self.assertEqual(page.locator('button.location-row').count(),0)
  page.locator('#editor-open').click();page.locator('#houses-open').click();page.locator('[data-house-delete=review-house]').click();page.locator('#confirm-yes').click()
  page.wait_for_function("!window.gilneasApp.getData().factions.some(f=>f.id==='review-house')")
  self.assertEqual(page.locator('button.faction-row[data-faction-id=review-house]').count(),0)
  self.assertEqual(page.locator('button.location-row').count(),len(page.evaluate('window.gilneasApp.getData().locations')))
  self.assertTrue(page.locator('#faction-clear').is_hidden());self.assertEqual(page.locator('#house-error').text_content(),'')
  self.assertFalse(self.errors,self.errors)
 def test_reset_clears_removed_selected_house_filter(self):
  page=self.page;baseline=page.evaluate('window.gilneasApp.getData()')
  page.evaluate("const d=window.gilneasApp.getData();d.factions.push({id:'review-house',name:'Проверочный дом',parent:'gilneas',color:'#927454'});window.gilneasApp.replaceData(d)")
  page.locator('button.faction-row[data-faction-id=review-house]').click()
  page.locator('#editor-open').click();page.locator('#draft-reset').click();page.locator('#confirm-yes').click()
  page.wait_for_function("localStorage.getItem('gilneas-atlas-draft-v1')===null")
  self.assertEqual(page.evaluate('window.gilneasApp.getData()'),baseline)
  self.assertEqual(page.locator('button.faction-row[data-faction-id=review-house]').count(),0)
  self.assertEqual(page.locator('button.location-row').count(),len(baseline['locations']))
  self.assertTrue(page.locator('#faction-clear').is_hidden());self.assertEqual(page.locator('button.faction-row[aria-pressed=true]').count(),0)
  page.locator('#search').fill(baseline['locations'][0]['name']);self.assertGreater(page.locator('button.location-row').count(),0)
  self.assertFalse(self.errors,self.errors)
 def test_map_interaction_doubleclick_finishes_before_duplicate_vertex_guard(self):
  page=self.page
  page.evaluate("window.gilneasApp.ui.setPanel('navigation',false);window.gilneasApp.ui.setPanel('layers',false);window.gilneasApp.ui.home(false);const ui=window.gilneasApp.ui;const set=ui.setMapInteraction.bind(ui);ui.setMapInteraction=callback=>{window.reviewInteraction=callback;set(callback)}")
  count=page.evaluate('window.gilneasApp.getData().territories.length');page.locator('#editor-open').click();page.locator('#territories-open').click();page.locator('#territory-name').fill('Область callback');page.locator('#territory-faction').select_option('crowley');page.locator('#territory-form button[type=submit]').click()
  page.evaluate("window.reviewCallback=window.reviewInteraction;for(const p of [[1450,3730],[1620,3730],[1620,3910]])window.reviewCallback(p,{type:'click'});window.reviewCallback([1620,3910],{type:'dblclick'})")
  self.assertEqual(page.evaluate('window.gilneasApp.getData().territories.length'),count+1)
  self.assertEqual(len(page.evaluate('window.gilneasApp.getData().territories.at(-1).points')),3)
  page.evaluate("window.reviewCallback([1620,3910],{type:'dblclick'});window.reviewCallback([1620,3910],{type:'dblclick'})")
  self.assertEqual(page.evaluate('window.gilneasApp.getData().territories.length'),count+1)
  self.assertTrue(page.locator('#map-task').is_hidden());self.assertFalse(self.errors,self.errors)
 def test_native_doubleclick_finishes_real_polygon_task(self):
  page=self.page;page.evaluate("window.gilneasApp.ui.setPanel('navigation',false);window.gilneasApp.ui.setPanel('layers',false);window.gilneasApp.ui.home(false)")
  count=page.evaluate('window.gilneasApp.getData().territories.length');page.locator('#editor-open').click();page.locator('#territories-open').click();page.locator('#territory-name').fill('Область двойного щелчка');page.locator('#territory-faction').select_option('crowley');page.locator('#territory-form button[type=submit]').click();cam=page.evaluate('window.gilneasApp.ui.getCamera()');r=page.locator('#viewport').bounding_box()
  def screen(x,y):return (r['x']+cam['x']+x*cam['scale'],r['y']+cam['y']+y*cam['scale'])
  page.mouse.click(*screen(1450,3730));page.mouse.click(*screen(1620,3730));page.mouse.dblclick(*screen(1620,3910));page.wait_for_timeout(80)
  self.assertEqual(page.evaluate('window.gilneasApp.getData().territories.length'),count+1,'Native dblclick must close and commit the polygon')
  self.assertEqual(len(page.evaluate('window.gilneasApp.getData().territories.at(-1).points')),3)
  snapshot=page.evaluate('window.gilneasApp.getData()')
  page.mouse.dblclick(*screen(1620,3910));page.mouse.dblclick(*screen(1620,3910))
  self.assertEqual(page.evaluate('window.gilneasApp.getData()'),snapshot)
  self.assertEqual(page.evaluate("JSON.parse(localStorage.getItem('gilneas-atlas-draft-v1'))"),snapshot)
  self.assertTrue(page.locator('#map-task').is_hidden());self.assertFalse(self.errors,self.errors)
 def test_native_doubleclick_first_vertex_closes_without_duplicate(self):
  page=self.page;page.evaluate("window.gilneasApp.ui.setPanel('navigation',false);window.gilneasApp.ui.setPanel('layers',false);window.gilneasApp.ui.home(false)")
  count=page.evaluate('window.gilneasApp.getData().territories.length');page.locator('#editor-open').click();page.locator('#territories-open').click();page.locator('#territory-name').fill('Замыкание первой вершины');page.locator('#territory-faction').select_option('crowley');page.locator('#territory-form button[type=submit]').click();cam=page.evaluate('window.gilneasApp.ui.getCamera()');r=page.locator('#viewport').bounding_box()
  def screen(x,y):return (r['x']+cam['x']+x*cam['scale'],r['y']+cam['y']+y*cam['scale'])
  for point in [(1450,3730),(1620,3730),(1620,3910)]:page.mouse.click(*screen(*point))
  page.mouse.dblclick(*screen(1450,3730))
  self.assertEqual(page.evaluate('window.gilneasApp.getData().territories.length'),count+1)
  points=page.evaluate('window.gilneasApp.getData().territories.at(-1).points')
  self.assertEqual(len(points),3);self.assertEqual(len({tuple(p) for p in points}),3)
  self.assertTrue(page.locator('#map-task').is_hidden());self.assertFalse(self.errors,self.errors)
if __name__=='__main__':unittest.main()
