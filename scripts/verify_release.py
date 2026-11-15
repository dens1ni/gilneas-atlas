"""Verify a clean ZIP byte-for-byte, then exercise root and project paths."""
import argparse
import functools
import hashlib
import http.server
import json
import shutil
import threading
import zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright

SOURCE=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--zip',default='/Users/daniil_si/Downloads/Гилнеас-GitHub-Pages.zip')
parser.add_argument('--output',default='/Users/daniil_si/.hermes/cache/scratch/gilneas-clean-release-verification')
args=parser.parse_args()
archive_path=Path(args.zip)
output=Path(args.output)
output.mkdir(parents=True,exist_ok=True)
clean=output/'site'
prefixed=output/'project'/'gilneas-atlas'
for target in (clean,prefixed):
    if target.exists():shutil.rmtree(target)
    target.mkdir(parents=True)
manifest=json.loads((SOURCE/'assets/runtime-manifest.json').read_text())
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None,'ZIP CRC failed'
    names=archive.namelist()
    assert len(names)==len(set(names))==len(manifest)
    assert set(names)==set(manifest)
    for name in names:
        assert not name.startswith('/') and '..' not in Path(name).parts,name
        assert archive.read(name)==(SOURCE/name).read_bytes(),f'Candidate byte mismatch: {name}'
    archive.extractall(clean)
shutil.copytree(clean,prefixed,dirs_exist_ok=True)
published=json.loads((clean/'assets/data/atlas.json').read_text())
results=[]
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

with sync_playwright() as playwright:
    browser=playwright.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
    for server_root,prefix in [(clean,'/'),(prefixed.parent,'/gilneas-atlas/')]:
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(server_root)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        try:
            page=context.new_page();page.set_default_timeout(15000);errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
            page.on('response',lambda response:errors.append(f'{response.status} {response.url}') if response.status>=400 else None)
            url=f'http://127.0.0.1:{server.server_port}'+prefix
            page.goto(url,wait_until='domcontentloaded')
            page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=40000)
            page.wait_for_function('document.querySelector("#base-map").complete && document.querySelector("#base-map").naturalWidth>0',polling=50)
            data=page.evaluate('window.gilneasApp.getData()')
            assert len(data['locations'])==39 and len(data['nobles'])==26 and len(data['sources'])==124
            assert data['meta']['publicationRevision']=='royal-council-v5'
            assert len(data['royalCouncil']['members'])==33
            for field in ['locations','nobles','sources','factions','territories','royalCouncil']:
                assert data[field]==published[field],field
            assert page.locator('#base-map').evaluate('e=>[e.naturalWidth,e.naturalHeight]')==[5289,6822]
            assert not page.locator('#editing-enabled').is_checked()
            assert page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")') is None
            page.locator('#help-open').click()
            assert page.locator('#help .dialog-content > section').count()==1
            assert page.locator('#help .dialog-content h3').inner_text()=='Управление картой'
            page.keyboard.press('Escape')
            page.locator('#search').fill('Торговая площадь')
            page.locator('button.location-row[data-location-id="merchant-square"]').click()
            favorite=page.locator('#dossier-favorite');favorite.scroll_into_view_if_needed();favorite.click()
            assert favorite.locator('svg').evaluate('e=>getComputedStyle(e).fill')=='rgb(224, 196, 147)'
            assert page.evaluate('window.gilneasApp.getData()')==data
            assert page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")') is None
            page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close="editor"]').click()
            page.locator('#search').fill('Янтарная')
            page.locator('button.location-row[data-location-id="ambermill"]').click()
            assert page.locator('#dossier-owner').inner_text()=='Дариус Краули'
            page.locator('#dossier-add-object').click();page.locator('#object-name').fill('Проверка чистого архива')
            page.locator('#modifier-bonus-add').click();page.locator('#modifier-list textarea').fill('  Проверочный бонус +1  ')
            page.locator('#object-form button[type=submit]').click()
            saved=page.evaluate('window.gilneasApp.getData()')
            for field in ['nobles','sources','factions','territories','territoryGrid','royalCouncil']:
                assert saved[field]==data[field],field
            assert any(obj['name']=='Проверка чистого архива' for row in saved['locations'] for obj in row['objects'])
            page.reload(wait_until='domcontentloaded');page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=40000)
            assert page.evaluate('window.gilneasApp.getData()')==saved
            assert not page.locator('#editing-enabled').is_checked()
            page.locator('#editor-open').click()
            with page.expect_download(timeout=60000) as download:page.locator('#export-json').click()
            json_path=output/('snapshot-root.json' if prefix=='/' else 'snapshot-prefix.json')
            download.value.save_as(str(json_path));assert json.loads(json_path.read_text())==saved
            with page.expect_download(timeout=60000) as download:page.locator('#export-site').click()
            zip_path=output/('reexport-root.zip' if prefix=='/' else 'reexport-prefix.zip')
            download.value.save_as(str(zip_path))
            with zipfile.ZipFile(zip_path) as exported:
                assert exported.testzip() is None
                assert set(exported.namelist())==set(manifest)
                assert json.loads(exported.read('assets/data/atlas.json'))==saved
                for name in manifest:
                    if name!='assets/data/atlas.json':assert exported.read(name)==(SOURCE/name).read_bytes(),name
            page.locator('[data-close="editor"]').click()
            page.set_viewport_size({'width':390,'height':844})
            page.evaluate('window.gilneasApp.nobleDossier.open("noble-mia")')
            assert page.locator('#noble-name').inner_text()=='Миа Седогрив'
            assert page.locator('#noble-dossier .noble-life-status').get_attribute('data-life-status')=='alive'
            assert page.locator('#noble-holdings .noble-holding').count()==0
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(output/('family-root.png' if prefix=='/' else 'family-prefix.png')))
            assert not errors,errors
            results.append({'prefix':prefix,'nobles':len(data['nobles']),'locations':len(data['locations']),'sources':len(data['sources']),'council':len(data['royalCouncil']['members']),'readonly_start_reload':True,'favorite_gold_no_draft':True,'editor_reload':True,'json_reexport':True,'site_reexport':True,'mobile_family':True,'errors':errors})
        finally:
            context.close();server.shutdown();server.server_close();thread.join(timeout=2)
    browser.close()
report={'archive':str(archive_path),'archiveSHA256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),'runtimeFiles':len(manifest),'sourceBytesMatch':True,'checks':results}
(output/'release-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
