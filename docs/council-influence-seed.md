# Королевский совет: стартовое влияние — предложение, не запись канона

**Статус:** только ревью; production не применён. Все баллы имеют `basis: "scenario"` и авторизованы пользователем как игровой старт. Источники удостоверяют личности, роли и объекты, но **ни один источник не сообщает эти числовые рейтинги**.

Срез из текущего Council: **После Второй войны, до выхода Гилнеаса из Альянса и до возведения Стены Седогрива.**

Текущий состав содержит 24 строки: 7 домов и 17 людей; 14 людей активны, 3 исторические записи неактивны. Среди активных: 3 роялиста, 1 интернационалист и 10 нейтралов. Сохранён исходный порядок `royalCouncil.members`, отфильтрованный только по `kind === "person"`; все 17 `memberId/refId` уникальны.

Прочитаны текущий `assets/data/atlas.json` (Council, nobles, factions/rulers, locations, sources и сценарные территории), `assets/js/noble-profile.mjs`, его функции из `model.mjs`, существующие `docs/court-politics-research.json/.md`, ledger и связанные архивные выдержки. Нового веб-поиска нет. Изменены только два новых файла seed в `docs/`.

## Что означает шкала

- `kingdom` — сценарная политическая значимость в Гилнеасе, максимум 100 на человека; не процент земель, населения, богатства или голосов.
- `party` — значимость внутри **уже назначенной** партии, также максимум 100. Для нейтралов 0: это отсутствие партии, не утверждение о нулевой ценности будущего союзника.
- `active:false` имеет 0/0; наследие предков не превращается в дополнительный активный голос.
- Исторические и недатированные потенциальные союзники не получают ранние должности автоматически. Три подтверждённых ранних советника — Дариус, Годфри и барон Эшбери.[3][4][7]

## Прозрачные игровые веса

Это открытая калибровка сценария, **не формула истинного влияния и не вывод канонических чисел**. Размер учитывается качественно: столица, ополчение, крепость и два северных узла важнее малого хозяйства. Ни население, ни кадастровая площадь не известны; реконструированные контуры карты не измеряют канонический домен.

| Компонент `kingdom` | Вес | Ограничение |
|---|---:|---|
| Активный сценарный резерв | 5 | Только доступность текущей активной записи |
| Суверен | 35 | Генн; вместо бонуса главы дома |
| Явный глава дома | 10 | Непустое точное `faction.ruler === noble.name` |
| Подтверждённый ранний совет | 20 | Только три проверенных человека |
| Командование постоянным ополчением | 30 | Годфри; должность, не владение крепостью |
| Широкое личное влияние | 15 | Дариус и Годфри; качественная ранняя опора |
| Доверенный придворный друг | 20 | Барон Эшбери |
| Общекоролевский охват | 20 | Генн; не сумма вассалов |
| Упомянутый, но не локализованный пограничный домен | 15 | Марли; не новые IDs или размер земли |
| Послевоенный гость с королевской поддержкой | 15 | Исиден; не имущество или должность |
| Недатированный потенциальный союзник | 3 | Одинаковый малый резерв, без поздних служебных бонусов |
| Столица | 40 | `gilneas-city`, без повторного сложения кварталов |
| Крепость | 30 → 25 | `shadowfang`: хозяин назван, дата до стены неизвестна |
| Северный городок | 15 каждый | `pyrewood`, `ambermill` |
| Малое поместье/хозяйство | 4 → 2 | Недатированные `greymane-manor`, `crowley-orchard`, `crowley-stable-grounds` |

Для активных людей суммируются только перечисленные ролевые веса и уникальные непосредственно оцениваемые активы; результат ограничивается 0…100. Показатель партии: `kingdom + 10` для лидера, `kingdom + 5` для Годфри как участника планирования, `kingdom + 5` для сценарной придворной ориентации Эшбери, затем то же ограничение. Нейтралы и неактивные имеют `party=0`.

Ранний рассказ прямо сопоставляет широкое влияние Краули с Годфри и отдельно называет командование Годфри постоянным ополчением.[1] Это оправдывает близкую высокую категорию, **не доказывает 84, 80 или их разницу**.

Столица подтверждена как столица, а не набор частных квартальных титулов.[31]

Владение Краули двумя северными поселениями засвидетельствовано прямо.[2][4]

Янтарная мельница известна как сравнительно небольшой лесозаготовительный узел, а не крупная столица.[35]

Для поместья Генна, сада и конюшен Краули текущая домовая принадлежность допускает только осторожный сценарный вес: дата до стены и пустой личный owner не исправляются.[32][33][34]

## Полные 17 записей — стабильный порядок

