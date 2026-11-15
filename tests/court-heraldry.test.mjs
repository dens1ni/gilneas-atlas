import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';
import { createFactionShield } from '../assets/js/heraldry.mjs';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

// Attribute-only DOM adapter for Node. Real SVG image loading and script-safety
// are exercised separately in the scratch browser fixture, with the real module.
class SvgElement {
  constructor(namespace, tagName) {
    this.namespaceURI = namespace;
    this.tagName = tagName;
    this.attributes = new Map();
    this.children = [];
    this.dataset = {};
  }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  append(child) { this.children.push(child); }
}

beforeEach(() => {
  globalThis.document = {
    baseURI: 'https://atlas.example/gilneas-atlas/index.html',
    createElementNS: (namespace, tagName) => new SvgElement(namespace, tagName),
  };
});

const rootHeraldry = {
  symbol: 'assets/ui/gilneas-royal-symbol.png',
  field: '#131516', edge: '#65707b', device: '#9aa8b6',
};
const snapshot = () => ({
  meta: { gilneasHeraldry: { ...rootHeraldry } },
  factions: [
    { id: 'gilneas', parent: null, color: '#9aa8b6' },
    { id: 'greymane', parent: 'gilneas', color: '#c49b60' },
  ],
});
const device = svg => svg.children.find(child => child.tagName === 'image');
const field = svg => svg.children.find(child => child.tagName === 'path');

test('an author-designed faction uses its direct device on its exact own color', () => {
  const data = snapshot();
  data.factions.push({
    id: 'author-court', parent: 'greymane', color: '#375979',
    heraldry: {
      symbol: 'assets/ui/factions/custom-device.svg',
      edge: '#65707b', device: '#9aa8b6', origin: 'author',
    },
  });
  const original = structuredClone(data);
  const shield = createFactionShield(data, 'author-court');
  assert.equal(device(shield)?.getAttribute('href'), 'assets/ui/factions/custom-device.svg');
  assert.equal(field(shield).getAttribute('fill'), '#375979');
  assert.equal(field(shield).getAttribute('stroke'), '#65707b');
  assert.equal(device(shield).dataset.deviceColor, '#9aa8b6');
  assert.deepEqual(data, original, 'rendering must not mutate faction records');
});

test('a newly created faction with no heraldry stays plain rather than borrowing any ancestor', () => {
  const data = snapshot();
  data.factions.push({ id: 'new-court', parent: 'greymane', color: '#355f71' });
  const shield = createFactionShield(data, 'new-court');
  assert.equal(device(shield), undefined);
  assert.equal(field(shield).getAttribute('fill'), '#355f71');
  assert.equal(field(shield).getAttribute('stroke'), '#87918d', 'a new plain faction must not borrow a custom royal rim');
});

test('an independent foreign faction uses its own emblem and the shared silver edge', () => {
  const data = snapshot();
  data.factions.push({
    id: 'lordaeron', parent: null, color: '#7592b2',
    heraldry: { symbol: 'assets/ui/factions/lordaeron-device.svg', edge: '#65707b', device: '#9aa8b6' },
  });
  const shield = createFactionShield(data, 'lordaeron');
  assert.equal(device(shield)?.getAttribute('href'), 'assets/ui/factions/lordaeron-device.svg');
  assert.equal(field(shield).getAttribute('fill'), '#7592b2');
  assert.equal(field(shield).getAttribute('stroke'), '#65707b');
});

test('an explicit invalid symbol never falls back to the royal or parent crest', () => {
  const data = snapshot();
  data.factions[1].heraldry = { symbol: 'javascript:globalThis.__heraldryInjected = true', edge: '#65707b' };
  const shield = createFactionShield(data, 'greymane');
  assert.equal(device(shield), undefined);
  assert.equal(field(shield).getAttribute('fill'), '#c49b60');
});

test('a cyclic parent chain terminates without borrowing a device', () => {
  const data = snapshot();
  data.factions.push({ id: 'cycle-a', parent: 'cycle-b', color: '#436479' },
    { id: 'cycle-b', parent: 'cycle-a', color: '#563f76' });
  assert.equal(device(createFactionShield(data, 'cycle-a')), undefined);
});

