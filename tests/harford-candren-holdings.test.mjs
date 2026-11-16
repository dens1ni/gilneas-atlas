import test from 'node:test';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';
import {effectiveFaction, normalizeData, serializeSnapshot, deserializeSnapshot} from '../assets/js/model.mjs';
import {deriveNobleProfile} from '../assets/js/noble-profile.mjs';
const read = name => JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`, import.meta.url), 'utf8'));
const MOSSY = 'location-fb88bb30-c639-4f75-a142-92445555a772';
const GRAY = 'location-df0aa1e2-31ba-43fa-b6b0-84c7733f625a';
const HARFORD = ['northgate-woods', MOSSY];
const CANDREN = [GRAY, 'location-gray-ford-godfrey-estate', 'location-gray-ford-north-burned-house', 'location-gray-ford-east-burned-house'];

test('Harford and Candren receive exactly the requested canonical holdings and every nested own object', () => {
  const data = read('atlas.json');
  for (const [factionId, nobleId, owner, ids] of [
    ['harford', 'noble-harford', 'Лорд Харфорд', HARFORD],
    ['candren', 'noble-candren', 'Лорд Кандрен', CANDREN],
  ]) {
    const house = data.factions.find(record => record.id === factionId);
    assert.ok(house, factionId);
    assert.equal(house.ruler, owner);
    assert.equal(house.parent, 'gilneas');
    assert.equal(house.provenance.authorScenario.basis, 'explicit-user-authorship');
    assert.equal(house.provenance.authorScenario.canonicalEarlyCadastre, false);
    const noble = data.nobles.find(record => record.id === nobleId);
    assert.equal(noble.house, factionId);
    assert.equal(noble.lifeStatus, 'unknown', 'Authored stewardship does not establish a canonical early birth or life status');
    assert.equal(noble.provenance.authorScenario.ownership.basis, 'explicit-user-authorship');
    assert.deepEqual(data.locations.filter(record => record.faction === factionId).map(record => record.id).sort(), [...ids].sort());
    for (const id of ids) {
      const location = data.locations.find(record => record.id === id);
      assert.ok(location, id);
      assert.equal(location.owner, owner);
      assert.equal(location.provenance.authorScenario.ownership.basis, 'explicit-user-authorship');
      assert.equal(location.provenance.authorScenario.ownership.canonicalEarlyCadastre, false);
      assert.match(location.description, new RegExp(factionId === 'harford' ? 'Харфорд' : 'Кандрен', 'u'));
      assert.doesNotMatch(location.description + location.shortDescription, /Годфри|Марли/u);
      for (const object of location.objects) {
        assert.equal(effectiveFaction(location, object), factionId, object.id);
        assert.equal(object.owner, owner, object.id);
        assert.match(object.description, new RegExp(factionId === 'harford' ? 'Харфорд' : 'Кандрен', 'u'));
      }
    }
    const profile = deriveNobleProfile(data, nobleId);
    assert.equal(profile.house.id, factionId);
    assert.deepEqual(profile.holdings.filter(record => record.kind === 'location').map(record => record.id).sort(), [...ids].sort());
    const person = data.royalCouncil.members.find(record => record.kind === 'person' && record.refId === nobleId);
    assert.equal(person.party, 'neutral');
    assert.equal(person.stance, 'unknown');
    assert.equal(person.advisor, false);
    assert.equal(person.votingSeat, false);
  }
  assert.equal(data.factions.length, 16);
  assert.equal(data.nobles.length, 26);
  assert.equal(data.locations.length, 86);
  assert.equal(data.royalCouncil.members.length, 33);
  assert.equal(data.locations.flatMap(record => record.objects).length, 98);
  assert.ok(isDeepStrictEqual(data.territoryGrid, read('publication-v6.json').territoryGrid), 'Holdings retain the current explicitly redrawn grid');
  assert.equal(data.territoryGrid.migration.method, 'author-full-realm-layout');
  assert.deepEqual(data.territories, []);
  const event=JSON.parse(fs.readFileSync(new URL('./fixtures/crown-order-event.json',import.meta.url),'utf8'));
  assert.deepEqual(data.meta.wallConstruction, {...read('publication-author-v5.json').meta.wallConstruction, baseValue: 0, value: 10, events:[event]});
  assert.deepEqual(data, read('publication-v6.json'));
  assert.deepEqual(normalizeData(data), data);
  assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)), data);
});

test('Gray Ford retains literal house IDs and fire condition, while Marley keeps Emberstone compensation', () => {
  const data = read('atlas.json');
  const gray = data.locations.find(record => record.id === GRAY);
  assert.deepEqual(gray.linkedLocationIds, CANDREN.slice(1));
  for (const [index, id] of CANDREN.slice(1).entries()) {
    const house = data.locations.find(record => record.id === id);
    assert.equal(house.destroyed, index !== 0);
    assert.equal(house.objects[0].destroyed, index !== 0);
    assert.deepEqual([house.x, house.y], [[1527, 2714], [1616, 2612], [1676, 2704]][index]);
  }
  for (const id of ['emberstone-village', 'emberstone-mine']) {
    const location = data.locations.find(record => record.id === id);
    assert.equal(location.faction, 'marley');
    for (const object of location.objects) assert.equal(effectiveFaction(location, object), 'marley');
  }
  const lamp = data.locations.flatMap(record => record.objects).find(record => record.id === 'object-2cd23821-608a-534c-9d26-125f4dd6fba5');
  assert.equal(lamp.rules.compensatedByObjectId, 'object-emberstone-watch-post');
  assert.deepEqual(data.locations.find(record => record.id === 'northgate-woods').linkedLocationIds, [MOSSY]);
});
