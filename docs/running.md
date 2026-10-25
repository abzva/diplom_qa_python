# Подробный запуск и конфигурация

[Краткий README](../README.md) · [Результаты и ограничения](validation.md)

## Установка


Команды для zsh/bash выполняются из корня репозитория. Нужны Python 3.13, а для локального UI — установленный Chrome. Selenium Manager использует `.cache/selenium`; первый запуск может потребовать загрузки ChromeDriver. API не запускает браузер.

Только для нового клона, если `.venv` ещё нет:

```bash
python3.13 -m venv .venv
```

```bash
mkdir -p .tmp/pip .cache/pip
TMPDIR="$PWD/.tmp/pip" .venv/bin/python -m pip install --cache-dir .cache/pip -r requirements.txt
PIP_CACHE_DIR="$PWD/.cache/pip" .venv/bin/python -m pip check
```

Локальные UI/API работают без `.env` и облачных реквизитов. Для Mobile нужен собственный доступ App Automate, доступные минуты и app URL этой сборки. В новом клоне скопируйте [.env.example](../.env.example) в `.env` **только если файла ещё нет**; существующий файл не заменяйте. Заполните пять `BROWSERSTACK_*` полей своими значениями. Тесты APK не загружают; на другом аккаунте приложение должно быть предварительно загружено или разрешено этому аккаунту.

