"""Pydantic model for a single result from the Meta Ads Library."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class AdResult(BaseModel):
    """Represents one ad returned by Meta Ads Library search.

    This is an intermediate model used before Facebook/Instagram page analysis.
    After page analysis the data is merged into :class:`~leadfinder.models.business.BusinessLead`.
    """

    advertiser_name: str = Field(..., description="Display name of the advertiser (page name)")
    advertiser_url: Optional[str] = Field(default=None, description="URL of the advertiser Facebook page")
    ad_url: Optional[str] = Field(default=None, description="Direct link to the specific ad in the library")
    cta: Optional[str] = Field(default=None, description="Call-to-Action button text (e.g. 'Learn More')")
    platforms: list[str] = Field(default_factory=list, description="Platforms the ad runs on (Facebook, Instagram, etc.)")
    status: str = Field(default="Unknown", description="Ad status: 'Active' or 'Inactive'")
    country: str = Field(..., description="Country code used in the search (e.g. IN, US)")
    keyword: str = Field(..., description="Keyword used in the search")

    model_config = {
        "json_schema_extra": {
            "example": {
                "advertiser_name": "Dream Home Realty",
                "advertiser_url": "https://www.facebook.com/dreamhomerealty",
                "ad_url": "https://www.facebook.com/ads/library/?id=123456789",
                "cta": "Learn More",
                "platforms": ["Facebook", "Instagram"],
                "status": "Active",
                "country": "IN",
                "keyword": "Real Estate",
            }
        }
    }
