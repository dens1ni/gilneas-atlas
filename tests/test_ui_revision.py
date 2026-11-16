"""UI revision tracer bullets; real DOM/CSS, only app bootstrap is isolated.

Fixtures are test-only and never saved to the atlas. Run with:
/Users/daniil_si/.hermes/cache/scratch/gilneas-venv/bin/python tests/test_ui_revision.py -v
"""
import copy
import functools
import json
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-ui-revision-evidence')
ATLAS = json.loads((ROOT / 'assets/data/atlas.json').read_text())

# Frozen expectation is independent of the live atlas and never routed into
# production/bootstrap integration tests. New own objects are parent-owned.
CURRENT_ATLAS_FIXTURE = json.loads(r'''
{
  "label": "Frozen authorv6 canonical UI fixture including House Raft and the three requested ferry docks; independent expected typed ID sets",
  "locations": [
    {
      "id": "gilneas-city",
      "name": "Город Гилнеас",
      "type": "city",
      "faction": "greymane",
      "sources": [
        1,
        2,
        3,
        9,
        10
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Gilneas_City",
      "provenance": {
        "sources": [
          1,
          2,
          3,
          4
        ]
      }
    },
    {
      "id": "greymane-manor",
      "name": "Поместье Седогрива",
      "type": "estate",
      "faction": "greymane",
      "sources": [
        3,
        5
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Greymane_Manor",
      "provenance": {
        "sources": [
          5,
          4
        ]
      }
    },
    {
      "id": "cathedral-quarter",
      "name": "Соборный квартал",
      "type": "district",
      "faction": "greymane",
      "sources": [
        2,
        6,
        7
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Cathedral_Quarter",
      "provenance": {
        "sources": [
          6,
          1,
          4
        ]
      }
    },
    {
      "id": "lights-dawn-cathedral",
      "name": "Собор Рассвета",
      "type": "church",
      "faction": "gilneas",
      "sources": [
        1,
        2,
        7
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Light%27s_Dawn_Cathedral",
      "provenance": {
        "sources": [
          7,
          4
        ]
      }
    },
    {
      "id": "greymane-court",
      "name": "Площадь Седогрива",
      "type": "district",
      "faction": "greymane",
      "sources": [
        3,
        8
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Greymane_Court",
      "provenance": {
        "sources": [
          8,
          1,
          4
        ]
      }
    },
    {
      "id": "merchant-square",
      "name": "Торговая площадь",
      "type": "district",
      "faction": "greymane",
      "sources": [
        9
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Merchant_Square",
      "provenance": {
        "sources": [
          9,
          1,
          4
        ]
      }
    },
    {
      "id": "military-district",
      "name": "Военный квартал",
      "type": "district",
      "faction": "greymane",
      "sources": [
        10,
        11
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Military_District",
      "provenance": {
        "sources": [
          10,
          1,
          4
        ]
      }
    },
    {
      "id": "stoneward-prison",
      "name": "Каменная тюрьма",
      "type": "fortress",
      "faction": "gilneas",
      "sources": [
        2,
        11
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Stoneward_Prison",
      "provenance": {
        "sources": [
          11,
          4
        ]
      }
    },
    {
      "id": "keel-harbor",
      "name": "Килевая гавань",
      "type": "harbor",
      "faction": "raft",
      "sources": [
        12
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Keel_Harbor",
      "provenance": {
        "sources": [
          12,
          4
        ]
      }
    },
    {
      "id": "duskhaven",
      "name": "Темная Гавань",
      "type": "city",
      "faction": "gilneas",
      "sources": [
        3,
        13,
        14,
        17
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Duskhaven",
      "provenance": {
        "sources": [
          13,
          4
        ]
      }
    },
    {
      "id": "hayward-fishery",
      "name": "Рыбное хозяйство Хейварда",
      "type": "fishery",
      "faction": "gilneas",
      "sources": [
        16
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Hayward_Fishery",
      "provenance": {
        "sources": [
          16,
          4
        ]
      }
    },
    {
      "id": "hammond-farmstead",
      "name": "Ферма Хэммондов",
      "type": "farm",
      "faction": "gilneas",
      "sources": [
        17,
        18
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Hammond_Farmstead",
      "provenance": {
        "sources": [
          17,
          4
        ]
      }
    },
    {
      "id": "allen-farmstead",
      "name": "Ферма Аллена",
      "type": "farm",
      "faction": "gilneas",
      "sources": [
        17,
        18
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Allen_Farmstead",
      "provenance": {
        "sources": [
          18,
          4
        ]
      }
    },
    {
      "id": "emberstone-village",
      "name": "Деревня Тлеющего Угля",
      "type": "settlement",
      "faction": "gilneas",
      "sources": [
        19,
        20
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Emberstone_Village",
      "provenance": {
        "sources": [
          19,
          4
        ]
      }
    },
    {
      "id": "emberstone-mine",
      "name": "Шахта Тлеющего Угля",
      "type": "mine",
      "faction": "gilneas",
      "sources": [
        19,
        20
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Emberstone_Mine",
      "provenance": {
        "sources": [
          20,
          4
        ]
      }
    },
    {
      "id": "stormglen",
      "name": "Грозовой Перевал",
      "type": "settlement",
      "faction": "gilneas",
      "sources": [
        21,
        22
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Stormglen_Village",
      "provenance": {
        "sources": [
          21,
          22,
          4
        ]
      }
    },
    {
      "id": "blackwald",
      "name": "Черная дубрава",
      "type": "forest",
      "faction": "harvest-witches",
      "sources": [
        23,
        24,
        25
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Blackwald",
      "provenance": {
        "sources": [
          23,
          4,
          46,
          50
        ]
      }
    },
    {
      "id": "taldoren",
      "name": "Тал'дорен",
      "type": "forest",
      "faction": "harvest-witches",
      "sources": [
        1,
        24
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Tal%27doren",
      "provenance": {
        "sources": [
          24,
          4
        ]
      }
    },
    {
      "id": "bradshaw-mill",
      "name": "Мельница Брэдшоу",
      "type": "mill",
      "faction": "gilneas",
      "sources": [
        21,
        25
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Bradshaw_Mill",
      "provenance": {
        "sources": [
          25,
          4
        ]
      }
    },
    {
      "id": "tempests-reach",
      "name": "Предел бури",
      "type": "settlement",
      "faction": "walden",
      "sources": [
        26
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Tempest%27s_Reach",
      "provenance": {
        "sources": [
          26,
          4
        ]
      }
    },
    {
      "id": "aderics-repose",
      "name": "Покой Адерика",
      "type": "cemetery",
      "faction": "raft",
      "sources": [
        27
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Aderic%27s_Repose",
      "provenance": {
        "sources": [
          27,
          4
        ]
      }
    },
    {
      "id": "northgate-woods",
      "name": "Лес Северных врат",
      "type": "forest",
      "faction": "gilneas",
      "sources": [
        28
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Northgate_Woods",
      "provenance": {
        "sources": [
          28,
          4
        ]
      }
    },
    {
      "id": "northern-headlands",
      "name": "Северный каменистый мыс",
      "type": "landmark",
      "faction": "gilneas",
      "sources": [
        30,
        43,
        46
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Northern_Headlands",
      "provenance": {
        "sources": [
          30,
          4
        ]
      }
    },
    {
      "id": "the-headlands",
      "name": "Каменистый мыс",
      "type": "forest",
      "faction": "raft",
      "sources": [
        29,
        31
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Headlands",
      "provenance": {
        "sources": [
          31,
          4
        ]
      }
    },
    {
      "id": "pyrewood",
      "name": "Деревня Погребальных Костров",
      "type": "settlement",
      "faction": "crowley",
      "sources": [
        2,
        32,
        33,
        40
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Pyrewood_Village",
      "provenance": {
        "sources": [
          32,
          4
        ]
      }
    },
    {
      "id": "shadowfang",
      "name": "Крепость Пирвуд",
      "type": "fortress",
      "faction": "silverlaine",
      "sources": [
        3,
        33,
        59
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Shadowfang_Keep",
      "provenance": {
        "sources": [
          33,
          34
        ]
      }
    },
    {
      "id": "ambermill",
      "name": "Янтарная мельница",
      "type": "settlement",
      "faction": "crowley",
      "sources": [
        32,
        35
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Ambermill",
      "provenance": {
        "sources": [
          32,
          35,
          4
        ]
      }
    },
    {
      "id": "dalaran-city",
      "name": "Даларан",
      "type": "city",
      "faction": "dalaran",
      "sources": [
        36,
        37
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Dalaran",
      "provenance": {
        "sources": [
          36,
          37,
          4
        ]
      }
    },
    {
      "id": "fenris-keep",
      "name": "Крепость Фенриса",
      "type": "fortress",
      "faction": "lordaeron",
      "sources": [
        38
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Fenris_Keep",
      "provenance": {
        "sources": [
          38,
          4
        ]
      }
    },
    {
      "id": "fenris-isle",
      "name": "Остров Фенриса",
      "type": "landmark",
      "faction": "lordaeron",
      "sources": [
        38
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Fenris_Isle",
      "provenance": {
        "sources": [
          38,
          4
        ]
      }
    },
    {
      "id": "lordaeron-city",
      "name": "Столица Лордерона",
      "type": "city",
      "faction": "lordaeron",
      "sources": [
        39,
        45,
        46
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Capital_City",
      "provenance": {
        "sources": [
          39
        ]
      }
    },
    {
      "id": "silverpine",
      "name": "Серебряный бор",
      "type": "forest",
      "faction": "lordaeron",
      "sources": [
        32,
        40,
        41
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Silverpine_Forest",
      "provenance": {
        "sources": [
          40,
          32,
          4
        ]
      }
    },
    {
      "id": "lordamere-lake",
      "name": "Озеро Лордамер",
      "type": "landmark",
      "faction": null,
      "sources": [
        36,
        38,
        41
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Lordamere_Lake",
      "provenance": {
        "sources": [
          41
        ]
      }
    },
    {
      "id": "deep-elem-mine",
      "name": "Серебряный рудник",
      "type": "mine",
      "faction": "lordaeron",
      "sources": [
        40,
        42
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Deep_Elem_Mine",
      "provenance": {
        "sources": [
          42
        ]
      }
    },
    {
      "id": "galewatch-lighthouse",
      "name": "Штормовой маяк",
      "type": "lighthouse",
      "faction": "gilneas",
      "sources": [
        43
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Galewatch_Lighthouse",
      "provenance": {
        "sources": [
          43
        ]
      }
    },
    {
      "id": "violet-citadel",
      "name": "Аметистовая цитадель",
      "type": "fortress",
      "faction": "dalaran",
      "sources": [
        44
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Violet_Citadel",
      "provenance": {
        "sources": [
          44,
          36
        ]
      }
    },
    {
      "id": "location-df0aa1e2-31ba-43fa-b6b0-84c7733f625a",
      "name": "Деревня Серый Брод",
      "type": "settlement",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-ff52d2ed-f36b-4aba-8eac-7de87c8c76d7",
      "name": "Храм Владыки Глубин",
      "type": "church",
      "faction": "tidesages",
      "sources": [
        "source-lore-tidesages-wowpedia",
        "source-lore-tidesage-legends-wowpedia",
        "source-lore-kul-tiras-founding-wowpedia",
        "source-lore-kul-tiras-settlers-wowpedia"
      ],
      "provenance": {
        "sources": [
          "source-lore-tidesages-wowpedia",
          "source-lore-tidesage-legends-wowpedia",
          "source-lore-kul-tiras-founding-wowpedia",
          "source-lore-kul-tiras-settlers-wowpedia"
        ]
      }
    },
    {
      "id": "location-fb88bb30-c639-4f75-a142-92445555a772",
      "name": "Деревня Мшистые Кровли",
      "type": "settlement",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-4f29a377-1080-4a49-b400-026ff4c7c589",
      "name": "Ипподром",
      "type": "stable",
      "faction": "walden",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-9020653f-e319-4959-854d-9669422e14cc",
      "name": "Поместье Дома Вальден",
      "type": "estate",
      "faction": "walden",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-e8c8f59c-83ac-49ff-819f-9708a9734ff1",
      "name": "Маяк Звёздного Порядка",
      "type": "lighthouse",
      "faction": "walden",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-52d50172-b218-4b6b-be09-eccd9fb419ce",
      "name": "Поместье Дома Эшбери",
      "type": "estate",
      "faction": "ashbury",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-b415ddf5-f12a-4421-829f-e8723bdaa1d4",
      "name": "Кладбище Черной Дубравы",
      "type": "cemetery",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-a4bf5eb0-1154-4519-9400-f17ced83a1d9",
      "name": "Дом смотрителя кладбища",
      "type": "building",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-75988492-6f32-4e29-9058-ef9d73e1746d",
      "name": "Дом травника",
      "type": "building",
      "faction": "harvest-witches",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-5187131a-bb77-4e98-948d-ddd4247781f2",
      "name": "Туманные Топи",
      "type": "landmark",
      "faction": "harvest-witches",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-8288bc4e-bb08-45d9-ace3-bc878fe7e8ba",
      "name": "Дом егеря",
      "type": "building",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-54cebe0e-8a63-43c7-86d2-b85f6edf2732",
      "name": "Дом егеря",
      "type": "building",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-544521a1-babb-4fea-af73-6ebb91c476e0",
      "name": "Дом смотрителя",
      "type": "building",
      "faction": "raft",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-8ee04e39-6c00-4b0b-9bcf-17de4fddb9bb",
      "name": "Церковь Темной Гавани",
      "type": "church",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-3325cfda-47a7-4e3d-9cac-3797f4dbaa9d",
      "name": "Маяк Темной Гавани",
      "type": "lighthouse",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-17511ea5-f77c-4d83-a187-ee2da7acbf21",
      "name": "Лечебница Тихий Холм",
      "type": "hospital",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-426acd7a-5f00-48c0-a6aa-1de9ce3ac2fc",
      "name": "Портовый район",
      "type": "harbor",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-ecbf79ff-610a-4bde-8d16-a437954ed7a4",
      "name": "Казарма стражи",
      "type": "barracks",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-f2adc0b4-c081-404a-a546-16ca52d028aa",
      "name": "Городской рынок",
      "type": "market",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-94b0bb4b-f058-4b9d-9ec3-eb3fdb02b21f",
      "name": "Городская ратуша",
      "type": "building",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-3cfcf216-6753-4b1a-bd43-3adc40bd96f0",
      "name": "Паб Медный Пес",
      "type": "inn",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-18f52fa5-7ee8-467f-81a1-d8d8ec11929f",
      "name": "Алкогольная мануфактура",
      "type": "workshop",
      "faction": "evermont",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-76bf7c1a-fcd2-4dfc-9013-26b909b4732f",
      "name": "Поместье Дома Эвермонт",
      "type": "estate",
      "faction": "evermont",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-60382f79-7237-4492-a95b-749b4f290d9b",
      "name": "Поместье Краули",
      "type": "estate",
      "faction": "crowley",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-883f0f53-ba1a-44a5-bd8e-60b2d5d8cc22",
      "name": "Дом для прислуги",
      "type": "building",
      "faction": "crowley",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-ea37cf4e-63d7-48d1-bb38-c5a465f16f3a",
      "name": "Конюшни Краули",
      "type": "stable",
      "faction": "crowley",
      "provenance": {
        "sources": [
          15,
          "family-source-3",
          14
        ]
      },
      "sources": [
        15,
        "family-source-3",
        14
      ],
      "wowpediaUrl": "https://wowpedia.fandom.com/wiki/Crowley_Stable_Grounds"
    },
    {
      "id": "location-6f6350b7-e0d4-49f0-b333-a807c0003842",
      "name": "Конюшни поместья Эвермонт",
      "type": "stable",
      "faction": "evermont",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-d62d4e06-bb2d-48dc-8f59-fcbe0641f652",
      "name": "Псарня поместья Эвермонт",
      "type": "building",
      "faction": "evermont",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-d3cda392-00e2-4afd-8cb4-09e8330221a6",
      "name": "Домик прислуги поместья Эвермонт",
      "type": "building",
      "faction": "evermont",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-6e3bbad5-4890-4ae0-b8cc-1a3fa97535a4",
      "name": "Постоялый двор",
      "type": "inn",
      "faction": null,
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "ambermill-town-hall",
      "name": "Ратуша Янтарной мельницы",
      "type": "building",
      "faction": "crowley",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "ambermill-westbank-farm",
      "name": "Ферма Янтарный Колос",
      "type": "farm",
      "faction": "crowley",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "ambermill-firrow-farm",
      "name": "Ферма Вересковый Двор",
      "type": "farm",
      "faction": "crowley",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "ambermill-moorfield-farm",
      "name": "Ферма Тёплая Борозда",
      "type": "farm",
      "faction": "crowley",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-raft-estate",
      "name": "Поместье Дома Рафт",
      "type": "estate",
      "faction": "raft",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "ferry-duskhaven",
      "name": "Паромщик Темной Гавани",
      "type": "ferry",
      "faction": "gilneas",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "ferry-keel-harbor",
      "name": "Паромщик Килевой гавани",
      "type": "ferry",
      "faction": "raft",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "ferry-stormglen",
      "name": "Паромщик под Грозовым Перевалом",
      "type": "ferry",
      "faction": "gilneas",
      "provenance": {
        "sources": []
      }
    },
    {
      "id": "location-gray-ford-godfrey-estate",
      "name": "Поместье Годфри у Серого Брода",
      "type": "estate",
      "faction": "godfrey",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "conditionBasis": "user described one intact and two burned houses on the supplied raster",
          "placement": "visual original-raster anchor; not measured world coordinates",
          "ownership": {
            "basis": "explicit-user-authorized-scenario-inference",
            "canonicalEarlyCadastre": false
          }
        },
        "sources": []
      }
    },
    {
      "id": "location-gray-ford-north-burned-house",
      "name": "Северное пепелище Серого Брода",
      "type": "building",
      "faction": "godfrey",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "conditionBasis": "user described one intact and two burned houses on the supplied raster",
          "placement": "visual original-raster anchor; not measured world coordinates",
          "ownership": {
            "basis": "explicit-user-authorized-scenario-inference",
            "canonicalEarlyCadastre": false
          }
        },
        "sources": []
      }
    },
    {
      "id": "location-gray-ford-east-burned-house",
      "name": "Восточное пепелище Серого Брода",
      "type": "building",
      "faction": "godfrey",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "conditionBasis": "user described one intact and two burned houses on the supplied raster",
          "placement": "visual original-raster anchor; not measured world coordinates",
          "ownership": {
            "basis": "explicit-user-authorized-scenario-inference",
            "canonicalEarlyCadastre": false
          }
        },
        "sources": []
      }
    },
    {
      "id": "location-merchant-cloth-shop",
      "name": "Лавка суконщика «Серый Бархат»",
      "type": "market",
      "faction": "greymane",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "placement": "existing building roof or garden in the supplied raster; use is scenario-authored"
        },
        "sources": []
      }
    },
    {
      "id": "location-merchant-herbal-shop",
      "name": "Травная лавка «Вереск и Воск»",
      "type": "market",
      "faction": "greymane",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "placement": "existing building roof or garden in the supplied raster; use is scenario-authored"
        },
        "sources": []
      }
    },
    {
      "id": "location-merchant-ironware-shop",
      "name": "Скобяная лавка «Медный Ключ»",
      "type": "market",
      "faction": "greymane",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "placement": "existing building roof or garden in the supplied raster; use is scenario-authored"
        },
        "sources": []
      }
    },
    {
      "id": "location-military-forge",
      "name": "Кузница «Королевская Искра»",
      "type": "forge",
      "faction": "greymane",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "placement": "existing building roof or garden in the supplied raster; use is scenario-authored"
        },
        "sources": []
      }
    },
    {
      "id": "location-military-barracks",
      "name": "Казармы «Каменный Караул»",
      "type": "barracks",
      "faction": "greymane",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "placement": "existing building roof or garden in the supplied raster; use is scenario-authored"
        },
        "sources": []
      }
    },
    {
      "id": "location-greymane-record-office",
      "name": "Палата городских книг",
      "type": "building",
      "faction": "greymane",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "placement": "existing building roof or garden in the supplied raster; use is scenario-authored"
        },
        "sources": []
      }
    },
    {
      "id": "location-greymane-post-office",
      "name": "Дом королевской почты",
      "type": "building",
      "faction": "greymane",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "placement": "existing building roof or garden in the supplied raster; use is scenario-authored"
        },
        "sources": []
      }
    },
    {
      "id": "location-cathedral-rose-park",
      "name": "Парк «Тихие Розы»",
      "type": "garden",
      "faction": "greymane",
      "provenance": {
        "confidence": "custom",
        "authorScenario": {
          "basis": "explicit-user-authorship",
          "canonicalEvidence": false,
          "placement": "existing building roof or garden in the supplied raster; use is scenario-authored"
        },
        "sources": []
      }
    }
  ],
  "factions": [
    {
      "id": "gilneas",
      "parent": null
    },
    {
      "id": "greymane",
      "parent": "gilneas"
    },
    {
      "id": "crowley",
      "parent": "gilneas"
    },
    {
      "id": "silverlaine",
      "parent": "crowley"
    },
    {
      "id": "godfrey",
      "parent": "gilneas"
    },
    {
      "id": "ashbury",
      "parent": "gilneas"
    },
    {
      "id": "marley",
      "parent": "gilneas"
    },
    {
      "id": "walden",
      "parent": "gilneas"
    },
    {
      "id": "dalaran",
      "parent": null
    },
    {
      "id": "lordaeron",
      "parent": null
    },
    {
      "id": "evermont",
      "parent": "gilneas"
    },
    {
      "id": "harvest-witches",
      "parent": "gilneas"
    },
    {
      "id": "tidesages",
      "parent": "gilneas"
    },
    {
      "id": "raft",
      "parent": "gilneas"
    }
  ],
  "nobles": [
    {
      "id": "noble-genn"
    },
    {
      "id": "noble-darius"
    },
    {
      "id": "noble-godfrey"
    },
    {
      "id": "noble-ashbury"
    },
    {
      "id": "noble-marley"
    },
    {
      "id": "noble-archibald"
    },
    {
      "id": "noble-ashbury-first"
    },
    {
      "id": "noble-walden"
    },
    {
      "id": "noble-hewell"
    },
    {
      "id": "noble-silverlaine"
    },
    {
      "id": "noble-longshore"
    },
    {
      "id": "noble-candren"
    },
    {
      "id": "noble-isiden"
    },
    {
      "id": "noble-tulvan"
    },
    {
      "id": "noble-harford"
    },
    {
      "id": "noble-morrison"
    },
    {
      "id": "noble-aderic"
    },
    {
      "id": "noble-mia"
    },
    {
      "id": "noble-liam"
    },
    {
      "id": "noble-tess"
    },
    {
      "id": "noble-lorna"
    },
    {
      "id": "noble-hiram-creed"
    },
    {
      "id": "noble-woofington"
    },
    {
      "id": "noble-alys-finnsson"
    },
    {
      "id": "noble-ashmore"
    },
    {
      "id": "noble-lady-in-white"
    }
  ],
  "sources": [
    {
      "id": 1,
      "url": "https://wowpedia.fandom.com/wiki/Gilneas_City",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Gilneas_City"
    },
    {
      "id": 2,
      "url": "https://wowpedia.fandom.com/wiki/Gilneas_(kingdom)?action=render",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Gilneas_(kingdom)"
    },
    {
      "id": 3,
      "url": "https://wowpedia.fandom.com/wiki/Nobles_of_Gilneas",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Nobles_of_Gilneas"
    },
    {
      "id": 4,
      "url": "https://wago.tools/db2/AreaTable/csv?build=4.4.2.60895&locale=ruRU",
      "canonicalUrl": "https://wago.tools/db2/AreaTable/csv?build=4.4.2.60895&locale=ruRU"
    },
    {
      "id": 5,
      "url": "https://wowpedia.fandom.com/wiki/Greymane_Manor",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Greymane_Manor"
    },
    {
      "id": 6,
      "url": "https://wowpedia.fandom.com/wiki/Cathedral_Quarter",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Cathedral_Quarter"
    },
    {
      "id": 7,
      "url": "https://wowpedia.fandom.com/wiki/Light%27s_Dawn_Cathedral",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Light%27s_Dawn_Cathedral"
    },
    {
      "id": 8,
      "url": "https://warcraft.wiki.gg/wiki/Greymane_Court",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Greymane_Court"
    },
    {
      "id": 9,
      "url": "https://warcraft.wiki.gg/wiki/Merchant_Square",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Merchant_Square"
    },
    {
      "id": 10,
      "url": "https://warcraft.wiki.gg/wiki/Military_District",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Military_District"
    },
    {
      "id": 11,
      "url": "https://warcraft.wiki.gg/wiki/Stoneward_Prison",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Stoneward_Prison"
    },
    {
      "id": 12,
      "url": "https://wowpedia.fandom.com/wiki/Keel_Harbor",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Keel_Harbor"
    },
    {
      "id": 13,
      "url": "https://wowpedia.fandom.com/wiki/Duskhaven",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Duskhaven"
    },
    {
      "id": 14,
      "url": "https://wowpedia.fandom.com/wiki/Crowley_Orchard",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Crowley_Orchard"
    },
    {
      "id": 15,
      "url": "https://wowpedia.fandom.com/wiki/Crowley_Stable_Grounds",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Crowley_Stable_Grounds"
    },
    {
      "id": 16,
      "url": "https://wowpedia.fandom.com/wiki/Hayward_Fishery",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Hayward_Fishery"
    },
    {
      "id": 17,
      "url": "https://wowpedia.fandom.com/wiki/Hammond_Farmstead",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Hammond_Farmstead"
    },
    {
      "id": 18,
      "url": "https://wowpedia.fandom.com/wiki/Allen_Farmstead",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Allen_Farmstead"
    },
    {
      "id": 19,
      "url": "https://wowpedia.fandom.com/wiki/Emberstone_Village",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Emberstone_Village"
    },
    {
      "id": 20,
      "url": "https://wowpedia.fandom.com/wiki/Emberstone_Mine",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Emberstone_Mine"
    },
    {
      "id": 21,
      "url": "https://wowpedia.fandom.com/wiki/Stormglen_Village",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Stormglen_Village"
    },
    {
      "id": 22,
      "url": "https://www.wowhead.com/ru/quest=24483/%D0%B3%D1%80%D0%BE%D0%B7%D0%BE%D0%B2%D0%BE%D0%B9-%D0%BF%D0%B5%D1%80%D0%B5%D0%B2%D0%B0%D0%BB",
      "canonicalUrl": "https://www.wowhead.com/ru/quest=24483/%D0%B3%D1%80%D0%BE%D0%B7%D0%BE%D0%B2%D0%BE%D0%B9-%D0%BF%D0%B5%D1%80%D0%B5%D0%B2%D0%B0%D0%BB"
    },
    {
      "id": 23,
      "url": "https://wowpedia.fandom.com/wiki/Blackwald",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Blackwald"
    },
    {
      "id": 24,
      "url": "https://wowpedia.fandom.com/wiki/Tal%27doren",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Tal%27doren"
    },
    {
      "id": 25,
      "url": "https://wowpedia.fandom.com/wiki/Bradshaw_Mill",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Bradshaw_Mill"
    },
    {
      "id": 26,
      "url": "https://wowpedia.fandom.com/wiki/Tempest%27s_Reach",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Tempest%27s_Reach"
    },
    {
      "id": 27,
      "url": "https://wowpedia.fandom.com/wiki/Aderic%27s_Repose",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Aderic%27s_Repose"
    },
    {
      "id": 28,
      "url": "https://wowpedia.fandom.com/wiki/Northgate_Woods",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Northgate_Woods"
    },
    {
      "id": 29,
      "url": "https://warcraft.wiki.gg/wiki/Northgate_River",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Northgate_River"
    },
    {
      "id": 30,
      "url": "https://wowpedia.fandom.com/wiki/Northern_Headlands",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Northern_Headlands"
    },
    {
      "id": 31,
      "url": "https://wowpedia.fandom.com/wiki/Headlands",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Headlands"
    },
    {
      "id": 32,
      "url": "https://wowpedia.fandom.com/wiki/Darius_Crowley",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Darius_Crowley"
    },
    {
      "id": 33,
      "url": "https://wowpedia.fandom.com/wiki/Shadowfang_Keep",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Shadowfang_Keep"
    },
    {
      "id": 34,
      "url": "https://warcraft.wiki.gg/wiki/Shadowfang_Keep",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Shadowfang_Keep"
    },
    {
      "id": 35,
      "url": "https://wowpedia.fandom.com/wiki/Ambermill",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Ambermill"
    },
    {
      "id": 36,
      "url": "https://wowpedia.fandom.com/wiki/Dalaran_(kingdom)?action=render",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Dalaran_(kingdom)"
    },
    {
      "id": 37,
      "url": "https://wowpedia.fandom.com/wiki/Antonidas",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Antonidas"
    },
    {
      "id": 38,
      "url": "https://wowpedia.fandom.com/wiki/Fenris_Isle",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Fenris_Isle"
    },
    {
      "id": 39,
      "url": "https://wowpedia.fandom.com/wiki/Capital_City",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Capital_City"
    },
    {
      "id": 40,
      "url": "https://wowpedia.fandom.com/wiki/Silverpine_Forest",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Silverpine_Forest"
    },
    {
      "id": 41,
      "url": "https://wowpedia.fandom.com/wiki/Lordamere_Lake",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lordamere_Lake"
    },
    {
      "id": 42,
      "url": "https://wowpedia.fandom.com/wiki/Deep_Elem_Mine",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Deep_Elem_Mine"
    },
    {
      "id": 43,
      "url": "https://wowpedia.fandom.com/wiki/Galewatch_Lighthouse",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Galewatch_Lighthouse"
    },
    {
      "id": 44,
      "url": "https://wowpedia.fandom.com/wiki/Violet_Citadel",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Violet_Citadel"
    },
    {
      "id": 45,
      "url": "https://wowpedia.fandom.com/wiki/Genn_Greymane",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Genn_Greymane"
    },
    {
      "id": 46,
      "url": "https://worldofwarcraft.blizzard.com/en-us/media/short-story/genn-greymane-lord-of-his-pack",
      "canonicalUrl": "https://worldofwarcraft.blizzard.com/en-us/media/short-story/genn-greymane-lord-of-his-pack"
    },
    {
      "id": 47,
      "url": "https://wowpedia.fandom.com/wiki/Greymane_family",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Greymane_family"
    },
    {
      "id": 48,
      "url": "https://worldofwarcraft.blizzard.com/ru-ru/media/short-story/genn-greymane-lord-of-his-pack",
      "canonicalUrl": "https://worldofwarcraft.blizzard.com/ru-ru/media/short-story/genn-greymane-lord-of-his-pack"
    },
    {
      "id": 49,
      "url": "https://wowpedia.fandom.com/wiki/Lord_Vincent_Godfrey",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Vincent_Godfrey"
    },
    {
      "id": 50,
      "url": "https://wowpedia.fandom.com/wiki/Baron_Ashbury",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Baron_Ashbury"
    },
    {
      "id": 51,
      "url": "https://wowpedia.fandom.com/wiki/Betrayal_at_Tempest%27s_Reach",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Betrayal_at_Tempest%27s_Reach"
    },
    {
      "id": 52,
      "url": "https://wowpedia.fandom.com/wiki/Lord_Marley?mobileaction=toggle_view_mobile",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Marley"
    },
    {
      "id": 53,
      "url": "https://wowpedia.fandom.com/wiki/Archibald_Greymane",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Archibald_Greymane"
    },
    {
      "id": 54,
      "url": "https://warcraft.wiki.gg/wiki/Lord_Ashbury_the_1st",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Ashbury_the_1st"
    },
    {
      "id": 55,
      "url": "https://wowpedia.fandom.com/wiki/Lord_Walden",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Walden"
    },
    {
      "id": 56,
      "url": "https://warcraft.wiki.gg/wiki/Leader_of_the_Pack_(quest)",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Leader_of_the_Pack_(quest)"
    },
    {
      "id": 57,
      "url": "https://wowpedia.fandom.com/wiki/Lord_Hewell",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Hewell"
    },
    {
      "id": 58,
      "url": "https://www.wowhead.com/ru/quest=24677/%D0%B0%D1%82%D0%B0%D0%BA%D0%B0-%D1%81-%D1%84%D0%BB%D0%B0%D0%BD%D0%B3%D0%B0",
      "canonicalUrl": "https://www.wowhead.com/ru/quest=24677/%D0%B0%D1%82%D0%B0%D0%BA%D0%B0-%D1%81-%D1%84%D0%BB%D0%B0%D0%BD%D0%B3%D0%B0"
    },
    {
      "id": 59,
      "url": "https://wowpedia.fandom.com/wiki/Baron_Silverlaine",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Baron_Silverlaine"
    },
    {
      "id": 60,
      "url": "https://worldofwarcraft.blizzard.com/en-us/news/24095666/unveiling-cataclysm-classic-zones-dungeons-and-pvp-season-9",
      "canonicalUrl": "https://worldofwarcraft.blizzard.com/en-us/news/24095666/unveiling-cataclysm-classic-zones-dungeons-and-pvp-season-9"
    },
    {
      "id": 61,
      "url": "https://wowpedia.fandom.com/wiki/Baron_Longshore",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Baron_Longshore"
    },
    {
      "id": 62,
      "url": "https://wowpedia.fandom.com/wiki/The_Baron%27s_Demands",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/The_Baron%27s_Demands"
    },
    {
      "id": 63,
      "url": "https://wowpedia.fandom.com/wiki/Lord_Candren",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Candren"
    },
    {
      "id": 64,
      "url": "https://wowpedia.fandom.com/wiki/Isiden_Perenolde",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Isiden_Perenolde"
    },
    {
      "id": 65,
      "url": "https://wowpedia.fandom.com/wiki/Lord_Geoffery_Tulvan?action=render",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Geoffery_Tulvan?action=render"
    },
    {
      "id": 66,
      "url": "https://wowpedia.fandom.com/wiki/Lord_Harford?action=render",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Harford?action=render"
    },
    {
      "id": 67,
      "url": "https://wowpedia.fandom.com/wiki/Lord_Mayor_Morrison?action=render",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Mayor_Morrison?action=render"
    },
    {
      "id": 68,
      "url": "https://wowpedia.fandom.com/wiki/Aderic?action=render",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Aderic?action=render"
    },
    {
      "id": 69,
      "url": "https://wowpedia.fandom.com/wiki/File:Gineas.jpg?action=render",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/File:Gineas.jpg"
    },
    {
      "id": "court-source-8",
      "url": "https://wowpedia.fandom.com/wiki/Lord_Marley"
    },
    {
      "id": "court-source-20",
      "url": "https://warcraft.wiki.gg/wiki/Lord_Geoffery_Tulvan",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Geoffery_Tulvan"
    },
    {
      "id": "court-source-21",
      "url": "https://warcraft.wiki.gg/wiki/Lord_Harford",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Harford"
    },
    {
      "id": "court-source-22",
      "url": "https://warcraft.wiki.gg/wiki/Lord_Mayor_Morrison",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Mayor_Morrison"
    },
    {
      "id": "court-source-23",
      "url": "https://warcraft.wiki.gg/wiki/Aderic",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Aderic"
    },
    {
      "id": "court-source-24",
      "url": "https://wowpedia.fandom.com/wiki/Lord_Geoffery_Tulvan"
    },
    {
      "id": "court-source-25",
      "url": "https://wowpedia.fandom.com/wiki/Lord_Harford"
    },
    {
      "id": "court-source-26",
      "url": "https://wowpedia.fandom.com/wiki/Lord_Mayor_Morrison"
    },
    {
      "id": "court-source-27",
      "url": "https://wowpedia.fandom.com/wiki/Aderic"
    },
    {
      "id": "court-source-29",
      "url": "http://media.blizzard.com/wow/lore/pdfdownload/leader-story/genn-greymane/greymane-enUS.pdf"
    },
    {
      "id": "court-source-30",
      "url": "https://wowpedia.fandom.com/wiki/Lord_Ashbury_the_1st?action=render"
    },
    {
      "id": "noble-life-source-1",
      "url": "https://warcraft.wiki.gg/wiki/Patriarch%27s_Blessing",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Patriarch%27s_Blessing"
    },
    {
      "id": "noble-life-source-2",
      "url": "https://wowpedia.fandom.com/wiki/Innkeeper",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Innkeeper"
    },
    {
      "id": "noble-life-source-3",
      "url": "https://www.engadget.com/2010-12-15-know-your-lore-shadowfang-keep.html",
      "canonicalUrl": "https://www.engadget.com/2010-12-15-know-your-lore-shadowfang-keep.html"
    },
    {
      "id": "family-source-1",
      "url": "https://wowpedia.fandom.com/wiki/Nobles_of_Gilneas"
    },
    {
      "id": "family-source-2",
      "url": "https://wowpedia.fandom.com/wiki/Greymane_family"
    },
    {
      "id": "family-source-3",
      "url": "https://wowpedia.fandom.com/wiki/Crowley"
    },
    {
      "id": "family-source-4",
      "url": "https://wowpedia.fandom.com/wiki/Mia_Greymane"
    },
    {
      "id": "family-source-5",
      "url": "https://wowpedia.fandom.com/wiki/Liam_Greymane"
    },
    {
      "id": "family-source-8",
      "url": "https://worldofwarcraft.blizzard.com/en-us/media/short-story/genn-greymane-lord-of-his-pack"
    },
    {
      "id": "family-source-9",
      "url": "https://worldofwarcraft.blizzard.com/ru-ru/media/short-story/genn-greymane-lord-of-his-pack"
    },
    {
      "id": "family-source-15",
      "url": "https://wowpedia.fandom.com/wiki/Countess_Ashmore"
    },
    {
      "id": "family-source-16",
      "url": "https://warcraft.wiki.gg/wiki/Tess_Greymane"
    },
    {
      "id": "family-source-17",
      "url": "https://warcraft.wiki.gg/wiki/Liam_Greymane"
    },
    {
      "id": "family-source-18",
      "url": "https://warcraft.wiki.gg/wiki/Lorna_Crowley"
    },
    {
      "id": "family-source-19",
      "url": "https://wowpedia.fandom.com/wiki/Dame_Alys_Finnsson?so=search",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Dame_Alys_Finnsson"
    },
    {
      "id": "family-source-20",
      "url": "https://wowpedia.fandom.com/wiki/Lord_Woofington?so=search",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Woofington"
    },
    {
      "id": "family-source-23",
      "url": "https://web.archive.org/web/20251118114028/https://wowpedia.fandom.com/wiki/Lord_Woofington",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Woofington"
    },
    {
      "id": "family-source-26",
      "url": "https://wowpedia.fandom.com/wiki/Baron_Silverlaine"
    },
    {
      "id": "family-source-28",
      "url": "https://wowpedia.fandom.com/wiki/Magistrate_Henry_Maleb"
    },
    {
      "id": "family-source-29",
      "url": "https://wowpedia.fandom.com/wiki/Gilneas_Nobleman"
    },
    {
      "id": "family-source-40",
      "url": "https://wowpedia.fandom.com/wiki/Isiden_Perenolde"
    },
    {
      "id": "family-source-41",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Liam+Greymane&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Liam_Greymane"
    },
    {
      "id": "family-source-42",
      "url": "https://wowpedia.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category%3AAristocrats&cmlimit=500&format=json&cmcontinue=page%7C53544f524d534f4e472c204252414e4e4f4e0a4252414e4e4f4e2053544f524d534f4e47%7C564363&continue=-%7C%7C"
    },
    {
      "id": "family-source-43",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Tess+Greymane&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Tess_Greymane"
    },
    {
      "id": "family-source-45",
      "url": "https://wowpedia.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category%3AAristocrats&cmlimit=500&format=json"
    },
    {
      "id": "family-source-46",
      "url": "https://wowpedia.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category%3AGilneas+%28kingdom%29&cmlimit=500&format=json"
    },
    {
      "id": "family-source-47",
      "url": "https://wowpedia.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category%3AGilneas+NPCs&cmlimit=500&format=json"
    },
    {
      "id": "family-source-48",
      "url": "https://www.wowhead.com/ru/npc=35378/lorna-crowley"
    },
    {
      "id": "family-source-50",
      "url": "https://warcraft.wiki.gg/wiki/To_Gilneas_(Horde)"
    },
    {
      "id": "family-source-51",
      "url": "https://worldofwarcraft.blizzard.com/ru-ru/media/short-story/elegy"
    },
    {
      "id": "family-source-54",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Agent+Crowley&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Agent_Crowley"
    },
    {
      "id": "family-source-57",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lorna+Crowley&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lorna_Crowley"
    },
    {
      "id": "family-source-58",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Elizabeth+Crowley&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Elizabeth_Crowley"
    },
    {
      "id": "family-source-59",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lieutenant+Walden&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lieutenant_Walden"
    },
    {
      "id": "family-source-60",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Countess+Ashmore&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Countess_Ashmore"
    },
    {
      "id": "family-source-61",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lady+in+White&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lady_in_White"
    },
    {
      "id": "family-source-63",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Archibald+Greymane&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Archibald_Greymane"
    },
    {
      "id": "family-source-64",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Ashbury+the+1st&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Ashbury_the_1st"
    },
    {
      "id": "family-source-66",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Candren&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Candren"
    },
    {
      "id": "family-source-68",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Marley&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Marley"
    },
    {
      "id": "family-source-69",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Mayor+Morrison&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Mayor_Morrison"
    },
    {
      "id": "family-source-71",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Vincent+Godfrey&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Vincent_Godfrey"
    },
    {
      "id": "family-source-75",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Krennan+Aranas&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Krennan_Aranas"
    },
    {
      "id": "family-source-76",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Hiram+Creed&prop=text%7Crevid&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Hiram_Creed"
    },
    {
      "id": "source-lore-harvest-witches-wowpedia",
      "url": "https://wowpedia.fandom.com/wiki/Harvest-witch",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Harvest-witch"
    },
    {
      "id": "source-lore-kul-tiras-founding-wowpedia",
      "url": "https://wowpedia.fandom.com/wiki/Kul_Tiras_(kingdom)",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Kul_Tiras_(kingdom)"
    },
    {
      "id": "source-lore-tides-blessing-wowpedia",
      "url": "https://wowpedia.fandom.com/wiki/Blessing_of_the_Tides",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Blessing_of_the_Tides"
    },
    {
      "id": "source-lore-walden-wowpedia-api",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Lord+Walden&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Lord_Walden"
    },
    {
      "id": "source-lore-walden-house-wowpedia-api",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Leader+of+the+Pack+%28quest%29&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Leader_of_the_Pack_(quest)"
    },
    {
      "id": "source-lore-tidesages-wowpedia",
      "url": "https://wowpedia.fandom.com/wiki/Tidesages",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Tidesages"
    },
    {
      "id": "source-lore-tidesage-legends-wowpedia",
      "url": "https://wowpedia.fandom.com/wiki/Legends_of_the_Tidesages",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Legends_of_the_Tidesages"
    },
    {
      "id": "source-lore-kul-tiras-settlers-wowpedia",
      "url": "https://wowpedia.fandom.com/wiki/Kul_Tiras",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Kul_Tiras"
    },
    {
      "id": "source-lore-cdev3-blizzplanet",
      "url": "https://www.blizzplanet.com/blog/comments/ask-creative-development-round-iii",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Ask_CDev"
    },
    {
      "id": "source-lore-harvest-witches-warcraftwiki",
      "url": "https://warcraft.wiki.gg/wiki/Harvest-witch",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Harvest-witch"
    },
    {
      "id": "source-lore-harvest-famine-wowpedia-api",
      "url": "https://wowpedia.fandom.com/api.php?action=parse&page=Moonfire+%28worgen%29&prop=text%7Crevid%7Cdisplaytitle&format=json",
      "canonicalUrl": "https://wowpedia.fandom.com/wiki/Moonfire_(worgen)"
    }
  ]
}
''')
EXPECTED_LOCATION_IDS = tuple(row['id'] for row in CURRENT_ATLAS_FIXTURE['locations'])
EXPECTED_LOCATIONS = {row['id']: row for row in CURRENT_ATLAS_FIXTURE['locations']}
AUTHOR_SEED = json.loads((Path(__file__).resolve().parents[1] / 'assets/data/publication-author-v5.json').read_text())


