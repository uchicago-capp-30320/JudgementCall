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

# long tenure (>=10yr)

# has ruled to protect <topic>

# has ruled to infringe upon <topic>


### NOT TENURE-SPECIFIC ATTRIBUTES ###

# worked as a public defender

# worked as a prosecutor

# idk fancy law school?

# personal party affiliation

# do a filler for relevant endorsements
# list of municipal endorsers and then randomly select in favor or against

# could do same for scandal, should set toggle to turn these off if we don't want them

# maybe change color to indicate fake data


def get_icon_dict():
    """
    end product should look like:
    person_attributes = {
        if judge {judge_stuff},
        person stuff {person_stuff}
    }
    """
    # TODO
