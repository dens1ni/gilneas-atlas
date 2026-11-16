import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {effectiveFaction,normalizeData} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));

test('Pyrewood belongs to its unnamed lord-mayor within House Silverlaine',()=>{
 const data=read('atlas.json'),place=data.locations.find(location=>location.id==='pyrewood');
 assert.equal(place.name,'Деревня Погребальных Костров');
 assert.equal(place.owner,'Лорд-мэр деревни');
 assert.equal(place.faction,'silverlaine');
 assert.equal(data.factions.find(faction=>faction.id==='silverlaine').name,'Дом Сребролена');
 assert.equal(data.factions.find(faction=>faction.id==='silverlaine').parent,'crowley');
 for(const object of place.objects)assert.equal(effectiveFaction(place,object),'silverlaine',object.id);
 assert.doesNotMatch(place.description,/владения Дариуса Краули|принадлежит Дариусу Краули/);
 assert.doesNotMatch(place.shortDescription,/деревня дома Краули/i);
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(data,read('publication-v6.json'));
});
