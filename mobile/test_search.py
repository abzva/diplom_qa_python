import allure

pytestmark = [allure.parent_suite("Mobile"), allure.epic("Mobile"),
              allure.feature("Поиск Wikipedia"), allure.suite("Поиск Wikipedia")]


@allure.title("MOBILE-01: Поиск находит статью Python (programming language)")
def test_search_finds_python_programming_language(search_page):
    with allure.step("Ввести запрос Python programming"):
        search_page.search("Python programming")
    with allure.step("Проверить точную статью в результатах поиска"):
        search_page.should_find_article("Python (programming language)")


@allure.title("MOBILE-02: Замена запроса обновляет результаты поиска")
def test_replacing_query_updates_results(search_page):
    with allure.step("Найти статью Python и подтвердить исходное состояние"):
        search_page.search("Python programming")
        search_page.should_find_article("Python (programming language)")
    with allure.step("Заменить запрос на Selenium software"):
        search_page.replace_query("Selenium software")
    with allure.step("Проверить статью Selenium и исчезновение прежнего результата"):
        search_page.should_find_article("Selenium (software)")
        search_page.should_not_find_article("Python (programming language)")


@allure.title("MOBILE-03: Очистка удаляет запрос и прежние результаты")
def test_clear_query_removes_text_and_previous_results(search_page):
    with allure.step("Найти статью Python и подтвердить исходные результаты"):
        search_page.search("Python programming")
        search_page.should_find_article("Python (programming language)")
    with allure.step("Нажать очистку поискового запроса"):
        search_page.clear_query()
    with allure.step("Проверить пустое поле и отсутствие прежних результатов"):
        search_page.should_have_cleared_search()