test('a root direct emblem cannot override valid preserved royal metadata', () => {
  const data = snapshot();
  data.factions[0].heraldry = { symbol: 'assets/ui/factions/not-the-royal-device.svg', field: '#ff0000' };
  const shield = createFactionShield(data, 'gilneas');
  assert.equal(device(shield)?.getAttribute('href'), rootHeraldry.symbol);
  assert.equal(field(shield).getAttribute('fill'), '#131516');
});

test('unsafe image URLs stay plain and cannot introduce script nodes or evaluation', () => {
  const unsafe = [
    'javascript:alert(1)', 'data:image/svg+xml,<svg onload="alert(1)"/>',
    'blob:https://atlas.example/attack.svg', 'file:///tmp/attack.png',
    '//evil.example/device.svg', 'https://user:secret@evil.example/device.svg',
    'https://evil.example/attack.html', 'https://evil.example/attack.svg\\n',
    'assets\\\\ui\\\\device.svg', 'https://evil.example/device%0a.svg',
    'assets/ui/device.svg#<svg/onload=alert(1)>',
    'https://evil.example/device.svg?x="/><script>alert(1)</script>',
  ];
  for (const symbol of unsafe) {
    const data = snapshot();
    data.factions[1].heraldry = { symbol };
    const shield = createFactionShield(data, 'greymane');
    assert.equal(device(shield), undefined, `reject ${symbol}`);
    assert.deepEqual(shield.children.map(child => child.tagName), ['path']);
  }
});

test('a migrated snapshot does not replace an absent current-house device with royal legacy art', () => {
  const data = snapshot();
  data.factions[0].heraldry = { ...rootHeraldry };
  data.factions[1].heraldry = { symbol: 'assets/ui/factions/greymane-device.svg' };
  data.factions.push({ id: 'crowley', parent: 'gilneas', color: '#639096' });
  const shield = createFactionShield(data, 'crowley');
  assert.equal(device(shield), undefined);
  assert.equal(field(shield).getAttribute('fill'), '#639096');
});

test('the root retains custom royal metadata even when only another faction is migrated', () => {
  const data = snapshot();
  data.meta.gilneasHeraldry = { symbol: 'assets/ui/custom-royal.svg', field: '#102030', edge: '#566778', device: '#c0c8d0' };
  data.factions[1].heraldry = { symbol: 'assets/ui/factions/greymane-device.svg' };
  const shield = createFactionShield(data, 'gilneas');
  assert.equal(device(shield)?.getAttribute('href'), 'assets/ui/custom-royal.svg');
  assert.equal(field(shield).getAttribute('fill'), '#102030');
  assert.equal(field(shield).getAttribute('stroke'), '#566778');
  assert.equal(device(shield).dataset.deviceColor, '#c0c8d0');
});

test('malformed optional snapshots and missing parent records safely produce a plain shield', () => {
  for (const data of [null, {}, { factions: null }, { factions: [null, { id: 'stray', parent: 'missing', color: '#424f6a' }] }]) {
    assert.doesNotThrow(() => {
      const shield = createFactionShield(data, 'stray');
      assert.equal(device(shield), undefined);
      assert.equal(field(shield).getAttribute('d'), 'M1 1H59V46.4L30 71 1 46.4Z');
    });
  }
});

test('an explicitly unsafe custom royal symbol stays plain instead of taking the default direct root asset', () => {
  const data = snapshot();
  data.meta.gilneasHeraldry = { ...rootHeraldry, symbol: 'javascript:alert(1)', field: '#112233' };
  data.factions[0].heraldry = { ...rootHeraldry };
  const shield = createFactionShield(data, 'gilneas');
  assert.equal(device(shield), undefined);
  assert.equal(field(shield).getAttribute('fill'), '#112233');
});

test('safe custom HTTP and relative image references remain literal without parent fallback', () => {
  for (const symbol of ['assets/ui/factions/custom.svg', './assets/custom.png', '/assets/custom.webp', 'https://cdn.example/custom.svg?rev=2#device', 'http://cdn.example/custom.png']) {
    const data = snapshot();
    data.factions[1].heraldry = { symbol };
    assert.equal(device(createFactionShield(data, 'greymane'))?.getAttribute('href'), symbol);
  }
});