| № | Точный `memberId` | Точный `refId` · имя | Текущая партия | Активен | `party` | `kingdom` |
|---:|---|---|---|---|---:|---:|
| 1 | `council-noble-genn` | `noble-genn` · Генн Седогрив | `royalists` | Да | 100 | 100 |
| 2 | `council-noble-darius` | `noble-darius` · Дариус Краули | `internationalists` | Да | 94 | 84 |
| 3 | `council-noble-godfrey` | `noble-godfrey` · Винсент Годфри | `royalists` | Да | 85 | 80 |
| 4 | `council-noble-ashbury` | `noble-ashbury` · Барон Эшбери | `royalists` | Да | 60 | 55 |
| 5 | `council-noble-marley` | `noble-marley` · Лорд Марли | `neutral` | Да | 0 | 30 |
| 6 | `council-noble-archibald` | `noble-archibald` · Арчибальд Седогрив | `neutral` | Нет | 0 | 0 |
| 7 | `council-noble-ashbury-first` | `noble-ashbury-first` · Лорд Эшбери I | `neutral` | Нет | 0 | 0 |
| 8 | `council-noble-walden` | `noble-walden` · Лорд Уолден | `neutral` | Да | 0 | 8 |
| 9 | `council-noble-hewell` | `noble-hewell` · Лорд Хьювелл | `neutral` | Да | 0 | 8 |
| 10 | `council-noble-silverlaine` | `noble-silverlaine` · Барон Сребролен | `neutral` | Да | 0 | 40 |
| 11 | `council-noble-longshore` | `noble-longshore` · Барон Дольноберег | `neutral` | Да | 0 | 8 |
| 12 | `council-noble-candren` | `noble-candren` · Лорд Кандрен | `neutral` | Да | 0 | 8 |
| 13 | `council-noble-isiden` | `noble-isiden` · Исиден Перенольд | `neutral` | Да | 0 | 20 |
| 14 | `council-noble-tulvan` | `noble-tulvan` · Лорд Джеффри Тулван | `neutral` | Да | 0 | 8 |
| 15 | `council-noble-harford` | `noble-harford` · Лорд Харфорд | `neutral` | Да | 0 | 8 |
| 16 | `council-noble-morrison` | `noble-morrison` · Лорд-мэр Моррисон | `neutral` | Да | 0 | 8 |
| 17 | `council-noble-aderic` | `noble-aderic` · Адерик | `neutral` | Нет | 0 | 0 |

## Основания, точные владельческие совпадения и пробелы

`people[].holdings` — полный список точных ID из **реально исполненного** `deriveNobleProfile` текущего снимка. Он включает личную, домовую и вассальную **сферу контроля**, не только частную собственность. В `method.personAudit[].explicitKnownHoldings` отдельно перечислены буквальные непустые совпадения `location.owner` с именем. Это честная инвентаризация данных, не подтверждение нового частного титула или даты.

Генн видит 30 локаций, Дариус — 5, Сребролен — 1; остальные 14 людей имеют пустой список. В текущих 39 локациях нет вложенных объектов. Оценены ровно 7 уникальных локаций: 2 у Генна, 4 у Дариуса, 1 у Сребролена. У косвенно видимых дочерних активов вес 0.

### 1. Генн Седогрив — `council-noble-genn` / `noble-genn`

**Сценарий:** `100/100` (`party/kingdom`).

Король и глава роялистского направления; faction.ruler точно совпадает для gilneas и greymane.[2][3][5]

Столица — главная политическая опора.[2][3][5]

Общекоролевский охват не превращает владения Краули и Сребролена в личную собственность Генна.[2][3][5]

Поместье включено только по действующей домовой принадлежности с осторожным весом.[2][3][5]

Сырой сценарный результат 102 ограничен до 100; кварталы столицы и вассальные активы повторно не прибавлены.[2][3][5]

**explicitKnownHoldings:** `gilneas-city`. **Явная ruler-власть:** `gilneas`, `greymane`. **Оцениваемые активы:** `gilneas-city` +40, `greymane-manor` +2.

**Полный holdings:** `gilneas-city`, `greymane-manor`, `cathedral-quarter`, `lights-dawn-cathedral`, `greymane-court`, `merchant-square`, `military-district`, `stoneward-prison`, `keel-harbor`, `duskhaven`, `crowley-orchard`, `crowley-stable-grounds`, `hayward-fishery`, `hammond-farmstead`, `allen-farmstead`, `emberstone-village`, `emberstone-mine`, `stormglen`, `blackwald`, `taldoren`, `bradshaw-mill`, `tempests-reach`, `aderics-repose`, `northgate-woods`, `northern-headlands`, `the-headlands`, `pyrewood`, `shadowfang`, `ambermill`, `galewatch-lighthouse`.

**Точные atlas sourceIds:** `48`, `45`, `46`, `47`, `3`, `1`, `2`, `9`, `10`, `4`, `5`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Буквальный location.owner для gilneas-city описывает текущую запись атласа; источник о столице сам по себе не доказывает частный земельный титул на город.[2][3][5]

greymane-manor.owner пуст: позднее семейное владение известно, но дата здания до стены не доказана.[2][3][5]

Остальные пустые owners не заполняются.[2][3][5]

Проект стены на 10/100 — авторский этап, не датированная реальная политическая шкала.[2][3][5]

Суверен не становится собственным советником.[2][3][5]

Дополнительная архивная опора: [31][32][18].

### 2. Дариус Краули — `council-noble-darius` / `noble-darius`

**Сценарий:** `94/84` (`party/kingdom`).

Глава crowley, подтверждённый ранний советник и лидер интернационалистского направления.[1][2][4]

Пирвуд и Янтарная мельница прямо записаны за Дариусом и названы в ранней ретроспективе; два северных узла важнее малых хозяйств.[1][2][4]

Харизма и широкое влияние засвидетельствованы.[1][2][4]

Сад и конюшни имеют пустой owner и лишь осторожный сценарный вес через его дом.[1][2][4]

shadowfang виден в вассальной сфере, но его активный вес целиком оставлен Сребролену.[1][2][4]

**explicitKnownHoldings:** `pyrewood`, `ambermill`. **Явная ruler-власть:** `crowley`. **Оцениваемые активы:** `crowley-orchard` +2, `crowley-stable-grounds` +2, `pyrewood` +15, `ambermill` +15.

