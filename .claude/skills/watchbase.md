# watchbase

Скилл для работы с локальным генератором контента 316.watch (репозиторий watchbase).

## Когда использовать

Когда пользователь хочет:
- запустить Streamlit-приложение,
- протестировать генерацию карточки на конкретном артикуле,
- обновить README или добавить скриншоты,
- проверить код на ошибки,
- внести изменения в генератор, поиск или справочник калибров,
- подготовить проект к публикации (GitHub, Streamlit Cloud и т.п.),
- очистить кэш и историю генерации.

## Контекст проекта

- Репозиторий: https://github.com/ekaterinaplekhanova-cmyk/watchbase/
- Технологии: Python 3.10+, Streamlit, Ollama (`qwen2.5:14b`), Playwright, requests, BeautifulSoup.
- Структура:
  - `app/app.py` — Streamlit-интерфейс.
  - `app/generator.py` — генерация карточки, описания модели, Telegram-поста.
  - `app/search.py` — поиск источников характеристик.
  - `app/caliber_reference.py` — справочник калибров для fallback.
  - `app/brand_urls.py`, `app/retailers.py` — правила поиска и классификация источников.
  - `app/ollama_client.py` — клиент для Ollama.
  - `app/image_search.py` — поиск по изображению.
  - `app/utils.py` — сохранение результатов.
  - `data/` — Tone of Voice и примеры постов.
  - `prompts/` — промпты для агентов.
  - `templates/watch_card_template.json` — шаблон карточки.

## Важные правила работы с проектом

1. **Не выдумывать технические характеристики часов.** Если данных не хватает — указать, что нужно уточнить.
3. **Особое внимание к точности:** калибр, механизм, материалы, количество камней, запас хода, водозащита.
4. **Перед тестированием после изменений очищать кэш:**
   - `output/card_cache.json`
   - `output/search_cache.json`
   - `output/render_cache.json`
   - `app/__pycache__`
5. **Перед запуском Streamlit убивать старые процессы**, чтобы не загрузилась устаревшая версия кода.
6. **Использовать `python -m streamlit`** для запуска, если `streamlit` не в PATH.
7. **Проверять изменения на тестовом артикуле**, например `AB2010161C1A1` Breitling.
8. **Соблюдать ToV:** без пафоса, маркетинговых клише, выдуманных историй.

## Команды

### `/run`

Запускает Streamlit-приложение на `http://localhost:8501`.

Перед запуском:
1. Убить старые Streamlit-процессы.
2. Удалить `__pycache__`.
3. Запустить `python -m streamlit run app/app.py` из папки проекта.

Пример (Windows, PowerShell):
```powershell
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*streamlit*" } | Stop-Process -Force
Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force
cd C:\Users\kitty\Проект\app
python -m streamlit run app.py --server.headless true
```

### `/test <артикул> <бренд>`

Проверяет генерацию карточки для указанного артикула.

Перед тестом:
1. Очистить файловые кэши.
2. Удалить `__pycache__`.
3. Запустить `python -u -c` с вызовом `generate_package(..., card_only=True)`.
4. Показать результат: калибр, камни, запас хода, частота, водозащита, источник.

Если артикул не указан — использовать `AB2010161C1A1` / `Breitling`.

### `/readme`

Помогает обновить README.md:
- актуализировать описание,
- добавить разделы,
- добавить или заменить скриншоты в `images/`,
- обновить список зависимостей или инструкции.

### `/lint`

Проверяет Python-код на синтаксические ошибки:
```bash
python -m py_compile app/app.py app/generator.py app/search.py app/caliber_reference.py app/brand_urls.py app/retailers.py app/ollama_client.py app/image_search.py app/utils.py
```

### `/clean`

Очищает кэш и временные файлы:
- `output/card_cache.json`
- `output/search_cache.json`
- `output/render_cache.json`
- `app/__pycache__`

### `/deploy`

Подготавливает проект к публикации:
- проверяет `.gitignore`,
- удаляет временные файлы из git-индекса,
- проверяет README,
- делает `git status`,
- коммитит и пушит изменения.

## Примеры запросов пользователя

- "запусти watchbase"
- "проверь артикул AB2010161C1A1 Breitling"
- "обнови README"
- "проверь код на ошибки"
- "подготовь проект к публикации"
- "убей старый стримлит и перезапусти"

## Заметки

- Проект использует локальную Ollama. Для публикации в Streamlit Cloud потребуется либо VDS, либо переход на облачный LLM API.
- Все значимые изменения должны сохраняться в git и пушиться на GitHub только с согласия пользователя.
