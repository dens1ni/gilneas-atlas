# Именная перепись гилнеасской знати и семей

**Результат:** только проверенное предложение; production не применяется, существующие 17 записей не изменяются.

**Срез:** После Второй войны, до выхода Гилнеаса из Альянса и до возведения Стены Седогрива.

## Проверенная полнота

В переписи 38 кандидатов: 26 включены (17 уже существующих и 9 новых), 12 исключены с причиной; нет произвольного лимита.

Прямой каталог содержит 22 именные строки, все покрыты; Dame Alys Finnsson дополнительно найдена в Trivia. Названные Greymane/Crowley родственники включены, фамильные гипотезы сохранены как исключения.[1][2][3]

Полный живой API аристократии дал 637 уникальных pageid: 630 статей и 7 подкатегорий; обе страницы завершены без has_more. В Category:Gilneas (kingdom) 394 записей, пересечение с аристократией — 24.[45][42][46]

HTML показывает 629 страниц глобально, но корректный парсер всех переходящих буквеных списков получил 630; пропуск имени с кавычками исправлен, countDiscrepancyResolved есть в aristocrats-category-audit.json. API namespace-сумма, а не ошибочный счётчик HTML, является итоговой проверкой.[45][42]

Category:Gilneas NPCs также получена целиком: 92 записи, continuation отсутствует; её участники сверены отдельно с ранней родословной.[47]

Обычных новых советников и голосующих нет: семейные и справочные записи получают advisor=false/votingSeat=false, party=neutral, stance=unknown. Баллы не источник лора.

## Все новые записи

| ID | Имя | Дом | lifeStatus раннего среза | active | Роль | Влияние партия/королевство (scenario) |
|---|---|---|---|---|---|---|
| `noble-mia` | Миа Седогрив | `greymane` | `alive` | `true` | `royal_consort` | 0/30 |
| `noble-liam` | Лиам Седогрив | `greymane` | `unknown` | `false` | `royal_heir_reference` | 0/0 |
| `noble-tess` | Тесс Седогрив | `greymane` | `alive` | `true` | `royal_princess` | 0/5 |
| `noble-lorna` | Лорна Краули | `crowley` | `unknown` | `false` | `noble_family_reference` | 0/0 |
| `noble-hiram-creed` | Хирам Крид | `null` | `unknown` | `false` | `suspected_noble_reference` | 0/0 |
| `noble-woofington` | Лорд Вуфингтон | `null` | `unknown` | `false` | `honorary_reference` | 0/0 |
| `noble-alys-finnsson` | Дама Алис Финнссон | `null` | `unknown` | `false` | `undated_noble_reference` | 0/0 |
| `noble-ashmore` | Графиня Эшмор | `null` | `unknown` | `false` | `noncanon_noble_reference` | 0/0 |
| `noble-lady-in-white` | Дама в белом | `null` | `unknown` | `false` | `noncanon_noble_reference` | 0/0 |

### Рождение и жизнь: что установлено, а что нет

Миа — жена Генна и мать Тесс; Тесс прямо существовала до выхода Гилнеаса из Альянса. У Тесс нет точного возраста или доказанного раннего наследного/советнического кресла. Активная Тесс здесь относится к предвыходному этапу, не ко всему интервалу начиная с первого дня после войны.[2][16][50]

Лиам показан подростком на уже построенной стене при Плети; редакторская заметка going up не заменяет раннюю birth-date. Он добавлен inactive/unknown; факт его поздней гибели не записан как ранний dead.[8][17][41]

Лорна — подтверждённая дочь Дариуса, но её рождение до стены не датировано; ранняя запись inactive/unknown. Нельзя получать раннюю партию от фамилии, мятежа или командования будущего.[57]

Хирам — драконид под маской лорда, подлинный дом Creed неизвестен; Вуфингтон — мастиф с поздним пожалованием; Алис — носительница обращения Dame, ранняя дата неизвестна. Все три сохранены как inactive/unknown, а не удалены или выданы за ранних людей.[76][20][1]

Эшмор и Дама в белом найдены категорийным/гильнеасским аудитом, но их Hearthstone-only истории явно считаются non-canon. Они включены лишь как маркированные inactive/unknown справки; дракон/призрак не становится ранним human noble.[60][61]

### Прозрачные сценарные веса

Сохранена дисциплина docs/council-influence-seed: нейтралы имеют party=0, inactive=0/0, личное владение/главенство/ранний совет не выводится из родства. Для новых ролей калибровка названа явно, а не выдана за исходную каноническую формулу.

- Миа: 30 kingdom = 5 active reserve + 25 contextual queen-consort dynastic weight. Ни раннее советничество, ни государственные земли Генна не прибавлены повторно.
- Тесс: 5 kingdom = минимальная активная семейная доступность; youthful role не даёт дополнительных голосов или будущих должностей.
- Лиам: текущие 0/0; при отдельно проверенном рождении в конкретном сценарии допустим условный резерв наследника 15=5+10, но он не применён.
- Лорна: текущие 0/0; только после отдельного раннего подтверждения возможен малый сценарный резерв 3, не позднее командование.
- Остальные пять спорных/почётных/неканонических записей: 0/0. Ни новые holdings/owners, ни партийный reseed не выполняются.

