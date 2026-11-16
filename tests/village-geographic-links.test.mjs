import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalizeData} from '../assets/js/model.mjs';
import {resolveLocationLinks} from '../assets/js/location-links.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const GRAY='location-df0aa1e2-31ba-43fa-b6b0-84c7733f625a';
const MOSSY='location-fb88bb30-c639-4f75-a142-92445555a772';
const place=(data,id)=>{const record=data.locations.find(location=>location.id===id);assert.ok(record,id);return record;};

test('Gray Ford is linked to Northern Headlands beside the existing Storm Lighthouse',()=>{
 const data=read('atlas.json'),parent=place(data,'northern-headlands'),village=place(data,GRAY);
 assert.equal(parent.name,'Северный каменистый мыс');
 assert.equal(village.name,'Деревня Серый Брод');
 assert.deepEqual(parent.linkedLocationIds,['galewatch-lighthouse',GRAY],'Append Gray Ford without removing the lighthouse');
 assert.equal(parent.isLocation,true);
 assert.equal(village.isLocation,true);
 assert.equal(village.type,'settlement');
 assert.deepEqual([village.x,village.y],[1611,2689]);
 assert.strictEqual(resolveLocationLinks(data,parent.id).children[1],village);
 assert.deepEqual(resolveLocationLinks(data,GRAY).parents.map(location=>location.id),['northern-headlands']);
 assert.equal(village.faction,'candren');assert.equal(village.owner,'Лорд Кандрен');
 assert.ok(!place(data,'the-headlands').linkedLocationIds.includes(GRAY),'Do not confuse the distinct Raft cape');
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(data,read('publication-v6.json'));
});

test('Mossy Roofs is the canonical village child of Northgate Woods with the separately requested Harford village assignment',()=>{
 const data=read('atlas.json'),parent=place(data,'northgate-woods'),village=place(data,MOSSY);
 assert.equal(parent.name,'Лес Северных врат');
 assert.equal(village.name,'Деревня Мшистые Кровли');
 assert.deepEqual(parent.linkedLocationIds,[MOSSY],'Attach Mossy Roofs to Northgate Woods');
 assert.equal(parent.isLocation,true);
 assert.equal(village.isLocation,true);
 assert.equal(village.type,'settlement');
 assert.deepEqual([village.x,village.y],[1933,2683]);
 assert.strictEqual(resolveLocationLinks(data,parent.id).children[0],village);
 assert.deepEqual(resolveLocationLinks(data,MOSSY).parents.map(location=>location.id),['northgate-woods']);
 assert.equal(village.faction,'harford');assert.equal(village.owner,'Лорд Харфорд');
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(data,read('publication-v6.json'));
});
