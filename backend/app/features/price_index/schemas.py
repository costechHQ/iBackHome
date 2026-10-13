"""Shapes for the price index."""

from datetime import date

from pydantic import BaseModel, Field


class SurveyRow(BaseModel):
    """One line of the materials price survey, already cleaned."""

    item: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=60)
    price_minor: int = Field(gt=0)
    supplier: str = Field(min_length=1, max_length=120)
    observed_on: date
    source: str = Field(default="survey", max_length=60)


class CurrentPrice(BaseModel):
    """The index price of one item: the median of each supplier's latest price."""

    item_key: str
    item: str
    unit: str
    currency: str
    price_minor: int
    low_minor: int
    high_minor: int
    supplier_count: int
    last_observed_on: date
    stale: bool = Field(description="True when the newest observation is older than 14 days")
