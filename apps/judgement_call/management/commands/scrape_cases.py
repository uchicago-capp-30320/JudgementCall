import csv
from pathlib import Path
import string
import us
from django_typer.management import Typer
from ingestion.setup_us_states_counties import make_county_to_court_df
from ingestion.ingest_cases_opinions import produce_tables, generate_case_id
from ingestion.ingest_sc_cases import scrape_scdb
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
    all_current_cases = scrape_scdb(write_on=False)

    # check if any are new
    # eg new_cases = df[df["docket_id"].notin(all_cases)]
    db_cases_ids = [case["case_id"] for case in Case.objects.values("case_id")]
    new_cases = all_current_cases[~all_current_cases["case_id"].isin(db_cases_ids)]
    print("New cases not in database:")
    print(new_cases)

    # run LLM processing on new_cases
    if not new_cases.empty:
        prompt_path = Path(__file__).parent.parent.parent.parent.parent / "ingestion" / "prompt.txt"
        table_dic = produce_tables(new_cases, prompt_path, use_existing=False)

        cases = table_dic["case_table"].reset_index(drop=True).to_dict(orient="records")
        for case in cases:
            Case.objects.update_or_create(**case)

        ind_opinions = (
            table_dic["individual_opinion_table"].reset_index(drop=True).to_dict(orient="records")
        )
        for ind_op in ind_opinions:
            IndividualOpinion.objects.update_or_create(**ind_op)


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
