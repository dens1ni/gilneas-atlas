import test from 'node:test';
import assert from 'node:assert/strict';

const councilModule = () => import('../assets/js/royal-council.mjs');
const snapshot = () => ({
  version: 1,
  meta: { width: 300, height: 200, chronicle: [{ title: 'Original', text: '<script>literal</script>', sources: [45] }] },
  factions: [
    { id: 'gilneas', name: 'Королевство Гилнеас', color: '#111111', parent: null },
    ...['greymane', 'crowley', 'silverlaine', 'godfrey', 'ashbury', 'marley', 'walden'].map((id, index) => ({
      id, name: `Тестовый дом ${id}`, color: `#12345${index}`, parent: id === 'silverlaine' ? 'crowley' : 'gilneas',
      heraldry: { symbol: 'assets/ui/gilneas-symbol.png', field: '#123456' }, authorExtension: { keep: false },
    })),
  ],
  nobles: [
    { id: 'noble-genn', name: 'Генн Седогрив', title: 'Король Гилнеаса', house: 'greymane', sources: [45] },
    { id: 'noble-darius', name: 'Дариус Краули', title: 'Лорд', house: 'crowley', sources: ['archive-46'] },
  ],
  sources: [{ id: 45, title: 'Original numeric source', url: 'https://example.com/genn' },
    { id: 'archive-46', title: 'Original literal source', url: 'https://example.com/darius' }],
  locations: [{ id: 'original-place', name: 'Владение', x: 12, y: 13, faction: 'silverlaine', owner: 'Дариус Краули',
    objects: [{ id: 'original-object', name: 'Object', type: 'building', modifiers: [{ id: 'original-modifier', kind: 'bonus', text: '' }] }] }],
  territories: [{ id: 'original-territory', faction: 'greymane', points: [[1, 1], [1, 3], [3, 1]], note: '' }],
  territoryGrid: { version: 1, cellSize: 100, columns: 3, rows: 2, keys: ['gilneas', 'greymane', 'crowley'], cells: [0, 1, 2, 3, 0, 2],
    manual: { '0': 0, '5': 2 }, provenance: { sources: [45], note: 'Literal manual zero' } },
  authorMetadata: { falseLiteral: false, blank: '', nil: null },
});
const member = (patch = {}) => ({
  id: 'council-test-genn', kind: 'person', refId: 'noble-genn', party: 'royalists',
  stance: 'unknown', advisor: false, active: true, note: '', ...patch,
});
const council = (...members) => ({ version: 1, members });

test('party definitions are immutable identities with two canonical noble leaders, not assignments', async () => {
  const { COUNCIL_PARTIES } = await councilModule();
  assert.deepEqual(COUNCIL_PARTIES, [
    { id: 'royalists', name: 'Роялисты', leaderId: 'noble-genn' },
    { id: 'internationalists', name: 'Интернационалисты', leaderId: 'noble-darius' },
    { id: 'neutral', name: 'Нейтралы' },
  ]);
  assert.ok(Object.isFrozen(COUNCIL_PARTIES));
  for (const party of COUNCIL_PARTIES) assert.ok(Object.isFrozen(party));
  assert.throws(() => COUNCIL_PARTIES.push({ id: 'invented' }), TypeError);
  assert.throws(() => { COUNCIL_PARTIES[0].name = 'Renamed'; }, TypeError);
  assert.equal(typeof globalThis.document, 'undefined');
});

test('optional legacy council is absent, while a present council must contain a version-one members array', async () => {
  const { validateRoyalCouncil } = await councilModule();
  assert.equal(typeof validateRoyalCouncil, 'function');
  assert.equal(validateRoyalCouncil(undefined, snapshot()), true);
  assert.equal(validateRoyalCouncil(council(), snapshot()), true);
  for (const value of [null, false, [], '', { version: '1', members: [] }, { version: 2, members: [] }, { version: 1 }, { version: 1, members: null }]) {
    assert.throws(() => validateRoyalCouncil(value, snapshot()), /[Сс]овет|version|members/);
  }
  const valid = council(member());
  const before = structuredClone(valid);
  assert.equal(validateRoyalCouncil(valid, snapshot()), true);
  assert.deepEqual(valid, before);
});

