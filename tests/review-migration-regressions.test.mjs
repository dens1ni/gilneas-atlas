import test from 'node:test';
import assert from 'node:assert/strict';
import { reconcileDraftPublication } from '../assets/js/draft-publication.mjs';
import { normalizeData } from '../assets/js/model.mjs';

const prior = () => ({
  version: 1,
  meta: { width: 100, height: 100 },
  factions: [{ id: 'house', name: 'Дом', color: '#123456', parent: null, ruler: 'Лорд' }],
  locations: [{ id: 'estate', name: 'Усадьба', x: 10, y: 20, faction: 'house', owner: '', description: 'Прежний текст', objects: [] }],
  nobles: [{ id: 'lord', name: 'Лорд', house: 'house', description: 'Прежняя биография', sources: [2] }],
  sources: [{ id: 1, title: 'Первый', url: 'https://example.invalid/one' }, { id: 2, title: 'Второй', url: 'https://example.invalid/two' }],
  territories: [],
});
const release = () => {
  const data = prior();
  data.meta.publicationRevision = 'review-v2';
  data.meta.gilneasCrest = 'assets/ui/gilneas-shield.svg';
  data.meta.crestSource = 'https://example.invalid/published-crest';
  data.meta.wallConstruction = { value: 10, max: 100 };
  data.nobles[0].description = 'Новая биография';
  return data;
};

test('migration does not resurrect an author-deleted baseline source', () => {
  const previous = prior(), published = release(), draft = prior();
  draft.sources = draft.sources.filter(source => source.id !== 1);
  const before = structuredClone(draft);
  const result = normalizeData(reconcileDraftPublication(draft, published, previous));
  assert.deepEqual(result.sources, draft.sources);
  assert.deepEqual(draft, before);
});

test('migration preserves author-modified publication metadata', () => {
  for (const hadDefaults of [false, true]) {
    const previous = prior(), published = release(), draft = prior();
    if (hadDefaults) Object.assign(previous.meta, {
      gilneasCrest: 'assets/ui/prior.svg', crestSource: 'https://example.invalid/prior-crest',
      wallConstruction: { value: 0, max: 100 },
    });
    Object.assign(draft.meta, {
      gilneasCrest: 'https://example.invalid/author-crest.svg',
      crestSource: 'https://example.invalid/author-crest-evidence',
      wallConstruction: { value: 43, max: 91, note: '  Авторская стадия  ' },
    });
    const before = structuredClone(draft);
    const result = reconcileDraftPublication(draft, published, previous);
    for (const field of ['gilneasCrest', 'crestSource', 'wallConstruction']) {
      assert.deepEqual(result.meta[field], before.meta[field], field);
    }
    assert.deepEqual(draft, before);
  }
});

test('migration upgrades the known former banner publication default', () => {
  const previous = prior(), published = release(), draft = prior();
  draft.meta.gilneasCrest = 'assets/ui/gilneas-human-banner.png';
  const result = reconcileDraftPublication(draft, published, previous);
  assert.equal(result.meta.gilneasCrest, 'assets/ui/gilneas-shield.svg');
});

test('migration adds safe supporting source IDs to unchanged noble citations', () => {
  const previous = prior(), published = release(), draft = prior();
  published.sources.push({ id: 65, title: 'Новый источник', url: 'https://example.invalid/release-65' });
  published.nobles[0].sources.push(65);
  const result = normalizeData(reconcileDraftPublication(draft, published, previous));
  assert.deepEqual(result.nobles[0].sources, [2, 65]);
  assert.deepEqual(result.sources.at(-1), published.sources.at(-1));
});

test('incoming noble citations cannot reintroduce an author-deleted source reference', () => {
  const previous = prior(), published = release(), draft = prior();
  draft.sources = draft.sources.filter(source => source.id !== 1);
  published.sources.push({ id: 65, title: 'Новый источник', url: 'https://example.invalid/release-65' });
  published.nobles[0].sources = [2, 1, 65];
  const result = normalizeData(reconcileDraftPublication(draft, published, previous));
  assert.deepEqual(result.nobles[0].sources, [2, 65]);
  assert.equal(result.sources.some(source => source.id === 1), false);
});

test('duplicate source URLs retain distinct new release IDs without rewriting author citations', () => {
  const previous = prior(), published = release(), draft = prior();
  const url = 'https://example.invalid/shared';
  draft.sources.push({ id: 'author-source', title: 'Авторский источник', url });
  draft.locations[0].sources = ['author-source'];
  published.sources.push({ id: 65, title: 'Источник новой биографии', url });
  published.nobles[0].sources.push(65);
  const result = normalizeData(reconcileDraftPublication(draft, published, previous));
  assert.deepEqual(result.nobles[0].sources, [2, 65]);
  assert.deepEqual(result.locations[0].sources, ['author-source']);
  assert.deepEqual(result.sources.filter(source => source.url === url).map(source => source.id), ['author-source', 65]);
});

