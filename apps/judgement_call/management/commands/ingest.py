import csv
import pathlib
import string
import json
import us
from pathlib import Path
from tqdm import tqdm
from dateutil.parser import parse
from django_typer.management import Typer
from ingestion.setup_us_states_counties import make_county_to_court_df
from ingestion.ingest_courts import MERGED_COURTS_PATH
from ingestion.merge_wiki_slri import OUTPUT_CSV as MERGED_JUDGES_PATH
from ingestion.state_crosswalks import (
    COURT_LOOKUP_LONG,
    COURT_LOOKUP_SHORT,
)
from datetime import date, datetime
from apps.judgement_call.models import (
    Court,
    CountyToCourt,
    CaseProcessingRun,
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

"""

app = Typer()


@app.command()
def command(self, data: str):
    if data == "courts":
        count_courts = 0
        count_courts_created = 0
        if MERGED_COURTS_PATH.is_file():
            with open(MERGED_COURTS_PATH, encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    headers = row
                    break
                for row in tqdm(reader):
                    court = dict(zip(headers, row))
                    numeric_fields = ["bench_size", "term_length"]

                    for field in numeric_fields:
                        court[field] = empty_string_to_none(court[field])

                    # print(court) #todo: verbose flag
                    court, created = Court.objects.update_or_create(
                        court_id=court["court_id"], defaults={**court}
                    )
                    count_courts += 1
                    if created:
                        count_courts_created += 1

                    # print(court, created)
        print(f"courts: {count_courts}, created: {count_courts_created}")

    if data == "county-to-court":
        count_countytocourts = 0
        count_countytocourts_created = 0
        county_df = make_county_to_court_df()
        for _, row in tqdm(county_df.iterrows()):
            county = dict(**row)
            lookup_court = Court.objects.get(court_id=county["court_id"])
            countytocourt, created = CountyToCourt.objects.get_or_create(
                state=county["state"], county=county["county"], fips=county["fips"]
            )
            countytocourt.court.add(lookup_court)
            count_countytocourts += 1
            if created:
                count_countytocourts_created += 1
            # print(f"county:{countytocourt}, created: {created}, added court: {lookup_court}")
        print(f"countytocourts: {count_countytocourts}, created: {count_countytocourts_created}")

    if data == "cases":
        with open("./data/run_metadata/llm_run_05-15-2026.json") as file:
            d = json.load(file)
            d.pop("cases_processed")
            print(d)
            d["timestamp"] = datetime.strptime(d["timestamp"], "%m-%d-%Y")
            cpr, cpr_created = CaseProcessingRun.objects.get_or_create(**d)
            print(cpr, cpr_created)

        cases_created = 0
        for state in us.STATES:
            print(state.name)
            state_case_path = pathlib.Path(f"./data/cases/{state.name}.csv")
            print(f"{state.name} file found: {state_case_path.is_file()}")

            court_id = COURT_LOOKUP_LONG[state.name]
            lookup_court = Court.objects.get(court_id=court_id)

            with open(state_case_path, encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    headers = row
                    break
                for row in reader:
                    row_dict = dict(zip(headers, row))
                    case_dict = build_case(row_dict)
                    case_dict["court"] = lookup_court
                    # case["decision_date"] = case["decision_date"].replace("/", "-")
                    case_dict["case_processing_run"] = cpr
                    print(cpr)
                    print(case_dict)
                    case, created = Case.objects.update_or_create(
                        case_id=case_dict["case_id"], defaults=case_dict
                    )
                    print(case, created)
                    cases_created += created
            print(f"Cases created: {cases_created}")

    if data == "individual-opinions":
        opinions_created = 0

        for state in us.STATES:
            print(state.name)
            state_opinion_path = pathlib.Path(f"./data/opinions/{state.name}.csv")
            print(f"{state.name} file found: {state_opinion_path.is_file()}")
            court_id = COURT_LOOKUP_LONG[state.name]
            lookup_court = Court.objects.get(court_id=court_id)

            with open(state_opinion_path, encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    headers = row
                    break
                for row in reader:
                    row_dict = dict(zip(headers, row))
                    # link to case
                    case_id = row_dict["case_id"]
                    lookup_case = Case.objects.get(case_id=case_id)
                    # link to alias
                    alias, found = Alias.objects.get_or_create(
                        alias=row_dict["name"], court=lookup_case.court
                    )
                    # create indop dict
                    indop = build_indop(row_dict)
                    indop["judge_alias"] = alias
                    indop["case"] = lookup_case
                    print(indop)
                    indop, created = IndividualOpinion.objects.update_or_create(
                        case=lookup_case, judge_alias=alias, defaults=indop
                    )
                    print(indop, created)
                    opinions_created += created
            print(f"Opinions created: {opinions_created}")

    if data == "tenures":
        date_fields = ["start_date", "end_date", "birth_date"]
        with open(MERGED_JUDGES_PATH, encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                headers = row
                break
            for row in tqdm(reader):
                judge = dict(zip(headers, row))
                # quick fix for missing underscore, need to change in scraper
                judge["professional_experience"] = judge["professional experience"]
                print(judge["next election date"])
                print(judge)
                # handle dates
                for field in date_fields:
                    year = year_only(judge.get(field))
                    judge[field] = datetime(year, 1, 1) if year is not None else None
                for party_field in ["ticket_party", "appointer_party"]:
                    party = judge[party_field]
                    judge[party_field] = party_mapping.get(party, PartyAffiliation.UNKNOWN)

                # build person object from judge dict
                person_name, person = build_person(judge)
                person_obj, created = Person.objects.update_or_create(
                    name_canonical=person_name, defaults=person
                )
                print(f"person: {person_obj}, created: {created}")

                # build tenure obj from judge dict
                court_id, tenure = build_tenure(judge)
                court_obj = Court.objects.get(court_id=court_id)
                try:
                    tenure_obj, created = Tenure.objects.update_or_create(
                        court=court_obj, person=person_obj, defaults=tenure
                    )
                    print(f"tenure: {tenure_obj}, created: {created}")
                except IntegrityError as e:  # debugging
                    print(f"integrity error: {e}")
                    continue


# HELPER FUNCTIONS


def empty_string_to_none(value):
    return value if value != "" else None


def year_only(date_as_string):
    if date_as_string and date_as_string is not None:
        if "or" in date_as_string:
            date_as_string = date_as_string.split(" ")[0]
        return parse(date_as_string, fuzzy=True).year


def build_indop(row_dict: dict):
    indop_fields = ["description", "ruling"]
    return {k: v for k, v in row_dict.items() if k in indop_fields}


def build_case(row_dict: dict):
    case_fields = case_model_cols
    row_dict["case_type"] = row_dict["type"]
    row_dict["decision_date"] = row_dict["date"]
    row_dict["case_title"] = row_dict["title"]
    return {k: v for k, v in row_dict.items() if k in case_fields}


def build_person(row_dict: dict):
    person_fields = [
        "name_canonical",
        "birth_date",
        "gender",
        "race",
        "party_registration",
        "professional_experience",
        "law_school",
    ]
    person_name = row_dict.get("name")
    defaults = {k: v for k, v in row_dict.items() if k in person_fields}
    return person_name, defaults


def build_tenure(row_dict: dict):
    tenure_fields = [
        # "court",
        # "person",
        "start_date",
        "end_date",
        "selection_type",
        "ticket_party",
        "appointer_name",
        "appointer_party",
        "chief_justice",
        "source_url",
        "scraped_at",
    ]
    court_id = COURT_LOOKUP_LONG.get(row_dict.get("state", ""), "")
    defaults = {k: v for k, v in row_dict.items() if k in tenure_fields}
    return court_id, defaults


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


party_mapping = {
    # wikipedia appointer party
    "D": PartyAffiliation.DEM,
    "R": PartyAffiliation.REP,
    # wikipedia ticket party
    "Democrat": PartyAffiliation.DEM,
    "Republican": PartyAffiliation.REP,
    # SLRI party codes
    "democrat": PartyAffiliation.DEM,
    "republican": PartyAffiliation.REP,
    "independent": PartyAffiliation.IND,
    "unsure": PartyAffiliation.UNKNOWN,
}

indop_csv_cols = ["case_id", "name", "description", "ruling"]

case_csv_cols = [
    # "",
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
    # "",
    "case_id",
    "docket_no",
    "case_title",
    # "state",
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
