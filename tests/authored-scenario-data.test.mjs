import test from 'node:test';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';
import {normalizeData} from '../assets/js/model.mjs';
import {TYPE_DEFINITIONS, OBJECT_TYPE_IDS} from '../assets/js/object-types.mjs';

const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const atlas=()=>read('atlas.json');
const place=(data,id)=>{const found=data.locations.find(location=>location.id===id);assert.ok(found,id);return found;};
const ids={
  evermont:'location-76bf7c1a-fcd2-4dfc-9013-26b909b4732f',
  crowley:'location-60382f79-7237-4492-a95b-749b4f290d9b',
  distillery:'location-18f52fa5-7ee8-467f-81a1-d8d8ec11929f',
  walden:'location-9020653f-e319-4959-854d-9669422e14cc',
  southernBeacon:'location-e8c8f59c-83ac-49ff-819f-9708a9734ff1',
  darkBeacon:'location-3325cfda-47a7-4e3d-9cac-3797f4dbaa9d',
  hippodrome:'location-4f29a377-1080-4a49-b400-026ff4c7c589',
  temple:'location-ff52d2ed-f36b-4aba-8eac-7de87c8c76d7',
  herb:'location-75988492-6f32-4e29-9058-ef9d73e1746d',
  moor:'location-5187131a-bb77-4e98-948d-ddd4247781f2',
};

test('v6 uses the author snapshot as its full baseline and contains all requested places',()=>{
  const data=atlas();
  assert.equal(data.meta.publicationRevision,'authored-estates-v6');
  assert.equal(data.locations.length,86);
  assert.equal(data.factions.length,16);
  assert.equal(data.nobles.length,26);
  assert.equal(data.royalCouncil.members.length,33);
  assert.deepEqual(data,read('publication-v6.json'));
  assert.deepEqual(normalizeData(data),data);
});

test('author coordinates, literal IDs, existing objects, journal and evidence survive enrichment with explicit boundary redraw',()=>{
  const data=atlas(),author=read('publication-author-v5.json');
  assert.equal(author.locations.length,67);
  for(const original of author.locations){
    const current=place(data,original.id);
    assert.equal(current.id,original.id);
    if(original.id==='ambermill'){
      assert.ok(current.x<original.x);
      assert.equal(current.y,original.y);
    }else assert.deepEqual([current.x,current.y],[original.x,original.y],original.id);
    for(const object of original.objects){
      const retained=current.objects.find(item=>item.id===object.id);
      assert.ok(retained,object.id);
      const assignedAderic=object.id==='object-c9942c46-4400-47d9-92e7-8defa7ba9cf4';
      for(const [field,value] of Object.entries(object))if(!['description','modifiers'].includes(field)){
        const expected=assignedAderic&&field==='owner'?'Дом Рафт':assignedAderic&&field==='faction'?'raft':value;
        assert.deepEqual(retained[field],expected,`${object.id}.${field}`);
      }
      for(const modifier of object.modifiers){
        const kept=retained.modifiers.find(item=>item.id===modifier.id);assert.ok(kept,modifier.id);
        for(const [field,value] of Object.entries(modifier))if(field!=='text')assert.deepEqual(kept[field],value,`${modifier.id}.${field}`);
      }
      assert.equal(retained.amount,object.amount);
    }
  }
  assert.ok(isDeepStrictEqual(data.territoryGrid,read('publication-v6.json').territoryGrid), 'Published full-realm boundaries are retained exactly');
  assert.ok(!isDeepStrictEqual(data.territoryGrid,author.territoryGrid), 'Explicit redraw replaces the historical author grid');
  assert.equal(data.territoryGrid.migration.method,'author-full-realm-layout');
  assert.equal(data.territoryGrid.migration.legacyPolygonsRetained,false);
  assert.deepEqual(data.territories,[]);
  const event=JSON.parse(fs.readFileSync(new URL('./fixtures/crown-order-event.json',import.meta.url),'utf8'));
  assert.deepEqual(data.meta.wallConstruction,{...author.meta.wallConstruction,baseValue:0,value:10,events:[event]},'Explicit zero-start and Crown Order corrections preserve the manual event and effect identities');
  assert.deepEqual(data.royalCouncil.influence,author.royalCouncil.influence);
  for(const source of author.sources)assert.deepEqual(data.sources.find(item=>item.id===source.id),source);
  for(const id of ['crowley-orchard','crowley-stable-grounds','northgate-river'])assert.ok(!data.locations.some(item=>item.id===id),id);
});

test('requested canonical estate, settlement and annex links retain their actual markers',()=>{
  const data=atlas();
  const expected={
    [ids.evermont]:['location-6f6350b7-e0d4-49f0-b333-a807c0003842','location-d62d4e06-bb2d-48dc-8f59-fcbe0641f652','location-d3cda392-00e2-4afd-8cb4-09e8330221a6',ids.distillery],
    [ids.crowley]:['location-883f0f53-ba1a-44a5-bd8e-60b2d5d8cc22','location-ea37cf4e-63d7-48d1-bb38-c5a465f16f3a'],
    'tempests-reach':[ids.walden,ids.southernBeacon,ids.hippodrome],
    'ambermill':['ambermill-town-hall','ambermill-westbank-farm','ambermill-firrow-farm','ambermill-moorfield-farm'],
  };
  for(const [parent,children] of Object.entries(expected)){
    const record=place(data,parent);assert.equal(record.isLocation,true,parent);
    assert.deepEqual(record.linkedLocationIds,children,parent);
    for(const child of children)assert.ok(data.locations.some(item=>item.id===child),child);
  }
  const harbor=place(data,'duskhaven');
  for(const id of [ids.evermont,ids.crowley,ids.distillery,ids.darkBeacon,'location-426acd7a-5f00-48c0-a6aa-1de9ce3ac2fc','location-f2adc0b4-c081-404a-a546-16ca52d028aa','location-94b0bb4b-f058-4b9d-9ec3-eb3fdb02b21f'])assert.ok(harbor.linkedLocationIds.includes(id),id);
});