**Полный holdings:** `crowley-orchard`, `crowley-stable-grounds`, `pyrewood`, `shadowfang`, `ambermill`.

**Точные atlas sourceIds:** `48`, `32`, `46`, `3`, `14`, `15`, `4`, `2`, `33`, `40`, `35`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Граница северного домена и население городков не измерены; сценарные контуры не канонический кадастр.[1][2][4]

Янтарная мельница не превращается в крупную столицу из-за слова town.[1][2][4]

Сад и конюшни не датированы до стены и не дают Дариусу доказанный личный довоенный титул на каждое здание.[1][2][4]

silverlaine.parent === crowley сохранён как авторская конфигурация; это не доказательство единого партийного голоса барона.[1][2][4]

Сопоставление раннего влияния Краули и Годфри качественное.[1][2][4]

Баллы 84/80 не числа из рассказа; поздние мятеж, заключение и воргенская армия не учитываются.[1][2][4]

Дополнительная архивная опора: [33][34][35].

### 3. Винсент Годфри — `council-noble-godfrey` / `noble-godfrey`

**Сценарий:** `85/80` (`party/kingdom`).

Глава godfrey и подтверждённый ранний советник.[1][2][6]

Главный вес даёт прямо засвидетельствованное командование постоянным ополчением, а не выдуманный замок.[1][2][6]

Ранняя сцена признаёт его широкое влияние, сопоставимое с Краули; при обсуждении стены он предлагает созвать совет.[1][2][6]

Известный по тексту собственный realm остаётся без канонического location ID, поэтому holdings пуст и нет земельного бонуса.[1][2][6]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** `godfrey`. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `46`, `48`, `49`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

В данных нет ни одного location.owner === «Винсент Годфри» и ни одной локации его домовой ветви.[1][2][6]

Размер ополчения и точные границы его realm не установлены.[1][2][6]

Нельзя назначать ему shadowfang, keel-harbor, northgate-woods, northern-headlands или emberstone-village/emberstone-mine: поздний захват, соседство и военная должность не право собственности.[1][2][6]

Бонус должности не утверждает, что этот же командный пост непрерывно сохранялся каждую дату между ранними сценами; отдельного календарного протокола нет.[1][2][6]

Он сначала опасается разрыва торговли; высокий рейтинг не означает безусловной ранней вражды ко всему Альянсу или переноса будущей измены.[1][2][6]

### 4. Барон Эшбери — `council-noble-ashbury` / `noble-ashbury`

**Сценарий:** `60/55` (`party/kingdom`).

Глава ashbury, подтверждённый ранний советник и доверенный друг Генна.[1][3][7]

Средний общекоролевский вес основан на придворной связи и семейной верности, не на неназванных замках.[1][3][7]

В текущем Council он роялист с partyBasis=scenario; отдельный голос за стену не доказан.[1][3][7]

Именных владений в атласе нет.[1][3][7]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** `ashbury`. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `46`, `45`, `50`, `51`, `3`, `54`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Поддержка малого союзного войска не равна голосу за стену или отказу от торговли.[1][3][7]

Довоенный частный домен не локализован.[1][3][7]

Позднее eastern lord и присутствие в tempests-reach не дают владения поселением.[1][3][7]

Не приписывается автоматическое наследование того же титула от Лорда Эшбери I; отец не получает повторный активный рейтинг.[1][3][7]

### 5. Лорд Марли — `council-noble-marley` / `noble-marley`

**Сценарий:** `0/30` (`party/kingdom`).

Точное ruler-соответствие marley разрешает только существующую домовую власть.[2][5][8]

Приграничный домен прямо упомянут при планировании стены, но ни одной его локации или личного owner в атласе нет.[2][5][8]

Ограниченный рейтинг 30 отражает этот качественный контекст, не площадь, вымышленный замок или раннее кресло советника.[2][5][8]

Текущая партия neutral: party=0, в запас партий не входит.[2][5][8]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** `marley`. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `48`, `3`, `court-source-8`, `52`, `46`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Домен существует в тексте, но размер, точный участок и канонические IDs неизвестны; holdings=[] не означает, что Марли вообще не имел земли.[2][5][8]

Нельзя назначать Марли ambermill, deep-elem-mine или соседние северные локации по вики-гипотезе.[2][5][8]

noble.title/socialStatus/description и faction.description называют советника, но без ранней даты.[2][5][8]

Текущий Council и исследование строже: advisor=false; неподтверждённая должность не получает бонус.[2][5][8]

### 6. Арчибальд Седогрив — `council-noble-archibald` / `noble-archibald`

**Сценарий:** `0/0` (`party/kingdom`).

Исторический предшественник, active=false.[3][16][29]

Наследие Арчибальда объясняет традицию Генна, но не даёт действующего участника, владений или второй суммы за корону.[3][16][29]

Оба сценарных показателя равны нулю.[3][16][29]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `45`, `53`, `court-source-29`, `46`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Дата смерти не назначается.[3][16][29]

Прошлая монаршая власть не переносится на current faction.ruler и нынешний партийный запас.[3][16][29]

### 7. Лорд Эшбери I — `council-noble-ashbury-first` / `noble-ashbury-first`

**Сценарий:** `0/0` (`party/kingdom`).

Представитель двора Арчибальда, отец барона; active=false.[5][19][30]

Историческая служба не является ранним назначением при Генне.[5][19][30]

