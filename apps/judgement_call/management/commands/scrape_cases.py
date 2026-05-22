import csv
from pathlib import Path
import string
import us
from django.core.management.base import BaseCommand
from django_typer.management import Typer
from ingestion.ingest_cases_opinions import produce_tables
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
    def ingest_new_cases():
        # TODO: scrape State Case Database
        all_current_cases = scrape_scdb(write_on=False)

        # check if any are new
        # eg new_cases = df[df["docket_id"].notin(all_cases)]
        db_cases_ids = [case["case_id"] for case in Case.objects.values("case_id")]
        new_cases = all_current_cases[~all_current_cases["case_id"].isin(db_cases_ids)]
        print("New cases not in database:")
        print(new_cases)

        # run LLM processing on new_cases if there are any
        if not new_cases.empty:
            prompt_path = (
                Path(__file__).parent.parent.parent.parent.parent / "ingestion" / "prompt.txt"
            )
            table_dic, run_metadata = produce_tables(new_cases, prompt_path, use_existing=False)

            # Insert cases into database
            cases = table_dic["case_table"].reset_index(drop=True).to_dict(orient="records")
            for case in cases:
                Case.objects.update_or_create(**case)

            # Insert individual opinions into database
            ind_opinions = (
                table_dic["individual_opinion_table"]
                .reset_index(drop=True)
                .to_dict(orient="records")
            )
            for ind_op in ind_opinions:
                IndividualOpinion.objects.update_or_create(**ind_op)

            # Insert run metadata into database
            run_metadata.pop("cases_processed")
            CaseProcessingRun.objects.update_or_create(**run_metadata)