def typed_id(value):
    return (type(value).__name__, value)


def assert_current_canonical_collections(case, snapshot):
    for collection in ('locations', 'factions', 'nobles', 'sources'):
        expected = [typed_id(row['id']) for row in CURRENT_ATLAS_FIXTURE[collection]]
        actual = [typed_id(row['id']) for row in snapshot[collection]]
        case.assertEqual(len(actual), len(expected), collection)
        case.assertEqual(sorted(actual), sorted(expected), collection + ' exact typed canonical IDs')
        case.assertEqual(len(set(actual)), len(actual), collection + ' unique IDs')
    # All original source records, including types, quotes and extras, survive.
    case.assertEqual(snapshot['sources'][:len(AUTHOR_SEED['sources'])], AUTHOR_SEED['sources'])


def expected_citations(record):
    """Exact available canonical evidence, with no fallback/synthetic source."""
    ledger = {typed_id(source['id']): (index, source)
              for index, source in enumerate(CURRENT_ATLAS_FIXTURE['sources'], 1)}
    seen = set()
    result = []
    for source_id in [*record.get('provenance', {}).get('sources', []), *record.get('sources', [])]:
        key = typed_id(source_id)
        if key in seen:
            continue
        seen.add(key)
        if key not in ledger:
            continue  # Missing author references legitimately have no citation.
        index, source = ledger[key]
        href = next((source[k] for k in ('url', 'canonicalUrl')
                     if isinstance(source.get(k), str) and source[k].lower().startswith(('http://', 'https://'))), None)
        number = source_id if type(source_id) is int else index
        result.append({'id': str(source_id), 'href': href, 'number': number})
    return result
