from django.core.management.base import BaseCommand
from django_typer.management import Typer
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

app = Typer()


class Command(BaseCommand):
    help = "Matches aliases against names of judges in the tenure table"

    def add_arguments(self, parser):
        parser.add_argument("add", type=bool)
        parser.add_argument("update", type=bool)

    def handle(self, **options):
        matched_tenures = 0

        all_aliases = Alias.objects.all()
        count_all_aliases = len(all_aliases)
        for alias in all_aliases:
            if options["add"]:
                tenure = alias.match_tenure(options["update"])
                if tenure is not None:
                    matched_tenures += 1
            else:
                matches = alias.find_matches()
                print(matches)
        print(
            f"{matched_tenures} out of {count_all_aliases}",
            f"({matched_tenures / count_all_aliases * 100}%) of aliases matched",
        )
