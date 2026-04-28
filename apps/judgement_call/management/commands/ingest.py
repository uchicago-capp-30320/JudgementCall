# import ingestion.ingest_courts_data
# import ingestion.merge_courts_data
import csv
from apps.judgement_call.models import Court
from django_typer.management import Typer

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
    print("Hello world")

    if data == "courts":
        with open("ingestion/merged_courts_local.csv", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                headers = row
                break
            for row in reader:
                court = dict(zip(headers, row))
                court["term_length"] = (
                    court["term_length"]
                    .replace(" yrs", "")
                    .replace("yrs", "")
                    .replace(" years", "")
                )
                try:
                    court["term_length"] = int(court["term_length"])
                except ValueError:
                    court["term_length"] = None
                try:
                    court["bench_size"] = int(court["bench_size"])
                except ValueError:
                    court["bench_size"] = None
                Court.objects.update_or_create(**court)
