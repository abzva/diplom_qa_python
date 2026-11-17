import allure

from pages.catalog_page import CatalogPage
from pages.product_page import ProductPage

pytestmark = [
    allure.parent_suite("UI"),
    allure.epic("UI"),
    allure.feature("Карточка товара"),
    allure.suite("Карточка товара"),
]


@allure.title("UI-05: Карточка соответствует выбранному товару")
def test_product_details_match_selected_catalog_product(
    catalog_page: CatalogPage,
    product_page: ProductPage,
) -> None:
    with allure.step("Сохранить данные выбранного товара из каталога"):
        catalog_page.open()
        selected_product = catalog_page.product_by_id(1)

    with allure.step("Открыть карточку выбранного товара"):
        catalog_page.open_product(selected_product)

    with allure.step("Сравнить ID, название, цену и проверить характеристики"):
        product_page.should_match(selected_product)