Мобильный объём проекта — **только BrowserStack**; локальный Android-режим не реализован. [Общая инструкция QA.GURU](https://github.com/qa-guru/diploma-requirements/wiki/MOBILE-тестирование-Python) описывает два режима. Выбранный здесь объём отличается от неё; подтверждение отдельного одобрения преподавателем не представлено.

При скачивании Mobile-видео используется отдельная HTTP-сессия без `.netrc`, неявной авторизации и настроек proxy/CA из окружения (`trust_env=False`). TLS-проверка включена, используется стандартный доверенный CA bundle Requests. Скачивание требует прямого доступа к хранилищу; если сеть требует proxy или корпоративный CA, их поддержку нужно настроить явно, не отключая TLS-проверку.

Mobile и Selenoid читают корневой `.env` явно, без интерполяции и перекрытия значениями процесса. Поэтому в Jenkins следует подготовить локальный файл через механизм секретов, а не рассчитывать только на environment variables. `.env` не публикуется. В PyCharm выберите `.venv/bin/python`, pytest и корень проекта как рабочую директорию.

## Проверка доступности API из Jenkins

После установки зависимостей выполните из корня проекта следующий блок. Он делает **один GET**, не следует перенаправлениям, не создаёт аккаунты и не запускает pytest/браузер. Корневой `.env` и мобильная конфигурация не загружаются. Используются BASE_URL и API-таймауты проекта; TLS-проверка включена, повторы не добавлены. Обычные сетевые proxy/CA-настройки Requests сохраняются. Не передавайте реквизиты в BASE_URL.

```bash
.venv/bin/python - <<'PY'
import sys
import requests
from pydantic import ValidationError
from config import settings
from diplom_qa_python.api.session import read_json, response_summary
from models.catalog import ProductsResponse

try:
    response = requests.get(
        settings.base_url + "/api/productsList",
        timeout=settings.api_timeout, allow_redirects=False,
    )
except requests.RequestException as error:
    print("NETWORK_ERROR:", type(error).__name__)
    sys.exit(3)
try:
    body = read_json(response)
except requests.exceptions.JSONDecodeError:
    summary = response_summary(response)
    print("UNEXPECTED_FORMAT:", summary)
    sys.exit(2 if "HTML" in summary else 4)
try:
    catalog = ProductsResponse.model_validate(body)
except ValidationError:
    print("UNEXPECTED_JSON: catalog schema mismatch; HTTP", response.status_code)
    sys.exit(4)
if (response.status_code != 200 or catalog.responseCode != 200
        or not catalog.products
        or any(not p.name.strip() or not p.price.strip() for p in catalog.products)):
    print("UNEXPECTED_JSON: HTTP, business code or product content mismatch")
    sys.exit(4)
print("EXPECTED_JSON: HTTP 200; responseCode 200; catalog validated")
PY
```

Коды выхода: **0** — ожидаемый JSON с проверенными данными; **2** — HTML (описание `HTML verification page` только при совпадении двух сохранённых текстовых признаков); **3** — сетевая ошибка без полученного ответа; **4** — другой неожиданный формат, схема, статус или содержимое. Код 2 не доказывает поставщика защиты или блокировку аккаунта. Тело ответа, cookies и заголовки авторизации команда не печатает. Проверка подготовлена, но из Jenkins ещё не выполнялась; её успех сам по себе не подтверждает POST/DELETE или весь набор.

## Запуск

Ниже самостоятельные команды. Для каждого запуска создаётся новый каталог; не объединяйте результаты разных прогонов.

**Только API — 6 тестов, без браузера:**

```bash
RUN_DIR=".artifacts/runs/api-$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest tests/api -v --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

**Только UI — 8 тестов в локальном Chrome:**

```bash
RUN_DIR=".artifacts/runs/ui-$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest tests/test_login.py tests/test_catalog.py tests/test_product.py tests/test_cart.py -v --ui-mode=local --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

По умолчанию Chrome работает headless; `--headed` показывает окно.

**Общий локальный UI/API-набор — 14 тестов:**

```bash
RUN_DIR=".artifacts/runs/ui-api-$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest tests -v --ui-mode=local --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

**Только Mobile — 3 облачные сессии, нужны BrowserStack-реквизиты:**

```bash
RUN_DIR=".artifacts/runs/mobile-$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest mobile -v --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

Один Mobile-тест: вместо `mobile` укажите `mobile/test_search.py::test_search_finds_python_programming_language`. По умолчанию pytest собирает только `tests/`, без Mobile. Сборка всех 17 без выполнения и без облачных реквизитов:

```bash
.venv/bin/python -m pytest tests mobile --collect-only -q
```

### Удалённый UI — открытый пункт сдачи

Конфигурация сохранена: `SELENOID_URL`, `SELENOID_LOGIN`, `SELENOID_PASS`, `SELENOID_BROWSER_VERSION`, `SELENOID_VIDEO_BASE_URL`; при необходимости отдельная пара `SELENOID_VIDEO_USERNAME`/`SELENOID_VIDEO_PASSWORD`. Адреса: WebDriver `https://selenoid.qa.guru/wd/hub`, видео `https://selenoid.qa.guru/video/`, status `https://selenoid.qa.guru/hub/status`. Версия браузера должна быть подтверждена сервером; повторный `/wd/hub` не добавляется.

**Selenoid недоступен из локального окружения; причина не установлена.** Поддержка remote и MP4 есть в коде, реального подтверждения нет. Подробности — в [ограничениях](validation.md#selenoid-и-оставшиеся-действия).

При настройке **учебного Jenkins** нужно сначала проверить доступ из Jenkins и доступную версию Chrome, затем выполнить один тест:

```bash
RUN_DIR=".artifacts/runs/selenoid-$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest tests/test_catalog.py::test_catalog_has_products_with_names_prices_and_detail_links -v --ui-mode=selenoid --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

Критерий закрытия пункта: тест прошёл удалённо, сессия закрыта, MP4 получен и воспроизводится во вложении этого теста Allure; `Selenoid session and video (finished)` содержит `quit_completed=true`, `video_status=attached`. До этой проверки пункт остаётся открытым.

## Отчёт Allure

Все команды выше сохраняют `allure-results` в отдельный каталог `$RUN_DIR`. Если Allure CLI уже доступен в учебной среде:

```bash
allure generate "$RUN_DIR/allure-results" -o "$RUN_DIR/allure-report"
allure open "$RUN_DIR/allure-report"
```

Python-пакет allure-pytest не устанавливает Allure CLI; CLI должен быть доступен отдельно в учебной среде. Для Jenkins настроить публикацию каталога текущего запуска также при ненулевом exit code pytest, сохранив статус ошибки. Статус внешних Allure Report/TestOps указан в [результатах проверок](validation.md).

## Позднее видео BrowserStack

Если видео собственной завершённой сессии стало доступно после teardown, можно дополнить **копию** результатов без нового теста. Подставить свои локальные пути и ID уже закрытой сессии; каталог output должен быть новым:

```bash
.venv/bin/python -m mobile.attach_video \
  --results .artifacts/your-run/allure-results \
  --output .artifacts/your-run-with-video \
  --session-id YOUR_COMPLETED_SESSION_ID
```

Это шаблон параметров, не готовая команда для запуска без подстановки. Скрипт не создаёт облачную сессию и не меняет оригинал результатов; при недоступном видео возвращает ошибку. Не объединять оригинал и копию в одном отчёте.

## Структура

- `diplom_qa_python/api/` — HTTP-сессия с базовым адресом из фикстуры, helpers аккаунта.
- `models/`, `pages/` — модели API/UI и Page Objects магазина.
- `tests/` — UI, `tests/api/` — API; `tests/conftest.py` — независимые фикстуры.
- `mobile/config.py`, `mobile/conftest.py`, `mobile/pages/` — отдельная мобильная конфигурация, сессия и Page Object.
- `reporting.py`, `mobile/reporting.py`, `selenoid.py` — безопасные вложения и завершение сессий.
- `docs/` — инструкции, ручные кейсы, результаты проверок и иллюстрации. Генерируемые результаты сохраняются локально в `.artifacts/`.
