"""Verify exact deployed bytes and exercise the actual Pages application."""
import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('url')
parser.add_argument('--output', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
base = args.url.rstrip('/') + '/'
manifest = json.loads((root / 'assets/runtime-manifest.json').read_text())
verified = []
for name in manifest:
    if name == '.nojekyll' or name.startswith('.github/'):
        continue
    request = urllib.request.Request(base + name, headers={'User-Agent': 'Gilneas-Atlas-Release-Verification/1.0', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=60) as response:
        actual = response.read()
        assert response.status == 200, (name, response.status)
    expected = (root / name).read_bytes()
    assert actual == expected, f'Deployed file differs from reviewed release: {name}'
    verified.append({'path': name, 'bytes': len(actual), 'sha256': hashlib.sha256(actual).hexdigest()})

errors = []
failed = []
console_errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--disable-renderer-backgrounding', '--disable-background-timer-throttling', '--disable-backgrounding-occluded-windows'])
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
    page.on('response', lambda response: failed.append({'url': response.url, 'status': response.status}) if response.status >= 400 else None)
    page.goto(base, wait_until='networkidle', timeout=120000)
    page.wait_for_function('window.gilneasApp?.ready', timeout=60000)
    baseline = page.evaluate('window.gilneasApp.getData()')
    assert len(baseline['locations']) == 39
    assert len(baseline['nobles']) == 17
    assert len(baseline['sources']) == 69
    assert len(baseline['territoryGrid']['cells']) == 62985
    assert page.locator('#wall-progress').get_attribute('value') == '10'
    assert page.locator('#wall-progress').get_attribute('max') == '100'
    assert page.locator('#boundary-vector path').count() > 0
    assert baseline['meta']['gilneasCrest'] == 'assets/ui/gilneas-royal-shield.svg'
    assert page.locator('.brand img').get_attribute('src') == 'assets/ui/gilneas-royal-shield.svg'
    assert page.locator('#map-home img').get_attribute('src') == 'assets/ui/gilneas-royal-shield.svg'
    assert page.locator('.brand img').evaluate('e=>getComputedStyle(e).backgroundColor') == 'rgba(0, 0, 0, 0)'
    assert page.locator('img[src*=gilneas-human-banner]').count() == 0
    assert all(location.get('wowpediaUrl') and location.get('shortDescription') for location in baseline['locations'])
    assert page.locator('#base-map').evaluate('e=>[e.naturalWidth,e.naturalHeight]') == [5289, 6822]
    assert all(not location['objects'] for location in baseline['locations'])
    page.screenshot(path=str(out / 'live-desktop.png'), full_page=True)
    page.locator('#search').fill('Янтарная')
    page.locator('button.location-row[data-location-id=ambermill]').click()
    assert page.locator('#dossier-owner').inner_text() == 'Дариус Краули'
    page.locator('#dossier-add-object').click()
    page.locator('#object-name').fill('Проверка опубликованного атласа')
    page.locator('#modifier-bonus-add').click()
    page.locator('#modifier-list textarea').fill('Бонус проверки +1')
    page.locator('#modifier-penalty-add').click()
    page.locator('#modifier-list textarea').nth(1).fill('Штраф проверки −1')
    page.locator('#object-form button[type=submit]').click()
    snapshot = page.evaluate('window.gilneasApp.getData()')
    location = next(record for record in snapshot['locations'] if record['id'] == 'ambermill')
    obj = next(record for record in location['objects'] if record['name'] == 'Проверка опубликованного атласа')
    assert {modifier['kind'] for modifier in obj['modifiers']} == {'bonus', 'penalty'}
    page.reload(wait_until='networkidle')
    page.wait_for_function('window.gilneasApp?.ready')
    assert page.evaluate('window.gilneasApp.getData()') == snapshot
    page.evaluate("window.gilneasApp.selectId('ambermill')")
    page.wait_for_timeout(550)
    page.screenshot(path=str(out / 'live-dossier.png'), full_page=True)
    stored = page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')")
    invalid = json.loads(json.dumps(snapshot))
    invalid['meta']['labels'] = {}
    message = page.evaluate("""async data=>{try{await window.gilneasApp.importSnapshot(new File([JSON.stringify(data)],'invalid.json',{type:'application/json'}));return null}catch(e){return e.message}}""", invalid)
    assert message, 'Invalid metadata must fail validation'
    assert page.evaluate('window.gilneasApp.getData()') == snapshot
    assert page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')") == stored
    page.locator('#editor-open').click()
    with page.expect_download(timeout=60000) as download:
        page.locator('#export-site').click()
    zip_path = out / 'live-export.zip'
    download.value.save_as(str(zip_path))
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.testzip() is None
        assert archive.read('.nojekyll') == b''
        assert archive.read('.github/workflows/deploy-pages.yml') == (root / '.github/workflows/deploy-pages.yml').read_bytes()
        assert json.loads(archive.read('assets/data/atlas.json')) == snapshot
        assert set(archive.namelist()) == set(manifest)
    page.locator('#draft-reset').click()
    page.locator('#confirm-yes').click()
    assert page.evaluate('window.gilneasApp.getData()') == baseline
    page.reload(wait_until='networkidle')
    page.wait_for_function('window.gilneasApp?.ready')
    assert page.evaluate('window.gilneasApp.getData()') == baseline
    page.locator('#filter-all').click()
    page.locator('#search').fill('')
    page.evaluate("window.gilneasApp.ui.setPanel('navigation',true)")
    tree=page.locator('#location-list details[data-faction-id=gilneas] details[data-faction-id=crowley] details[data-faction-id=silverlaine]')
    assert tree.count()==1
    page.evaluate("window.gilneasApp.ui.setPanel('dossier',false);window.gilneasApp.ui.setPanel('navigation',false);window.gilneasApp.ui.setPanel('layers',false);window.gilneasApp.ui.focusLocation('shadowfang',false)")
    page.locator('.map-marker[data-location-id=shadowfang]').hover()
    assert page.locator('#marker-tooltip').is_visible()
    assert page.locator('.tooltip-faction').inner_text()=='Дом Сребролена'
    page.mouse.move(2,2)
    page.evaluate("window.gilneasApp.nobleDossier.open('noble-darius')")
    assert page.locator('#noble-dossier').is_visible()
    assert 'Генн Седогрив' in page.locator('#noble-suzerain').inner_text()
    assert 'Крепость над Пирвудом' in page.locator('#noble-holdings').inner_text()
    assert page.locator('#noble-crest .faction-shield').count() == 1
    assert page.locator('#noble-crest .shield-device').get_attribute('href').endswith('gilneas-royal-symbol.png')
    assert page.locator('#noble-dossier').evaluate('e=>getComputedStyle(e).backgroundColor') == page.locator('#navigation').evaluate('e=>getComputedStyle(e).backgroundColor')
    page.screenshot(path=str(out/'live-noble.png'),full_page=True)
    page.mouse.click(2,2)
    assert page.locator('#noble-dossier').is_hidden()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.evaluate("window.gilneasApp.selectId('gilneas-city')")
    page.wait_for_timeout(550)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(out / 'live-mobile.png'), full_page=True)
    assert not errors, errors
    assert not failed, failed
    assert not console_errors, console_errors
    context.close()
    browser.close()

result = {'url': base, 'byte_matches': verified, 'catalogue': {'locations': 39, 'nobles': 17, 'sources': 69}, 'image_size': [5289, 6822], 'tests': {'editor_bonus_penalty': 'passed', 'hover': 'passed', 'tree': 'passed', 'noble_modal': 'passed', 'naitroud_boundaries': 'passed', 'wall_progress': 'passed', 'reload': 'passed', 'invalid_import_atomicity': 'passed', 'browser_zip_export': 'passed', 'reset': 'passed', 'mobile': 'passed'}, 'page_errors': errors, 'http_errors': failed, 'console_errors': console_errors}
(out / 'live-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
