# Королевский совет Гилнеаса — политические позиции

## Результат и рамка

| Проверяемый объём | Результат |
|---|---|
| Личности | **17/17**, исходные ID сохранены |
| Дома | **7/7**, исходные ID сохранены |
| Формат | Исследовательский файл; репозиторий не изменяется |

| Авторская конвенция | Значение |
|---|---|
| Роялисты | Направление Генна Седогрива; не каноническая формальная партия |
| Интернационалисты | Направление Дариуса Краули; не каноническая формальная партия |
| Нейтральные | Неустановленная позиция; потенциальные союзники, не доказанное бездействие |

| Срез сценария | После Второй войны, до выхода из Альянса и до возведения стены |
|---|---|
| 10/100 | Авторский показатель проекта, не точная дата и не построенный рубеж |

Ретроспективный рассказ Blizzard содержит ранние разговоры о союзе и о планировании стены; его поздние главы не становятся текущими событиями.[1][2][29]

Генн — инициатор изоляционного рубежа; Годфри после торговых оговорок одобряет путь и предлагает созвать совет.[1][2]

Краули прямо защищает союзную помощь; его несогласие со стеной подтверждено ретроспективой.[2][4] В выбранном сценарии он ещё не мятежник, не узник и не ворген.

Эшбери правдоподобно отнести к королевскому лагерю по ранней дружбе и ограниченной военной политике, **но отдельного голоса за стену источник не даёт**: `party=royalists`, `partyBasis=scenario`, `stance=unknown`.[1][7]

Марли — лорд пограничного домена в сцене планирования; его собственное выступление о стене отсутствует.[2][8] Общий каталог называет его советником Генна, но не датирует раннюю службу.[5] Консервативная рекомендация: `advisor=false`, потенциальный союзник.

## Как читать классификацию

| Поле | Правило интерпретации |
|---|---|
| `lore` | Прямая политическая линия/роль; названия партий всё равно авторские |
| `scenario` | Ограниченное авторское допущение: симпатия, агрегация дома или приглашение |
| `unknown` | Неустановленная позиция, без приписанного нейтрального убеждения |
| `advisor=true` | Подтверждённый ранний совет Генну; монарх не свой советник |
| `includeDefault=true` | Рекомендуемое присутствие; потенциальный союзник не получает автоматически голос/кресло |
| Позиция дома | Агрегирована от главы, не доказанное единогласие семьи и не дополнительный голос |

## Личности: текущий состав и возможные союзники

