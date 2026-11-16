import test from 'node:test';
import assert from 'node:assert/strict';

// Import failure is an assertion in RED, not an unrelated loader failure.
const condition = await import('../assets/js/object-condition.mjs').catch(() => ({}));

test('validation accepts absent and literal booleans without changing records', () => {
  assert.equal(typeof condition.validateObjectCondition, 'function', 'validator export is missing');
  for (const record of [{ id: 'pin' }, { destroyed: true }, { destroyed: false }]) {
    const before = structuredClone(record);
    assert.doesNotThrow(() => condition.validateObjectCondition(record));
    assert.deepEqual(record, before);
  }
});

test('validation rejects nonboolean own values before caller persistence', () => {
  for (const destroyed of ['true', 'false', '', null, undefined, 0, 1, [], {}, new Boolean(true)]) {
    let writes = 0;
    assert.throws(() => {
      condition.validateObjectCondition({ destroyed });
      writes++;
    }, /destroyed|Разрушено/);
    assert.equal(writes, 0);
  }
});

test('inherited condition values do not become authored fields', () => {
  for (const destroyed of [true, 'invalid', null]) {
    const record = Object.create({ destroyed });
    record.id = 'pin';
    assert.doesNotThrow(() => condition.validateObjectCondition(record));
    assert.equal(Object.hasOwn(record, 'destroyed'), false);
  }
});

test('validation is safe with null prototypes and a shadowed hasOwnProperty', () => {
  const record = Object.assign(Object.create(null), { destroyed: false, hasOwnProperty: null });
  assert.doesNotThrow(() => condition.validateObjectCondition(record));
  record.destroyed = 'false';
  assert.throws(() => condition.validateObjectCondition(record), /destroyed|Разрушено/);
});

test('pin and nested own-object extensions survive condition-only author merges', () => {
  const fixture = { locations: [{ id: 'pin', extension: { keep: ['literal'] }, ownobjects: [
    { id: 'own', destroyed: false, bonuses: [{ criterion: 'unchanged', value: 4 }], extension: { keep: true } }
  ] }] };
  const before = structuredClone(fixture);
  condition.validateObjectCondition(fixture.locations[0]);
  condition.validateObjectCondition(fixture.locations[0].ownobjects[0]);
  assert.deepEqual(fixture, before);
  const updated = { ...fixture.locations[0].ownobjects[0], destroyed: true };
  assert.deepEqual(updated.extension, before.locations[0].ownobjects[0].extension);
  assert.deepEqual(updated.bonuses, before.locations[0].ownobjects[0].bonuses);
  assert.equal(Object.hasOwn(fixture.locations[0], 'destroyed'), false);
});

// Minimal DOM boundary: native interaction remains the parent's browser gate.
class Element extends EventTarget {
  constructor(tag) { super(); this.tagName = tag.toUpperCase(); this.children = []; this.checked = false; }
  append(...nodes) { for (const node of nodes) { node.parentElement = this; this.children.push(node); } }
  before(node) { node.parentElement = this.parentElement; this.parentElement.children.splice(this.parentElement.children.indexOf(this), 0, node); }
  after(node) { node.parentElement = this.parentElement; this.parentElement.children.splice(this.parentElement.children.indexOf(this) + 1, 0, node); }
  closest(tag) { return this.tagName.toLowerCase() === tag ? this : this.parentElement?.closest(tag); }
  querySelector(selector) {
    for (const child of this.children) {
      if (selector.startsWith('#') ? child.id === selector.slice(1) : child.type === 'submit') return child;
      const nested = child.querySelector(selector);
      if (nested) return nested;
    }
    return null;
  }
}
function withDocument(run) {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'document');
  const root = new Element('main');
  const document = { createElement: tag => new Element(tag), getElementById: id => root.querySelector(`#${id}`) };
  for (const kind of ['location', 'object']) {
    const form = new Element('form'); form.id = `${kind}-form`;
    const label = new Element('label');
    const description = new Element('textarea'); description.id = `${kind}-description`;
    label.append(description); form.append(label); root.append(form);
  }
  Object.defineProperty(globalThis, 'document', { configurable: true, value: document });
  try { return run(document); } finally {
    if (previous) Object.defineProperty(globalThis, 'document', previous);
    else delete globalThis.document;
  }
}

