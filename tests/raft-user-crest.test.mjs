import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createFactionShield} from '../assets/js/heraldry.mjs';

// Attribute-only DOM adapter; actual image loading is covered in native tests.
class Node {
 constructor(tag){this.tagName=tag;this.attributes=new Map();this.children=[];this.dataset={};}
 setAttribute(name,value){this.attributes.set(name,String(value));}
 getAttribute(name){return this.attributes.get(name)??null;}
 append(node){this.children.push(node);}
}
function withDOM(run){
 const before=Object.getOwnPropertyDescriptor(globalThis,'document');
 globalThis.document={baseURI:'https://atlas.example/gilneas-atlas/',createElementNS:(_,tag)=>new Node(tag)};
 try{return run();}finally{if(before)Object.defineProperty(globalThis,'document',before);else delete globalThis.document;}
}
const SHAPE='M1 1H59V46.4L30 71 1 46.4Z';

test('a house may use its own dark heraldic field without recoloring its map territories',()=>withDOM(()=>{
 const data={meta:{gilneasHeraldry:{field:'#131516',edge:'#65707b',symbol:'assets/ui/gilneas-royal-symbol.png'}},factions:[
  {id:'gilneas',color:'#9aa8b6',parent:null},
  {id:'raft',color:'#697f77',parent:'gilneas',heraldry:{symbol:'assets/ui/factions/raft-device.svg',field:'#1c1512',edge:'#94745a',device:'#bac1c5'}},
  {id:'plain',color:'#375979',parent:'raft'}]};
 const before=structuredClone(data),svg=createFactionShield(data,'raft'),field=svg.children[0];
 assert.equal(field.getAttribute('fill'),'#1c1512','Use the directly supplied shield field, not the map colour');
 assert.equal(field.getAttribute('stroke'),'#94745a');assert.equal(field.getAttribute('d'),SHAPE);
 assert.equal(svg.getAttribute('viewBox'),'0 0 60 72');
 assert.equal(svg.dataset.color,'#1c1512');
 assert.deepEqual(['x','y','width','height'].map(key=>svg.children[1].getAttribute(key)),['10','8','40','44']);
 assert.equal(createFactionShield(data,'gilneas').children[0].getAttribute('fill'),'#131516');
 const invalid=structuredClone(data);invalid.factions[1].heraldry.field='red';
 assert.equal(createFactionShield(invalid,'raft').children[0].getAttribute('fill'),'#87918d','Unsafe field tokens stay neutral rather than executing CSS or borrowing the ancestor');
 assert.deepEqual(invalid.factions[1].color,'#697f77');
 const plain=createFactionShield(data,'plain');assert.equal(plain.children[0].getAttribute('fill'),'#375979');assert.equal(plain.children.length,1);
 assert.deepEqual(data,before);assert.equal(data.factions[1].color,'#697f77');
}));

test('House Raft uses the supplied silver bare tree and bronze rim in the same shared shield',()=>{
 const data=JSON.parse(fs.readFileSync(new URL('../assets/data/atlas.json',import.meta.url),'utf8'));
 const house=data.factions.find(f=>f.id==='raft');
 assert.equal(house.color,'#94745a','Use the brown from the crest rim as the House Raft map colour');
 assert.equal(house.color,house.heraldry.edge,'House colour matches its existing bronze-brown heraldry');
 assert.equal(house.heraldry.field,'#1c1512','Give the supplied tree a dark warm field');
 assert.equal(house.heraldry.edge,'#94745a');assert.equal(house.heraldry.device,'#bac1c5');
 assert.equal(house.heraldry.symbol,'assets/ui/factions/raft-device.svg');assert.equal(house.heraldry.origin,'author');
 assert.match(house.heraldry.note,/user-supplied|supplied by the user/i);
 assert.equal(house.heraldry.referenceSHA256,'c716ca3852f6ff0fbf9b2a9ef15eff310cb6e7449d9432d72bb69f3f029d482d');
 const svg=fs.readFileSync(new URL('../assets/ui/factions/raft-device.svg',import.meta.url),'utf8');
 assert.match(svg,/viewBox="0 0 40 44"/);assert.match(svg,/data-symbol="bare-tree-with-roots"/);
 assert.match(svg,/data-part="trunk"/);assert.match(svg,/data-part="branches"/);assert.match(svg,/data-part="roots"/);
 assert.match(svg,/#bac1c5/);assert.doesNotMatch(svg,/олень|колосья|stag|grain/i);
 assert.doesNotMatch(svg,/<(?:script|image|foreignObject|iframe|text)\b|\bon\w+\s*=|href\s*=|<!DOCTYPE|<!ENTITY|url\s*\(/i);
 assert.deepEqual(data,JSON.parse(fs.readFileSync(new URL('../assets/data/publication-v6.json',import.meta.url),'utf8')));
});

test('custom and absent author fields remain their own choices through complete normalization and old-draft reconciliation',async()=>{
 const {normalizeData,serializeSnapshot,deserializeSnapshot}=await import('../assets/js/model.mjs');
 const {reconcileDraftPublication}=await import('../assets/js/draft-publication.mjs');
 const load=name=>JSON.parse(fs.readFileSync(new URL('../assets/data/'+name,import.meta.url),'utf8'));
 const release=load('atlas.json'),old=load('publication-v5.json'),seed=load('publication-author-v5.json');
 const raw=serializeSnapshot(release);assert.deepEqual(deserializeSnapshot(raw),release);
 assert.deepEqual(normalizeData(reconcileDraftPublication(seed,release,old,seed)),release);
 for(const field of [undefined,'#263844']){
  const draft=structuredClone(release),house=draft.factions.find(f=>f.id==='raft');
  if(field===undefined)delete house.heraldry.field;else house.heraldry.field=field;
  house.heraldry.authorExtension={literal:'  Авторские данные  ',value:false};
  const before=structuredClone(draft);
  assert.deepEqual(normalizeData(reconcileDraftPublication(draft,release,release,seed)),before);
  assert.deepEqual(deserializeSnapshot(serializeSnapshot(draft)),before);
 }
 const invalid=structuredClone(release);invalid.factions.find(f=>f.id==='raft').heraldry.field='dark';
 assert.throws(()=>normalizeData(invalid),/heraldry\.field/);assert.deepEqual(release,load('atlas.json'));
});
