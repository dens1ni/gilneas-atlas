import test from 'node:test';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';
import {effectiveFaction,normalizeData,sovereignOf} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const assignedIds=[
 'location-df0aa1e2-31ba-43fa-b6b0-84c7733f625a',
 'location-fb88bb30-c639-4f75-a142-92445555a772',
 'location-b415ddf5-f12a-4421-829f-e8723bdaa1d4',
 'location-a4bf5eb0-1154-4519-9400-f17ced83a1d9',
 'location-8288bc4e-bb08-45d9-ace3-bc878fe7e8ba',
 'location-54cebe0e-8a63-43c7-86d2-b85f6edf2732',
 'location-544521a1-babb-4fea-af73-6ebb91c476e0',
 'location-8ee04e39-6c00-4b0b-9bcf-17de4fddb9bb',
 'location-3325cfda-47a7-4e3d-9cac-3797f4dbaa9d',
 'location-17511ea5-f77c-4d83-a187-ee2da7acbf21',
 'location-426acd7a-5f00-48c0-a6aa-1de9ce3ac2fc',
 'location-ecbf79ff-610a-4bde-8d16-a437954ed7a4',
 'location-f2adc0b4-c081-404a-a546-16ca52d028aa',
 'location-94b0bb4b-f058-4b9d-9ec3-eb3fdb02b21f',
 'location-3cfcf216-6753-4b1a-bd43-3adc40bd96f0',
 'location-6e3bbad5-4890-4ae0-b8cc-1a3fa97535a4',
];

test('formerly unassigned Gilnean places remain assigned, with the exact later Raft, Candren and Harford transfers',()=>{
 const data=read('atlas.json');
 assert.equal(assignedIds.length,16);
 for(const id of assignedIds){
  const location=data.locations.find(place=>place.id===id);assert.ok(location,id);
  const assignments={'location-544521a1-babb-4fea-af73-6ebb91c476e0':['raft','Дом Рафт'],'location-df0aa1e2-31ba-43fa-b6b0-84c7733f625a':['candren','Лорд Кандрен'],'location-fb88bb30-c639-4f75-a142-92445555a772':['harford','Лорд Харфорд']};
  const [faction,owner]=assignments[id]??['gilneas',''];
  assert.equal(location.faction,faction,id);
  assert.equal(location.owner,owner,id+' only explicit or evidence-labelled later author assignments');
  for(const object of location.objects)assert.equal(effectiveFaction(location,object),faction,object.id);
 }
 const grid=data.territoryGrid;
 for(const location of data.locations){
  const x=Math.floor(location.x/grid.step),y=Math.floor(location.y/grid.step);
  const value=grid.cells[y*grid.width+x];
  if(value && sovereignOf(data.factions,grid.keys[value-1])==='gilneas'){
   assert.notEqual(location.faction,null,location.id);
   for(const object of location.objects)assert.notEqual(effectiveFaction(location,object),null,object.id);
  }
 }
 // The separately requested full-realm redraw replaces historical owner-0 pockets.
 assert.ok(isDeepStrictEqual(grid,read('publication-v6.json').territoryGrid), 'Current published full-realm boundaries remain exact');
 assert.equal(grid.migration.method,'author-full-realm-layout');
 assert.deepEqual(data.territories,[]);
 const lake=data.locations.find(place=>place.id==='lordamere-lake');
 assert.equal(lake.faction,null);
 for(const object of lake.objects)assert.equal(effectiveFaction(lake,object),null);
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(data,read('publication-v6.json'));
});
