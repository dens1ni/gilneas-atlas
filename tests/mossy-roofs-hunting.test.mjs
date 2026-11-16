import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalizeData} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));

test('Mossy Roofs is a hunting village with its original object refocused on trappers',()=>{
 const data=read('atlas.json');
 const place=data.locations.find(location=>location.id==='location-fb88bb30-c639-4f75-a142-92445555a772');
 assert.equal(place.name,'Деревня Мшистые Кровли');
 assert.match(place.description,/охот/i);
 assert.match(place.description,/ловчи/i);
 assert.match(place.description,/след|силк|капкан|дич/i);
 assert.match(place.shortDescription,/охот/i);
 assert.equal(place.objects.length,1);
 const object=place.objects[0];
 assert.equal(object.id,'object-fd65f111-b104-5c40-ad6a-690e67e8123a');
 assert.equal(object.name,'Двор ловчих');
 assert.equal(object.type,'building');
 assert.match(object.description,/ловч|след|силк|капкан/i);
 assert.doesNotMatch(object.description,/зерн|приёмк/i);
 assert.deepEqual(object.modifiers,[{
  id:'modifier-4321cb13-0526-5270-bfdc-9a22084562fe',kind:'bonus',
  text:'+1 к проверкам Мудрости (Выживание) всей фракции.'
 }]);
 assert.equal(object.rules.activation,'ownership');
 assert.equal(object.rules.scope,'faction');
 assert.equal(object.rules.appliesTo,'all-members');
 assert.equal(place.faction,'harford'); // Later explicit author assignment; hunting content stays unchanged.
 assert.equal(place.owner,'Лорд Харфорд');
 assert.deepEqual([place.x,place.y],[1933,2683]);
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(data,read('publication-v6.json'));
});