test('every assignment requires typed political fields and a usable literal person identity', async () => {
  const { validateRoyalCouncil } = await councilModule();
  for (const patch of [
    { id: '' }, { id: 12 }, { id: 'x'.repeat(101) }, { kind: 'noble' }, { party: 'RoyAlists' },
    { party: ' royalists ' }, { stance: 'abstain' }, { advisor: 'false' }, { advisor: null },
    { active: 0 }, { active: undefined }, { note: null }, { note: false }, { note: undefined },
    { name: false }, { name: null }, { title: 0 }, { title: null }, { title: undefined },
    { basis: 'assumed' }, { basis: false }, { basis: undefined },
  ]) assert.throws(() => validateRoyalCouncil(council(member(patch)), snapshot()), /[Сс]овет|участник|поле|ID/);
  for (const field of ['id', 'kind', 'party', 'stance', 'advisor', 'active', 'note']) {
    const incomplete = member(); delete incomplete[field];
    assert.throws(() => validateRoyalCouncil(council(incomplete), snapshot()), /[Сс]овет|участник|поле|ID/);
  }
  for (const bad of [null, [], 'person', false]) assert.throws(() => validateRoyalCouncil(council(bad), snapshot()));
  for (const name of ['', '   ', '\n\t', 3, false, null, undefined]) {
    const independent = member({ name }); delete independent.refId;
    assert.throws(() => validateRoyalCouncil(council(independent), snapshot()), /имя|участник|поле/);
  }
  for (const basis of ['lore', 'scenario', 'unknown']) {
    const literal = member({ name: '  <script>literal person</script>  ', title: '', basis, active: false, advisor: false,
      note: '  untouched  ', sources: [], authorFlag: false });
    delete literal.refId;
    const before = structuredClone(literal);
    assert.equal(validateRoyalCouncil(council(literal), snapshot()), true);
    assert.deepEqual(literal, before);
  }
});

test('references are exact typed registry IDs, never fallback names or normalized lookup tokens', async () => {
  const { validateRoyalCouncil } = await councilModule();
  const data = snapshot();
  for (const refId of ['greymane', ' noble-genn ', 'NOBLE-GENN', 'missing', '', null, undefined, 45, false]) {
    assert.throws(() => validateRoyalCouncil(council(member({ refId, name: 'Fallback must not mask a bad ref' })), data), /refId|ссылка|персонаж/);
  }
  for (const refId of ['noble-genn', ' greymane ', 'missing', null, undefined, 3, false]) {
    assert.throws(() => validateRoyalCouncil(council(member({ kind: 'faction', refId })), data), /refId|ссылка|фракция/);
  }
  const missingFaction = member({ kind: 'faction', name: 'Not a registry faction' }); delete missingFaction.refId;
  assert.throws(() => validateRoyalCouncil(council(missingFaction), data), /refId|ссылка|фракция/);
  assert.equal(validateRoyalCouncil(council(member({ kind: 'faction', refId: 'silverlaine', name: '', title: '' })), data), true);
  data.factions.push({ id: ' new-house ', name: 'Literal added house', parent: 'gilneas', color: '#112233' });
  assert.equal(validateRoyalCouncil(council(member({ kind: 'faction', refId: ' new-house ' })), data), true);
  assert.throws(() => validateRoyalCouncil(council(member({ kind: 'faction', refId: 'new-house' })), data));
  data.nobles.push({ id: 'later-imported-person', name: 'Imported', house: null });
  assert.equal(validateRoyalCouncil(council(member({ refId: 'later-imported-person' })), data), true);
  assert.throws(() => validateRoyalCouncil(council(member(), member()), data), /Повтор|повтор/);
  assert.throws(() => validateRoyalCouncil(council(member(), member({ id: 'second-assignment' })), data), /Повтор|повтор/);
  for (const id of ['greymane', 'noble-darius', 'original-place', 'original-object', 'original-modifier', 'original-territory', 'archive-46']) {
    assert.throws(() => validateRoyalCouncil(council(member({ id })), data), /Повтор|повтор/);
  }
});