0/0, без повторного влияния через сына или дом ashbury.[5][19][30]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `3`, `54`, `court-source-30`, `46`, `50`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Жизнь и служба при Генне после Второй войны не установлены; дата смерти и автоматическое наследование одного баронского титула не выводятся.[5][19][30]

### 8. Лорд Уолден — `council-noble-walden` / `noble-walden`

**Сценарий:** `0/8` (`party/kingdom`).

Низкий сценарный резерв недатированного потенциального союзника.[5][9][28]

walden.ruler — пустая строка, поэтому house=walden не делает Уолдена главой дома и не открывает чужие владения.[5][9][28]

Поздние сведения о семье и доме у берега не задают его ранний личный актив.[5][9][28]

Нейтрал: party=0.[5][9][28]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `3`, `55`, `60`, `51`, `56`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Ранние титул, придворная служба, партия и собственник дома не установлены.[5][9][28]

Поздний Walden house, помощь Годфри, измена и пребывание в tempests-reach не дают ранней должности, владения или роялистского бонуса.[5][9][28]

### 9. Лорд Хьювелл — `council-noble-hewell` / `noble-hewell`

**Сценарий:** `0/8` (`party/kingdom`).

Недатированный потенциальный союзник без домовой власти и личного location.owner.[10]

Лишь малый сценарный резерв; поздняя верность Генну не используется как ранний партийный или советнический бонус.[10]

Нейтрал: party=0, holdings=[].[10]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `57`, `58`, `3`, `26`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Ранний приезд, должность и владение не подтверждены.[10]

Поздняя связь с tempests-reach или manor не доказывает собственность до стены.[10]

Имя и noble-hewell сохранены буквально.[10]

### 10. Барон Сребролен — `council-noble-silverlaine` / `noble-silverlaine`

**Сценарий:** `0/40` (`party/kingdom`).

Локальное влияние названного хозяина каменной крепости.[5][11][12]

shadowfang.owner буквально совпадает с именем барона, silverlaine.ruler также совпадает.[5][11][12]

Крепость весит больше малого здания, но её точная датировка до стены неизвестна: вес уменьшен с 30 до 25.[5][11][12]

Рейтинг 40 ниже подтверждённых ранних государственных ролей; партия нейтральная, без автоматического голоса Краули.[5][11][12]

**explicitKnownHoldings:** `shadowfang`. **Явная ruler-власть:** `silverlaine`. **Оцениваемые активы:** `shadowfang` +25.

**Полный holdings:** `shadowfang`.

**Точные atlas sourceIds:** `3`, `59`, `60`, `33`, `34`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Поздняя ретроспектива подтверждает хозяина до падения крепости, не точный год до стены; location.provenance.ownerStatus=unknown сохранён.[5][11][12]

Вассальная связь с Краули авторская и не создаёт личного голоса против стены.[5][11][12]

Пирвуд и Янтарная мельница не передаются барону.[5][11][12]

Замковый актив учитывается один раз у барона; видимость у Дариуса и Генна в deriveNobleProfile не даёт им повторных земельных баллов.[5][11][12]

Дополнительная архивная опора: [28].

### 11. Барон Дольноберег — `council-noble-longshore` / `noble-longshore`

**Сценарий:** `0/8` (`party/kingdom`).

Малый сценарный резерв потенциального союзника.[5][13][14]

Личное позднее свидетельство о настоящем прежнем баронстве не датирует раннюю власть и не локализует участок.[5][13][14]

Ни дом, ни усадьба, ни корабль не добавлены.[5][13][14]

Нейтрал: party=0.[5][13][14]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `3`, `61`, `62`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Дата титула, довоенная земля и раннее участие неизвестны.[5][13][14]

Поздний Heedless, пиратство и отсечение стеной не дают активов или голоса в текущем срезе.[5][13][14]

### 12. Лорд Кандрен — `council-noble-candren` / `noble-candren`

**Сценарий:** `0/8` (`party/kingdom`).

Малый резерв недатированного потенциального союзника.[5][17]

Поздняя интендантская должность не считается ранним административным ресурсом.[5][17]

Земли семьи в исследовании прямо не локализованы; власть и holdings не придуманы.[5][17]

Нейтрал: party=0.[5][17]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `3`, `63`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Дата титула, домен и назначение при Генне после Второй войны неизвестны.[5][17]

Снабжение гилнеасцев в позднем Дарнасе не раннее кресло советника.[5][17]

### 13. Исиден Перенольд — `council-noble-isiden` / `noble-isiden`

**Сценарий:** `0/20` (`party/kingdom`).

Послевоенный альтеракский претендент и гость с поддержкой Генна.[3][15]

Это даёт ограниченную дипломатическую значимость 20, но не гилнеасский суверенитет, имущество или должность.[3][15]

Притязание на Альтерак не владеемый объект.[3][15]

Нейтрал: party=0.[3][15]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `45`, `64`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Поддержка направлена от Генна к Исидену, обратная клятва или партийная принадлежность не доказана.[3][15]

Точная длительность пребывания, усадьба и дата участия на 10/100 неизвестны.[3][15]

### 14. Лорд Джеффри Тулван — `council-noble-tulvan` / `noble-tulvan`

**Сценарий:** `0/8` (`party/kingdom`).

Малый резерв недатированной ранней версии личности из реестра.[5][20][24]

Ни графский домен, ни замок, ни ранняя военная должность не выведены из поздней биографии или прозвища.[5][20][24]

Нейтрал: party=0, holdings=[].[5][20][24]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `3`, `court-source-20`, `court-source-24`, `65`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Дата титула и земли семьи неизвестны.[5][20][24]

