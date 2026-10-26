"""Independent catalog/search tests: no accounts or browser required."""

import logging

import allure
import requests

from config import settings
from diplom_qa_python.api.session import read_json
from models.catalog import ProductsResponse, SearchErrorResponse, SearchProductRequest


pytestmark = [allure.parent_suite("API"), allure.epic("API"),
              allure.feature("Каталог и поиск"), allure.suite("Каталог и поиск")]


logger = logging.getLogger(__name__)


def read_json_response(response: requests.Response) -> dict:
    logger.info(
        "%s %s -> HTTP %s; Content-Type: %s",
        response.request.method, response.url, response.status_code,
        response.headers.get("Content-Type"),
    )
    assert response.status_code == 200, f"Unexpected HTTP status: {response.status_code}"
    # This API sends JSON with text/html; do not require application/json.
    body = read_json(response)
    assert isinstance(body, dict), "Expected a JSON object"
    logger.info("API body: responseCode=%s", body.get("responseCode"))
    return body


@allure.title("API-01: GET каталога возвращает данные товаров")
def test_get_products_catalog(api_session):
    with allure.step("Получить каталог через GET"):
        response = api_session.get(
            "/api/productsList", timeout=settings.api_timeout,
        )
    with allure.step("Проверить HTTP, строгую модель, бизнес-код и товары"):
        catalog = ProductsResponse.model_validate(read_json_response(response))

        assert catalog.responseCode == 200, catalog
        assert catalog.products, "The catalog is empty"
        for product in catalog.products:
            assert product.name.strip(), f"Empty name for product {product.id}"
            assert product.price.strip(), f"Empty price for product {product.id}"
        logger.info("Validated %s catalog products", len(catalog.products))


@allure.title("API-02: Поиск возвращает исходный ID и название товара")
def test_search_existing_product(api_session):
    with allure.step("Получить каталог и выбрать данные для модели поиска"):
        catalog_response = api_session.get(
            "/api/productsList", timeout=settings.api_timeout,
        )
        catalog = ProductsResponse.model_validate(read_json_response(catalog_response))
        assert catalog.responseCode == 200, catalog
        assert catalog.products, "Cannot select a product from an empty catalog"
        selected_product = catalog.products[0]
        assert selected_product.name.strip(), "Cannot search for an empty product name"
        search = SearchProductRequest(search_product=selected_product.name)

    with allure.step("Отправить POST поиска с сериализованной моделью"):
        response = api_session.post(
            "/api/searchProduct",
            data=search.model_dump(), timeout=settings.api_timeout,
        )
    with allure.step("Проверить HTTP, модель, бизнес-код и найденный товар"):
        results = ProductsResponse.model_validate(read_json_response(response))

        assert results.responseCode == 200, results
        matches = [product for product in results.products if product.id == selected_product.id]
        assert matches, f"Product {selected_product.id} was not found by its catalog name"
        assert all(product.name == selected_product.name for product in matches), matches
        logger.info("Found catalog product id=%s, name=%r", selected_product.id, selected_product.name)


@allure.title("API-03: Сервер отклоняет поиск без обязательного параметра")
def test_search_without_required_parameter(api_session):
    with allure.step("Исключить search_product из сериализованной модели"):
        search = SearchProductRequest(search_product="unused")
        # Deliberately remove the required field from a valid serialized request.
        payload = search.model_dump(exclude={"search_product"})
        assert "search_product" not in payload

    with allure.step("Отправить запрос без параметра на сервер"):
        response = api_session.post(
            "/api/searchProduct",
            data=payload, timeout=settings.api_timeout,
        )
    with allure.step("Проверить HTTP 200, модель, бизнес-код 400 и сообщение"):
        result = SearchErrorResponse.model_validate(read_json_response(response))

        assert result.responseCode == 400, result
        assert result.message == (
            "Bad request, search_product parameter is missing in POST request."
        ), result
        logger.info("Server rejected the missing search_product: %s", result.message)
