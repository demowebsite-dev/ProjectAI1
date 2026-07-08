"""TXT exporter for LeadFinder AI.

Exports a list of lead dictionaries into a formatted text file.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("leadfinder.exporters.txt")


def export_txt(leads: list[dict[str, Any]], filepath: str) -> str:
    """Export a list of leads to a formatted text file.

    Format per lead:
    ```
    Business
    Dream Home Realty

    Followers
    9

    Phone
    9382380980

    WhatsApp
    YES

    Website
    NO

    Score
    98

    --------------------------------
    ```

    Args:
        leads: List of lead dictionaries.
        filepath: Output text file path.

    Returns:
        The absolute path to the saved file.
    """
    if not filepath.endswith(".txt"):
        filepath += ".txt"

    with open(filepath, mode="w", encoding="utf-8") as f:
        for lead in leads:
            def get_val(key, default=""):
                if isinstance(lead, dict):
                    actual_key = "name" if key == "business" else key
                    return lead.get(actual_key, default)
                else:
                    actual_key = "name" if key == "business" else key
                    return getattr(lead, actual_key, default)

            business = get_val("business", "Unknown")
            followers = get_val("followers")
            if followers is None or followers == "":
                followers = "Unknown"
            phone = get_val("phone", "None") or "None"
            whatsapp = "YES" if get_val("whatsapp") else "NO"
            website = get_val("website")
            website_status = "YES" if website else "NO"
            score = get_val("score", 0)

            f.write("Business\n")
            f.write(f"{business}\n\n")

            f.write("Followers\n")
            f.write(f"{followers}\n\n")

            f.write("Phone\n")
            f.write(f"{phone}\n\n")

            f.write("WhatsApp\n")
            f.write(f"{whatsapp}\n\n")

            f.write("Website\n")
            f.write(f"{website_status}\n\n")

            f.write("Score\n")
            f.write(f"{score}\n\n")

            f.write("--------------------------------\n")
    
    logger.info("Exported %d leads to TXT: %s", len(leads), filepath)
    return filepath