Арена, сила, форма воргена и «Earl of Evisceration» не ранние ресурсы и не основание назначения советником.[5][20][24]

### 15. Лорд Харфорд — `council-noble-harford` / `noble-harford`

**Сценарий:** `0/8` (`party/kingdom`).

Малый резерв потенциального союзника без установленного раннего домена.[5][21][25]

Прямая поздняя реплика о гилнеасской родине не доказывает вассалитет Краули, владение крепостью или сторону в споре.[5][21][25]

Нейтрал: party=0.[5][21][25]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `3`, `court-source-21`, `court-source-25`, `66`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Ранние титул, служба и участок неизвестны; likely/географическое соседство не устанавливают власть.[5][21][25]

Служба Аругалу, плен и Серебряный Рассвет относятся к позднему контексту и не дают бонуса.[5][21][25]

### 16. Лорд-мэр Моррисон — `council-noble-morrison` / `noble-morrison`

**Сценарий:** `0/8` (`party/kingdom`).

Малый сценарный резерв возможного представителя жителей.[5][22][26]

Муниципальный титул в позднем источнике не датирует раннее мэрство, не даёт частного Пирвуда или кресла королевского советника.[5][22][26]

Рейтинг не получает бонуса за город Дариуса.[5][22][26]

Нейтрал: party=0.[5][22][26]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `3`, `court-source-22`, `court-source-26`, `32`, `67`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Начало муниципальной службы и ранняя политическая сторона неизвестны.[5][22][26]

Владелец pyrewood в текущих данных — Дариус Краули; управление советом не личное владение и не доказанный вассальный договор.[5][22][26]

### 17. Адерик — `council-noble-aderic` / `noble-aderic`

**Сценарий:** `0/0` (`party/kingdom`).

Мемориальный патриарх, active=false.[5][23][27]

Ни королевский пир, ни захоронение в aderics-repose не образуют живого владельца или партийного ресурса.[5][23][27]

0/0; королевский титул и принадлежность к Седогривам не назначены.[5][23][27]

**explicitKnownHoldings:** ∅. **Явная ruler-власть:** ∅. **Оцениваемые активы:** нет.

**Полный holdings:** ∅.

**Точные atlas sourceIds:** `3`, `court-source-23`, `court-source-27`, `27`, `46`, `68`. Это IDs текущего `data.sources`, не `[n]` из отчёта.

**Неопределённость:**

Дата смерти, монарший титул и династическая связь не установлены.[5][23][27]

Имя мемориала не personal location.owner.[5][23][27]

## Разовые стартовые партийные запасы

| Запас | Единственные учитываемые люди | Python-сумма `kingdom` | Доля стартового запаса |
|---|---|---:|---:|
| `royalists` | `noble-genn`, `noble-godfrey`, `noble-ashbury` | 100 + 80 + 55 = **235** | 73.67% |
| `internationalists` | `noble-darius` | 84 = **84** | 26.33% |

Общий стартовый запас: **319**. В JSON: `partyPoints = {"royalists": 235, "internationalists": 84}`. Сумма вычислена Python по активным людям и их **текущей** партии, а не по домам, `party`-полоскам или числу владений.

Запас **без верхнего лимита 100**: показывать число без `/100` и доли от двух текущих партийных запасов. Королевское серебро / приглушённый teal — оформление, не свидетельство лора.

**Это однократный старт. Затем партийные запасы независимы.** Будущие явные игровые действия могут их менять или тратить; перерисовка, reload, изменение полоски человека, обновление источников или вербовка не пересчитывают, не пополняют и не списывают запас автоматически. Повторный seed при reload недопустим. При изменении обеих сумм доли вычисляются заново от запасов, но не от персонифицированных рейтингов.

Вычислительная проверка использует ту же явную фильтрацию:

```python
party_points = {
    party: sum(
        person["influence"]["kingdom"]
        for person in seed["people"]
        if member_by_id[person["memberId"]]["active"] is True
        and member_by_id[person["memberId"]]["party"] == party
    )
    for party in ("royalists", "internationalists")
}
```

### Защита от повторного счёта

- Семь домовых строк не рейтингуются и не суммируются. Предки 0/0, нейтралы исключены из обоих запасов.
- `shadowfang` получает вес только у Сребролена. Косвенная видимость этого ID у Дариуса и Генна не прибавляет вторую крепость.
- `gilneas-city` — единственный столичный актив; его кварталы, собор и тюрьма отдельно не умножают столицу и ополчение.
- Пирвуд и Янтарная мельница учитываются у Дариуса; муниципальный титул Моррисона и суверенитет Генна не дают второй личный городской актив.
- Общекоролевский охват Генна — отдельная качественная роль, а не сумма баллов вассалов. Нет наследственных дополнительных голосов детям или супругам.

## Честный аудит текущих данных

