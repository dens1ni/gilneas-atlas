import test from 'node:test';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';
import {effectiveFaction,normalizeData} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const GRAY='location-df0aa1e2-31ba-43fa-b6b0-84c7733f625a',MOSSY='location-fb88bb30-c639-4f75-a142-92445555a772';
test('Harford and Candren retain the explicitly assigned villages, with one intact estate and two destroyed houses',()=>{
 const data=read('atlas.json');
 const gray=data.locations.find(l=>l.id===GRAY),mossy=data.locations.find(l=>l.id===MOSSY);
 assert.equal(gray.faction,'candren');assert.equal(gray.owner,'Лорд Кандрен');assert.match(gray.description,/пожар/iu);assert.match(gray.description,/оправ|восстанов/iu);
 assert.equal(mossy.faction,'harford');assert.equal(mossy.owner,'Лорд Харфорд');assert.match(mossy.description,/охот|ловч/iu);
 for(const l of [gray,mossy]){assert.equal(l.provenance.authorScenario.ownership.canonicalEarlyCadastre,false);for(const o of l.objects){assert.equal(effectiveFaction(l,o),l.faction);assert.equal(o.owner,l.owner);}}
 const ids=['location-gray-ford-godfrey-estate','location-gray-ford-north-burned-house','location-gray-ford-east-burned-house'];
 assert.deepEqual(gray.linkedLocationIds,ids);
 for(const [i,id] of ids.entries()){
  const house=data.locations.find(l=>l.id===id);assert.ok(house,id);assert.equal(house.isLocation,false);assert.equal(house.faction,'candren');assert.equal(house.owner,'Лорд Кандрен');
  assert.deepEqual([house.x,house.y],[[1527,2714],[1616,2612],[1676,2704]][i]);
  assert.equal(house.destroyed,i!==0);assert.equal(house.type,i===0?'estate':'building');
  if(i!==0){assert.match(house.description,/сгор|обгор|выгор|пожар/iu);assert.equal(house.objects[0].destroyed,true);}
 }
 assert.equal(data.nobles.filter(n=>n.id==='noble-godfrey').length,1);assert.equal(data.nobles.filter(n=>n.id==='noble-marley').length,1);
 assert.ok(isDeepStrictEqual(data.territoryGrid,read('publication-v6.json').territoryGrid), 'Village holdings retain the current explicitly redrawn grid');assert.equal(data.territoryGrid.migration.method,'author-full-realm-layout');assert.deepEqual(data.territories,[]);assert.deepEqual(normalizeData(data),data);assert.deepEqual(data,read('publication-v6.json'));
});
