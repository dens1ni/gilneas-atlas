import test from 'node:test';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';
import {effectiveFaction,normalizeData,serializeSnapshot,deserializeSnapshot} from '../assets/js/model.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`,import.meta.url),'utf8'));
const MOORS='location-5187131a-bb77-4e98-948d-ddd4247781f2';

test('wandering lights may guide or mislead, with simple faction effects compensated at Taldoren',()=>{
 const data=read('atlas.json');
 const moors=data.locations.find(place=>place.id===MOORS);
 const taldoren=data.locations.find(place=>place.id==='taldoren');
 const lights=moors.objects.find(object=>object.id==='object-misty-moors-wandering-lights');
 assert.ok(lights,'The moors need their own wandering-lights object');
 assert.equal(lights.name,'Блуждающие огоньки');
 assert.equal(lights.type,'landmark');
 assert.match(lights.description,/указыв|показыв|вывод|ведут/i);
 assert.match(lights.description,/интересн|забыт|скрыт|находк/i);
 assert.match(lights.description,/заманив|увод|завод/i);
 assert.match(lights.description,/топ|трясин/i);
 assert.deepEqual(lights.modifiers,[
  {id:'modifier-misty-moors-lights-bonus',kind:'bonus',text:'+1 к проверкам Мудрости (Внимательность) всей фракции.'},
  {id:'modifier-misty-moors-lights-penalty',kind:'penalty',text:'−1 к проверкам Мудрости (Выживание) всей фракции.'},
 ]);
 const blessing=taldoren.objects.find(object=>object.id==='object-taldoren-nature-blessing');
 assert.ok(blessing,'The requested nature blessing compensates the wandering lights');
 assert.equal(blessing.name,'Благословение Природы');
 assert.match(blessing.description,/Ведьм[\p{L}\s]*Урожая/iu);
 assert.match(blessing.description,/незапамятн/i);
 assert.match(blessing.description,/ш[её]пот|шепч/i);
 assert.match(blessing.description,/духовн|душев|настро/i);
 assert.deepEqual(blessing.modifiers,[
  {id:'modifier-taldoren-nature-blessing-bonus',kind:'bonus',text:'+2 к проверкам Мудрости (Выживание) всей фракции.'},
 ]);
 assert.equal(lights.rules.compensatedByObjectId,blessing.id);
 assert.equal(blessing.rules.compensatesObjectId,lights.id);
 for(const [place,object] of [[moors,lights],[taldoren,blessing]]){
  assert.equal(effectiveFaction(place,object),'harvest-witches');
  assert.equal(object.rules.activation,'ownership');
  assert.equal(object.rules.scope,'faction');
  assert.equal(object.rules.appliesTo,'all-members');
  assert.equal(object.rules.stacking,'additive');
  for(const modifier of object.modifiers)assert.doesNotMatch(modifier.text,/при |если|после|только|подготов|отдых|минут|избран|дозор|не сумм/i);
  assert.equal(object.provenance.confidence,'custom');
  assert.equal(object.provenance.authorScenario.canonicalEvidence,false);
 }
 // Existing authored objects and their IDs are retained beside the additions.
 assert.ok(moors.objects.some(object=>object.id==='object-51faea2e-ab1e-549b-9bd4-b680e1329603'));
 assert.ok(taldoren.objects.some(object=>object.id==='object-435950d1-e1a9-566d-af0d-54a5997d197c'));
 assert.ok(isDeepStrictEqual(data.territoryGrid,read('publication-v6.json').territoryGrid), 'Natural wonders retain the current explicitly redrawn grid');
 assert.equal(data.territoryGrid.migration.method,'author-full-realm-layout');
 assert.deepEqual(data.territories,[]);
 assert.deepEqual(normalizeData(data),data);
 assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)),data);
 assert.deepEqual(data,read('publication-v6.json'));
});