- **Марли:** legacy-поля `noble.title/socialStatus/description` и `faction.description` называют его советником, однако ранняя дата не найдена. Council сохраняет `advisor=false`; строгая политика не получает выдуманный ранний должностной бонус.[2][5][8]
- **Годфри:** командование прямо засвидетельствовано, а собственный realm упомянут без канонических IDs. Ноль mapped holdings не отрицает этот текст и не разрешает фантазийный keep.[1]
- **Уолден:** `faction.ruler` буквально пуст; домовая принадлежность не ruler. Поздняя семейная география и сотрудничество с Годфри не устанавливают ранний домен или пост.[5][9][28]
- **Сребролен:** owner записан буквально, но `ownerStatus=unknown` относится к раннему срезу. Владение до позднего падения известно; датировка до стены и вассальная цепь отдельно не доказаны.[5][11][28]
- **Факультативные союзники:** Council `active=true` не тождественен доказанной ранней службе; старые `historical_reference` и `displayInEarlyCourt=false` не переписываются. Их резерв — только сценарная доступность.[10][17][26]
- Точные canonical IDs и текущие sourceIds проверяются по атласу; локальные `[n]` взяты из существующего politics ledger. Для пяти коротких сохранённых цитат атласа добавлены task-local IDs 31…35, без нового web retrieval.

## Проверка границ записи

- Production-data SHA-256 до/после: `632c6623f4b16216fda80ff278de8b6670ee75fad8fd0bcc47fb767edc6ffaca`. `assets/data/atlas.json` не изменён; имена, owners, партии, rulers, карты/координаты и исходные 80 источников сохранены буквально.
- Проверены байты всех 10 существующих файлов `assets/maps/`; контрольный SHA-256 набора хэшей до/после: `26ae3a3cae2ce8ef5a26fef363d42f4ca8a0aa38b3afadc9fdf7dbb3b3f3947a`.
- Реально исполнен `deriveNobleProfile` для всех 17; сверены 17 точных пар ID, диапазоны, исходный порядок, все sourceIds, все literal owner/ruler-сопоставления и 7 уникальных оцениваемых активов. Перепроверены 66 цитатных связей существующего исследования по сохранённым текстам.
- Итоговые JSON/Markdown должны быть прочитаны обратно точным путём; отдельный валидатор повторно вычисляет баллы, запас и хэши после записи. Никаких production/data writes, коммитов и деплоя этим заданием не выполняется.
- Общий worktree уже содержит чужую параллельную работу; относительно стартового снимка замечены изменения UI: `assets/css/court-ui.css`, `assets/css/royal-council.css`, `assets/js/council-window.mjs`, `assets/js/draft-publication.mjs`, `assets/js/royal-council.mjs`. **Весь UI-bundle не объявляется неизменным**; проверка неизменности относится к данным атласа, картам и прочитанным исходным доказательствам. Эти файлы не записываются этим seed-аудитом.

## Сопоставление ссылок

`[n]` ниже — локальные citation identities, **не** значения `sourceIds`. Первые 30 сохранены из существующего politics ledger; соответствия взяты из `court-politics-research.json.sourceMap`. Дополнительные короткие выдержки взяты только из текущего `data.sources`.

| Локальная ссылка | Точный atlas sourceId |
|---|---|
| `[1]` | `46` |
| `[2]` | `48` |
| `[3]` | `45` |
| `[4]` | `32` |
| `[5]` | `3` |
| `[6]` | `49` |
| `[7]` | `50` |
| `[8]` | `court-source-8` |
| `[9]` | `55` |
| `[10]` | `57` |
| `[11]` | `59` |
| `[12]` | `33` |
| `[13]` | `61` |
| `[14]` | `62` |
| `[15]` | `64` |
| `[16]` | `53` |
| `[17]` | `63` |
| `[18]` | `47` |
| `[19]` | `54` |
| `[20]` | `court-source-20` |
| `[21]` | `court-source-21` |
| `[22]` | `court-source-22` |
| `[23]` | `court-source-23` |
| `[24]` | `court-source-24` |
| `[25]` | `court-source-25` |
| `[26]` | `court-source-26` |
| `[27]` | `court-source-27` |
| `[28]` | `60` |
| `[29]` | `court-source-29` |
| `[30]` | `court-source-30` |
| `[31]` | `1` |
| `[32]` | `5` |
| `[33]` | `14` |
| `[34]` | `15` |
| `[35]` | `35` |

## Sources

[1] https://worldofwarcraft.blizzard.com/en-us/media/short-story/genn-greymane-lord-of-his-pack — Genn Greymane: Lord of His Pack - Media Gallery - World of Warcraft
    > "“You want to wall off our entire nation? Close our borders and end trade with the rest of the Alliance? I… it is a rather large decision, would you not say?”"
    > "His name was Godfrey. Genn trusted his counsel but was always suspicious about his ambitions. Godfrey’s notion was not motivated by empathy as Crowley’s was. It was a smart political play that ensured notoriety for Godfrey, the commander of that standing militia."
    > "“It is a path that does have merit, my lord,” Baron Ashbury added. Ashbury was one of Genn’s most trusted friends. Genn had grown up with him; his father, Lord Ashbury the 1st, had helped Archibald build the nation up, and Archibald had always told Genn to trust in the Ashburys’ fidelity to the crown."
    > "“I had thought of this before as well. It is a fair direction. But… Crowley is powerful. He has much influence, as much as even you, Godfrey. He may not take this lightly.”"
    > "“Indeed it would, Godfrey. And, of course, it would make your realm the most strategically valuable, as it would become our buffer to the outside. You would have the realm nearest to the wall.”"