test('source IDs keep their exact types and parent normalization receives global claim and source callbacks', async () => {
  const { validateRoyalCouncil } = await councilModule();
  const data = snapshot();
  for (const sources of [null, false, {}, '45', [null], ['45'], [46], ['missing'], [undefined]]) {
    assert.throws(() => validateRoyalCouncil(council(member({ sources })), data), /источник|sources/);
  }
  const literal = member({ sources: [45, 'archive-46'], name: '', title: '', basis: 'unknown', advisor: false, active: false });
  const calls = [];
  const before = structuredClone(literal);
  assert.equal(validateRoyalCouncil(council(literal), data, {
    claim: (value, label) => calls.push(['claim', value.id, label]),
    validateSources: value => calls.push(['sources', value.sources]),
  }), true);
  assert.deepEqual(calls, [['claim', literal.id, 'участник Совета'], ['sources', [45, 'archive-46']]]);
  assert.deepEqual(literal, before);
  assert.throws(() => validateRoyalCouncil(council(member()), data, { claim: () => { throw new Error('parent-global-collision'); } }), /parent-global-collision/);
  assert.throws(() => validateRoyalCouncil(council(member()), data, { validateSources: () => { throw new Error('parent-source-policy'); } }), /parent-source-policy/);
});

test('assignment upsert creates legacy council and edits immutably without touching author maps or lore', async () => {
  const { upsertCouncilMember, validateRoyalCouncil } = await councilModule();
  assert.equal(typeof upsertCouncilMember, 'function');
  const original = snapshot();
  const before = structuredClone(original);
  const literal = member({ kind: 'faction', refId: 'silverlaine', sources: [45, 'archive-46'], title: '', basis: 'scenario',
    extension: { blank: '', flag: false, payload: '<script>literal</script>' } });
  const created = upsertCouncilMember(original, literal);
  assert.deepEqual(original, before);
  assert.notEqual(created, original);
  assert.deepEqual(created.royalCouncil, council(literal));
  const { royalCouncil, ...untouched } = created;
  assert.deepEqual(untouched, before);
  created.royalCouncil.archiveNote = '  author council metadata  ';
  const edited = upsertCouncilMember(created, { ...literal, party: 'neutral', advisor: true, active: false, note: '  exact edited note  ' });
  assert.equal(edited.royalCouncil.archiveNote, '  author council metadata  ');
  assert.equal(edited.royalCouncil.members.length, 1);
  assert.equal(edited.royalCouncil.members[0].party, 'neutral');
  assert.equal(edited.royalCouncil.members[0].advisor, true);
  assert.equal(edited.royalCouncil.members[0].active, false);
  assert.deepEqual(edited.royalCouncil.members[0].sources, [45, 'archive-46']);
  assert.deepEqual(edited.royalCouncil.members[0].extension, literal.extension);
  assert.deepEqual(edited.territoryGrid, before.territoryGrid);
  assert.deepEqual(edited.factions, before.factions);
  assert.deepEqual(edited.nobles, before.nobles);
  edited.authorMetadata.blank = 'mutated result'; edited.royalCouncil.members[0].extension.blank = 'mutated result';
  assert.equal(created.authorMetadata.blank, '');
  assert.equal(literal.extension.blank, '');
  assert.equal(validateRoyalCouncil(created.royalCouncil, created), true);
  for (const bad of [member({ refId: 'deleted' }), member({ advisor: 'false' }), member({ title: null }), member({ sources: ['45'] })]) {
    assert.throws(() => upsertCouncilMember(original, bad));
    assert.deepEqual(original, before);
  }
});

test('removing an assignment keeps the person registry, council metadata, other assignments and exact full JSON', async () => {
  const { upsertCouncilMember, removeCouncilMember } = await councilModule();
  assert.equal(typeof removeCouncilMember, 'function');
  const original = snapshot();
  const independent = member({ id: 'council-independent', name: '  Тестовый самостоятельный человек  ', title: '',
    party: 'neutral', stance: 'oppose', active: false, advisor: true, sources: ['archive-46'], note: '<script>literal</script>' });
  delete independent.refId;
  const withBoth = upsertCouncilMember(upsertCouncilMember(original, member()), independent);
  withBoth.royalCouncil.customArchive = { literal: false, empty: '' };
  const before = structuredClone(withBoth);
  const removed = removeCouncilMember(withBoth, independent.id);
  assert.deepEqual(withBoth, before);
  assert.deepEqual(removed.royalCouncil.members, [member()]);
  assert.deepEqual(removed.royalCouncil.customArchive, { literal: false, empty: '' });
  assert.deepEqual(removed.nobles, original.nobles);
  assert.deepEqual(removed.sources.map(source => source.id), [45, 'archive-46']);
  const { royalCouncil, ...unchanged } = removed;
  assert.deepEqual(unchanged, original);
  const final = removeCouncilMember(removed, member().id);
  assert.deepEqual(final.royalCouncil, { version: 1, members: [], customArchive: { literal: false, empty: '' } });
  assert.deepEqual(JSON.parse(JSON.stringify(withBoth)), before);
  for (const id of [null, undefined, 3, 'missing', ' council-test-genn ']) {
    assert.throws(() => removeCouncilMember(withBoth, id), /ID|найден/);
    assert.deepEqual(withBoth, before);
  }
  assert.throws(() => removeCouncilMember(original, 'missing'), /найден/);
});

