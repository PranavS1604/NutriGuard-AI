import pandas as pd
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# Resolve paths relative to this file's location (works regardless of CWD)
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "nutrition"

class IFCTRepository:
    def __init__(
        self,
        core_path: str = None,
        tags_path: str = None
    ):
        core_csv = Path(core_path) if core_path else _DATA_DIR / "ifct_core.csv"
        tags_csv = Path(tags_path) if tags_path else _DATA_DIR / "nutrition_tags.csv"

        self.df_core = pd.read_csv(core_csv)
        if tags_csv.exists():
            self.df_tags = pd.read_csv(tags_csv)
            # Merge tags using food_code
            self.df = pd.merge(
                self.df_core,
                self.df_tags[['food_code', 'tags']],
                on='food_code',
                how='left'
            )
        else:
            self.df = self.df_core

    def search_food(self, food_name: str) -> List[Dict[str, Any]]:
        """
        Search for foods in the IFCT database by name (case-insensitive).
        """
        result = self.df[
            self.df["food_name"]
            .str.contains(food_name, case=False, na=False)
        ]
        return result.to_dict("records")

    def get_food_by_code(self, food_code: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific food by its food code.
        """
        result = self.df[self.df["food_code"] == food_code]
        if not result.empty:
            return result.iloc[0].to_dict()
        return None
