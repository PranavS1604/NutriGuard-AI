import pandas as pd
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from rapidfuzz import process, fuzz

# Resolve path relative to this file's location (works regardless of CWD)
_USDA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "nutrition" / "usda_foundation"

class USDARepository:
    def __init__(self, folder_path: str = None):
        folder = Path(folder_path) if folder_path else _USDA_DIR
        self.df_food = pd.read_csv(folder / "food.csv", low_memory=False)
        self.df_food_nutrient = pd.read_csv(folder / "food_nutrient.csv", low_memory=False)
        self.df_nutrient = pd.read_csv(folder / "nutrient.csv", low_memory=False)

        
        try:
            self.df_foundation_food = pd.read_csv(folder / "foundation_food.csv", low_memory=False)
            self.df_food_category = pd.read_csv(folder / "food_category.csv", low_memory=False)
            self.df_measure_unit = pd.read_csv(folder / "measure_unit.csv", low_memory=False)
            
            # Merge food category descriptions
            category_mapping = self.df_food_category[["id", "description"]].rename(
                columns={"id": "food_category_id", "description": "food_category_description"}
            )
            self.df_food = pd.merge(self.df_food, category_mapping, on="food_category_id", how="left")
            
            # Merge foundation food specifics (e.g., NDB_number)
            self.df_food = pd.merge(self.df_food, self.df_foundation_food, on="fdc_id", how="left")
        except (FileNotFoundError, Exception):
            pass  # Fallback gracefully if extra datasets are missing

            
        # Caches for performance optimization
        self._search_cache = {}
        self._nutrient_cache = {}

    def search_food(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for foods in the USDA foundation food list, prioritizing exact matches,
        foundation (unbranded) foods, substring matches, and falling back to fuzzy matching.
        """
        if not query:
            return []
            
        if query in self._search_cache:
            return self._search_cache[query]

        df_foundation = self.df_food[self.df_food["data_type"] == "foundation_food"]

        # 1. Exact case-insensitive match in foundation_food
        exact_foundation = df_foundation[df_foundation["description"].str.lower() == query.lower()]
        if not exact_foundation.empty:
            res = exact_foundation.to_dict("records")
            self._search_cache[query] = res
            return res

        # 2. Exact case-insensitive match in all foods
        exact_all = self.df_food[self.df_food["description"].str.lower() == query.lower()]
        if not exact_all.empty:
            res = exact_all.to_dict("records")
            self._search_cache[query] = res
            return res

        # 3. Substring match in foundation_food
        contains_foundation = df_foundation[df_foundation["description"].str.contains(query, case=False, na=False)]
        if not contains_foundation.empty:
            res = contains_foundation.to_dict("records")
            self._search_cache[query] = res
            return res

        # 4. Fuzzy match in foundation_food
        foundation_choices = df_foundation["description"].tolist()
        fuzzy_matches = process.extract(query, foundation_choices, limit=5, score_cutoff=60, scorer=fuzz.token_sort_ratio)
        if fuzzy_matches:
            matched_descriptions = [m[0] for m in fuzzy_matches]
            matched_df = df_foundation[df_foundation["description"].isin(matched_descriptions)]
            matched_df = matched_df.set_index("description").loc[matched_descriptions].reset_index()
            res = matched_df.to_dict("records")
            self._search_cache[query] = res
            return res

        # 5. Substring match in all foods
        contains_all = self.df_food[self.df_food["description"].str.contains(query, case=False, na=False)]
        if not contains_all.empty:
            res = contains_all.to_dict("records")
            self._search_cache[query] = res
            return res

        # 6. Fuzzy match in all foods
        choices_all = self.df_food["description"].tolist()
        fuzzy_matches_all = process.extract(query, choices_all, limit=5, score_cutoff=60, scorer=fuzz.token_sort_ratio)
        if fuzzy_matches_all:
            matched_descriptions_all = [m[0] for m in fuzzy_matches_all]
            records = []
            for desc in matched_descriptions_all:
                sub_df = self.df_food[self.df_food["description"] == desc]
                if not sub_df.empty:
                    records.append(sub_df.iloc[0].to_dict())
            self._search_cache[query] = records
            return records

        self._search_cache[query] = []
        return []

    def get_nutrients(self, fdc_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve nutrient details for a specific Food Data Central (fdc_id) with caching.
        """
        if fdc_id in self._nutrient_cache:
            return self._nutrient_cache[fdc_id]

        nutrients = self.df_food_nutrient[self.df_food_nutrient["fdc_id"] == fdc_id]
        merged = pd.merge(
            nutrients, 
            self.df_nutrient, 
            left_on="nutrient_id", 
            right_on="id",
            how="left"
        )
        res = merged[["name", "amount", "unit_name"]].fillna("").to_dict("records")
        self._nutrient_cache[fdc_id] = res
        return res
