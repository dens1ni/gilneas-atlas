import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createFactionShield} from '../assets/js/heraldry.mjs';
import {normalizeData,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';

const load=name=>JSON.parse(fs.readFileSync(new URL('../assets/data/'+name,import.meta.url),'utf8'));
const SHAPE='M1 1H59V46.4L30 71 1 46.4Z';
class Element {
 constructor(tag){this.tagName=tag;this.attributes=new Map();this.children=[];this.dataset={};}
 setAttribute(name,value){this.attributes.set(name,String(value));}
 getAttribute(name){return this.attributes.get(name)??null;}
 append(child){this.children.push(child);}
}
function withDOM(run){
 const before=Object.getOwnPropertyDescriptor(globalThis,'document');
 globalThis.document={baseURI:'https://atlas.example/gilneas-atlas/',createElementNS:(_,tag)=>new Element(tag)};
 try{return run();}finally{if(before)Object.defineProperty(globalThis,'document',before);else delete globalThis.document;}
}

test('Evermont has a red faction colour and the supplied gold-on-burgundy crest in the unchanged shield',()=>withDOM(()=>{
 const data=load('atlas.json'),before=structuredClone(data),house=data.factions.find(f=>f.id==='evermont');
 assert.equal(house.color,'#cc6666','Give House Evermont the requested red faction colour');
 assert.equal(house.heraldry.field,'#350a13','The supplied gold symbol keeps its dark burgundy field');
 assert.equal(house.heraldry.edge,'#cda24f');assert.equal(house.heraldry.device,'#cda24f');
 assert.equal(house.heraldry.symbol,'assets/ui/factions/evermont-device.svg');assert.equal(house.heraldry.origin,'author');
 assert.equal(house.heraldry.referenceSHA256,'0d94e42e45ab78870ca8cfe3659048f61ec639991ef187a81eeefe98e236bc37');
 assert.match(house.heraldry.note,/user-supplied/i);assert.match(house.heraldry.note,/not canonical/i);
 const svg=createFactionShield(data,'evermont'),field=svg.children[0],image=svg.children[1];
 assert.equal(svg.getAttribute('viewBox'),'0 0 60 72');assert.equal(field.getAttribute('d'),SHAPE);
 assert.equal(field.getAttribute('fill'),'#350a13');assert.equal(field.getAttribute('stroke'),'#cda24f');
 assert.equal(image.getAttribute('href'),'assets/ui/factions/evermont-device.svg');
 assert.deepEqual(['x','y','width','height'].map(key=>image.getAttribute(key)),['10','8','40','44']);
 assert.equal(data.factions.find(f=>f.id==='raft').color,'#94745a','Keep the previously requested Raft brown');
 assert.deepEqual(data,before);assert.deepEqual(data,load('publication-v6.json'));
}));

test('the compact Evermont asset has one needle with an open eye, a snake and a separate apple, not the former barrel',()=>{
 const svg=fs.readFileSync(new URL('../assets/ui/factions/evermont-device.svg',import.meta.url),'utf8');
 assert.match(svg,/viewBox="0 0 40 44"/);assert.match(svg,/data-symbol="needle-snake-apple"/);
 for(const part of ['needle','snake','apple'])assert.match(svg,new RegExp('data-part="'+part+'"'));
 assert.match(svg,/data-detail="needle-eye"/);assert.match(svg,/#cda24f/);
 assert.doesNotMatch(svg,/<(?:script|image|foreignObject|iframe|text)\b|\bon\w+\s*=|href\s*=|<!DOCTYPE|<!ENTITY|url\s*\(/i);
 const manifest=JSON.parse(fs.readFileSync(new URL('../assets/runtime-manifest.json',import.meta.url),'utf8'));
 assert.ok(manifest.includes('assets/ui/factions/evermont-device.svg'));
});

test('Evermont identity survives normalization, full exports and old-author migration while custom or deleted fields remain literal',()=>{
 const data=load('atlas.json'),old=load('publication-v5.json'),seed=load('publication-author-v5.json');
 assert.deepEqual(normalizeData(data),data);assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);
 assert.deepEqual(normalizeData(reconcileDraftPublication(seed,data,old,seed)),data);
 for(const field of [undefined,'#263844']){
  const custom=structuredClone(data),house=custom.factions.find(f=>f.id==='evermont');
  if(field===undefined)delete house.heraldry.field;else house.heraldry.field=field;
  house.color='#aa4444';house.heraldry.authorExtension={literal:'  Свои цвета  ',tokens:[0,'0',false,null]};
  const before=structuredClone(custom);
  assert.deepEqual(normalizeData(reconcileDraftPublication(custom,data,data,seed)),before);
  assert.deepEqual(deserializeSnapshot(serializeSnapshot(custom)),before);
 }
});
