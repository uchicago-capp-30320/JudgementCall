# import ingestion.ingest_courts_data
# import ingestion.merge_courts_data
import csv
import pathlib
from apps.judgement_call.models import Court, CountyToCourt, Case, IndividualOpinion, Alias
from django_typer.management import Typer
from ingestion.setup_us_states_counties import make_county_to_court_df
from ingestion.ingest_courts import (
    MERGED_COURTS_PATH,
    get_courts_df,
    COURT_LOOKUP_LONG,
    COURT_LOOKUP_SHORT,
)
from datetime import date, datetime
from apps.judgement_call.models import (
    Court,
    Case,
    IndividualOpinion,
    Person,
    Tenure,
    Alias,
    SelectionType,
    PersonGender,
    PersonRace,
    PartyAffiliation,
)
from django.db import IntegrityError

"""
TO DO: decide how to format this - one ingest function to be called
from the command line for each dataset?
courts will probably need to be created once,
people and tenure will need to be updated occasionally,
cases will need to be updated regularly
"""

app = Typer()


@app.command()
def command(self, data: str):
    if data == "courts":
        if MERGED_COURTS_PATH.is_file():
            with open(MERGED_COURTS_PATH, encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    headers = row
                    break
                for row in reader:
                    court = dict(zip(headers, row))
                    numeric_fields = ["bench_size", "term_length"]

                    for field in numeric_fields:
                        court[field] = empty_string_to_none(court[field])

                    print(court)
                    Court.objects.update_or_create(**court)

    if data == "cases":
        with open("./data/prototype_cases.csv", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                headers = row
                break
            for row in reader:
                case = dict(zip(case_model_cols, row))
                case.pop("", None)
                court_id = COURT_LOOKUP_LONG[case["state"]]
                lookup_court = Court.objects.get(court_id=court_id)
                case["court"] = lookup_court
                case.pop("state", None)
                case["decision_date"] = case["decision_date"].replace("/", "-")
                print(case)
                Case.objects.update_or_create(**case)

    if data == "individual-opinions":
        with open("./data/prototype_individual_opinions.csv", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                headers = row
                break
            for row in reader:
                indop = dict(zip(headers, row))
                indop.pop("", None)
                case_id = indop["case_id"]
                lookup_case = Case.objects.get(case_id=case_id)
                print(lookup_case.court)
                indop["case"] = lookup_case
                alias = indop["name"]
                alias, found = Alias.objects.get_or_create(alias=alias, court=lookup_case.court)
                print(alias)
                indop["judge_alias"] = alias
                indop.pop("name", None)
                indop.pop("case_id", None)
                print(indop)
                IndividualOpinion.objects.update_or_create(**indop)

    if data == "county-to-court":
        county_df = make_county_to_court_df()
        for index, row in county_df.iterrows():
            county = dict(**row)
            court = county.pop("court", None)
            lookup_court = Court.objects.get(court_id=court)
            county, created = CountyToCourt.objects.update_or_create(**county)
            county.court.add(lookup_court)
            
    if data == "tenures":
        with open("./data/judges_slri.csv", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                headers = row
                break
            for row in reader:
                person = {}
                tenure = {}
                judge = dict(zip(headers, row))
                court_id = COURT_LOOKUP_SHORT.get(judge["state"], None)
                if court_id is None:
                    continue
                lookup_court = Court.objects.get(court_id=court_id)
                print(lookup_court)
                person = {
                    "name_canonical": judge["name"],
                    # "birth_date": ,
                    "gender": slri_gender.get(judge["gender"], judge["gender"]),
                    "race": slri_race.get(judge["race"], judge["race"]),
                    "party_registration": slri_party.get(judge["party"], None),  # NOT ACCURATE
                    "professional_experience": judge["professional experience"],
                    "law_school": "",
                }
                print(judge)
                person, created = Person.objects.update_or_create(**person)
                # create person and return person
                try:
                    judge["term start"] = datetime.strptime(judge["term start"], "%B %d, %Y")
                except (TypeError, ValueError):
                    judge["term start"] = datetime(3000, 1, 1, 0, 0)
                try:
                    judge["term end"] = datetime.strptime(judge["term end"], "%B %d, %Y")
                except (TypeError, ValueError):
                    judge["term end"] = datetime(3000, 1, 1, 0, 0)
                tenure = {
                    "court": lookup_court,
                    "person": person,  # returned person value
                    "start_date": judge["term start"],
                    "end_date": judge["term end"],
                    "selection_type": slri_selection_type_parse(
                        judge["election type"]
                    ),  # choices selection type
                    # "ticket_party": "", #????
                    # "appointer_name": "",
                    # "appointer_party": "", #
                    # "chief_justice": "",
                }
                try:
                    tenure, created = Tenure.objects.update_or_create(**tenure)
                except IntegrityError:
                    continue


def empty_string_to_none(value):
    if value == "":
        return None
    else:
        return value


slri_race = {
    "white": PersonRace.WHITE,
    "black": PersonRace.BLACK,
    "asian american": PersonRace.ASIAN,
    "pacific islander": PersonRace.NHPI,
}

slri_gender = {
    "male": PersonGender.MALE,
    "female": PersonGender.FEMALE,
}

slri_party = {
    "democrat": PartyAffiliation.DEM,
    "republican": PartyAffiliation.REP,
    "unsure": "",
}

slri_selection_type = {
    "elected, nonpartisan": SelectionType.NONPARTISAN,
    "elected, partisan": SelectionType.PARTISAN,
    "appointed": SelectionType.APPOINTMENT,
    "appointed, leg confirmed": SelectionType.APPOINTMENT,
    "appointed, retention elected": SelectionType.RETENTION,
    "appointed, leg confirmed, retention elected": SelectionType.RETENTION,
}


def slri_selection_type_parse(slri_selection_type):
    if "elected, nonpartisan" in slri_selection_type:
        return SelectionType.NONPARTISAN
    elif "elected, partisan" in slri_selection_type:
        return SelectionType.PARTISAN
    elif "retention elected" in slri_selection_type:
        return SelectionType.RETENTION
    elif "appointed" in slri_selection_type:
        return SelectionType.APPOINTMENT
    elif "leg elected" in slri_selection_type:
        return SelectionType.LEGISLATURE
    else:
        return None


case_csv_cols = [
    "",
    "case_id",
    "docket_no",
    "title",
    "state",
    "date",
    "type",
    "description",
    "plaintiff_argument",
    "defendant_argument",
    "decision_outcome",
    "decision_winner",
    "environment",
    "consumers",
    "reproductive_rights",
    "democratic_norms",
    "free_press",
    "public_health",
    "separation_church_state",
    "voting_access",
    "public_education",
    "free_speech",
    "privacy",
    "worker_rights",
]

case_model_cols = [
    "",
    "case_id",
    "docket_no",
    "case_title",
    "state",
    "decision_date",
    "case_type",
    "description",
    "plaintiff_argument",
    "defendant_argument",
    "decision_outcome",
    "decision_winner",
    "environment",
    "consumers",
    "reproductive_rights",
    "democratic_norms",
    "free_press",
    "public_health",
    "separation_church_state",
    "voting_access",
    "public_education",
    "free_speech",
    "privacy",
    "worker_rights",
]
