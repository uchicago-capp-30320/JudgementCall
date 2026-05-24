from .models import (
    # Court,
    # Person,
    # Election,
    # Candidacy,
    # Tenure,
    # Case,
    IndividualOpinion,
    # CourtLevel,
    # SelectionType,
    # CaseType,
    # SelectionJurisdictionType,
    # Alias,
    # CaseParticipant,
    # TopicAlignment,
    # RulingType,
    # CountyToCourt,
    # PersonGender,
    # PersonRace,
    # PartyAffiliation,
)
from collections import defaultdict

TOPIC_ICON_DICT = {
    "environment": "eco",
    "consumers": "wallet",
    "reproductive_rights": "pregnancy",
    "democratic_norms": "assured_workload",  # might review later
    "free_press": "newspaper",
    "public_health": "stethoscope",
    "separation_church_state": "church",
    "voting_access": "how_to_vote",
    "public_education": "local_library",
    "free_speech": "campaign",
    "privacy": "eye_tracking",
    "worker_rights": "person_apron",
}

### PEOPLE WITH TENURE ###


# up for election soon
def up_for_election(tenure):
    "returns bool"
    return (tenure.tenure_length_remaining() <= 1, "gray")


# long tenure (>=10yr)
def long_tenure(tenure):
    "returns bool indicating >=10yr of current tenure"
    return (tenure.tenure_length_to_date() >= 10, "gray")


def effective_stance(alignment, indiv_ruling):
    "flip judge stance on topic if dissented from majority opinion"
    if indiv_ruling == "dissent" and alignment != "NA":
        return "protected" if alignment == "infringed" else "infringed"
    return alignment


def issue_stance_dict(tenure):
    """returns freq dictionary of for/against topic issues"""
    topic_tallies = defaultdict(lambda: defaultdict(int))
    opinions = IndividualOpinion.objects.select_related(
        "case__court", "judge_alias__tenure"
    ).filter(judge_alias__tenure=tenure, case__court=tenure.court)

    for opinion in opinions:
        case = opinion.case
        ruling = opinion.ruling

        for attr in case.topic_flags():
            topic_alignment = getattr(case, attr, None)
            if topic_alignment != "NA":
                stance = effective_stance(topic_alignment, ruling)
                topic_tallies[attr][stance] += 1

    return topic_tallies


def classify_topic(tallies):
    protect = tallies.get("protected", 0)
    infringe = tallies.get("infringed", 0)
    total = protect + infringe

    # insufficient number of cases to decide
    if total < 3:
        return (False, "gray")

    ratio = infringe / protect if protect > 0 else float("inf")

    # 2 infringe for every 1 protect
    if ratio >= 2:
        return (True, "red")
    # 1 infringe for every 2 protect
    elif ratio <= 0.5:
        return (True, "green")
    # unremarkable ratio
    else:
        return (False, "gray")


# has ruled to protect <topic>
def topics_of_note(tenure):
    "returns something indicating issue protect/infringe areas, tbd"
    issue_dict = issue_stance_dict(tenure)

    topic_classifications = {attr: classify_topic(tallies) for attr, tallies in issue_dict.items()}

    return topic_classifications


### NOT TENURE-SPECIFIC ATTRIBUTES ###


# worked as a public defender
# worked as a prosecutor
# worked in legal aid
# professor? hmm
def relevant_experience():
    "returns indicators of having certain types of public-oriented professional experience"
    # TODO


# idk fancy law school?
def prestigious_school():
    "returns indicator for an expensive education, maybe top 15?"
    # TODO


# personal party affiliation
def personal_party():
    "returns indicator for personal party, maybe should be candidates only? idk"
    # TODO


# do a filler for relevant endorsements
# list of municipal & party endorsers and then randomly select in favor or against
def endorsements():
    "returns fake endorsements"
    # TODO


# could do same for scandal, should set toggle to turn these off if we don't want them
def has_scandals():
    "returns fake scandal flag"
    # TODO


# maybe change color to indicate fake data


def get_judge_icons(tenure, icon_dict):
    "get icons related to judges"
    # icon_dict["release_alert"] = up_for_election(tenure)
    # icon_dict["hourglass"] = long_tenure(tenure)
    topics_to_include = topics_of_note(tenure)
    topic_icons = {
        TOPIC_ICON_DICT[k]: v for k, v in topics_to_include.items() if k in TOPIC_ICON_DICT
    }

    icon_dict = icon_dict | topic_icons

    return icon_dict


def get_candidate_icons(candidacy, icon_dict):
    "get icons related to candidates"


def get_icon_dict(instance, is_judge):
    """
    end product should look like:
    person_attributes = {
        if judge {judge_stuff},
        person stuff {person_stuff}
    }
    """
    # get relevant instance and then flag if it's for a judge or not I guess
    # call all the helpers to create person-level dictionary
    if is_judge:
        icon_dict = {}
        icon_dict = get_judge_icons(instance, icon_dict)
    # otherwise is candidate
    else:
        icon_dict = {}
        icon_dict = get_candidate_icons(instance, icon_dict)

    return icon_dict