| Существующий ID · имя | Партия | Стена | Основание | Советник | По умолчанию | Краткая записка |
|---|---|---|---|---|---|---|
| `noble-genn` · Генн Седогрив | Роялисты | За | `lore` | Нет | Да | Король ставит самостоятельность Гилнеаса выше союзных обязательств и предлагает новый северный рубеж. Выход из Альянса ещё не совершён.[2][3] |
| `noble-darius` · Дариус Краули | Интернационалисты | Против | `lore` | Да | Да | Северный лорд отстаивает общую защиту с соседними королевствами; проект стены угрожает связям и землям его дома. Спор с короной ещё не стал мятежом.[2][4] |
| `noble-godfrey` · Винсент Годфри | Роялисты | За | `lore` | Да | Да | Годфри поддерживает горную линию стены, укрепляющую оборону и значение его владений. Расчётливый союзник короля; разрыв торговли сначала вызывает у него сомнения.[1][2][6] |
| `noble-ashbury` · Барон Эшбери | Роялисты | Неизвестно | `scenario` | Да | Да | Давний друг Генна поддерживает бережную к казне политику и малое союзное войско. В королевском лагере правдоподобен, но его отдельное решение о стене не известно.[1][3][7] |
| `noble-marley` · Лорд Марли | Нейтральный | Неизвестно | `unknown` | Нет | Да | Лорд пограничной провинции: его земли рассматриваются для нового рубежа. До решения о маршруте он остаётся возможным союзником; личного голоса за стену или против неё не сохранилось.[2][5][8] |
| `noble-walden` · Лорд Уолден | Нейтральный | Неизвестно | `unknown` | Нет | Нет | Гилнеасский лорд из позднего реестра. Для спора о стене его голос неизвестен; возможное приглашение — авторское, без назначения советником.[5][9][28] |
| `noble-hewell` · Лорд Хьювелл | Нейтральный | Неизвестно | `unknown` | Нет | Нет | Лорд Хьювелл может стать союзником короны, но его место в раннем дворе и отношение к стене не известны. Пока не принадлежит ни одной партии.[10] |
| `noble-silverlaine` · Барон Сребролен | Нейтральный | Неизвестно | `scenario` | Нет | Да | Барон хранит северное владение. Связь с домом Краули принята в сценарии, однако она не заменяет его собственного решения о стене.[5][11][28] |
| `noble-longshore` · Барон Дольноберег | Нейтральный | Неизвестно | `unknown` | Нет | Нет | Барон Дольноберег — гилнеасец с засвидетельствованным прежним баронским титулом. Когда он получил его и какую позицию занимает при обсуждении стены, не известно.[5][13][14] |
| `noble-candren` · Лорд Кандрен | Нейтральный | Неизвестно | `unknown` | Нет | Нет | Лорд Кандрен известен службой гилнеасцам, но его раннее место при дворе и решение о северном рубеже не установлены. Возможный союзник вне партий.[5][17] |
| `noble-isiden` · Исиден Перенольд | Нейтральный | Неизвестно | `unknown` | Нет | Да | Альтеракский претендент ищет поддержки в Гилнеасе. Покровительство Генна подтверждено, но личная партия и взгляд на стену не раскрыты; он возможный гость, не советник короля.[3][15] |
| `noble-tulvan` · Лорд Джеффри Тулван | Нейтральный | Неизвестно | `unknown` | Нет | Нет | Лорд Джеффри Тулван — имя из реестра знати; его ранний титул, владения и позиция в споре о стене не известны. Возможный союзник только по условиям сценария.[5][20][24] |
| `noble-harford` · Лорд Харфорд | Нейтральный | Неизвестно | `unknown` | Нет | Нет | Лорд Харфорд считает Гилнеас родиной, но его прежние обязательства и отношение к стене не известны. Предполагаемые северные связи ещё не означают принадлежность партии Краули.[5][21][25] |
| `noble-morrison` · Лорд-мэр Моррисон | Нейтральный | Неизвестно | `unknown` | Нет | Нет | Моррисон известен муниципальной службой Пирвуду; ранняя дата назначения не установлена. Если пригласить его, он может представлять интересы жителей, но его голос о стене неизвестен.[5][22][26] |

## Исторические предшественники и память — отдельно, исключены

| ID · имя | Роль | Почему не включать в текущий совет |
|---|---|---|
| `noble-archibald` · Арчибальд Седогрив | `historical_predecessor` | Предшественник Генна, не живой участник нынешнего совета; календарная дата смерти не назначается.[3][16][29] |
| `noble-ashbury-first` · Лорд Эшбери I | `historical_predecessor` | Засвидетельствован как отец барона и советник прошлого монарха; присутствие/служба при Генне после Второй войны не установлены.[5][19][30] |
| `noble-aderic` · Адерик | `historical_memory` | Предок/мемориальная фигура; нет основания представлять действующим человеком, королём или советником текущего двора.[5][23][27] |

Для этих записей `party=neutral`, `stance=unknown`, `advisor=false`, `includeDefault=false` — техническое исключение, не политическая оценка предков. Адерик назван патриархом, не установленным королём; Арчибальд и Эшбери I относятся к предыдущему поколению.[3][27][30] Даты смерти не назначаются.

## Все существующие дома

