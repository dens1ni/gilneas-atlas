import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {normalizeData,sovereignOf,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
import {generateRealmTerritoryLayout} from '../assets/js/realm-territory-layout.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const sha=name=>createHash('sha256').update(fs.readFileSync(new URL(`../${name}`,import.meta.url))).digest('hex');
export function planOf(data){const g=data.territoryGrid;const {rootKeys,domainCells,...meta}=g.realmLayout;return {...meta,version:1,width:g.width,height:g.height,step:g.step,mapWidth:g.mapWidth,mapHeight:g.mapHeight,keys:rootKeys,cells:domainCells};}

test('the explicit redraw discards former polygons and fills continuous political regions across internal water',()=>{
 const data=read('atlas.json'),author=read('publication-author-v5.json'),grid=data.territoryGrid;
 assert.deepEqual(data.territories,[],'All former published faction polygons are removed');
 assert.equal(grid.migration.method,'author-full-realm-layout');assert.equal(grid.migration.legacyPolygonsRetained,false);
 assert.ok(JSON.stringify(grid.cells)!==JSON.stringify(author.territoryGrid.cells));
 assert.deepEqual(grid.keys,data.factions.map(f=>f.id));assert.equal(grid.keys.length,16);
 assert.deepEqual(grid.realmLayout.rootKeys,['gilneas','lordaeron','dalaran']);
 assert.equal(Object.hasOwn(grid.realmLayout,'landMask'),false,'Political rendering must not clip to the historical land mask');
 assert.equal(grid.realmLayout.pixelClipRequired,false);
 assert.equal(grid.realmLayout.waterPolicy,'continuous-political-regions');
 assert.ok(grid.realmLayout.waterContinuity.filledCells>0,'Enclosed water and coastal bays join continuous regions');
 assert.equal(grid.realmLayout.waterContinuity.outerOpenSeaRemainsOutside,true);
 assert.equal(sha('assets/maps/origins-realm-landmask.png'),grid.realmLayout.terrainEvidence.landMaskSHA256,'Historical mask remains immutable archival evidence');
 assert.equal(sha(data.meta.image),grid.realmLayout.terrainEvidence.rasterSHA256);
 const root=new Map(data.factions.map(f=>[f.id,sovereignOf(data.factions,f.id)]));
 const counts=new Map();for(let i=0;i<grid.cells.length;i++){
  const value=grid.cells[i],domain=grid.realmLayout.domainCells[i];
  assert.equal(value===0,domain===0,`Outside political domain cell ${i}`);
  if(domain){const id=grid.keys[value-1];assert.equal(root.get(id),grid.realmLayout.rootKeys[domain-1]);counts.set(id,(counts.get(id)||0)+1);}
 }
 for(const id of ['gilneas','crowley','silverlaine','harford','candren','raft','evermont','harvest-witches','tidesages','dalaran','lordaeron'])assert.ok(counts.get(id)>0,id+' has a rendered region');
 const rebuilt=generateRealmTerritoryLayout(data,planOf(data),{radius:grid.radius});assert.deepEqual(rebuilt.cells,grid.cells);
 for(const location of data.locations){
  if(location.faction==null||location.type==='ferry')continue;
  const index=Math.min(grid.height-1,Math.floor(location.y/grid.step))*grid.width+Math.min(grid.width-1,Math.floor(location.x/grid.step));
  assert.equal(root.get(grid.keys[grid.cells[index]-1]),root.get(location.faction),location.id+' stays in its actual sovereign domain');
 }
 assert.deepEqual(normalizeData(data),data);assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);assert.deepEqual(data,read('publication-v6.json'));
 const manifest=JSON.parse(fs.readFileSync(new URL('../assets/runtime-manifest.json',import.meta.url),'utf8'));
 for(const file of ['assets/maps/origins-realm-landmask.png','assets/js/realm-territory-layout.mjs'])assert.ok(manifest.includes(file),file);
});
