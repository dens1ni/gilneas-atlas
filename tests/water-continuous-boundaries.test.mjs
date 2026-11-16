import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalizeData,sovereignOf} from '../assets/js/model.mjs';
const read=()=>JSON.parse(fs.readFileSync(new URL('../assets/data/atlas.json',import.meta.url),'utf8'));
test('political territory spans internal water without pixel clipping and retains sovereign hierarchy',()=>{
 const d=read(),g=d.territoryGrid,l=g.realmLayout;
 assert.equal(l.waterPolicy,'continuous-political-regions');
 assert.equal(Object.hasOwn(l,'landMask'),false);
 assert.equal(l.pixelClipRequired,false);
 assert.ok(l.waterContinuity.filledCells>0);
 for(const p of d.locations.filter(p=>p.faction!=null)){
  const i=Math.floor(p.y/g.step)*g.width+Math.floor(p.x/g.step);
  assert.equal(sovereignOf(d.factions,g.keys[g.cells[i]-1]),sovereignOf(d.factions,p.faction),p.id);
 }
 assert.deepEqual(normalizeData(d),d);
});