test('new stakeholder factions receive only their requested assets and Walden is not duplicated',()=>{
  const data=atlas(),factions=new Map(data.factions.map(f=>[f.id,f]));
  for(const [id,name] of [['evermont','Дом Эвермонт'],['harvest-witches','Ведьмы Урожая'],['tidesages','Жрецы Моря'],['walden','Дом Вальден']]){
    assert.equal(factions.get(id)?.name,name);
    assert.equal(factions.get(id)?.parent,'gilneas');
  }
  for(const id of [ids.evermont,ids.distillery,'location-6f6350b7-e0d4-49f0-b333-a807c0003842','location-d62d4e06-bb2d-48dc-8f59-fcbe0641f652','location-d3cda392-00e2-4afd-8cb4-09e8330221a6'])assert.equal(place(data,id).faction,'evermont',id);
  for(const id of [ids.moor,ids.herb,'blackwald','taldoren'])assert.equal(place(data,id).faction,'harvest-witches',id);
  for(const id of ['tempests-reach',ids.walden,ids.southernBeacon,ids.hippodrome])assert.equal(place(data,id).faction,'walden',id);
  assert.equal(place(data,ids.temple).faction,'tidesages');
  assert.equal(data.nobles.filter(n=>n.englishName==='Lord Walden').length,1);
  assert.equal(data.nobles.find(n=>n.id==='noble-walden').name,'Лорд Вальден');
  assert.equal(data.nobles.find(n=>n.id==='noble-walden').house,'walden');
});

test('every visible place description is immersive current knowledge and every pin has simple faction effects',()=>{
  const data=atlas();
  const ooc=/\b(?:Wowpedia|wiki|NPC|Cataclysm|out.of.role)\b|реконструкц|каноническ|в поздних|выбранн\w* эпох|не установл|сценарн|игрок|ворген|Отрекш|Катаклизм/i;
  for(const location of data.locations){
    assert.ok(location.description.trim().length>=80,location.id);
    assert.ok(location.shortDescription.trim().length>=15,location.id);
    assert.doesNotMatch(location.description,ooc,location.id);
    assert.doesNotMatch(location.shortDescription,ooc,location.id);
    assert.ok(OBJECT_TYPE_IDS.includes(location.type),location.id);
    assert.ok(location.objects.length>=1,location.id);
    const seeded=location.objects.filter(object=>object.rules?.edition==='dnd5e');
    assert.ok(seeded.length>=1,location.id);
    for(const object of seeded){
      assert.equal(object.rules.homebrew,true);
      assert.equal(object.rules.activation,'ownership');
      assert.equal(object.rules.scope,'faction');
      assert.equal(object.rules.appliesTo,'all-members');
      assert.equal(object.rules.stacking,'additive');
      assert.ok([1,2].includes(object.rules.bonusValue));
      assert.ok(object.modifiers.some(m=>m.kind==='bonus'&&/^\+[12] /.test(m.text)),object.id);
      for(const modifier of object.modifiers){
        assert.doesNotMatch(modifier.text,/спасброск\w*\s+Воли/i);
        assert.doesNotMatch(modifier.text,/[+−-][3-9]\b/);
        assert.match(modifier.text,/всей фракции\.$/);
        assert.doesNotMatch(modifier.text,/при |пока|после|если|отдых|минут|подготов|следующ|выбран|участник|применени|не сумм/i);
        if(modifier.kind==='penalty')assert.match(modifier.text,/^−1 /);
      }
    }
  }
});

test('all three actual lighthouse pins share the new beacon icon without rewriting existing type geometry',()=>{
  const data=atlas();
  for(const id of ['galewatch-lighthouse',ids.darkBeacon,ids.southernBeacon])assert.equal(place(data,id).type,'lighthouse');
  assert.equal(TYPE_DEFINITIONS.find(t=>t.id==='lighthouse').label,'Маяк');
  assert.equal(place(data,'hayward-fishery').type,'fishery');
  assert.equal(place(data,'bradshaw-mill').type,'mill');
  assert.equal(place(data,'location-17511ea5-f77c-4d83-a187-ee2da7acbf21').type,'hospital');
  assert.equal(place(data,'location-f2adc0b4-c081-404a-a546-16ca52d028aa').type,'market');
});

test('v6 migration inputs and helper are packaged and the real bootstrap fetches the author seed',()=>{
  const manifest=JSON.parse(fs.readFileSync(new URL('../assets/runtime-manifest.json',import.meta.url),'utf8'));
  for(const path of ['assets/data/publication-v6.json','assets/data/publication-author-v5.json','assets/js/scenario-publication.mjs'])assert.ok(manifest.includes(path),path);
  const app=fs.readFileSync(new URL('../assets/js/app.mjs',import.meta.url),'utf8');
  assert.match(app,/publication-author-v5\.json/);
  assert.match(app,/reconcileDraftPublication\(data,baseline,previous,authorSeed\)/);
});
