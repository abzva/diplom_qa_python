# Запуск и конфигурация

[README](../README.md) · [Результаты](../README.md#status)

## Установка

Команды выполняются из корня проекта в bash или zsh. Установка проверена в чистом окружении **Python 3.13.7**; требуется Python **3.13+**. Продуктовые зависимости закреплены в `requirements.txt`. Для локального UI нужен Chrome; Selenium Manager использует `.cache/selenium` и при первом запуске может загрузить ChromeDriver.

Для нового окружения выберите нужный Python и создайте `.venv`. Существующее окружение заменять не нужно:

```bash
python3 --version
python3 -m venv .venv
mkdir -p .tmp/pip .cache/pip
TMPDIR="$PWD/.tmp/pip" .venv/bin/python -m pip install \
  --cache-dir .cache/pip -r requirements.txt
.venv/bin/python -m pip check
```

<a id="quality"></a>

## Проверки качества

`requirements-dev.txt` включает продуктовые зависимости и закрепляет инструменты:
Ruff **0.17.4**, mypy **2.4.1**, pre-commit **4.7.0**, stubs requests и зависимости
самих инструментов. Проверенная платформа установки — macOS arm64, Python 3.13.7.
Настройки находятся в `pyproject.toml`; pytest продолжает использовать `pytest.ini`.

```bash
.venv/bin/python -m pip install --cache-dir .cache/pip -r requirements-dev.txt
.venv/bin/python -m pip check
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy
PRE_COMMIT_HOME="$PWD/.cache/pre-commit" .venv/bin/python -m pre_commit validate-config
PRE_COMMIT_HOME="$PWD/.cache/pre-commit" .venv/bin/python -m pre_commit run --all-files
```

Ruff проверяет и форматирует Python-код с длиной строки 100. mypy проверяет
аннотации продуктовых тестов, фикстур, страниц, моделей, API и отчётности;
`checks/` проверяется Ruff и отдельным запуском pytest. Настройки находятся
в `pyproject.toml`.

Для автоматического запуска перед commit:

```bash
PRE_COMMIT_HOME="$PWD/.cache/pre-commit" .venv/bin/python -m pre_commit install
```

Локальные hooks используют именно `.venv/bin/python`, поэтому версии берутся из
`requirements-dev.txt` без второго набора зависимостей. Hooks проверяют весь проект,
не изменяют файлы и не запускают UI/API/Mobile. Смена файлов конфигурации не приводит
к пропуску mypy. Параметр `PRE_COMMIT_HOME` размещает кэш ручного запуска в проекте;
при обычном `git commit` без этой переменной pre-commit использует стандартный кэш
пользователя. Для отключения hooks используется `.venv/bin/python -m pre_commit uninstall`.

Настройки сверены с документацией [Ruff](https://docs.astral.sh/ruff/configuration/),
[mypy](https://mypy.readthedocs.io/en/stable/config_file.html) и
[локальных hooks pre-commit](https://pre-commit.com/#repository-local-hooks).

## Настройки

- **API и локальный UI:** работают без `.env`. Адрес `https://automationexercise.com` задан в `config.py`; для другого стенда используется переменная процесса `BASE_URL`.
- **Selenoid:** в корневом `.env` нужны `SELENOID_URL`, `SELENOID_BROWSER_VERSION`, `SELENOID_VIDEO_BASE_URL`. Учебные адреса: `https://selenoid.qa.guru/wd/hub` и `https://selenoid.qa.guru/video/`. В подтверждённом прогоне Chrome — **156.0.8078.47**. Версию для нового запуска выбирайте из доступных на сервере. Если требуется HTTP Basic Auth, заполните `SELENOID_LOGIN`/`SELENOID_PASS`; доступ к видео настраивается отдельно через `SELENOID_VIDEO_USERNAME`/`SELENOID_VIDEO_PASSWORD`.
- **Mobile:** нужны пять `BROWSERSTACK_*` полей из [.env.example](../.env.example), доступ App Automate, доступные минуты и заранее загруженный APK. Приложение должно быть доступно используемому аккаунту; тесты его не загружают.

Selenoid и Mobile читают только корневой `.env` через `python-dotenv`: переменные процесса не заменяют значения этого файла. Для нового клона создайте `.env` по образцу `.env.example`; существующий файл сохраняйте. В Jenkins предоставляйте его через механизм секретов, вне Git и консольного вывода.

Mobile-тесты запускаются в BrowserStack App Automate.

Скачивание видео требует прямого доступа к хранилищу: оно не использует `.netrc` и proxy/CA-переменные процесса; TLS-проверка включена.

## Запуск из терминала

Каждая команда создаёт отдельный каталог результатов. По умолчанию pytest выбирает `tests/` — 14 UI/API-тестов. Для Mobile каталог указывается явно.

<a id="api-checks"></a>

Поиск проверяется по названию, как в [сценарии 9 стенда](https://automationexercise.com/test_cases) и [API 5](https://automationexercise.com/api_list). Из исходного каталога выбираются искомый товар и контрольный товар, в названии которого нет ни одного слова запроса. Проверяется наличие исходных ID/названия и отсутствие контрольного ID; число результатов не фиксируется. Если подходящей пары нет, тест завершается ошибкой подготовки данных.

Очистка использует [API 14 — `GET /api/getUserDetailByEmail`](https://automationexercise.com/api_list) с параметром `email`, без пароля. Положительный ответ проверяется по коду, ID и точному email. Отсутствие принимается только при HTTP 200, `responseCode=404`, сообщении `Account not found with this email, try another email!` и отсутствии объекта `user`; отказ `verifyLogin` таким доказательством не является. Документация API 14 описывает только положительный ответ; отрицательный ответ подтверждён на реальном стенде 26.10.2026 для нового неиспользованного email и после удаления собственного тестового аккаунта. Любой другой ответ или таймаут сохраняется в группе «ошибки при очистке аккаунта». В примечании исходного исключения указан этап: первичная проверка email, удаление или проверка после удаления. Ошибка начального запроса не отменяет попытку DELETE с исходными реквизитами своего аккаунта; ошибки удаления и контрольного запроса также сохраняются. Подтверждённое отсутствие аккаунта отдельно записывается в журнал даже при более раннем сбое; эта запись не отменяет ошибку teardown.

**API — 6 тестов:**

```bash
RUN_DIR=".artifacts/runs/api-$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest tests/api -v \
  --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" \
  --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

**UI — 8 тестов в локальном Chrome:**

```bash
RUN_DIR=".artifacts/runs/ui-$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest \
  tests/test_login.py tests/test_catalog.py tests/test_product.py tests/test_cart.py \
  --ui-mode=local -v --basetemp="$RUN_DIR/pytest-tmp" \
  --alluredir="$RUN_DIR/allure-results" --junitxml="$RUN_DIR/junit.xml" \
  --log-file="$RUN_DIR/run.log"
```

Chrome работает headless; `--headed` показывает окно. Для общего локального UI/API-прогона используйте `tests` вместо списка UI-модулей и новый `RUN_DIR`.

Локальный запуск использует временный профиль Chrome в `.tmp/chrome`, который
удаляется после закрытия браузера. Общие настройки local/Selenoid находятся
в `browser.py`. Перед закрытием сохраняются скриншот, HTML без секретов и
`browser_observation.json` со счётчиками уровней консоли, хостами и кодами сетевых
ошибок. Полные сообщения консоли и параметры URL не сохраняются. Ошибки вложений отмечаются
предупреждениями и не отменяют закрытие драйвера.

Для Selenoid ID сессии и имя видео сохраняются до `quit()`, видео запрашивается
только после успешного закрытия. HTTP 404 повторно проверяется в пределах 30 секунд;
другие статусы и транспортные ошибки не повторяются. Ограничение времени проверяется
между чтениями, поэтому ожидающее чтение сокета может добавить до 5 секунд.
Размер видео ограничен 50 МиБ. Ошибка видео сохраняется в метаданных и не меняет
результат сценария; ошибка `quit()` остаётся ошибкой teardown.

<a id="mobile-browserstack"></a>

### Mobile · BrowserStack App Automate

Appium Python Client управляет Wikipedia Android sample. Три сценария проверяют поиск статьи, замену запроса и очистку результатов. `mobile/config.py` валидирует пять полей корневого `.env`: `BROWSERSTACK_USERNAME`, `BROWSERSTACK_ACCESS_KEY`, `BROWSERSTACK_APP_URL`, `BROWSERSTACK_DEVICE_NAME`, `BROWSERSTACK_PLATFORM_VERSION`. Идентификатор приложения `bs://…` берётся из своего App Automate.

Последовательный запуск без повторной загрузки APK и ретраев; `--maxfail=1` останавливает прогон при первой ошибке:

```bash
RUN_DIR=".artifacts/runs/mobile-$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest mobile -v --maxfail=1 \
  --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" \
  --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

Для одного Mobile-теста вместо `mobile` укажите, например, `mobile/test_search.py::test_search_finds_python_programming_language`.

Фикстура сохраняет ID сессии в метке Allure `browserstack_session_id` сразу после
создания драйвера. Метаданные сохраняются в `session.json` и отдельном вложении
Allure при создании и завершении сессии. Ошибка записи файла не мешает вложению,
закрытию драйвера и обновлению статуса. Ошибки `quit()` и обновления статуса
остаются ошибками teardown.

`mobile/browserstack.py` содержит настройки удалённой сессии и запросы управления
ею; `mobile/video.py` скачивает видео отдельной HTTP-сессией без ключа BrowserStack.
Получение видео начинается после успешного `quit()`. Лимит размера — 50 МиБ;
60-секундный срок загрузки проверяется между чтениями, таймаут соединения —
15 секунд, чтения — 30 секунд. Это не жёсткий предел общей длительности запроса:
ожидание сети и редиректы могут увеличить время. Ошибки видео отмечаются
в диагностике и не меняют результат проверки Wikipedia.

В `allure_session.json` и одноимённом по содержанию вложении отчёта поле
`video_stage` показывает этап: `request`, `read`, `validate`, `save`, `saved`,
`attach` или `attached`. При ожидаемой ошибке загрузки `video_error_type`
содержит класс исключения, без его текста и подписанного URL. Собственные проверки
дополнительно задают `video_error`: `invalid_mp4`, `video_exceeds_50_mib` или
`download_deadline_exceeded`. Для HTTP-ошибки смотрите `video_http_status`;
наличие `Content-Type: video/mp4` само по себе не подтверждает формат файла.
Это диагностика причины отказа, а не автоматический повтор загрузки.

**Сборка всех 17 тестов без выполнения, браузеров и облачных реквизитов:**

```bash
.venv/bin/python -m pytest tests mobile --collect-only -q
```

Адресные локальные проверки вложений, поиска, очистки и связи Mobile-сессий находятся отдельно от дипломных сценариев. Сеть и чтение `.env` в них запрещены:

```bash
.venv/bin/python -B -m pytest checks -q
```

## Jenkins Freestyle и Selenoid

Задача [anastasia-diplom-python-ci](https://jenkins.qa.guru/job/anastasia-diplom-python-ci/) — **Freestyle**, 8 UI-тестов через Selenoid и 6 API-тестов. Mobile запускается отдельно.

Установите зависимости из `requirements-dev.txt` в `.venv` и предоставьте корневой
`.env` с Selenoid-настройками через механизм секретов Jenkins. Пример для шага
**Execute shell** (настройка внешней задачи выполняется отдельно):

```bash
#!/bin/bash
set -eu
.venv/bin/python -m pip check
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy
RUN_DIR=".artifacts/jenkins/$BUILD_NUMBER"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest tests --ui-mode=selenoid -v \
  --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" \
  --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

Для адресной проверки замените команду pytest в **Execute shell** одним из вариантов
ниже. Выполняйте их в отдельных сборках; установка зависимостей, предоставление
`.env` и `RUN_DIR=".artifacts/jenkins/$BUILD_NUMBER"` остаются как в примере выше.

**UI-01 — порядок завершения входа:**

```bash
.venv/bin/python -m pytest \
  tests/test_login.py::test_login_with_api_created_user --ui-mode=selenoid -v \
  --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" \
  --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

Зависимости подготовки: `api_session → account_data → test_user → user_browser →
user_login_page`. В завершении браузер сохраняет диагностику, вызывает `quit()`
и обрабатывает видео до API-очистки аккаунта. При ошибке `quit()` видео помечается
как недоступное, ошибка закрытия остаётся ошибкой teardown, а pytest продолжает
очистку аккаунта. Финализатор аккаунта зарегистрирован до POST создания; он
выполняется и при сбое подготовки. API-тесты не зависят от браузера.

**UI-05 — один диагностический запуск Products:**

```bash
.venv/bin/python -m pytest \
  tests/test_product.py::test_product_details_match_selected_catalog_product \
  --ui-mode=selenoid --ui-diagnostics -v \
  --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" \
  --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

Обычные Selenoid-настройки в `.env` сохраняются; дополнительных секретов не нужно.
Флаг работает только с `--ui-mode=selenoid` и не меняет навигацию, локаторы,
`pageLoadStrategy=eager` или таймауты. Он запрашивает:

- Chrome performance log: события Network/Page с временем, связями запросов,
  HTTP-кодами и сетевыми кодами ошибок. Сохраняются хосты и только известные
  публичные маршруты магазина; query, fragments, заголовки, cookies, тела запросов
  и ответов исключены. Идентификаторы запросов хешируются. Вложение —
  `Chrome loading trace (filtered)`, локальный файл — `loading_trace.json`.
- Selenoid `enableLog=true` и уникальный `logName`. После закрытия и обработки
  видео выполняется один GET `/logs/<logName>` на том же сервере с имеющейся
  WebDriver-авторизацией. В `driver_log.json` и вложение попадают только времена,
  имена команд/ответов и признак renderer timeout, без исходных payload.

Доступ к логам учебного сервера **не подтверждён**. `enableLog` запрашивает их
сохранение, но не включает verbose-режим ChromeDriver: для него нужна настройка
образа на сервере. HTTP 401/403/404, ошибка транспорта, отсутствие команд в логе
или неподдерживаемый performance log явно отражаются в диагностике. Логи не
перезапрашиваются; сбои диагностических вложений не заменяют результат теста.
Сырые логи не записываются в файлы и не прикрепляются к Allure.

Форматы описаны в документации
[Selenoid](https://aerokube.com/selenoid/latest/#_saving_session_logs) и
[ChromeDriver performance log](https://developer.chrome.com/docs/chromedriver/logging/performance-log).

Передавайте в публикацию результаты только текущего `$RUN_DIR`, включая упавшие запуски. Сохраняйте ненулевой код выхода pytest; не заменяйте его успешным кодом загрузчика отчёта. Сохраняйте каталог результатов текущей сборки как артефакт до очистки workspace.

## Allure Report и TestOps

`allure-results` — исходные JSON и вложения. **Allure Report** — генерируемый HTML-отчёт; **Allure TestOps** — отдельный сервис хранения результатов и тест-кейсов.

При установленном Allure CLI для выбранного `$RUN_DIR`:

```bash
allure generate "$RUN_DIR/allure-results" -o "$RUN_DIR/allure-report"
allure open "$RUN_DIR/allure-report"
```

`allure-pytest` не устанавливает Allure CLI. В Jenkins Allure Report и загрузчик
TestOps должны получать тот же каталог, что указан в `--alluredir`.

На [учебном TestOps](https://allure.qa.guru/project/5398/settings/cleanup) глобальный
срок хранения успешных сценариев, фикстур и вложений — 24 часа. Очистка применяется
к закрытым запускам. Архивируйте исходные JSON вместе со всеми файлами вложений
и готовый отчёт отдельно. Более длинное проектное правило не отменяет глобальное;
см. [политики очистки TestOps](https://docs.qameta.io/administer/maintenance/cleanup-policies/).

## Позднее видео BrowserStack

Если видео завершённой сессии появилось после teardown, `mobile.attach_video` добавляет его в **новую копию** результатов без повторного теста.

Сразу после создания драйвера в Allure сохраняется метка `browserstack_session_id`. Утилита находит результат по этому ID даже при таймауте получения метаданных. Для старых результатов поддерживается ссылка на BrowserStack-сессию. При нескольких подходящих результатах или противоречащих ID утилита останавливается до обращения в облако.

Подставьте свои пути и ID; каталог `--output` не должен существовать:

```bash
.venv/bin/python -m mobile.attach_video \
  --results .artifacts/your-run/allure-results \
  --output .artifacts/your-run-with-video \
  --session-id YOUR_COMPLETED_SESSION_ID
```

Каталог копии должен находиться вне каталога исходных результатов. Оригинальные результаты сохраняются; не объединяйте оригинал и копию в одном отчёте.

Для нескольких сессий передавайте следующему вызову `--results` из предыдущей
успешной копии, каждый раз выбирая новый `--output`. Так ранее добавленные видео
сохранятся. Если CLI завершился с ошибкой, копии результатов может не быть:
сначала изучите `late-video-diagnostics/allure_session.json` и не подменяйте
исходный отчёт неудачной попыткой.

Итоговую копию можно собрать в один HTML-файл со встроенными вложениями
(проверено с Allure CLI 2.44.0):

```bash
allure generate .artifacts/your-run-with-video/allure-results \
  -o .artifacts/your-run-with-video/allure-report --single-file
```

Для просмотра откройте `allure-report/index.html`. Видео включены внутрь HTML,
поэтому размер файла может быть значительно больше обычного отчёта.

CLI использует тот же механизм получения видео, что и teardown Mobile-сессии.
Копия создаётся только при наличии видео. Тест определяется по метке ID сессии
или, для старых результатов, по ссылке BrowserStack; неоднозначные и конфликтующие
ID отклоняются. Ссылка из ответа BrowserStack дополнительно сверяется с запрошенным
ID до скачивания видео. Статус, шаги и длительность теста в копии сохраняются.

## Структура

- `tests/`, `tests/api/` — UI- и API-тесты, фикстуры браузера и аккаунтов.
- `pages/`, `models/` — Page Objects магазина и модели запросов, ответов и товаров.
- `diplom_qa_python/api/` — HTTP-сессия и общие проверки аккаунтов.
- `mobile/` — конфигурация BrowserStack, фикстуры, Page Object, три теста и получение видео.
- `browser.py` — общие настройки Chrome и создание локального драйвера.
- `reporting.py`, `selenoid.py` — вложения Allure, удалённый браузер и загрузка его видео.
- `checks/` — технические проверки без сети; не входят в 17 продуктовых сценариев.
- `docs/` — инструкции запуска и изображения. Ручные сценарии хранятся в [TestOps](https://allure.qa.guru/project/5398/test-cases).

`.env`, окружение, временные файлы, внутренние отчёты и исходные артефакты исключены из Git.
