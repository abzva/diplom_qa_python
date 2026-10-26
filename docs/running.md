# Запуск и конфигурация

[README](../README.md) · [Результаты](validation.md)

## Установка

Команды выполняются из корня проекта в bash или zsh. В подтверждённом Jenkins-прогоне использован Python **3.14.4**; локальное окружение — **3.13.7**. Зависимости закреплены в `requirements.txt`. Для локального UI нужен Chrome; Selenium Manager использует `.cache/selenium` и при первом запуске может загрузить ChromeDriver.

Для нового окружения выберите нужный Python и создайте `.venv`. Существующее окружение заменять не нужно:

```bash
python3 --version
python3 -m venv .venv
mkdir -p .tmp/pip .cache/pip
TMPDIR="$PWD/.tmp/pip" .venv/bin/python -m pip install \
  --cache-dir .cache/pip -r requirements.txt
.venv/bin/python -m pip check
```

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

Очистка использует [API 14 — `GET /api/getUserDetailByEmail`](https://automationexercise.com/api_list) с параметром `email`, без пароля. Положительный ответ проверяется по коду, ID и точному email. Отсутствие принимается только при HTTP 200, `responseCode=404`, сообщении `Account not found with this email, try another email!` и отсутствии объекта `user`; отказ `verifyLogin` таким доказательством не является. Документация API 14 описывает только положительный ответ; отрицательный ответ подтверждён на реальном стенде 26.10.2026 для нового неиспользованного email и после удаления собственного тестового аккаунта. Любой другой ответ или таймаут сохраняется как ошибка «очистка не подтверждена». Ошибка начального запроса не отменяет попытку DELETE с исходными реквизитами своего аккаунта; ошибки удаления и контрольного запроса также сохраняются.

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

**Сборка всех 17 тестов без выполнения, браузеров и облачных реквизитов:**

```bash
.venv/bin/python -m pytest tests mobile --collect-only -q
```

Адресные локальные проверки вложений, поиска, очистки и связи Mobile-сессий находятся отдельно от дипломных сценариев. Сеть и чтение `.env` в них запрещены:

```bash
.venv/bin/python -B -m pytest checks -q
```

## Jenkins Freestyle и Selenoid

Задача [anastasia-diplom-python-ci](https://jenkins.qa.guru/job/anastasia-diplom-python-ci/) — **Freestyle**. Подтверждённый UI/API-прогон: **14 passed за 62,02 с**, без ошибок teardown; 8 UI выполнены через Selenoid, 6 API прошли с подтверждённой очисткой четырёх аккаунтов.

В рабочем каталоге Jenkins должны быть установлены зависимости в `.venv` и предоставлен `.env` с Selenoid-настройками. Для шага **Execute shell**:

```bash
#!/bin/bash
set -eu
RUN_DIR=".artifacts/jenkins/$BUILD_NUMBER"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest tests --ui-mode=selenoid -v \
  --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" \
  --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

Для пробного запуска одного UI-теста замените `tests` на `tests/test_catalog.py::test_catalog_has_products_with_names_prices_and_detail_links`. Фикстура создаёт новую сессию на тест, сохраняет диагностику, вызывает `quit()` и запрашивает видео завершённой сессии.

Передавайте в публикацию результаты только текущего `$RUN_DIR`, включая упавшие запуски. Сохраняйте ненулевой код выхода pytest; не заменяйте его успешным кодом загрузчика отчёта. Передача результатов UI/API в [TestOps](https://allure.qa.guru/jobrun/56202) подтверждена.

## Allure Report и TestOps

`allure-results` — исходные JSON и вложения. **Allure Report** — генерируемый HTML-отчёт; **Allure TestOps** — отдельный сервис хранения результатов и тест-кейсов.

При установленном Allure CLI для выбранного `$RUN_DIR`:

```bash
allure generate "$RUN_DIR/allure-results" -o "$RUN_DIR/allure-report"
allure open "$RUN_DIR/allure-report"
```

`allure-pytest` не устанавливает Allure CLI. В Jenkins публикацию настраивают для каталога результатов текущей сборки. [Allure Report сборки #7](https://jenkins.qa.guru/job/anastasia-diplom-python-ci/7/allure/) опубликован.

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

## Структура

- `tests/`, `tests/api/` — UI- и API-тесты, фикстуры браузера и аккаунтов.
- `pages/`, `models/` — Page Objects магазина и модели запросов, ответов и товаров.
- `diplom_qa_python/api/` — HTTP-сессия и общие проверки аккаунтов.
- `mobile/` — конфигурация BrowserStack, фикстуры, Page Object, три теста и получение видео.
- `reporting.py`, `selenoid.py` — вложения Allure и удалённый браузер.
- `docs/` — инструкции, результаты и изображения. Ручные сценарии хранятся в [TestOps](https://allure.qa.guru/project/5398/test-cases).

`.env`, окружение, временные файлы, внутренние отчёты и исходные артефакты исключены из Git.
