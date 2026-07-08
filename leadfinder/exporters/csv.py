"""CSV exporter for LeadFinder AI.

Exports a list of lead dictionaries into a CSV file.
"""

from __future__ import annotations

import csv
import logging
from typing import Any

logger = logging.getLogger("leadfinder.exporters.csv")


def export_csv(leads: list[dict[str, Any]], filepath: str) -> str:
    """Export a list of leads to a CSV file.

    Args:
        leads: List of lead dictionaries.
        filepath: Output CSV file path.

    Returns:
        The absolute path to the saved file.
    """
    if not filepath.endswith(".csv"):
        filepath += ".csv"

    columns = ["business", "followers", "phone", "website", "whatsapp", "score"]

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        
        for lead in leads:
            # Handle both dict and object (if BusinessLead was passed)
            def get_val(key, default=""):
                if isinstance(lead, dict):
                    # Map 'name' to 'business' for backwards compatibility with earlier milestones
                    actual_key = "name" if key == "business" else key
                    return lead.get(actual_key, default)
                else:
                    actual_key = "name" if key == "business" else key
                    return getattr(lead, actual_key, default)

            row = {
                "business": get_val("business", "Unknown"),
                "followers": get_val("followers", ""),
                "phone": get_val("phone", ""),
                "website": get_val("website", ""),
                "whatsapp": "YES" if get_val("whatsapp") else "NO",
                "score": get_val("score", 0),
            }
            writer.writerow(row)
    
    logger.info("Exported %d leads to CSV: %s", len(leads), filepath)
    return filepath
