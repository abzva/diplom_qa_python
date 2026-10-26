"""The selected product's information, scoped away from other page sections."""

import logging
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from models.product import ProductSnapshot, parse_price


logger = logging.getLogger(__name__)


class ProductPage:
    INFORMATION = (By.CSS_SELECTOR, ".product-details .product-information")
    QUANTITY = (By.CSS_SELECTOR, "input#quantity")
    ADD_TO_CART = (By.CSS_SELECTOR, "button.cart")

    def __init__(self, browser):
        self.browser = browser
        self.wait = WebDriverWait(browser, settings.ui_timeout)

    def should_match(self, expected: ProductSnapshot):
        self.wait.until(
            lambda driver: urlsplit(driver.current_url).path
            == f"/product_details/{expected.product_id}"
        )
        info = self.wait.until(conditions.visibility_of_element_located(self.INFORMATION))
        name = info.find_element(By.CSS_SELECTOR, ":scope > h2")
        price = info.find_element(By.CSS_SELECTOR, ":scope > span > span")
        assert name.is_displayed() and price.is_displayed(), "Product name/price must be visible"
        assert name.text.strip() == expected.name, (
            f"Product name differs: catalog={expected.name!r}, details={name.text!r}"
        )
        actual_price = parse_price(price.text)
        assert actual_price == expected.price, (
            f"Product price differs: catalog={expected.price}, details={actual_price}"
        )

        attributes = {}
        for paragraph in info.find_elements(By.CSS_SELECTOR, ":scope > p"):
            assert paragraph.is_displayed(), "Product attributes must be visible"
            label, separator, value = paragraph.text.partition(":")
            if separator:
                attributes[label.strip()] = value.strip()
        for label in ("Category", "Availability", "Condition", "Brand"):
            assert attributes.get(label), f"Missing or empty product attribute: {label}"

        quantity = info.find_element(*self.QUANTITY)
        add_button = info.find_element(*self.ADD_TO_CART)
        assert quantity.is_displayed() and quantity.is_enabled(), "Quantity must be editable"
        assert add_button.is_displayed() and add_button.is_enabled(), "Add to cart must be available"
        logger.info("UI: product id=%s matches the saved catalog data; attributes are visible", expected.product_id)

    def set_quantity(self, quantity: int):
        info = self.wait.until(conditions.visibility_of_element_located(self.INFORMATION))
        field = self.wait.until(conditions.element_to_be_clickable(
            info.find_element(*self.QUANTITY)
        ))
        field.clear()
        field.send_keys(str(quantity))
        self.wait.until(lambda _: field.get_attribute("value") == str(quantity))
        logger.info("UI: set product quantity to %s before adding", quantity)

    def add_to_cart(self):
        info = self.wait.until(conditions.visibility_of_element_located(self.INFORMATION))
        self.wait.until(conditions.element_to_be_clickable(
            info.find_element(*self.ADD_TO_CART)
        )).click()
        logger.info("UI: clicked Add to cart in the selected product's information")
