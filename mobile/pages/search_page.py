"""Search screen of BrowserStack's Wikipedia 2.5.194 alpha sample."""

import logging

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait


logger = logging.getLogger(__name__)


class SearchPage:
    OPEN_SEARCH = (AppiumBy.ACCESSIBILITY_ID, "Search Wikipedia")
    SEARCH_INPUT = (AppiumBy.ID, "org.wikipedia.alpha:id/search_src_text")
    RESULTS = (AppiumBy.ID, "org.wikipedia.alpha:id/search_results_list")
    RESULT_TITLE = (AppiumBy.ID, "org.wikipedia.alpha:id/page_list_item_title")
    CLEAR_QUERY = (AppiumBy.ID, "org.wikipedia.alpha:id/search_close_btn")
    RECENT_PANEL = (AppiumBy.ID, "org.wikipedia.alpha:id/search_panel_recent")

    def __init__(self, driver, timeout=25):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def open_fresh_search(self):
        # This 2017 sample opens the main screen directly; do not assume that
        # onboarding from a newer Wikipedia release exists in this build.
        logger.info("Open Wikipedia search")
        self.wait.until(conditions.element_to_be_clickable(self.OPEN_SEARCH)).click()
        self.wait.until(conditions.visibility_of_element_located(self.RECENT_PANEL))
        self.wait.until(self._query_is_empty, message="New session must start with an empty query")
        self.wait.until(conditions.invisibility_of_element_located(self.RESULTS))
        self.wait.until(lambda driver: [element.text for element in
            driver.find_element(*self.RECENT_PANEL).find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")
            if element.is_displayed()] == ["Recent searches:"],
            message="New session must have an empty recent-search history")
        logger.info("Fresh session verified: empty query, no search history or results")

    def _query_is_empty(self, driver):
        field = driver.find_element(*self.SEARCH_INPUT)
        # Android can expose the hint as text when the editable value is empty.
        return field.is_displayed() and field.text in ("", "Search…")

    def search(self, query):
        field = self.wait.until(conditions.element_to_be_clickable(self.SEARCH_INPUT))
        logger.info("Search Wikipedia for %r", query)
        field.send_keys(query)
        self.wait.until(lambda driver: driver.find_element(*self.SEARCH_INPUT).text == query,
                        message="Search field must contain the entered query")

    def _find_visible_article(self, expected_title):
        results = self.driver.find_element(*self.RESULTS)
        return next((element for element in results.find_elements(*self.RESULT_TITLE)
                     if element.is_displayed() and element.text == expected_title), False)

    def should_find_article(self, expected_title):
        self.wait.until(conditions.visibility_of_element_located(self.RESULTS))

        self.wait.until(lambda _: self._find_visible_article(expected_title),
                        message=f"Expected article {expected_title!r} in Wikipedia search results")
        logger.info("Found the expected article: %s", expected_title)

    def replace_query(self, query):
        self.wait.until(conditions.element_to_be_clickable(self.SEARCH_INPUT)).clear()
        self.search(query)

    def should_not_find_article(self, old_title):
        self.wait.until(lambda _: not self._find_visible_article(old_title),
                        message=f"Previous result {old_title!r} must disappear after changing the query")
        logger.info("Previous result no longer shown: %s", old_title)

    def clear_query(self):
        self.wait.until(conditions.element_to_be_clickable(self.CLEAR_QUERY)).click()
        logger.info("Clicked Clear query")

    def should_have_cleared_search(self):
        self.wait.until(self._query_is_empty, message="Search query should be cleared")
        self.wait.until(conditions.invisibility_of_element_located(self.RESULTS))
        self.wait.until(conditions.visibility_of_element_located(self.RECENT_PANEL))
        self.wait.until(lambda driver: not any(
            title.is_displayed() for title in driver.find_elements(*self.RESULT_TITLE)
        ), message="Previous search results must no longer be visible")
        logger.info("Query cleared and previous result rows are no longer displayed")
