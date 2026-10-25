# Изображения проекта

Снимки приложений сделаны в наших запусках 22.10.2026, скопированы без редактирования. Просмотрены перед включением в документацию: паролей и ключей на них нет.

- `ui_catalog.png`: UI-03, `.artifacts/ui/20261022T174418295822Z_test_catalog_has_products_with_names_prices_and_detail_links/screen.png`; каталог из прогона [проверки воспроизводимости](../validation.md#ui-и-api). Этот тест прошёл; общий прогон содержал отдельные ошибки.
- `mobile_search.png`: MOBILE-01, `.artifacts/mobile/20261022T142910622911Z_test_search_finds_python_programming_language/screen.png`; реальный поиск в Wikipedia sample в [проверке Allure](../validation.md#mobile-и-видео), 1 passed. Samsung Galaxy S23, Android 13.0.

## Allure TestOps · 25.10.2026

Настоящие скриншоты открытого в Chrome проекта `baz-allure-diplom` (#5398). Сняты после проверки содержимого страниц, без изменения изображения; показывают TestOps, а не отдельный Allure Report. На них видны название учебного проекта и имя владельца кейсов; паролей и токенов нет.

- `testops_launch_overview.png` — [обзор запуска #56722](https://allure.qa.guru/launch/56722), `anastasia-diplom-python-ci - #6`: 14 успешных результатов, 100%.
- `testops_ui_steps.png` — [результат UI-06 #1153434](https://allure.qa.guru/launch/56722/tree/1153434), успешные шаги проверки корзины.
- `testops_ui_attachments.png` — [вложения UI-06](https://allure.qa.guru/launch/56722/tree/1153434/attachments): логи браузера, HTML, сведения Selenoid, MP4 и PNG. Скриншот подтверждает наличие вложений, а не просмотр видео целиком.
- `testops_manual_cases.png` — [пять ручных кейсов](https://allure.qa.guru/project/5398/test-cases), #54176–54180, перенесённых из репозитория. Открыт MAN-01; статус «Черновик», полного ручного прогона не было.

Исходные сырые артефакты остаются локально и исключены из Git. Выбранные изображения предназначены для README. Права на интерфейсы/контент принадлежат соответствующим владельцам; изображения иллюстрируют учебное тестирование.
