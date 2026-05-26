import csv
from pathlib import Path
import string
import us
from django.core.management.base import BaseCommand
from django_typer.management import Typer
from ingestion.ingest_cases_opinions import produce_tables
from ingestion.ingest_sc_cases import scrape_scdb
from ingestion.state_crosswalks import (
    COURT_LOOKUP_LONG,
    COURT_LOOKUP_SHORT,
)
from datetime import date, datetime
from apps.judgement_call.models import (
    Court,
    CountyToCourt,
    Case,
    CaseProcessingRun,
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


class Command(BaseCommand):
    def handle(self, **options):
        # Scrape State Case Database
        all_current_cases = scrape_scdb(write_on=True, incremental=True)

        # check if any are new
        # eg new_cases = df[df["docket_id"].notin(all_cases)]
        db_cases_ids = [case["case_id"] for case in Case.objects.values("case_id")]
        new_cases = all_current_cases[~all_current_cases["case_id"].isin(db_cases_ids)]
        print(f"There are {len(new_cases)} new cases not in database:")
        print(new_cases)

        # run LLM processing on new_cases if there are any
        if not new_cases.empty:
            table_dic, run_metadata = produce_tables(new_cases, use_existing=False, write_on=False)

            # Insert run metadata into database
            run_metadata.pop("cases_processed")
            run_metadata["timestamp"] = datetime.strptime(run_metadata["timestamp"], "%m-%d-%Y")
            cpr, cpr_created = CaseProcessingRun.objects.get_or_create(**run_metadata)

            # Insert cases into database
            cases = table_dic["case_table"].reset_index(drop=True).to_dict(orient="records")
            for case in cases:
                court = Court.objects.get(court_id=COURT_LOOKUP_LONG[case["state"]])
                new_case = {
                    "case_id": case["case_id"],
                    "case_processing_run": cpr,
                    "case_title": case["title"],
                    "case_type": case["type"],
                    "consumers": case["consumers"],
                    "court": court,
                    "decision_date": datetime.strptime(case["date"], "%Y-%m-%d"),
                    "decision_outcome": case["decision_outcome"],
                    "decision_winner": case["decision_winner"],
                    "defendant_argument": case["defendant_argument"],
                    "democratic_norms": case["democratic_norms"],
                    "description": case["description"],
                    "docket_no": case["docket_no"],
                    "environment": case["environment"],
                    "free_press": case["free_press"],
                    "free_speech": case["free_speech"],
                    "plaintiff_argument": case["plaintiff_argument"],
                    "privacy": case["privacy"],
                    "public_education": case["public_education"],
                    "public_health": case["public_health"],
                    "reproductive_rights": case["reproductive_rights"],
                    "separation_church_state": case["separation_church_state"],
                    "voting_access": case["voting_access"],
                    "worker_rights": case["worker_rights"],
                }
                if len(case["opinion_link"]) > 200:
                    new_case["document_url"] = None
                else:
                    new_case["document_url"] = case["opinion_link"]

                Case.objects.update_or_create(case_id=case["case_id"], defaults=new_case)

            # Insert individual opinions into database
            ind_opinions = (
                table_dic["individual_opinion_table"]
                .reset_index(drop=True)
                .to_dict(orient="records")
            )
            for ind_op in ind_opinions:
                case = Case.objects.get(case_id=ind_op["case_id"])
                alias, found = Alias.objects.get_or_create(alias=ind_op["name"], court=case.court)
                new_opinion = {
                    "case": case,
                    "judge_alias": alias,
                    "description": ind_op["description"],
                    "ruling": ind_op["ruling"],
                }
                IndividualOpinion.objects.update_or_create(
                    case=case, judge_alias=alias, defaults=new_opinion
                )
        else:
            print("No new cases that are not in the database.")
