from jellyfish import jaro_winkler_similarity
import pandas as pd

STATE_MAP = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def match(wiki: pd.DataFrame, slri: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a dataframe of canonical wikipedia names and a dataframe of slri names.
    For each slri name, calculates Jaro-Winkler similarity against every wikipedia
    name and identifies the best match. Returns a dataframe with each slri name,
    its best matching wikipedia name, and a match quality rating (High/Medium/Low).
    """
    r_table = {"slri_name": [], "wiki_name": [], "match_quality": []}

    for slri_name_raw in slri["name"]:
        slri_name = slri_name_raw.lower().replace(".", "").replace("\n", "").strip()
        r_table["slri_name"].append(slri_name)

        scores = []
        for wiki_name_raw in wiki["name"]:
            wiki_name = wiki_name_raw.lower().replace(".", "").replace("\n", "").strip()
            scores.append(jaro_winkler_similarity(slri_name, wiki_name))

        best_idx = pd.Series(scores).idxmax()
        best_score = scores[best_idx]
        best_wiki_name = wiki["name"].iloc[best_idx]

        r_table["wiki_name"].append(best_wiki_name)

        if best_score >= 0.9:
            r_table["match_quality"].append("High")
        elif best_score >= 0.5:
            r_table["match_quality"].append("Medium")
        else:
            r_table["match_quality"].append("Low")

    return pd.DataFrame(r_table)


def run_matching(wikipedia: pd.DataFrame, slri: pd.DataFrame) -> pd.DataFrame:
    """
    Iterates through each state present in wikipedia, runs match() on the
    state subset of each source, and concatenates results. States with no
    corresponding slri records are skipped.
    """
    unique_states = wikipedia["state"].unique()
    r_list = []

    for state in unique_states:
        print(f"Matching names for {state}")
        wiki_state = wikipedia[wikipedia["state"] == state].reset_index(drop=True)
        slri_state = slri[slri["state"] == state].reset_index(drop=True)

        if slri_state.empty:
            continue

        match_results = match(wiki_state, slri_state)
        match_results["state"] = state
        r_list.append(match_results)

    return pd.concat(r_list, ignore_index=True)


def merge_sources(wikipedia: pd.DataFrame, slri: pd.DataFrame) -> pd.DataFrame:
    """
    Left-merges slri into wikipedia using fuzzy-matched names within each state.
    Wikipedia rows with no match in slri are retained. A match_quality column
    indicates the confidence of each name match (High/Medium/Low).
    """
    slri = slri.copy()
    slri["state"] = slri["state"].map(STATE_MAP)  # normalize abbreviations to full state names

    # build a bridge table: slri_name -> wiki_name + match_quality, per state
    bridge = run_matching(
        wikipedia=wikipedia[["state", "name"]],
        slri=slri[["state", "name"]],
    )

    # standardize slri names the same way match() does, so the join key aligns
    slri["slri_name"] = (
        slri["name"].str.lower().str.replace(".", "", regex=False)
                    .str.replace("\n", "").str.strip()
    )
    bridge["slri_name"] = (
        bridge["slri_name"].str.lower().str.replace(".", "", regex=False)
                           .str.replace("\n", "").str.strip()
    )

    # print every matched pair
    print("\n--- Name Matches ---")
    for _, row in bridge.iterrows():
        print(f"  [{row['state']}] SLRI: '{row['slri_name']}' -> WIKI: '{row['wiki_name']}' ({row['match_quality']})")


    # attach bridge (wiki_name, match_quality) to slri rows
    slri_with_bridge = slri.merge(
        bridge[["slri_name", "state", "wiki_name", "match_quality"]],
        on=["slri_name", "state"],
        how="left",
    )

    # slri rows that didn't match any wikipedia name
    slri_unmatched = slri_with_bridge[slri_with_bridge["wiki_name"].isna()]
    print(f"\n--- SLRI names with no wikipedia match: {len(slri_unmatched)} ---")
    for _, row in slri_unmatched.iterrows():
        print(f"  [{row['state']}] {row['name']}")

    # left merge into wikipedia on canonical wiki name + state
    merged = wikipedia.merge(
        slri_with_bridge.drop(columns=["slri_name", "name"]),
        left_on=["name", "state"],
        right_on=["wiki_name", "state"],
        how="left",
    ).drop(columns=["wiki_name"])

    # wikipedia rows that didn't match any slri name
    wiki_unmatched = merged[merged["match_quality"].isna()]
    print(f"\n--- Wikipedia names with no SLRI match: {len(wiki_unmatched)} ---")
    for _, row in wiki_unmatched.iterrows():
        print(f"  [{row['state']}] {row['name']}")

    return merged

if __name__ == "__main__":
    wikipedia = pd.read_csv("wikipedia.csv")
    slri = pd.read_csv("slri.csv")
    result = merge_sources(wikipedia, slri)
    result.to_csv("merged_judges.csv", index=False)