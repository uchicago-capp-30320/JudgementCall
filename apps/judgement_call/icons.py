from .models import (
    Court,
    Person,
    Election,
    Candidacy,
    Tenure,
    Case,
    IndividualOpinion,
    CourtLevel,
    SelectionType,
    CaseType,
    SelectionJurisdictionType,
    Alias,
    CaseParticipant,
    TopicAlignment,
    RulingType,
    CountyToCourt,
    PersonGender,
    PersonRace,
    PartyAffiliation,
)

### PEOPLE WITH TENURE ###


# up for election soon
def up_for_election():
    "returns bool"
    up_for_election = True

    return up_for_election


# long tenure (>=10yr)
def long_tenure():
    "returns bool indicating >=10yr of current tenure"
    long_tenure = True

    return long_tenure


# has ruled to protect <topic>
def protect_topics():
    "returns something indicating issue protection areas, tbd"
    # TODO


# has ruled to infringe upon <topic>
def infringe_topics():
    "returns something indicating issue infringement areas, tbd"
    # TODO


### NOT TENURE-SPECIFIC ATTRIBUTES ###


# worked as a public defender
# worked as a prosecutor
# worked in legal aid
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


# do a filler for relevant endorsements
# list of municipal & party endorsers and then randomly select in favor or against
def endorsements():
    "returns fake endorsements"


# could do same for scandal, should set toggle to turn these off if we don't want them
def has_scandals():
    "returns fake scandal flag"


# maybe change color to indicate fake data


def get_judge_icons(tenure):
    "get icons related to judges"


def get_candidate_icons(person):
    "get icons related to candidates"


def get_icon_dict(id, is_election):
    """
    end product should look like:
    person_attributes = {
        if judge {judge_stuff},
        person stuff {person_stuff}
    }
    """
    # get relevant id and then flag if it's for an election or not I guess
    # call all the helpers to create person-level dictionary
    # if not is_election:
    #     # working with court_id
    #     court = Court.objects.get(court_id=id)
    #     justices = [ten for ten in Tenure.objects.filter(court=court)]

    #     for ten in justices:
    #         icon_dict = get_judge_icons(ten)
