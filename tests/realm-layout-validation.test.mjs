import test from 'node:test';
import assert from 'node:assert/strict';
import { validate } from '../assets/js/territory-engine.mjs';
const factions=[{id:'gilneas',parent:null},{id:'crowley',parent:'gilneas'},{id:'silverlaine',parent:'crowley'},{id:'lordaeron',parent:null},{id:'dalaran',parent:null}];
const meta={width:32,height:16,image:'assets/maps/test-only.webp',mapRevision:'test-only'};
const valid=()=>({version:1,width:2,height:1,step:16,mapWidth:32,mapHeight:16,keys:factions.map(f=>f.id),cells:[2,0],radius:260,realmLayout:{version:1,image:meta.image,mapRevision:meta.mapRevision,rootKeys:['gilneas','lordaeron','dalaran'],domainCells:[1,0],authorNotes:{sources:['literal opaque source extension']}}});

test('a map-bound sovereign layout is validated before cloning or accepting a snapshot',()=>{
 for(const mutation of [
  grid=>grid.realmLayout=null,
  grid=>grid.realmLayout.version='1',
  grid=>grid.realmLayout.image='wrong.webp',
  grid=>grid.realmLayout.mapRevision='wrong-map',
  grid=>grid.realmLayout.rootKeys=['gilneas','crowley','dalaran'],
  grid=>grid.realmLayout.rootKeys=['gilneas','gilneas','dalaran'],
  grid=>grid.realmLayout.rootKeys=['gilneas','lordaeron','missing'],
  grid=>grid.realmLayout.domainCells=[1],
  grid=>grid.realmLayout.domainCells=[1,4],
  grid=>grid.realmLayout.domainCells=[1,'0'],
  grid=>delete grid.realmLayout.domainCells[1],
 ]) {const grid=valid();mutation(grid);assert.throws(()=>validate(grid,factions,meta),/territoryGrid/,JSON.stringify(grid));}
});

test('valid layouts retain opaque author metadata and do not restrict later intentional brush edits',()=>{
 const grid=valid();grid.cells=[4,0]; // Manual authoring can redraw a political frontier.
 const before=structuredClone(grid),detached=validate(grid,factions,meta);
 assert.deepEqual(detached,before);assert.deepEqual(grid,before);assert.notEqual(detached.realmLayout,grid.realmLayout);
 assert.notEqual(detached.realmLayout.domainCells,grid.realmLayout.domainCells);
 delete grid.realmLayout;assert.deepEqual(validate(grid,factions,meta),grid,'Legacy grids remain valid and absent layout metadata stays absent');
});
