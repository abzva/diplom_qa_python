import allure

from pages.cart_page import CartPage
from pages.catalog_page import CatalogPage
from pages.product_page import ProductPage


pytestmark = [allure.parent_suite("UI"), allure.epic("UI"),
              allure.feature("Корзина"), allure.suite("Корзина")]


@allure.title("UI-06: Корзина содержит два разных товара")
def test_cart_contains_two_different_products(browser):
    with allure.step("Проверить пустую гостевую корзину и выбрать два разных товара"):
        cart = CartPage(browser)
        cart.open()
        cart.should_be_empty()
        catalog = CatalogPage(browser)
        catalog.open()
        products = catalog.products()
        first = products[0]
        different_products = [product for product in products if product.product_id != first.product_id]
        assert different_products, "Two different catalog products are required"
        second = different_products[0]
        product_page = ProductPage(browser)

    with allure.step("Добавить первый товар и продолжить покупки"):
        catalog.open_product(first)
        product_page.add_to_cart()
        cart.continue_shopping()
    with allure.step("Добавить второй товар и открыть корзину"):
        catalog.open()
        catalog.open_product(second)
        product_page.add_to_cart()
        cart.open_from_confirmation()

    with allure.step("Проверить ровно две позиции, цены, количества и суммы"):
        cart.should_contain_exactly([(first, 1), (second, 1)])


@allure.title("UI-07: Корзина учитывает количество 4 и сумму строки")
def test_cart_uses_quantity_selected_before_adding(browser):
    with allure.step("Проверить пустую корзину и открыть выбранный товар"):
        cart = CartPage(browser)
        cart.open()
        cart.should_be_empty()
        catalog = CatalogPage(browser)
        catalog.open()
        selected_product = catalog.select_product()
        catalog.open_product(selected_product)
        product_page = ProductPage(browser)

    with allure.step("Задать количество 4 до добавления и открыть корзину"):
        product_page.set_quantity(4)
        product_page.add_to_cart()
        cart.open_from_confirmation()

    with allure.step("Проверить товар, количество и исходную цену × 4"):
        cart.should_contain_exactly([(selected_product, 4)])


@allure.title("UI-08: Удаление последнего товара опустошает корзину")
def test_removing_last_product_leaves_cart_empty(browser):
    with allure.step("Проверить пустую корзину и выбрать товар"):
        cart = CartPage(browser)
        cart.open()
        cart.should_be_empty()
        catalog = CatalogPage(browser)
        catalog.open()
        selected_product = catalog.select_product()
    with allure.step("Добавить товар и подтвердить его наличие в корзине"):
        catalog.open_product(selected_product)
        ProductPage(browser).add_to_cart()
        cart.open_from_confirmation()
        cart.should_contain_exactly([(selected_product, 1)])

    with allure.step("Удалить добавленный товар через UI"):
        cart.remove(selected_product)

    with allure.step("Проверить пустое состояние и отсутствие товарных строк"):
        cart.should_be_empty()
