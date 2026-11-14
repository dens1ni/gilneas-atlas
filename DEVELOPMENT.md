# Build and verification prerequisites

Use a project virtual environment and install `Pillow`, `numpy`, `scipy`, `playwright` and `opencv-python-headless`. The Origins replacement-mask registration uses OpenCV; visitors need none of these dependencies.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install pillow numpy scipy playwright opencv-python-headless
.venv/bin/python -m playwright install chromium
npm test
npm run check
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

## Исследовательские источники

В `assets/data/atlas.json` уже включены краткие тексты и полный каталог используемых URL. Поддерживающие цитаты проверены по сохранённым страницам; повторный сбор не требуется для обычного редактирования карты. `build_data.py` создаёт первичную ограниченную основу, `merge_research.py` использует отдельно сохранённые исследовательские JSON, затем `finalize_data.py` очищает только отображение ссылочной разметки. Не запускайте первый скрипт поверх авторского атласа без резервной копии: опубликованный `atlas.json` — актуальный baseline.

Runtime is dependency-free plain HTML, CSS and ES modules. None of these Python packages are downloaded by visitors. Image source paths in processing tests refer to the original supplied local archive; pass the extracted original pair at those paths or adjust the local test fixture. Production processing metadata records hashes of the untouched source pair.

The map-export ZIP deliberately includes only runtime dependencies, package metadata, README and the Pages workflow, not processing experiments or QA screenshots. The workflow runs pure model tests when source tests are present and always checks required runtime paths and module syntax.