| ID · дом | Представитель | Партия | Стена | Основание | Ранний советник-представитель | По умолчанию | Записка |
|---|---|---|---|---|---|---|---|
| `greymane` · Дом Седогривов | `noble-genn` | Роялисты | За | `scenario` | Нет | Да | Правящий дом отстаивает самостоятельность королевства под руководством Генна. Его курс за стену не означает единогласия всех членов семьи.[2][18] |
| `crowley` · Дом Краули | `noble-darius` | Интернационалисты | Против | `scenario` | Да | Да | Дом Дариуса поддерживает общую безопасность с союзными королевствами и сохранение северных связей. Линия главы — не объявленный семейный устав.[2][4] |
| `silverlaine` · Дом Сребролена | `noble-silverlaine` | Нейтральный | Неизвестно | `scenario` | Нет | Да | Северный баронский дом связан с Краули по принятому сценарию, но его самостоятельное отношение к стене остаётся открытым.[5][11][12] |
| `godfrey` · Дом Годфри | `noble-godfrey` | Роялисты | За | `scenario` | Да | Да | Дом Годфри следует расчётливой поддержке королевского рубежа. Его глава сначала заботится о торговых потерях, затем поддерживает выгодную горную линию.[1][2] |
| `ashbury` · Дом Эшбери | `noble-ashbury` | Роялисты | Неизвестно | `scenario` | Да | Да | Старый союзный короне дом тяготеет к Генну; сохранение гилнеасских сил подтверждено, а отдельное одобрение стены — нет.[1][7] |
| `marley` · Дом Марли | `noble-marley` | Нейтральный | Неизвестно | `unknown` | Нет | Да | Приграничный дом Марли может поддержать одну из сторон после гарантий о земле и цене рубежа. Его действительное решение неизвестно.[2][5] |
| `walden` · Дом Уолденов | `noble-walden` | Нейтральный | Неизвестно | `unknown` | Нет | Нет | Дом Уолденов известен по поздней знати; для раннего спора о стене он остаётся возможным, недатированным союзником.[5][9] |

Сребролен → Краули сохраняется **только как авторская конфигурация**. Каталожное «making ... a vassal ... as a result» — производный вывод; ранний рассказ Blizzard не называет эту цепь.[1][5]

Владение крепостью подтверждено, но стеновой голос не установлен.[11][12] Рекомендация: личность и дом нейтральны, `stance=unknown`.

Ранняя служба Уолдена и голос о стене не установлены; каталог и личная статья описывают его поздние роли.[5][9] Официальная характеристика рядом с Годфри также относится к позднему контексту.[28] Рекомендация: факультативный потенциальный союзник, без раннего советнического кресла.

## Рекомендуемый список по умолчанию

**7 личностей:** Генн как монарх; Дариус, Годфри и барон Эшбери как **3 подтверждённых ранних советника**; Марли, Сребролен и Исиден как потенциальные союзники.[2][3][4] Сценарная рекомендация: потенциальным союзникам не назначать автоматически кресло или собственный голос; Сребролен включён по авторской конфигурации, Исиден — как гость.

Марли существует при планировании; Сребролен известен как бывший хозяин северной крепости, но точная дата до стены отдельно не доказана; Исиден ищет убежище и поддержку Генна в послевоенном споре об Альтераке.[2][11][15]

**7 факультативных нейтралов:** Уолден, Хьювелл, Дольноберег, Кандрен, Тулван, Харфорд, Моррисон. Для них допустим авторский пул ранних человеческих версий с `presenceBasis=scenario`, `advisor=false`, `votingSeat=false`, но не утверждение о реальном участии во дворе после Второй войны.

Дольноберег лично свидетельствует о прежнем настоящем баронстве без даты; Кандрен известен поздней интендантской должностью; Харфорд прямо называет Гилнеас родиной.[14][17][25]

Ранний голос о стене в этих свидетельствах не установлен.[14][17][25]

Моррисон засвидетельствован как глава местного совета Пирвуда, а не ранний королевский советник; Тулван — поздний воин без установленного раннего домена.[5][24][26] Рекомендация: не выводить партию из соседства, недатированного титула или предполагаемой вассальной связи.

