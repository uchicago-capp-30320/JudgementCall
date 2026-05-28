from .models import (
    Tenure,
    IndividualOpinion,
)
from collections import defaultdict

# maps topic areas to icons
TOPIC_ICON_DICT = {
    "environment": "eco",
    "consumers": "wallet",
    "reproductive_rights": "pregnancy",
    "democratic_norms": "assured_workload",
    "free_press": "newspaper",
    "public_health": "stethoscope",
    "separation_church_state": "church",
    "voting_access": "how_to_vote",
    "public_education": "local_library",
    "free_speech": "campaign",
    "privacy": "eye_tracking",
    "worker_rights": "person_apron",
}

# maps topics to appropriate phrasing for pop-ups
TOPIC_REPHRASED = {
    "environment": "the environment",
    "consumers": "consumer protections",
    "reproductive_rights": "reproductive rights",
    "democratic_norms": "democratic norms",
    "free_press": "the free press",
    "public_health": "public health",
    "separation_church_state": "the separation of church and state",
    "voting_access": "voting access",
    "public_education": "public education",
    "free_speech": "free speech",
    "privacy": "privacy rights",
    "worker_rights": "worker rights",
}

### PEOPLE WITH TENURE ###


# up for election soon
def up_for_election(tenure):
    "Returns gray icon tuple if judge term is anticipated to end in a year."
    if tenure.end_date is not None:
        return (
            tenure.tenure_length_remaining <= 1,
            "#808080ff",
            "This judge's term ends soon.",
        )
    else:
        return (
            False,
            "#808080ff",
            "This judge's term ends soon.",
        )


# long tenure (>=10yr)
def long_tenure(tenure):
    "Returns gray icon tuple if judge has served on current bench for 10+ years."
    if tenure.start_date is not None:
        return (
            tenure.tenure_length_to_date >= 10,
            "#808080ff",
            "This judge has served for 10+ years.",
        )
    else:
        return (
            False,
            "#808080ff",
            "This judge has served for 10+ years.",
        )


def effective_stance(alignment, indiv_ruling):
    """
    Takes court decision and indiv judge ruling and flips alignment if judge
    dissented from main opinion.
    """
    if indiv_ruling == "dissent" and alignment != "NA":
        return "protected" if alignment == "infringed" else "infringed"
    return alignment


def issue_stance_dict(tenure):
    """
    Takes tenure, collects relevant opinions, creates frequency dictionary of
    issue stances depending on overall court ruling and indiv opinion.
    """
    topic_tallies = defaultdict(lambda: defaultdict(int))

    # get opinions for a judge on a court
    opinions = IndividualOpinion.objects.select_related(
        "case__court", "judge_alias__tenure"
    ).filter(judge_alias__tenure=tenure, case__court=tenure.court)

    for opinion in opinions:
        case = opinion.case
        ruling = opinion.ruling

        # go through each topic area, check case alignment
        for attr in case.topic_flags():
            topic_alignment = getattr(case, attr, None)
            if topic_alignment != "NA":
                # correct judge alignment based on decision vs. their opinion
                stance = effective_stance(topic_alignment, ruling)
                topic_tallies[attr][stance] += 1

    return topic_tallies


def classify_topic(attr, tallies):
    """
    Takes issue and tallies from freq_dict and assigns appropriate icon tuples
    depending on ratio of support/dissent for a given issue area.
    """
    protect = tallies.get("protected", 0)
    infringe = tallies.get("infringed", 0)
    total = protect + infringe

    # insufficient number of cases to decide
    if total < 3:
        return (False, "#808080ff", "")

    ratio = infringe / protect if protect > 0 else float("inf")

    # 2 infringe for every 1 protect
    if ratio >= 2:
        return (
            True,
            "#b02e2eff",
            f"This judge has historically ruled against {TOPIC_REPHRASED[attr]}.",
        )
    # 1 infringe for every 2 protect
    elif ratio <= 0.5:
        return (
            True,
            "#378e4aff",
            f"This judge has historically ruled to protect {TOPIC_REPHRASED[attr]}.",
        )
    # unremarkable ratio
    else:
        return (False, "#808080ff", "")


# has ruled to protect <topic>
def topics_of_note(tenure):
    """
    Takes tenure, builds frequency dictionary, and then iterates through issue
    areas to collect icon tuples. Topic icons have non-gray colors.
    """
    issue_dict = issue_stance_dict(tenure)

    topic_classifications = {
        attr: classify_topic(attr, tallies) for attr, tallies in issue_dict.items()
    }

    return topic_classifications


### NOT TENURE-SPECIFIC ATTRIBUTES ###


# worked as a public defender
# worked as a prosecutor
# worked in legal aid
def relevant_experience():
    """
    Returns indicators of having certain types of public-oriented legal
    professional experience
    """
    # TODO


def prestigious_school():
    "Returns indicator for an expensive education, maybe top 15 schools?"
    # TODO


# personal party affiliation, controversial
def personal_party():
    "Returns indicator for personal party registration."
    # TODO


# for testing endorsement integration
def endorsements():
    "Returns visually distinct, synthetic endorsements for UI/UX testing purposes."
    # TODO


# inspired by Injustice Watch flags
def has_scandals():
    "Returns visually distinct, synthetic scandal icons for UI/UX testing purposes."
    # TODO


def get_judge_icons(tenure, icon_dict):
    """Collects icon tuples for people with tenure."""
    if tenure is not None:
        icon_dict["release_alert"] = up_for_election(tenure)
        icon_dict["hourglass"] = long_tenure(tenure)
        topics_to_include = topics_of_note(tenure)
        topic_icons = {
            TOPIC_ICON_DICT[k]: v for k, v in topics_to_include.items() if k in TOPIC_ICON_DICT
        }

        icon_dict = icon_dict | topic_icons

    return icon_dict


def get_candidate_icons(candidacy, icon_dict):
    """Collects icon tuples for candidates with without previous judicial experience."""
    # person = candidacy.person
    # TODO


def get_icon_dict(instance, is_judge):
    """
    Collects appropriate icon tuples for candidates and judges. Flag parameter
    signals which set to collect.
    """
    if is_judge:
        icon_dict = {}
        icon_dict = get_judge_icons(instance, icon_dict)
    # otherwise is candidate
    else:
        icon_dict = {}
        icon_dict = get_candidate_icons(instance, icon_dict)

    return icon_dict


# quick implementation due to not having time/permission to implement candidate icons
def get_topic_icons(person):
    "Used to retrieve just topic icons for judges in elections view."
    tenures = Tenure.objects.filter(person=person)

    topic_tallies = defaultdict(lambda: defaultdict(int))

    for tenure in tenures:
        opinions = IndividualOpinion.objects.select_related(
            "case__court", "judge_alias__tenure"
        ).filter(judge_alias__tenure=tenure)

        for opinion in opinions:
            case = opinion.case
            ruling = opinion.ruling
            for attr in case.topic_flags():
                topic_alignment = getattr(case, attr, None)
                if topic_alignment != "NA":
                    stance = effective_stance(topic_alignment, ruling)
                    topic_tallies[attr][stance] += 1

    topic_classifications = {
        attr: classify_topic(attr, tallies) for attr, tallies in topic_tallies.items()
    }

    return {TOPIC_ICON_DICT[k]: v for k, v in topic_classifications.items() if k in TOPIC_ICON_DICT}
