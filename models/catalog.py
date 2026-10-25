"""API catalog fields used by the tests; separate from the UI snapshot."""

from pydantic import BaseModel, ConfigDict


class SearchProductRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    search_product: str


class Product(BaseModel):
    # Extra fields (brand/category) are allowed by the observed API format.
    # We validate only the fields used by these scenarios, without coercion.
    model_config = ConfigDict(strict=True, extra="ignore")

    id: int
    name: str
    price: str


class ProductsResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    responseCode: int
    products: list[Product]


class SearchErrorResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    responseCode: int
    message: str