test('new release source ID conflicts fail before merging any draft fields', () => {
  const previous = prior(), published = release(), draft = prior();
  const authorUrl = 'https://example.invalid/author-65', releaseUrl = 'https://example.invalid/release-65';
  draft.sources.push({ id: 65, title: 'Мой источник', url: authorUrl });
  published.sources.push({ id: 65, title: 'Новый источник', url: releaseUrl });
  published.nobles[0].sources.push(65);
  const before = structuredClone({ draft, published, previous });
  assert.throws(() => reconcileDraftPublication(draft, published, previous), error => {
    assert.match(error.message, /source[- ]ID conflict.*65/i);
    assert.ok(error.message.includes(authorUrl));
    assert.ok(error.message.includes(releaseUrl));
    assert.match(error.message, /ID.*references|ID.*ссыл/i);
    return true;
  });
  assert.deepEqual({ draft, published, previous }, before);
});

test('incoming citations do not bind new lore to an author-retargeted baseline source', () => {
  const previous = prior(), published = release(), draft = prior();
  draft.sources[0].url = 'https://example.invalid/author-retargeted-one';
  draft.sources[0].title = '  Author evidence  ';
  published.nobles[0].sources = [2, 1];
  const result = normalizeData(reconcileDraftPublication(draft, published, previous));
  assert.deepEqual(result.sources, draft.sources);
  assert.deepEqual(result.nobles[0].sources, [2]);
});

test('known old-banner default follows the incoming publication crest path', () => {
  const previous = prior(), published = release(), draft = prior();
  draft.meta.gilneasCrest = 'assets/ui/gilneas-human-banner.png';
  published.meta.gilneasCrest = 'assets/ui/gilneas-royal-shield.svg';
  assert.equal(reconcileDraftPublication(draft, published, previous).meta.gilneasCrest, published.meta.gilneasCrest);
});

test('known old-banner default upgrades when the publication revision already matches', () => {
  const previous = prior(), published = release(), draft = prior();
  draft.meta.publicationRevision = published.meta.publicationRevision;
  draft.meta.gilneasCrest = 'assets/ui/gilneas-human-banner.png';
  published.meta.gilneasCrest = 'assets/ui/gilneas-royal-shield.svg';
  const result = reconcileDraftPublication(draft, published, previous);
  assert.equal(result.meta.gilneasCrest, published.meta.gilneasCrest);
  assert.deepEqual(result.nobles, draft.nobles);
  draft.meta.gilneasCrest = 'https://example.invalid/custom.svg';
  assert.deepEqual(reconcileDraftPublication(draft, published, previous), draft);
});

test('valid migration preserves author citation edits and exact numeric/string source identities', () => {
  const previous = prior(), published = release(), draft = prior();
  draft.sources.push({ id: '1', title: 'Строковый ID', url: 'https://example.invalid/string-one' });
  draft.nobles[0].sources = ['1'];
  draft.locations[0].x = 31;
  draft.locations[0].objects.push({ id: 'forge', name: '  Авторская кузница  ', type: 'building', owner: '', description: '', modifiers: [], extra: { literal: '<script>literal</script>' } });
  published.nobles[0].sources = [2, 1];
  const result = normalizeData(reconcileDraftPublication(draft, published, previous));
  assert.deepEqual(result.nobles[0].sources, ['1']);
  assert.deepEqual(result.locations[0].objects, draft.locations[0].objects);
  assert.equal(result.locations[0].x, 31);
  assert.deepEqual(result.sources.map(source => source.id), [1, 2, '1']);
  assert.deepEqual(reconcileDraftPublication(result, published, previous), result);
});

test('publication metadata adopts absent or exactly unchanged previous defaults', () => {
  for (const absent of [false, true]) {
    const previous = prior(), published = release(), draft = prior();
    Object.assign(previous.meta, { gilneasCrest: 'assets/ui/prior.svg', crestSource: 'https://example.invalid/old-crest', wallConstruction: { value: 0, max: 100 } });
    if (!absent) Object.assign(draft.meta, structuredClone(previous.meta));
    const result = reconcileDraftPublication(draft, published, previous);
    for (const field of ['gilneasCrest', 'crestSource', 'wallConstruction']) assert.deepEqual(result.meta[field], published.meta[field]);
  }
});