[2] https://worldofwarcraft.blizzard.com/ru-ru/media/short-story/genn-greymane-lord-of-his-pack — Генн Седогрив: Вожак Стаи - Галерея - World of Warcraft
    > "— Мы построим стену, идущую через горы, и земли Северных врат обеспечат нашу безопасность. Все правильно. Что же до лорда Краули… Дариусу придется смириться."
    > "— Но господин, другие народы стремятся к объединению, — настаивал Краули. — Если Троллебой, Перенольд и прочие примкнут к Альянсу, как можем мы оставаться в стороне и продолжать называть себя друзьями и соседями?"
    > "— Надо созвать совет дворянства, — сказал он, вставая из кресла. — Мы идем верным путем, мой повелитель, хотя, возможно, он полон подводных камней."
    > "— Судя по этим наброскам, вы планируете затронуть владения лорда Марли… Но взгляните и сюда — здесь начинается горная цепь, идеальное природное заграждение…"
[3] https://wowpedia.fandom.com/wiki/Genn_Greymane — Genn Greymane
    > "After the Second War, he was present at the meeting with other kings of the Alliance in Nethergarde Keep. Greymane complained about the expenses of the keep, though the newly crowned King of Stormwind Varian Wrynn pointed out that a price couldn't be put on something as essential as their safety."
    > "Accompanied by a group of nobles including Baron Ashbury, Lord Vincent Godfrey, and Lord Darius Crowley, the youngest and newest of the council of lords, Greymane listened to the plight of Anduin Lothar regarding the fall of Stormwind and the threat of the orcish Horde."
    > "After Archibald's death, Genn took the throne and led Gilneas much like his father had."
    > "He supported the claim of Lord Perenolde's nephew, Isiden, to Alterac's throne. A base in Alterac would give Gilneas access to resources the southern kingdom did not have, and the excuse to send its mighty ships across the Great Sea."
[4] https://wowpedia.fandom.com/wiki/Darius_Crowley — Darius Crowley
    > "Despite being young and new to the Gilnean council of Lords, his altruistic and charismatic qualities made him loved by the Gilnean people and earned him the respect and friendship of King Genn Greymane."
    > "A pro-Alliance figure, he dissented with King Genn Greymane's decision to separate his people with the Greymane Wall."
    > "He owned the towns of Pyrewood Village and Ambermill."
[5] https://wowpedia.fandom.com/wiki/Nobles_of_Gilneas — Nobles of Gilneas
    > "Councilor of King Genn Greymane."
    > "Councilor of King Archibald Greymane. Father of Baron Ashbury."
    > "Former councilor of King Genn Greymane, traitor alongside Ashbury and Godfrey."
    > "The Crowley family ruled over the lands that constituted both Pyrewood Village (and as a result, Shadowfang Keep) and Ambermill,[4] making Baron Silverlaine a vassal of theirs as a result."
    > "Captain of the pirate ship Heedless, and one of the Gilneans locked out of Gilneas by the Greymane Wall."
    > "The lands of the Tulvans and Candrens are entirely unknown with no allusions to any potential regions, though the Tulvans are stated to be 'earls'."
    > "Lord Harford was also noted as a servant of Arugal and from beyond the wall, meaning he was likely one of Crowley's vassals as well."
    > "Lord Mayor Morrison was also the mayor of Pyrewood, placing him implicitly under Crowley's service."
    > "Referred to as a "patriarch", and has the Royal Aderic Banquet named in his honor.[9] Possibly a long-dead king or nobleman."
    > "The Greymane family rules over all of Gilneas."
    > "This area of Gilneas has since sunk outside of the manor, but once held cottages for the Crowley[2] and the Walden families."
[6] https://wowpedia.fandom.com/wiki/Lord_Vincent_Godfrey — Lord Vincent Godfrey
    > "Genn warned that Darius might not take well to having his lands cut off, but Godfrey insisted that it was the best course of action for Gilneas."
[7] https://wowpedia.fandom.com/wiki/Baron_Ashbury — Baron Ashbury
    > "He was present in the Capital City to create the Alliance of Lordaeron and agreed with Lord Godfrey, to send only a token army."
[8] https://wowpedia.fandom.com/wiki/Lord_Marley — Lord Marley
    > "King Genn Greymane had originally planned to have the Greymane Wall cut through Marley's domain, but later decided to have it cut through Lord Darius Crowley's domain instead at the recommendation of Lord Godfrey."
[9] https://wowpedia.fandom.com/wiki/Lord_Walden — Lord Walden
    > "Lord Walden was a human nobleman from eastern Gilneas."
[10] https://wowpedia.fandom.com/wiki/Lord_Hewell — Lord Hewell
    > "Lord Hewell is a nobleman of Gilneas who can be found at Tempest's Reach during the worgen starting experience."
    > "Hewell refused to betray his king. Instead he remained by Greymane's side until Krennan Aranas sent an adventurer to help."
[11] https://wowpedia.fandom.com/wiki/Baron_Silverlaine — Baron Silverlaine
    > "Baron Silverlaine was master of the keep before it fell to Arugal's worgen."
[12] https://wowpedia.fandom.com/wiki/Shadowfang_Keep — Shadowfang Keep
    > "The lord of the castle was Baron Silverlaine and his forces were led by Commander Springvale, a paladin of the Silver Hand."
[13] https://wowpedia.fandom.com/wiki/Baron_Longshore — Baron Longshore
    > "Baron Longshore is the former captain of the Heedless, a ship in the pirate fleet of the Southsea Freebooters, and hails from Gilneas."
[14] https://wowpedia.fandom.com/wiki/The_Baron%27s_Demands — The Baron's Demands
    > "Oh, me word is good, friend. I used ta be a real Baron, ye know."
[15] https://wowpedia.fandom.com/wiki/Isiden_Perenolde — Isiden Perenolde
    > "When Alterac was placed under martial law by order of King Terenas, Isiden fled to Gilneas, where he hoped to rally support.[2] He was eventually backed by Genn Greymane, Gilneas' king, as the matter of the succession began to heat up."
    > "Nothing has been heard from Isiden since then and his status is unknown."
