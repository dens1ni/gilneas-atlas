# Жизненный статус гилнеасской знати: ранний срез

После Второй войны, до выхода Гилнеаса из Альянса Лордерона и до начала возведения Стены Седогрива; ранний человеческий Гилнеас.

**Результат:** 6 живы, 1 мертв, 10 неизвестны; проверены все 17 исходных ID, по одной записи на каждого.

Предложение для родительского агента: `lifeStatus = alive | dead | unknown`; теги — «Жив» (зеленый), «Мертв» (красный), «Неизвестно» (серый). Это исследование не меняет модель, UI, партии, должности, семью, владения или публикации.

Порог доказательства: ранний эпизод/жизненная дата либо явная последовательность событий. Поздний взрослый NPC без рождения/ранней сцены не считается автоматически живым; поздняя смерть не переносится назад. `basis=chronological_inference` отмечает вывод, а не указанную источником календарную дату.

| Исходный ID · имя | Тег для среза | Основание |
|---|---|---|
| `noble-genn` · Генн Седогрив | **Жив · зеленый** | Лично присутствует на послевоенной встрече королей; стена еще обсуждается.[1][2] |
| `noble-darius` · Дариус Краули | **Жив · зеленый** | Живой участник раннего совета; позднее проклятие не меняет ранний статус.[3][2] |
| `noble-godfrey` · Винсент Годфри | **Жив · зеленый** | Лично обсуждает будущую стену после Второй войны; самоубийство позднее.[4] |
| `noble-ashbury` · Барон Эшбери | **Жив · зеленый** | Вырос с Генном и жив до войны; погибает лишь в позднем кризисе.[2][5] |
| `noble-marley` · Лорд Марли | **Жив · зеленый** | Назван лордом текущего домена при планировании; позднее жив в сценах охот.[2][6] |
| `noble-archibald` · Арчибальд Седогрив | **Мертв · красный** | Смерть → воцарение Генна → Генн уже король до Второй войны.[1][4][7] |
| `noble-ashbury-first` · Лорд Эшбери I | **Неизвестно · серый** | Помогал Арчибальду; когда умер, не установлено. «Предшественник» ≠ «мертв».[8][2] |
| `noble-walden` · Лорд Уолден | **Неизвестно · серый** | Человеком и погибшим показан позднее; жизнь до выхода из Альянса не датирована.[9] |
| `noble-hewell` · Лорд Хьювелл | **Неизвестно · серый** | Жив в позднем стартовом сюжете; ранней жизненной даты нет.[10] |
| `noble-silverlaine` · Барон Сребролен | **Неизвестно · серый** | Гибель — Третья война; надежная жизнь до выхода из Альянса не установлена.[11][23][24] |
| `noble-longshore` · Барон Дольноберег | **Неизвестно · серый** | Прежнее баронство и жизнь за закрытой стеной есть, датировки до строительства нет.[13][14][21] |
| `noble-candren` · Лорд Кандрен | **Неизвестно · серый** | Поздний живой интендант; рождения или ранней сцены не найдено.[15] |
| `noble-isiden` · Исиден Перенольд | **Жив · зеленый** | Живым бежит в Гилнеас и ищет поддержки в послевоенном споре об Альтераке.[16] |
| `noble-tulvan` · Лорд Джеффри Тулван | **Неизвестно · серый** | Живым показан только поздний боец; ранняя жизнь не установлена.[17] |
| `noble-harford` · Лорд Харфорд | **Неизвестно · серый** | Плен у Аругала и казнь поздние; рождения до раннего среза не установлено.[18] |
| `noble-morrison` · Лорд-мэр Моррисон | **Неизвестно · серый** | Жизнь и гибель засвидетельствованы поздно; ранней даты нет.[19][21] |
| `noble-aderic` · Адерик | **Неизвестно · серый** | Поздняя гробница доказана; ранний пир не назван поминальным. Дата смерти открыта.[20][2][22] |

## Спорные хронологические границы

**Арчибальд:** смерть прямо предшествует воцарению Генна; Генн уже король до Второй войны. Поэтому «Мертв» доказан без выдуманного года.[1][4]

**Эшбери I:** сведения о помощи Арчибальду есть, события смерти нет. Инфобокс `Deceased` и прошлое поколение не устанавливают смерть до среза.[8][2]

