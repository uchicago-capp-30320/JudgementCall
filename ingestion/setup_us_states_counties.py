import pandas as pd
from pathlib import Path
from ingestion.ingest_courts import COURT_LOOKUP_SHORT
from ingestion.state_crosswalks import FIPS_TO_ABBR

# Path for data
# Directory of the current script (ingestion/)
BASE_DIR = Path(__file__).resolve().parent

# Path to the data/ folder and make sure it exists
DATA_DIR = BASE_DIR.parent / "data" / "counties"
DATA_DIR.mkdir(exist_ok=True)

# Final CSV path
COUNTIES_CSV = DATA_DIR / "united-states.csv"


def counties_csv_to_df():
    return pd.read_csv(COUNTIES_CSV)


def make_county_to_court_df():
    df = counties_csv_to_df()
    df = df.rename(
        columns={"FIPS State and County Codes": "fips", "Geographic area name": "county"}
    )
    df = df[["fips", "county"]]
    df["fips"] = df["fips"].astype(str).apply(lambda s: s.zfill(5))
    df["state"] = df["fips"].str[:2]
    df = df[df["state"] != "00"]
    df["state"] = df["state"].apply(lambda x: FIPS_TO_ABBR.get(x))
    df["court_id"] = df["state"].apply(lambda x: COURT_LOOKUP_SHORT.get(x))
    df.dropna(inplace=True)
    return df
