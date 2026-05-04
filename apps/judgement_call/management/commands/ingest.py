# import ingestion.ingest_courts_data
# import ingestion.merge_courts_data
import csv
import pathlib
from apps.judgement_call.models import Court, Case, IndividualOpinion, Alias
from django_typer.management import Typer
from ingestion.ingest_courts import MERGED_COURTS_PATH, get_courts_df, COURT_LOOKUP_LONG

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


def empty_string_to_none(value):
    if value == "":
        return None
    else:
        return value


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
