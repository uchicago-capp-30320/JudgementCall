from jellyfish import jaro_winkler_similarity
from string import punctuation

ENDINGS = [
    "C.J.",
    "P.J.",
    "J.",
    "Sp. J.",
    "JJ.",
    "PJJ",
    "C. J.",
    "P.JJ.",
    "V.C.J.",
    "A.R.J.",
    "D.J.",
    "S.J.",
    "P.J.A.D",
    "J.P.T.",
    "PJ",
    "J",
    "CJ",
]

KEY_WORDS = [
    "justice",
    "judge",
    "chief justice",
    "chief",
    "presiding justice",
    "associate justice",
    "associate chief justice",
    "retired",
    "sitting",
    "by designation",
]


def standardize_name(name: str):
    name = name.replace("\n", "")
    return name.strip().lower().translate(str.maketrans("", "", punctuation))


def standardize_alias(alias: str):
    for end in ENDINGS:
        if alias.endswith(end):
            alias = alias.removesuffix(end, "")

    alias = alias.strip().lower().translate(str.maketrans("", "", punctuation))

    for word in KEY_WORDS:
        if word in alias:
            alias = alias.replace(word, "")
    return alias.strip()


def analyze_potential_matches(alias: str, names: list[str], num_words: int = None):
    matches = {}

    for name in names:
        standard_name = standardize_name(name)
        if num_words is None:
            matches[name] = jaro_winkler_similarity(alias, standard_name)
        else:
            name_portion = " ".join(standard_name.split(" ")[-num_words:]).strip()
            matches[name] = jaro_winkler_similarity(alias, name_portion)

    return matches


def find_best_match(alias: str, names: list[str]):
    standard_alias = standardize_alias(alias)
    matches = analyze_potential_matches(standard_alias, names)
    top_match = max(matches, key=lambda k: matches[k])

    # Return match if the top-matching name and standardized alias are
    # the exactly the same
    if standard_alias == standardize_name(top_match):
        return top_match

    # If the top-matching name has a 0.9+ JW score return the match
    elif matches[top_match]["score"] > 0.9:
        return top_match

    else:
        # If both of the conditions above fail, then reverse iterate
        # through the terms of the standardized alias to match them with
        # the corresponding terms in the standardized top-matching name
        alias_terms = standard_alias.split(" ")
        build_out_term = ""

        for i, term in reversed(list(enumerate(alias_terms))):
            # Compute build out alias and build out top-matching name
            build_out_term = " ".join([term, build_out_term]).strip()
            matches = analyze_potential_matches(build_out_term, names, num_words=i + 1)
            top_match = max(matches, key=lambda k: matches[k])
            build_out_name = " ".join(top_match.split(" ")[-i:]).strip()

            # If the build out top-matching name and build out alias
            # are the same, return the match
            if build_out_name == build_out_term:
                return top_match

            # If the build out top-matching name and build out alias
            # have a 0.9+ JW score, return the match
            elif matches[top_match] > 0.9:
                return top_match
