"""Product listing; hover overlays and recommendations are outside our locators."""

import logging
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from models.product import ProductSnapshot, parse_price


logger = logging.getLogger(__name__)


class CatalogPage:
    PRODUCTS_LINK = (By.CSS_SELECTOR, 'header .shop-menu a[href="/products"]')
    TITLE = (By.CSS_SELECTOR, ".features_items > h2.title")
    CARDS = (By.CSS_SELECTOR, ".features_items .product-image-wrapper")
    INFO = (By.CSS_SELECTOR, ".single-products > .productinfo")
    DETAILS_LINK = (By.CSS_SELECTOR, '.choose a[href^="/product_details/"]')
    SEARCH_INPUT = (By.CSS_SELECTOR, "#search_product")
    SEARCH_SUBMIT = (By.CSS_SELECTOR, "#submit_search")

    def __init__(self, browser):
        self.browser = browser
        self.wait = WebDriverWait(browser, settings.ui_timeout)

    def open(self):
        logger.info("UI: opening the catalog through the Products navigation link")
        self.browser.get(f"{settings.base_url}/")
        self.wait.until(conditions.element_to_be_clickable(self.PRODUCTS_LINK)).click()
        self.wait.until(lambda driver: urlsplit(driver.current_url).path == "/products")
        title = self.wait.until(conditions.visibility_of_element_located(self.TITLE))
        assert title.text == "ALL PRODUCTS", title.text

    def products(self) -> list[ProductSnapshot]:
        cards = self.wait.until(conditions.visibility_of_all_elements_located(self.CARDS))
        products = [self._read_card(card) for card in cards]
        logger.info("UI: read %s catalog cards from their main productinfo blocks", len(products))
        return products

    def select_product(self) -> ProductSnapshot:
        # Any available card is suitable; no fixed SKU, price or ordering assertion.
        card = self.wait.until(conditions.visibility_of_element_located(self.CARDS))
        product = self._read_card(card)
        logger.info("UI: saved catalog data before navigation: %s", product)
        return product

    def open_product(self, product: ProductSnapshot):
        link = (By.CSS_SELECTOR,
                f'.features_items .choose a[href="/product_details/{product.product_id}"]')
        self.wait.until(conditions.element_to_be_clickable(link)).click()
        logger.info("UI: clicked View Product for id=%s", product.product_id)

    def search(self, name: str):
        search_input = self.wait.until(conditions.element_to_be_clickable(self.SEARCH_INPUT))
        search_input.clear()
        search_input.send_keys(name)
        self.wait.until(conditions.element_to_be_clickable(self.SEARCH_SUBMIT)).click()
        logger.info("UI: submitted product search for %r", name)

    def should_show_search_result(self, expected: ProductSnapshot):
        # The same listing becomes the results section after the UI submits search.
        # Wait for its new heading before reading cards, never use the old catalog.
        self.wait.until(conditions.text_to_be_present_in_element(self.TITLE, "SEARCHED PRODUCTS"))
        self.wait.until(conditions.visibility_of_element_located(self.TITLE))
        matches = [product for product in self.products()
                   if product.product_id == expected.product_id]
        assert matches, f"Product id={expected.product_id} is missing from search results"
        assert all(product.name == expected.name for product in matches), (
            f"Search result name differs from catalog name {expected.name!r}: {matches}"
        )
        logger.info("UI: search results contain id=%s, name=%r", expected.product_id, expected.name)

    def _read_card(self, card) -> ProductSnapshot:
        info = card.find_element(*self.INFO)
        name = info.find_element(By.CSS_SELECTOR, ":scope > p")
        price = info.find_element(By.CSS_SELECTOR, ":scope > h2")
        add_button = info.find_element(By.CSS_SELECTOR, "a[data-product-id]")
        link = card.find_element(*self.DETAILS_LINK)
        assert name.is_displayed() and price.is_displayed() and link.is_displayed(), (
            "Catalog name, price and View Product must be visible"
        )
        product_id = int(add_button.get_attribute("data-product-id"))
        assert urlsplit(link.get_attribute("href")).path == f"/product_details/{product_id}", (
            f"View Product points to a different product than card id={product_id}"
        )
        return ProductSnapshot(product_id, name.text.strip(), parse_price(price.text))
