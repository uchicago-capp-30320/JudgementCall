from jellyfish import jaro_winkler_similarity
import pandas as pd


def match(names: pd.DataFrame, aliases: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a dataframe with canonical names, and a dataframe with aliases.
    Iterates through each alias, standardizes it, and calculates its
    Jaro-Winkler similary score against every standardized canonical name.

    It identifies the highest scoring canonical name match, and gives a match
    quality rating.

    Returns a pandas dataframe with every unique alias given in the alias
    input dataframe, along with its found match, and the match quality.
    """
    r_table = {"alias": [], "name": [], "match_quality": []}

    unique_aliases = aliases["name"].unique()
    num_aliases = len(unique_aliases)
    for num in range(num_aliases):
        alias = aliases.loc[num, "name"].lower().replace(".", "").replace("\n", "")
        r_table["alias"].append(alias)

        num_names = len(names)

        matching_table = {"name": list(names["name"]), "match_score": []}

        for i in range(num_names):
            name = names.loc[i, "name"].lower().replace(".", "").replace("I", "")
            score = jaro_winkler_similarity(alias, name)
            matching_table["match_score"].append(score)

        top_match = (
            pd.DataFrame(matching_table).sort_values(by="match_score", ascending=False).iloc[0]
        )
        match_name = top_match["name"]
        r_table["name"].append(match_name)
        match_score = top_match["match_score"]

        if match_score >= 0.9:
            r_table["match_quality"].append("High")
        elif (match_score < 0.9) and (match_score >= 0.5):
            r_table["match_quality"].append("Medium")
        else:
            r_table["match_quality"].append("Low")

    return pd.DataFrame(r_table)


def run_matching(names: pd.DataFrame, alias: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a dataframe with canonical names, and a dataframe with aliases. Function
    iterates through each state (or court) and runs the match() function on them
    returning a dataframe of unique aliases with their matches and match quality.
    """
    unique_states = names["state"].unique()

    r_list = []

    for state in unique_states:
        print(f"Matching names for {state}")
        state_names = names[names["state"] == state].reset_index(drop=True)
        state_aliases = alias[alias["state"] == state].reset_index(drop=True)

        match_results = match(state_names, state_aliases)

        r_list.append(match_results)

    return pd.concat(r_list)