Хьювелл позднее сохраняет личную верность Генну; это не доказывает его позицию о стене или раннее назначение.[10]

## Источники и проверка

| Контроль источников | Проверенный результат |
|---|---|
| Извлечённые URL | **30**: Wowpedia, Blizzard HTML/PDF и атрибутированные зеркала |
| Цитатные связи | **66** |
| Уникальные дословные цитаты | **52**, каждая проверена по сохранённому тексту |

Первоначальные 403/network_error на нескольких URL Wowpedia записаны в сырой evidence; затем извлечены атрибутированные зеркала и повторные варианты оригиналов. Зеркальные статьи относятся к тем же ранним/поздним личностям и не добавляют независимого первичного свидетельства.[19][20][21]

Имена и местные роли в восстановленных страницах сопоставлены с оригинальным каталогом; зеркальные версии Моррисона и Адерика не датируют их раннее участие.[5][22][23]

HTTPS-загрузка `media.blizzard.com` не прошла проверку имени сертификата; проверка TLS не отключалась. Найденный официальный HTTP URL вернул 200. PDF сохранён как `politics-evidence/greymane-enUS.pdf`, полный извлечённый текст — `politics-evidence/greymane-enUS-full-extracted.md`.[29]

| Схема ссылок | Значение |
|---|---|
| `[n]` отчёта | Локальный politics citation-ledger, **не source IDs атласа** |
| `existingSourceIds` | Точное URL-сопоставление с существующим атласом |
| `existingSourceMatches` | Отдельно canonical/same-page matches; исходные IDs не перенумеровываются |

Контроль: 17/17 ID личностей, 7/7 ID домов; дубликатов нет. Код, assets/data, публикации и Git не изменялись; браузер приложения, коммиты и деплой не запускались.

## Дословная опора по ключевым спорным случаям

**Годфри — поддержка после оговорок:** «— Надо созвать совет дворянства, — сказал он, вставая из кресла. — Мы идем верным путем, мой повелитель, хотя, возможно, он полон подводных камней.»[2]

**Эшбери — ранний совет, не стеновое голосование:** “He was present in the Capital City to create the Alliance of Lordaeron and agreed with Lord Godfrey, to send only a token army.”[7]

**Краули — согласованная с лором линия против стены:** “A pro-Alliance figure, he dissented with King Genn Greymane's decision to separate his people with the Greymane Wall.”[4]

**Сребролен — подтверждено владение, не голос и не первичный вассалитет:** “Baron Silverlaine was master of the keep before it fell to Arugal’s worgen.”[28]

**Марли — ранний домен, не выступление:** «— Судя по этим наброскам, вы планируете затронуть владения лорда Марли… Но взгляните и сюда — здесь начинается горная цепь, идеальное природное заграждение…»[2]

Точные цитаты, относящиеся к каждому полю каждой личности и дома, находятся в JSON; у каждой есть `scope`, полный фактически прочитанный URL и путь к сохранённому тексту.

## Sources

[1] https://worldofwarcraft.blizzard.com/en-us/media/short-story/genn-greymane-lord-of-his-pack — Genn Greymane: Lord of His Pack - Media Gallery - World of Warcraft
    > "“You want to wall off our entire nation? Close our borders and end trade with the rest of the Alliance? I… it is a rather large decision, would you not say?”"
    > "His name was Godfrey. Genn trusted his counsel but was always suspicious about his ambitions. Godfrey’s notion was not motivated by empathy as Crowley’s was. It was a smart political play that ensured notoriety for Godfrey, the commander of that standing militia."
    > "“It is a path that does have merit, my lord,” Baron Ashbury added. Ashbury was one of Genn’s most trusted friends. Genn had grown up with him; his father, Lord Ashbury the 1st, had helped Archibald build the nation up, and Archibald had always told Genn to trust in the Ashburys’ fidelity to the crown."
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