test('member identity resolves from the latest exact registry, with true house heraldry and literal independent names', async () => {
  const { resolveCouncilMember } = await councilModule();
  assert.equal(typeof resolveCouncilMember, 'function');
  const data = snapshot();
  const faction = resolveCouncilMember(data, member({ kind: 'faction', refId: 'silverlaine', name: 'Stale must not override faction' }));
  assert.equal(faction.name, 'Тестовый дом silverlaine');
  assert.deepEqual(faction.faction, data.factions.find(value => value.id === 'silverlaine'));
  assert.deepEqual(faction.heraldry, faction.faction.heraldry);
  assert.equal(faction.noble, null);
  assert.equal(faction.house, null);
  const person = resolveCouncilMember(data, member({ name: 'Stale must not override noble' }));
  assert.equal(person.name, 'Генн Седогрив');
  assert.equal(person.title, 'Король Гилнеаса');
  assert.equal(person.house.id, 'greymane');
  assert.deepEqual(person.heraldry, person.house.heraldry);
  assert.equal(person.noble.id, 'noble-genn');
  assert.equal(person.faction, null);
  assert.equal(resolveCouncilMember(data, member({ title: '' })).title, '');
  data.nobles[0].name = 'Генн — новое имя автора'; data.factions[1].name = 'Дом — новый текст';
  assert.equal(resolveCouncilMember(data, member()).name, 'Генн — новое имя автора');
  assert.equal(resolveCouncilMember(data, member()).house.name, 'Дом — новый текст');
  const independent = member({ name: '  <img src=x onerror=evil()>  ', title: '  literal title  ' }); delete independent.refId;
  const resolved = resolveCouncilMember(data, independent);
  assert.equal(resolved.name, independent.name);
  assert.equal(resolved.title, independent.title);
  for (const field of ['house', 'faction', 'heraldry', 'noble']) assert.equal(resolved[field], null);
  for (const bad of [member({ refId: 'deleted' }), member({ kind: 'faction', refId: 'noble-genn' }), member({ refId: null })]) {
    assert.throws(() => resolveCouncilMember(data, bad), /refId|ссылка/);
  }
});

test('malformed JSON collections and extension payloads are rejected rather than silently coerced or dropped', async () => {
  const { validateRoyalCouncil, upsertCouncilMember } = await councilModule();
  const data = snapshot();
  const cyclic = { blank: '' }; cyclic.self = cyclic;
  for (const extension of [undefined, NaN, Infinity, () => {}, 1n, new Map(), new Date(), cyclic]) {
    const invalid = member({ extension });
    assert.throws(() => validateRoyalCouncil(council(invalid), data), /JSON|Совет/);
    assert.throws(() => upsertCouncilMember(data, invalid), /JSON|Совет|clone/);
  }
  const sparse = { version: 1, members: Array(1) };
  assert.throws(() => validateRoyalCouncil(sparse, data), /JSON|Совет/);
  const sparseSources = member({ sources: Array(1) });
  assert.throws(() => validateRoyalCouncil(council(sparseSources), data));
  const undefinedCouncil = { ...data, royalCouncil: undefined };
  assert.throws(() => upsertCouncilMember(undefinedCouncil, member()), /JSON/);
  const nonJSONSnapshot = { ...data, authorMetadata: { infinity: Infinity } };
  assert.throws(() => upsertCouncilMember(nonJSONSnapshot, member()), /JSON/);
  assert.equal(Object.hasOwn(data, 'royalCouncil'), false);
});
