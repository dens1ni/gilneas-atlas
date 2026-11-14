"""Exercise the clean delivered ZIP at root and a project Pages prefix."""
import json,functools,http.server,threading,zipfile,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ZIP=Path('/Users/daniil_si/Downloads/Гилнеас-GitHub-Pages.zip')
ROOT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-clean-release-verification')
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
shutil.rmtree(ROOT,ignore_errors=True);ROOT.mkdir(parents=True)
z=zipfile.ZipFile(ZIP);assert z.testzip() is None;z.extractall(ROOT)
shutil.copytree(ROOT,ROOT.parent/'gilneas-clean-project-prefix'/'gilneas-atlas',dirs_exist_ok=True)
results=[]
with sync_playwright() as p:
 b=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
 for root,prefix in [(ROOT,'/'),(ROOT.parent/'gilneas-clean-project-prefix','/gilneas-atlas/')]:
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   ctx=b.new_context(viewport={'width':1440,'height':1000});page=ctx.new_page();err=[];bad=[];page.on('pageerror',lambda e:err.append(str(e)));page.on('response',lambda r:bad.append([r.status,r.url]) if r.status>=400 else None)
   page.goto(f'http://127.0.0.1:{server.server_port}'+prefix);page.wait_for_function('window.gilneasApp?.ready');d=page.evaluate('window.gilneasApp.getData()');assert len(d['locations'])==39;assert len(d['nobles'])==17;assert all(not l['objects'] for l in d['locations']);assert page.locator('#base-map').evaluate('(e)=>[e.naturalWidth,e.naturalHeight]')==[5289,6822]
   page.locator('#search').fill('Янтарная');page.locator('button.location-row[data-location-id=ambermill]').click();assert page.locator('#dossier-owner').inner_text()=='Дариус Краули';page.locator('#dossier-add-object').click();page.locator('#object-name').fill('Проверка архива');page.locator('#modifier-bonus-add').click();page.locator('#modifier-list textarea').fill('Работает в экспортированном сайте');page.locator('#object-form button[type=submit]').click();page.reload();page.wait_for_function('window.gilneasApp?.ready');assert any(o['name']=='Проверка архива' for l in page.evaluate('window.gilneasApp.getData()')['locations'] for o in l['objects']);assert not err,err;assert not bad,bad
   results.append({'prefix':prefix,'points':len(d['locations']),'nobles':len(d['nobles']),'asset_errors':bad,'page_errors':err,'editor_reload':'passed'});ctx.close()
  finally:server.shutdown();server.server_close()
 b.close()
Path('/Users/daniil_si/gilneas-atlas/docs/release-verification.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
