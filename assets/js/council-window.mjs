import { COUNCIL_PARTIES, resolveCouncilMember, upsertCouncilMember, removeCouncilMember } from './royal-council.mjs';
import * as councilInfluence from './council-influence.mjs';
import { createFactionShield } from './heraldry.mjs';
import { isEditingEnabled, getEditingRevision } from './edit-mode.mjs';
import { makeId } from './model.mjs';
import { createNobleLifeStatusTag } from './noble-life-status.mjs';

const STANCES = Object.freeze({ support: 'Поддерживает строительство Стены', oppose: 'Против строительства Стены',
  unknown: 'Позиция по Стене не установлена' });

function element(tag, text = '', className = '') {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

/** The parent alone validates/persists full snapshots through replaceData. */
export function initRoyalCouncilWindow(ctx) {
  const editingEnabled = () => ctx.isEditingEnabled?.() ?? isEditingEnabled();
  const dialog = element('dialog', '', 'iron-dialog council-dialog');
  dialog.id = 'royal-council'; dialog.tabIndex = -1;
  dialog.setAttribute('aria-labelledby', 'council-title');
  const header = element('header', '', 'dialog-head');
  const identity = element('div');
  const title = element('h2', 'Королевский Совет'); title.id = 'council-title';
  identity.append(element('span', 'КОРОЛЕВСКИЙ РЕЕСТР · ПОЛИТИЧЕСКИЕ НАЗНАЧЕНИЯ', 'eyebrow'), title);
  const closeButton = element('button', '×', 'square'); closeButton.id = 'council-close'; closeButton.type = 'button';
  closeButton.setAttribute('aria-label', 'Закрыть Королевский Совет'); closeButton.dataset.close = 'royal-council';
  header.append(identity, closeButton);
  const body = element('div', '', 'council-body');
  const toolbar = element('div', '', 'council-toolbar');
  const add = element('button', 'Добавить участника', 'brass-button'); add.id = 'council-add'; add.type = 'button';
  const historyLabel = element('label', '', 'council-check');
  const history = element('input'); history.type = 'checkbox'; history.id = 'council-show-history';
  historyLabel.append(history, element('span', 'Показать исторические записи'));
  toolbar.append(add, historyLabel);
  const filters = element('div', '', 'council-filters');
  function filter(id, label, options) {
    const wrapper = element('label', label); const control = element('select'); control.id = id;
    choices(control, options); control.value = 'all'; wrapper.append(control); filters.append(wrapper); return control;
  }
  const partyFilter = filter('council-filter-party', 'Партия', [['all', 'Все партии'], ...COUNCIL_PARTIES.map(party => [party.id, party.name])]);
  const kindFilter = filter('council-filter-kind', 'Участники', [['all', 'Люди и дома'], ['person', 'Люди'], ['faction', 'Дома / фракции']]);
  kindFilter.value = 'faction';
  // Presentation-only hint: consumed once, never restored by render/open.
  const kindFilterLabel = kindFilter.parentElement;
  kindFilterLabel.classList.add('council-filter-hint');
  kindFilterLabel.addEventListener('mouseover', () => {
    kindFilterLabel.classList.remove('council-filter-hint');
  }, { once: true });
  const influence = element('section', '', 'council-influence'); influence.id = 'council-influence';
  influence.setAttribute('aria-labelledby', 'council-influence-title');
  const influenceTitle = element('h3', 'Влияние партий'); influenceTitle.id = 'council-influence-title';
  const influenceHeader = element('div', '', 'council-influence-head');
  const influenceEdit = element('button', 'Изменить запас очков', 'iron-button'); influenceEdit.id = 'council-influence-edit'; influenceEdit.type = 'button';
  influenceEdit.setAttribute('aria-controls', 'council-influence-form'); influenceEdit.setAttribute('aria-expanded', 'false');
  influenceHeader.append(influenceTitle, influenceEdit);
  const influenceLabels = element('div', '', 'council-influence-labels');
  const influenceBar = element('div', '', 'council-influence-bar'); influenceBar.setAttribute('role', 'img');
  const poolDisplays = new Map();
  for (const partyId of ['royalists', 'internationalists']) {
    const label = element('div', '', 'council-influence-label'); label.dataset.party = partyId;
    label.append(element('strong', COUNCIL_PARTIES.find(party => party.id === partyId).name, 'council-influence-name'));
    const values = element('div', '', 'council-influence-values');
    const points = element('span', '', 'council-influence-points'); const percent = element('span', '', 'council-influence-percent');
    values.append(points, percent); label.append(values); influenceLabels.append(label);
    const span = element('span'); span.id = `council-influence-${partyId}`; span.setAttribute('aria-hidden', 'true');
    influenceBar.append(span); poolDisplays.set(partyId, { points, percent, span });
  }
  influence.style.setProperty('--council-royalist-color', councilInfluence.COUNCIL_INFLUENCE_COLORS.royalists);
  influence.style.setProperty('--council-internationalist-color', councilInfluence.COUNCIL_INFLUENCE_COLORS.internationalists);
  const influenceMessage = element('p', '', 'council-influence-message');
  const influenceForm = element('form', '', 'council-influence-form'); influenceForm.id = 'council-influence-form'; influenceForm.hidden = true; influenceForm.noValidate = true;
  const influenceFields = element('div', '', 'council-form-fields');
  function poolField(id, label) {
    const wrapper = element('label', label); const input = element('input'); input.id = id;
    input.type = 'number'; input.min = '0'; input.step = '1'; input.required = true;
    wrapper.append(input); influenceFields.append(wrapper); return input;
  }
  const royalistPoints = poolField('council-royalist-points', 'Роялисты · запас очков');
  const internationalistPoints = poolField('council-internationalist-points', 'Интернационалисты · запас очков');
  const influenceError = element('p', '', 'council-form-error'); influenceError.id = 'council-influence-error'; influenceError.setAttribute('role', 'alert'); influenceError.hidden = true;
  const influenceActions = element('div', '', 'council-form-actions');
  const influenceSave = element('button', 'Сохранить запас', 'brass-button'); influenceSave.id = 'council-influence-save'; influenceSave.type = 'submit';
  const influenceCancel = element('button', 'Отмена', 'iron-button'); influenceCancel.id = 'council-influence-cancel'; influenceCancel.type = 'button';
  influenceActions.append(influenceSave, influenceCancel); influenceForm.append(influenceFields, influenceError, influenceActions);
  influence.append(influenceHeader, influenceLabels, influenceBar, influenceMessage, influenceForm);
  const rosters = element('div', '', 'council-rosters');
  const historical = element('section', '', 'council-history'); historical.id = 'council-history'; historical.hidden = true;
  const form = element('form', '', 'council-form'); form.id = 'council-form'; form.hidden = true; form.noValidate = true;
  const formTitle = element('h3'); formTitle.id = 'council-form-title';
  const fields = element('div', '', 'council-form-fields');
  function field(tag, id, label) {
    const wrapper = element('label', label); const control = element(tag); control.id = id;
    wrapper.append(control); fields.append(wrapper); return control;
  }
  function choices(control, options) {
    control.replaceChildren(...options.map(([value, text]) => { const option = element('option', text); option.value = value; return option; }));
  }
  const kind = field('select', 'council-kind', 'Участник'); choices(kind, [['person', 'Человек'], ['faction', 'Дом / фракция']]);
  const factionSelect = field('select', 'council-faction', 'Дом из текущего реестра');
  const personSelect = field('select', 'council-person', 'Персонаж из текущего реестра');
  const name = field('input', 'council-name', 'Имя отдельного человека'); name.type = 'text';
  const memberTitle = field('input', 'council-member-title', 'Титул / роль (необязательно)'); memberTitle.type = 'text';
  const partySelect = field('select', 'council-party', 'Политическая партия');
  choices(partySelect, COUNCIL_PARTIES.map(party => [party.id, party.name]));
  const stance = field('select', 'council-stance', 'Позиция по Стене'); choices(stance, Object.entries(STANCES));
  const advisor = field('input', 'council-advisor', 'Королевский советник'); advisor.type = 'checkbox'; advisor.parentElement.className = 'council-check';
  const active = field('input', 'council-active', 'Входит в действующий Совет'); active.type = 'checkbox'; active.parentElement.className = 'council-check';
  const personPartyInfluence = field('input', 'council-person-party-influence', 'Влияние в партии · от 0 до 100');
  const personKingdomInfluence = field('input', 'council-person-kingdom-influence', 'Влияние во всём королевстве · от 0 до 100');
  for (const control of [personPartyInfluence, personKingdomInfluence]) { control.type = 'number'; control.min = '0'; control.max = '100'; control.step = '1'; }
  const personInfluenceHint = element('p', '', 'council-person-influence-hint'); personInfluenceHint.id = 'council-person-influence-hint'; fields.append(personInfluenceHint);
  const note = field('textarea', 'council-note', 'Заметка / основание назначения'); note.rows = 3;
  const errorMessage = element('p', '', 'council-form-error'); errorMessage.id = 'council-form-error'; errorMessage.setAttribute('role', 'alert'); errorMessage.hidden = true;
  const actions = element('div', '', 'council-form-actions');
  const save = element('button', 'Сохранить назначение', 'brass-button'); save.id = 'council-save'; save.type = 'submit';
  const cancel = element('button', 'Отмена', 'iron-button'); cancel.id = 'council-cancel'; cancel.type = 'button'; actions.append(save, cancel);
  form.append(formTitle, fields, errorMessage, actions);
  body.append(toolbar, filters, influence, form, rosters, historical); dialog.append(header, body); document.body.append(dialog);
  for (const node of [add, form, influenceEdit, influenceForm]) node.setAttribute('data-edit-only', '');
  let editId = null;
  const touchedPersonInfluence = new Set();

  function refreshSelectors(data) {
    const factionId = factionSelect.value, personId = personSelect.value;
    choices(factionSelect, [['', 'Выберите дом'], ...(data.factions ?? []).map(record => [record.id, record.name])]);
    choices(personSelect, [['', 'Отдельный человек — имя вручную'], ...(data.nobles ?? []).map(record => [record.id, record.name])]);
    for (const [control, id] of [[factionSelect, factionId], [personSelect, personId]]) {
      if (id && ![...control.options].some(option => option.value === id)) {
        const missing = element('option', `Удалён из реестра: ${id}`); missing.value = id; missing.disabled = true; control.append(missing);
      }
    }
    factionSelect.value = factionId; personSelect.value = personId;
    factionSelect.parentElement.hidden = kind.value !== 'faction';
    personSelect.parentElement.hidden = kind.value !== 'person';
    const independent = kind.value === 'person' && !personSelect.value;
    name.parentElement.hidden = !independent; name.required = independent;
    memberTitle.parentElement.hidden = kind.value !== 'person';
    personPartyInfluence.parentElement.hidden = kind.value !== 'person';
    personKingdomInfluence.parentElement.hidden = kind.value !== 'person';
    personPartyInfluence.disabled = kind.value !== 'person';
    personKingdomInfluence.disabled = kind.value !== 'person';
    personInfluenceHint.hidden = kind.value !== 'person';
    factionSelect.required = kind.value === 'faction'; personSelect.required = false;
  }

  function edit(id = null) {
    if (!editingEnabled()) return;
    const data = ctx.getData(); const member = id ? data.royalCouncil?.members.find(record => record.id === id) : null;
    if (id && !member) throw new Error('Участник Совета не найден');
    editId = id; formTitle.textContent = id ? 'Изменить назначение' : 'Новый участник';
    kind.value = member?.kind ?? 'person'; refreshSelectors(data);
    factionSelect.value = member?.kind === 'faction' ? member.refId : '';
    personSelect.value = member?.kind === 'person' ? member.refId ?? '' : '';
    name.value = member?.name ?? ''; memberTitle.value = member?.title ?? '';
    refreshSelectors(data);
    partySelect.value = member?.party ?? 'neutral'; stance.value = member?.stance ?? 'unknown';
    advisor.checked = member?.advisor ?? false; active.checked = member?.active ?? true; note.value = member?.note ?? '';
    personPartyInfluence.value = member?.influence?.party ?? 0; personKingdomInfluence.value = member?.influence?.kingdom ?? 0;
    touchedPersonInfluence.clear();
    personInfluenceHint.textContent = !member || member.kind !== 'person' ? 'Оценки 0 будут сохранены только при сохранении нового человека.' :
      Object.hasOwn(member, 'influence') ? 'Две независимые оценки от 0 до 100; они не пополняют запас очков партии.' :
      'Оценки не заданы. Значение 0 — только для справки; без правки этих полей оценки не сохраняются.';
    clearMemberError(); save.disabled = false; form.hidden = false; kind.focus();
  }

  function clearMemberError() { errorMessage.textContent = ''; errorMessage.hidden = true; }

  function readPersonRating(control, label) {
    if (control.value === '' || !Number.isInteger(control.valueAsNumber) || control.valueAsNumber < 0 || control.valueAsNumber > 100) {
      throw new Error(`${label}: укажите целое число от 0 до 100.`);
    }
    return control.valueAsNumber;
  }

  function saveMember(event) {
    event.preventDefault(); if (!editingEnabled() || form.hidden) return; clearMemberError();
    try {
      const ratings = kind.value === 'person' ? {
        party: readPersonRating(personPartyInfluence, 'Влияние в партии'),
        kingdom: readPersonRating(personKingdomInfluence, 'Влияние во всём королевстве') } : null;
      if (!form.reportValidity()) return;
      const data = ctx.getData(); const previous = editId ? data.royalCouncil?.members.find(record => record.id === editId) : null;
      if (editId && !previous) throw new Error('Участник Совета удалён из текущего снимка');
      const member = { ...previous, id: editId ?? makeId('council-member'), kind: kind.value,
        party: partySelect.value, stance: stance.value, advisor: advisor.checked, active: active.checked, note: note.value };
      if (kind.value === 'faction') {
        member.refId = factionSelect.value;
        if (previous?.kind === 'person') delete member.influence;
      }
      else {
        if (Object.hasOwn(previous ?? {}, 'title') || memberTitle.value !== '' || !personSelect.value) member.title = memberTitle.value;
        if (personSelect.value) member.refId = personSelect.value;
        else { delete member.refId; member.name = name.value; }
        if (!previous || previous.kind !== 'person' || touchedPersonInfluence.size) {
          member.influence = { ...previous?.influence,
            party: touchedPersonInfluence.has('party') || !previous || previous.kind !== 'person' ? ratings.party : previous.influence?.party ?? 0,
            kingdom: touchedPersonInfluence.has('kingdom') || !previous || previous.kind !== 'person' ? ratings.kingdom : previous.influence?.kingdom ?? 0 };
        }
      }
      ctx.replaceData(upsertCouncilMember(data, member));
      form.hidden = true; editId = null; render(); ctx.toast?.('Назначение Совета сохранено.'); add.focus();
    } catch (error) { errorMessage.textContent = error.message; errorMessage.hidden = false; ctx.toast?.(error.message); }
  }

  async function remove(id) {
    if (!editingEnabled()) return;
    const revision = getEditingRevision();
    try {
      const data = ctx.getData(); const member = data.royalCouncil?.members.find(record => record.id === id);
      if (!member) throw new Error('Участник Совета не найден');
      const profile = resolveCouncilMember(data, member);
      if (!ctx.confirm || !(await ctx.confirm('Удалить назначение Совета?', `Назначение «${profile.name}» будет удалено. Дома и персонажи останутся в атласе.`))) return;
      if (!editingEnabled() || revision !== getEditingRevision()) return;
      ctx.replaceData(removeCouncilMember(ctx.getData(), id));
      if (editId === id) { form.hidden = true; editId = null; }
      render(); ctx.toast?.('Назначение Совета удалено.'); add.focus();
    } catch (error) { errorMessage.textContent = error.message; errorMessage.hidden = false; ctx.toast?.(error.message); }
  }

  function sourceLinks(container, data, ids) {
    const links = element('div', '', 'council-source-links');
    for (const id of ids ?? []) {
      const source = (data.sources ?? []).find(value => value.id === id);
      if (!source) continue;
      let url;
      try { url = new URL(source.url); } catch { continue; }
      if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) continue;
      const link = element('a', `[${id}] ${source.title ?? 'Источник'}`);
      link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; links.append(link);
    }
    if (links.childElementCount) container.append(links);
  }

  function memberRow(data, member) {
    const profile = resolveCouncilMember(data, member);
    const row = element('article', '', 'council-member'); row.dataset.memberId = member.id;
    const identity = element('div', '', 'council-member-identity');
    const factionId = profile.faction?.id ?? profile.house?.id;
    if (factionId) identity.append(createFactionShield(data, factionId));
    const text = element('div', '', 'council-member-name'); text.append(element('h5', profile.name));
    if (member.kind === 'person') text.firstElementChild.append(createNobleLifeStatusTag(profile.noble));
    if (profile.title) text.append(element('p', profile.title, 'council-member-title'));
    if (profile.house) text.append(element('p', profile.house.name, 'council-member-house'));
    if (member.advisor) text.append(element('strong', member.kind === 'faction' ? 'Представитель — советник короля' : 'Королевский советник', 'council-advisor-badge'));
    identity.append(text); row.append(identity);
    const badges = element('div', '', 'council-member-badges');
    badges.append(element('span', COUNCIL_PARTIES.find(party => party.id === member.party).name, 'council-party-badge'));
    if (member.potentialAlly) badges.append(element('span', 'Возможный союзник', 'council-potential-badge'));
    if (!member.active) badges.append(element('span', 'Не входит в действующий Совет', 'council-inactive-badge'));
    row.append(badges, element('p', STANCES[member.stance], `council-stance stance-${member.stance}`));
    if (member.kind === 'person') {
      const ratings = element('div', '', 'council-person-ratings');
      ratings.style.setProperty('--council-rating-color', councilInfluence.COUNCIL_INFLUENCE_COLORS[member.party] ?? 'var(--royal-muted, #96978d)');
      const partyLabel = { royalists: 'Среди роялистов', internationalists: 'Среди интернационалистов', neutral: 'Среди нейтралов' }[member.party];
      for (const [scope, label] of [['party', partyLabel], ['kingdom', 'Во всём королевстве']]) {
        const value = member.influence?.[scope] ?? 0;
        const wrapper = element('label', '', 'council-person-rating');
        const caption = element('span', '', 'council-rating-caption');
        caption.append(element('span', label), element('span', `${value} / 100`, 'council-rating-value'));
        const progress = element('progress', `${value} / 100`); progress.dataset.influenceScope = scope;
        progress.setAttribute('max', '100'); progress.setAttribute('value', String(value));
        wrapper.append(caption, progress); ratings.append(wrapper);
      }
      if (!Object.hasOwn(member, 'influence')) ratings.append(element('p', 'Оценки не заданы; 0 показан только для справки.', 'council-rating-unknown'));
      row.append(ratings);
    }
    if (member.note) row.append(element('p', member.note, 'council-note'));
    sourceLinks(row, data, member.sources);
    const editButton = element('button', 'Изменить назначение', 'iron-button'); editButton.type = 'button'; editButton.dataset.councilEdit = member.id;
    editButton.setAttribute('data-edit-only', ''); editButton.hidden = !editingEnabled();
    editButton.addEventListener('click', () => edit(member.id)); row.append(editButton);
    const removeButton = element('button', 'Удалить назначение', 'danger-button'); removeButton.type = 'button'; removeButton.dataset.councilRemove = member.id;
    removeButton.setAttribute('data-edit-only', ''); removeButton.hidden = !editingEnabled();
    removeButton.addEventListener('click', () => remove(member.id)); row.append(removeButton);
    if (profile.noble && ctx.onShowNoble) {
      const button = element('button', 'Открыть досье', 'iron-button'); button.type = 'button';
      button.dataset.councilNoble = profile.noble.id;
      button.addEventListener('click', () => { dialog.close(); ctx.onShowNoble(profile.noble.id); }); row.append(button);
    }
    return row;
  }

  function clearInfluenceError() { influenceError.textContent = ''; influenceError.hidden = true; }

  function hideInfluenceEditor({ focus = true } = {}) {
    influenceForm.hidden = true; influenceEdit.setAttribute('aria-expanded', 'false'); clearInfluenceError();
    if (focus) influenceEdit.focus({ preventScroll: true });
  }

  function toggleInfluenceEditor() {
    if (!editingEnabled()) return;
    if (!influenceForm.hidden) { hideInfluenceEditor(); return; }
    const pools = councilInfluence.derivePartyInfluence(ctx.getData().royalCouncil);
    royalistPoints.value = pools.royalists; internationalistPoints.value = pools.internationalists;
    clearInfluenceError(); influenceForm.hidden = false; influenceEdit.setAttribute('aria-expanded', 'true'); royalistPoints.focus();
  }

  function readPoolPoints(control, label) {
    if (control.value === '' || !Number.isSafeInteger(control.valueAsNumber) || control.valueAsNumber < 0) {
      throw new Error(`${label}: укажите неотрицательное целое число очков, точно представимое в JSON.`);
    }
    return control.valueAsNumber;
  }

  function saveInfluence(event) {
    event.preventDefault(); if (!editingEnabled() || influenceForm.hidden) return; clearInfluenceError();
    try {
      const points = { royalists: readPoolPoints(royalistPoints, 'Роялисты'),
        internationalists: readPoolPoints(internationalistPoints, 'Интернационалисты') };
      ctx.replaceData(councilInfluence.updatePartyInfluence(ctx.getData(), points));
      hideInfluenceEditor(); render(); ctx.toast?.('Запас очков влияния сохранён.');
    } catch (error) { influenceError.textContent = error.message; influenceError.hidden = false; }
  }

  function renderInfluence(data) {
    const pools = councilInfluence.derivePartyInfluence(data.royalCouncil);
    influence.dataset.empty = String(pools.empty);
    const percentages = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 });
    for (const [partyId, share] of [['royalists', pools.royalistShare], ['internationalists', pools.internationalistShare]]) {
      const { points, percent, span } = poolDisplays.get(partyId);
      points.textContent = `${pools[partyId]} очк.`;
      percent.textContent = `${percentages.format(share * 100)}%`;
      span.style.width = `${share * 100}%`;
    }
    influenceBar.setAttribute('aria-label', `Роялисты: ${pools.royalists} очков, ${poolDisplays.get('royalists').percent.textContent}; Интернационалисты: ${pools.internationalists} очков, ${poolDisplays.get('internationalists').percent.textContent}`);
    influenceMessage.textContent = !pools.initialized ? (editingEnabled() ?
      'Очки влияния партий не заданы. Задайте общий запас каждой партии.' : 'Очки влияния партий не заданы.') :
      pools.empty ? 'У партий нет очков влияния. Доли не распределены.' :
      'Общий запас очков партий. Он не зависит от числа людей и домов или выбранных фильтров.';
  }

  function render() {
    const data = ctx.getData();
    add.hidden = !editingEnabled(); influenceEdit.hidden = !editingEnabled();
    const focused = document.activeElement;
    const focusAction = ['councilEdit', 'councilRemove', 'councilNoble'].find(key => focused?.dataset?.[key] !== undefined);
    const focusId = focusAction ? focused.dataset[focusAction] : null;
    refreshSelectors(data);
    renderInfluence(data);
    if (!form.hidden && editId && !data.royalCouncil?.members.some(member => member.id === editId)) {
      errorMessage.textContent = 'Участник Совета удалён из текущего снимка. Несохранённые поля оставлены для проверки.';
      errorMessage.hidden = false; save.disabled = true;
    }
    rosters.replaceChildren();
    const members = data.royalCouncil?.members ?? [];
    const matchesFilters = member => (partyFilter.value === 'all' || member.party === partyFilter.value) &&
      (kindFilter.value === 'all' || member.kind === kindFilter.value);
    const filtered = members.filter(matchesFilters);
    rosters.dataset.partyFilter = partyFilter.value;
    for (const party of COUNCIL_PARTIES) {
      if (partyFilter.value !== 'all' && partyFilter.value !== party.id) continue;
      const section = element('section', '', 'council-party'); section.dataset.party = party.id;
      const assignedParty = filtered.filter(member => member.active && member.party === party.id);
      section.append(element('h3', `${party.name} · ${assignedParty.length}`));
      if (party.leaderId) {
        const noble = (data.nobles ?? []).find(record => record.id === party.leaderId);
        section.append(element('p', `Лидер партии: ${noble?.name ?? 'Персонаж не найден в текущем реестре'}`, 'council-leader'));
      }
      for (const [className, heading, kind] of [['house', 'Дома', 'faction'], ['person', 'Люди', 'person']]) {
        if (kindFilter.value !== 'all' && kindFilter.value !== kind) continue;
        const group = element('div', '', `council-${className}-list`);
        const assigned = assignedParty.filter(member => member.kind === kind);
        group.append(element('h4', `${heading} · ${assigned.length}`));
        for (const member of assigned) group.append(memberRow(data, member));
        if (!assigned.length) group.append(element('p', 'Нет назначений.', 'council-empty'));
        section.append(group);
      }
      rosters.append(section);
    }
    historical.hidden = !history.checked;
    const inactive = filtered.filter(member => !member.active);
    historical.replaceChildren(element('h3', `Исторические записи · не действующий Совет · ${inactive.length}`));
    if (history.checked) {
      for (const member of inactive) historical.append(memberRow(data, member));
      if (!inactive.length) historical.append(element('p', 'Исторических назначений нет.', 'council-empty'));
    }
    if (focusAction) {
      const replacement = [...dialog.querySelectorAll('button')].find(button => button.dataset[focusAction] === focusId);
      (replacement ?? add).focus({ preventScroll: true });
    }
  }
  function open() {
    render();
    if (!dialog.open) {
      document.querySelectorAll('dialog[open]').forEach(node => node.close());
      dialog.showModal();
    }
    dialog.focus({ preventScroll: true });
  }
  const opener = document.getElementById('council-open');
  opener?.addEventListener('click', open);
  closeButton.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => { if (!dialog.open) { editId = null; form.hidden = true; errorMessage.hidden = true; hideInfluenceEditor({ focus: false }); } });
  add.addEventListener('click', () => edit());
  cancel.addEventListener('click', () => { form.hidden = true; editId = null; add.focus(); });
  kind.addEventListener('change', () => refreshSelectors(ctx.getData()));
  personSelect.addEventListener('change', () => refreshSelectors(ctx.getData()));
  form.addEventListener('submit', saveMember);
  form.addEventListener('input', clearMemberError);
  history.addEventListener('change', render);
  partyFilter.addEventListener('change', render);
  kindFilter.addEventListener('change', render);
  influenceEdit.addEventListener('click', toggleInfluenceEditor);
  influenceCancel.addEventListener('click', () => hideInfluenceEditor());
  influenceForm.addEventListener('submit', saveInfluence);
  royalistPoints.addEventListener('input', clearInfluenceError);
  internationalistPoints.addEventListener('input', clearInfluenceError);
  personPartyInfluence.addEventListener('input', () => touchedPersonInfluence.add('party'));
  personKingdomInfluence.addEventListener('input', () => touchedPersonInfluence.add('kingdom'));
  window.addEventListener('gilneas-data-changed', () => { if (dialog.open) render(); });
  window.addEventListener('gilneas-edit-mode-changed', event => {
    if (event.detail?.enabled === false) {
      editId = null; form.reset(); form.hidden = true; touchedPersonInfluence.clear(); clearMemberError();
      influenceForm.reset(); hideInfluenceEditor({ focus: false });
    }
    render();
  });
  return { open, render };
}
