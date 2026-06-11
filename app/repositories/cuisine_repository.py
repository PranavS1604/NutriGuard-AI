import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cuisines"

class CuisineRepository:
    def __init__(self, path: str = None):
        csv_path = Path(path) if path else _DATA_DIR / "world_food_kb_light.csv"
        try:
            self.df = pd.read_csv(csv_path, dtype=str, low_memory=False)
        except FileNotFoundError:
            self.df = pd.DataFrame()

        # FIX: Gracefully handle missing columns to prevent KeyErrors
        expected_columns = ["name", "alias", "cuisines", "associated_cuisines", "countries", "area", "ingredients", "text_description"]
        for col in expected_columns:
            if col not in self.df.columns:
                self.df[col] = ""

    def get_dishes_by_country(self, country_name: str) -> List[Dict[str, Any]]:
        if self.df.empty: return []
        result = self.df[self.df["countries"].str.contains(country_name, case=False, na=False) | self.df["area"].str.contains(country_name, case=False, na=False)]
        return result.to_dict("records")

    def get_dishes_by_cuisine(self, cuisine_name: str) -> List[Dict[str, Any]]:
        if self.df.empty: return []
        result = self.df[self.df["cuisines"].str.contains(cuisine_name, case=False, na=False) | self.df["associated_cuisines"].str.contains(cuisine_name, case=False, na=False)]
        return result.to_dict("records")
        
    def get_dish_details(self, dish_name: str) -> Optional[Dict[str, Any]]:
        if self.df.empty: return None
        result = self.df[self.df["name"].str.lower() == dish_name.lower()]
        return result.iloc[0].to_dict() if not result.empty else None