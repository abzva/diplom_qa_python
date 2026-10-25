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

### Ручные кейсы · Allure TestOps

Пять ручных кейсов перенесены в [проект TestOps](https://allure.qa.guru/project/5398/test-cases): условия, данные, приоритеты, 23 шага с отдельными ожидаемыми результатами и очистка. Кейсы имеют статус **«Черновик»**; полный ручной прогон ещё не выполнен.

| Кейс | Проверка |
|---|---|
| [MAN-01 · #54176](https://allure.qa.guru/project/5398/test-cases/54176) | Переключение категории Women / Tops → Men / Jeans |
| [MAN-02 · #54177](https://allure.qa.guru/project/5398/test-cases/54177) | Переключение бренда Polo → H&M |
| [MAN-03 · #54178](https://allure.qa.guru/project/5398/test-cases/54178) | Добавление товара из рекомендаций |
| [MAN-04 · #54179](https://allure.qa.guru/project/5398/test-cases/54179) | Сохранение гостевой корзины после входа |
| [MAN-05 · #54180](https://allure.qa.guru/project/5398/test-cases/54180) | Выход из аккаунта и обновление страницы |

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

### Allure TestOps · запуск Jenkins №6

В [запуске №56722](https://allure.qa.guru/launch/56722), связанном со [сборкой Jenkins №6](https://jenkins.qa.guru/job/anastasia-diplom-python-ci/6/), подтверждены **14 успешных тестов: 8 UI + 6 API**. Скриншоты интерфейса TestOps сделаны 25.10.2026. Для открытия ссылок может потребоваться авторизация.

[![Allure TestOps: 14 успешных тестов, 100%](docs/images/testops_launch_overview.png)](https://allure.qa.guru/launch/56722)

<details>
<summary><b>Шаги UI-теста, вложения и ручные кейсы</b></summary>

**UI-06 — проверка двух разных товаров в корзине:**

[![UI-06: успешные шаги проверки корзины](docs/images/testops_ui_steps.png)](https://allure.qa.guru/launch/56722/tree/1153434)

**Вложения UI-06:** логи, HTML страницы, сведения о Selenoid, PNG и MP4 «Видео Selenoid» (396,76 КБ). [Открыть вложения и видео →](https://allure.qa.guru/launch/56722/tree/1153434/attachments)

[![UI-06: диагностические вложения и видео Selenoid](docs/images/testops_ui_attachments.png)](https://allure.qa.guru/launch/56722/tree/1153434/attachments)

**Пять перенесённых ручных кейсов:**

[![MAN-01–MAN-05 в Allure TestOps](docs/images/testops_manual_cases.png)](https://allure.qa.guru/project/5398/test-cases)

[Происхождение скриншотов](docs/images/README.md)

</details>

<a id="status"></a>

## Текущий статус

- **Реальные результаты на 25.10.2026:** UI/API — **14 passed** в [TestOps, запуск №56722](https://allure.qa.guru/launch/56722); Mobile — **3 passed** отдельным запуском. **Общего подтверждённого запуска «17 passed» не было.** [Результаты и ограничения](docs/validation.md).
- **Automation Exercise:** новый успешный CI-прогон подтверждён. История прежних сетевых отказов и неопределённой очистки аккаунтов сохранена в [диагностике](docs/validation.md); новый прогон не подтверждает удаление аккаунтов прежних запусков.
- **Wikipedia sample:** открытие статьи возвращало `An error occurred`, причина неизвестна. Замена сценария — изменение покрытия, не исправление приложения.
- **Selenoid / UI-видео:** в UI-06 запуска №6 подтверждены вложения браузерных логов, PNG, HTML, сведений о сессии и MP4. [Посмотреть вложения](https://allure.qa.guru/launch/56722/tree/1153434/attachments).
- **Jenkins / TestOps:** передача 14 результатов сборки №6 подтверждена в интерфейсе TestOps. Отдельная публикация Allure Report не проверялась.
- **Ручные кейсы:** MAN-01–MAN-05 перенесены в TestOps и проверены после повторного открытия. Выполнение остаётся отдельным этапом; Passed им не присвоен.

[Инструкции](docs/running.md) · [Проверенные результаты и оставшиеся действия](docs/validation.md)
