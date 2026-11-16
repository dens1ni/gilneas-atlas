import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const json=async name=>JSON.parse(await readFile(new URL('../assets/data/'+name,import.meta.url),'utf8'));

test('every existing location retains source-linked immersive lore and receives its reviewed new map point',async()=>{
  const [current,original]=await Promise.all([json('publication-v5.json'),json('publication-v1.json')]);
  assert.equal(current.locations.length,39);assert.deepEqual(current.locations.map(l=>l.id),original.locations.map(l=>l.id));
  for(const location of current.locations){
    const before=original.locations.find(l=>l.id===location.id);
    assert.equal(location.name,before.name,location.id);
    assert.ok(location.x>=0&&location.x<=current.meta.width&&location.y>=0&&location.y<=current.meta.height,location.id+' map bounds');
    assert.ok(location.description.length>=100,location.id+' needs actual lore');
    assert.ok(location.shortDescription?.length,location.id+' needs a hover summary');
    assert.doesNotMatch(location.description,/реконструкц|можно добав|не назнач|для вашего сценария|показан[ао]? как|поздн.{0,12}источник/i,location.id);
    const url=new URL(location.wowpediaUrl);assert.equal(url.hostname,'wowpedia.fandom.com',location.id);assert.ok(url.pathname.startsWith('/wiki/'),location.id);
    assert.ok(location.provenance.sources.length,location.id);
    if(location.id==='shadowfang')assert.equal(location.owner,'Барон Сребролен');else assert.equal(location.owner,before.owner,'No unrequested private owner inventions: '+location.id);
  }
});

test('every registered noble gets historical description appearance social status and a source-backed allegiance',async()=>{
  const [current,original]=await Promise.all([json('publication-v5.json'),json('publication-v1.json')]);
  const census=JSON.parse(await readFile(new URL('../docs/noble-family-census.json',import.meta.url),'utf8'));
  assert.equal(current.nobles.length,original.nobles.length+census.additions.length);
  assert.deepEqual(current.nobles.slice(0,original.nobles.length).map(n=>n.id),original.nobles.map(n=>n.id));
  assert.deepEqual(current.nobles.slice(original.nobles.length).map(n=>n.id),census.additions.map(a=>a.noble.id));
  for(const noble of current.nobles){
    assert.ok(noble.description?.length,noble.id);assert.ok(noble.appearance?.length,noble.id);assert.ok(noble.socialStatus?.length,noble.id);assert.ok(noble.allegiance?.length||noble.overlord?.length,noble.id);assert.ok(noble.sources.length,noble.id);
    if(original.nobles.some(row=>row.id===noble.id))assert.doesNotMatch(noble.description,/реконструкц|не назнач|не перенос|в текущем слое/i,noble.id);
    else assert.deepEqual(noble,census.additions.find(a=>a.noble.id===noble.id).noble,'New archival references retain their reviewed chronological and canonicality caveats');
  }
  assert.equal(current.factions.find(f=>f.id==='silverlaine').parent,'crowley');assert.equal(current.factions.find(f=>f.id==='silverlaine').ruler,'Барон Сребролен');
  assert.equal(current.meta.wallConstruction.value,10);assert.equal(current.meta.wallConstruction.max,100);assert.equal(current.meta.publicationRevision,'royal-council-v5');
});