## Каждый кандидат: решение и точное основание

### Archibald Greymane — уже есть noble-archibald

Уже присутствует под точным ID noble-archibald; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | King Archibald Greymane | Deceased | King of Gilneas. Father of Genn. |[1]

### Genn Greymane — уже есть noble-genn

Уже присутствует под точным ID noble-genn; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | King Genn Greymane | Alive | King of Gilneas. Son of Archibald. |[1]

### Lord Ashbury the 1st — уже есть noble-ashbury-first

Уже присутствует под точным ID noble-ashbury-first; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Ashbury the 1st | Deceased | Councilor of King Archibald Greymane. Father of Baron Ashbury. |[1]

### Baron Ashbury — уже есть noble-ashbury

Уже присутствует под точным ID noble-ashbury; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Baron Ashbury | Deceased (Undead) | Son of Lord Ashbury the 1st. Former councilor of King Genn Greymane, traitor alongside Godfrey and Walden. Raised as Forsaken, he later followed Godfrey within Shadowfang Keep. Killed on the orders of both factions. |[1]

### Darius Crowley — уже есть noble-darius

Уже присутствует под точным ID noble-darius; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Darius Crowley | Alive | Leader of the rebels during the Northgate Rebellion. Now leader of the Gilneas Liberation Front and the Gilneas Brigade. |[1]

### Lord Candren — уже есть noble-candren

Уже присутствует под точным ID noble-candren; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Candren | Alive | Gilneas Quartermaster. |[1]

### Lord Geoffery Tulvan — уже есть noble-tulvan

Уже присутствует под точным ID noble-tulvan; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Geoffery Tulvan | Killable | Fighter in the Crucible of Carnage. |[1]

### Lord Harford — уже есть noble-harford

Уже присутствует под точным ID noble-harford; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Harford | Deceased | A former worgen servant of Arugal in Shadowfang Keep who escaped and joined the Argent Dawn. Captured by the Scarlet Crusade and executed by the death knights of Acherus. |[1]

### Lord Hewell — уже есть noble-hewell

Уже присутствует под точным ID noble-hewell; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Hewell | Alive | Unknown. |[1]

### Lord Marley — уже есть noble-marley

Уже присутствует под точным ID noble-marley; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Marley | Unknown | Councilor of King Genn Greymane. |[1]

### Vincent Godfrey — уже есть noble-godfrey

Уже присутствует под точным ID noble-godfrey; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Vincent Godfrey | Deceased (Undead) | Former councilor of King Genn Greymane, traitor alongside Ashbury and Walden. Raised as Forsaken, he later betrayed Sylvanas and became the master of Shadowfang Keep. Killed on the orders of both factions. |[1]

### Lord Walden — уже есть noble-walden

Уже присутствует под точным ID noble-walden; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Walden | Deceased (Undead) | Former councilor of King Genn Greymane, traitor alongside Ashbury and Godfrey. Raised as Forsaken, he later followed Godfrey within Shadowfang Keep. Killed on the orders of both factions. |[1]

### Lord Mayor Morrison — уже есть noble-morrison

Уже присутствует под точным ID noble-morrison; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Lord Mayor Morrison | Deceased | Leader of Pyrewood Council and Arugal's puppet. Killed during an ambush by the Deathstalkers.&#91;7&#93; |[1]

### Baron Silverlaine — уже есть noble-silverlaine

Уже присутствует под точным ID noble-silverlaine; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Baron Silverlaine | Active (Undead) | Former lord of Shadowfang Keep, an area that held loyalty to Darius Crowley past the Greymane Wall. Slain by Arugal and his worgen and cursed to defend the keep as a ghost. Even after Arugal was slain, the baron's spirit continues to defend his former home. |[1]

### Baron Longshore — уже есть noble-longshore

Уже присутствует под точным ID noble-longshore; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Baron Longshore&#91;8&#93; | Killable | Captain of the pirate ship Heedless, and one of the Gilneans locked out of Gilneas by the Greymane Wall. Imprisoned by the forces of Theramore on the Merchant Coast. |[1]

### Aderic — уже есть noble-aderic

Уже присутствует под точным ID noble-aderic; включён в перепись без повторной записи и без изменения его полей.[1]

**Время:** Поздний инфобокс не используется для замены раннего lifeStatus; существующая запись сохранена целиком, отдельный аудит исходных 17 принадлежит родительскому заданию.[1]

> | Aderic | Deceased | Referred to as a "patriarch", and has the Royal Aderic Banquet named in his honor.&#91;9&#93; Possibly a long-dead king or nobleman. |[1]

### Isiden Perenolde — уже есть noble-isiden

Уже существует noble-isiden: альтеракский претендент и гость Гилнеаса, не новый гилнеасский дом.[40]

**Время:** Бегство в Гилнеас и поддержка Генна засвидетельствованы; эти сведения не создают раннюю должность или землю.[40]