**Адерик:** ранний пир и позднее погребение не образуют доказательство ранней смерти; в каталоге «long-dead king» находится в спекулятивном разделе. До брака Генна гробница не засвидетельствована.[2][20][21]

**Сребролен:** игровой пересказ прямо относит нападение Аругала к Третьей войне; статья крепости также связывает гибель с воргенами и нашествием Плети.[23][12] Обзор Engadget допускает более раннее владение, но смешивает мятеж и закрытие стены и называет ряд своих связей предположениями; этот альтернативный ранний вывод оставлен в `uncertainties`, не принят за каноническую живую сцену.[24]

**Исиден:** живое бегство/покровительство засвидетельствованы в послевоенной фазе; дальнейшая неизвестность не отменяет этого ограниченного раннего статуса.[16]

## Проверка и сохранение

Числа ссылок в этом MD назначены task-local citation-ledger, а не атласом. Точные числовые и строковые atlas source IDs сохранены в JSON; `newSources` содержит лишь новые `noble-life-source-N`. URL реально прочитанной страницы, canonical URL, автор/атрибуция, дословные цитаты и SHA-256 evidence находятся в ledger.

Все цитаты проверяются как буквальные подстроки сохраненного текста. Итоговый JSON содержит только исходные 17 человек; расширенный семейный переписной реестр остается отдельной задачей родителя.

403 на повторной загрузке Patriarch’s Blessing и на `action=render` сохранены в журнале; архивная лестница дала `recovered=false`, затем прочитано атрибутированное живое зеркало Warcraft Wiki. Ранние смерти не подменены текущими статусами зеркала.

Проверка исходных hashes и ограничения записи приведены в `noble-life-status-ledger.json`. Сторонние параллельные изменения shared worktree отмечены отдельно от неизмененных atlas-data/доказательств.

## Sources

[1] https://wowpedia.fandom.com/wiki/Genn_Greymane — Genn Greymane
[2] https://worldofwarcraft.blizzard.com/en-us/media/short-story/genn-greymane-lord-of-his-pack — Genn Greymane: Lord of His Pack - Media Gallery - World of Warcraft
[3] https://wowpedia.fandom.com/wiki/Darius_Crowley — Darius Crowley
[4] https://wowpedia.fandom.com/wiki/Lord_Vincent_Godfrey — Lord Vincent Godfrey
[5] https://wowpedia.fandom.com/wiki/Baron_Ashbury — Baron Ashbury
[6] https://wowpedia.fandom.com/wiki/Lord_Marley — Lord Marley
[7] https://wowpedia.fandom.com/wiki/Archibald_Greymane — Archibald Greymane
[8] https://wowpedia.fandom.com/wiki/Lord_Ashbury_the_1st?action=render — References
[9] https://wowpedia.fandom.com/wiki/Lord_Walden — Lord Walden
[10] https://wowpedia.fandom.com/wiki/Lord_Hewell — Lord Hewell
[11] https://wowpedia.fandom.com/wiki/Baron_Silverlaine — Baron Silverlaine
[12] https://wowpedia.fandom.com/wiki/Shadowfang_Keep — Shadowfang Keep
[13] https://wowpedia.fandom.com/wiki/Baron_Longshore — Baron Longshore
[14] https://wowpedia.fandom.com/wiki/The_Baron%27s_Demands — The Baron's Demands
[15] https://wowpedia.fandom.com/wiki/Lord_Candren — Lord Candren
[16] https://wowpedia.fandom.com/wiki/Isiden_Perenolde — Isiden Perenolde
[17] https://wowpedia.fandom.com/wiki/Lord_Geoffery_Tulvan — Lord Geoffery Tulvan
[18] https://wowpedia.fandom.com/wiki/Lord_Harford — Lord Harford
[19] https://wowpedia.fandom.com/wiki/Lord_Mayor_Morrison — Lord Mayor Morrison
[20] https://wowpedia.fandom.com/wiki/Aderic — Aderic
[21] https://wowpedia.fandom.com/wiki/Nobles_of_Gilneas — Nobles of Gilneas
[22] https://warcraft.wiki.gg/wiki/Patriarch%27s_Blessing — Patriarch's Blessing - Warcraft Wiki - Your wiki guide to the World of Warcraft
[23] https://wowpedia.fandom.com/wiki/Innkeeper — Innkeeper
[24] https://www.engadget.com/2010-12-15-know-your-lore-shadowfang-keep.html — Know Your Lore: Shadowfang Keep
