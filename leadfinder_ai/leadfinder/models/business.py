"""Pydantic model representing a business lead."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BusinessLead(BaseModel):
    """Represents a single business lead discovered via Meta Ads Library."""

    id: Optional[int] = Field(default=None, description="Database unique identifier")
    name: str = Field(..., description="Name of the business")
    facebook: Optional[str] = Field(default=None, description="Facebook page URL")
    instagram: Optional[str] = Field(default=None, description="Instagram profile URL")
    followers: Optional[int] = Field(default=None, ge=0, description="Number of followers on FB or IG")
    phone: Optional[str] = Field(default=None, description="Normalized phone number")
    website: Optional[str] = Field(default=None, description="Website URL if found")
    whatsapp: Optional[bool] = Field(default=None, description="Whether WhatsApp contact is available")
    cta: Optional[str] = Field(default=None, description="Call-to-Action type from the ad")
    country: Optional[str] = Field(default=None, description="Country of the lead")
    keyword: Optional[str] = Field(default=None, description="Keyword used to find the lead")
    score: Optional[int] = Field(default=None, ge=0, le=100, description="Lead quality score (0-100)")
    created_at: Optional[datetime] = Field(default=None, description="Timestamp when record was created")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Dream Home Realty",
                "facebook": "https://facebook.com/dreamhomerealty",
                "instagram": "https://instagram.com/dreamhomerealty",
                "followers": 9,
                "phone": "+919382380980",
                "website": None,
                "whatsapp": True,
                "cta": "Learn More",
                "country": "India",
                "keyword": "Real Estate",
                "score": 98,
            }
        }
    }

    def to_db_dict(self) -> dict:
        """Return a dict suitable for database insertion (excludes id and created_at)."""
        return self.model_dump(exclude={"id", "created_at"}, exclude_none=False)
