import { deriveWallProgress, updateWallEvent, removeWallEvent } from './wall-progress.mjs';
import { makeId } from './model.mjs';
import { svgIcon } from './icons.mjs';
import { isEditingEnabled, getEditingRevision } from './edit-mode.mjs';

const element = (tag, className = '', text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};
const field = (id, labelText, tag = 'input', type = 'text') => {
  const label = element('label', '', labelText);
  const input = element(tag);
  input.id = id;
  if (tag === 'input') input.type = type;
  else input.rows = 3;
  label.append(input);
  return { label, input };
};

/** The parent owns validation, storage and the full-snapshot commit. */
export function initWallJournal(ctx) {
  const editingEnabled = () => ctx.isEditingEnabled?.() ?? isEditingEnabled();
  const opener = document.getElementById('wall-history-open');
  const dialog = element('dialog', 'iron-dialog wide');
  dialog.id = 'wall-journal';
  dialog.tabIndex = -1;
  dialog.setAttribute('aria-labelledby', 'wall-journal-title');
  const head = element('header', 'dialog-head');
  const heading = element('div');
  const title = element('h2', '', 'Летопись Стены Седогрива');
  title.id = 'wall-journal-title';
  heading.append(element('span', 'eyebrow', 'КОРОЛЕВСКАЯ ЛЕТОПИСЬ'), title);
  const closeButton = element('button', 'square');
  closeButton.type = 'button';
  closeButton.dataset.close = dialog.id;
  closeButton.setAttribute('aria-label', 'Закрыть летопись стены');
  closeButton.append(svgIcon('close'));
  head.append(heading, closeButton);
  const body = element('div', 'dialog-content wall-journal-body');
  const summary = element('div', 'wall-journal-summary');
  summary.id = 'wall-journal-summary';
  const progressHeading = element('div', 'wall-heading');
  const progressValue = element('span', 'wall-journal-progress-value');
  progressValue.id = 'wall-journal-progress-value';
  progressHeading.append(element('strong', '', 'Строительство Стены Седогрива'), progressValue);
  const journalProgress = element('progress');
  journalProgress.id = 'wall-journal-progress';
  const trackNotice = element('p', 'wall-journal-note');
  summary.append(progressHeading, journalProgress, trackNotice);
  heading.append(summary);
  const order = element('p', 'wall-journal-note', 'События идут в порядке добавления. Изменение или удаление записи пересчитывает все последующие события.');
  order.setAttribute('data-edit-only', '');
  const history = element('div', 'wall-event-history');
  history.id = 'wall-event-history';
  const form = element('form', 'wall-event-form');
  form.id = 'wall-event-form';
  form.setAttribute('data-edit-only', '');
  form.noValidate = true;
  const id = element('input');
  id.id = 'wall-event-id';
  id.type = 'hidden';
  const name = field('wall-event-name', 'Название');
  name.input.required = true;
  const description = field('wall-event-description', 'Краткое описание', 'textarea');
  const delta = field('wall-event-delta', 'Изменение прогресса (+ / −)', 'input', 'number');
  delta.input.required = true;
  delta.input.step = '1';
  delta.input.min = '-1000000';
  delta.input.max = '1000000';
  const effectsSection = element('section', 'wall-effect-fields');
  const effectList = element('div', 'wall-effect-list');
  effectList.id = 'wall-effect-list';
  const effectActions = element('div', 'wall-effect-add-actions');
  const bonusAdd = element('button', 'bonus-button', 'Добавить бонус');
  bonusAdd.type = 'button';
  bonusAdd.id = 'wall-effect-bonus-add';
  const penaltyAdd = element('button', 'penalty-button', 'Добавить штраф');
  penaltyAdd.type = 'button';
  penaltyAdd.id = 'wall-effect-penalty-add';
  effectActions.append(bonusAdd, penaltyAdd);
  effectsSection.append(element('h4', '', 'Бонусы и штрафы'), effectList, effectActions);
  let effectsDraft = [];
  const formTitle = element('h3', '', 'Новое событие');
  const errorField = element('p', 'error');
  errorField.id = 'wall-event-error';
  errorField.setAttribute('role', 'alert');
  const saveButton = element('button', 'brass-button', 'Сохранить событие');
  saveButton.type = 'submit';
  form.append(formTitle, id, name.label, description.label, delta.label, effectsSection, errorField, saveButton);
  body.append(order, history, form);
  dialog.append(head, body);
  document.body.append(dialog);

  function render() {
    const snapshot = ctx.getData();
    const hasTrack = Object.hasOwn(snapshot.meta, 'wallConstruction');
    const derived = deriveWallProgress(hasTrack ? snapshot.meta.wallConstruction : { value: 0, max: 100 });
    for (const input of [name.input, description.input, delta.input, saveButton, bonusAdd, penaltyAdd]) input.disabled = !hasTrack;
    const progress = document.getElementById('wall-progress');
    progress.max = derived.max;
    progress.value = derived.value;
    progress.textContent = `${derived.value} / ${derived.max}`;
    progress.setAttribute('aria-valuemin', '0');
    progress.setAttribute('aria-valuenow', String(derived.value));
    progress.setAttribute('aria-valuemax', String(derived.max));
    progress.setAttribute('aria-label', `Строительство Стены Седогрива: ${derived.value} из ${derived.max}`);
    document.getElementById('wall-progress-value').textContent = `${derived.value} / ${derived.max}`;
    journalProgress.max = derived.max;
    journalProgress.value = derived.value;
    journalProgress.textContent = `${derived.value} / ${derived.max}`;
    for (const attribute of ['aria-valuemin', 'aria-valuenow', 'aria-valuemax', 'aria-label']) journalProgress.setAttribute(attribute, progress.getAttribute(attribute));
    progressValue.textContent = `${derived.value} / ${derived.max}`;
    trackNotice.textContent = hasTrack ? '' : 'Шкала строительства не задана в этом снимке. Добавление событий недоступно.';
    trackNotice.hidden = hasTrack;
    history.replaceChildren();
    if (!derived.events.length) history.append(element('p', 'wall-history-empty', 'События ещё не добавлены'));
    for (const event of derived.events) {
      const card = element('article', 'wall-event-card');
      card.dataset.wallEventId = event.id;
      const signed = event.delta < 0 ? `−${Math.abs(event.delta)}` : `+${event.delta}`;
      card.append(element('h3', '', event.name), element('p', 'wall-event-description', event.description ?? ''),
        element('p', 'wall-event-progress', `${signed} · ${event.before} → ${event.after}`));
      if (event.appliedDelta !== event.delta) {
        const effective = event.appliedDelta < 0 ? `−${Math.abs(event.appliedDelta)}` : `+${event.appliedDelta}`;
        card.append(element('p', 'wall-event-clipped', `Фактически: ${effective} (пределы 0…${derived.max})`));
      }
      for (const effect of event.effects ?? []) {
        card.append(element('p', `wall-event-effect ${effect.kind}`, `${effect.kind === 'bonus' ? 'Бонус' : 'Штраф'}: ${effect.text}`));
      }
      const actions = element('div', 'wall-event-actions');
      actions.setAttribute('data-edit-only', '');
      const editButton = element('button', 'iron-button', 'Редактировать');
      editButton.type = 'button';
      editButton.dataset.wallEventEdit = event.id;
      editButton.addEventListener('click', () => edit(event.id));
      const deleteButton = element('button', 'danger-button', 'Удалить');
      deleteButton.type = 'button';
      deleteButton.dataset.wallEventDelete = event.id;
      deleteButton.addEventListener('click', () => remove(event.id));
      actions.append(editButton, deleteButton);
      card.append(actions);
      history.append(card);
    }
  }

  function renderEffects() {
    effectList.replaceChildren();
    for (const effect of effectsDraft) {
      const row = element('div', `wall-effect-editor-row ${effect.kind}`);
      row.dataset.wallEffectId = effect.id;
      const label = element('label', '', effect.kind === 'bonus' ? 'Бонус' : 'Штраф');
      const input = element('textarea');
      input.rows = 2;
      input.value = effect.text;
      input.addEventListener('input', () => { effect.text = input.value; });
      label.append(input);
      const removeButton = element('button', 'square');
      removeButton.type = 'button';
      removeButton.dataset.wallEffectRemove = effect.id;
      removeButton.setAttribute('aria-label', effect.kind === 'bonus' ? 'Удалить бонус' : 'Удалить штраф');
      removeButton.append(svgIcon('close'));
      removeButton.addEventListener('click', () => {
        effectsDraft = effectsDraft.filter(record => record.id !== effect.id);
        renderEffects();
        bonusAdd.focus();
      });
      row.append(label, removeButton);
      effectList.append(row);
    }
  }
  function addEffect(kind) {
    if (!editingEnabled()) return;
    effectsDraft.push({ id: makeId('wall-effect'), kind, text: '' });
    renderEffects();
    effectList.lastElementChild.querySelector('textarea').focus();
  }
  bonusAdd.addEventListener('click', () => addEffect('bonus'));
  penaltyAdd.addEventListener('click', () => addEffect('penalty'));

  function resetForm() {
    form.reset();
    effectsDraft = [];
    renderEffects();
    id.value = '';
    delta.input.value = '0';
    errorField.textContent = '';
    formTitle.textContent = 'Новое событие';
  }

  function edit(eventId) {
    if (!editingEnabled()) return;
    const record = ctx.getData().meta.wallConstruction.events?.find(event => event.id === eventId);
    if (!record) return;
    resetForm();
    id.value = record.id;
    name.input.value = record.name;
    description.input.value = record.description ?? '';
    delta.input.value = String(record.delta);
    effectsDraft = structuredClone(record.effects ?? []);
    renderEffects();
    formTitle.textContent = 'Редактирование события';
    name.input.focus();
  }

  async function remove(eventId) {
    if (!editingEnabled()) return;
    const revision = getEditingRevision();
    try {
      if (!await ctx.confirm('Удалить событие стены?', 'Запись будет удалена, а все последующие события пересчитаны.')) return;
      if (!editingEnabled() || revision !== getEditingRevision()) return;
      ctx.replaceData(removeWallEvent(ctx.getData(), eventId));
      if (id.value === eventId) resetForm();
      render();
      ctx.toast?.('Событие стены удалено');
    } catch (error) {
      errorField.textContent = error instanceof Error ? error.message : String(error);
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!editingEnabled()) return;
    errorField.textContent = '';
    try {
      if (!delta.input.value.trim()) throw new Error('Укажите изменение прогресса целым числом');
      const record = {
        id: id.value || makeId('wall-event'), name: name.input.value,
        description: description.input.value, delta: Number(delta.input.value), effects: structuredClone(effectsDraft),
      };
      ctx.replaceData(updateWallEvent(ctx.getData(), record));
      resetForm();
      render();
      ctx.toast?.('Событие стены сохранено');
    } catch (error) {
      errorField.textContent = error instanceof Error ? error.message : String(error);
    }
  });

  function open() {
    document.querySelectorAll('dialog[open]').forEach(other => { if (other !== dialog) other.close(); });
    if (!dialog.open) resetForm();
    render();
    if (!dialog.open) dialog.showModal();
    dialog.focus({ preventScroll: true });
  }
  function close() { dialog.close(); }
  // Native close events are queued: never clear a newly reopened draft.
  dialog.addEventListener('close', () => { if (!dialog.open) resetForm(); });
  opener.addEventListener('click', open);
  closeButton.addEventListener('click', close);
  window.addEventListener('gilneas-data-changed', render);
  window.addEventListener('gilneas-edit-mode-changed', event => {
    if (!event.detail?.enabled) resetForm();
  });
  render();
  return { open, render, close };
}
