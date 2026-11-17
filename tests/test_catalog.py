import allure

from models.product import select_search_products
from pages.catalog_page import CatalogPage

pytestmark = [
    allure.parent_suite("UI"),
    allure.epic("UI"),
    allure.feature("Каталог и поиск"),
    allure.suite("Каталог и поиск"),
]


@allure.title("UI-03: Каталог содержит пригодные для выбора товары")
def test_catalog_has_products_with_names_prices_and_detail_links(catalog_page: CatalogPage) -> None:
    with allure.step("Открыть каталог через Products"):
        catalog_page.open()

    with allure.step("Прочитать видимые карточки и проверить ссылки"):
        products = catalog_page.products()

    with allure.step("Проверить непустой каталог, названия и положительные цены"):
        assert products, "The catalog must contain products"
        for product in products:
            assert product.name, f"Empty name for product id={product.product_id}"
            assert product.price > 0, f"Non-positive price for product id={product.product_id}"


@allure.title("UI-04: Поиск находит товар, выбранный из каталога")
def test_search_finds_selected_catalog_product(catalog_page: CatalogPage) -> None:
    with allure.step("Сохранить название и ID товара из каталога"):
        catalog_page.open()
        selected_product, unrelated_product = select_search_products(catalog_page.products())

    with allure.step("Найти товар через интерфейс"):
        catalog_page.search(selected_product.name)

    with allure.step("Проверить исходные ID и название в разделе результатов"):
        catalog_page.should_show_search_result(selected_product, unrelated_product)
