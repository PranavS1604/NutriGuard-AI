import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Resolve path relative to this file's location (works regardless of CWD)
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "drug_interactions"

class DrugRepository:
    def __init__(self, path: str = None):
        json_path = Path(path) if path else _DATA_DIR / "drug_food_interactions.json"
        with open(json_path, "r", encoding="utf-8") as f:
            self.interactions = json.load(f)

    def find_interactions(self, drug_name: str) -> List[str]:
        """
        Find food interactions for a drug name (case-insensitive, substring matching).
        """
        drug_name_lower = drug_name.lower()
        # First try exact match
        for item in self.interactions:
            if item.get("name", "").lower() == drug_name_lower:
                return item.get("food_interactions", [])

        # Then try substring match
        for item in self.interactions:
            if drug_name_lower in item.get("name", "").lower():
                return item.get("food_interactions", [])

        return []

    def get_food_warnings(self, drug_name: str) -> List[str]:
        """
        Get structured warning messages for food interactions.
        """
        return self.find_interactions(drug_name)

    def get_severity(self, drug_name: str) -> str:
        """
        Assign a severity level based on food interaction warning keywords.
        """
        interactions = self.find_interactions(drug_name)
        if not interactions:
            return "Low"

        text = " ".join(interactions).lower()
        if any(w in text for w in ["avoid", "severe", "danger", "contraindicated", "fatal"]):
            return "High"
        elif any(w in text for w in ["limit", "caution", "moderate", "monitor"]):
            return "Medium"
        return "Low"
