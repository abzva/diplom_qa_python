<h1 align="center">Диплом QA.GURU · Python</h1>

Автотесты интернет-магазина **Automation Exercise** и Android-приложения **Wikipedia sample**. Проект объединяет 8 UI-, 6 API- и 3 Mobile-сценария: Page Objects, подготовку пользователя через API, проверку моделей и диагностику Allure. Результаты запусков и ограничения приведены в разделе статуса.

<p align="center">
  <img src="docs/images/tech/python.svg" width="44" height="44" alt="Python" title="Python"> 
  <img src="docs/images/tech/pytest.svg" width="44" height="44" alt="pytest" title="pytest"> 
  <img src="docs/images/tech/selenium.svg" width="44" height="44" alt="Selenium" title="Selenium"> 
  <img src="docs/images/tech/pydantic.svg" width="44" height="44" alt="Pydantic" title="Pydantic"> 
  <img src="docs/images/tech/appium.svg" width="44" height="44" alt="Appium" title="Appium">
</p>
<p align="center">Python · pytest · Selenium · requests · Pydantic · Appium · BrowserStack · Allure</p>

<p align="center">
  <a href="#products">Продукты</a> · <a href="#coverage">Покрытие</a> ·
  <a href="#run">Запуск</a> · <a href="#reporting">Отчётность</a> · <a href="#status">Статус</a>
</p>

<a id="products"></a>

## Тестируемые продукты