> Isiden Perenolde&#91;1&#93; was the nephew of Lord Aiden Perenolde, King of Alterac. When Alterac was placed under martial law by order of King Terenas, Isiden fled to Gilneas, where he hoped to rally support.&#91;2&#93; He was eventually backed by Genn Greymane, Gilneas' king, as the matter of the succession began to heat up.&#91;3&#93;[40]

### Mia Greymane — новая noble-mia

Пропущенная супруга Генна и мать Лиама и Тесс: включить самостоятельную королевскую запись noble-mia, не ordinary advisor.[4][2][16]

**Время:** Миа — королева и мать Тесс, чьё существование до выхода из Альянса прямо подтверждено. Ни дата брака, ни раннее голосование не выдумываются.[4][2][16]

> Mia Greymane is the wife of Genn Greymane and former queen consort of Gilneas.[4]

### Liam Greymane — новая noble-liam

Пропущенный сын и наследник Генна: включить noble-liam; умер в будущем, не отмечать ранним dead.[5][8][17]

**Время:** Первичная сцена показывает подростка на уже построенной стене при Плети. Даты рождения до рассматриваемого послевоенного момента нет; редакторская прикидка не заменяет её. selected-era lifeStatus=unknown, active=false; поздний факт смерти хранится отдельно.[5][8][17]

> Prince Liam Greymane was a member of the royal family of Gilneas, and the son and heir of King Genn Greymane.&#91;1&#93;[5]

### Tess Greymane — новая noble-tess

Пропущенная дочь Генна и Миа: включить noble-tess как юную принцессу, не правящую королеву и не раннего наследника вместо Лиама.[43][16][50]

**Время:** Калия прямо помнит Тесс очень молодой при выходе Гилнеаса из Альянса; текущая статья ставит её рождение до выхода. Для предвыходного среза допустима alive семейная запись без возраста и самостоятельного голоса; она не гарантирует существование в самый первый день после Второй войны.[43][16][50]

> Genn & Mia (parents),  Liam (brother),  Archibald (grandfather)[43]

### Lorna Crowley — новая noble-lorna

Пропущенная подтверждённая дочь Дариуса: включить noble-lorna, а не всех людей с фамилией Crowley.[57][18]

**Время:** Рождение и существование до стены не датированы; первый развёрнутый эпизод относится к позднему нападению воргенов. selected-era lifeStatus=unknown, active=false; командование и мятеж не переносятся назад.[57][18]

> Lorna Crowley is the daughter of Lord Darius Crowley, one of the principal leaders during the Northgate Rebellion.[57]

### Hiram Creed — новая noble-hiram-creed

Именной каталоговый самозванец: включить noble-hiram-creed только как неактивную спорную справку, не раннего human noble.[76][1]

**Время:** Драконид в облике знатного гилнеасца известен по позднему Гилнеасу после нашествия; подлинный дом Creed и ранняя личность не установлены. lifeStatus=unknown, active=false, influence=0/0.[76][1]

> Lord Hiram Creed was a black drakonid who disguises themselves as an affluent Gilnean noble.[76]

### Lord Woofington — новая noble-woofington

Именной каталоговый почётный лорд-мастиф: включить noble-woofington только как неактивную справку.[20][23]

**Время:** Титул дан собаке после безумия жителей Хейвенсвуда; это не человеческий наследственный дворянин и не предвоенное кресло. Дата рождения неизвестна: unknown, inactive, 0/0.[20][23]

> Lord Woofington is a mastiff companion.[20]

### Dame Alys Finnsson — новая noble-alys-finnsson

Именное обращение Dame и каталоговая гилнеасская привязка: включить noble-alys-finnsson как неактивную недатированную справку.[1][19]

**Время:** Известна в поздних Сумеречных нагорьях как ворген-служительница Сумеречного Молота. Date/title-before-wall неизвестны; killable не доказывает раннюю смерть или жизнь. house=null, unknown, inactive, 0/0.[1][19]

> - The title used by Alys Finnsson, a Gilnean member of the Twilight's Hammer, of Dame is a part of the British honors system, as a female counterpart to the honorific of 'sir' bestowed upon knights.[1]

### Countess Ashmore — новая noble-ashmore

Явно категорийно найденная подозрительная гилнеасская графиня из Hearthstone: включить noble-ashmore как неканоническую неактивную справку с явным предупреждением.[15][60]

**Время:** Синий дракон, спорная родословная и Hearthstone-exclusive/non-canon; это не доказательство раннего человеческого графского дома. До стены existence=unknown, inactive, 0/0.[15][60]

> Countess Ashmore is a blue dragon&#91;1&#93; featured in the The Witchwood expansion for Hearthstone.[15]

### Lady in White — новая noble-lady-in-white

Категорийное пересечение прямо называет гилнеасскую дворянку в прошлом: сохранить именованный эпитет noble-lady-in-white, без выдуманного личного имени или дома.[61]

