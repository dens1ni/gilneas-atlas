import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const data=()=>JSON.parse(fs.readFileSync(new URL('../assets/data/atlas.json',import.meta.url),'utf8'));
test('the requested fortress name and Pyrewood child link preserve the literal fortress identity',()=>{
 const d=data(),fort=d.locations.find(l=>l.id==='shadowfang'),village=d.locations.find(l=>l.id==='pyrewood');
 assert.equal(fort.name,'Крепость Пирвуд');assert.deepEqual([fort.x,fort.y],[1675,1725]);
 assert.equal(fort.faction,'silverlaine');assert.equal(fort.owner,'Барон Сребролен');
 assert.ok(village.linkedLocationIds.includes('shadowfang'));assert.equal(village.owner,'Лорд-мэр деревни');
});
