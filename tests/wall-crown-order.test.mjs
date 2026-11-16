import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalizeData, serializeSnapshot, deserializeSnapshot} from '../assets/js/model.mjs';
import {deriveWallProgress} from '../assets/js/wall-progress.mjs';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';
const read = name => JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}`, import.meta.url), 'utf8'));
const EVENT = 'wall-event-f885cf03-ff4a-46aa-b195-436b5f0d9622';
export const CROWN_ORDER_DESCRIPTION = 'Король Генн Седогрив приказал возвести северный оборонительный рубеж; путь будущей Стены ещё обсуждают. Знать гадает, чьи земли окажутся снаружи, но Краули уверен: Даларан не позволит подвести рубеж так близко, чтобы защитить Янтарную мельницу. О выходе из Альянса король не говорит, хотя при дворе понимают, что Стена охладит отношения с союзниками.';

test('the Crown Order rewrites the existing manual Wall event without changing its identity or progress', () => {
  const data = read('atlas.json'), author = read('publication-author-v5.json');
  const track = data.meta.wallConstruction, original = author.meta.wallConstruction.events.find(event => event.id === EVENT);
  const event = track.events.find(event => event.id === EVENT);
  assert.ok(event, 'Keep the original manual event rather than adding a duplicate');
  assert.equal(event.name, 'Приказ Короны');
  assert.equal(event.description, CROWN_ORDER_DESCRIPTION);
  assert.equal(event.delta, original.delta);
  assert.equal(track.events.length, author.meta.wallConstruction.events.length);
  assert.deepEqual(event.effects.map(effect => [effect.id, effect.kind]), original.effects.map(effect => [effect.id, effect.kind]));
  assert.equal(event.effects[0].text, 'Гилнеас укрепляет оборону и суверенитет.');
  assert.equal(event.effects[1].text, 'Недовольная знать объединяется в Интернационалистов, выступающих против Стены Седогрива.');
  assert.deepEqual([track.baseValue, track.value, track.max], [0, 10, 100]);
  assert.equal(deriveWallProgress(track).value, 10);
  assert.deepEqual(event.sources, [45, 32, 48]);
  for (const id of event.sources) assert.ok(data.sources.some(source => source.id === id));
  assert.equal(event.provenance.authorScenario.basis, 'explicit-user-authorship');
  assert.equal(event.provenance.authorScenario.dalaranConstraint.canonicalEvidence, false);
  assert.equal(event.provenance.authorScenario.allianceWithdrawal, 'not-announced-in-current-scenario');
  assert.equal(event.provenance.authorScenario.internationalists.canonicalNameConfirmed, false);
  assert.equal(original.name, 'Седогрив вкусно покушал', 'The immutable author input remains unchanged');
  assert.deepEqual(normalizeData(data), data);
  assert.deepEqual(deserializeSnapshot(serializeSnapshot(data)), data);
  assert.deepEqual(data, read('publication-v6.json'));
});

test('an untouched author Wall ledger adopts the Crown Order while a custom event remains the author choice', () => {
  const published = read('publication-v6.json'), previous = read('publication-v5.json'), seed = read('publication-author-v5.json');
  const draft = structuredClone(seed), before = structuredClone(draft);
  const result = normalizeData(reconcileDraftPublication(draft, published, previous, seed));
  assert.deepEqual(draft, before);
  assert.deepEqual(result.meta.wallConstruction, published.meta.wallConstruction);
  const custom = structuredClone(seed);
  custom.meta.wallConstruction.events.find(event => event.id === EVENT).description = '  Собственная запись автора  ';
  const retained = reconcileDraftPublication(custom, published, previous, seed);
  assert.deepEqual(retained.meta.wallConstruction, custom.meta.wallConstruction);
});
