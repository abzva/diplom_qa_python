import allure

from pages.cart_page import CartPage
from pages.catalog_page import CatalogPage
from pages.product_page import ProductPage

pytestmark = [
    allure.parent_suite("UI"),
    allure.epic("UI"),
    allure.feature("Корзина"),
    allure.suite("Корзина"),
]


@allure.title("UI-06: Корзина содержит два разных товара")
def test_cart_contains_two_different_products(
    cart_page: CartPage,
    catalog_page: CatalogPage,
    product_page: ProductPage,
) -> None:
    with allure.step("Проверить пустую гостевую корзину и выбрать два разных товара"):
        cart_page.open()
        cart_page.should_be_empty()
        catalog_page.open()
        blue_top = catalog_page.product_by_id(1)
        men_tshirt = catalog_page.product_by_id(2)

    with allure.step("Добавить первый товар и продолжить покупки"):
        catalog_page.open_product(blue_top)
        product_page.add_to_cart()
        cart_page.continue_shopping()
    with allure.step("Добавить второй товар и открыть корзину"):
        catalog_page.open()
        catalog_page.open_product(men_tshirt)
        product_page.add_to_cart()
        cart_page.open_from_confirmation()

    with allure.step("Проверить ровно две позиции, цены, количества и суммы"):
        cart_page.should_contain_exactly([(blue_top, 1), (men_tshirt, 1)])


@allure.title("UI-07: Корзина учитывает количество 4 и сумму строки")
def test_cart_uses_quantity_selected_before_adding(
    cart_page: CartPage,
    catalog_page: CatalogPage,
    product_page: ProductPage,
) -> None:
    with allure.step("Проверить пустую корзину и открыть выбранный товар"):
        cart_page.open()
        cart_page.should_be_empty()
        catalog_page.open()
        selected_product = catalog_page.product_by_id(1)
        catalog_page.open_product(selected_product)

    with allure.step("Задать количество 4 до добавления и открыть корзину"):
        product_page.set_quantity(4)
        product_page.add_to_cart()
        cart_page.open_from_confirmation()

    with allure.step("Проверить товар, количество и исходную цену × 4"):
        cart_page.should_contain_exactly([(selected_product, 4)])


@allure.title("UI-08: Удаление последнего товара опустошает корзину")
def test_removing_last_product_leaves_cart_empty(
    cart_page: CartPage,
    catalog_page: CatalogPage,
    product_page: ProductPage,
) -> None:
    with allure.step("Проверить пустую корзину и выбрать товар"):
        cart_page.open()
        cart_page.should_be_empty()
        catalog_page.open()
        selected_product = catalog_page.product_by_id(1)
    with allure.step("Добавить товар и подтвердить его наличие в корзине"):
        catalog_page.open_product(selected_product)
        product_page.add_to_cart()
        cart_page.open_from_confirmation()
        cart_page.should_contain_exactly([(selected_product, 1)])

    with allure.step("Удалить добавленный товар через UI"):
        cart_page.remove(selected_product)

    with allure.step("Проверить пустое состояние и отсутствие товарных строк"):
        cart_page.should_be_empty()
