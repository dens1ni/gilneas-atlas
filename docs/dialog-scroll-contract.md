# Хроника и справка: область прокрутки

- `#chronicle` и `#help` сохраняют свои существующие заголовки, действия закрытия и `.dialog-content`; не создаётся второй вложенный wrapper.
- Внешний dialog имеет `overflow:hidden`, `height:fit-content` и реальный viewport cap. Header не прокручивается и не содержит вертикальную полосу; только shrinkable `.dialog-content` имеет `overflow-y:auto` и native scrollbar.
- Все вкладки хроники, поиск конкретной персоны/источника, справка и нижние записи остаются достижимы. `chronicle.open(tab,id)` прокручивает content-body, не прежний dialog.
- В справке временно оставлен только раздел «Управление картой»: жесты, выбор меток, поиск и горячие клавиши. Остальные разделы удалены из scroll-body; шапка и закрытие сохранены, последний раздел не оставляет лишнюю линию.
- CSS ограничен этими двумя reading dialogs; редактор, Совет, летопись стены и досье сохраняют свои layouts.
- Проверено native wheel, конечное положение scrollTop, неизменный header, hit-test/button close, все три reading вкладки и справка на desktop/390 portrait/844 landscape/320 portrait. Автоматические screenshots не доказывают полосу на macOS (overlay scrollbar может быть невидим); наличие native track подтверждается реальным scroll-container geometry и input.