test('tag renders only own literal true as safe fixed text', () => withDocument(() => {
  assert.equal(typeof condition.createObjectConditionTag, 'function', 'tag export is missing');
  for (const record of [{}, { destroyed: false }, Object.create({ destroyed: true }), null]) {
    assert.equal(condition.createObjectConditionTag(record), null);
  }
  const tag = condition.createObjectConditionTag({ destroyed: true, name: '<img onerror=evil()>' });
  assert.equal(tag.tagName, 'SPAN');
  assert.equal(tag.className, 'object-condition-tag');
  assert.equal(tag.textContent, 'Разрушено');
  assert.equal(tag.children.length, 0);
  assert.throws(() => condition.createObjectConditionTag({ destroyed: 'true' }), /destroyed|Разрушено/);
}));

test('editor installs two native labelled checkboxes and reuses its handles', () => withDocument(document => {
  assert.equal(typeof condition.initObjectConditionEditor, 'function', 'editor export is missing');
  const getData = () => ({ locations: [] });
  const editor = condition.initObjectConditionEditor({ getData });
  assert.equal(condition.initObjectConditionEditor({ getData }), editor);
  assert.deepEqual(Object.keys(editor).sort(), ['fillLocation', 'fillObject', 'readLocationPatch', 'readObjectPatch']);
  for (const kind of ['location', 'object']) {
    const checkbox = document.getElementById(`${kind}-destroyed`);
    assert.equal(checkbox.type, 'checkbox');
    assert.equal(checkbox.closest('label').children[1].textContent, 'Разрушено');
    assert.equal(checkbox.closest('form').id, `${kind}-form`);
  }
}));

test('editor patches preserve absent and explicit false independently', () => withDocument(document => {
  const editor = condition.initObjectConditionEditor({ getData: () => ({ locations: [] }) });
  editor.fillLocation({ id: 'pin' }); editor.fillObject({ id: 'own', destroyed: false });
  assert.deepEqual(editor.readLocationPatch(), {});
  assert.deepEqual(editor.readObjectPatch(), { destroyed: false });
  const checkbox = document.getElementById('location-destroyed');
  checkbox.checked = true; checkbox.dispatchEvent(new Event('change'));
  assert.deepEqual(editor.readLocationPatch(), { destroyed: true });
  checkbox.checked = false; checkbox.dispatchEvent(new Event('change'));
  assert.deepEqual(editor.readLocationPatch(), { destroyed: false });
  assert.deepEqual(editor.readObjectPatch(), { destroyed: false });
  editor.fillLocation({});
  assert.deepEqual(editor.readLocationPatch(), {});
}));

test('own-object author control preserves true, handles input and rejects invalid fills', () => withDocument(document => {
  const snapshot = { locations: [{ id: 'pin', ownobjects: [{ id: 'own', destroyed: true, extras: { keep: 1 } }] }] };
  const before = structuredClone(snapshot);
  const editor = condition.initObjectConditionEditor({ getData: () => snapshot });
  editor.fillObject(snapshot.locations[0].ownobjects[0]);
  assert.deepEqual(editor.readObjectPatch(), { destroyed: true });
  const checkbox = document.getElementById('object-destroyed');
  checkbox.checked = false; checkbox.dispatchEvent(new Event('input'));
  assert.deepEqual(editor.readObjectPatch(), { destroyed: false });
  assert.throws(() => editor.fillObject({ destroyed: null }), /destroyed|Разрушено/);
  assert.deepEqual(snapshot, before);
  editor.fillObject(Object.create({ destroyed: true }));
  assert.equal(checkbox.checked, false);
  assert.deepEqual(editor.readObjectPatch(), {});
}));