**Время:** Hearthstone-exclusive/non-canon; призрак после падения Гилнеаса. Human noble в её собственном прошлом не датирован до стены. lifeStatus=unknown, inactive, 0/0; late ghost не переносится в ранний портрет.[61]

> In life, the Lady in White was a Gilnean noble woman, who saw the destruction of almost all that she loved during the fall of Gilneas.[61]

### Brother Crowley — исключён

Фамилия сама по себе не доказывает родство с Дариусом/Лорной или гилнеасское дворянство; семейная страница прямо оставляет родство неизвестным.[3]

**Время:** Ни раннее родство, ни титул до стены не установлены; не создаётся nobleId или активное кресло.[3]

> - Brother Crowley - A member of the Scarlet Crusade; unknown if he's part of the family or not.[3]

### Morticia Crowley — исключён

Фамилия сама по себе не доказывает родство с Дариусом/Лорной или гилнеасское дворянство; семейная страница прямо оставляет родство неизвестным.[3]

**Время:** Ни раннее родство, ни титул до стены не установлены; не создаётся nobleId или активное кресло.[3]

> - Morticia Crowley - an undead found on Draenor; unknown if she's part of the family or not.[3]

### Agent Crowley — исключён

Фамилия сама по себе не доказывает родство с Дариусом/Лорной или гилнеасское дворянство; семейная страница прямо оставляет родство неизвестным.[3][54]

**Время:** Ни раннее родство, ни титул до стены не установлены; не создаётся nobleId или активное кресло.[3][54]

> - Agent Crowley - a human mage; unknown if he's part of the family or not.[3]

### Elizabeth Crowley — исключён

Фамилия сама по себе не доказывает родство с Дариусом/Лорной или гилнеасское дворянство; семейная страница прямо оставляет родство неизвестным.[3][58]

**Время:** Ни раннее родство, ни титул до стены не установлены; не создаётся nobleId или активное кресло.[3][58]

> - Elizabeth Crowley - Forsaken priest, unknown if she's part of the family or not.[3]

### Crispin Greymane — исключён

Семейная статья прямо называет неродственным: дворф или таунка, не член гилнеасской династии.[2]

**Время:** Нет гилнеасской noble/family привязки; иная раса и похожая фамилия не основание ранней записи.[2]

> There are also an unrelated Crispin Greymane dwarf and an Elder Graymane taunka.[2]

### Elder Graymane — исключён

Семейная статья прямо называет неродственным: дворф или таунка, не член гилнеасской династии.[2]

**Время:** Нет гилнеасской noble/family привязки; иная раса и похожая фамилия не основание ранней записи.[2]

> There are also an unrelated Crispin Greymane dwarf and an Elder Graymane taunka.[2]

### Lieutenant Walden — исключён

Гилнеасский лейтенант, но родство с Lord Walden лишь may be; звание офицера не дворянский титул.[59]

**Время:** Поздняя военная служба и смерть не доказывают раннюю noble-family запись.[59]

> He may be related to Lord Walden.[59]

### Brambley Morrison — исключён

Родство с лордом-мэром Моррисоном прямо помечено предположением; фамилии недостаточно для noble-family включения.[69]

**Время:** Не установлены раннее родство, титул и гилнеасская семья; отдельные статьи не нужны для принятия отрицательного genealogical решения.[69]

> He may be related to Brambley Morrison and Vinnie Morrison.[69]

### Vinnie Morrison — исключён

Родство с лордом-мэром Моррисоном прямо помечено предположением; фамилии недостаточно для noble-family включения.[69]

**Время:** Не установлены раннее родство, титул и гилнеасская семья; отдельные статьи не нужны для принятия отрицательного genealogical решения.[69]

> He may be related to Brambley Morrison and Vinnie Morrison.[69]

### Magistrate Henry Maleb — исключён

Магистрат Южнобережья из Лордерона, поздний союзник Краули; RPG-aristocrat не гилнеасское наследственное дворянство.[28]

**Время:** Позднее нахождение в Shadowfang и сотрудничество с гилнеасцами не делает его ранним гилнеасским лордом.[28]

> Before the Forsaken bombing of the city, he was the human Magistrate of Southshore in the Hillsbrad Foothills.[28]

### Krennan Aranas — исключён

Королевский химик назван в семейной статье как персонал, не как Known member; придворная должность не доказательство дворянства или родства.[75]

**Время:** Ранняя помощь Тесс допустима как биографическая связь, но не отдельное noble-family кресло.[75]

> Krennan Aranas is the Royal Chemist of Gilneas. Genn notes him as one of the most powerful chemists in Azeroth, or at least Gilneas.[75]

### Gilneas Nobleman — исключён

Безымянный шаблонный NPC, а не отдельный названный человек; к тому же удалённое PTR-содержимое.[29]

**Время:** Не вышел из позднего PTR; в раннюю родословную не добавляется.[29]

> The subject of this article or section did not make it out of the [patch 8.3.0](/wiki/Patch_8.3.0)[test realms](/wiki/Public_Test_Realm).[29]

## Семейные пробелы без вымышленных имён

