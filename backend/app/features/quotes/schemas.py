"""Request and response shapes for the quote checker. Owner: Gabriel.

`ParsedQuote` is what the model must return (validated, never trusted further than that): it only
copies text. Every money figure in `QuoteCheckOut` comes from the quote's own text (checked) or
from the price index, and every comparison is made in plain Python.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# What the model returns -----------------------------------------------------------------------


class ParsedLine(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item: str = Field(
        min_length=1, max_length=200, description="The item as written, e.g. 'Cement (50 kg bag)'"
    )
    unit: str = Field(min_length=1, max_length=40, description="The unit as written, e.g. 'bag'")
    quantity: str = Field(pattern=r"^\d{1,9}(\.\d{1,3})?$", description="As written, digits only, e.g. '100'")
    unit_price: str = Field(
        pattern=r"^\d{1,12}(\.\d{1,2})?$",
        description="Naira per unit as written, no commas or symbol, e.g. '9500'",
    )


class ParsedQuote(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lines: list[ParsedLine] = Field(min_length=1, max_length=200)


# The API ------------------------------------------------------------------------------------


class QuoteCheckIn(BaseModel):
    """Send the quote as a PDF (base64) or as plain text: exactly one of them."""

    model_config = ConfigDict(extra="forbid")

    pdf_base64: str | None = Field(default=None, max_length=7_000_000, description="The quote PDF, base64")
    text: str | None = Field(
        default=None, min_length=1, max_length=30_000, description="Or the quote as text"
    )

    @model_validator(mode="after")
    def _exactly_one(self) -> "QuoteCheckIn":
        if (self.pdf_base64 is None) == (self.text is None):
            raise ValueError("send exactly one of pdf_base64 or text")
        return self


LineFlag = Literal["over_index", "within_index", "not_in_index", "unit_differs", "not_found_in_quote"]


class QuoteLineCheck(BaseModel):
    item: str
    unit: str
    quantity: str
    unit_price_minor: int = Field(description="From the quote's text (checked to appear in it), in kobo")
    line_total_minor: int = Field(description="quantity x unit_price_minor, rounded half up, computed here")
    flag: LineFlag = Field(
        description=(
            "over_index: more than 15% above the index; within_index; not_in_index: no index price; "
            "unit_differs: the index prices another unit; not_found_in_quote: the model's numbers are not in "
            "the quote text, so the line is not compared"
        )
    )
    index_item: str | None = None
    index_unit: str | None = None
    index_price_minor: int | None = Field(default=None, description="The price index median, in kobo")
    percent_above_index: str | None = Field(
        default=None, description="(quote - index) / index x 100, one decimal place; negative when cheaper"
    )
    index_stale: bool | None = Field(default=None, description="The index price is older than 14 days")


class QuoteCheckOut(BaseModel):
    run_id: uuid.UUID = Field(description="The agent_runs row of the parse")
    currency: Literal["NGN"] = "NGN"
    threshold_percent: int
    lines: list[QuoteLineCheck]
    flagged_count: int
    quote_total_minor: int = Field(description="Sum of line_total_minor, computed here")
