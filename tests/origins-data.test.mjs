import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);

test('Origins replaces every reviewed marker point while preserving names owners lore and map glyph types',async()=>{
  const data=JSON.parse(await readFile(new URL('assets/data/publication-v5.json',root),'utf8'));
  const previous=JSON.parse(await readFile(new URL('assets/data/publication-v2.json',root),'utf8'));
  assert.equal(data.meta.width,3526,'Use the newly supplied custom map');assert.equal(data.meta.height,4548);
  assert.equal(data.meta.image,'assets/maps/gilneas-origins-enhanced.webp');
  assert.equal(data.meta.mapRevision,'origins-map-v3');
  const coords=JSON.parse(await readFile(new URL('assets/data/origins-coordinates.json',root),'utf8'));
  assert.equal(coords.locations.length,39);assert.equal(new Set(coords.locations.map(record=>record.id)).size,39);
  assert.deepEqual(data.locations.map(record=>record.id),previous.locations.map(record=>record.id));
  for(const location of data.locations){
    const before=previous.locations.find(record=>record.id===location.id),reviewed=coords.locations.find(record=>record.id===location.id);
    assert.ok(reviewed,location.id);assert.deepEqual([location.x,location.y],[reviewed.x,reviewed.y],location.id);
    assert.notDeepEqual([location.x,location.y],[before.x,before.y],location.id+' must be reviewed on the new raster');
    for(const field of ['name','owner','faction','type','capital','description','shortDescription','wowpediaUrl','objects'])assert.deepEqual(location[field],before[field],location.id+' '+field);
    assert.ok(location.x>=0&&location.x<=data.meta.width&&location.y>=0&&location.y<=data.meta.height,location.id);
  }
  assert.equal(data.meta.gilneasCrest,'assets/ui/gilneas-royal-shield.svg');
  assert.equal(data.meta.gilneasHeraldry.symbol,'assets/ui/gilneas-royal-symbol.png');
});

test('scenario territories follow relocated major estates and the junior-vassal castle',async()=>{
  const {prepareTerritoryGrid}=await import('../assets/js/territory-data.mjs');
  const raw=JSON.parse(await readFile(new URL('assets/data/publication-v5.json',root),'utf8')),data=prepareTerritoryGrid(raw),grid=data.territoryGrid;
  for(const [id,expected] of [['greymane-manor','greymane'],['duskhaven','gilneas'],['crowley-orchard','crowley'],['crowley-stable-grounds','crowley'],['galewatch-lighthouse','gilneas'],['the-headlands','gilneas'],['shadowfang','silverlaine'],['dalaran-city','dalaran']]){
    const point=data.locations.find(record=>record.id===id),owner=grid.cells[Math.floor(point.y/grid.step)*grid.width+Math.floor(point.x/grid.step)];
    assert.equal(grid.keys[owner-1]??null,expected,id+' must be inside its relocated scenario influence, not the old point envelope');
  }
});