- **[Automation Exercise](https://automationexercise.com/)** — UI магазина и [API](https://automationexercise.com/api_list): вход, каталог, поиск, карточка, корзина, жизненный цикл своего аккаунта. Без покупок и оплаты.
- **[Wikipedia Android sample](https://www.browserstack.com/app-automate/sample-apps/android/WikipediaSample.apk)** — поиск, замена и очистка запроса через BrowserStack. Версия **2.5.194-alpha-2017-05-30**, Samsung Galaxy S23 / Android 13.0. Это старый учебный sample, не актуальная Wikipedia.

<a id="coverage"></a>

## Покрытие · 17 сценариев

### UI · 8

- **UI-01** — вход созданным через API пользователем: имя и Logout.
- **UI-02** — неверные реквизиты: ошибка, форма сохранена, авторизации нет.
- **UI-03** — каталог: названия, положительные цены, ссылки на карточки.
- **UI-04** — поиск: исходный товар найден по сохранённым ID и названию.
- **UI-05** — карточка совпадает с данными выбранного товара из каталога.
- **UI-06** — два товара в корзине: состав, цены, количество и суммы строк.
- **UI-07** — количество 4: сумма равна исходной цене × 4.
- **UI-08** — удаление последнего товара: строка исчезает, корзина пуста.

### API · 6

- **API-01** — GET каталога: содержимое и структура товаров.
- **API-02** — POST поиска: товар из свежего каталога найден.
- **API-03** — POST поиска без обязательного поля: сервер возвращает ошибку.
- **API-04** — POST создания аккаунта: исходные реквизиты принимаются.
- **API-05** — DELETE аккаунта: прежние реквизиты больше не принимаются.
- **API-06** — неверный пароль отвергается, исходный продолжает работать.

### Mobile · 3

- **MOBILE-01** — поиск `Python programming` находит `Python (programming language)`.
- **MOBILE-02** — замена запроса показывает `Selenium (software)` и убирает прежний результат.
- **MOBILE-03** — очистка удаляет введённый текст и прежние результаты.

Дополнительно подготовлены **[5 ручных кейсов](docs/manual_test_cases.md)**. Их ещё предстоит перенести и выполнить в TestOps.

## Как связаны API и UI

Фикстура создаёт уникального пользователя через API; Page Object выполняет UI-вход и проверяет имя. Очистка зарегистрирована заранее: удаляет только свой аккаунт и отдельно подтверждает отсутствие. Ошибки очистки не скрываются; её API-вызовы не считаются самостоятельными тестами.

Pydantic-модели `CreateAccountRequest`, `Credentials`, `SearchProductRequest` сериализуют поля запросов; `AccountResponse`, `ProductsResponse`, `SearchErrorResponse` разбирают ответы со строгой проверкой типов. HTTP-статус и бизнес-код проверяются отдельно. UI-снимок `ProductSnapshot` не смешан с API-моделью; цены сравниваются через `Decimal`. Тесты используют отдельные сессии и ожидания состояния без `sleep` и автоматических ретраев.

<a id="run"></a>

## Установка и запуск

Из корня проекта, Python 3.13; для локального UI нужен Chrome. Создавайте `.venv` только если её ещё нет:

```bash
python3.13 -m venv .venv
mkdir -p .tmp/pip .cache/pip
TMPDIR="$PWD/.tmp/pip" .venv/bin/python -m pip install \
  --cache-dir .cache/pip -r requirements.txt
.venv/bin/python -m pip check
```

**UI — локальный Chrome, 8 тестов:**

```bash
RUN_DIR=".artifacts/runs/ui-$(date -u +%Y%m%dT%H%M%S)"
.venv/bin/python -m pytest \
  tests/test_login.py tests/test_catalog.py tests/test_product.py tests/test_cart.py \
  --ui-mode=local -v --alluredir="$RUN_DIR/allure-results"
```

**API — без браузера, 6 тестов:**

```bash
RUN_DIR=".artifacts/runs/api-$(date -u +%Y%m%dT%H%M%S)"
.venv/bin/python -m pytest tests/api -v --alluredir="$RUN_DIR/allure-results"
```

**Mobile — только BrowserStack, 3 теста:**

```bash
RUN_DIR=".artifacts/runs/mobile-$(date -u +%Y%m%dT%H%M%S)"
.venv/bin/python -m pytest mobile -v --alluredir="$RUN_DIR/allure-results"
```

UI/API не требуют облачных реквизитов. Для Mobile нужны собственный доступ App Automate, минуты и пять `BROWSERSTACK_*` полей из [.env.example](.env.example) в локальном `.env`; существующий файл не заменяйте. APK тестами не загружается. Android SDK, эмулятор и локальный Appium не нужны.

[Подробная настройка, общий запуск 14 тестов, Selenoid и команды Allure →](docs/running.md)

<a id="reporting"></a>

## Отчётность и реальные материалы

Allure: группы UI/API/Mobile, названия, шаги и безопасные вложения. **UI:** PNG, HTML и логи; **API:** запрос/ответ и транспортные ошибки; **Mobile:** PNG, page source, ссылка на сессию и видео. Секретные поля маскируются; диагностика собирается до закрытия сессии.

<details>
<summary><b>Снимки наших реальных запусков · 22.10.2026</b></summary>

<p>Каталог Automation Exercise и поиск Wikipedia. Это снимки приложений, не скриншоты визуального Allure Report. Нажмите для просмотра оригинала.</p>
<p>
  <a href="docs/images/ui_catalog.png"><img src="docs/images/ui_catalog.png" width="440" alt="UI-03: каталог Automation Exercise"></a>
  <a href="docs/images/mobile_search.png"><img src="docs/images/mobile_search.png" width="210" alt="MOBILE-01: найденная статья Python в Wikipedia sample"></a>
</p>

[Происхождение изображений](docs/images/README.md)

</details>

**[Видео реальной Mobile-сессии →](https://app-automate.browserstack.com/builds/08f506e141fa67697527228d24e16182ed0f5b34/sessions/0a0ce7880f0af9ea4a62b2705b7fd4a47c320612)** Поиск Python, сессия закрыта; MP4 получен и приложен к копии Allure-результата. Для просмотра может требоваться доступ к BrowserStack; ссылка не гарантирует бессрочное хранение видео.

Скриншоты Allure Report — обзор и тест со вложениями — и UI-видео будут добавлены после проверки учебной инфраструктуры.

<a id="status"></a>

## Текущий статус

- **Реальные результаты:** Mobile — 3 passed отдельно. Последний полный UI/API-прогон — 13 passed, 1 failed и 1 teardown error. **Общего подтверждённого запуска «17 passed» не было.** [Результаты и ограничения](docs/validation.md).
- **Automation Exercise:** последняя выборочная проверка 6 API + UI-01 — 4 failed / 7 errors (включая setup/teardown): HTML вместо JSON и ReadTimeout. Создание/очистка четырёх новых аккаунтов не подтверждены; сохраняется и прежняя неопределённая очистка одного аккаунта. [Диагностика и результаты](docs/validation.md).
- **Wikipedia sample:** открытие статьи возвращало `An error occurred`, причина неизвестна. Замена сценария — изменение покрытия, не исправление приложения.
- **Selenoid / UI-видео:** по предоставленному результату из Jenkins один удалённый UI-тест прошёл: **1 passed за 9,96 с**, Chrome 156.0.8078.47. Исправлена ошибка сбора браузерных логов; исправление и получение MP4 требуют проверки в Jenkins. [Подробности](docs/validation.md).
- **Jenkins / Allure Report / TestOps:** создана учебная Jenkins job и настроена связь с TestOps. Один удалённый UI-запуск прошёл; передача результатов в TestOps и публикация Allure Report ещё не подтверждены. Проверенные ссылки добавим после запуска; ручные кейсы нужно перенести и выполнить.

[Инструкции](docs/running.md) · [Проверенные результаты и оставшиеся действия](docs/validation.md)
