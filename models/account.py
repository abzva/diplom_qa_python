"""Account request/response models shared by API tests and UI preparation."""

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class Credentials(BaseModel):
    email: str
    password: str = Field(repr=False)


class CreateAccountRequest(Credentials):
    name: str
    title: str = "Mrs"
    birth_date: str = "1"
    birth_month: str = "1"
    birth_year: str = "1995"
    firstname: str = "Diploma"
    lastname: str = "Test"
    company: str = "QA training"
    address1: str = "1 Test Street"
    address2: str = ""
    country: str = "Canada"
    zipcode: str = "A1A1A1"
    state: str = "Test State"
    city: str = "Test City"
    mobile_number: str = "0000000000"


class AccountResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", hide_input_in_errors=True)

    responseCode: StrictInt
    message: StrictStr