const expectedColors = {
  gilneas: '#9aa8b6', greymane: '#c49b60', crowley: '#639096', silverlaine: '#93a798',
  godfrey: '#8e789b', ashbury: '#b47869', marley: '#9b9d68', walden: '#91836e',
  dalaran: '#aa85c4', lordaeron: '#7592b2',
};

test('the asset manifest covers exactly ten unchanged faction colors and real distinct safe devices', async () => {
  let manifest;
  try { manifest = JSON.parse(await readFile(new URL('../docs/faction-heraldry.json', import.meta.url), 'utf8')); }
  catch (error) { assert.fail(`Complete faction heraldry manifest is required: ${error.message}`); }
  assert.equal(manifest.factions.length, 10);
  assert.deepEqual(manifest.factions.map(record => record.id).sort(), Object.keys(expectedColors).sort());
  assert.equal(new Set(manifest.factions.map(record => record.heraldry.symbol)).size, 10);
  const atlas = JSON.parse(await readFile(new URL('../assets/data/atlas.json', import.meta.url), 'utf8'));
  for (const record of manifest.factions) {
    const faction = atlas.factions.find(faction => faction.id === record.id);
    assert.equal(faction.color, expectedColors[record.id]);
    assert.equal(record.fieldColor, expectedColors[record.id]);
    assert.equal(record.heraldry.edge, '#65707b');
    assert.equal(record.heraldry.device, '#9aa8b6');
    assert.equal(record.heraldry.origin, record.origin);
    assert.equal(typeof record.heraldry.symbol, 'string');
    assert.equal(record.origin, ['dalaran', 'lordaeron'].includes(record.id) ? 'canonical-stylized' : 'author');
    const asset = await readFile(new URL(`../${record.heraldry.symbol}`, import.meta.url));
    assert.ok(asset.length > 100, record.id);
    assert.ok(manifest.assets.includes(record.heraldry.symbol), record.id);
    if (record.id === 'gilneas') {
      assert.equal(record.heraldry.symbol, 'assets/ui/gilneas-royal-symbol.png');
      assert.equal(record.heraldry.field, '#131516');
      assert.equal(createHash('sha256').update(asset).digest('hex'), '0aaeb453e3475503e9260f33b5dce1158bc087138a01cf07e7018f2b2d9798c3');
    } else {
      assert.ok(!Object.hasOwn(record.heraldry, 'field'), 'only the root owns a field override');
      assert.match(record.heraldry.symbol, new RegExp(`^assets/ui/factions/${record.id}-device\\.svg$`));
      const svg = asset.toString('utf8');
      assert.match(svg, /viewBox="0 0 40 44"/);
      assert.match(svg, /#9aa8b6/);
      assert.doesNotMatch(svg, /<(?:script|image|foreignObject|iframe)\b|\bon\w+\s*=|href\s*=|<!DOCTYPE|<!ENTITY|url\s*\(/i);
      assert.ok(record.sourceUrls.length >= 1, 'factual basis must have retrieved attribution');
    }
  }
  assert.equal(new Set(manifest.assets).size, manifest.assets.length);
  assert.equal(manifest.assets.length, 10);
});

test('Lordaeron keeps a strengthened source trace for legibility without importing the source frame', async () => {
  const svg = await readFile(new URL('../assets/ui/factions/lordaeron-device.svg', import.meta.url), 'utf8');
  assert.match(svg, /paint-order="stroke fill"/);
  assert.match(svg, /data-source="Human_Crest\.jpg"/);
  assert.match(svg, /data-treatment="small-size-strengthened"/);
  assert.doesNotMatch(svg, /<(?:text|image|script)\b|href\s*=/i);
});

test('old unmigrated Gilnean snapshots retain only the documented royal compatibility fallback', () => {
  const data = snapshot();
  data.factions.push({ id: 'silverlaine', parent: 'greymane', color: '#93a798' },
    { id: 'foreign-plain', parent: null, color: '#375979' });
  assert.equal(device(createFactionShield(data, 'silverlaine'))?.getAttribute('href'), rootHeraldry.symbol);
  assert.equal(device(createFactionShield(data, 'foreign-plain')), undefined);
  assert.equal(device(createFactionShield(data, 'unknown-id')), undefined);
});
