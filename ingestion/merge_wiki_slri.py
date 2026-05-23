import pandas as pd
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.matching import find_best_match

# Path for data
# Directory of the current script (ingestion/)
BASE_DIR = Path(__file__).resolve().parent

# Path to the data/ folder and make sure it exists
DATA_DIR = BASE_DIR.parent / "data" / "judges"
DATA_DIR.mkdir(exist_ok=True)

# Input csv paths
WIKI = DATA_DIR / "wikipedia.csv"
SLRI = DATA_DIR / "slri.csv"

# Final csv path
OUTPUT_CSV = DATA_DIR / "merged_judges.csv"
MATCH_REPORT_CSV = DATA_DIR / "match_wiki_slri_report.csv"

STATE_MAP = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}


def merge_sources(wiki: pd.DataFrame, slri: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    wiki = wiki.copy()
    slri = slri.copy()
    slri["state"] = slri["state"].map(STATE_MAP)

    def match_row(row):
        slri_names = slri[slri["state"] == row["state"]]["name"].tolist()
        if not slri_names:
            return None
        return find_best_match(row["name"], slri_names)

    wiki["slri_name"] = wiki.apply(match_row, axis=1)

    ########### MERGE REPORT

    # wiki rows with no slri match
    wiki_unmatched = wiki[wiki["slri_name"].isna()][["name", "state"]].copy()
    wiki_unmatched["match_status"] = "wiki only"

    # slri rows with no wiki match
    matched_slri_names = wiki["slri_name"].dropna().tolist()
    slri_unmatched = slri[~slri["name"].isin(matched_slri_names)][["name", "state"]].copy()
    slri_unmatched["match_status"] = "slri only"

    # matched pairs
    matched = wiki[wiki["slri_name"].notna()][["name", "state", "slri_name"]].copy()
    matched = matched.rename(columns={"name": "wiki_name"})
    matched["match_status"] = "matched"

    report = pd.concat(
        [
            matched.rename(columns={"wiki_name": "name"}),
            wiki_unmatched,
            slri_unmatched,
        ],
        ignore_index=True,
    )

    ########### END MERGE REPORT
    merged = wiki.merge(
        slri,
        left_on=["slri_name", "state"],
        right_on=["name", "state"],
        how="left",
        suffixes=("", "_slri"),
    ).drop(columns=["slri_name", "name_slri"])

    return merged, report


if __name__ == "__main__":
    """
    Add argument --include_matched" to generate match report.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--include_unmatched", action="store_true")
    args = parser.parse_args()

    wiki = pd.read_csv(WIKI)
    slri = pd.read_csv(SLRI)
    result, report = merge_sources(wiki, slri)
    result.to_csv(OUTPUT_CSV, index=False)

    if args.include_unmatched:
        report.to_csv(MATCH_REPORT_CSV, index=False)
