import csv
import pathlib
import string
import us
from django_typer.management import Typer
from ingestion.setup_us_states_counties import make_county_to_court_df
from ingestion.ingest_courts import (
    MERGED_COURTS_PATH,
    COURT_LOOKUP_LONG,
    COURT_LOOKUP_SHORT,
)
from datetime import date, datetime
from apps.judgement_call.models import (
    Court,
    CountyToCourt,
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

"""
TO DO: decide how to format this - one ingest function to be called
from the command line for each dataset?
courts will probably need to be created once,
people and tenure will need to be updated occasionally,
cases will need to be updated regularly
"""

app = Typer()


@app.command()
def command(self):
    # TODO: scrape State Case Database
    # generate unique document IDs
    # check if any are new
    # eg new_cases = df[df["docket_id"].notin(all_cases)]
    all_cases = [case["case_id"] for case in Case.objects.values("case_id")]
    print(all_cases)
    # run LLM processing on new_cases
    # case = {"case_id": , ...}
    # case, updated = Case.objects.update_or_create(**case)
    # indop = {"case": case, "judge_alias": , ...}
    # indop, created = IndividualOpinion.objects.get_or_create(**indop)


# HELPER FUNCTIONS


def empty_string_to_none(value):
    return value if value != "" else None


def standardize_alias(alias: str):
    return alias.strip().lower().translate(str.maketrans("", "", string.punctuation))


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
