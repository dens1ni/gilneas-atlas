import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';
import {normalizeData} from '../assets/js/model.mjs';
import {generateRealmTerritoryLayout} from '../assets/js/realm-territory-layout.mjs';
import fs from 'node:fs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
function fixture(){
 const previous=read('publication-v5.json'),seed=read('publication-author-v5.json'),published=read('atlas.json');
 const plan={version:1,width:Math.ceil(published.meta.width/16),height:Math.ceil(published.meta.height/16),step:16,mapWidth:published.meta.width,mapHeight:published.meta.height,image:published.meta.image,mapRevision:published.meta.mapRevision,keys:['gilneas','lordaeron','dalaran'],cells:new Array(Math.ceil(published.meta.width/16)*Math.ceil(published.meta.height/16)).fill(1),basis:'explicit-user-authorship'};
 // Labelled synthetic land plan: domain integration, NOT production cartography.
 published.territories=[];published.territoryGrid=generateRealmTerritoryLayout(published,plan);
 return {previous,seed,published};
}

test('a full-domain release replaces an untouched supplied author grid and old polygons atomically',()=>{
 const {previous,seed,published}=fixture(),before=structuredClone(seed);
 const next=normalizeData(reconcileDraftPublication(seed,published,previous,seed));
 assert.deepEqual(seed,before);assert.ok(JSON.stringify(next.territoryGrid)===JSON.stringify(published.territoryGrid),'Untouched author grid must adopt the new full-domain grid');
 assert.deepEqual(next.territories,[]);
});

test('a full-domain release preserves a custom grid, explicit erasures and an absent grid after prior presence',()=>{
 const {previous,seed,published}=fixture();
 for(const change of [draft=>{draft.territoryGrid.cells[1000]=draft.territoryGrid.cells[1000]===0?1:0;},draft=>{draft.territoryGrid.authorNotes={sources:['  авторский текст  ']};},draft=>{delete draft.territoryGrid;}]){
  const draft=structuredClone(seed);change(draft);const before=structuredClone(draft);
  const next=reconcileDraftPublication(draft,published,previous,seed);
  assert.deepEqual(draft,before);assert.equal(Object.hasOwn(next,'territoryGrid'),Object.hasOwn(before,'territoryGrid'));
  if(Object.hasOwn(before,'territoryGrid'))assert.deepEqual(next.territoryGrid,before.territoryGrid);
 }
});

test('a current house deletion does not adopt invalid new grid keys, and custom legacy polygons remain literal',()=>{
 const {previous,seed,published}=fixture();
 const noHouse=structuredClone(seed);noHouse.factions=noHouse.factions.filter(f=>f.id!=='silverlaine');
 for(const location of noHouse.locations)if(location.faction==='silverlaine')location.faction='crowley';
 for(const noble of noHouse.nobles)if(noble.house==='silverlaine')noble.house=null;
 noHouse.territories=noHouse.territories.filter(p=>p.faction!=='silverlaine');
 noHouse.territoryGrid.keys=noHouse.territoryGrid.keys.filter(key=>key!=='silverlaine');noHouse.territoryGrid.cells.fill(0);
 const result=reconcileDraftPublication(noHouse,published,previous,seed);
 assert.deepEqual(result.territoryGrid,noHouse.territoryGrid);
 const custom=structuredClone(seed);custom.territories[0].authorNotes='  старая ручная область  ';
 assert.deepEqual(reconcileDraftPublication(custom,published,previous,seed).territories,custom.territories);
});