FIXTURE = {
    'version': 1,
    'meta': {'width': 3247, 'height': 4860,
             'image': 'assets/maps/gilneas-enhanced.webp',
             'mist': 'assets/maps/inactive-mist.webp', 'labels': []},
    'factions': [
        {'id': 'gilneas', 'name': 'Тестовое королевство Гилнеас', 'color': '#a74657', 'parent': None},
        {'id': 'test-house', 'name': 'Тестовый старший дом', 'color': '#639096', 'parent': 'gilneas'},
        {'id': 'test-vassal', 'name': 'Тестовый младший дом', 'color': '#93a798', 'parent': 'test-house'},
        {'id': 'test-other', 'name': 'Тестовая иная держава', 'color': '#aa85c4', 'parent': None},
        {'id': 'test-empty', 'name': 'Тестовый пустой дом', 'color': '#7592b2', 'parent': 'gilneas'},
    ],
    'locations': [
        {'id': 'test-crown-place', 'name': 'Тестовая столица', 'type': 'city', 'faction': 'gilneas',
         'x': 1800, 'y': 3400, 'capital': True, 'owner': '',
         'description': 'Тестовое первое предложение. Тестовое второе предложение.', 'objects': []},
        {'id': 'test-house-place', 'name': 'Тестовое поместье', 'type': 'estate', 'faction': 'test-house',
         'x': 1950, 'y': 3200, 'owner': 'Тестовый владелец',
         'description': 'Тестовая земля.', 'provenance': {'confidence': 'reconstruction'}, 'objects': []},
        {'id': 'test-vassal-place', 'name': 'Тестовый младший удел', 'type': 'fortress', 'faction': 'test-vassal',
         'x': 1550, 'y': 3600, 'owner': '', 'description': 'Тестовый удел.', 'objects': []},
        {'id': 'test-other-place', 'name': 'Тестовый другой город', 'type': 'city', 'faction': 'test-other',
         'x': 2300, 'y': 2200, 'owner': '', 'description': '', 'objects': []},
    ],
    'territories': [{'id': 'test-territory', 'faction': 'test-house',
                     'points': [[1700, 3000], [2100, 3000], [2100, 3300], [1700, 3300]]}],
    'nobles': [{'id': 'test-noble', 'name': 'Тестовый дворянин', 'title': 'Тестовый титул', 'house': 'test-house'}],
    'sources': [],
}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class UIRevisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=[
            '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
        ])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.page = self.context.new_page()
        self.page.set_default_timeout(3000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
            status=200, content_type='application/javascript', body='// Test-only bootstrap seam.'))

    def tearDown(self):
        self.context.close()

    def boot(self, fixture=None, remove_reconstruction_control=False, delegate_territories=False):
        snapshot = copy.deepcopy(fixture if fixture is not None else FIXTURE)
        # Labelled, full test-only snapshot route, installed before initial boot.
        self.page.route('**/assets/data/atlas.json', lambda route: route.fulfill(
            status=200, content_type='application/json', body=json.dumps(snapshot)))
        self.page.goto(self.url + '/index.html', wait_until='networkidle')
        self.page.evaluate("""async options => {
            document.body.classList.add('edit-mode');
            if (options.removeControl) {
                const control = document.querySelector('#show-reconstructions');
                (control?.closest('label') || control)?.remove();
            }
            window.fixtureData = await (await fetch('./assets/data/atlas.json')).json();
            window.fixtureSelected = null;
            window.calls = [];
            window.territoryCalls = [];
            const context = {
                getData: () => window.fixtureData,
                getSelectedId: () => window.fixtureSelected,
                onSelect: id => { window.fixtureSelected = id; window.calls.push(['select', id]); window.ui.render(); },
                onShowNoble: id => window.calls.push(['noble', id]),
                onEditLocation: id => window.calls.push(['edit', id]),
                onAddObject: id => window.calls.push(['add', id]),
                onEditObject: (id, objectId) => window.calls.push(['edit-object', id, objectId]),
                onDeleteObject: (id, objectId) => window.calls.push(['delete-object', id, objectId]),
            };
            if (options.delegateTerritories) {
                const sentinel = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                sentinel.dataset.boundarySentinel = 'parent';
                document.querySelector('#territory-layer').append(sentinel);
                context.onRenderTerritories = state => window.territoryCalls.push(state);
            }
            const { initUI } = await import('./assets/js/ui.mjs');
            window.ui = initUI(context);
        }""", {'removeControl': remove_reconstruction_control, 'delegateTerritories': delegate_territories})
        self.page.wait_for_function("document.querySelector('#base-map').complete && document.querySelector('#base-map').naturalWidth > 0", polling=50)
        self.page.mouse.move(2, 2)

    def select(self, location_id):
        self.page.evaluate("id => { window.fixtureSelected = id; window.ui.render(); window.ui.focusLocation(id, false); }", location_id)

    def center_marker(self, location_id):
        self.page.evaluate("id => { window.ui.setPanel('navigation', false); window.ui.setPanel('layers', false); window.ui.setPanel('dossier', false); window.ui.focusLocation(id, false); }", location_id)
        return self.page.locator(f'.map-marker[data-location-id="{location_id}"]')

    def location_ids(self):
        return self.page.locator('#location-list .location-row').evaluate_all('(rows) => rows.map(row => row.dataset.locationId)')

    def assert_clean(self):
        self.assertEqual(self.errors, [])

    def test_00_frozen_authorv6_fixture_has_the_complete_approved_canonical_sets(self):
        self.assertEqual(len(EXPECTED_LOCATION_IDS), 86, 'explicit authorv6 plus Raft, ferry docks, three Gray Ford houses and eight capital pins, not a dynamic release count')
        self.assertEqual(len(set(EXPECTED_LOCATION_IDS)), 86)
        self.assertEqual(len(CURRENT_ATLAS_FIXTURE['factions']), 14)
        self.assertEqual(len(AUTHOR_SEED['locations']), 67)
        self.assertEqual(set(EXPECTED_LOCATION_IDS), {row['id'] for row in AUTHOR_SEED['locations']} | {
            'ambermill-town-hall', 'ambermill-westbank-farm', 'ambermill-firrow-farm', 'ambermill-moorfield-farm', 'location-raft-estate', 'ferry-duskhaven', 'ferry-keel-harbor', 'ferry-stormglen', 'location-gray-ford-godfrey-estate', 'location-gray-ford-north-burned-house', 'location-gray-ford-east-burned-house', 'location-merchant-cloth-shop', 'location-merchant-herbal-shop', 'location-merchant-ironware-shop', 'location-military-forge', 'location-military-barracks', 'location-greymane-record-office', 'location-greymane-post-office', 'location-cathedral-rose-park'})
        assert_current_canonical_collections(self, ATLAS)

    def test_12b_labelled_empty_full_snapshot_keeps_zero_objects_and_empty_walden_gates(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['meta']['testFixture'] = 'Test-only empty objects / empty Walden full snapshot'
        fixture['factions'].append({'id': 'walden', 'name': 'Тестовый пустой Вальден',
                                    'parent': 'gilneas', 'color': '#91836e'})
        self.boot(fixture)
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        stored = self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')
        self.assertEqual(self.page.locator('.registry-category[data-category-id="objects"]').count(), 0, 'exclude empty categories')
        self.assertEqual(self.page.locator('#location-list details.faction-tree[data-faction-id="walden"]').count(), 0, 'exclude empty groups')
        self.assertEqual(sorted(self.location_ids()), sorted(row['id'] for row in fixture['locations']))
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'), stored)
        self.assert_clean()

    def test_01_native_hover_is_literal_safe_and_shows_immediate_faction_and_sovereign(self):
        fixture = copy.deepcopy(FIXTURE)
        unsafe = '<img src=x onerror="window.uiXss=1"> & <script>window.uiXss=2</script>'
        location = fixture['locations'][2]
        location['name'] = unsafe
        location['shortDescription'] = 'Тестовая краткая строка ' + unsafe
        self.boot(fixture)
        marker = self.center_marker(location['id'])
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        marker.hover()
        tooltip = self.page.locator('#marker-tooltip')
        self.assertEqual(tooltip.count(), 1, 'native hover must create/use the viewport tooltip')
        self.assertTrue(tooltip.is_visible())
        self.assertEqual(tooltip.get_attribute('role'), 'tooltip')
        self.assertEqual(tooltip.locator('.tooltip-title').text_content(), unsafe)
        self.assertEqual(tooltip.locator('.tooltip-description').text_content(), location['shortDescription'])
        self.assertIn('Тестовый младший дом', tooltip.locator('.tooltip-faction').text_content())
        self.assertEqual(tooltip.locator('.tooltip-sovereign').count(), 1, 'sovereign needs its own styled tooltip line')
        self.assertIn('Тестовое королевство Гилнеас', tooltip.locator('.tooltip-sovereign').text_content())
        self.assertEqual(tooltip.evaluate('node => node.style.getPropertyValue("--tooltip-color")'), '#93a798')
        self.assertIsNone(marker.get_attribute('title'), 'native title must not compete with the custom tooltip')
        self.assertEqual(marker.get_attribute('aria-describedby'), 'marker-tooltip')
        self.assertEqual(tooltip.locator('img,script').count(), 0)
        self.assertIsNone(self.page.evaluate('window.uiXss'))
        self.assertEqual(tooltip.evaluate("node => node.parentElement.id"), 'viewport')
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before)
        self.assert_clean()

    def test_02_native_focus_and_leave_manage_the_shared_tooltip(self):
        self.boot()
        marker = self.center_marker('test-crown-place')
        tooltip = self.page.locator('#marker-tooltip')
        marker.focus()
        self.assertTrue(tooltip.is_visible(), 'keyboard focus must show the same tooltip as hover')
        self.assertEqual(tooltip.locator('.tooltip-description').text_content(), 'Тестовое первое предложение.')
        self.page.locator('#viewport').focus()
        self.assertTrue(tooltip.is_hidden(), 'blur must clear the tooltip')
        self.assertIsNone(marker.get_attribute('aria-describedby'))
        marker.hover()
        self.assertTrue(tooltip.is_visible())
        self.page.mouse.move(2, 2)
        self.assertTrue(tooltip.is_hidden(), 'mouseleave must not leave a stale tooltip')
        self.assertIsNone(marker.get_attribute('aria-describedby'))
        marker.hover()
        self.assertEqual(tooltip.count(), 1, 'reuse one viewport tooltip')
        self.assert_clean()

    def test_03_camera_selection_and_editing_hide_stale_tooltips(self):
        self.boot()
        marker = self.center_marker('test-crown-place')
        tooltip = self.page.locator('#marker-tooltip')
        marker.hover()
        self.assertTrue(tooltip.is_visible())
        self.page.mouse.wheel(0, -80)
        self.page.wait_for_timeout(50)
        self.assertTrue(tooltip.is_hidden(), 'native wheel must hide the old screen-space tooltip')
        marker = self.center_marker('test-crown-place')
        marker.hover()
        self.page.mouse.down()
        self.assertTrue(tooltip.is_hidden(), 'pan initiation must clear the tooltip')
        self.page.mouse.move(800, 500, steps=4)
        self.page.mouse.up()
        marker = self.center_marker('test-crown-place')
        marker.focus()
        self.page.evaluate('window.ui.setMapInteraction(() => {})')
        self.assertTrue(tooltip.is_hidden(), 'editing mode must hide the tooltip')
        marker.focus()
        self.assertTrue(tooltip.is_hidden(), 'editing must not reopen hover/focus tooltips')
        self.page.evaluate('window.ui.setMapInteraction(null)')
        self.page.locator('#viewport').focus()
        marker.focus()
        self.page.evaluate('window.ui.render()')
        self.assertTrue(tooltip.is_hidden(), 'data rerenders must clear removed marker references')
        marker = self.center_marker('test-crown-place')
        marker.focus()
        self.page.keyboard.press('Enter')
        self.assertEqual(self.page.evaluate('window.fixtureSelected'), 'test-crown-place')
        self.assertTrue(tooltip.is_hidden(), 'selecting a location must not leave a tooltip over its dossier')
        self.assert_clean()

    def test_04_hover_tooltip_is_clamped_in_unscaled_viewport_coordinates(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['name'] = 'Тестовая_' + 'длинная_метка_' * 35
        fixture['locations'][0]['shortDescription'] = 'Тестовое описание. ' * 35
        self.boot(fixture)
        marker = self.center_marker('test-crown-place')
        tooltip = self.page.locator('#marker-tooltip')
        for width, height in [(1440, 1000), (390, 844)]:
            self.page.set_viewport_size({'width': width, 'height': height})
            self.page.wait_for_function('height => parseFloat(document.documentElement.style.getPropertyValue("--app-height")) === height', arg=height, polling=25)
            self.center_marker('test-crown-place')
            viewport = self.page.locator('#viewport').bounding_box()
            for x, y in [(24, viewport['height'] / 2), (width - 24, viewport['height'] / 2), (width / 2, viewport['height'] - 110)]:
                point = [viewport['x'] + x, viewport['y'] + y]
                self.page.evaluate("point => { const p = window.ui.toMap(...point); const l = window.fixtureData.locations[0]; l.x = p[0]; l.y = p[1]; window.ui.render(); }", point)
                marker.hover()
                box = tooltip.bounding_box()
                self.assertGreaterEqual(box['x'], viewport['x'] + 7, 'left edge must be clamped')
                self.assertGreaterEqual(box['y'], viewport['y'] + 7, 'top edge must be clamped')
                self.assertLessEqual(box['x'] + box['width'], viewport['x'] + viewport['width'] - 7, 'right edge must be clamped')
                self.assertLessEqual(box['y'] + box['height'], viewport['y'] + viewport['height'] - 7, 'bottom edge must be clamped')
                self.assertEqual(tooltip.evaluate('node => getComputedStyle(node).position'), 'absolute')
                self.assertEqual(tooltip.evaluate('node => getComputedStyle(node).pointerEvents'), 'none')
                self.assertEqual(tooltip.evaluate('node => getComputedStyle(node).transform'), 'none')
                self.page.mouse.move(2, 2)
        self.assert_clean()

    def test_05_tooltip_distinguishes_unknown_affiliation_from_explicit_independence(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['faction'] = None
        fixture['locations'][0]['provenance'] = {'confidence': 'reconstruction', 'affiliationStatus': 'unknown'}
        fixture['locations'][1]['faction'] = None
        fixture['locations'][1]['provenance'] = {'confidence': 'reconstruction', 'affiliationStatus': 'independent'}
        self.boot(fixture)
        self.center_marker('test-crown-place').hover()
        self.assertIn('Принадлежность не установлена', self.page.locator('.tooltip-faction').text_content())
        self.assertIn('Подданство: Не установлено', self.page.locator('.tooltip-sovereign').text_content())
        self.center_marker('test-house-place').hover()
        self.assertIn('Независимое владение', self.page.locator('.tooltip-sovereign').text_content())
        self.assertNotIn('не установлена', self.page.locator('.tooltip-faction').text_content())
        self.assert_clean()

    def test_06_dossier_uses_immediate_faction_color_and_keeps_full_owner_text(self):
        fixture = copy.deepcopy(FIXTURE)
        owner = 'Тестовый полный владелец с очень длинным именем, титулом и наследственным домом'
        fixture['locations'][2]['owner'] = owner
        self.boot(fixture)
        self.select('test-vassal-place')
        self.assertEqual(self.page.locator('#dossier').evaluate('node => node.style.getPropertyValue("--dossier-faction-color")'), '#93a798')
        self.assertEqual(self.page.locator('#dossier-faction').evaluate('node => node.style.color'), 'var(--dossier-faction-color)')
        self.assertEqual(self.page.locator('#dossier-faction').text_content(), 'Тестовый младший дом')
        self.assertEqual(self.page.locator('#dossier-sovereign').text_content(), 'Тестовое королевство Гилнеас')
        self.assertEqual(self.page.locator('#dossier-owner').text_content(), owner)
        self.select('test-other-place')
        self.assertEqual(self.page.locator('#dossier').evaluate('node => node.style.getPropertyValue("--dossier-faction-color")'), '#aa85c4')
        self.assertEqual(self.page.locator('#dossier-owner').text_content(), 'Не установлен')
        self.assert_clean()

    def test_07_collapsed_object_badges_use_effective_affiliation_and_keep_modifier_semantics(self):
        fixture = copy.deepcopy(FIXTURE)
        owner = 'Тестовый полный хозяин объекта, наследственный хранитель и глава длинного имени'
        fixture['locations'][1]['objects'] = [
            {'id': 'test-inherited-object', 'type': 'building', 'name': 'Тестовый наследуемый объект', 'owner': owner,
             'modifiers': [{'id': 'test-bonus', 'kind': 'bonus', 'text': '+2 тестовых единицы'},
                           {'id': 'test-penalty', 'kind': 'penalty', 'text': '−1 тестовая единица'}]},
            {'id': 'test-neutral-object', 'type': 'resource', 'name': 'Тестовый независимый объект', 'faction': None, 'modifiers': []},
            {'id': 'test-own-object', 'type': 'landmark', 'name': 'Тестовый чужой объект', 'faction': 'test-other', 'modifiers': []},
        ]
        self.boot(fixture)
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        self.select('test-house-place')
        for object_id, color, label in [('test-inherited-object', '#639096', 'Тестовый старший дом'),
                                        ('test-neutral-object', '#b39467', 'Независимый объект'),
                                        ('test-own-object', '#aa85c4', 'Тестовая иная держава')]:
            card = self.page.locator(f'.object-card[data-object-id="{object_id}"]')
            self.assertFalse(card.evaluate('node => node.open'))
            badge = card.locator('summary .object-faction-badge')
            self.assertEqual(badge.count(), 1, 'affiliation belongs INSIDE the collapsed summary')
            self.assertTrue(badge.is_visible())
            self.assertEqual(badge.text_content(), label)
            self.assertEqual(card.evaluate('node => node.style.getPropertyValue("--object-color")'), color)
            self.assertEqual(badge.evaluate('node => node.style.color'), 'var(--object-color)')
        inherited = self.page.locator('.object-card[data-object-id="test-inherited-object"]')
        inherited.locator('summary').click()
        self.assertEqual(inherited.locator('summary .object-owner-badge').text_content(), owner)
        self.assertEqual(inherited.locator('.object-ownership').count(), 0, 'Affiliation appears once, in the collapsed summary')
        self.assertEqual(inherited.locator('.modifier.bonus').text_content(), '+2 тестовых единицы')
        self.assertEqual(inherited.locator('.modifier.penalty').text_content(), '−1 тестовая единица')
        self.assertNotEqual(inherited.locator('.modifier.bonus').evaluate('node => getComputedStyle(node).color'),
                            inherited.locator('.modifier.penalty').evaluate('node => getComputedStyle(node).color'))
        inherited.locator('[data-object-edit]').click()
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['edit-object', 'test-house-place', 'test-inherited-object'])
        inherited.locator('[data-object-delete]').click()
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['delete-object', 'test-house-place', 'test-inherited-object'])
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before)
        self.assert_clean()

    def test_08_dossier_hides_bookkeeping_but_preserves_citations_and_direct_wowpedia(self):
        fixture = copy.deepcopy(FIXTURE)
        note = 'Тестовая редакторская инструкция: не назначать владельцев и не добавлять догадки.'
        fixture['sources'] = [{'id': 'test-source', 'title': 'Тестовый источник', 'url': 'https://example.org/test-source'},
                              {'id': 'test-unsafe-source', 'title': '<img src=x onerror="window.uiXss=1">', 'url': 'javascript:window.uiXss=1'}]
        location = fixture['locations'][0]
        location['provenance'] = {'confidence': 'reconstruction', 'note': note, 'sources': ['test-source', 'test-unsafe-source']}
        location['wowpediaUrl'] = 'https://wowpedia.fandom.com/wiki/Test_location'
        self.boot(fixture)
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        self.select('test-crown-place')
        provenance = self.page.locator('#dossier-provenance')
        self.assertEqual(provenance.locator('.confidence').count(), 0, 'no visible confirmed/reconstruction/custom bookkeeping')
        self.assertNotIn(note, self.page.locator('#dossier').text_content())
        citation = provenance.locator('.source-citation[data-source-id="test-source"]')
        self.assertEqual(citation.get_attribute('href'), 'https://example.org/test-source')
        self.assertEqual(citation.get_attribute('rel'), 'noopener noreferrer')
        wowpedia = provenance.locator('.wowpedia-link')
        self.assertEqual(wowpedia.count(), 1)
        self.assertEqual(wowpedia.get_attribute('href'), location['wowpediaUrl'])
        self.assertEqual(wowpedia.get_attribute('target'), '_blank')
        self.assertEqual(wowpedia.get_attribute('rel'), 'noopener noreferrer')
        self.assertNotIn('source-citation', wowpedia.get_attribute('class'))
        self.assertIsNone(wowpedia.get_attribute('data-source-id'))
        self.assertEqual(self.page.locator('#dossier-owner').text_content(), 'Не установлен')
        self.assertEqual(provenance.locator('a[href^="javascript:"]').count(), 0)
        self.assertIsNone(self.page.evaluate('window.uiXss'))
        self.page.evaluate("window.fixtureData.locations[0].wowpediaUrl = 'javascript:window.uiXss=2'; window.ui.renderDossier()")
        self.assertEqual(provenance.locator('.wowpedia-link').count(), 0, 'reject non-HTTP direct links')
        self.page.evaluate("window.fixtureData.locations[0].wowpediaUrl = 'https://wowpedia.fandom.com/wiki/Test_location'")
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before, 'rendering never rewrites provenance')
        self.assert_clean()

    def test_09_reconstruction_checkbox_is_optional_and_never_filters_or_dashes_markers(self):
        self.boot()
        self.page.evaluate("const control = document.querySelector('#show-reconstructions'); if (control) { control.checked = false; control.dispatchEvent(new Event('change', { bubbles: true })); }")
        marker = self.center_marker('test-house-place')
        self.assertFalse(marker.evaluate('node => node.hidden'), 'reconstruction is not a visibility category')
        self.assertNotIn('reconstruction', marker.get_attribute('class'))
        self.assertEqual(marker.evaluate('node => getComputedStyle(node, ":before").borderTopStyle'), 'solid')
        self.boot(remove_reconstruction_control=True)
        self.assertEqual(self.page.locator('.map-marker').count(), len(FIXTURE['locations']))
        self.page.evaluate('window.ui.render()')
        self.assertEqual(self.page.locator('.map-marker.reconstruction').count(), 0)
        self.assert_clean()

    def test_10_dossier_independence_is_explicit_and_does_not_reuse_unknown_labels(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['faction'] = None
        fixture['locations'][0]['provenance'] = {'confidence': 'reconstruction', 'affiliationStatus': 'unknown'}
        fixture['locations'][1]['faction'] = None
        fixture['locations'][1]['provenance'] = {'confidence': 'reconstruction', 'affiliationStatus': 'independent'}
        self.boot(fixture)
        self.select('test-crown-place')
        self.assertEqual(self.page.locator('#dossier-faction').text_content(), 'Принадлежность не установлена')
        self.select('test-house-place')
        self.assertEqual(self.page.locator('#dossier-faction').text_content(), 'Без державы')
        self.assertEqual(self.page.locator('#dossier-sovereign').text_content(), 'Независимое владение')
        self.assertEqual(self.page.locator('#dossier').evaluate('node => node.style.getPropertyValue("--dossier-faction-color")'), '#b39467')
        self.assert_clean()

    def test_11_new_subject_factions_without_heraldry_stay_plain_without_borrowing_the_royal_device(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['meta']['gilneasHeraldry'] = {'symbol':'assets/ui/gilneas-royal-symbol.png','field':'#131516','edge':'#65707b','device':'#9aa8b6'}
        self.boot(fixture)
        self.select('test-vassal-place')
        shield = self.page.locator('#dossier-seal .faction-shield')
        self.assertEqual(shield.count(), 1, 'dossier uses the simple shield, not a full banner image')
        faction = next(row for row in fixture['factions'] if row['id']==fixture['locations'][2]['faction'])
        self.assertEqual(shield.locator('.shield-field').get_attribute('fill'), faction['color'])
        self.assertEqual(shield.locator('.shield-device').count(), 0, 'A test-only new house must not borrow the sovereign device')
        self.assertEqual(self.page.locator('#dossier-seal img').count(), 0)
        self.select('test-other-place')
        self.assertEqual(self.page.locator('#dossier-seal .faction-shield').count(), 1)
        self.assertEqual(self.page.locator('#dossier-seal .shield-device').count(), 0)
        self.assert_clean()

    def test_12_real_atlas_navigation_is_nested_and_every_canonical_location_occurs_once(self):
        self.boot(ATLAS)
        source_ids = sorted(location['id'] for location in ATLAS['locations'])
        assert_current_canonical_collections(self, ATLAS)
        self.assertEqual(len(source_ids), len(EXPECTED_LOCATION_IDS))
        self.assertEqual(source_ids, sorted(EXPECTED_LOCATION_IDS))
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        stored = self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')
        self.assertEqual(sorted(self.location_ids()), source_ids)
        self.assertEqual(len(set(self.location_ids())), len(source_ids))
        hierarchy = self.page.evaluate("""() => {
            const root = document.querySelector('#location-list details.faction-tree[data-faction-id="gilneas"]');
            const house = root?.querySelector('.faction-children > details.faction-tree[data-faction-id="crowley"]');
            const junior = house?.querySelector('.faction-children > details.faction-tree[data-faction-id="silverlaine"]');
            return { root: !!root, house: !!house, junior: !!junior,
                rootCount: root?.querySelector(':scope > summary .group-count')?.textContent,
                houseCount: house?.querySelector(':scope > summary .group-count')?.textContent,
                juniorCount: junior?.querySelector(':scope > summary .group-count')?.textContent };
        }""")
        self.assertTrue(hierarchy['root'], 'kingdom is a real recursive group')
        self.assertTrue(hierarchy['house'], 'Crowley must be a child of Gilneas, not a sibling')
        self.assertTrue(hierarchy['junior'], 'Silverlaine must be a child of Crowley, not a sibling')
        factions = {faction['id']: faction for faction in ATLAS['factions']}
        def within(faction_id, parent):
            while faction_id is not None:
                if faction_id == parent:
                    return True
                faction_id = factions[faction_id].get('parent')
            return False
        for group, faction_id in [('rootCount', 'gilneas'), ('houseCount', 'crowley'), ('juniorCount', 'silverlaine')]:
            self.assertEqual(hierarchy[group], str(sum(within(location.get('faction'), faction_id) for location in ATLAS['locations'])))
        # Independently derive every nonempty category from the actual current
        # baseline (including future parent-integrated own objects), not v5.
        expected_categories = {}
        for location in ATLAS['locations']:
            faction_id = location.get('faction')
            unknown = location.get('provenance', {}).get('affiliationStatus') == 'unknown' or (
                faction_id is None and location.get('provenance', {}).get('confidence') == 'reconstruction'
                and location.get('provenance', {}).get('affiliationStatus') != 'independent')
            group = faction_id or ('unknown' if unknown else 'independent')
            expected_categories.setdefault((group, 'locations'), []).append(location['id'])
            for obj in location.get('objects', []):
                if 'faction' in obj:
                    expected_categories.setdefault((obj['faction'] or 'independent', 'objects'), []).append(
                        location['id'] + '/' + obj['id'])
        categories = self.page.locator('#location-list .registry-category').evaluate_all("""nodes => nodes.map(node => {
            const group = node.closest('.faction-tree');
            return {group: group.dataset.factionId || group.dataset.affiliation, kind: node.dataset.categoryId,
                count: node.querySelector(':scope > summary .category-count').textContent,
                ids: [...node.querySelectorAll(':scope > button')].map(row => row.dataset.objectId
                    ? row.dataset.locationId + '/' + row.dataset.objectId : row.dataset.locationId)};
        })""")
        self.assertEqual(sorted((row['group'], row['kind']) for row in categories), sorted(expected_categories))
        for row in categories:
            expected = expected_categories[(row['group'], row['kind'])]
            self.assertEqual(row['count'], str(len(expected)))
            self.assertEqual(sorted(row['ids']), sorted(expected))
        self.assertEqual(self.page.locator('.registry-category[data-category-id="objects"]').count(),
                         sum(kind == 'objects' for _, kind in expected_categories))
        walden_present = any(within(location.get('faction'), 'walden') for location in ATLAS['locations']) or any(
            'faction' in obj and within(obj['faction'], 'walden')
            for location in ATLAS['locations'] for obj in location.get('objects', []))
        self.assertEqual(self.page.locator('#location-list details.faction-tree[data-faction-id="walden"]').count(), int(walden_present))
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'), stored)
        self.assert_clean()

    def test_13_explicit_object_affiliations_get_separate_rows_counts_and_canonical_selection(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['objects'] = [
            {'id': 'test-inherited', 'name': 'Тестовый наследуемый объект', 'type': 'building', 'modifiers': []},
            {'id': 'test-house-object', 'name': 'Тестовый объект старшего дома', 'type': 'building', 'faction': 'test-house', 'modifiers': []},
            {'id': 'test-vassal-object', 'name': 'Тестовый объект младшего дома', 'type': 'landmark', 'faction': 'test-vassal', 'modifiers': []},
            {'id': 'test-independent-object', 'name': 'Тестовый независимый запас', 'type': 'resource', 'faction': None, 'modifiers': []},
        ]
        self.boot(fixture)
        self.assertEqual(self.page.locator('#location-list .object-row').count(), 3, 'index explicit object affiliation only, including null')
        self.assertEqual(sorted(self.location_ids()), sorted(location['id'] for location in fixture['locations']))
        root = self.page.locator('details.faction-tree[data-faction-id="gilneas"]')
        self.assertEqual(root.locator(':scope > summary .group-count').text_content(), '3', 'object rows do not inflate location totals')
        self.assertEqual(root.locator(':scope > summary .group-object-count').text_content(), '2')
        junior = self.page.locator('details.faction-tree[data-faction-id="test-vassal"]')
        self.assertEqual(junior.locator(':scope > summary .group-count').text_content(), '1')
        self.assertEqual(junior.locator(':scope > .registry-category[data-category-id="objects"] .category-count').text_content(), '1')
        self.assertEqual(self.page.locator('.object-row[data-object-id="test-inherited"]').count(), 0)
        independent = self.page.locator('.object-row[data-object-id="test-independent-object"]')
        self.assertEqual(independent.get_attribute('data-location-id'), 'test-crown-place')
        self.assertIn('Тестовая столица', independent.locator('small').text_content())
        self.assertEqual(independent.evaluate('node => node.closest(".faction-tree").dataset.affiliation'), 'independent')
        row = self.page.locator('.object-row[data-object-id="test-vassal-object"]')
        row.click()
        self.assertEqual(self.page.evaluate('window.fixtureSelected'), 'test-crown-place')
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['select', 'test-crown-place'])
        self.assertTrue(self.page.locator('.object-card[data-object-id="test-vassal-object"]').evaluate('node => node.open'))
        self.assertIn('active', self.page.locator('.location-row[data-location-id="test-crown-place"]').get_attribute('class'))
        self.page.evaluate("window.ui.setPanel('dossier', false); window.ui.setPanel('layers', true)")
        self.page.locator('.faction-row[data-faction-id="test-house"]').click()
        self.assertEqual(sorted(self.location_ids()), ['test-house-place', 'test-vassal-place'])
        self.assertEqual(sorted(self.page.locator('#location-list .object-row').evaluate_all('(rows) => rows.map(row => row.dataset.objectId)')), ['test-house-object', 'test-vassal-object'])
        self.assert_clean()

    def test_14_search_autoexpands_ancestors_without_overwriting_normal_group_and_category_state(self):
        self.boot()
        category = self.page.locator('.faction-tree[data-faction-id="test-vassal"] > .registry-category[data-category-id="locations"]')
        category.locator('summary').click()
        self.assertFalse(category.evaluate('node => node.open'))
        self.page.evaluate('window.ui.render()')
        self.assertFalse(category.evaluate('node => node.open'), 'ordinary category collapse must survive rerender')
        root = self.page.locator('.faction-tree[data-faction-id="gilneas"]')
        root.locator(':scope > summary').click()
        self.page.locator('#search').fill('младший удел')
        self.assertEqual(self.location_ids(), ['test-vassal-place'])
        self.assertEqual(self.page.locator('#location-list .faction-tree[open]').count(), 3)
        self.assertTrue(category.evaluate('node => node.open'))
        self.page.evaluate('window.ui.render(); document.querySelector("#search").value = ""; document.querySelector("#search").dispatchEvent(new Event("input"))')
        self.assertFalse(root.evaluate('node => node.open'), 'search autoexpand must not overwrite ordinary kingdom collapse')
        self.assertFalse(category.evaluate('node => node.open'), 'search autoexpand must not overwrite ordinary category collapse')
        root.locator(':scope > summary').click()
        self.page.locator('#fold-groups').click()
        self.assertEqual(self.page.locator('#location-list details[open]').count(), 0)
        self.page.locator('#search').fill('младший удел')
        self.assertGreater(self.page.locator('#location-list details[open]').count(), 0)
        self.page.locator('#search').fill('')
        self.assertEqual(self.page.locator('#location-list details[open]').count(), 0)
        self.page.locator('#fold-groups').click()
        self.assertEqual(self.page.locator('#location-list details:not([open])').count(), 0)
        self.assert_clean()

    def test_15_noble_rows_resolve_house_names_and_keep_the_parent_noble_callback(self):
        self.boot()
        self.page.locator('#filter-nobles').click()
        row = self.page.locator('.noble-row[data-noble-id="test-noble"]')
        self.assertIn('Тестовый старший дом', row.locator('small').text_content())
        self.assertNotIn('test-house', row.text_content())
        self.page.locator('#search').fill('старший дом')
        self.assertEqual(self.page.locator('.noble-row').count(), 1, 'search matches the resolved house name')
        row.click()
        self.assertEqual(self.page.evaluate('window.calls.at(-1)'), ['noble', 'test-noble'])
        self.assertIsNone(self.page.evaluate('window.fixtureSelected'), 'opening noble remains the parent callback, not location selection')
        self.assert_clean()

    def test_16_unknown_navigation_is_not_mislabeled_as_independent(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['faction'] = None
        fixture['locations'][0]['provenance'] = {'affiliationStatus': 'unknown'}
        fixture['locations'][1]['faction'] = None
        fixture['locations'][1]['provenance'] = {'affiliationStatus': 'independent'}
        self.boot(fixture)
        unknown = self.page.locator('.faction-tree[data-affiliation="unknown"]')
        self.assertEqual(unknown.count(), 1, 'unknown locations need an honest unknown group')
        self.assertEqual(unknown.locator(':scope > summary .group-name').text_content(), 'Принадлежность не установлена')
        self.assertEqual(unknown.locator('.location-row').get_attribute('data-location-id'), 'test-crown-place')
        independent = self.page.locator('.faction-tree[data-affiliation="independent"]')
        self.assertEqual(independent.locator('.location-row').get_attribute('data-location-id'), 'test-house-place')
        self.assertNotIn('не установлена', independent.locator(':scope > summary .group-name').text_content())
        self.assertEqual(sorted(self.location_ids()), sorted(location['id'] for location in fixture['locations']))
        self.assert_clean()

    def test_17_junior_vassal_header_prioritizes_its_ruler_without_changing_canonical_house(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['factions'][2]['ruler'] = 'Тестовый барон младшего дома'
        self.boot(fixture)
        summary = self.page.locator('.faction-tree[data-faction-id="test-vassal"] > summary')
        self.assertEqual(summary.locator('.group-name').text_content(), 'Тестовый барон младшего дома')
        self.assertEqual(summary.locator('.group-house-name').text_content(), 'Тестовый младший дом')
        self.assertEqual(self.page.locator('.faction-tree[data-faction-id="test-house"] > summary .group-name').text_content(), 'Тестовый старший дом')
        self.assertEqual(self.page.evaluate('window.fixtureData.factions[2].name'), 'Тестовый младший дом')
        self.page.locator('#search').fill('Тестовый барон младшего дома')
        self.assertEqual(self.location_ids(), ['test-vassal-place'])
        self.assertEqual(self.page.locator('.faction-tree').count(), 3, 'ruler search keeps the two real ancestors')
        self.assert_clean()

    def test_18_territory_callback_owns_the_layer_and_receives_visibility_and_descendant_filter(self):
        self.boot(delegate_territories=True)
        self.assertEqual(self.page.locator('#territory-layer [data-boundary-sentinel="parent"]').count(), 1, 'UI must not replace the parent-owned boundary layer')
        self.assertEqual(self.page.locator('#territory-layer polygon').count(), 0)
        state = self.page.evaluate('window.territoryCalls.at(-1)')
        self.assertEqual(state['visible'], True)
        self.assertIsNone(state['selectedFaction'])
        self.assertIsNone(state['includedFactions'])
        self.page.locator('.faction-row[data-faction-id="test-house"]').click()
        state = self.page.evaluate('window.territoryCalls.at(-1)')
        self.assertEqual(state['selectedFaction'], 'test-house')
        self.assertEqual(sorted(state['includedFactions']), ['test-house', 'test-vassal'])
        self.page.locator('label:has(#show-territories)').click()
        self.assertEqual(self.page.evaluate('window.territoryCalls.at(-1).visible'), False)
        self.assertEqual(self.page.locator('#territory-layer [data-boundary-sentinel="parent"]').count(), 1)
        self.boot()
        polygon = self.page.locator('#territory-layer polygon[data-territory-id="test-territory"]')
        self.assertEqual(polygon.count(), 1, 'legacy standalone fixtures keep polygon fallback')
        self.assertEqual(polygon.get_attribute('points'), '1700,3000 2100,3000 2100,3300 1700,3300')
        self.assertEqual(polygon.get_attribute('fill'), '#639096')
        self.page.locator('label:has(#show-territories)').click()
        self.assertTrue(self.page.locator('#territory-layer').evaluate('node => node.hasAttribute("hidden")'))
        self.assert_clean()

    def test_19_collapsed_object_heading_stacks_badge_below_title_before_the_chevron(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['locations'][0]['objects'] = [{'id': 'test-heading', 'name': 'Тестовый объект', 'type': 'building', 'modifiers': []}]
        self.boot(fixture)
        self.select('test-crown-place')
        summary = self.page.locator('.object-card[data-object-id="test-heading"] > summary')
        self.assertEqual(summary.locator(':scope > .object-heading').count(), 1, 'title and badge share the middle summary column')
        self.assertEqual(summary.locator('.object-heading .object-title').text_content(), 'Тестовый объект')
        self.assertEqual(summary.locator('.object-heading .object-faction-badge').count(), 1)
        self.assertEqual(summary.locator(':scope > .chevron').count(), 1)
        self.assertTrue(summary.locator('.object-faction-badge').is_visible())
        self.assert_clean()

    def test_20_unknown_inherited_objects_are_not_presented_as_explicit_independent_objects(self):
        fixture = copy.deepcopy(FIXTURE)
        location = fixture['locations'][0]
        location['faction'] = None
        location['provenance'] = {'affiliationStatus': 'unknown'}
        location['objects'] = [
            {'id': 'test-unknown-inherited', 'name': 'Тестовый объект неизвестной земли', 'type': 'building', 'modifiers': []},
            {'id': 'test-explicit-independent', 'name': 'Тестовый явно независимый объект', 'type': 'resource', 'faction': None, 'modifiers': []},
        ]
        self.boot(fixture)
        self.select('test-crown-place')
        unknown = self.page.locator('.object-card[data-object-id="test-unknown-inherited"]')
        self.assertEqual(unknown.locator('.object-faction-badge').text_content(), 'Принадлежность не установлена')
        self.assertEqual(unknown.locator('.object-ownership').count(), 0, 'Keep the unknown affiliation only in the summary badge')
        independent = self.page.locator('.object-card[data-object-id="test-explicit-independent"]')
        self.assertEqual(independent.locator('.object-faction-badge').text_content(), 'Независимый объект')
        self.assertEqual(unknown.evaluate('node => node.style.getPropertyValue("--object-color")'), '#b39467')
        self.assert_clean()

    def test_21_selected_label_is_not_clipped_and_keeps_real_map_anchor_at_multiple_scales(self):
        # Integration gate for the parent-owned scoped CSS, not a CSS fixture.
        self.boot(ATLAS)
        self.select('northern-headlands')
        marker = self.page.locator('.map-marker[data-location-id="northern-headlands"]')
        label = marker.locator('.marker-label')
        self.assertEqual(label.text_content(), 'Северный каменистый мыс')
        initial_width = marker.bounding_box()['width']
        for factor in [1, 1.25, 0.8]:
            self.page.evaluate('factor => window.ui.zoom(factor)', factor)
            self.page.evaluate("window.ui.focusLocation('northern-headlands', false)")
            geometry = marker.evaluate("""node => {
                const marker = node.getBoundingClientRect(), label = node.querySelector('.marker-label'), box = label.getBoundingClientRect();
                const range = document.createRange(); range.selectNodeContents(label);
                const text = range.getBoundingClientRect();
                return {center: [marker.x + marker.width / 2, marker.y + marker.height / 2], width: marker.width,
                    labelCenter: box.x + box.width / 2, textLeft: text.left, textRight: text.right,
                    left: box.left, right: box.right, overflow: getComputedStyle(node).overflow};
            }""")
            self.assertEqual(geometry['overflow'], 'visible', 'global button clipping must be reset for map markers')
            self.assertGreaterEqual(geometry['textLeft'], geometry['left'] + 4)
            self.assertLessEqual(geometry['textRight'], geometry['right'] - 4)
            self.assertAlmostEqual(geometry['labelCenter'], geometry['center'][0], delta=1)
            self.assertAlmostEqual(geometry['width'], initial_width, delta=0.2)
            point = self.page.evaluate('point => window.ui.toMap(...point)', geometry['center'])
            location = next(item for item in ATLAS['locations'] if item['id'] == 'northern-headlands')
            self.assertAlmostEqual(point[0], location['x'], delta=0.02)
            self.assertAlmostEqual(point[1], location['y'], delta=0.02)
        self.assert_clean()

    def test_22_registry_shields_use_the_supplied_royal_device_without_lending_it_to_new_houses(self):
        fixture = copy.deepcopy(FIXTURE)
        fixture['meta']['gilneasCrest'] = 'assets/ui/rose.svg'
        fixture['meta']['gilneasHeraldry'] = {'symbol':'assets/ui/gilneas-royal-symbol.png','field':'#131516','edge':'#65707b','device':'#9aa8b6'}
        self.boot(fixture)
        before = self.page.evaluate('JSON.stringify(window.fixtureData)')
        for selector in ['.faction-tree[data-faction-id="gilneas"] > summary .faction-shield', '.faction-row[data-faction-id="gilneas"] > .faction-shield']:
            shield = self.page.locator(selector)
            self.assertEqual(shield.count(), 1)
            self.assertEqual(shield.locator('.shield-field').get_attribute('fill'), '#131516')
            self.assertEqual(shield.locator('.shield-device').get_attribute('href'), fixture['meta']['gilneasHeraldry']['symbol'])
        for selector in ['.faction-tree[data-faction-id="test-house"] > summary .faction-shield', '.faction-row[data-faction-id="test-house"] > .faction-shield']:
            shield = self.page.locator(selector)
            self.assertEqual(shield.count(), 1)
            self.assertEqual(shield.locator('.shield-field').get_attribute('fill'), '#639096')
            self.assertEqual(shield.locator('.shield-device').count(), 0, 'A test-only house has no assigned device')
        self.assertEqual(self.page.locator('.faction-crest').count(), 0, 'Registry identities use the preserved shield, not a full image card')
        self.assertEqual(self.page.evaluate('JSON.stringify(window.fixtureData)'), before)
        self.assert_clean()


if __name__ == '__main__':
    unittest.main()
