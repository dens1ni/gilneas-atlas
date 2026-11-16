import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  TYPE_DEFINITIONS, OBJECT_TYPE_IDS, typeName, createTypeIcon, populateTypeSelect,
} from '../assets/js/object-types.mjs';

// Captured from the actual catalog before the lighthouse addition.
const LEGACY_TYPE_COUNT = 39;
const LEGACY_ID_PATH_SHA256 = 'f925187ac6283cc6d9c7169ba3e366e0aa6cd1323784c379b4b8d0be8c71526d';
const LEGACY_DEFINITION_SHA256 = '580adc8c95abc7a0991646d124d4ad324f562e318ba42eb24134820c271a8a0a';
const SVG_NAMESPACE = 'http://www.w3.org/2000/svg';

// Test-only DOM primitives; rendering and option population use the real module.
class TinyElement {
  constructor(localName, namespaceURI = null) {
    this.localName = localName;
    this.namespaceURI = namespaceURI;
    this.children = [];
    this.attributes = new Map();
    this.value = '';
    this.textContent = '';
  }

  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = [...children]; }
}

function withTinyDocument(run) {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'document');
  Object.defineProperty(globalThis, 'document', {
    configurable: true,
    value: {
      createElement: name => new TinyElement(name),
      createElementNS: (namespace, name) => new TinyElement(name, namespace),
    },
  });
  try {
    return run();
  } finally {
    if (original) Object.defineProperty(globalThis, 'document', original);
    else delete globalThis.document;
  }
}

function sha256(value) {
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

test('shared type catalog imports in Node without browser globals', () => {
  assert.equal(typeof globalThis.document, 'undefined');
  assert.equal(typeof globalThis.window, 'undefined');
  assert.equal(typeof createTypeIcon, 'function');
  assert.equal(typeof populateTypeSelect, 'function');
  assert.ok(Object.isFrozen(TYPE_DEFINITIONS));
  assert.ok(Object.isFrozen(OBJECT_TYPE_IDS));
});

test('lighthouse is selectable for markers and objects with its own 24x24 beacon', () => {
  assert.ok(OBJECT_TYPE_IDS.includes('lighthouse'), 'missing literal type ID: lighthouse');
  assert.equal(TYPE_DEFINITIONS.length, LEGACY_TYPE_COUNT + 2, 'the requested ferry type is the only subsequent catalog addition');
  assert.deepEqual(OBJECT_TYPE_IDS, TYPE_DEFINITIONS.map(definition => definition.id));
  assert.equal(new Set(OBJECT_TYPE_IDS).size, OBJECT_TYPE_IDS.length);
  const definition = TYPE_DEFINITIONS.find(item => item.id === 'lighthouse');
  assert.ok(Object.isFrozen(definition));
  assert.deepEqual(Object.keys(definition).sort(), ['id', 'label', 'path']);
  assert.equal(definition.label, 'Маяк');
  assert.equal(typeName('lighthouse'), 'Маяк');
  assert.ok(TYPE_DEFINITIONS.every(item => item.id === 'lighthouse' || item.path !== definition.path),
    'lighthouse must not reuse an existing icon');
  assert.match(definition.path, /^[MLHVZ\d.\s-]+$/, 'use framework-free line geometry');
  const coordinates = [...definition.path.matchAll(/-?\d+(?:\.\d+)?/g)].map(match => Number(match[0]));
  assert.ok(coordinates.length > 0);
  assert.ok(coordinates.every(coordinate => coordinate >= 0 && coordinate <= 24), 'stay in the 24x24 viewBox');

  // Guard a peaked roof, enclosed lantern, tall tapered shaft and bilateral light beams.
  for (const [feature, path] of [
    ['roof', 'M8 5 12 2 16 5Z'],
    ['lantern', 'M9 5H15V9H9Z'],
    ['lantern mullion', 'M12 5V9'],
    ['gallery', 'M8 10H16'],
    ['tapered tower', 'M10 10 8 22H16L14 10Z'],
    ['left upper beam', 'M2 5 6 6'],
    ['left lower beam', 'M2 9 6 8'],
    ['right upper beam', 'M18 6 22 5'],
    ['right lower beam', 'M18 8 22 9'],
  ]) {
    assert.ok(definition.path.includes(path), `missing lighthouse feature: ${feature}`);
  }

  const icons = withTinyDocument(() => ['location', 'object'].map(scope => {
    const select = document.createElement('select');
    select.append(document.createElement('option'));
    populateTypeSelect(select, { scope });
    assert.equal(select.value, scope === 'location' ? 'settlement' : 'building');
    assert.deepEqual(select.children.map(option => option.value), OBJECT_TYPE_IDS);
    const options = select.children.filter(option => option.value === 'lighthouse');
    assert.equal(options.length, 1, `${scope} creation must offer lighthouse exactly once`);
    assert.equal(options[0].textContent, 'Маяк');

    populateTypeSelect(select, { scope, currentType: 'lighthouse' });
    assert.equal(select.value, 'lighthouse');
    assert.equal(select.children.length, TYPE_DEFINITIONS.length, 'known type must not use the unknown-type fallback');
    const container = document.createElement(scope === 'location' ? 'button' : 'span');
    container.setAttribute('class', scope === 'location' ? 'marker' : 'object-icon');
    const icon = createTypeIcon(select.value, 'test-lighthouse-icon');
    container.append(icon);
    assert.equal(container.children[0], icon);
    assert.equal(icon.localName, 'svg');
    assert.equal(icon.namespaceURI, SVG_NAMESPACE);
    for (const [name, value] of Object.entries({
      viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.6',
      'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true',
      focusable: 'false', 'data-type': 'lighthouse', class: 'test-lighthouse-icon',
    })) assert.equal(icon.getAttribute(name), value, `${scope}: ${name}`);
    assert.equal(icon.children.length, 1);
    assert.equal(icon.children[0].localName, 'path');
    assert.equal(icon.children[0].namespaceURI, SVG_NAMESPACE);
    assert.equal(icon.children[0].getAttribute('d'), definition.path);
    return icon;
  }));
  assert.notEqual(icons[0], icons[1], 'each consumer receives its own SVG node');
  assert.notEqual(icons[0].children[0], icons[1].children[0]);
  assert.equal(typeof globalThis.document, 'undefined', 'restore the Node-only environment');
});

test('lighthouse addition preserves all original type IDs and paths byte-for-byte', () => {
  const legacyDefinitions = TYPE_DEFINITIONS.filter(definition => !['lighthouse','ferry'].includes(definition.id));
  assert.equal(legacyDefinitions.length, LEGACY_TYPE_COUNT);
  assert.equal(sha256(legacyDefinitions.map(({ id, path }) => [id, path])), LEGACY_ID_PATH_SHA256);
  assert.equal(sha256(legacyDefinitions), LEGACY_DEFINITION_SHA256, 'preserve original labels and definition order too');
});
