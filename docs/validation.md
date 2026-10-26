# Результаты и требования

[README](../README.md) · [Запуск](running.md)

## UI/API в Jenkins

Подтверждённый прогон кода [4b051a9](https://github.com/abzva/diplom_qa_python/commit/4b051a9c88969be54811b81ac889333b472762bc): **14 passed за 62,02 с**.

- Задача [anastasia-diplom-python-ci](https://jenkins.qa.guru/job/anastasia-diplom-python-ci/), тип Freestyle, Python **3.14.4**.
- **8 UI** через Selenoid, Chrome **156.0.8078.47**.
- **6 API**; очистка всех четырёх созданных в этом прогоне аккаунтов подтверждена.
- Ошибок teardown нет. Результаты загружены в TestOps без ошибок: [jobrun #56202](https://allure.qa.guru/jobrun/56202), [запуск #56722](https://allure.qa.guru/launch/56722).
- MP4-вложение «Видео Selenoid» подтверждено в предыдущем одиночном успешном запуске. Сохранены также [скриншоты вложений UI-06](images/README.md). Полное воспроизведение и наличие видео у всех восьми UI-тестов отдельно не подтверждены.

Результаты относятся к указанному коммиту.

## Mobile

Три сценария отдельно проходили через BrowserStack: **3 passed за 98,24 с**. Wikipedia sample **2.5.194-alpha-2017-05-30**, Samsung Galaxy S23 / Android 13.0.

| Сценарий | Сессия |
|---|---|
| Поиск Python | [MOBILE-01](https://app-automate.browserstack.com/builds/da672467ece5b15b759b1503dd8ae8c7852be96a/sessions/4189c12c3d75e1b918a4232ce6cd1d7cf54a17c6) |
| Замена запроса | [MOBILE-02](https://app-automate.browserstack.com/builds/da672467ece5b15b759b1503dd8ae8c7852be96a/sessions/041756a0f2e2550eadef6c480a31949fbcd34d2a) |
| Очистка запроса | [MOBILE-03](https://app-automate.browserstack.com/builds/da672467ece5b15b759b1503dd8ae8c7852be96a/sessions/1339b106a6c2b64a75e759fc1ae2b0d65d7cfcff) |

Для отдельного [запуска MOBILE-01 с Allure](https://app-automate.browserstack.com/builds/08f506e141fa67697527228d24e16182ed0f5b34/sessions/0a0ce7880f0af9ea4a62b2705b7fd4a47c320612) MP4 получен после завершения сессии и добавлен в копию результатов. Ссылки BrowserStack могут требовать авторизации.

Mobile в Jenkins не проверен; общего прогона всех 17 тестов не было. Это старое учебное приложение: покрыт поиск, а открытие статьи ранее возвращало `An error occurred` и не входит в текущие сценарии.

## Соответствие заданию и QA.GURU

Основание — [Python Base](https://github.com/qa-guru/diploma-requirements/wiki/Python-Base) и связанные страницы [общих](https://github.com/qa-guru/diploma-requirements/wiki/Общие-требования-к-дипломy-Python), [UI](https://github.com/qa-guru/diploma-requirements/wiki/UI-тестирование-Python), [API](https://github.com/qa-guru/diploma-requirements/wiki/API-тестирование-Python) и [Mobile](https://github.com/qa-guru/diploma-requirements/wiki/MOBILE-тестирование-Python) требований.

| Требование | Состояние |
|---|---|
| UI: минимум 7 тестов, бизнес-модули, Page Objects, шаги Allure | 8 тестов в четырёх модулях; реализовано |
| API: минимум 5 тестов, GET/POST/DELETE, относительные endpoint, модели запросов/ответов, проверки статуса и содержимого, логирование | 6 тестов; реализовано |
| Mobile: минимум 3 теста, настройки Pydantic/dotenv, фикстуры и Allure | 3 теста; реализован удалённый режим |
| Mobile: локальный и удалённый режимы с отдельными конфигурациями | Только BrowserStack. Это выбранный объём проекта; одобрение отклонения преподавателем не подтверждено |
| Public-репозиторий, README, requirements.txt, .gitignore, разделение по пакетам, ссылка на Jenkins | Репозиторий доступен публично; файлы и ссылка есть. Общий API-код в `diplom_qa_python`, Page Objects и модели — в отдельных пакетах |
| Опубликованный Allure Report в Jenkins и ссылка в README | Не подтверждены |
| Подготовка пользователя через API для UI-сценария — задание проекта | Реализована в UI-01 |
| Ручные кейсы в TestOps — задание проекта | MAN-01–MAN-05 созданы; 23 шага с ожидаемыми результатами, статус «Черновик», полный ручной прогон не выполнен |
| Mobile в Jenkins и профиль GitHub со ссылками — оставшиеся пункты проекта | Завершение не подтверждено |

**Рекомендации wiki:** параметризация, тесты работы с файлами, дополнительные метки Allure и Telegram-уведомление. HTML-вложение UI указано как необязательное. Ссылка TestOps в общей wiki приветствуется; ручные кейсы входят в задание этого проекта. Эти пожелания не следует смешивать с обязательными минимумами тестов и двумя режимами Mobile.

## Осталось перед сдачей

1. Проверить Mobile в Jenkins и сохранить результаты.
2. Опубликовать Allure Report в Jenkins и добавить рабочую ссылку.
3. Выполнить пять ручных кейсов в [TestOps](https://allure.qa.guru/project/5398/test-cases), записав фактические результаты.
4. Завершить профиль GitHub со ссылками на дипломный проект.
5. Закрыть расхождение с требованием локального Mobile-режима: реализовать его либо получить подтверждение допустимости BrowserStack-only.
6. Проверить воспроизведение UI-видео и наличие вложений у всех восьми UI-тестов.
