"""Lead scoring utility for LeadFinder AI.

Calculates a lead score (0-100) based on the presence of contact info
and business metrics.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("leadfinder.utils.scorer")


def calculate_score(lead: dict | Any) -> int:
    """Calculate a lead score between 0 and 100.

    Scoring rules:
    - Running Ads: +30 (always True in our context)
    - Phone found: +20
    - WhatsApp found: +20
    - Followers < 1000: +20 (small business needs more help)
    - No website: +30 (prime candidate for web dev services)
    - Website exists: -20 (already has a website)

    Args:
        lead: A dictionary or a BusinessLead model instance representing the lead.

    Returns:
        Integer score from 0 to 100.
    """
    # Handle dict vs model instance
    if isinstance(lead, dict):
        phone = lead.get("phone")
        whatsapp = lead.get("whatsapp", False)
        followers = lead.get("followers")
        website = lead.get("website")
    else:
        phone = getattr(lead, "phone", None)
        whatsapp = getattr(lead, "whatsapp", False)
        followers = getattr(lead, "followers", None)
        website = getattr(lead, "website", None)

    score = 30  # Base score (Running Ads)

    if phone:
        score += 20

    if whatsapp:
        score += 20

    if followers is not None and followers < 1000:
        score += 20

    if not website:
        score += 30
    else:
        score -= 20

    # Clamp the result between 0 and 100
    final_score = max(0, min(100, score))
    
    logger.debug("Calculated score %d for lead (phone=%s, wa=%s, fol=%s, web=%s)",
                 final_score, bool(phone), bool(whatsapp), followers, bool(website))
    
    return final_score
