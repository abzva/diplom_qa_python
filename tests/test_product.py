import allure

from pages.catalog_page import CatalogPage
from pages.product_page import ProductPage


pytestmark = [allure.parent_suite("UI"), allure.epic("UI"),
              allure.feature("Карточка товара"), allure.suite("Карточка товара")]


@allure.title("UI-05: Карточка соответствует выбранному товару")
def test_product_details_match_selected_catalog_product(browser):
    with allure.step("Сохранить данные выбранного товара из каталога"):
        catalog = CatalogPage(browser)
        catalog.open()
        selected_product = catalog.select_product()

    with allure.step("Открыть карточку выбранного товара"):
        catalog.open_product(selected_product)

    with allure.step("Сравнить ID, название, цену и проверить характеристики"):
        ProductPage(browser).should_match(selected_product)