[16] https://wowpedia.fandom.com/wiki/Archibald_Greymane — Archibald Greymane
    > "Archibald Greymane was the king of Gilneas and the father of Genn Greymane. Under his rule, Gilneas prospered."
[17] https://wowpedia.fandom.com/wiki/Lord_Candren — Lord Candren
    > "Lord Candren is the quartermaster for Gilneas. He is found in Darnassus's Temple Gardens, near the flight master."
[18] https://wowpedia.fandom.com/wiki/Greymane_family — Greymane family - Wowpedia - Your wiki guide to the World of Warcraft
    > "is the ruling line"
[19] https://warcraft.wiki.gg/wiki/Lord_Ashbury_the_1st — Lord Ashbury the 1st - Warcraft Wiki - Your wiki guide to the World of Warcraft
    > "King Archibald always told his son Prince Genn to trust in the Ashburys’ fidelity to the crown because of the accomplishments of Lord Ashbury."
[20] https://warcraft.wiki.gg/wiki/Lord_Geoffery_Tulvan — Lord Geoffery Tulvan - Warcraft Wiki - Your wiki guide to the World of Warcraft
    > "Lord Geoffery Tulvan is a worgen located at the Crucible of Carnage in the Twilight Highlands."
[21] https://warcraft.wiki.gg/wiki/Lord_Harford — Lord Harford - Warcraft Wiki - Your wiki guide to the World of Warcraft
    > "Lord Harford is an Argent Dawn prisoner of the death knights in the Scarlet Enclave."
[22] https://warcraft.wiki.gg/wiki/Lord_Mayor_Morrison — Lord Mayor Morrison - Warcraft Wiki - Your wiki guide to the World of Warcraft
    > "Lord Mayor Morrison is a human and leader of the Pyrewood Council who appears in Pyrewood Village in Silverpine Forest during [15] Pyrewood Ambush."
[23] https://warcraft.wiki.gg/wiki/Aderic — Aderic - Warcraft Wiki - Your wiki guide to the World of Warcraft
    > "Aderic was a human who was a Gilnean patriarch. He is buried at Aderic's Repose at the top of the hill."
[24] https://wowpedia.fandom.com/wiki/Lord_Geoffery_Tulvan — Lord Geoffery Tulvan
    > "Lord Geoffery Tulvan is a worgen located at the Crucible of Carnage in the Twilight Highlands. He is one of the challengers and seeks to become the greatest warrior in the world."
[25] https://wowpedia.fandom.com/wiki/Lord_Harford — Lord Harford
    > "Remember Gilneas, our beloved home. This world is worth saving."
[26] https://wowpedia.fandom.com/wiki/Lord_Mayor_Morrison — Lord Mayor Morrison
    > "Lord Mayor Morrison is a human and leader of the Pyrewood Council who appears in Pyrewood Village in Silverpine Forest during"
[27] https://wowpedia.fandom.com/wiki/Aderic — Aderic
    > "Aderic was a human who was a Gilnean patriarch. He is buried at Aderic's Repose at the top of the hill."
[28] https://worldofwarcraft.blizzard.com/en-us/news/24095666/unveiling-cataclysm-classic-zones-dungeons-and-pvp-season-9 — Unveiling Cataclysm Classic Zones, Dungeons, and PvP Season 9
    > "Godfrey’s right-hand man, the arrogant Lord Walden vowed to pay any price, including death, to serve his compatriot."
    > "Baron Silverlaine was master of the keep before it fell to Arugal’s worgen."
[29] http://media.blizzard.com/wow/lore/pdfdownload/leader-story/genn-greymane/greymane-enUS.pdf — greymane-enUS
    > ""Never take a man's hand, Son..." King Archibald Greymane said, his strong frame now a muddied silhouette against the fading glow of twilight."
[30] https://wowpedia.fandom.com/wiki/Lord_Ashbury_the_1st?action=render — References
    > "Lord Ashbury the 1st was a Gilnean noble and the father of Baron Ashbury. Lord Ashbury helped King Archibald Greymane build Gilneas up to a nation of great power."
[31] https://wowpedia.fandom.com/wiki/Gilneas_City — Gilneas City
    > "Gilneas City (or the Ruins of Gilneas City[3] and simply Gilneas) was the capital city of the kingdom of Gilneas located in the peninsula of the same name."
[32] https://wowpedia.fandom.com/wiki/Greymane_Manor — Greymane Manor
    > "Greymane Manor is a palatial estate high in the hills of western Gilneas, owned by Genn Greymane and his family."
[33] https://wowpedia.fandom.com/wiki/Crowley_Orchard — Crowley Orchard
    > "Crowley Orchard was an apple orchard located south and very close to the town of Duskhaven in southwestern Gilneas."
[34] https://wowpedia.fandom.com/wiki/Crowley_Stable_Grounds — Crowley Stable Grounds - Wowpedia - Your wiki guide to the World of Warcraft
    > "The Crowley Stable Grounds was an extensive area located east of the Crowley Orchard in Gilneas ."
[35] https://wowpedia.fandom.com/wiki/Ambermill — Ambermill - Wowpedia - Your wiki guide to the World of Warcraft
    > "Prior to the advent of the Third War , Ambermill was a relatively unimportant site in the Silverpine Forest and was mainly used for lumber harvesting, but"