- **Mia parents / maiden family**: В прочитанной Mia Greymane назван только father-in-law Archibald, не её родные отец или мать; их имена и родной дом не установлены. Не создавать безымянных родителей.[4]
- **Genn mother / Archibald wife / older generations**: Статья Арчибальда называет сына, невестку и внуков, но не имя супруги, родителей или матери Генна. Иные имена из User:/roleplay не входят в source scope.[63][2]
- **Darius spouse**: В Known members супруг(а) Дариуса показан(а) N/A; N/A не доказывает отсутствие супруги или смерть, но имени для записи нет.[3]
- **Lorna sibling / other children**: Свежая Warcraft Wiki сообщает at least one sibling из my children. Это только безымянная неопределённость; не идентифицировать её ни с одним Crowley Others и не создавать второй noble.[18]
- **father and son / other spouses or children**: Именная ранняя пара Lord Ashbury the 1st → Baron Ashbury уже представлена обоими точными IDs; иных именных родственников в прочитанных страницах нет.[64]
- **wife and family**: Известны погибшая супруга и семья, но без имён; поздняя гибель после призыва воргенов не ранняя дата. Не создавать безымянные noble-записи.[26]
- **Lieutenant Walden**: Именной офицер отдельно проверен и исключён: лишь предположение о родстве.[59]
- **Brambley / Vinnie**: Оба кандидата сохранены с include=false: лишь may be related.[69]
- **spouses and other children**: Полные свежие API-статьи проверены; новых прямо названных родственников не выявлено. География и одинаковые фамилии не разворачиваются в выдуманные дома.[71][68][66]

## Локализация

Миа Седогрив прямо названа в официальной русской «Элегии»; Лиам и Тесс имеют официальные русские личные имена из «Вожака Стаи», их семейная фамилия выведена из подтверждённых Greymane связей и русского Седогрив. Для Лорны прочитана ruRU-карточка Wowhead; остальные новые имена прямо помечены transliteration/editorial_translation, не ложной локализацией.[51][9][48]

## Проверка и ограничения записи

Всe 81 зарегистрированные цитатные связи проверены по сохранённым текстам; источники namespaced family-source-N совпадают с механически выданными ledger IDs. Все relations имеют exact known/proposed nobleIds; новые IDs уникальны.

SHA-256 assets/data/atlas.json: до `632c6623f4b16216fda80ff278de8b6670ee75fad8fd0bcc47fb767edc6ffaca`, после `ea5db3dac4e4098a2e4eab2bab7a4d9718ffa18b14a2796f28e96e7ad30a50b7`. Родитель параллельно добавил lifeStatus/lifeStatusBasis/lifeStatusNote и fieldSources.lifeStatus исходным 17; остальные их поля совпали. Этот census production не писал. Все карты, координаты и публикационные baseline-снимки совпали по SHA-256; весь UI-bundle неизменным не объявляется.

