import pandas as pd
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional

# Resolve path relative to this file's location (works regardless of CWD)
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cuisines"

class CuisineRepository:
    def __init__(self, path: str = None):
        csv_path = Path(path) if path else _DATA_DIR / "world_food_kb_light.csv"
        self.df = pd.read_csv(csv_path, dtype=str, low_memory=False)

    def search_dish(self, query: str) -> List[Dict[str, Any]]:
        """
        Search dishes by name or alias (case-insensitive).
        """
        result = self.df[
            self.df["name"].str.contains(query, case=False, na=False) |
            self.df["alias"].str.contains(query, case=False, na=False)
        ]
        return result.to_dict("records")

    def get_dishes_by_cuisine(self, cuisine_name: str) -> List[Dict[str, Any]]:
        """
        Get dishes associated with a cuisine name (e.g. 'Japanese').
        """
        result = self.df[
            self.df["cuisines"].str.contains(cuisine_name, case=False, na=False) |
            self.df["associated_cuisines"].str.contains(cuisine_name, case=False, na=False)
        ]
        return result.to_dict("records")

    def get_dishes_by_country(self, country_name: str) -> List[Dict[str, Any]]:
        """
        Get dishes associated with a country (e.g. 'Japan').
        """
        result = self.df[
            self.df["countries"].str.contains(country_name, case=False, na=False) |
            self.df["area"].str.contains(country_name, case=False, na=False)
        ]
        return result.to_dict("records")

    def get_dish_details(self, dish_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full details of a specific dish by exact name.
        """
        result = self.df[self.df["name"].str.lower() == dish_name.lower()]
        if not result.empty:
            return result.iloc[0].to_dict()
        return None
