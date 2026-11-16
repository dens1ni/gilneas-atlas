import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {effectiveFaction,normalizeData} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const entries=data=>data.locations.flatMap(location=>location.objects.map(object=>({location,object,faction:effectiveFaction(location,object)})));

test('all published object effects are immediate faction-wide ownership effects without usage criteria',()=>{
 const data=read('atlas.json'),all=entries(data);
 assert.equal(all.length,98); // Three ferry services, eleven new map children and Marley compensation.
 for(const {object} of all){
  assert.equal(object.rules.activation,'ownership',object.id);
  assert.equal(object.rules.scope,'faction',object.id);
  assert.equal(object.rules.appliesTo,'all-members',object.id);
  assert.equal(object.rules.stacking,'additive',object.id);
  for(const modifier of object.modifiers){
   assert.ok(modifier.text.length<=115,`${object.id}: overloaded modifier`);
   assert.match(modifier.text,/всей фракции\.$/);
   assert.doesNotMatch(modifier.text,/при |пока|после|если|только|следующ|минут|подготов|отдых|выбран|участник|расход|применени|не сумм|на месте|дозор|испуган/i);
  }
  for(const old of ['activationMinutes','bonusScope','expiresAt','negativeScope','groupPositiveLimit','groupBeneficiaryLimit','positiveRollLimitPerGroupCycle','groupReset','selectionLockedAt','requiresPermissionAndOrdinaryMaterials'])assert.ok(!Object.hasOwn(object.rules,old),`${object.id}.${old}`);
 }
 assert.equal(data.meta.contextualObjectRules.mode,'faction-ownership');
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(data,read('publication-v6.json'));
});

test('sparse faction penalties have one matching plus-two compensation at another owned place',()=>{
 const data=read('atlas.json'),all=entries(data);
 const penalties=all.filter(e=>e.object.modifiers.some(m=>m.kind==='penalty'));
 const doubled=all.filter(e=>e.object.rules.bonusValue===2);
 assert.ok(penalties.length>0,'Keep a few meaningful drawbacks, not mandatory ones everywhere');
 assert.ok(penalties.length<all.length/3,'Most objects must have no penalty');
 assert.equal(doubled.length,penalties.length);
 const paired=new Set();
 for(const entry of penalties){
  const negative=entry.object.modifiers.filter(m=>m.kind==='penalty');
  assert.equal(negative.length,1,entry.object.id);
  assert.match(negative[0].text,/^−1 /);
  assert.ok(entry.faction!=null,'Do not invent a shared faction for unassigned objects');
  const compensation=all.find(e=>e.object.id===entry.object.rules.compensatedByObjectId);
  assert.ok(compensation,entry.object.id);
  assert.notEqual(compensation.location.id,entry.location.id);
  assert.equal(compensation.faction,entry.faction);
  assert.equal(compensation.object.rules.bonusValue,2);
  assert.equal(compensation.object.rules.compensatesObjectId,entry.object.id);
  assert.ok(!paired.has(compensation.object.id));paired.add(compensation.object.id);
  const target=negative[0].text.slice(3);
  assert.equal(compensation.object.modifiers.find(m=>m.kind==='bonus').text,'+2 '+target);
 }
 for(const {object} of all){
  assert.equal(object.modifiers.filter(m=>m.kind==='bonus').length,1,object.id);
  if(!object.rules.compensatesObjectId){
   assert.equal(object.rules.bonusValue,1,object.id);
   assert.match(object.modifiers.find(m=>m.kind==='bonus').text,/^\+1 /);
  }else assert.match(object.modifiers.find(m=>m.kind==='bonus').text,/^\+2 /);
 }
});
