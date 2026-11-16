import test from 'node:test';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';
import {normalizeData,effectiveFaction} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const specs=[["location-merchant-cloth-shop", "merchant-square", "market", 1884, 2881], ["location-merchant-herbal-shop", "merchant-square", "market", 1929, 2881], ["location-merchant-ironware-shop", "merchant-square", "market", 1938, 2939], ["location-military-forge", "military-district", "forge", 1934, 3237], ["location-military-barracks", "military-district", "barracks", 2019, 3163], ["location-greymane-record-office", "greymane-court", "building", 1631, 3172], ["location-greymane-post-office", "greymane-court", "building", 1729, 3176], ["location-cathedral-rose-park", "cathedral-quarter", "garden", 1789, 2949]];
test('capital shops, forge, barracks, municipal offices and park are eight distinct canonical map children',()=>{
 const data=read('atlas.json');
 for(const [id,parentId,type,x,y] of specs){
  const location=data.locations.find(l=>l.id===id),parent=data.locations.find(l=>l.id===parentId);assert.ok(location,id);
  assert.equal(location.type,type);assert.deepEqual([location.x,location.y],[x,y]);assert.equal(location.isLocation,false);assert.equal(location.faction,parent.faction);
  assert.ok(parent.linkedLocationIds.includes(id));assert.ok(location.description.length>80);assert.ok(location.shortDescription.length>15);
  assert.equal(location.provenance.authorScenario.canonicalEvidence,false);
  assert.equal(location.objects.length,1);const object=location.objects[0];assert.equal(effectiveFaction(location,object),parent.faction);assert.equal(object.rules.bonusValue,1);assert.equal(object.rules.activation,'ownership');assert.equal(object.rules.stacking,'additive');
 }
 const forge=data.locations.find(l=>l.id==='location-military-forge');assert.equal(forge.objects[0].modifiers[0].text,'+1 к броскам атаки ближним оружием всей фракции.');
 const barracks=data.locations.find(l=>l.id==='location-military-barracks');assert.equal(barracks.objects[0].modifiers[0].text,'+1 к защите (КД) всей фракции.');
 assert.ok(isDeepStrictEqual(data.territoryGrid,read('publication-v6.json').territoryGrid), 'Capital additions retain the current explicitly redrawn grid');assert.equal(data.territoryGrid.migration.method,'author-full-realm-layout');assert.deepEqual(data.territories,[]);assert.deepEqual(normalizeData(data),data);assert.deepEqual(data,read('publication-v6.json'));
});
