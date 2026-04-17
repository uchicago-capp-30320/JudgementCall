import ingestion
from apps.app_name.models import Court

"""
TO DO: decide how to format this - one ingest function to be called from the command line for each dataset?
courts will probably need to be created once,
people and tenure will need to be updated occasionally,
cases will need to be updated regularly
"""


def create_courts():
    courts_data = ingestion.ingest_courts_data()
    for court in courts_data:
        continue  # don't want to touch database yet!
        Court.objects.update_or_create(
            name=court["name"],
            # etc
        )
