# Результаты запусков

[README](../README.md) · [Запуск](running.md)

## UI/API в Jenkins

Подтверждённый прогон кода [4b051a9](https://github.com/abzva/diplom_qa_python/commit/4b051a9c88969be54811b81ac889333b472762bc): **14 passed за 62,02 с**.

- Задача [anastasia-diplom-python-ci](https://jenkins.qa.guru/job/anastasia-diplom-python-ci/), тип Freestyle, Python **3.14.4**.
- **8 UI** через Selenoid, Chrome **156.0.8078.47**.
- **6 API**; очистка всех четырёх созданных в этом прогоне аккаунтов подтверждена.
- Ошибок teardown нет. Результаты загружены в TestOps без ошибок: [jobrun #56202](https://allure.qa.guru/jobrun/56202), [запуск #56722](https://allure.qa.guru/launch/56722).
- MP4-вложение «Видео Selenoid» подтверждено в предыдущем одиночном успешном запуске. Сохранены также [скриншоты вложений UI-06](images/README.md). Полное воспроизведение и наличие видео у всех восьми UI-тестов отдельно не подтверждены.

Результаты относятся к указанному коммиту.

[Allure Report сборки #7](https://jenkins.qa.guru/job/anastasia-diplom-python-ci/7/allure/) опубликован.

## Mobile · 26.10.2026

**3 passed за 161,73 с** — последовательный запуск рабочей версии от 26.10.2026. Wikipedia sample **2.5.194-alpha-2017-05-30**, Samsung Galaxy S23 / Android 13.0, BrowserStack App Automate.

| Тест | Сценарий и сессия | Результат | Завершение |
|---|---|---|---|
| MOBILE-01 | [Поиск Python](https://app-automate.browserstack.com/builds/08f506e141fa67697527228d24e16182ed0f5b34/sessions/38badb2028a471bbeea391fbdf8a2b93afe4c32a) | passed | Закрыта; BrowserStack: passed |
| MOBILE-02 | [Замена запроса](https://app-automate.browserstack.com/builds/08f506e141fa67697527228d24e16182ed0f5b34/sessions/7eac79ae6dd94226404626c7b488fc5306f05c5f) | passed | Закрыта; BrowserStack: passed |
| MOBILE-03 | [Очистка запроса](https://app-automate.browserstack.com/builds/08f506e141fa67697527228d24e16182ed0f5b34/sessions/58b02e19e0e9f60c52dba8b838057a35caa81320) | passed | Закрыта; BrowserStack: passed |

Все три вызова `quit()` завершились успешно; ошибок teardown и обновления статуса BrowserStack нет. Для каждой сессии подтверждено пустое начальное состояние поиска.

При teardown видео не прикрепилось: сервер вернул HTTP 200 и Content-Type MP4, но содержимое не прошло проверку формата. Отдельное получение через `mobile.attach_video` для MOBILE-01 завершилось `ReadTimeout` при чтении данных сессии. Видео нового прогона не получены и не просмотрены; исходные результаты сохранены.

Ссылки BrowserStack могут требовать авторизации. Результаты Mobile сохранены отдельно от опубликованного UI/API-отчёта Jenkins; они не загружены в TestOps.

## Реализация

- UI: [Page Objects](../pages/) и восемь сценариев в `tests/`.
- API: [Pydantic-модели](../models/) формируют body POST-запросов и десериализуют ответы; шесть сценариев в `tests/api/`.
- Связь API/UI: [фикстура `test_user`](../tests/conftest.py) создаёт аккаунт для UI-входа; очистка подтверждает его отсутствие.
- Mobile: [конфигурация](../mobile/config.py), [Page Object Wikipedia](../mobile/pages/search_page.py), [три сценария](../mobile/test_search.py).
- Ручные кейсы: [MAN-01–MAN-05, #54176–54180](https://allure.qa.guru/project/5398/test-cases); 23 шага с ожидаемыми результатами, статус «Черновик». Полный ручной прогон не выполнен.

## Границы результатов

UI/API и Mobile выполнены отдельными запусками. Wikipedia sample — старое учебное приложение: покрыт поиск; открытие статьи ранее возвращало `An error occurred` и не входит в сценарии.

Сохранённые скриншоты относятся к датам, указанным в [описании изображений](images/README.md). Скачивание MP4 и проверка формата не означают полного просмотра видео.
