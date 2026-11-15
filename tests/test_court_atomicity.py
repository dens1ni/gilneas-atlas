"""New optional court registries fail before persistence and live replacement."""
import functools,http.server,json,threading,unittest,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
class CourtAtomicity(unittest.TestCase):
    def test_bad_court_wall_and_heraldry_imports_leave_exact_live_and_saved_data(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling'])
                page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}'+PREFIX);page.wait_for_function('window.gilneasApp?.ready')
                before=page.evaluate('window.gilneasApp.getData()');raw=json.dumps(before,ensure_ascii=False,indent=3)+'\n'
                page.evaluate("raw=>localStorage.setItem('gilneas-atlas-draft-v1',raw)",raw)
                page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click()
                cases=[]
                for council in [None,{}, {'version':1,'members':[{'id':'bad-seat','kind':'faction','refId':'missing','party':'neutral','stance':'unknown','advisor':False,'active':True,'note':''}]}]:
                    bad=json.loads(json.dumps(before));bad['royalCouncil']=council;cases.append(bad)
                for track in [{'value':10,'max':100,'events':{}},{'value':10,'max':100,'baseValue':10,'events':[{'id':'bad-event','name':'Событие','delta':5}]}]:
                    bad=json.loads(json.dumps(before));bad['meta']['wallConstruction']=track;cases.append(bad)
                for heraldry in [None,{'symbol':{}},{'symbol':'assets/ui/rose.svg','edge':'bad'}]:
                    bad=json.loads(json.dumps(before));bad['factions'][0]['heraldry']=heraldry;cases.append(bad)
                for bad in cases:
                    message=page.evaluate("""async value=>{try{await window.gilneasApp.importSnapshot(new File([JSON.stringify(value)],'invalid-court.json',{type:'application/json'}));return null}catch(e){return e.message}}""",bad)
                    self.assertIsNotNone(message)
                    self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before)
                    self.assertEqual(page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')"),raw)
                self.assertEqual(errors,[]);b.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
