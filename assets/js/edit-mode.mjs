/** Presentation state only: never part of an atlas snapshot or saved draft. */
let editingRevision = 0;

export function isEditingEnabled() {
  return document.body.classList.contains('edit-mode');
}

/** A pending write belongs to the opt-in session in which it started. */
export function getEditingRevision() {
  return editingRevision;
}

export function initEditMode({ onChange } = {}) {
  const checkbox = document.getElementById('editing-enabled');
  const status = document.getElementById('editing-mode-status');
  if (!checkbox || !status) throw new Error('Не найдены настройки режима редактирования');
  function setEnabled(value) {
    const enabled = value === true;
    const changed = enabled !== isEditingEnabled();
    document.body.classList.toggle('edit-mode', enabled);
    checkbox.checked = enabled;
    checkbox.defaultChecked = false;
    checkbox.indeterminate = false;
    status.textContent = enabled ? 'Редактирование включено. Изменения сохраняются в этом браузере.' :
      'Режим просмотра. Изменение записей выключено.';
    if (changed) {
      editingRevision += 1;
      onChange?.(enabled);
      window.dispatchEvent(new CustomEvent('gilneas-edit-mode-changed', { detail: { enabled } }));
    }
  }
  checkbox.addEventListener('change', () => setEnabled(checkbox.checked));
  // Native restoration may retain checkbox state; a new page starts read-only.
  window.addEventListener('pageshow', () => setEnabled(false));
  setEnabled(false);
  return { isEnabled: isEditingEnabled, setEnabled, getRevision: getEditingRevision };
}
