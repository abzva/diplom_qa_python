# Запуск и конфигурация

[README](../README.md) · [Результаты и требования](validation.md)

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

Mobile реализован только через BrowserStack. Локальный Android/Appium-режим отсутствует, хотя [требования QA.GURU](https://github.com/qa-guru/diploma-requirements/wiki/MOBILE-тестирование-Python) предусматривают оба режима. Одобрение этого отклонения преподавателем не подтверждено.

Скачивание видео требует прямого доступа к хранилищу: оно не использует `.netrc` и proxy/CA-переменные процесса; TLS-проверка включена.

## Локальный запуск

Каждая команда создаёт отдельный каталог результатов. По умолчанию pytest выбирает `tests/` — 14 UI/API-тестов. Для Mobile каталог указывается явно.

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

**Mobile — 3 теста через BrowserStack:**

```bash
RUN_DIR=".artifacts/runs/mobile-$(date -u +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
.venv/bin/python -m pytest mobile -v \
  --basetemp="$RUN_DIR/pytest-tmp" --alluredir="$RUN_DIR/allure-results" \
  --junitxml="$RUN_DIR/junit.xml" --log-file="$RUN_DIR/run.log"
```

Для одного Mobile-теста вместо `mobile` укажите, например, `mobile/test_search.py::test_search_finds_python_programming_language`.

**Сборка всех 17 тестов без выполнения, браузеров и облачных реквизитов:**

```bash
.venv/bin/python -m pytest tests mobile --collect-only -q
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

Передавайте в публикацию результаты только текущего `$RUN_DIR`, включая упавшие запуски. Сохраняйте ненулевой код выхода pytest; не заменяйте его успешным кодом загрузчика отчёта. Передача результатов UI/API в [TestOps](https://allure.qa.guru/jobrun/56202) подтверждена. **Mobile в Jenkins пока не проверен.**

## Allure Report и TestOps

`allure-results` — исходные JSON и вложения. **Allure Report** — генерируемый HTML-отчёт; **Allure TestOps** — отдельный сервис хранения результатов и тест-кейсов. Успешная загрузка в TestOps не подтверждает публикацию Allure Report в Jenkins.

При установленном Allure CLI для выбранного `$RUN_DIR`:

```bash
allure generate "$RUN_DIR/allure-results" -o "$RUN_DIR/allure-report"
allure open "$RUN_DIR/allure-report"
```

`allure-pytest` не устанавливает Allure CLI. В Jenkins публикацию настраивают для каталога результатов текущей сборки; рабочая ссылка на опубликованный Allure Report пока не подтверждена.

## Позднее видео BrowserStack

Если видео завершённой сессии появилось после teardown, `mobile.attach_video` добавляет его в **новую копию** результатов без повторного теста. Подставьте свои пути и ID; каталог `--output` не должен существовать:

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