Изменены только noble-family-census.json/.md, noble-family-ledger.json и noble-family-evidence/*. Нет production/data/model/UI/CSS/test/manifest writes, commit или deploy.

Retrieval: 403/challenge/redirect-only и HTML truncation не приняты как лор; Wowpedia API дал полные статьи. PDF Blizzard имеет TLS hostname failure; вместо него использован официальный HTML рассказ. Parenthesized wiki URLs требуют локального URL-parser исправления citation verifier; исходные URLs не изменяются.

## Sources

[1] https://wowpedia.fandom.com/wiki/Nobles_of_Gilneas — Nobles of Gilneas
    > "The nobles of Gilneas are the ruling class of the kingdom of Gilneas. Some were slain during the civil war, while others were turned into worgen or Forsaken during the Forsaken invasion. Others remain human in exile from their homeland.[1]"
    > "| King Archibald Greymane | Deceased | King of Gilneas. Father of Genn. |"
    > "| King Genn Greymane | Alive | King of Gilneas. Son of Archibald. |"
    > "| Lord Ashbury the 1st | Deceased | Councilor of King Archibald Greymane. Father of Baron Ashbury. |"
    > "| Baron Ashbury | Deceased (Undead) | Son of Lord Ashbury the 1st. Former councilor of King Genn Greymane, traitor alongside Godfrey and Walden. Raised as Forsaken, he later followed Godfrey within Shadowfang Keep. Killed on the orders of both factions. |"
    > "| Lord Darius Crowley | Alive | Leader of the rebels during the Northgate Rebellion. Now leader of the Gilneas Liberation Front and the Gilneas Brigade. |"
    > "| Lord Candren | Alive | Gilneas Quartermaster. |"
    > "| Lord Geoffery Tulvan | Killable | Fighter in the Crucible of Carnage. |"
    > "| Lord Harford | Deceased | A former worgen servant of Arugal in Shadowfang Keep who escaped and joined the Argent Dawn. Captured by the Scarlet Crusade and executed by the death knights of Acherus. |"
    > "| Lord Hewell | Alive | Unknown. |"
    > "| Lord Marley | Unknown | Councilor of King Genn Greymane. |"
    > "| Lord Vincent Godfrey | Deceased (Undead) | Former councilor of King Genn Greymane, traitor alongside Ashbury and Walden. Raised as Forsaken, he later betrayed Sylvanas and became the master of Shadowfang Keep. Killed on the orders of both factions. |"
    > "| Lord Walden | Deceased (Undead) | Former councilor of King Genn Greymane, traitor alongside Ashbury and Godfrey. Raised as Forsaken, he later followed Godfrey within Shadowfang Keep. Killed on the orders of both factions. |"
    > "| Lord Mayor Morrison | Deceased | Leader of Pyrewood Council and Arugal's puppet. Killed during an ambush by the Deathstalkers.[7] |"
    > "| Baron Silverlaine | Active (Undead) | Former lord of Shadowfang Keep, an area that held loyalty to Darius Crowley past the Greymane Wall. Slain by Arugal and his worgen and cursed to defend the keep as a ghost. Even after Arugal was slain, the baron's spirit continues to defend his former home. |"
    > "| Baron Longshore[8] | Killable | Captain of the pirate ship Heedless, and one of the Gilneans locked out of Gilneas by the Greymane Wall. Imprisoned by the forces of Theramore on the Merchant Coast. |"
    > "| Aderic | Deceased | Referred to as a "patriarch", and has the Royal Aderic Banquet named in his honor.[9] Possibly a long-dead king or nobleman. |"
    > "Given that he was, in truth, a drakonid, it is unknown if there is an actual Creed family that he infiltrated / impersonated into, or if he was the only member."
    > "- The title used by Alys Finnsson, a Gilnean member of the Twilight's Hammer, of Dame is a part of the British honors system, as a female counterpart to the honorific of 'sir' bestowed upon knights."
[2] https://wowpedia.fandom.com/wiki/Greymane_family — Greymane family
    > "The Greymane family (also known as the Greymane clan)[1] is the ruling line of the kingdom of Gilneas. The family ruled from Greymane Manor and had a Royal Chemist in the form of Krennan Aranas."
    > "Mia is the wife of Genn and mother of Tess and Liam.[2]"
    > "There are also an unrelated Crispin Greymane dwarf and an Elder Graymane taunka."
[3] https://wowpedia.fandom.com/wiki/Crowley — Crowley
    > "Crowley is the name of a notorious noble family of Gilneas. They owned the lands of Pyrewood Village and Ambermill. They also were the owners of Crowley Orchard and Crowley Stable Grounds."
    > "- Brother Crowley - A member of the Scarlet Crusade; unknown if he's part of the family or not."
    > "- Morticia Crowley - an undead found on Draenor; unknown if she's part of the family or not."
    > "- Agent Crowley - a human mage; unknown if he's part of the family or not."
    > "- Elizabeth Crowley - Forsaken priest, unknown if she's part of the family or not."
    > "| N/A | One of the lords of Gilneas. | Alive |"
[4] https://wowpedia.fandom.com/wiki/Mia_Greymane — Mia Greymane
    > "Mia Greymane is the wife of Genn Greymane and former queen consort of Gilneas."
    > "Mia met her future husband Genn at the Royal Aderic Banquet, where he was smitten by her. They later married for love, rather than political reasons.[1][2]"
    > "Genn (husband), Tess (daughter), Liam (son), Archibald (father-in-law)"
[5] https://wowpedia.fandom.com/wiki/Liam_Greymane — Liam Greymane
    > "Prince Liam Greymane was a member of the royal family of Gilneas, and the son and heir of King Genn Greymane.[1]"
[8] https://worldofwarcraft.blizzard.com/en-us/media/short-story/genn-greymane-lord-of-his-pack — Genn Greymane: Lord of His Pack - Media Gallery - World of Warcraft
    > "Genn, a teenage Liam, the captain, and the infamous royal archmage known as Arugal were standing on the ramparts high above the Greymane Wall."
[9] https://worldofwarcraft.blizzard.com/ru-ru/media/short-story/genn-greymane-lord-of-his-pack — Генн Седогрив: Вожак Стаи - Галерея - World of Warcraft
    > "Рядом с кораблем плыли еще несколько эльфийских фрегатов; Генн знал, что на одном из них, на «Свете Элуны», плыли его жена Миа и дочь Тесс. Все, что осталось от его семьи. Как же тяжело было думать о семье, в которой нет больше сына! Эта боль была сильнее любых физических страданий, сильнее тоски по потерянному королевству."
    > "Капитан стражи с трудом скрывал свой страх, не в силах отвести взгляда от того, что творилось у подножия Стены Седогрива. Рядом с ним на дозорном укреплении стояли Генн, юный принц Лиам и знаменитый верховный маг, известный как Аругал."
[15] https://wowpedia.fandom.com/wiki/Countess_Ashmore — Countess Ashmore
    > "Countess Ashmore is a blue dragon[1] featured in the The Witchwood expansion for Hearthstone."
    > "It is not clear if Ashmore is truly the scion of a forgotten noble family returned home in a time of need, or if she is something much more dangerous.[2]"
[16] https://warcraft.wiki.gg/wiki/Tess_Greymane — Tess Greymane
    > "Tess was born to Queen Mia and King Genn before Gilneas left the Alliance of Lordaeron after the Second War.[8]"
[17] https://warcraft.wiki.gg/wiki/Liam_Greymane — Liam Greymane
    > "- As Liam was a young teenager during the Greymane Wall going up and the Scourge attacking it; he would have been in his mid-twenties when he died."
[18] https://warcraft.wiki.gg/wiki/Lorna_Crowley — Lorna Crowley
    > "Darius (father), at least one sibling[1]"
    > "Heavens no. This is the peace we--and my children--worked for. I hope they get to live in it."
[19] https://wowpedia.fandom.com/wiki/Dame_Alys_Finnsson?so=search — Dame Alys Finnsson
    > "Dame Alys Finnsson is a worgen, affiliated with the Twilight's Hammer, found in the Twilight Highlands."
    > "| Status | Killable |"
[20] https://wowpedia.fandom.com/wiki/Lord_Woofington?so=search — Lord Woofington
    > "Lord Woofington is a mastiff companion."
    > "Lord Woofington was given his title after the rest of the denizens of Havenswood succumbed to madness."
[23] https://web.archive.org/web/20251118114028/https://wowpedia.fandom.com/wiki/Lord_Woofington — Lord Woofington — Wayback snapshot 2025-11-18
    > "Lord Woofington was given his title after the rest of the denizens of Havenswood succumbed to madness."
[26] https://wowpedia.fandom.com/wiki/Baron_Silverlaine — Baron Silverlaine
    > "Relative(s)
 Deceased wife"
    > "Baron Silveraline and his family were killed by the worgen, summoned by Archmage Arugal from the Emerald Dream to aid Gilneans against the Scourge, after they turned on the Gilneans. After the Fourth War, Mathias Shaw reported a common belief that the ghost of Baron Silverlaine still haunts the keep.[1]"
[28] https://wowpedia.fandom.com/wiki/Magistrate_Henry_Maleb — Magistrate Henry Maleb
    > "Before the Forsaken bombing of the city, he was the human Magistrate of Southshore in the Hillsbrad Foothills."
    > "He was classified as an aristocrat and a fighter."
[29] https://wowpedia.fandom.com/wiki/Gilneas_Nobleman — Gilneas Nobleman
    > "The subject of this article or section did not make it out of the [patch 8.3.0](/wiki/Patch_8.3.0)[test realms](/wiki/Public_Test_Realm)."
[40] https://wowpedia.fandom.com/wiki/Isiden_Perenolde — Isiden Perenolde
    > "Isiden Perenolde[1] was the nephew of Lord Aiden Perenolde, King of Alterac. When Alterac was placed under martial law by order of King Terenas, Isiden fled to Gilneas, where he hoped to rally support.[2] He was eventually backed by Genn Greymane, Gilneas' king, as the matter of the succession began to heat up.[3]"
[41] https://wowpedia.fandom.com/api.php?action=parse&page=Liam+Greymane&prop=text%7Crevid%7Cdisplaytitle&format=json — Liam-wowpedia-api
    > "He was killed by Sylvanas Windrunner during the Battle for Gilneas City."
[42] https://wowpedia.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category%3AAristocrats&cmlimit=500&format=json&cmcontinue=page%7C53544f524d534f4e472c204252414e4e4f4e0a4252414e4e4f4e2053544f524d534f4e47%7C564363&continue=-%7C%7C — aristocrats-api-02
    > ""title": "Lord Walden""
[43] https://wowpedia.fandom.com/api.php?action=parse&page=Tess+Greymane&prop=text%7Crevid%7Cdisplaytitle&format=json — Tess-wowpedia-api
    > "Genn & Mia (parents),
 Liam (brother),
 Archibald (grandfather)"
    > "Tess' life was saved by a potion made by Krennan Aranas; if not for him, she would have died soon after she was born.[2]"
[45] https://wowpedia.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category%3AAristocrats&cmlimit=500&format=json — Wowpedia Category:Aristocrats — MediaWiki API batch 1
    > ""ns": 0,
      "title": "Aristocrat""
[46] https://wowpedia.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category%3AGilneas+%28kingdom%29&cmlimit=500&format=json — gilneas-category — MediaWiki API
    > ""title": "Lorna Crowley""
[47] https://wowpedia.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category%3AGilneas+NPCs&cmlimit=500&format=json — gilneas-npc-category — MediaWiki API
    > ""title": "Mia Greymane""
[48] https://www.wowhead.com/ru/npc=35378/lorna-crowley — Лорна Краули
    > "# Лорна Краули"
[50] https://warcraft.wiki.gg/wiki/To_Gilneas_(Horde) — To Gilneas (Horde)
    > "I only know Tess in passing, she was very young when Gilneas left the Alliance after the Second War."
[51] https://worldofwarcraft.blizzard.com/ru-ru/media/short-story/elegy — Элегия - Галерея - World of Warcraft
    > "Королева Миа Седогрив действительно была частой гостьей в Воющем дубе — дарнасском лагере, где жили гилнеасцы. Андуин был о ней очень высокого мнения. Он согласился: вряд ли кто-то мог справиться с задачей Генна лучше, чем эта миниатюрная, волевая женщина с добрым сердцем и острым умом."
[54] https://wowpedia.fandom.com/api.php?action=parse&page=Agent+Crowley&prop=text%7Crevid%7Cdisplaytitle&format=json — Agent Crowley — Wowpedia MediaWiki API
    > "Agent Crowley could be related to other people called Crowley."
[57] https://wowpedia.fandom.com/api.php?action=parse&page=Lorna+Crowley&prop=text%7Crevid%7Cdisplaytitle&format=json — Lorna Crowley — Wowpedia MediaWiki API
    > "Lorna Crowley is the daughter of Lord Darius Crowley, one of the principal leaders during the Northgate Rebellion."
    > "The day of the worgen attack on Gilneas City, Lorna saved a worgen adventurer by shooting Josiah Avery."
[58] https://wowpedia.fandom.com/api.php?action=parse&page=Elizabeth+Crowley&prop=text%7Crevid%7Cdisplaytitle&format=json — Elizabeth Crowley — Wowpedia MediaWiki API
    > "This article contains information from the Trading Card Game which is considered non-canon."
[59] https://wowpedia.fandom.com/api.php?action=parse&page=Lieutenant+Walden&prop=text%7Crevid%7Cdisplaytitle&format=json — Lieutenant Walden — Wowpedia MediaWiki API
    > "He may be related to Lord Walden."
    > "Lieutenant Walden is a human quest giver located in Merchant Square in the worgen starting zone of Gilneas City. He was under Liam Greymane's command to help evacuate the city, but was killed by worgen during their invasion of Gilneas."
[60] https://wowpedia.fandom.com/api.php?action=parse&page=Countess+Ashmore&prop=text%7Crevid%7Cdisplaytitle&format=json — Countess Ashmore — Wowpedia MediaWiki API
    > "This article contains information and lore exclusive to Hearthstone, and is considered non-canon."
[61] https://wowpedia.fandom.com/api.php?action=parse&page=Lady+in+White&prop=text%7Crevid%7Cdisplaytitle&format=json — Lady in White — Wowpedia MediaWiki API
    > "In life, the Lady in White was a Gilnean noble woman, who saw the destruction of almost all that she loved during the fall of Gilneas."
    > "This article contains information and lore exclusive to Hearthstone, and is considered non-canon."
    > "As a ghost, she seeks to help the living restore all that was lost.[1]"
[63] https://wowpedia.fandom.com/api.php?action=parse&page=Archibald+Greymane&prop=text%7Crevid%7Cdisplaytitle&format=json — Archibald Greymane — Wowpedia family audit API
    > "Genn (son), Mia (daughter-in-law), Tess and Liam (grandchildren)"
[64] https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Ashbury+the+1st&prop=text%7Crevid%7Cdisplaytitle&format=json — Lord Ashbury the 1st — Wowpedia family audit API
    > "Lord Ashbury the 1st was a Gilnean noble and the father of Baron Ashbury."
[66] https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Candren&prop=text%7Crevid%7Cdisplaytitle&format=json — Lord Candren — Wowpedia family audit API
    > "Lord Candren is the quartermaster for Gilneas. He is found in Darnassus's Temple Gardens, near the flight master."
[68] https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Marley&prop=text%7Crevid%7Cdisplaytitle&format=json — Lord Marley — Wowpedia family audit API
    > "Lord Marley was a Gilnean noble."
[69] https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Mayor+Morrison&prop=text%7Crevid%7Cdisplaytitle&format=json — Lord Mayor Morrison — Wowpedia family audit API
    > "He may be related to Brambley Morrison and Vinnie Morrison."
[71] https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Vincent+Godfrey&prop=text%7Crevid%7Cdisplaytitle&format=json — Lord Vincent Godfrey — Wowpedia family audit API
    > "Prior to the Second War, Godfrey was among the Gilnean nobles who accompanied King Genn Greymane to Lordaeron to create the Alliance of Lordaeron."
[75] https://wowpedia.fandom.com/api.php?action=parse&page=Krennan+Aranas&prop=text%7Crevid%7Cdisplaytitle&format=json — Krennan Aranas — Wowpedia family audit API
    > "Krennan Aranas is the Royal Chemist of Gilneas. Genn notes him as one of the most powerful chemists in Azeroth, or at least Gilneas."
[76] https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Hiram+Creed&prop=text%7Crevid&format=json — Lord Hiram Creed — Wowpedia MediaWiki API
    > "Lord Hiram Creed was a black drakonid who disguises themselves as an affluent Gilnean noble."
    > "Black Prince Wrathion sent his rogue champion who sought to earn his favor to assassinate Creed in his crusade to eliminate all corrupted black dragons on Azeroth.[1] With his death, it is unknown what the fate of the Blackhowl group is."
