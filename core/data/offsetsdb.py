"""Load the local OffsetsDB snapshot (data/raw/offsetsdb, not redistributed)."""

from functools import lru_cache

import pandas as pd

from core.config import PROJECT_ROOT

EXTRACTED = PROJECT_ROOT / "data" / "raw" / "offsetsdb" / "extracted"


@lru_cache(maxsize=1)
def credits() -> pd.DataFrame:
    df = pd.read_parquet(EXTRACTED / "credits.parquet")
    df["registry"] = df["project_id"].str.extract(r"^([A-Z]+?)(?:\d|$)", expand=False)
    df.loc[df["registry"].str.startswith("ISO", na=False), "registry"] = "ISO"
    df["year"] = pd.to_datetime(df["transaction_date"], utc=True).dt.year
    return df


@lru_cache(maxsize=1)
def projects() -> pd.DataFrame:
    return pd.read_parquet(EXTRACTED / "projects.parquet")


def snapshot_date() -> str:
    import json
    return json.loads((EXTRACTED / "metadata.json").read_text(encoding="utf-8"))["generated_at"][:10]


REGISTRY_NAMES = {
    "VCS": "Verra", "GLD": "Gold Standard", "ACR": "American Carbon Registry", "CAR": "Climate Action Reserve",
    "CCB": "Cercarbono", "ART": "ART TREES", "ISO": "Isometric",
}
