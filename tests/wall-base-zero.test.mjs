import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalizeData,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
import {deriveWallProgress,removeWallEvent} from '../assets/js/wall-progress.mjs';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const approvedEvent=JSON.parse(fs.readFileSync(new URL('./fixtures/crown-order-event.json',import.meta.url),'utf8'));
const expectedTrack=author=>({...structuredClone(author),baseValue:0,value:10,events:author.events.map(event=>event.id===approvedEvent.id?structuredClone(approvedEvent):structuredClone(event))});

test('the Wall starts at zero while the complete manually authored event still contributes ten',()=>{
 const data=read('atlas.json'),author=read('publication-author-v5.json');
 const track=data.meta.wallConstruction,original=author.meta.wallConstruction;
 assert.equal(original.baseValue,10,'The supplied author input stays immutable');
 assert.equal(original.value,20);
 assert.equal(track.baseValue,0,'Remove only the inherited ten-point starting value');
 assert.equal(track.value,10,'The manually added +10 event remains applied');
 assert.equal(track.max,100);
 assert.deepEqual(track.events,expectedTrack(original).events,'Only the expressly rewritten Crown Order text and attribution change');
 assert.deepEqual(track,{...expectedTrack(original)});
 assert.deepEqual(track.events.map(event=>[event.id,event.delta,event.effects.map(effect=>[effect.id,effect.kind])]),original.events.map(event=>[event.id,event.delta,event.effects.map(effect=>[effect.id,effect.kind])]),'Every original event/effect ID, kind, order and delta stays literal');
 const progress=deriveWallProgress(track);
 assert.equal(progress.baseValue,0);
 assert.equal(progress.value,10);
 assert.deepEqual(progress.events.map(event=>[event.id,event.before,event.after,event.appliedDelta]),[
  ['wall-event-f885cf03-ff4a-46aa-b195-436b5f0d9622',0,10,10],
 ]);
 const withoutEvent=removeWallEvent(data,original.events[0].id);
 assert.equal(deriveWallProgress(withoutEvent.meta.wallConstruction).value,0);
 assert.deepEqual(data,read('publication-v6.json'));
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);
});

test('an unchanged author ZIP ledger adopts only the requested zero-start correction in real reconciliation',()=>{
 const release=read('publication-v6.json'),previous=read('publication-v5.json'),seed=read('publication-author-v5.json');
 const draft=structuredClone(seed),before=structuredClone(draft);
 const result=normalizeData(reconcileDraftPublication(draft,release,previous,seed));
 assert.equal(result.meta.wallConstruction.baseValue,0,'The actual saved author ledger must not keep the obsolete start');
 assert.deepEqual(result.meta.wallConstruction,expectedTrack(seed.meta.wallConstruction));
 assert.deepEqual(result.meta.wallConstruction.events,expectedTrack(seed.meta.wallConstruction).events);
 assert.deepEqual(result,release);
 assert.deepEqual(draft,before,'Migration does not mutate the stored author input');
});

test('the zero-start publication does not replace author-edited, emptied or deleted Wall ledgers',()=>{
 const release=read('publication-v6.json'),previous=read('publication-v5.json'),seed=read('publication-author-v5.json');
 const drafts=[];
 const missing=structuredClone(seed);delete missing.meta.wallConstruction;drafts.push(missing);
 const empty=structuredClone(seed);empty.meta.wallConstruction={...empty.meta.wallConstruction,events:[],value:10};drafts.push(empty);
 const custom=structuredClone(seed);custom.meta.wallConstruction.baseValue=3;custom.meta.wallConstruction.value=13;drafts.push(custom);
 const edited=structuredClone(seed);edited.meta.wallConstruction.events[0].description='  Мой исправленный текст  ';drafts.push(edited);
 const extra=structuredClone(seed);extra.meta.wallConstruction.events.push({id:'wall-zero-extra-event',name:'  Дополнительное событие  ',delta:-4,effects:[]});extra.meta.wallConstruction.value=16;drafts.push(extra);
 const extension=structuredClone(seed);extension.meta.wallConstruction.note='  Авторская заметка  ';drafts.push(extension);
 for(const draft of drafts){
  normalizeData(draft);
  const before=structuredClone(draft),result=normalizeData(reconcileDraftPublication(draft,release,previous,seed));
  assert.equal(Object.hasOwn(result.meta,'wallConstruction'),Object.hasOwn(draft.meta,'wallConstruction'));
  if(Object.hasOwn(draft.meta,'wallConstruction'))assert.deepEqual(result.meta.wallConstruction,draft.meta.wallConstruction);
  assert.deepEqual(draft,before,'Readonly migration keeps the full input literal');
 }
});
