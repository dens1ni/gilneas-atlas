const hasCondition = record => record != null && Object.prototype.hasOwnProperty.call(record, 'destroyed');

/** Validate only the optional condition; preserve every other authored field. */
export function validateObjectCondition(record) {
  if (hasCondition(record) && typeof record.destroyed !== 'boolean') {
    throw new TypeError('destroyed («Разрушено») должен быть literal boolean: true или false.');
  }
  return record;
}

/** The same inert condition label works for map records and nested own objects. */
export function createObjectConditionTag(record) {
  validateObjectCondition(record);
  if (!hasCondition(record) || record.destroyed !== true) return null;
  const tag = document.createElement('span');
  tag.className = 'object-condition-tag';
  tag.textContent = 'Разрушено';
  return tag;
}

const editorsByForm = new WeakMap();

function createConditionField(form, kind) {
  const label = document.createElement('label');
  label.className = 'check-label object-condition-check';
  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.id = `${kind}-destroyed`;
  checkbox.name = 'destroyed';
  const text = document.createElement('span');
  text.textContent = 'Разрушено';
  label.append(checkbox, text);
  const description = form.querySelector(`#${kind}-description`)?.closest('label');
  if (description) description.after(label);
  else {
    const submit = form.querySelector('[type="submit"]');
    if (submit) submit.before(label);
    else form.append(label);
  }
  let present = false;
  let touched = false;
  const touch = () => { touched = true; };
  checkbox.addEventListener('input', touch);
  checkbox.addEventListener('change', touch);
  return {
    fill(record) {
      validateObjectCondition(record);
      present = hasCondition(record);
      touched = false;
      checkbox.checked = present && record.destroyed === true;
    },
    readPatch() {
      return present || touched || checkbox.checked ? { destroyed: checkbox.checked } : {};
    }
  };
}

/** Unsaved form helpers only: parent merges patches into its validated transaction. */
export function initObjectConditionEditor({ getData }) {
  if (typeof getData !== 'function') throw new TypeError('getData должен быть функцией.');
  const locationForm = document.getElementById('location-form');
  const objectForm = document.getElementById('object-form');
  if (!locationForm || !objectForm) throw new Error('Не найдены location-form / object-form.');
  const existing = editorsByForm.get(locationForm);
  if (existing?.objectForm === objectForm) return existing.handles;
  const location = createConditionField(locationForm, 'location');
  const object = createConditionField(objectForm, 'object');
  const handles = {
    fillLocation: location.fill,
    fillObject: object.fill,
    readLocationPatch: location.readPatch,
    readObjectPatch: object.readPatch
  };
  editorsByForm.set(locationForm, { objectForm, handles });
  return handles;
}
