"""Guest cart and the shared confirmation of adding a product."""

import logging
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from models.product import ProductSnapshot, parse_price


logger = logging.getLogger(__name__)


class CartPage:
    MODAL = (By.CSS_SELECTOR, "#cartModal")
    ADDED_MESSAGE = (By.CSS_SELECTOR, "#cartModal .modal-body > p:first-child")
    CONTINUE_SHOPPING = (By.CSS_SELECTOR, "#cartModal .close-modal")
    VIEW_CART = (By.CSS_SELECTOR, '#cartModal a[href="/view_cart"]')
    CART = (By.CSS_SELECTOR, "#cart_items #cart_info")
    ROWS = (By.CSS_SELECTOR, '#cart_info_table tbody tr[id^="product-"]')
    EMPTY_MESSAGE = (By.CSS_SELECTOR, "#cart_info #empty_cart p > b")

    def __init__(self, browser):
        self.browser = browser
        self.wait = WebDriverWait(browser, settings.ui_timeout)

    def open(self):
        self.browser.get(f"{settings.base_url}/view_cart")
        self._wait_for_cart()
        logger.info("UI: opened the guest cart")

    def continue_shopping(self):
        self._wait_for_confirmation()
        self.wait.until(conditions.element_to_be_clickable(self.CONTINUE_SHOPPING)).click()
        self.wait.until(conditions.invisibility_of_element_located(self.MODAL))
        logger.info("UI: closed the added-product confirmation")

    def open_from_confirmation(self):
        self._wait_for_confirmation()
        self.wait.until(conditions.element_to_be_clickable(self.VIEW_CART)).click()
        self._wait_for_cart()
        logger.info("UI: opened the cart through View Cart in the confirmation")

    def should_contain_exactly(self, expected: list[tuple[ProductSnapshot, int]]):
        rows = self.wait.until(conditions.visibility_of_all_elements_located(self.ROWS))
        expected_ids = {f"product-{product.product_id}" for product, _ in expected}
        actual_ids = {row.get_attribute("id") for row in rows}
        assert len(rows) == len(expected) and actual_ids == expected_ids, (
            f"Expected {len(expected)} cart rows {expected_ids}, got {len(rows)} rows {actual_ids}"
        )
        for product, quantity in expected:
            row = self.browser.find_element(*self._row_locator(product.product_id))
            name = row.find_element(By.CSS_SELECTOR, ".cart_description h4 a")
            price = row.find_element(By.CSS_SELECTOR, ".cart_price p")
            count = row.find_element(By.CSS_SELECTOR, ".cart_quantity button")
            total = row.find_element(By.CSS_SELECTOR, ".cart_total .cart_total_price")
            assert all(element.is_displayed() for element in (name, price, count, total)), (
                f"Cart fields must be visible for product {product.product_id}"
            )
            assert urlsplit(name.get_attribute("href")).path == f"/product_details/{product.product_id}"
            assert name.text.strip() == product.name, f"Unexpected name for product {product.product_id}"
            assert parse_price(price.text) == product.price, f"Unexpected price for product {product.product_id}"
            assert int(count.text.strip()) == quantity, f"Unexpected quantity for product {product.product_id}"
            assert parse_price(total.text) == product.price * quantity, (
                f"Unexpected total for product {product.product_id}: {total.text!r}, "
                f"expected {product.price} * {quantity}"
            )
            logger.info("UI: cart id=%s, name=%r, price=%s, quantity=%s, total=%s",
                        product.product_id, product.name, product.price, quantity, parse_price(total.text))

    def remove(self, product: ProductSnapshot):
        locator = self._row_locator(product.product_id)
        row = self.wait.until(conditions.visibility_of_element_located(locator))
        button = row.find_element(By.CSS_SELECTOR, ".cart_quantity_delete")
        assert button.get_attribute("data-product-id") == str(product.product_id)
        self.wait.until(conditions.element_to_be_clickable(button)).click()
        self.wait.until(conditions.staleness_of(row))
        self.wait.until_not(conditions.presence_of_element_located(locator))
        logger.info("UI: removed product id=%s; its row is absent", product.product_id)

    def should_be_empty(self):
        message = self.wait.until(conditions.visibility_of_element_located(self.EMPTY_MESSAGE))
        assert message.text == "Cart is empty!", message.text
        self.wait.until(lambda driver: not driver.find_elements(*self.ROWS),
                        message="Product rows remain in the empty cart")
        logger.info("UI: Cart is empty! is visible and no product rows remain")

    def _wait_for_confirmation(self):
        message = self.wait.until(conditions.visibility_of_element_located(self.ADDED_MESSAGE))
        assert message.text == "Your product has been added to cart.", message.text
        logger.info("UI: adding a product was confirmed")

    def _wait_for_cart(self):
        self.wait.until(lambda driver: urlsplit(driver.current_url).path == "/view_cart")
        self.wait.until(conditions.visibility_of_element_located(self.CART))

    @staticmethod
    def _row_locator(product_id: int):
        return By.CSS_SELECTOR, f"#cart_info_table tbody tr#product-{product_id}"
